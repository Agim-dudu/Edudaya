from app import app, db
from app.model import User, Token, Classes, UserClasses
from werkzeug.security import generate_password_hash
from datetime import datetime

with app.app_context():
    # Kosongkan tabel relasi dan user
    db.session.query(UserClasses).delete()
    db.session.query(User).delete()

    # Ambil token dan kelas
    token = Token.query.filter_by(token="#FreeToken1").first()
    kelas = Classes.query.filter_by(classes="Contoh").first()

    if not token or not kelas:
        print("❌ Token atau kelas tidak ditemukan. Jalankan seeder token & classes dulu.")
    else:
        users = [
            {
                "username": "SuperAdmin",
                "full_name": "Super Admin",
                "password": "12345",
                "level": 2,
                "progress": 100,
            },
            {
                "username": "ContohGuru",
                "full_name": "Contoh Guru",
                "password": "12345",
                "level": 1,
                "progress": 100,
            },
            {
                "username": "SiswaProgres",
                "full_name": "Siswa Progres",
                "password": "12345",
                "level": 0,
                "progress": 100,
            },
            {
                "username": "SiswaBiasa",
                "full_name": "Siswa Biasa",
                "password": "12345",
                "level": 0,
                "progress": 0,
            },
        ]

        for u in users:
            hashed_pw = generate_password_hash(u["password"])

            new_user = User(
                username=u["username"],
                full_name=u["full_name"],
                password=hashed_pw,
                level=u["level"],              # <- fix dari role
                token=token.token,             # <- wajib
                progress=u["progress"],        # <- fix dari progres
                # image otomatis 'default.jpg'
                # field lain nullable → tidak perlu diisi
            )

            db.session.add(new_user)
            db.session.flush()

            # Relasi ke kelas
            user_class = UserClasses(
                user_id=new_user.id,
                class_id=kelas.id
            )
            db.session.add(user_class)

        db.session.commit()
        print("✅ Seeder User berhasil! Data user dan relasi ke kelas sudah masuk.")
