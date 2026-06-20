import json
from app import db
from app.model import User, ActivityLog, Score, Classes
from flask_login import current_user
from datetime import datetime
from app.controller.EvaluationController import QUESTIONS_EVALUATION
from flask import jsonify, request, render_template, redirect, url_for, flash, session

# ---------------------------------------------------------------------------
# BAB CONFIGURATION REGISTRY
# ---------------------------------------------------------------------------

BAB_CONFIG = {
    "bab1": {
        "label": "Bab 1",
        "flow": [
            {"activity_key": "bab1_chapter1_activity", "route": "learning_bab1_chapter1"},
            {"activity_key": "bab1_chapter2_activity", "route": "learning_bab1_chapter2"},
            {"activity_key": "bab1_summary",           "route": "learning_bab1_summary"},
            {"activity_key": "bab1_quiz",              "route": "learning_bab1_quiz"},
        ],
        "dir": "bab1",
        "prerequisite_quiz": None,
    },
    "bab2": {
        "label": "Bab 2",
        "flow": [
            {"activity_key": "bab2_chapter1_activity", "route": "learning_bab2_chapter1"},
            {"activity_key": "bab2_chapter2_activity", "route": "learning_bab2_chapter2"},
            {"activity_key": "bab2_summary",           "route": "learning_bab2_summary"},
            {"activity_key": "bab2_quiz",              "route": "learning_bab2_quiz"},
        ],
        "dir": "bab2",
        "prerequisite_quiz": "Bab 1",
    },
    "evaluation": {
        "label": "Evaluation",
        "flow": [
            {"activity_key": "evaluation", "route": "learning_evaluation"},
        ],
        "dir": "evaluation",
        "prerequisite_quiz": "Bab 2",
    },
}

