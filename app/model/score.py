from app import db
from datetime import datetime


class Score(db.Model):
    __tablename__ = 'scores'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id', ondelete='SET NULL'), nullable=True)
    
    score_type = db.Column(db.String(20), nullable=False)  # Isinya: 'quiz' atau 'final_exam'
    chapter = db.Column(db.String(50), nullable=True)      # Isinya contoh: 'Bab 1', 'Bab 2'
    
    correct = db.Column(db.Integer, nullable=False)
    incorrect = db.Column(db.Integer, nullable=False)
    value = db.Column(db.Integer, nullable=False)          # Nilai gabungan ketepatan + kecepatan
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 🛠️ PERBAIKAN DI SINI: Sesuai nama kolom di atas
    def __repr__(self):
        return f'<Score user_id={self.user_id} type={self.score_type} chapter={self.chapter} value={self.value}>'
