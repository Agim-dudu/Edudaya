from app import db
from app.model import ActivityLog, Score, Classes
from flask_login import current_user
from datetime import datetime, timezone
from app.controller.EvaluationController import QUESTIONS_EVALUATION
from flask import abort, jsonify, render_template, redirect, url_for, flash, session

# ---------------------------------------------------------------------------
# Learning routes retained by the active curriculum.
BAB_CONFIG = {
    "bangun_datar": {
        "label": "Bangun Datar",
        "quiz_route": "quiz_bangun_datar",
        "prerequisite_quiz": None,
    },
    "evaluation": {
        "label": "Evaluation",
        "flow": [{"activity_key": "evaluation", "route": "learning_evaluation"}],
        "dir": "evaluation",
        "prerequisite_quiz": "Bangun Datar",
    },
}

FOLDERS = ["low", "medium", "high"]
QUIZ_COOLDOWN_SECONDS = 180
QUIZ_DURATION_SECONDS = 900
EVALUATION_DURATION_SECONDS = 20 * 60
DEFAULT_KKM = 75

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _folder(klasifikasi: int) -> str:
    return FOLDERS[klasifikasi] if 0 <= klasifikasi < len(FOLDERS) else "high"

def _guard(user_id: int):
    if user_id != current_user.id:
        return render_template("403.html")
    return None

def has_activity(user_id: int, activity_key: str) -> bool:
    return ActivityLog.query.filter_by(
        user_id=user_id,
        activity_key=activity_key,
    ).first() is not None

def get_first_incomplete_route(user_id: int, klasifikasi: int, flow: list):
    for step in flow:
        if not has_activity(user_id, step["activity_key"]):
            return redirect(url_for(step["route"], user_id=user_id, klasifikasi=klasifikasi))
    return None

def _log_activity(user_id: int, activity_key: str, progress_value: int = 0):
    if not has_activity(user_id, activity_key):
        db.session.add(ActivityLog(user_id=user_id, activity_key=activity_key))
        if current_user.progress < progress_value:
            current_user.progress = progress_value
        db.session.commit()

def _get_kkm(user) -> int:
    user_class = Classes.query.get(user.class_id)
    return user_class.kkm if user_class else DEFAULT_KKM


def _guard_prerequisite_quiz(user_id: int, klasifikasi: int, bab_key: str):
    prereq_label = BAB_CONFIG[bab_key].get("prerequisite_quiz")
    if not prereq_label or current_user.level != 0:
        return None

    kkm = _get_kkm(current_user)

    best_score = Score.query.filter_by(
        user_id=user_id,
        score_type="quiz",
        chapter=prereq_label,
    ).order_by(Score.value.desc()).first()

    if not best_score or best_score.value < kkm:
        achieved = best_score.value if best_score else 0
        flash(
            f"Kamu harus mencapai nilai KKM ({kkm}) pada Quiz {prereq_label} "
            f"sebelum mengakses materi ini. Nilai tertinggimu: {achieved}.",
            "warning",
        )
        prereq_config = next((v for v in BAB_CONFIG.values() if v["label"] == prereq_label), None)
        prereq_key = next(k for k, v in BAB_CONFIG.items() if v["label"] == prereq_label)
        return redirect(url_for(
            prereq_config.get("quiz_route", f"learning_{prereq_key}_quiz"),
            user_id=user_id,
            klasifikasi=klasifikasi,
        ))

    return None

def _get_last_score(user_id: int, score_type: str, chapter: str):
    """Ambil score terbaru berdasarkan created_at DESC — single source of truth."""
    return Score.query.filter_by(
        user_id=user_id,
        score_type=score_type,
        chapter=chapter,
    ).order_by(Score.created_at.desc()).first()

def _compute_cooldown(last_score) -> int:
    """Hitung sisa cooldown dalam detik. Negatif berarti sudah boleh retry."""
    if not last_score or last_score.created_at is None:
        return -1
    delta = (datetime.utcnow() - last_score.created_at).total_seconds()
    return int(QUIZ_COOLDOWN_SECONDS - delta)

# ---------------------------------------------------------------------------
# Active assessment access functions

