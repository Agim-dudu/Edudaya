from app import app, db
from app.model import Token  # Sesuaikan path jika perlu
from datetime import datetime, timedelta

with app.app_context():
    # Kosongkan tabel tokens
    db.session.query(Token).delete()

    # Data token contoh
    sample_tokens = [
        {
            "token": "#FreeToken1",
            "expires_at": datetime.utcnow() + timedelta(days=1)
        },
        {
            "token": "#FreeToken2",
            "expires_at": datetime.utcnow() + timedelta(days=2)
        },
        {
            "token": "#FreeToken3",
            "expires_at": datetime.utcnow() + timedelta(hours=12)
        }
    ]

    # Tambahkan token ke database
    for t in sample_tokens:
        new_token = Token(token=t["token"], expires_at=t["expires_at"])
        db.session.add(new_token)

    db.session.commit()
    print("✅ Seeder untuk Token berhasil dijalankan!")
