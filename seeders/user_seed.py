from app import app, db
from app.model import User, Classes, ClassTeachers  # 🧠 DIUBAH: Menggunakan ClassTeachers, hapus UserClasses
from datetime import datetime

with app.app_context():
    # 1. Hapus data lama dengan urutan yang aman (child table dulu baru parent table)
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
                "username": "SiswaProgres",
                "full_name": "Siswa Progres",
                "password": "12345",
                "level": 0,
                "gender": "L",
                "progress": 100,
            },
            {
                "username": "SiswaBiasa",
                "full_name": "Siswa Biasa",
                "password": "12345",
                "level": 0,
                "gender": "L",
                "progress": 0,
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

        db.session.commit()
        print("✅ Seeder User & Relasi Kelas Berhasil Diperbarui!")