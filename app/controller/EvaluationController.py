import json
from app import db
from flask import jsonify, url_for
from app.model import User, EvaluationResult
from app.controller.PretestController import QUESTIONS_PRETEST

# Evaluasi memakai soal yang sama persis dengan pretest.
QUESTIONS_EVALUATION = QUESTIONS_PRETEST

def save_evaluation(data, user_id):
    if not data or "answers" not in data:
        return jsonify({"error": "Data jawaban tidak ditemukan"}), 400

    student_answers = data["answers"]
    time_taken      = data.get("time_taken", 0)

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    answer_details = []
    for q in QUESTIONS_EVALUATION:
        answer_details.append({
            "nomor": q["id"],
            "tingkat": q["level"],
            "catatan_ai": q["note_ai"],
            "pertanyaan": q["question"],
            "topik": q["topic"],
            "jawaban_siswa": student_answers.get(str(q["id"])),
            "jawaban_benar": q["correct"],
        })

    # ── JIKA USER LEVEL 0 (SISWA), SIMPAN DATA KE DATABASE ──
    # Catatan: Sesuaikan 'user.level' dengan nama kolom level/role di database Anda
    if hasattr(user, 'level') and user.level == 0:
        
        # Simpan jawaban isian untuk penilaian akhir, seperti pada pretest.
        # Jawaban bebas tidak dinilai dengan perbandingan string literal.
        if EvaluationResult.query.filter_by(user_id=user_id).first():
            return jsonify({"error": "Evaluasi sudah dikirim."}), 409

        db.session.add(EvaluationResult(
            user_id=user_id,
            time_taken=time_taken,
            topic_scores=json.dumps({}, ensure_ascii=False),
            answer_details=json.dumps(answer_details, ensure_ascii=False),
        ))
        user.evaluation = 1
        db.session.commit()

    # ── JIKA GURU / ADMIN (BUKAN LEVEL 0) ──
    # Database tidak akan diubah, tapi mereka tetap diarahkan ke halaman hasil evaluasi (bisa untuk simulasi/testing)
    else:
        pass

    return jsonify({
        "status": "success",
        "redirect_url": url_for("learning_evaluation", user_id=user_id, klasifikasi=user.klasifikasi)
    })
