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
    "note_ai": "Toleransi typo nama bangun datar.",
    "level": "Mudah",
    "question": "Aku adalah bangun datar yang memiliki 4 sisi dan sepasang sisi sejajar. Siapakah aku?",
    "correct": "trapesium",
    "topic": "Sifat Bangun Datar",
    "score": "10"
  },
  {
    "id": 2,
    "image": "none",
    "note_ai": "Toleransi typo nama bangun datar.",
    "level": "Mudah",
    "question": "Bangun datar yang memiliki 2 diagonal yang saling tegak lurus namun tidak sama panjang. 2 pasang sisi yang panjangnya berbeda. Bangun datar apakah yang memiliki ciri-ciri tersebut?",
    "correct": "layang-layang",
    "topic": "Sifat Bangun Datar",
    "score": "10"
  },
  {
    "id": 3,
    "image": "none",
    "note_ai": "Luas = p x l = 12 x 5 = 60 cm².",
    "level": "Mudah",
    "question": "Sebuah persegi panjang memiliki panjang 12 cm dan lebar 5 cm. Berapa luasnya?",
    "correct": "60 cm²",
    "topic": "Luas Bangun Datar",
    "score": "10"
  },
  {
    "id": 4,
    "image": "none",
    "note_ai": "Keliling = 4 x s = 4 x 15 = 60 cm.",
    "level": "Sedang",
    "question": "Yogi memiliki sebuah kertas berbentuk persegi dengan panjang sisi 15 cm. Ia ingin menempelkan pita di sepanjang tepi kertas tersebut. Berapa panjang pita yang dibutuhkan Yogi?",
    "correct": "60 cm",
    "topic": "Keliling Bangun Datar",
    "score": "10"
  },
  {
    "id": 5,
    "image": "none",
    "note_ai": "Luas = 1/2 x a x t = 1/2 x 6 x 4 = 12 cm².",
    "level": "Sedang",
    "question": "Sebuah segitiga memiliki alas 6 cm dan tinggi 4cm. Berapakah luasnya?",
    "correct": "12 cm²",
    "topic": "Luas Segitiga",
    "score": "10"
  },
  {
    "id": 6,
    "image": "none",
    "note_ai": "Luas A = 100 cm², Luas B = 96 cm². Bangun A lebih besar.",
    "level": "Sedang",
    "question": "Bangun A berbentuk persegi dengan sisi 10 cm. Bangun B berbentuk persegi panjang dengan panjang 12 cm dan lebar 8 cm. Bangun manakah yang memiliki luas lebih besar?",
    "correct": "Bangun A",
    "topic": "Komparasi Luas",
    "score": "10"
  },
  {
    "id": 7,
    "image": "none",
    "note_ai": "Jawaban 'Salah' saja mendapat 50% skor. Alasan esensial: 2x(p+l) adalah keliling, harusnya Luas = p x l = 84 cm².",
    "level": "Sedang",
    "question": "Siti menghitung luas sebuah persegi panjang yang panjangnya 14 cm dan lebarnya 6 cm dengan cara: \"2 × (14 + 6) = 40\" Siti mengatakan bahwa luas persegi panjang tersebut adalah 40 cm². Apakah jawaban Siti benar? Kemukakan alasanmu!",
    "correct": "Salah. 2 × (p + l) adalah rumus keliling. Luas persegi panjang seharusnya 14 × 6 = 84 cm².",
    "topic": "Analisis Kesalahan Konsep",
    "score": "10"
  },
  {
    "id": 8,
    "image": "none",
    "note_ai": "Pilihan pasangan (p, l) yang menghasilkan luas 72: (72,1), (36,2), (24,3), (18,4), (12,6), (9,8). Pasangan yang mendekati bentuk persegi memiliki keliling lebih kecil (misal: 9 cm dan 8 cm).",
    "level": "Tinggi",
    "question": "Sebuah persegi panjang memiliki luas 72 cm². Tuliskan dua kemungkinan ukuran panjang dan lebar persegi panjang tersebut. Kemudian tentukan persegi panjang mana yang memiliki keliling lebih kecil.",
    "correct": "Dua kemungkinan pasangan (p, l) misal: (18 dan 4) serta (9 dan 8). Ukuran yang mendekati sama (9 cm dan 8 cm) memiliki keliling lebih kecil.",
    "topic": "Problem Solving Luas & Keliling",
    "score": "10"
  },
  {
    "id": 9,
    "image": "none",
    "note_ai": "Syarat segitiga: a + b > c. Karena 4 + 5 = 9, kawat tidak bisa membentuk segitiga maupun bangun datar tertutup lainnya.",
    "level": "Tinggi",
    "question": "Jika sebuah kawat dengan panjang 4 cm, 5 cm, dan 9 cm. Maka bangun datar yang dapat dibuat dari ketiga kawat tersebut?",
    "correct": "Tidak ada bangun datar yang dapat dibuat, karena jumlah dua sisi terpendek (4 + 5 = 9) sama dengan sisi terpanjang sehingga kawat hanya membentuk garis lurus.",
    "topic": "Ketidaksamaan Segitiga",
    "score": "10"
  },
  {
    "id": 10,
    "image": "none",
    "note_ai": "Keliling = 40 m -> p + l = 20 m. Pasangan (p, l) yang valid: (19,1), (18,2), (17,3), (16,4), (15,5), (14,6), (13,7), (12,8), (11,9), (10,10). Menjawab 3 pasang benar = Skor penuh.",
    "level": "Tinggi",
    "question": "Ibu mempunyai 40 meter kawat untuk membuat sebuah pagar berbentuk persegi panjang. Kawat tersebut harus digunakan seluruhnya. Tentukan 3 kemungkinan ukuran panjang dan lebar pagar.",
    "correct": "3 pasang ukuran panjang dan lebar yang jika dijumlahkan bernilai 20 m (contoh: 18m & 2m, 16m & 4m, 14m & 6m).",
    "topic": "Problem Solving Keliling",
    "score": "10"
  }
]

