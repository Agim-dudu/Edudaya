from app import db
from datetime import datetime

class Classes(db.Model):
    __tablename__ = 'classes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    classes = db.Column(db.String(45), nullable=False, unique=True)
    kkm = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_classes = db.relationship('UserClasses', backref='class_obj', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Classes {self.classes}>'
