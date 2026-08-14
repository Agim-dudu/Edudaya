from app import app
from app.controller import *
from app.decorator.utils import level_required
from flask_login import current_user, login_required
from app.model import Classes
from app.controller.PretestController import QUESTIONS_PRETEST
from flask import Flask, render_template, request, redirect, url_for


@app.route("/")
def index():
    
    amount_classes=get_amount_classes()
    amount_teacher=get_amount_teacher()
    amount_student=get_amount_student()
    
    return render_template("index.html", ac=amount_classes, at=amount_teacher, ast=amount_student)

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
        return render_template("403.html")
    
    return render_template("pretest/preparation.html", user_id=user_id)

@app.route("/pretest/start/<int:user_id>", methods=["GET"])
@login_required
def pretest_start(user_id):
    if user_id != current_user.id:
        return render_template("403.html")
    
    safe_questions = [
        {k: v for k, v in q.items() if k != "correct"}
        for q in QUESTIONS_PRETEST
    ]
    return render_template("pretest/pretest_start.html", questions=safe_questions, user_id=user_id)

@app.route("/pretest/submit/<int:user_id>", methods=["POST"])
@login_required
def submit_pretest(user_id):
    if user_id != current_user.id:
        return render_template("403.html")

    data = request.get_json()

    return save_pretest(data, user_id)

@app.route("/api/pretest/analyze/<int:user_id>", methods=["POST"])
@login_required
def api_analyze_pretest(user_id):
    if user_id != current_user.id:
        return render_template("403.html")

    data = request.get_json()

    return analyze_pretest(data)

@app.route("/pretest/finish/<int:user_id>", methods=["GET"])
@login_required
def finish_pretest(user_id):
    if user_id != current_user.id:
        return render_template("403.html")

    # Jika akses diizinkan, render halaman ini
    return render_template("pretest/finish_pretest.html", user_id=user_id)


# Halaman menunggu analisis AI oleh guru ===========================================================
@app.route("/pretest/waiting/<int:user_id>", methods=["GET"])
@login_required
def waiting_analysis(user_id):
    if user_id != current_user.id:
        return render_template("403.html")
    return render_template("pretest/waiting_analysis.html", user_id=user_id)

# End Pretest Handle ===============================================================================

@app.route("/waiting/pretest/<int:user_id>", methods=["GET"])
@login_required
def waiting_pretest(user_id):
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
        return render_template("403.html")

    data = request.get_json()
    print(data)

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
        pr = current_user.pretest_result
        blocked_prefixes = ('/learning/', '/quiz/', '/evaluation/', '/api/learning/', '/api/bab')
        if path.startswith(blocked_prefixes):
            if pr is None or pr.ai_analysis is None:
                from flask import flash
                if pr is None:
                    flash("Kamu harus menyelesaikan Pretest terlebih dahulu.", "warning")
                    return redirect(url_for('pretest', user_id=current_user.id))
                flash("Selesaikan Pretest atau tunggu analisis guru terlebih dahulu.", "warning")
                return redirect(url_for('dashboard_student', user_id=current_user.id))

# Routing Learning Bab 1 ====================================================================================

