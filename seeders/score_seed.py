# from app import app, db
# from app.model.scores import Score
# from app.model.user import User
# from datetime import datetime
# import random

# with app.app_context():
#     users = User.query.all()

#     if not users:
#         print("❌ Tidak ada user ditemukan. Seeder Score dihentikan.")
#     else:
#         for user in users:
#             if user.id in [1, 2, 3]:  # Untuk user id 1 dan 2
#                 # Skor quiz chapter 1-6 (semua 100)
#                 for chapter in range(1, 7):  # Loop dari chapter 1 sampai 6
#                     score = Score(
#                         user_id=user.id,
#                         score_type='quiz',
#                         chapter=str(chapter),  # chapter disimpan sebagai string
#                         correct=10,
#                         incorrect=0,
#                         value=100,  # Nilai 100 untuk setiap chapter
#                         created_at=datetime.utcnow()
#                     )
#                     db.session.add(score)

#                 # Skor final exam (evaluasi) 100
#                 final_score = Score(
#                     user_id=user.id,
#                     score_type='evaluasi',
#                     chapter='Evaluasi',  # final exam tidak punya chapter
#                     correct=20,
#                     incorrect=0,
#                     value=100,  # Nilai 100 untuk evaluasi
#                     created_at=datetime.utcnow()
#                 )
#                 db.session.add(final_score)

#         db.session.commit()
#         print(f"✅ Seeder score sukses! Ditambahkan skor quiz dan final untuk user dengan ID 1 dan 2.")
