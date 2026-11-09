from app import app
from app.excel_export import workbook_bytes
from app.pdf_export import final_analysis_pdf, pretest_analysis_pdf
from app.controller import *
from app.decorator.utils import level_required
from flask_login import current_user, login_required
from app.model import Classes, User, EvaluationResult, PretestResult, Score, FinalResult
from app.controller.PretestController import QUESTIONS_PRETEST
from flask import Flask, render_template, request, redirect, url_for, Response
from flask import session
from datetime import datetime, timezone
import json


QUIZ_ATTEMPT_DURATION_SECONDS = 15 * 60
EVALUATION_ATTEMPT_DURATION_SECONDS = 20 * 60
AUTO_SUBMIT_GRACE_SECONDS = 5


def _consume_quiz_attempt(session_key):
    started_at = session.pop(session_key, None)
    if not isinstance(started_at, str):
        return False
    try:
        parsed_start = datetime.fromisoformat(started_at)
        if parsed_start.tzinfo is None:
            parsed_start = parsed_start.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - parsed_start).total_seconds()
    except (TypeError, ValueError):
        return False
    max_duration = (
        EVALUATION_ATTEMPT_DURATION_SECONDS
        if session_key == 'quiz_start_time_evaluation'
        else QUIZ_ATTEMPT_DURATION_SECONDS
    )
    # Browser waits two seconds after its timer reaches zero before auto-submit.
    return 0 <= elapsed <= max_duration + AUTO_SUBMIT_GRACE_SECONDS


TEMPLATE_SOURCE_EXTENSIONS = ('.html', '.htm', '.jinja', '.j2', '.bak', '.py', '.txt', '.md')


@app.before_request
def _hide_template_sources():
    # Learning pages keep their images/GIFs/JS under resources/views; only
    # template source files must be hidden, not the assets they reference.
    if request.path == '/resources/views':
        return 'Not Found', 404
    if request.path.startswith('/resources/views/'):
        if request.path.lower().endswith(TEMPLATE_SOURCE_EXTENSIONS):
            return 'Not Found', 404


@app.context_processor
def _inject_navigation_level():
    """Current level for learning navigation, with a safe fallback for previews."""
    level = (request.view_args or {}).get('klasifikasi')
    if level is None and current_user.is_authenticated:
        level = getattr(current_user, 'klasifikasi', None)
    return {'nav_klas': 0 if level is None else level}


@app.route("/")
def index():
    
    amount_classes=get_amount_classes()
    amount_teacher=get_amount_teacher()
    amount_student=get_amount_student()
    total_materi=get_total_materi()
    leaderboard=get_home_leaderboard()
    
    return render_template("index.html", ac=amount_classes, at=amount_teacher, ast=amount_student, total_materi=total_materi, leaderboard=leaderboard)

@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")

@app.route("/list-course", methods=["GET"])
def list_course():
    return render_template("list_course.html")

@app.route("/instruction", methods=["GET"])
def instruction():
    return render_template("instruction.html")

# Login Handle ====================================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        return UserController.login_siswa()

@app.route("/login/teacher", methods=["GET", "POST"])
def login_teacher():
    if request.method == "GET":
        return render_template("login_teacher.html")
    else:
        return UserController.login_teacher()

@app.route("/login/admin", methods=["GET", "POST"])
def login_admin():
    if request.method == "GET":
        return render_template("login_admin.html")
    else:
        return UserController.login_admin()

@app.route("/logout")
@login_required
def logout():
    return UserController.logout()

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        return UserController.register()

# End Login Handle ===============================================================================


# Pretest Handle ===============================================================================

