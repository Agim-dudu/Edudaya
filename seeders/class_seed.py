from app import app, db
from app.model.classes import Classes  # Pastikan path ini sesuai struktur folder kamu
from datetime import datetime

with app.app_context():
    # Opsional: Jika ingin membersihkan data kelas lama setiap kali seeder dijalankan,
    # hapus tanda komentar (#) pada baris di bawah ini:
    # db.session.query(Classes).delete()
    # db.session.commit()

    # Daftar data yang akan dimasukkan
    sample_classes = [
        "Contoh",
        "Contoh1",
        "Contoh2",
    ]
    sample_school = [
        "SDN 1 Banjarmasin",
        "SDN 1 Banjarbaru",
        "SDN 3 Banjarmasin",
    ]
    sample_token = [
        "#SDN-BJM1",
        "#SDN-BJB1",
        "#SDN-BJM3",
    ]
    sample_kkm = [
        70,
        80,
        70,
    ]

    # Pairing data menggunakan zip
    for class_name, school_name, class_token, kkm_value in zip(
        sample_classes, sample_school, sample_token, sample_kkm
    ):
        # 🧠 DIUBAH: Pengecekan duplikasi menggunakan token (karena token bersifat UNIQUE di DB)
        existing_class = Classes.query.filter_by(token=class_token).first()
        
        if not existing_class:
            kelas = Classes(
                name=class_name,       # 🔥 FIX: Menggunakan 'name' sesuai model baru, bukan 'classes'
                school=school_name, 
                token=class_token, 
                kkm=kkm_value
            )
            db.session.add(kelas)

    db.session.commit()
    print("✅ Seeder untuk Classes berhasil dijalankan (tanpa duplikasi)!")