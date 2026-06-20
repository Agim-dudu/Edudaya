import copy
import json
from app import db
from sqlalchemy import case
from flask_login import current_user 
from flask import request, jsonify, redirect, url_for
from app.model import User, Classes, EvaluationResult, ClassTeachers, Score

QUESTIONS_EVALUATION = [
    {
        "id": 1,
        "image": "none",
        "question": "Ibu membeli 24 apel EVALUASI. Apel tersebut akan dibagikan sama rata kepada 6 anak. Berapa apel yang didapat setiap anak?",
        "options": [
            {"id": "a", "text": "3 apel"},
            {"id": "b", "text": "4 apel"},
            {"id": "c", "text": "5 apel"},
            {"id": "d", "text": "6 apel"}
        ],
        "correct": "c",
        "topic": "Pembagian"
    },
    {
        "id": 2,
        "image": "none",
        "question": "Di dalam keranjang ada 35 telur. Pedagang menambahkan 17 telur lagi. Berapa jumlah telur sekarang?",
        "options": [
            {"id": "a", "text": "50 telur"},
            {"id": "b", "text": "51 telur"},
            {"id": "c", "text": "52 telur"},
            {"id": "d", "text": "53 telur"}
        ],
        "correct": "c",
        "topic": "Penjumlahan"
    },
    {
        "id": 3,
        "image": "none",
        "question": "Pak Budi mempunyai 80 batang pensil. Sebanyak 47 batang dibagikan kepada muridnya. Berapa sisa pensil Pak Budi?",
        "options": [
            {"id": "a", "text": "31 batang"},
            {"id": "b", "text": "32 batang"},
            {"id": "c", "text": "33 batang"},
            {"id": "d", "text": "34 batang"}
        ],
        "correct": "c",
        "topic": "Pengurangan"
    },
    {
        "id": 4,
        "image": "none",
        "question": "Sebuah toko kue menjual 9 kotak kue setiap hari. Setiap kotak berisi 8 kue. Berapa total kue yang terjual dalam 1 hari?",
        "options": [
            {"id": "a", "text": "63 kue"},
            {"id": "b", "text": "70 kue"},
            {"id": "c", "text": "72 kue"},
            {"id": "d", "text": "81 kue"}
        ],
        "correct": "c",
        "topic": "Perkalian"
    },
    {
        "id": 5,
        "image": "none",
        "question": "Tinggi badan Andi 125 cm, sedangkan tinggi badan kakaknya 148 cm. Berapa selisih tinggi badan mereka?",
        "options": [
            {"id": "a", "text": "21 cm"},
            {"id": "b", "text": "22 cm"},
            {"id": "c", "text": "23 cm"},
            {"id": "d", "text": "24 cm"}
        ],
        "correct": "c",
        "topic": "Pengurangan"
    },
    {
        "id": 6,
        "image": "none",
        "question": "Nilai ulangan matematika 5 siswa adalah: 70, 80, 90, 60, dan 100. Berapa nilai rata-rata mereka?",
        "options": [
            {"id": "a", "text": "75"},
            {"id": "b", "text": "78"},
            {"id": "c", "text": "80"},
            {"id": "d", "text": "82"}
        ],
        "correct": "c",
        "topic": "Rata-rata"
    },
    {
        "id": 7,
        "image": "none",
        "question": "Sebuah kolam renang berbentuk persegi panjang. Panjangnya 12 meter dan lebarnya 7 meter. Berapa luas kolam renang tersebut?",
        "options": [
            {"id": "a", "text": "74 m²"},
            {"id": "b", "text": "76 m²"},
            {"id": "c", "text": "82 m²"},
            {"id": "d", "text": "84 m²"}
        ],
        "correct": "c",
        "topic": "Luas Bangun Datar"
    },
    {
        "id": 8,
        "image": "none",
        "question": "Dina menabung Rp5.000 setiap hari. Setelah 2 minggu, berapa total uang tabungan Dina?",
        "options": [
            {"id": "a", "text": "Rp60.000"},
            {"id": "b", "text": "Rp65.000"},
            {"id": "c", "text": "Rp70.000"},
            {"id": "d", "text": "Rp75.000"}
        ],
        "correct": "c",
        "topic": "Perkalian"
    },
    {
        "id": 9,
        "image": "none",
        "question": "Dari 40 siswa di kelas, 25 siswa suka sepak bola dan sisanya suka badminton. Berapa persen siswa yang suka badminton?",
        "options": [
            {"id": "a", "text": "30%"},
            {"id": "b", "text": "35%"},
            {"id": "c", "text": "37,5%"},
            {"id": "d", "text": "40%"}
        ],
        "correct": "c",
        "topic": "Persentase"
    },
    {
        "id": 10,
        "image": "none",
        "question": "Sebuah taman berbentuk persegi dengan panjang sisi 15 meter. Berapakah keliling taman tersebut?",
        "options": [
            {"id": "a", "text": "45 meter"},
            {"id": "b", "text": "60 meter"},
            {"id": "c", "text": "75 meter"},
            {"id": "d", "text": "90 meter"}
        ],
        "correct": "c",
        "topic": "Keliling Bangun Datar"
    }
]

