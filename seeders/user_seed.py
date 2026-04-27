from app import app, db
from app.model import User, Classes, UserClasses
from werkzeug.security import generate_password_hash
from datetime import datetime

with app.app_context():
    # Hapus data lama
    db.session.query(UserClasses).delete()
    db.session.query(User).delete()

    token_kelas = Classes.query.filter_by(token="#SDN-BJM1").first()

    if not token_kelas:
        print("❌ Token kelas tidak ditemukan. Jalankan seeder classes dulu.")
    else:
        users = [
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

        for u in users:
            new_user = User(
                username=u["username"],
                full_name=u["full_name"],
                password=generate_password_hash(u["password"]),
                level=u["level"],
                gender=u["gender"],
                progress=u["progress"],
            )

            db.session.add(new_user)
            db.session.flush()

            user_class = UserClasses(
                user_id=new_user.id, class_token=token_kelas.id  # ✅ FIX DI SINI
            )
            db.session.add(user_class)

        db.session.commit()
        print("✅ Seeder User berhasil!")
