from app import db
from datetime import datetime

class Token(db.Model):
    __tablename__ = 'tokens'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    token = db.Column(db.String(45), unique=True, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, token, expires_at=None):
        self.token = token
        self.expires_at = expires_at or datetime.utcnow()

    def __repr__(self):
        return f'<Token {self.token}>'