@app.route("/pretest/<int:user_id>", methods=["GET"])
@login_required
def pretest(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403
    if current_user.level == 0 and current_user.pretest_result is not None:
        return redirect(url_for('dashboard_student', user_id=user_id))
    
    return render_template("pretest/preparation.html", user_id=user_id)

@app.route("/pretest/start/<int:user_id>", methods=["GET"])
@login_required
def pretest_start(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403
    if current_user.level == 0 and current_user.pretest_result is not None:
        return redirect(url_for('dashboard_student', user_id=user_id))
    
    safe_questions = [
        {k: v for k, v in q.items() if k != "correct"}
        for q in QUESTIONS_PRETEST
    ]
    return render_template("pretest/pretest_start.html", questions=safe_questions, user_id=user_id)

@app.route("/pretest/submit/<int:user_id>", methods=["POST"])
@login_required
def submit_pretest(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403
    if current_user.level == 0 and current_user.pretest_result is not None:
        return jsonify({'error': 'Pretest sudah dikirim.'}), 409

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('answers'), dict):
        return jsonify({'error': 'Format jawaban pretest tidak valid.'}), 400

    time_taken = data.get('time_taken', 0)
    if not isinstance(time_taken, int) or isinstance(time_taken, bool) or not 0 <= time_taken <= 60 * 60:
        return jsonify({'error': 'Durasi pretest tidak valid.'}), 400
    return save_pretest(data, user_id)

@app.route("/api/pretest/analyze/<int:user_id>", methods=["POST"])
@login_required
def api_analyze_pretest(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403

    data = request.get_json()

    return analyze_pretest(data)

@app.route("/pretest/finish/<int:user_id>", methods=["GET"])
@login_required
def finish_pretest(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403

    # Jika akses diizinkan, render halaman ini
    return render_template("pretest/finish_pretest.html", user_id=user_id)


# Halaman menunggu analisis AI oleh guru ===========================================================
@app.route("/pretest/waiting/<int:user_id>", methods=["GET"])
@login_required
def waiting_analysis(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403
    return render_template("pretest/waiting_analysis.html", user_id=user_id)

# End Pretest Handle ===============================================================================

@app.route("/waiting/pretest/<int:user_id>", methods=["GET"])
@login_required
def waiting_pretest(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403
    return render_template(f"waiting-for-analysis.html", user_id=user_id)

# Evaluation Handle ==================================================================================

@app.route("/learning/evaluation/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_evaluation(user_id, klasifikasi):
    return can_access_learning_evaluation(user_id, klasifikasi)

@app.route("/evaluation/start/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def evaluation_start(user_id, klasifikasi):
    return can_access_learning_evaluation_start(user_id, klasifikasi)

@app.route("/evaluation/submit/<int:user_id>", methods=["POST"])
@login_required
def submit_evaluation(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403
    if current_user.level == 0 and current_user.evaluation_result is not None:
        return jsonify({'error': 'Evaluasi sudah dikirim.'}), 409

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('answers'), dict):
        return jsonify({'error': 'Format jawaban evaluasi tidak valid.'}), 400
    time_taken = data.get('time_taken', 0)
    if not isinstance(time_taken, int) or isinstance(time_taken, bool) or not 0 <= time_taken <= EVALUATION_ATTEMPT_DURATION_SECONDS:
        return jsonify({'error': 'Durasi evaluasi tidak valid.'}), 400
    if current_user.level == 0 and not _consume_quiz_attempt('quiz_start_time_evaluation'):
        return jsonify({'error': 'Percobaan evaluasi tidak aktif, kedaluwarsa, atau sudah dikirim.'}), 409

    return save_evaluation(data, user_id)

# Evaluation Handle ==================================================================================

# Helper: cek akses siswa ke halaman belajar =======================================================
def _check_student_learning_access():
    if current_user.level != 0:
        return True
    pr = current_user.pretest_result
    if pr is None or pr.ai_analysis is None:
        return False
    return True

def is_student_waiting_analysis():
    if current_user.level != 0:
        return False
    pr = current_user.pretest_result
    return pr is not None and pr.ai_analysis is None


@app.before_request
def _block_student_if_waiting_analysis():
    if current_user.is_authenticated and current_user.level == 0:
        path = request.path
        requested_level = (request.view_args or {}).get('klasifikasi')
        if (
            requested_level is not None
            and current_user.klasifikasi is not None
            and requested_level != current_user.klasifikasi
        ):
            return render_template('403.html'), 403
        blocked_prefixes = ('/learning/', '/quiz/', '/evaluation/', '/api/learning/', '/api/bab')
        if path.startswith(blocked_prefixes):
            from flask import flash
            pr = getattr(current_user, 'pretest_result', None)
            if pr is None:
                flash("Kamu harus menyelesaikan Pretest terlebih dahulu.", "warning")
                return redirect(url_for('pretest', user_id=current_user.id))
            if pr.ai_analysis is None:
                flash("Selesaikan Pretest atau tunggu analisis guru terlebih dahulu.", "warning")
                return redirect(url_for('dashboard_student', user_id=current_user.id))
            if current_user.klasifikasi is None:
                flash("Klasifikasi kemampuanmu belum ditentukan. Silakan tunggu analisis guru.", "warning")
                return redirect(url_for('dashboard_student', user_id=current_user.id))

# Routing Learning Bangun Datar (Low) =========================================================================

@app.route("/learning/bangun_datar/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bangun_datar(user_id, klasifikasi):
    return can_access_bangun_datar(user_id, klasifikasi)

@app.route("/learning/bangun_datar/01_d/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bangun_datar_1d(user_id, klasifikasi):
    return can_access_bangun_datar_1d(user_id, klasifikasi)


@app.route("/learning/bangun_datar/01/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bangun_datar_1(user_id, klasifikasi):
    from app.controller.LearningController import can_access_bangun_datar
    return can_access_bangun_datar(user_id, klasifikasi)


@app.route("/learning/bangun_datar/02/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bangun_datar_2(user_id, klasifikasi):
    return can_access_bangun_datar_2(user_id, klasifikasi)

@app.route("/learning/bangun_datar/03/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bangun_datar_3(user_id, klasifikasi):
    return can_access_bangun_datar_3(user_id, klasifikasi)

@app.route("/learning/bangun_datar/04/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bangun_datar_4(user_id, klasifikasi):
    return can_access_bangun_datar_4(user_id, klasifikasi)

@app.route("/learning/bangun_datar/05/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bangun_datar_5(user_id, klasifikasi):
    return can_access_bangun_datar_5(user_id, klasifikasi)

@app.route("/learning/bangun_datar/06/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bangun_datar_6(user_id, klasifikasi):
    return can_access_bangun_datar_6(user_id, klasifikasi)
@app.route("/learning/bangun_datar/05_2/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bangun_datar_5_2(user_id, klasifikasi):
    return can_access_bangun_datar_5_2(user_id, klasifikasi)


@app.route("/learning/bangun_datar/05_3/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bangun_datar_5_3(user_id, klasifikasi):
    return can_access_bangun_datar_5_3(user_id, klasifikasi)


@app.route("/learning/bangun_datar/06_2/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bangun_datar_6_2(user_id, klasifikasi):
    return can_access_bangun_datar_6_2(user_id, klasifikasi)


@app.route("/learning/bangun_datar/06_3/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bangun_datar_6_3(user_id, klasifikasi):
    return can_access_bangun_datar_6_3(user_id, klasifikasi)


@app.route("/quiz/bangun_datar/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def quiz_bangun_datar(user_id, klasifikasi):
    return can_access_bangun_datar_quiz(user_id, klasifikasi)

@app.route("/quiz/bangun_datar/start/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def quiz_start_bangun_datar(user_id, klasifikasi):
    return can_access_bangun_datar_quiz_start(user_id, klasifikasi)

@app.route('/api/bangun_datar/quiz/<int:user_id>/0', methods=['POST'])
@login_required
def api_bangun_datar_quiz_submit_low(user_id):
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if current_user.level != 0:
        return jsonify({'error': 'Hanya siswa yang dapat mengirim hasil kuis.'}), 403
    if current_user.klasifikasi != 0:
        return jsonify({'error': 'Kuis tidak sesuai klasifikasi siswa.'}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('jawaban'), dict):
        return jsonify({'error': 'Format jawaban tidak valid.'}), 400
    if not _consume_quiz_attempt('quiz_start_time_bangun_datar'):
        return jsonify({'error': 'Percobaan kuis tidak aktif, kedaluwarsa, atau sudah dikirim.'}), 409

    # Jawaban dikirim dari frontend sebagai { 1: "soal1-c", 2: "soal2-b", ... }
    # Key bisa berupa int (JSON number) atau string — normalkan ke string semua
    jawaban_user_raw = data.get('jawaban', {})
    jawaban_user = {str(k): v for k, v in jawaban_user_raw.items()}

    kunci = {"1": "soal1-b", "2": "soal2-c", "3": "soal3-a", "4": "soal4-d", "5": "soal5-b", "6": "soal6-c", "7": "soal7-d", "8": "soal8-a", "9": "soal9-c", "10": "soal10-b"}

    total_soal  = len(kunci)
    total_benar = sum(1 for k, v in kunci.items() if jawaban_user.get(k) == v)
    total_salah = total_soal - total_benar
    score       = round((total_benar / total_soal) * 100)


    # Simpan nilai tertinggi; riwayat tetap menampilkan satu nilai terbaik.
    existing_score = Score.query.filter_by(
        user_id=user_id,
        score_type='quiz',
        chapter='Bangun Datar'
    ).first()

    if existing_score:
        if score > existing_score.value:
            existing_score.correct = total_benar
            existing_score.incorrect = total_salah
            existing_score.value = score
    else:
        db.session.add(Score(
            user_id=user_id,
            class_id=current_user.class_id,
            score_type='quiz',
            chapter='Bangun Datar',
            correct=total_benar,
            incorrect=total_salah,
            value=score,
        ))

    db.session.commit()

    user_class = Classes.query.get(current_user.class_id)
    user_kkm   = user_class.kkm if user_class else 75
    lulus      = score >= user_kkm

    return jsonify({
        'score':         score,
        'total_benar':   total_benar,
        'total_salah':   total_salah,
        'lulus':         lulus,
        'user_kkm':      user_kkm,
        'next_url':      url_for('quiz_bangun_datar', user_id=user_id, klasifikasi=current_user.klasifikasi),
        'jawaban_benar': kunci
    })
    
@app.route('/api/bangun_datar/quiz/<int:user_id>/1', methods=['POST'])
@login_required
def api_bangun_datar_quiz_submit_medium(user_id):
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if current_user.level != 0:
        return jsonify({'error': 'Hanya siswa yang dapat mengirim hasil kuis.'}), 403
    if current_user.klasifikasi != 1:
        return jsonify({'error': 'Kuis tidak sesuai klasifikasi siswa.'}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('jawaban'), dict):
        return jsonify({'error': 'Format jawaban tidak valid.'}), 400
    if not _consume_quiz_attempt('quiz_start_time_bangun_datar'):
        return jsonify({'error': 'Percobaan kuis tidak aktif, kedaluwarsa, atau sudah dikirim.'}), 409

    # Jawaban dikirim dari frontend sebagai { 1: "soal1-c", 2: "soal2-b", ... }
    # Key bisa berupa int (JSON number) atau string — normalkan ke string semua
    jawaban_user_raw = data.get('jawaban', {})
    jawaban_user = {str(k): v for k, v in jawaban_user_raw.items()}

    kunci = {"1": "soal1-b", "2": "soal2-c", "3": "soal3-b", "4": "soal4-c", "5": "soal5-c", "6": "soal6-b", "7": "soal7-c", "8": "soal8-b", "9": "soal9-c", "10": "soal10-b"}

    total_soal  = len(kunci)
    total_benar = sum(1 for k, v in kunci.items() if jawaban_user.get(k) == v)
    total_salah = total_soal - total_benar
    score       = round((total_benar / total_soal) * 100)


    # Simpan nilai tertinggi; riwayat tetap menampilkan satu nilai terbaik.
    existing_score = Score.query.filter_by(
        user_id=user_id,
        score_type='quiz',
        chapter='Bangun Datar'
    ).first()

    if existing_score:
        if score > existing_score.value:
            existing_score.correct = total_benar
            existing_score.incorrect = total_salah
            existing_score.value = score
    else:
        db.session.add(Score(
            user_id=user_id,
            class_id=current_user.class_id,
            score_type='quiz',
            chapter='Bangun Datar',
            correct=total_benar,
            incorrect=total_salah,
            value=score,
        ))

    db.session.commit()

    user_class = Classes.query.get(current_user.class_id)
    user_kkm   = user_class.kkm if user_class else 75
    lulus      = score >= user_kkm

    return jsonify({
        'score':         score,
        'total_benar':   total_benar,
        'total_salah':   total_salah,
        'lulus':         lulus,
        'user_kkm':      user_kkm,
        'next_url':      url_for('quiz_bangun_datar', user_id=user_id, klasifikasi=current_user.klasifikasi),
        'jawaban_benar': kunci
    })
    
@app.route('/api/bangun_datar/quiz/<int:user_id>/2', methods=['POST'])
@login_required
def api_bangun_datar_quiz_submit_high(user_id):
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if current_user.level != 0:
        return jsonify({'error': 'Hanya siswa yang dapat mengirim hasil kuis.'}), 403
    if current_user.klasifikasi != 2:
        return jsonify({'error': 'Kuis tidak sesuai klasifikasi siswa.'}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('jawaban'), dict):
        return jsonify({'error': 'Format jawaban tidak valid.'}), 400
    if not _consume_quiz_attempt('quiz_start_time_bangun_datar'):
        return jsonify({'error': 'Percobaan kuis tidak aktif, kedaluwarsa, atau sudah dikirim.'}), 409

    # Jawaban dikirim dari frontend sebagai { 1: "soal1-c", 2: "soal2-b", ... }
    # Key bisa berupa int (JSON number) atau string — normalkan ke string semua
    jawaban_user_raw = data.get('jawaban', {})
    jawaban_user = {str(k): v for k, v in jawaban_user_raw.items()}

    kunci = {"1": "soal1-c", "2": "soal2-a", "3": "soal3-c", "4": "soal4-d", "5": "soal5-c", "6": "soal6-b", "7": "soal7-a", "8": "soal8-c", "9": "soal9-b", "10": "soal10-d"}

    total_soal  = len(kunci)
    total_benar = sum(1 for k, v in kunci.items() if jawaban_user.get(k) == v)
    total_salah = total_soal - total_benar
    score       = round((total_benar / total_soal) * 100)


    # Simpan nilai tertinggi; riwayat tetap menampilkan satu nilai terbaik.
    existing_score = Score.query.filter_by(
        user_id=user_id,
        score_type='quiz',
        chapter='Bangun Datar'
    ).first()

    if existing_score:
        if score > existing_score.value:
            existing_score.correct = total_benar
            existing_score.incorrect = total_salah
            existing_score.value = score
    else:
        db.session.add(Score(
            user_id=user_id,
            class_id=current_user.class_id,
            score_type='quiz',
            chapter='Bangun Datar',
            correct=total_benar,
            incorrect=total_salah,
            value=score,
        ))

    db.session.commit()

    user_class = Classes.query.get(current_user.class_id)
    user_kkm   = user_class.kkm if user_class else 75
    lulus      = score >= user_kkm

    return jsonify({
        'score':         score,
        'total_benar':   total_benar,
        'total_salah':   total_salah,
        'lulus':         lulus,
        'user_kkm':      user_kkm,
        'next_url':      url_for('quiz_bangun_datar', user_id=user_id, klasifikasi=current_user.klasifikasi),
        'jawaban_benar': kunci
        })

# Halaman Khusus Dashboard Students ==============================================================

@app.route("/dashboard/student/<int:user_id>", methods=["GET"])
@login_required
@level_required(0)
def dashboard_student(user_id):
    if current_user.level == 0 and current_user.pretest_result is None:
        from flask import flash
        flash("Kamu harus menyelesaikan Pretest terlebih dahulu.", "warning")
        return redirect(url_for('pretest', user_id=current_user.id))

    user = get_user_by_id(user_id)

    return render_template(
        "dashboard/student/dashboard.html",
        user=user,
        user_id=user_id,
        overview=get_student_overview_stats(user_id),
        waiting_analysis=is_student_waiting_analysis()
    )

@app.route("/grades/student/<int:user_id>", methods=["GET"])
@login_required
@level_required(0)
def student_grades(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403

    user = get_user_by_id(user_id)
    stats = get_student_dashboard_stats(user_id)

    return render_template(
        "dashboard/student/grades.html",
        user=user,
        user_id=user_id,
        stats=stats
    )

@app.route("/profile/student/<int:user_id>", methods=["GET"])
@login_required
@level_required(0)
def student_profile(user_id):

    data = show_student_ai_analysis(user_id)
    user = get_user_by_id(user_id)
    return render_template(
        'dashboard/student/student_profile.html',
        user=user,
        user_id=user_id,
        student=data['student'],
        ai_analysis=data['ai_analysis'],
    )
    
@app.route('/profile/student/update/<int:user_id>', methods=['POST'])
@login_required
@level_required(0)
def update_profile_route(user_id):

    update_student_profile(user_id)
    
    return redirect(request.referrer or url_for('student_profile', user_id=user_id))

# End Dashboard Students =========================================================================


# Halaman Khusus Dashboard Guru ==================================================================

@app.route("/teacher/choise/course/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def teacher_choise_course(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403

    return render_template("teacher_choise_course.html", user_id=user_id)

@app.route('/teacher/klasifikasi/<int:user_id>', methods=['POST'])
@login_required
@level_required(1)
def teacher_update_klasifikasi(user_id):
    if user_id != current_user.id:
        return render_template('403.html'), 403
    # 1. Mengambil data dari form
    k = request.form.get('klasifikasi', type=int)

    # 2. Validasi input
    if k not in (0, 1, 2):
        flash('Klasifikasi tidak valid.', 'danger')
        # Menggunakan redirect standar Flask
        return redirect(url_for('teacher_choise_course', user_id=user_id))

    # 3. Update data ke database
    current_user.klasifikasi = k
    db.session.commit()
    
    # 4. Menentukan folder template (Gunakan '=' bukan '==')
    pilihan = "low" if k == 0 else "medium" if k == 1 else "high"

    # 5. Render template aktif sesuai klasifikasi
    return render_template(
        f'learning/{pilihan}/bangun_datar/01.html',
        user_id=user_id,
        klasifikasi=k
    )

@app.route("/dashboard/teacher/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def dashboard_teacher(user_id):
    # Cegah akses user lain
    if user_id != current_user.id:
        return render_template("403.html"), 403

    # Ambil jumlah siswa
    amount_student = get_amount_student_by_teacher(user_id)
    amount_class = get_amount_class_by_teacher(user_id)

    return render_template(
        'dashboard/teacher/dashboard.html',
        amount_student=amount_student,
        amount_class=amount_class,
        user_id=user_id
    )
    
@app.route("/teacher/analysis/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def dashboard_analysis(user_id):
    # Cegah akses user lain
    if user_id != current_user.id:
        return render_template("403.html"), 403
    
    get_kelas_pretest = get_kelas_pretest_by_guru(user_id)

    return render_template(
        'dashboard/teacher/analysis.html',
        user_id=user_id,
        list_class=get_kelas_pretest
    )

@app.route("/teacher/result/pretest/analysis/<int:user_id>/<int:class_id>", methods=["GET"])
@login_required
@level_required(1)
def dashboard_result_pretest_analysis(user_id, class_id):
    if user_id != current_user.id or not any(
        assignment.class_id == class_id for assignment in current_user.teacher_classes
    ):
        return render_template("403.html"), 403

    pretest_analysis = get_pretest_analysis(class_id)

    return render_template(
        'dashboard/teacher/result_pretest_analysis.html',
        class_id=class_id,
        user_id=user_id,
        pretest_analysis=pretest_analysis
    )


@app.route('/teacher/result/pretest/analysis/<int:user_id>/<int:class_id>/export.pdf', methods=['GET'])
@login_required
@level_required(1)
def teacher_pretest_analysis_pdf(user_id, class_id):
    if user_id != current_user.id or not any(
        assignment.class_id == class_id for assignment in current_user.teacher_classes
    ):
        return render_template('403.html'), 403

    kelas = Classes.query.get_or_404(class_id)
    rows = (db.session.query(PretestResult, User)
            .join(User, PretestResult.user_id == User.id)
            .filter(User.class_id == class_id, User.level == 0, PretestResult.ai_analysis.isnot(None))
            .order_by(User.full_name.asc()).all())
    students = [
        {
            'name': student.full_name,
            'pretest_score': result.score,
            'correct': result.correct,
            'analysis': json.loads(result.ai_analysis),
            'answers': json.loads(result.answer_details or '[]'),
        }
        for result, student in rows
    ]
    pdf = pretest_analysis_pdf(kelas.name, kelas.school, students)
    return Response(
        pdf,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="edudaya-analisis-pretest-kelas-{class_id}.pdf"'},
    )

@app.route("/teacher/result/pretest/analysis/<int:teacher_id>/student/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def dashboard_teacher_detail_pretest_analysis(teacher_id, user_id):
    if teacher_id != current_user.id:
        return render_template("403.html"), 403

    data = get_student_pretest_analysis_detail(teacher_id, user_id)

    if not data:
        flash("Data analisis AI untuk siswa ini belum tersedia.", "warning")
        return redirect(url_for('dashboard_result_pretest_analysis', user_id=teacher_id, class_id=current_user.teacher_classes[0].class_id))

    return render_template(
        'dashboard/teacher/detail_result_pretest_analysis.html',
        student=data['student'],
        score=data['score'],
        correct=data['correct'],
        total=data['total'],
        time_taken=data['time_taken'],
        answer_details=data['answer_details'],
        ai_analysis=data['ai_analysis'],
        teacher_id=teacher_id,
    )
   
@app.route("/teacher/batch/analyze/pretest/<int:teacher_id>/<int:class_id>", methods=["POST"])
@login_required
@level_required(1)
def dashboard_teacher_batch_analyze_pretest(teacher_id, class_id):
    return batch_analyze_pretest_logic(teacher_id, class_id)

@app.route("/teacher/result/final/analysis/<int:user_id>/<int:class_id>", methods=["GET"])
@login_required
@level_required(1)
def dashboard_result_final_analysis(user_id, class_id):
    if user_id != current_user.id or not any(
        assignment.class_id == class_id for assignment in current_user.teacher_classes
    ):
        return render_template("403.html"), 403

    final_analysis = get_final_analysis(class_id)

    return render_template(
        'dashboard/teacher/result_final_analysis.html',
        class_id=class_id,
        user_id=user_id,
        final_analysis=final_analysis
    )


@app.route('/teacher/result/final/analysis/<int:user_id>/<int:class_id>/export.pdf', methods=['GET'])
@login_required
@level_required(1)
def teacher_final_analysis_pdf(user_id, class_id):
    if user_id != current_user.id or not any(
        assignment.class_id == class_id for assignment in current_user.teacher_classes
    ):
        return render_template('403.html'), 403

    kelas = Classes.query.get_or_404(class_id)
    rows = (db.session.query(FinalResult, User, PretestResult, EvaluationResult)
            .join(User, FinalResult.user_id == User.id)
            .outerjoin(PretestResult, PretestResult.user_id == User.id)
            .outerjoin(EvaluationResult, EvaluationResult.user_id == User.id)
            .filter(User.class_id == class_id, User.level == 0)
            .order_by(User.full_name.asc()).all())
    students = []
    for result, student, pretest, evaluation in rows:
        students.append({
            'name': student.full_name,
            'pretest_score': pretest.score if pretest else None,
            'analysis': json.loads(result.ai_analysis or '{}'),
            'answers': json.loads(evaluation.answer_details or '[]') if evaluation else [],
        })
    pdf = final_analysis_pdf(kelas.name, kelas.school, students)
    return Response(
        pdf,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="edudaya-analisis-akhir-kelas-{class_id}.pdf"'},
    )


@app.route('/teacher/evaluation/export.xlsx/<int:user_id>/<int:class_id>', methods=['GET'])
@login_required
@level_required(1)
def teacher_evaluation_export(user_id, class_id):
    if user_id != current_user.id or not any(
        assignment.class_id == class_id for assignment in current_user.teacher_classes
    ):
        return render_template('403.html'), 403

    sheet_rows = []
    sheet_rows.append(['Siswa', 'Nomor', 'Topik', 'Pertanyaan', 'Jawaban Siswa', 'Kunci Jawaban', 'Tanggal Kirim'])
    results = (
        db.session.query(EvaluationResult, User)
        .join(User, EvaluationResult.user_id == User.id)
        .filter(User.class_id == class_id, User.level == 0)
        .order_by(User.full_name.asc(), EvaluationResult.created_at.asc())
        .all()
    )
    for result, student in results:
        for detail in json.loads(result.answer_details or '[]'):
            sheet_rows.append([
                _excel_safe(student.full_name),
                detail.get('nomor', ''),
                _excel_safe(detail.get('topik')),
                _excel_safe(detail.get('pertanyaan')),
                _excel_safe(detail.get('jawaban_siswa')),
                _excel_safe(detail.get('jawaban_benar')),
                result.created_at.strftime('%Y-%m-%d %H:%M:%S') if result.created_at else '',
            ])
    return _excel_response(sheet_rows, f'edudaya-evaluasi-kelas-{class_id}.xlsx', 'Evaluasi')


@app.route('/teacher/results/export.xlsx/<int:user_id>/<int:class_id>/<kind>', methods=['GET'])
@login_required
@level_required(1)
def teacher_results_export(user_id, class_id, kind):
    if user_id != current_user.id or not any(
        assignment.class_id == class_id for assignment in current_user.teacher_classes
    ):
        return render_template('403.html'), 403
    if kind not in {'pretest', 'quiz', 'final', 'recap'}:
        return 'Not Found', 404

    sheet_rows = []
    if kind == 'recap':
        recap, material_labels, material_keys = get_grades_recap(user_id)
        sheet_rows.append(['Siswa', 'Status Pretest', 'Nilai Pretest', *material_labels, 'Status Evaluasi', 'Nilai Evaluasi', 'Total', 'Rata-rata'])
        for kelas in recap:
            if kelas['class_id'] != class_id:
                continue
            for student in kelas['students']:
                sheet_rows.append([
                    _excel_safe(student['full_name']),
                    'Selesai' if student['pretest_done'] else 'Belum',
                    student['pretest_score'] if student['pretest_score'] is not None else '',
                    *(student['scores'].get(key) if student['scores'].get(key) is not None else '' for key in material_keys),
                    'Selesai' if student['evaluation_done'] else 'Belum',
                    student['evaluation_score'] if student['evaluation_score'] is not None else '',
                    student['total'], student['avg'],
                ])
    elif kind == 'pretest':
        sheet_rows.append(['Siswa', 'Nilai Pretest', 'Nomor', 'Topik', 'Pertanyaan', 'Jawaban Siswa', 'Kunci Jawaban', 'Tanggal Kirim'])
        rows = (db.session.query(PretestResult, User)
                .join(User, PretestResult.user_id == User.id)
                .filter(User.class_id == class_id, User.level == 0)
                .order_by(User.full_name.asc()).all())
        for result, student in rows:
            for detail in json.loads(result.answer_details or '[]'):
                sheet_rows.append([
                    _excel_safe(student.full_name), result.score if result.score is not None else '',
                    detail.get('nomor', ''), _excel_safe(detail.get('topik')),
                    _excel_safe(detail.get('pertanyaan')), _excel_safe(detail.get('jawaban_siswa')),
                    _excel_safe(detail.get('jawaban_benar')),
                    result.created_at.strftime('%Y-%m-%d %H:%M:%S') if result.created_at else '',
                ])
    elif kind == 'quiz':
        sheet_rows.append(['Siswa', 'Materi', 'Benar', 'Salah', 'Nilai', 'Tanggal'])
        rows = (db.session.query(Score, User)
                .join(User, Score.user_id == User.id)
                .filter(User.class_id == class_id, User.level == 0, Score.score_type == 'quiz')
                .order_by(User.full_name.asc(), Score.created_at.asc()).all())
        for score, student in rows:
            sheet_rows.append([
                _excel_safe(student.full_name), _excel_safe(score.chapter), score.correct,
                score.incorrect, score.value,
                score.created_at.strftime('%Y-%m-%d %H:%M:%S') if score.created_at else '',
            ])
    else:
        sheet_rows.append(['Siswa', 'Nilai Pretest', 'Peningkatan Skor', 'Level Akhir', 'Perkembangan', 'Analisis Perkembangan', 'Tanggal Analisis'])
        rows = (db.session.query(FinalResult, User, PretestResult)
                .join(User, FinalResult.user_id == User.id)
                .outerjoin(PretestResult, PretestResult.user_id == User.id)
                .filter(User.class_id == class_id, User.level == 0)
                .order_by(User.full_name.asc()).all())
        for result, student, pretest in rows:
            analysis = json.loads(result.ai_analysis or '{}')
            sheet_rows.append([
                _excel_safe(student.full_name), pretest.score if pretest and pretest.score is not None else '',
                analysis.get('peningkatan_skor', ''),
                _excel_safe((analysis.get('level_akhir') or {}).get('level')),
                _excel_safe(analysis.get('perkembangan')),
                _excel_safe(analysis.get('analisis_perkembangan')),
                result.created_at.strftime('%Y-%m-%d %H:%M:%S') if result.created_at else '',
            ])

    return _excel_response(sheet_rows, f'edudaya-{kind}-kelas-{class_id}.xlsx', kind.title())


@app.route("/teacher/batch/analyze/final/<int:teacher_id>/<int:class_id>", methods=["POST"])
@login_required
@level_required(1)
def dashboard_teacher_batch_analyze_final(teacher_id, class_id):
    return batch_analyze_final_logic(teacher_id, class_id)

@app.route("/teacher/result/final/analysis/<int:teacher_id>/student/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def dashboard_teacher_detail_final_analysis(teacher_id, user_id):
    if teacher_id != current_user.id:
        return render_template("403.html"), 403

    data = get_student_final_analysis_detail(teacher_id, user_id)

    if not data:
        flash("Data analisis AI untuk Final Test siswa ini belum tersedia.", "warning")
        return redirect(url_for('dashboard_result_final_analysis', user_id=teacher_id, class_id=current_user.teacher_classes[0].class_id))

    return render_template(
        'dashboard/teacher/detail_result_final_analysis.html',
        student=data['student'],
        ai_analysis=data['ai_analysis'],
        teacher_id=teacher_id,
    )

@app.route("/teacher/grades/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def teacher_grades(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403

    recap, material_labels, material_keys = get_grades_recap(user_id)

    return render_template(
        'dashboard/teacher/grades.html',
        user_id=user_id,
        recap=recap,
        material_labels=material_labels,
        material_keys=material_keys
    )

@app.route("/teacher/students/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def teacher_students(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403

    students_data = get_students_by_teacher(user_id)

    return render_template(
        'dashboard/teacher/students.html',
        user_id=user_id,
        students_data=students_data
    )


@app.route('/teacher/students/export.xlsx/<int:user_id>', methods=['GET'])
@app.route('/teacher/students/export.xlsx/<int:user_id>/<int:class_id>', methods=['GET'])
@login_required
@level_required(1)
def teacher_students_export(user_id, class_id=None):
    if user_id != current_user.id:
        return render_template('403.html'), 403
    if class_id is not None and not any(
        assignment.class_id == class_id for assignment in current_user.teacher_classes
    ):
        return render_template('403.html'), 403

    sheet_rows = [[
        'Kelas', 'Sekolah', 'No', 'Nama', 'L/P', 'Status Pretest',
        'Nilai Kuis', 'Materi Selesai', 'Total Materi', 'Total Nilai',
    ]]
    for kelas in get_students_by_teacher(user_id):
        if class_id is not None and kelas['class_id'] != class_id:
            continue
        for number, student in enumerate(kelas['students'], 1):
            sheet_rows.append([
                _excel_safe(kelas['class_name']), _excel_safe(kelas['school']), number,
                _excel_safe(student['full_name']), _excel_safe(student['gender']),
                'Selesai' if student['pretest_done'] else 'Belum',
                student['quiz_score'] if student['quiz_score'] is not None else '',
                student['materi_selesai'], student['total_bab'], student['total_score'],
            ])

    suffix = f'kelas-{class_id}' if class_id is not None else 'semua-kelas'
    return _excel_response(sheet_rows, f'edudaya-data-siswa-{suffix}.xlsx', 'Data Siswa')

@app.route("/teacher/classes/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def my_classes(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403

    my_classes_list = get_my_classes(user_id)

    return render_template(
        'dashboard/teacher/my_classes.html',
        user_id=user_id,
        my_classes=my_classes_list
    )

@app.route("/teacher/classes/create/<int:teacher_id>", methods=["POST"])
@login_required
@level_required(1)
def create_class_route(teacher_id):
    return create_class(teacher_id)

@app.route("/teacher/classes/edit/<int:teacher_id>/<int:class_id>", methods=["POST"])
@login_required
@level_required(1)
def edit_class_route(teacher_id, class_id):
    return edit_class(teacher_id, class_id)

@app.route("/profile/teacher/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def teacher_profile_route(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403
    user = teacher_profile(user_id)
    return render_template(
        'dashboard/teacher/teacher_profile.html',
        user=user,
        user_id=user_id
    )

@app.route("/profile/teacher/update/<int:user_id>", methods=["POST"])
@login_required
@level_required(1)
def update_teacher_profile_route(user_id):
    return update_teacher_profile(user_id)

# End Dashboard Guru ===========================================================================


# Halaman Khusus Dashboard Guru ==================================================================

@app.route("/admin/choise/course/<int:user_id>", methods=["GET"])
@login_required
@level_required(2)
def admin_choise_course(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403

    return render_template("admin_choise_course.html", user_id=user_id)

@app.route('/admin/klasifikasi/<int:user_id>', methods=['POST'])
@login_required
@level_required(2)
def admin_update_klasifikasi(user_id):
    if user_id != current_user.id:
        return render_template('403.html'), 403
    # 1. Mengambil data dari form
    k = request.form.get('klasifikasi', type=int)

    # 2. Validasi input
    if k not in (0, 1, 2):
        flash('Klasifikasi tidak valid.', 'danger')
        # Menggunakan redirect standar Flask
        return redirect(url_for('admin_choise_course', user_id=user_id))

    # 3. Update data ke database
    current_user.klasifikasi = k
    db.session.commit()
    
    # 4. Menentukan folder template (Gunakan '=' bukan '==')
    pilihan = "low" if k == 0 else "medium" if k == 1 else "high"

    # 5. Render template aktif sesuai klasifikasi
    return render_template(
        f'learning/{pilihan}/bangun_datar/01.html',
        user_id=user_id,
        klasifikasi=k
    )

@app.route("/dashboard/admin/<int:user_id>", methods=["GET"])
@login_required
@level_required(2)
def dashboard_admin(user_id):
    # Cegah akses user lain
    if user_id != current_user.id:
        return render_template("403.html"), 403

    dashboard_stats = get_admin_dashboard_stats()
    admin_scores = get_admin_scores()

    return render_template(
        'dashboard/admin/dashboard.html',
        amount_student=dashboard_stats['total_students'],
        amount_teacher=dashboard_stats['total_teachers'],
        amount_classes=dashboard_stats['total_classes'],
        active_tokens=dashboard_stats['active_tokens'],
        top_students=dashboard_stats['top_students'],
        admin_scores=admin_scores,
    )


@app.route('/admin/scores/export.xlsx', methods=['GET'])
@login_required
@level_required(2)
def admin_scores_export():
    sheet_rows = []
    sheet_rows.append(['Siswa', 'Username', 'Kelas', 'Sekolah', 'Materi', 'Jenis', 'Benar', 'Salah', 'Nilai', 'Tanggal'])
    for score, student, kelas in get_admin_scores():
        sheet_rows.append([
            _excel_safe(student.full_name),
            _excel_safe(student.username),
            _excel_safe(kelas.name if kelas else ''),
            _excel_safe(kelas.school if kelas else ''),
            _excel_safe(score.chapter or ''),
            _excel_safe(score.score_type),
            score.correct,
            score.incorrect,
            score.value,
            score.created_at.strftime('%Y-%m-%d %H:%M:%S') if score.created_at else '',
        ])

    return _excel_response(sheet_rows, 'edudaya-nilai-siswa.xlsx', 'Nilai Siswa')


def _excel_response(rows, filename, sheet_name):
    return Response(
        workbook_bytes(rows, sheet_name),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


def _excel_safe(value):
    value = '' if value is None else str(value)
    formula_candidate = value.lstrip(' \t\r\n')
    return "'" + value if formula_candidate.startswith(('=', '+', '-', '@')) else value


@app.route('/admin/profile/update/<int:user_id>', methods=['POST'])
@login_required
@level_required(2)
def admin_profile_update(user_id):
    if user_id != current_user.id:
        return render_template('403.html'), 403

    full_name = request.form.get('full_name', '')
    username = request.form.get('username', '')
    password = request.form.get('password') or None
    password_confirm = request.form.get('password_confirm')
    success, message = update_admin_profile(user_id, full_name, username, password, password_confirm)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('dashboard_admin', user_id=user_id) + '#admin-profile')

# Admin CRUD Kelas =============================================================================

@app.route("/admin/kelas", methods=["GET"])
@login_required
@level_required(2)
def admin_kelas_index():
    classes = get_all_classes()
    return render_template("dashboard/admin/kelas/index.html", classes=classes)

@app.route("/admin/kelas/create", methods=["GET"])
@login_required
@level_required(2)
def admin_kelas_create():
    teachers = get_all_teachers()
    return render_template("dashboard/admin/kelas/create.html", teachers=teachers)

@app.route("/admin/kelas/create", methods=["POST"])
@login_required
@level_required(2)
def admin_kelas_create_post():
    name = request.form.get("name")
    school = request.form.get("school")
    kkm = request.form.get("kkm", type=int)
    teacher_ids = request.form.getlist("teacher_ids")
    teacher_ids = [int(tid) for tid in teacher_ids if tid]
    if not name or not school:
        flash("Nama kelas dan sekolah wajib diisi.", "danger")
        return redirect(url_for("admin_kelas_create"))
    create_kelas(name, school, kkm or 75, teacher_ids=teacher_ids)
    flash("Kelas berhasil ditambahkan.", "success")
    return redirect(url_for("admin_kelas_index"))

@app.route("/admin/kelas/<int:kelas_id>/edit", methods=["GET"])
@login_required
@level_required(2)
def admin_kelas_edit(kelas_id):
    kelas = get_kelas_by_id(kelas_id)
    teachers = get_all_teachers()
    return render_template("dashboard/admin/kelas/edit.html", kelas=kelas, teachers=teachers)

@app.route("/admin/kelas/<int:kelas_id>/edit", methods=["POST"])
@login_required
@level_required(2)
def admin_kelas_edit_post(kelas_id):
    name = request.form.get("name")
    school = request.form.get("school")
    kkm = request.form.get("kkm", type=int)
    teacher_ids = request.form.getlist("teacher_ids")
    teacher_ids = [int(tid) for tid in teacher_ids if tid]
    if not name or not school:
        flash("Nama kelas dan sekolah wajib diisi.", "danger")
        return redirect(url_for("admin_kelas_edit", kelas_id=kelas_id))
    update_kelas(kelas_id, name, school, kkm or 75, teacher_ids=teacher_ids)
    flash("Kelas berhasil diperbarui.", "success")
    return redirect(url_for("admin_kelas_index"))

@app.route("/admin/kelas/<int:kelas_id>/delete", methods=["POST"])
@login_required
@level_required(2)
def admin_kelas_delete(kelas_id):
    delete_kelas(kelas_id)
    flash("Kelas berhasil dihapus.", "success")
    return redirect(url_for("admin_kelas_index"))

# Admin CRUD Guru ===============================================================================

@app.route("/admin/guru", methods=["GET"])
@login_required
@level_required(2)
def admin_guru_index():
    teachers = get_all_teachers()
    return render_template("dashboard/admin/guru/index.html", teachers=teachers)

@app.route("/admin/guru/create", methods=["GET"])
@login_required
@level_required(2)
def admin_guru_create():
    return render_template("dashboard/admin/guru/create.html")

@app.route("/admin/guru/create", methods=["POST"])
@login_required
@level_required(2)
def admin_guru_create_post():
    username = request.form.get("username")
    full_name = request.form.get("full_name")
    password = request.form.get("password")
    gender = request.form.get("gender")
    if not username or not full_name or not password:
        flash("Username, nama, dan password wajib diisi.", "danger")
        return redirect(url_for("admin_guru_create"))
    result = create_teacher(username, full_name, password, gender)
    if result is None:
        flash("Username sudah digunakan.", "danger")
        return redirect(url_for("admin_guru_create"))
    flash("Guru berhasil ditambahkan.", "success")
    return redirect(url_for("admin_guru_index"))

@app.route("/admin/guru/<int:teacher_id>/edit", methods=["GET"])
@login_required
@level_required(2)
def admin_guru_edit(teacher_id):
    teacher = get_teacher_by_id(teacher_id)
    return render_template("dashboard/admin/guru/edit.html", teacher=teacher)

@app.route("/admin/guru/<int:teacher_id>/edit", methods=["POST"])
@login_required
@level_required(2)
def admin_guru_edit_post(teacher_id):
    username = request.form.get("username")
    full_name = request.form.get("full_name")
    gender = request.form.get("gender")
    password = request.form.get("password") or None
    if not username or not full_name:
        flash("Username dan nama wajib diisi.", "danger")
        return redirect(url_for("admin_guru_edit", teacher_id=teacher_id))
    result = update_teacher(teacher_id, username, full_name, gender, password)
    if result is None:
        flash("Username sudah digunakan.", "danger")
        return redirect(url_for("admin_guru_edit", teacher_id=teacher_id))
    flash("Guru berhasil diperbarui.", "success")
    return redirect(url_for("admin_guru_index"))

@app.route("/admin/guru/<int:teacher_id>/delete", methods=["POST"])
@login_required
@level_required(2)
def admin_guru_delete(teacher_id):
    delete_teacher(teacher_id)
    flash("Guru berhasil dihapus.", "success")
    return redirect(url_for("admin_guru_index"))

# Admin CRUD Siswa =============================================================================

@app.route("/admin/siswa", methods=["GET"])
@login_required
@level_required(2)
def admin_siswa_index():
    siswa = get_all_siswa()
    return render_template("dashboard/admin/siswa/index.html", siswa=siswa)

@app.route("/admin/siswa/create", methods=["GET"])
@login_required
@level_required(2)
def admin_siswa_create():
    classes = get_all_classes()
    return render_template("dashboard/admin/siswa/create.html", classes=classes)

@app.route("/admin/siswa/create", methods=["POST"])
@login_required
@level_required(2)
def admin_siswa_create_post():
    username = request.form.get("username")
    full_name = request.form.get("full_name")
    password = request.form.get("password")
    gender = request.form.get("gender")
    class_id = request.form.get("class_id", type=int)
    if not username or not full_name or not password:
        flash("Username, nama, dan password wajib diisi.", "danger")
        return redirect(url_for("admin_siswa_create"))
    result = create_siswa(username, full_name, password, gender, class_id)
    if result is None:
        flash("Username sudah digunakan.", "danger")
        return redirect(url_for("admin_siswa_create"))
    flash("Siswa berhasil ditambahkan.", "success")
    return redirect(url_for("admin_siswa_index"))

@app.route("/admin/siswa/<int:siswa_id>/edit", methods=["GET"])
@login_required
@level_required(2)
def admin_siswa_edit(siswa_id):
    siswa = get_siswa_by_id(siswa_id)
    classes = get_all_classes()
    return render_template("dashboard/admin/siswa/edit.html", siswa=siswa, classes=classes)

@app.route("/admin/siswa/<int:siswa_id>/edit", methods=["POST"])
@login_required
@level_required(2)
def admin_siswa_edit_post(siswa_id):
    username = request.form.get("username")
    full_name = request.form.get("full_name")
    gender = request.form.get("gender")
    class_id = request.form.get("class_id", type=int)
    password = request.form.get("password") or None
    if not username or not full_name:
        flash("Username dan nama wajib diisi.", "danger")
        return redirect(url_for("admin_siswa_edit", siswa_id=siswa_id))
    result = update_siswa(siswa_id, username, full_name, gender, class_id, password)
    if result is None:
        flash("Username sudah digunakan.", "danger")
        return redirect(url_for("admin_siswa_edit", siswa_id=siswa_id))
    flash("Siswa berhasil diperbarui.", "success")
    return redirect(url_for("admin_siswa_index"))

@app.route("/admin/siswa/<int:siswa_id>/delete", methods=["POST"])
@login_required
@level_required(2)
def admin_siswa_delete(siswa_id):
    delete_siswa(siswa_id)
    flash("Siswa berhasil dihapus.", "success")
    return redirect(url_for("admin_siswa_index"))

# Admin CRUD Token =============================================================================

@app.route("/admin/token", methods=["GET"])
@login_required
@level_required(2)
def admin_token_index():
    tokens = get_all_tokens()
    return render_template("dashboard/admin/token/index.html", tokens=tokens)

@app.route("/admin/token/<int:kelas_id>/regenerate", methods=["POST"])
@login_required
@level_required(2)
def admin_token_regenerate(kelas_id):
    token = regenerate_token(kelas_id)
    flash(f"Token berhasil diperbarui: {token}", "success")
    return redirect(url_for("admin_token_index"))

@app.route("/admin/token/<int:kelas_id>/activate", methods=["POST"])
@login_required
@level_required(2)
def admin_token_activate(kelas_id):
    activate_token(kelas_id)
    flash("Token diaktifkan.", "success")
    return redirect(url_for("admin_token_index"))

@app.route("/admin/token/<int:kelas_id>/deactivate", methods=["POST"])
@login_required
@level_required(2)
def admin_token_deactivate(kelas_id):
    deactivate_token(kelas_id)
    flash("Token dinonaktifkan.", "success")
    return redirect(url_for("admin_token_index"))

# End Admin CRUD ===============================================================================
