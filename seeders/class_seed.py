from app import app, db
from app.model.classes import Classes  # pastikan ini path modelnya benar
from datetime import datetime

with app.app_context():
    # Daftar nama kelas yang ingin ditambahkan
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

    # Pairing nama kelas dan kkm dengan zip
    for class_name, school_name, class_token, kkm_value in zip(sample_classes, sample_school, sample_token, sample_kkm):
        existing_class = Classes.query.filter_by(classes=class_name).first()
        if not existing_class:
            kelas = Classes(classes=class_name, school=school_name, token=class_token, kkm=kkm_value)
            db.session.add(kelas)

    db.session.commit()
    print("✅ Seeder untuk Classes berhasil dijalankan (tanpa duplikasi)!")
