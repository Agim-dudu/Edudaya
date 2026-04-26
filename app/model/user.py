from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(50), unique=False, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    token = db.Column(db.String(45), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(255), nullable=True, default='default.jpg')
    recommendation = db.Column(db.String(255), nullable=True)
    star = db.Column(db.Integer, nullable=True)
    progress = db.Column(db.Integer, nullable=True)
    last_submission = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        # Method to hash the password
        self.password = generate_password_hash(password)

    def check_password(self, password):
        # Method to check hashed password
        return check_password_hash(self.password, password)
    

