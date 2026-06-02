from app import db
from datetime import datetime

# =========================================================================
# TABEL PENGHUBUNG (JEMBATAN): GURU MENGAMPIR/MEMILIKI KELAS (Many-to-Many)
# =========================================================================
class ClassTeachers(db.Model):
    __tablename__ = 'class_teachers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ClassTeachers teacher_id={self.teacher_id}, class_id={self.class_id}>'