def save_evaluation(data, user_id):
    if not data or "answers" not in data:
        return jsonify({"error": "Data jawaban tidak ditemukan"}), 400

    student_answers = data["answers"]
    time_taken      = data.get("time_taken", 0)

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    answer_details = []
    correct_count  = 0
    topic_scores   = {}

    for q in QUESTIONS_EVALUATION:
        qid            = str(q["id"])
        student_answer = student_answers.get(qid, None)
        is_correct     = student_answer == q["correct"]
        if is_correct:
            correct_count += 1

        topic = q["topic"]
        if topic not in topic_scores:
            topic_scores[topic] = {"correct": 0, "total": 0}
        topic_scores[topic]["total"] += 1
        if is_correct:
            topic_scores[topic]["correct"] += 1

        answer_details.append({
            "nomor"         : q["id"],
            "pertanyaan"    : q["question"],
            "topik"         : topic,
            "jawaban_siswa" : student_answer,
            "jawaban_benar" : q["correct"],
            "benar"         : is_correct
        })

    total_questions = len(QUESTIONS_EVALUATION)
    incorrect_count = total_questions - correct_count
    score_value     = round((correct_count / total_questions) * 100)

    # ── JIKA USER LEVEL 0 (SISWA), SIMPAN DATA KE DATABASE ──
    # Catatan: Sesuaikan 'user.level' dengan nama kolom level/role di database Anda
    if hasattr(user, 'level') and user.level == 0:
        
        # 1. Simpan detail jawaban & analisis per topik
        existing_result = EvaluationResult.query.filter_by(user_id=user_id).first()
        if existing_result:
            existing_result.time_taken     = time_taken
            existing_result.topic_scores   = json.dumps(topic_scores, ensure_ascii=False)
            existing_result.answer_details = json.dumps(answer_details, ensure_ascii=False)
        else:
            db.session.add(EvaluationResult(
                user_id        = user_id,
                time_taken     = time_taken,
                topic_scores   = json.dumps(topic_scores, ensure_ascii=False),
                answer_details = json.dumps(answer_details, ensure_ascii=False),
            ))

        # 2. Simpan ringkasan nilai
        existing_score = Score.query.filter_by(
            user_id    = user_id,
            score_type = 'evaluation',
            chapter    = 'evaluation'
        ).first()

        if existing_score:
            existing_score.correct   = correct_count
            existing_score.incorrect = incorrect_count
            existing_score.value     = score_value
        else:
            db.session.add(Score(
                user_id    = user_id,
                class_id   = user.class_id if hasattr(user, 'class_id') else None,
                score_type = 'evaluation',
                chapter    = 'evaluation',
                correct    = correct_count,
                incorrect  = incorrect_count,
                value      = score_value
            ))

        # 3. Tandai user sudah evaluasi & commit ke DB
        user.evaluation = 1
        db.session.commit()
    
    # ── JIKA GURU / ADMIN (BUKAN LEVEL 0) ──
    # Database tidak akan diubah, tapi mereka tetap diarahkan ke halaman hasil evaluasi (bisa untuk simulasi/testing)
    else:
        print(f"User {user_id} adalah Guru/Admin (Level: {getattr(user, 'level', 'Tidak diketahui')}). Data tidak disimpan.")

    return jsonify({
        "status": "success",
        "redirect_url": url_for("learning_evaluation", user_id=user_id, klasifikasi=user.klasifikasi)
    })
    