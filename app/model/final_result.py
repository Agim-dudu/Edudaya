from datetime import datetime
from app import db

# =========================================================================
# 3. MODEL Final RESULT (Hasil final Siswa)
# =========================================================================
class FinalResult(db.Model):
    __tablename__ = 'final_results'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    ai_analysis = db.Column(db.Text, nullable=True)    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # PERBAIKAN DI SINI:
    def __repr__(self):
        return f'<FinalResult User_ID={self.user_id}>'