FOLDERS = ["low", "medium", "high"]
QUIZ_COOLDOWN_SECONDS = 180
QUIZ_DURATION_SECONDS = 900
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
        prereq_key = next(k for k, v in BAB_CONFIG.items() if v["label"] == prereq_label)
        return redirect(url_for(
            f"learning_{prereq_key}_quiz",
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
# GENERIC ACCESS FUNCTIONS
# ---------------------------------------------------------------------------

def can_access_chapter(user_id: int, klasifikasi: int, bab_key: str, chapter_num: int):
    guard = _guard(user_id)
    if guard:
        return guard

    cfg    = BAB_CONFIG[bab_key]
    folder = _folder(klasifikasi)
    tmpl   = f"learning/{folder}/{cfg['dir']}/{chapter_num:02d}.html"

    block = _guard_prerequisite_quiz(user_id, klasifikasi, bab_key)
    if block:
        return block

    if current_user.level == 0 and chapter_num > 1:
        prev_key   = cfg["flow"][chapter_num - 2]["activity_key"]
        prev_route = cfg["flow"][chapter_num - 2]["route"]
        if not has_activity(user_id, prev_key):
            return redirect(url_for(prev_route, user_id=user_id, klasifikasi=klasifikasi))

    return render_template(tmpl, user_id=user_id)


def can_access_summary(user_id: int, klasifikasi: int, bab_key: str):
    guard = _guard(user_id)
    if guard:
        return guard

    cfg    = BAB_CONFIG[bab_key]
    folder = _folder(klasifikasi)

    block = _guard_prerequisite_quiz(user_id, klasifikasi, bab_key)
    if block:
        return block

    if current_user.level == 0:
        block = get_first_incomplete_route(user_id, klasifikasi, cfg["flow"][:-2])
        if block:
            return block
        _log_activity(user_id, f"{bab_key}_summary")

    return render_template(f"learning/{folder}/{cfg['dir']}/summary.html", user_id=user_id)


def can_access_quiz(user_id: int, klasifikasi: int, bab_key: str):
    guard = _guard(user_id)
    if guard:
        return guard

    cfg    = BAB_CONFIG[bab_key]
    folder = _folder(klasifikasi)

    block = _guard_prerequisite_quiz(user_id, klasifikasi, bab_key)
    if block:
        return block

    if current_user.level == 0:
        block = get_first_incomplete_route(user_id, klasifikasi, cfg["flow"][:-1])
        if block:
            return block

        _log_activity(user_id, f"{bab_key}_quiz")

        quiz_history = Score.query.filter_by(
            user_id=user_id,
            score_type="quiz",
            chapter=cfg["label"],
        ).order_by(Score.created_at.desc()).all()

        return render_template(
            f"learning/{folder}/{cfg['dir']}/quiz.html",
            user_id=user_id,
            quiz_history=quiz_history,
            user_kkm=_get_kkm(current_user),
        )

    return render_template(f"learning/{folder}/{cfg['dir']}/quiz.html", user_id=user_id)

def can_access_quiz_start(user_id: int, klasifikasi: int, bab_key: str):
    guard = _guard(user_id)
    if guard:
        return guard

    cfg        = BAB_CONFIG[bab_key]
    folder     = _folder(klasifikasi)
    quiz_route = f"learning_{bab_key}_quiz"

    block = _guard_prerequisite_quiz(user_id, klasifikasi, bab_key)
    if block:
        return block

    # Ambil KKM (Gunakan helper _get_kkm milikmu, default ke 70 jika tidak ketemu)
    kkm = _get_kkm(current_user) if current_user.is_authenticated else 70

    # ==================== JIKA USER ADALAH SISWA (LEVEL 0) ====================
    if current_user.level == 0:
        block = get_first_incomplete_route(user_id, klasifikasi, cfg["flow"][:-1])
        if block:
            return block

        if not has_activity(user_id, f"{bab_key}_quiz"):
            return redirect(url_for(quiz_route, user_id=user_id, klasifikasi=klasifikasi))

        last_score = _get_last_score(user_id, "quiz", cfg["label"])

        # Pengecekan apakah siswa sudah lulus KKM sebelumnya
        if last_score:
            if last_score.value >= kkm:
                flash(
                    f"Kamu sudah mencapai nilai KKM ({kkm}). "
                    f"Tidak perlu mengulang kuis ini lagi! 🎉",
                    "success",
                )
                return redirect(url_for(quiz_route, user_id=user_id, klasifikasi=klasifikasi))

            # Pengecekan masa tunggu (cooldown) siswa
            sisa_cooldown = _compute_cooldown(last_score)
            if sisa_cooldown > 0:
                flash(
                    f"Kamu baru saja mengerjakan kuis. "
                    f"Tunggu {sisa_cooldown // 60} menit {sisa_cooldown % 60} detik lagi.",
                    "warning",
                )
                return redirect(url_for(quiz_route, user_id=user_id, klasifikasi=klasifikasi))

        # Atur waktu mulai kuis di session jika belum ada
        if "quiz_start_time" not in session:
            session["quiz_start_time"] = datetime.utcnow().isoformat()

        # Hitung sisa detik kuis untuk siswa
        sisa_detik = QUIZ_DURATION_SECONDS - int(
            (datetime.utcnow() - datetime.fromisoformat(session["quiz_start_time"])).total_seconds()
        )
        if sisa_detik <= 0:
            session.pop("quiz_start_time", None)
            flash("Waktu pengerjaan kuis telah habis.", "warning")
            return redirect(url_for(quiz_route, user_id=user_id, klasifikasi=klasifikasi))

        # Render template dengan data lengkap untuk Siswa
        return render_template(
            f"learning/{folder}/{cfg['dir']}/quiz_start.html",
            user_id=user_id,
            sisa_detik=sisa_detik,
            user_kkm=kkm,
            user_level=0  # Penanda di JS bahwa ini Siswa
        )

    # ==================== JIKA USER ADALAH GURU (LEVEL != 0) ====================
    # Guru atau admin melewati semua validasi di atas (Bypass mode preview)
    return render_template(
        f"learning/{folder}/{cfg['dir']}/quiz_start.html", 
        user_id=user_id,
        sisa_detik=15 * 60,                # Berikan waktu default 15 menit untuk simulasi
        user_kkm=kkm,                      # Berikan nilai KKM asli kelas tersebut
        user_level=current_user.level      # Mengirim level asli guru (misal: 1 atau 2)
    )

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

        if "quiz_start_time" not in session:
            session["quiz_start_time"] = datetime.utcnow().isoformat()

        sisa_detik = QUIZ_DURATION_SECONDS - int(
            (datetime.utcnow() - datetime.fromisoformat(session["quiz_start_time"])).total_seconds()
        )
        if sisa_detik <= 0:
            session.pop("quiz_start_time", None)
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

# BAB 1
def can_access_bab1_chapter1(user_id, klasifikasi):
    return can_access_chapter(user_id, klasifikasi, "bab1", 1)

def can_access_bab1_chapter2(user_id, klasifikasi):
    return can_access_chapter(user_id, klasifikasi, "bab1", 2)

def can_access_bab1_summary(user_id, klasifikasi):
    return can_access_summary(user_id, klasifikasi, "bab1")

def can_access_bab1_quiz(user_id, klasifikasi):
    return can_access_quiz(user_id, klasifikasi, "bab1")

def can_access_bab1_quiz_start(user_id, klasifikasi):
    return can_access_quiz_start(user_id, klasifikasi, "bab1")

# BAB 2
def can_access_bab2_chapter1(user_id, klasifikasi):
    return can_access_chapter(user_id, klasifikasi, "bab2", 1)

def can_access_bab2_chapter2(user_id, klasifikasi):
    return can_access_chapter(user_id, klasifikasi, "bab2", 2)

def can_access_bab2_summary(user_id, klasifikasi):
    return can_access_summary(user_id, klasifikasi, "bab2")

def can_access_bab2_quiz(user_id, klasifikasi):
    return can_access_quiz(user_id, klasifikasi, "bab2")

def can_access_bab2_quiz_start(user_id, klasifikasi):
    return can_access_quiz_start(user_id, klasifikasi, "bab2")

# Evaluation
def can_access_learning_evaluation(user_id, klasifikasi):
    return can_access_evaluation(user_id, klasifikasi)

def can_access_learning_evaluation_start(user_id, klasifikasi):
    return can_access_evaluation_start(user_id, klasifikasi, "evaluation")