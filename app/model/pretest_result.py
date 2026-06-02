from datetime import datetime
from app import db

# =========================================================================
# 3. MODEL PRETEST RESULT (Hasil Pretest Siswa)
# =========================================================================
class PretestResult(db.Model):
    __tablename__ = 'pretest_results'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    score = db.Column(db.Integer, nullable=False)
    correct = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    time_taken = db.Column(db.Integer, nullable=True) 

    topic_scores = db.Column(db.Text, nullable=True)   
    answer_details = db.Column(db.Text, nullable=True) 
    ai_analysis = db.Column(db.Text, nullable=True)    

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PretestResult User_ID={self.user_id} Score={self.score}>'