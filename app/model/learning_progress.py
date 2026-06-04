from app import db
from datetime import datetime


class LearningProgress(db.Model):
    __tablename__ = 'learning_progress'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    lesson_key = db.Column(db.String(20), nullable=False, default='')
    material_key = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False, default=0)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'material_key', name='uq_user_material'),
    )

    def __repr__(self):
        return f'<LearningProgress user={self.user_id} lesson={self.lesson_key} key={self.material_key} score={self.score}>'