def can_access_evaluation(user_id: int, klasifikasi: int):
    guard = _guard(user_id)
    if guard:
        return guard

    block = _guard_prerequisite_quiz(user_id, klasifikasi, "evaluation")
    if block:
        return block

    folder = _folder(klasifikasi)

    if current_user.level == 0:
        _log_activity(user_id, "evaluation")

        quiz_history = Score.query.filter_by(
            user_id=user_id,
            score_type="evaluation",
            chapter="evaluation",
        ).order_by(Score.created_at.desc()).all()
        print(quiz_history)
        return render_template(
            f"learning/{folder}/evaluation/evaluation.html",
            user_id=user_id,
            quiz_history=quiz_history,
            user_kkm=_get_kkm(current_user),
        )

    return render_template(f"learning/{folder}/evaluation/evaluation.html", user_id=user_id)

def can_access_evaluation_start(user_id: int, klasifikasi: int, bab_key: str):
    guard = _guard(user_id)
    if guard:
        return guard

    safe_questions = [
        {k: v for k, v in q.items() if k != "correct"}
        for q in QUESTIONS_EVALUATION
    ]
    
    cfg        = BAB_CONFIG[bab_key]
    folder     = _folder(klasifikasi)
    quiz_route = f"learning_{bab_key}"

    block = _guard_prerequisite_quiz(user_id, klasifikasi, bab_key)
    if block:
        return block

    if current_user.level == 0:
        block = get_first_incomplete_route(user_id, klasifikasi, cfg["flow"][:-1])
        if block:
            return block

        if not has_activity(user_id, f"{bab_key}"):
            return redirect(url_for(quiz_route, user_id=user_id, klasifikasi=klasifikasi))

        last_score = _get_last_score(user_id, "evaluation", cfg["label"])

        # --- DEBUG (hapus setelah confirmed fix) ---
        print(f"[DEBUG] bab_key={bab_key} chapter={cfg['label']}")
        print(f"[DEBUG] last_score={last_score}")
        if last_score:
            print(f"[DEBUG] value={last_score.value} created_at={last_score.created_at}")
            print(f"[DEBUG] utcnow={datetime.utcnow()}")
            print(f"[DEBUG] sisa_cooldown={_compute_cooldown(last_score)}")
        # -------------------------------------------

        if last_score:
            kkm = _get_kkm(current_user)

            if last_score.value >= kkm:
                flash(
                    f"Kamu sudah mencapai nilai KKM ({kkm}). "
                    f"Tidak perlu mengulang quiz ini lagi! 🎉",
                    "success",
                )
                return redirect(url_for(quiz_route, user_id=user_id, klasifikasi=klasifikasi))

            sisa_cooldown = _compute_cooldown(last_score)
            if sisa_cooldown > 0:
                flash(
                    f"Kamu baru saja mengerjakan quiz. "
                    f"Tunggu {sisa_cooldown // 60} menit {sisa_cooldown % 60} detik lagi.",
                    "warning",
                )
                return redirect(url_for(quiz_route, user_id=user_id, klasifikasi=klasifikasi))

        session_key = f"quiz_start_time_{bab_key}"
        if session_key not in session:
            session[session_key] = datetime.utcnow().isoformat()

        sisa_detik = EVALUATION_DURATION_SECONDS - int(
            (datetime.utcnow() - datetime.fromisoformat(session[session_key])).total_seconds()
        )
        if sisa_detik <= 0:
            session.pop(session_key, None)
            flash("Waktu pengerjaan quiz telah habis.", "warning")
            return redirect(url_for(quiz_route, user_id=user_id, klasifikasi=klasifikasi))

        return render_template(
            f"learning/{folder}/{cfg['dir']}/evaluation_start.html",
            questions=safe_questions,
            user_id=user_id,
            sisa_detik=sisa_detik,
        )

    return render_template(f"learning/{folder}/{cfg['dir']}/evaluation_start.html", user_id=user_id, questions=safe_questions)
# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

# Evaluation
def can_access_learning_evaluation(user_id, klasifikasi):
    return can_access_evaluation(user_id, klasifikasi)