@app.route("/learning/bab1/chapter1/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bab1_chapter1(user_id, klasifikasi):
    return can_access_bab1_chapter1(user_id, klasifikasi)

@app.route('/api/learning/bab1/chapter1/<int:user_id>', methods=['POST'])
@login_required
def submit_activity_learning_bab1_chapter1(user_id):
    return bab1_chapter1_activity(user_id)

@app.route("/learning/bab1/chapter2/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bab1_chapter2(user_id, klasifikasi):
    return can_access_bab1_chapter2(user_id, klasifikasi)

@app.route('/api/learning/bab1/chapter2/<int:user_id>', methods=['POST'])
@login_required
def submit_activity_learning_bab1_chapter2(user_id):
    return bab1_chapter2_activity(user_id)

@app.route("/learning/bab1/summary/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bab1_summary(user_id, klasifikasi):
    return can_access_bab1_summary(user_id, klasifikasi)

@app.route("/learning/bab1/quiz/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bab1_quiz(user_id, klasifikasi):
    return can_access_bab1_quiz(user_id, klasifikasi)

@app.route("/quiz/bab1/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def quiz_start_bab1(user_id, klasifikasi):
    return can_access_bab1_quiz_start(user_id, klasifikasi)

@app.route('/api/bab1/quiz/<int:user_id>', methods=['POST'])
def api_bab1_quiz_submit(user_id):
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()

    # Jawaban dikirim dari frontend sebagai { 1: "soal1-c", 2: "soal2-b", ... }
    # Key bisa berupa int (JSON number) atau string — normalkan ke string semua
    jawaban_user_raw = data.get('jawaban', {})
    jawaban_user = {str(k): v for k, v in jawaban_user_raw.items()}

    kunci = {
        "1":  "soal1-c",
        "2":  "soal2-b",
        "3":  "soal3-c",
        "4":  "soal4-b",
        "5":  "soal5-a",
        "6":  "soal6-b",
        "7":  "soal7-c",
        "8":  "soal8-a",
        "9":  "soal9-c",
        "10": "soal10-b"
    }

    total_soal  = len(kunci)
    total_benar = sum(1 for k, v in kunci.items() if jawaban_user.get(k) == v)
    total_salah = total_soal - total_benar
    score       = round((total_benar / total_soal) * 100)

    session.pop('quiz_start_time', None)

    # Cek apakah sudah ada score sebelumnya
    existing_score = Score.query.filter_by(
        user_id=user_id,
        score_type='quiz',
        chapter='Bab 1'
    ).first()

    if existing_score:
        existing_score.correct   = total_benar
        existing_score.incorrect = total_salah
        existing_score.value     = score
    else:
        db.session.add(Score(
            user_id=user_id,
            class_id=current_user.class_id,
            score_type='quiz',
            chapter='Bab 1',
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
        'next_url':      url_for('learning_bab1_quiz', user_id=user_id, klasifikasi=current_user.klasifikasi),
        'jawaban_benar': kunci
    })
# End Routing Learning Bab 1 ====================================================================================

# Routing Learning Bab 2 ====================================================================================

@app.route("/learning/bab2/chapter1/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bab2_chapter1(user_id, klasifikasi):
    return can_access_bab2_chapter1(user_id, klasifikasi)

@app.route('/api/learning/bab2/chapter1/<int:user_id>', methods=['POST'])
@login_required
def submit_activity_learning_bab2_chapter1(user_id):
    return bab2_chapter1_activity(user_id)

@app.route("/learning/bab2/chapter2/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bab2_chapter2(user_id, klasifikasi):
    return can_access_bab2_chapter2(user_id, klasifikasi)

@app.route('/api/learning/bab2/chapter2/<int:user_id>', methods=['POST'])
@login_required
def submit_activity_learning_bab2_chapter2(user_id):
    return bab2_chapter2_activity(user_id)

@app.route("/learning/bab2/summary/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bab2_summary(user_id, klasifikasi):
    return can_access_bab2_summary(user_id, klasifikasi)

@app.route("/learning/bab2/quiz/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def learning_bab2_quiz(user_id, klasifikasi):
    return can_access_bab2_quiz(user_id, klasifikasi)

@app.route("/quiz/bab2/<int:user_id>/<int:klasifikasi>", methods=["GET"])
@login_required
def quiz_start_bab2(user_id, klasifikasi):
    return can_access_bab2_quiz_start(user_id, klasifikasi)

@app.route('/api/bab2/quiz/<int:user_id>', methods=['POST'])
def api_bab2_quiz_submit(user_id):
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()

    # Jawaban dikirim dari frontend sebagai { 1: "soal1-c", 2: "soal2-b", ... }
    # Key bisa berupa int (JSON number) atau string — normalkan ke string semua
    jawaban_user_raw = data.get('jawaban', {})
    jawaban_user = {str(k): v for k, v in jawaban_user_raw.items()}

    kunci = {
        "1":  "soal1-c",
        "2":  "soal2-b",
        "3":  "soal3-c",
        "4":  "soal4-b",
        "5":  "soal5-a",
        "6":  "soal6-b",
        "7":  "soal7-c",
        "8":  "soal8-a",
        "9":  "soal9-c",
        "10": "soal10-b"
    }

    total_soal  = len(kunci)
    total_benar = sum(1 for k, v in kunci.items() if jawaban_user.get(k) == v)
    total_salah = total_soal - total_benar
    score       = round((total_benar / total_soal) * 100)

    session.pop('quiz_start_time', None)

    # Cek apakah sudah ada score sebelumnya
    existing_score = Score.query.filter_by(
        user_id=user_id,
        score_type='quiz',
        chapter='Bab 2'
    ).first()

    if existing_score:
        existing_score.correct   = total_benar
        existing_score.incorrect = total_salah
        existing_score.value     = score
    else:
        db.session.add(Score(
            user_id=user_id,
            class_id=current_user.class_id,
            score_type='quiz',
            chapter='Bab 2',
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
        'next_url':      url_for('learning_bab2_quiz', user_id=user_id, klasifikasi=current_user.klasifikasi),
        'jawaban_benar': kunci
    })

# End Routing Learning Bab 2 ====================================================================================

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
    print(data)

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
    
    return redirect(request.referrer)

# End Dashboard Students =========================================================================


# Halaman Khusus Dashboard Guru ==================================================================

@app.route("/teacher/choise/course/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def teacher_choise_course(user_id):
    if user_id != current_user.id:
        return render_template("403.html")

    return render_template("teacher_choise_course.html", user_id=user_id)

@app.route('/teacher/klasifikasi/<int:user_id>', methods=['POST'])
@login_required
@level_required(1)
def teacher_update_klasifikasi(user_id):
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
    if k == 0:
        pilihan = "low"
    elif k == 1:
        pilihan = "medium"
    else:
        pilihan = "high"

    # 5. Render template sesuai pilihan
    return render_template(
        f'learning/{pilihan}/bab1/01.html',
        user_id=user_id
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
    
    pretest_analysis = get_pretest_analysis(class_id)

    return render_template(
        'dashboard/teacher/result_pretest_analysis.html',
        class_id=class_id,
        user_id=user_id,
        pretest_analysis=pretest_analysis
    )

@app.route("/teacher/result/pretest/analysis/<int:teacher_id>/student/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def dashboard_teacher_detail_pretest_analysis(teacher_id, user_id):
    if teacher_id != current_user.id:
        return render_template("403.html"), 403

    data = get_student_pretest_analysis_detail(teacher_id, user_id)

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
    
    final_analysis = get_final_analysis(class_id)

    return render_template(
        'dashboard/teacher/result_final_analysis.html',
        class_id=class_id,
        user_id=user_id,
        final_analysis=final_analysis
    )
    
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
        return redirect(url_for('dashboard_result_pretest_analysis', user_id=teacher_id, class_id=current_user.teacher_classes[0].class_id))

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
        return render_template("403.html")

    return render_template("admin_choise_course.html", user_id=user_id)

@app.route('/admin/klasifikasi/<int:user_id>', methods=['POST'])
@login_required
@level_required(2)
def admin_update_klasifikasi(user_id):
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
    if k == 0:
        pilihan = "low"
    elif k == 1:
        pilihan = "medium"
    else:
        pilihan = "high"

    # 5. Render template sesuai pilihan
    return render_template(
        f'learning/{pilihan}/bab1/01.html',
        user_id=user_id
    )

@app.route("/dashboard/admin/<int:user_id>", methods=["GET"])
@login_required
@level_required(2)
def dashboard_admin(user_id):
    # Cegah akses user lain
    if user_id != current_user.id:
        return render_template("403.html"), 403

    # Ambil jumlah siswa
    amount_student = get_amount_student_all()
    amount_teacher = get_amount_teacher_all()
    amount_classes = get_amount_classes_all()
    
    print(amount_classes)

    return render_template(
        'dashboard/admin/dashboard.html',
        amount_student=amount_student,
        amount_teacher=amount_teacher,
        amount_classes=amount_classes
    )

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