def get_safe_questions(questions):
    safe_questions = copy.deepcopy(questions)
    for question in safe_questions:
        if "correct" in question:
            del question["correct"]
    return safe_questions
 
def save_pretest(data, user_id):
    """
    Menyimpan JAWABAN siswa apa adanya, TANPA menghitung skor/benar-salah.
    Penilaian (score, correct, topic_scores) sengaja ditinggalkan kosong
    (None) untuk diisi belakangan oleh proses koreksi guru/AI
    (lihat analyze_pretest).
    """
    if not data or "answers" not in data:
        return jsonify({"error": "Data jawaban tidak ditemukan"}), 400

    student_answers = data["answers"]
    time_taken      = data.get("time_taken", 0)

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User tidak ditemukan"}), 404

    # Kumpulkan jawaban siswa per soal, tanpa membandingkan ke kunci jawaban
    answer_details = []
    for q in QUESTIONS_PRETEST:
        qid            = str(q["id"])
        student_answer = student_answers.get(qid, None)

        answer_details.append({
            "nomor"         : q["id"],
            "tingkat"    : q["level"],
            "catatan_ai"    : q["note_ai"],
            "topik"         : q["topic"],
            "pertanyaan"    : q["question"],
            "jawaban_benar" : q["correct"],  # disimpan sbg referensi untuk koreksi nanti
            "jawaban_siswa" : student_answer,
        })

    # ── JIKA USER LEVEL 0 (SISWA), SIMPAN DATA KE DATABASE ──
    if hasattr(user, 'level') and user.level == 0:

        # score & correct dibiarkan None (belum dinilai) — kolomnya sudah nullable.
        # total soal TIDAK disimpan di kolom terpisah (model tidak punya kolom
        # 'total'); jumlah soal cukup dihitung dari len(QUESTIONS_PRETEST) atau
        # dari panjang answer_details saat dibutuhkan.
        # time_taken = detik yang dipakai siswa mengerjakan (durasi total - sisa
        # waktu saat submit), dikirim dari frontend sebagai DURATION - timeLeft.
        existing = PretestResult.query.filter_by(user_id=user_id).first()
        if existing:
            existing.score          = None
            existing.correct        = None
            existing.time_taken     = time_taken
            existing.answer_details = json.dumps(answer_details, ensure_ascii=False)
            existing.ai_analysis    = None
        else:
            result = PretestResult(
                user_id        = user_id,
                score          = None,
                correct        = None,
                time_taken     = time_taken,
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

    return jsonify({
        "status": "success",
        "redirect_url": url_for("finish_pretest", user_id=user_id)
    })
    
def get_kelas_pretest_by_guru(user_id):
    guru = User.query.get(user_id)
    if not guru or guru.level != 1:
        return []

    kelas_details = []

    for rel in guru.teacher_classes:
        kelas = rel.class_obj
        if not kelas:
            continue

        jumlah_siswa = (
            User.query
            .filter(
                User.level == 0,
                User.class_id == kelas.id
            )
            .count()
        )

        kelas_details.append({
            'id': kelas.id,
            'nama_kelas': kelas.name,
            'nama_sekolah': kelas.school,
        })

    return kelas_details

def get_pretest_analysis(class_id: int) -> list[dict]:
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
            User.class_id == class_id,
            User.level == 0,
        )
        .order_by(
            # Belum mengerjakan pretest (tidak ada baris PretestResult) tampil paling akhir
            case((PretestResult.created_at == None, 1), else_=0).asc(),
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
            'pretest_done'  : row.created_at is not None,
            'analysis_done' : row.ai_analysis is not None,
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
        'total':          len(QUESTIONS_PRETEST),  # dihitung langsung, bukan dari kolom DB
        'time_taken':     pretest.time_taken,
        'answer_details': json.loads(pretest.answer_details) if pretest.answer_details else [],
        'ai_analysis':    json.loads(pretest.ai_analysis)    if pretest.ai_analysis    else None,
    }

def analyze_pretest(data):
    return jsonify({"status": "success", "message": "Analisis akan diproses oleh guru"})