def can_access_learning_evaluation_start(user_id, klasifikasi):
    return can_access_evaluation_start(user_id, klasifikasi, "evaluation")

# Bangun Datar (Low)
def can_access_bangun_datar(user_id, klasifikasi):
    guard = _guard(user_id)
    if guard:
        return guard
    folder = _folder(klasifikasi)
    return render_template(
        f"learning/{folder}/bangun_datar/01.html",
        user_id=user_id,
        klasifikasi=klasifikasi,
    )



def can_access_bangun_datar_1d(user_id, klasifikasi):
    guard = _guard(user_id)
    if guard:
        return guard
    if klasifikasi not in (0, 1):
        abort(404)
    folder = _folder(klasifikasi)
    return render_template(f"learning/{folder}/bangun_datar/01_d.html", user_id=user_id, klasifikasi=klasifikasi)


def can_access_bangun_datar_2(user_id, klasifikasi):
    guard = _guard(user_id)
    if guard:
        return guard
    folder = _folder(klasifikasi)
    return render_template(
        f"learning/{folder}/bangun_datar/02.html",
        user_id=user_id,
        klasifikasi=klasifikasi,
    )

def can_access_bangun_datar_3(user_id, klasifikasi):
    guard = _guard(user_id)
    if guard:
        return guard
    folder = _folder(klasifikasi)
    return render_template(
        f"learning/{folder}/bangun_datar/03.html",
        user_id=user_id,
        klasifikasi=klasifikasi,
    )

def can_access_bangun_datar_4(user_id, klasifikasi):
    guard = _guard(user_id)
    if guard:
        return guard
    if klasifikasi not in (0, 1):
        abort(404)
    folder = _folder(klasifikasi)
    return render_template(
        f"learning/{folder}/bangun_datar/04.html",
        user_id=user_id,
        klasifikasi=klasifikasi,
    )

def can_access_bangun_datar_5(user_id, klasifikasi):
    guard = _guard(user_id)
    if guard:
        return guard
    if klasifikasi not in (0, 1):
        abort(404)
    folder = _folder(klasifikasi)
    return render_template(
        f"learning/{folder}/bangun_datar/05.html",
        user_id=user_id,
        klasifikasi=klasifikasi,
    )

def can_access_bangun_datar_6(user_id, klasifikasi):
    guard = _guard(user_id)
    if guard:
        return guard
    if klasifikasi not in (0, 1):
        abort(404)
    folder = _folder(klasifikasi)
    return render_template(
        f"learning/{folder}/bangun_datar/06.html",
        user_id=user_id,
        klasifikasi=klasifikasi,
    )
    


def can_access_bangun_datar_5_2(user_id, klasifikasi):
    guard = _guard(user_id)
    if guard:
        return guard
    if klasifikasi not in (0, 1):
        abort(404)
    folder = _folder(klasifikasi)
    return render_template(f"learning/{folder}/bangun_datar/05_2.html", user_id=user_id, klasifikasi=klasifikasi)


def can_access_bangun_datar_5_3(user_id, klasifikasi):
    guard = _guard(user_id)
    if guard:
        return guard
    if klasifikasi not in (0, 1):
        abort(404)
    folder = _folder(klasifikasi)
    return render_template(f"learning/{folder}/bangun_datar/05_3.html", user_id=user_id, klasifikasi=klasifikasi)


def can_access_bangun_datar_6_2(user_id, klasifikasi):
    guard = _guard(user_id)
    if guard:
        return guard
    if klasifikasi not in (0, 1):
        abort(404)
    folder = _folder(klasifikasi)
    return render_template(f"learning/{folder}/bangun_datar/06_2.html", user_id=user_id, klasifikasi=klasifikasi)


def can_access_bangun_datar_6_3(user_id, klasifikasi):
    guard = _guard(user_id)
    if guard:
        return guard
    if klasifikasi not in (0, 1):
        abort(404)
    folder = _folder(klasifikasi)
    return render_template(f"learning/{folder}/bangun_datar/06_3.html", user_id=user_id, klasifikasi=klasifikasi)



