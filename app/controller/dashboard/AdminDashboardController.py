import secrets
import string
from app import db
from app.model import User, Classes, ClassTeachers
from flask import flash
from werkzeug.security import generate_password_hash

def get_amount_student_all(user_id=None):
    return User.query.filter(User.level == 0).count()

def get_amount_teacher_all(user_id=None):
    return User.query.filter(User.level == 1).count()

def get_amount_classes_all():
    return Classes.query.count()

def _generate_token():
    suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f'#CLS-{suffix}'

def get_all_classes():
    classes = Classes.query.all()
    result = []
    for c in classes:
        student_count = User.query.filter(User.level == 0, User.class_id == c.id).count()
        teachers = ClassTeachers.query.filter_by(class_id=c.id).all()
        teacher_names = []
        for t in teachers:
            teacher = User.query.get(t.teacher_id)
            if teacher:
                teacher_names.append(teacher.full_name)
        result.append({
            'id': c.id,
            'name': c.name,
            'school': c.school,
            'token': c.token,
            'kkm': c.kkm,
            'teachers': ', '.join(teacher_names) if teacher_names else '-',
            'student_count': student_count,
        })
    return result

def get_kelas_by_id(kelas_id):
    c = Classes.query.get_or_404(kelas_id)
    teachers = ClassTeachers.query.filter_by(class_id=c.id).all()
    teacher_ids = [t.teacher_id for t in teachers]
    return {
        'id': c.id,
        'name': c.name,
        'school': c.school,
        'token': c.token,
        'kkm': c.kkm,
        'teacher_ids': teacher_ids,
    }

def create_kelas(name, school, kkm, teacher_ids=None):
    token = _generate_token()
    while Classes.query.filter_by(token=token).first():
        token = _generate_token()
    kelas = Classes(name=name, school=school, kkm=kkm, token=token)
    db.session.add(kelas)
    db.session.flush()
    if teacher_ids:
        for tid in teacher_ids:
            db.session.add(ClassTeachers(class_id=kelas.id, teacher_id=tid))
    db.session.commit()
    return kelas


def update_kelas(kelas_id, name, school, kkm, teacher_ids=None):
    c = Classes.query.get_or_404(kelas_id)
    c.name = name
    c.school = school
    c.kkm = kkm
    if teacher_ids is not None:
        ClassTeachers.query.filter_by(class_id=kelas_id).delete()
        for tid in teacher_ids:
            db.session.add(ClassTeachers(class_id=kelas_id, teacher_id=tid))
    db.session.commit()
    return c

def delete_kelas(kelas_id):
    c = Classes.query.get_or_404(kelas_id)
    db.session.delete(c)
    db.session.commit()

def get_all_siswa():
    students = User.query.filter(User.level == 0).all()
    result = []
    for s in students:
        kelas_name = s.student_class_obj.name if s.student_class_obj else '-'
        school_name = s.student_class_obj.school if s.student_class_obj else '-'
        total_scores = sum(sc.value for sc in s.scores if sc.value > 0)
        count_scores = sum(1 for sc in s.scores if sc.value > 0)
        avg_score = round(total_scores / count_scores) if count_scores > 0 else 0
        result.append({
            'id': s.id,
            'username': s.username,
            'full_name': s.full_name,
            'gender': s.gender,
            'kelas': kelas_name,
            'school': school_name,
            'avg_score': avg_score,
            'progress': s.progress or 0,
        })
    return result

def get_siswa_by_id(siswa_id):
    s = User.query.get_or_404(siswa_id)
    kelas_name = s.student_class_obj.name if s.student_class_obj else '-'
    return {
        'id': s.id,
        'username': s.username,
        'full_name': s.full_name,
        'gender': s.gender,
        'class_id': s.class_id,
        'kelas_name': kelas_name,
        'progress': s.progress or 0,
    }

def create_siswa(username, full_name, password, gender, class_id):
    existing = User.query.filter_by(username=username).first()
    if existing:
        return None
    user = User(
        username=username,
        full_name=full_name,
        level=0,
        gender=gender,
        class_id=class_id if class_id else None,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user

def update_siswa(siswa_id, username, full_name, gender, class_id, password=None):
    s = User.query.get_or_404(siswa_id)
    existing = User.query.filter(User.username == username, User.id != siswa_id).first()
    if existing:
        return None
    s.username = username
    s.full_name = full_name
    s.gender = gender
    s.class_id = class_id if class_id else None
    if password:
        s.set_password(password)
    db.session.commit()
    return s

def delete_siswa(siswa_id):
    s = User.query.get_or_404(siswa_id)
    db.session.delete(s)
    db.session.commit()

def get_all_tokens():
    classes = Classes.query.all()
    result = []
    for c in classes:
        teachers = ClassTeachers.query.filter_by(class_id=c.id).all()
        teacher_names = []
        for t in teachers:
            teacher = User.query.get(t.teacher_id)
            if teacher:
                teacher_names.append(teacher.full_name)
        result.append({
            'id': c.id,
            'token': c.token,
            'kelas': c.name,
            'school': c.school,
            'teachers': ', '.join(teacher_names) if teacher_names else '-',
            'is_active': c.is_active,
        })
    return result

def regenerate_token(kelas_id):
    c = Classes.query.get_or_404(kelas_id)
    token = _generate_token()
    while Classes.query.filter_by(token=token).first():
        token = _generate_token()
    c.token = token
    db.session.commit()
    return token

def get_all_teachers():
    return User.query.filter(User.level == 1).all()


def get_teacher_by_id(teacher_id):
    t = User.query.get_or_404(teacher_id)
    return {
        'id': t.id,
        'username': t.username,
        'full_name': t.full_name,
        'gender': t.gender,
    }


def create_teacher(username, full_name, password, gender):
    existing = User.query.filter_by(username=username).first()
    if existing:
        return None
    user = User(
        username=username,
        full_name=full_name,
        level=1,
        gender=gender,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def update_teacher(teacher_id, username, full_name, gender, password=None):
    t = User.query.get_or_404(teacher_id)
    existing = User.query.filter(User.username == username, User.id != teacher_id).first()
    if existing:
        return None
    t.username = username
    t.full_name = full_name
    t.gender = gender
    if password:
        t.set_password(password)
    db.session.commit()
    return t


def delete_teacher(teacher_id):
    t = User.query.get_or_404(teacher_id)
    db.session.delete(t)
    db.session.commit()


def activate_token(kelas_id):
    c = Classes.query.get_or_404(kelas_id)
    c.is_active = True
    db.session.commit()

def deactivate_token(kelas_id):
    c = Classes.query.get_or_404(kelas_id)
    c.is_active = False
    db.session.commit()
