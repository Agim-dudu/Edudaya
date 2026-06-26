from app import db
from datetime import datetime

# =========================================================================
# 2. MODEL CLASSES (Tabel Kelas)
# =========================================================================
class Classes(db.Model):
    __tablename__ = 'classes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(45), nullable=False)   
    school = db.Column(db.String(45), nullable=False) 
    token = db.Column(db.String(45), nullable=False, unique=True) 
    kkm = db.Column(db.Integer, nullable=False, default=75)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 🔄 RELASI ORM
    # 1. Hubungan Kelas ke Tabel Jembatan (Untuk melihat siapa saja guru di kelas ini)
    class_teachers = db.relationship('ClassTeachers', backref='class_obj', cascade='all, delete-orphan', lazy=True)
    
    # 2. Hubungan Kelas ke Siswa (Untuk melihat seluruh siswa di kelas ini)
    students = db.relationship('User', backref='student_class_obj', foreign_keys='User.class_id', lazy=True)

    def __repr__(self):
        return f'<Classes {self.name} - Token: {self.token}>'