def can_access_bangun_datar_quiz(user_id, klasifikasi):
    guard = _guard(user_id)
    if guard:
        return guard      
    folder = _folder(klasifikasi)

    # ==================== JIKA USER ADALAH SISWA (LEVEL 0) ====================
    if current_user.level == 0:
        # Catat aktivitas siswa telah membuka halaman ini
        _log_activity(user_id, "bangun_datar_quiz")

        # Ambil data history dari database khusus untuk materi Bangun Datar
        quiz_history = Score.query.filter_by(
            user_id=user_id,
            score_type="quiz",
            chapter="Bangun Datar", # Pastikan string ini sama dengan format penyimpanan di DB kamu
        ).order_by(Score.created_at.desc()).all()

        return render_template(
            f"learning/{folder}/bangun_datar/quiz.html",
            user_id=user_id,
            klasifikasi=klasifikasi,
            quiz_history=quiz_history,
            user_kkm=_get_kkm(current_user),
        )

    # ==================== JIKA USER ADALAH GURU (LEVEL != 0) ====================
    return render_template(
        f"learning/{folder}/bangun_datar/quiz.html",
        user_id=user_id,
        klasifikasi=klasifikasi,
    )
    
def can_access_bangun_datar_quiz_start(user_id, klasifikasi):
    guard = _guard(user_id)
    if guard:
        return guard

    folder = _folder(klasifikasi)
    kkm = _get_kkm(current_user) if current_user.is_authenticated else 70
    chapter_label = "Bangun Datar" # Sesuaikan dengan nama chapter di database Score

    # ==================== JIKA USER ADALAH SISWA (LEVEL 0) ====================
    if current_user.level == 0:
        last_score = _get_last_score(user_id, "quiz", chapter_label)

        # 1. Pengecekan apakah siswa sudah lulus KKM sebelumnya
        if last_score:
            if last_score.value >= kkm:
                flash(
                    f"Kamu sudah mencapai nilai KKM ({kkm}). "
                    f"Tidak perlu mengulang kuis ini lagi! 🎉",
                    "success",
                )
                return redirect(url_for("learning_bangun_datar", user_id=user_id, klasifikasi=klasifikasi))

            # 2. Pengecekan masa tunggu (cooldown)
            sisa_cooldown = _compute_cooldown(last_score)
            if sisa_cooldown > 0:
                flash(
                    f"Kamu baru saja mengerjakan kuis. "
                    f"Tunggu {sisa_cooldown // 60} menit {sisa_cooldown % 60} detik lagi.",
                    "warning",
                )
                return redirect(url_for("learning_bangun_datar", user_id=user_id, klasifikasi=klasifikasi))

        # 3. Atur waktu mulai kuis di session (gunakan key spesifik agar tidak bentrok dengan bab lain)
        session_key = "quiz_start_time_bangun_datar"
        if session_key not in session:
            session[session_key] = datetime.utcnow().isoformat()

        # 4. Hitung sisa detik kuis
        sisa_detik = QUIZ_DURATION_SECONDS - int(
            (datetime.utcnow() - datetime.fromisoformat(session[session_key])).total_seconds()
        )
        
        if sisa_detik <= 0:
            session.pop(session_key, None)
            flash("Waktu pengerjaan kuis telah habis.", "warning")
            return redirect(url_for("learning_bangun_datar", user_id=user_id, klasifikasi=klasifikasi))

        # Render template untuk siswa
        return render_template(
            f"learning/{folder}/bangun_datar/quiz_start.html",
            user_id=user_id,
            klasifikasi=klasifikasi,
            sisa_detik=sisa_detik,
            user_kkm=kkm,
            user_level=0
        )

    # ==================== JIKA USER ADALAH GURU (LEVEL != 0) ====================
    # Guru melewati validasi timer/cooldown (Bypass untuk preview)
    return render_template(
        f"learning/{folder}/bangun_datar/quiz_start.html",
        user_id=user_id,
        klasifikasi=klasifikasi,
        sisa_detik=15 * 60,                # Waktu default 15 menit
        user_kkm=kkm,
        user_level=current_user.level
    )
