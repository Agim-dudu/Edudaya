import copy
import json
from app import db
from sqlalchemy import case
from flask_login import current_user 
from flask import request, jsonify, redirect, url_for
from app.model import User, Classes, PretestResult, ClassTeachers

QUESTIONS_PRETEST = [
    {
        "id": 1,
        "image": "none",
        "question": "Ibu membeli 24 apel. Apel tersebut akan dibagikan sama rata kepada 6 anak. Berapa apel yang didapat setiap anak?",
        "options": [
            {"id": "a", "text": "3 apel"},
            {"id": "b", "text": "4 apel"},
            {"id": "c", "text": "5 apel"},
            {"id": "d", "text": "6 apel"}
        ],
        "correct": "b",
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
        "correct": "d",
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
        "correct": "b",
        "topic": "Keliling Bangun Datar"
    }
]

def get_safe_questions(questions):
    safe_questions = copy.deepcopy(questions)
    for question in safe_questions:
        if "correct" in question:
            del question["correct"]
    return safe_questions
 
def save_pretest(data, user_id):
    if not data or "answers" not in data:
        return jsonify({"error": "Data jawaban tidak ditemukan"}), 400

    student_answers = data["answers"]
    time_taken      = data.get("time_taken", 0)

    # 🔥 FIX: Menyamakan ID target agar konsisten menggunakan parameter user_id
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    answer_details = []
    correct_count  = 0
    topic_scores   = {}

    for q in QUESTIONS_PRETEST:
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

    score = round((correct_count / len(QUESTIONS_PRETEST)) * 100)

    # ── JIKA USER LEVEL 0 (SISWA), SIMPAN DATA KE DATABASE ──
    if hasattr(user, 'level') and user.level == 0:
        
        # Simpan atau update hasil pretest
        existing = PretestResult.query.filter_by(user_id=user_id).first()
        if existing:
            existing.score          = score
            existing.correct        = correct_count
            existing.total          = len(QUESTIONS_PRETEST)
            existing.time_taken     = time_taken
            existing.topic_scores   = json.dumps(topic_scores, ensure_ascii=False)
            existing.answer_details = json.dumps(answer_details, ensure_ascii=False)
            existing.ai_analysis    = None  
        else:
            result = PretestResult(
                user_id        = user_id,
                score          = score,
                correct        = correct_count,
                total          = len(QUESTIONS_PRETEST),
                time_taken     = time_taken,
                topic_scores   = json.dumps(topic_scores, ensure_ascii=False),
                answer_details = json.dumps(answer_details, ensure_ascii=False),
                ai_analysis    = None  
            )
            db.session.add(result)

        # Update status pretest user
        user.pretest = 1
        db.session.commit()
        
    # ── JIKA GURU / ADMIN (BUKAN LEVEL 0) ──
    else:
        print(f"User {user_id} adalah Guru/Admin (Level: {getattr(user, 'level', 'Tidak diketahui')}). Data Pretest tidak disimpan.")

    # Mengembalikan url_for BERSIH tanpa parameter classification
    return jsonify({
        "status": "success",
        "redirect_url": url_for("finish_pretest", user_id=user_id)
    })
    
def get_kelas_pretest_by_guru(user_id):
    guru = User.query.get(user_id)
    if not guru or guru.level != 1:
        return []

    kelas_details = []

    # 🔥 FIX: Iterasi melalui tabel jembatan 'teacher_classes' (Many-to-Many Guru ke Kelas)
    for rel in guru.teacher_classes:
        kelas = rel.class_obj
        if not kelas:
            continue

        # 🔥 FIX: Hitung jumlah siswa langsung dari filter 'class_id' di tabel User
        jumlah_siswa = (
            User.query
            .filter(
                User.level == 0,
                User.class_id == kelas.id
            )
            .count()
        )

        kelas_details.append({
            'id': kelas.id,               # Diubah ke kelas.id untuk keperluan routing analisis nanti
            'nama_kelas': kelas.name,     # 🔥 FIX: Dari 'kelas.classes' ke 'kelas.name'
            'nama_sekolah': kelas.school,
        })

    return kelas_details

def get_pretest_analysis(class_id: int) -> list[dict]:
    # 🔥 FIX: Query disederhanakan tanpa melakukan join ke tabel jembatan buatan dulu
    results = (
        db.session.query(
            User.id.label('user_id'),
            User.full_name,
            PretestResult.score,
            PretestResult.time_taken,
            PretestResult.ai_analysis,
            PretestResult.created_at,
        )
        .outerjoin(PretestResult, PretestResult.user_id == User.id)
        .filter(
            User.class_id == class_id,   # 🔥 FIX: Filter langsung mencocokkan class_id di tabel User
            User.level == 0,             # 0 = siswa
        )
        .order_by(
            case((PretestResult.score == None, 1), else_=0).asc(),  
            PretestResult.score.desc(),
            User.full_name.asc(),
        )
        .all()
    )

    return [
        {
            'user_id'     : row.user_id,
            'full_name'   : row.full_name,
            'score'       : row.score,
            'time_taken'  : row.time_taken,
            'pretest_done'    : row.score is not None,
            'analysis_done'    : row.ai_analysis is not None,
        }
        for row in results
    ]

def get_student_pretest_analysis_detail(teacher_id, user_id):
    if teacher_id != current_user.id:
        abort(403)

    student = User.query.filter_by(id=user_id, level=0).first_or_404()

    teacher_class_ids = [ct.class_id for ct in current_user.teacher_classes]
    if student.class_id not in teacher_class_ids:
        abort(403)

    pretest = student.pretest_result
    if not pretest:
        flash("Data analisis AI untuk siswa ini belum tersedia.", "warning")
        return None

    return {
        'student':        student,
        'score':          pretest.score,
        'correct':        pretest.correct,
        'total':          pretest.total,
        'time_taken':     pretest.time_taken,
        'topic_scores':   json.loads(pretest.topic_scores)   if pretest.topic_scores   else {},
        'answer_details': json.loads(pretest.answer_details) if pretest.answer_details else [],
        'ai_analysis':    json.loads(pretest.ai_analysis)    if pretest.ai_analysis    else None,
    }

def analyze_pretest(data):
    return jsonify({"status": "success", "message": "Analisis akan diproses oleh guru"})