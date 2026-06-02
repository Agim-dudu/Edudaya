from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# =========================================================================
# 1. MODEL USER (Menampung Admin, Guru, dan Siswa)
# =========================================================================
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    
    # Hak Akses: 0 = Siswa, 1 = Guru, 2 = Admin
    level = db.Column(db.Integer, nullable=False, default=0) 
    gender = db.Column(db.String(5), nullable=False)
    image = db.Column(db.String(255), nullable=True, default='default.jpg')
    
    # Fitur Akademik Siswa
    pretest = db.Column(db.Integer, nullable=False, default=0)
    star = db.Column(db.Integer, nullable=True, default=0)
    progress = db.Column(db.Integer, nullable=True, default=0)
    last_submission = db.Column(db.DateTime, nullable=True)
    
    # 🔗 KUNCI SISWA: 1 Siswa hanya boleh masuk 1 kelas (One-to-Many langsung)
    # Diisi ID kelas jika Siswa. Jika Guru/Admin nilainya NULL.
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id', ondelete='SET NULL'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 🔄 RELASI ORM
    # 1. Hubungan Guru ke Tabel Jembatan (Untuk melihat daftar kelas yang dia ajar)
    teacher_classes = db.relationship('ClassTeachers', backref='teacher_obj', lazy=True)
    
    # 2. Hubungan Siswa ke Hasil Pretest (One-to-One)
    pretest_result = db.relationship('PretestResult', backref='user', uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        role = "Siswa" if self.level == 0 else "Guru" if self.level == 1 else "Admin"
        return f'<User {self.username} ({role})>'

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    

