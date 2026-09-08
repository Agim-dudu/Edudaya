import json
from app import app, db
from app.model import User, Classes, ClassTeachers, PretestResult  # 🧠 DIUBAH: Menggunakan ClassTeachers, hapus UserClasses
from datetime import datetime

with app.app_context():
    # 1. Hapus data lama dengan urutan yang aman (child table dulu baru parent table)
    db.session.query(PretestResult).delete()
    db.session.query(ClassTeachers).delete()
    db.session.query(User).delete()
    db.session.commit()

    # 2. Cari token kelas acuan
    token_kelas = Classes.query.filter_by(token="#SDN-BJM1").first()

    if not token_kelas:
        print("❌ Token kelas tidak ditemukan. Jalankan seeder classes dulu.")
    else:
        users_data = [
            {
                "username": "SuperAdmin",
                "full_name": "Super Admin",
                "password": "12345",
                "level": 2,
                "gender": "L",
                "progress": 100,
            },
            {
                "username": "ContohGuru",
                "full_name": "Contoh Guru",
                "password": "12345",
                "level": 1,
                "gender": "L",
                "progress": 100,
            },
            {
                "username": "SiswaRendah",
                "full_name": "Siswa Rendah",
                "password": "12345",
                "level": 0,
                "gender": "L",
                "progress": 0,
                "klasifikasi": 0,
                "pretest": {"score": 30, "correct": 3, "time_taken": 600,
                            "ai_analysis": {
                                "level_kemampuan": {"level": "rendah"},
                                "motivasi": "Jangan menyerah ya! Setiap ahli juga pernah menjadi pemula. Teruslah berlatih!",
                                "kekuatan": ["Sudah berani mencoba mengerjakan seluruh soal pretest"],
                                "kelemahan": ["Pemahaman konsep dasar bangun datar masih perlu penguatan", "Ketelitian dalam membaca soal perlu ditingkatkan"],
                                "rekomendasi_siswa": ["Mempelajari ulang materi Konsep Bangun Datar di level rendah", "Berlatih soal bersama guru atau teman"],
                            }},
            },
            {
                "username": "SiswaMedium",
                "full_name": "Siswa Medium",
                "password": "12345",
                "level": 0,
                "gender": "L",
                "progress": 0,
                "klasifikasi": 1,
                "pretest": {"score": 60, "correct": 6, "time_taken": 480,
                            "ai_analysis": {
                                "level_kemampuan": {"level": "sedang"},
                                "motivasi": "Kerja bagus! Kamu sudah memahami banyak konsep. Sedikit lagi menuju level tinggi!",
                                "kekuatan": ["Memahami sebagian besar konsep dasar bangun datar"],
                                "kelemahan": ["Masih keliru pada soal penerapan rumus keliling dan luas"],
                                "rekomendasi_siswa": ["Mengulang bagian keliling dan luas bangun datar", "Mengerjakan latihan tambahan setiap hari"],
                            }},
            },
            {
                "username": "SiswaTinggi",
                "full_name": "Siswa Tinggi",
                "password": "12345",
                "level": 0,
                "gender": "L",
                "progress": 0,
                "klasifikasi": 2,
                "pretest": {"score": 90, "correct": 9, "time_taken": 360,
                            "ai_analysis": {
                                "level_kemampuan": {"level": "tinggi"},
                                "motivasi": "Luar biasa! Pemahamanmu sangat kuat. Terus tantang dirimu dengan soal yang lebih menantang!",
                                "kekuatan": ["Pemahaman konsep bangun datar sangat baik", "Cepat dan teliti dalam mengerjakan soal"],
                                "kelemahan": ["Sedikit keliru pada soal analisis tingkat tinggi"],
                                "rekomendasi_siswa": ["Melanjutkan ke materi Segitiga level tinggi", "Membantu teman belajar agar pemahaman makin mendalam"],
                            }},
            },
        ]

        for u in users_data:
            # Tentukan class_id awal. Hanya Siswa (level 0) yang langsung punya class_id fisik
            target_class_id = token_kelas.id if u["level"] == 0 else None

            new_user = User(
                username=u["username"],
                full_name=u["full_name"],
                level=u["level"],
                gender=u["gender"],
                progress=u["progress"],
                klasifikasi=u.get("klasifikasi"),
                class_id=target_class_id  # 🔥 FIX: Siswa langsung dikunci ke kelasnya di sini
            )
            # Menggunakan method bawaan model untuk hash password
            new_user.set_password(u["password"]) 

            db.session.add(new_user)
            db.session.flush()  # Mengenerate new_user.id tanpa commit dulu

            # 🔥 FIX LOGIK GURU: Jika user adalah Guru (level 1), daftarkan ke tabel jembatan ClassTeachers
            if new_user.level == 1:
                teacher_class_bridge = ClassTeachers(
                    teacher_id=new_user.id,
                    class_id=token_kelas.id
                )
                db.session.add(teacher_class_bridge)

            # 🌱 DATA PRA-ISIS SISWA: buat PretestResult lengkap (score + analisis AI)
            # agar siswa bisa langsung masuk materi tanpa mengerjakan pretest ulang
            if u["level"] == 0 and "pretest" in u:
                pretest = PretestResult(
                    user_id=new_user.id,
                    score=u["pretest"]["score"],
                    correct=u["pretest"]["correct"],
                    time_taken=u["pretest"]["time_taken"],
                    answer_details=None,
                    ai_analysis=json.dumps(u["pretest"]["ai_analysis"], ensure_ascii=False),
                )
                db.session.add(pretest)

        db.session.commit()
        print("✅ Seeder User & Relasi Kelas Berhasil Diperbarui!")