import secrets
import string
from app import db
from app.model import User, Classes, ClassTeachers, PretestResult, LearningProgress
from app.controller.LearningController import MATERIAL_CATALOG
from flask_login import current_user
from flask import flash, redirect, url_for, request

def _generate_token():
    suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f'#CLS-{suffix}'


def get_amount_student_by_teacher(user_id):
    teacher = User.query.get(user_id)
    if not teacher or teacher.level != 1:
        return 0

    class_ids = [rel.class_id for rel in teacher.teacher_classes]

    if not class_ids:
        return 0

    amount_student = (
        User.query
        .filter(
            User.level == 0,
            User.class_id.in_(class_ids)
        )
        .count()
    )

    return amount_student


def get_amount_class_by_teacher(user_id):
    teacher = User.query.get(user_id)
    if not teacher or teacher.level != 1:
        return 0

    amount_class = len(teacher.teacher_classes)
    return amount_class


def get_my_classes(user_id):
    teacher = User.query.get(user_id)
    if not teacher or teacher.level != 1:
        return []

    classes = []
    for rel in teacher.teacher_classes:
        kelas = rel.class_obj
        if not kelas:
            continue

        total_siswa = User.query.filter(
            User.level == 0,
            User.class_id == kelas.id
        ).count()

        sudah_pretest = PretestResult.query.join(
            User, PretestResult.user_id == User.id
        ).filter(
            User.class_id == kelas.id,
            User.level == 0
        ).count()

        classes.append({
            'id': kelas.id,
            'name': kelas.name,
            'school': kelas.school,
            'token': kelas.token,
            'kkm': kelas.kkm,
            'total_siswa': total_siswa,
            'sudah_pretest': sudah_pretest,
        })

    return classes


def create_class(teacher_id):
    if teacher_id != current_user.id:
        flash("Akses ditolak.", "danger")
        return redirect(url_for('my_classes', user_id=teacher_id))

    name = request.form.get('name', '').strip()
    school = request.form.get('school', '').strip()
    kkm_str = request.form.get('kkm', '75').strip()

    if not name or not school:
        flash("Nama kelas dan sekolah wajib diisi.", "danger")
        return redirect(url_for('my_classes', user_id=teacher_id))

    try:
        kkm = int(kkm_str)
    except ValueError:
        kkm = 75

    token = _generate_token()
    while Classes.query.filter_by(token=token).first():
        token = _generate_token()

    kelas = Classes(name=name, school=school, kkm=kkm, token=token)
    db.session.add(kelas)
    db.session.flush()

    bridge = ClassTeachers(teacher_id=teacher_id, class_id=kelas.id)
    db.session.add(bridge)
    db.session.commit()

    flash(f"Kelas '{name}' berhasil dibuat. Token: {token}", "success")
    return redirect(url_for('my_classes', user_id=teacher_id))


def edit_class(teacher_id, class_id):
    if teacher_id != current_user.id:
        flash("Akses ditolak.", "danger")
        return redirect(url_for('my_classes', user_id=teacher_id))

    teacher_class_ids = [ct.class_id for ct in current_user.teacher_classes]
    if class_id not in teacher_class_ids:
        flash("Kelas bukan wewenang Anda.", "danger")
        return redirect(url_for('my_classes', user_id=teacher_id))

    kelas = Classes.query.get(class_id)
    if not kelas:
        flash("Kelas tidak ditemukan.", "danger")
        return redirect(url_for('my_classes', user_id=teacher_id))

    name = request.form.get('name', '').strip()
    school = request.form.get('school', '').strip()
    kkm_str = request.form.get('kkm', '75').strip()

    if not name or not school:
        flash("Nama kelas dan sekolah wajib diisi.", "danger")
        return redirect(url_for('my_classes', user_id=teacher_id))

    try:
        kkm = int(kkm_str)
    except ValueError:
        kkm = 75

    kelas.name = name
    kelas.school = school
    kelas.kkm = kkm
    db.session.commit()

    flash(f"Kelas '{name}' berhasil diperbarui.", "success")
    return redirect(url_for('my_classes', user_id=teacher_id))


def get_students_by_teacher(teacher_id):
    teacher = User.query.get(teacher_id)
    if not teacher or teacher.level != 1:
        return []

    class_ids = [ct.class_id for ct in teacher.teacher_classes]
    if not class_ids:
        return []

    classes_data = []
    for cid in class_ids:
        kelas = Classes.query.get(cid)
        if not kelas:
            continue
        students = User.query.filter_by(class_id=cid, level=0).order_by(User.full_name).all()
        student_list = []
        for s in students:
            pretest = s.pretest_result
            quiz = LearningProgress.query.filter_by(user_id=s.id, material_key='medium_1_quiz').first()
            quiz_completed = quiz.completed if quiz else False
            bab_count = 1 if quiz_completed else 0
            total_score = sum(r.score for r in s.learning_progress)
            student_list.append({
                'id': s.id,
                'full_name': s.full_name,
                'gender': s.gender,
                'pretest_done': s.pretest == 1,
                'quiz_score': quiz.score if quiz else None,
                'materi_selesai': bab_count,
                'total_bab': 1,
                'total_score': total_score,
            })
        classes_data.append({
            'class_id': kelas.id,
            'class_name': kelas.name,
            'school': kelas.school,
            'students': student_list,
        })

    return classes_data


def get_grades_recap(teacher_id):
    teacher = User.query.get(teacher_id)
    if not teacher or teacher.level != 1:
        return []

    material_keys = []
    material_labels = []
    for bab in MATERIAL_CATALOG:
        seq = 1
        for item in bab['materials']:
            material_keys.append(item['key'])
            if item['key'].endswith('_quiz'):
                material_labels.append(f"Kuis B{bab['bab_key'].split('_')[-1]}")
            else:
                material_labels.append(f"L{seq}")
                seq += 1

    recap = []
    for ct in teacher.teacher_classes:
        kelas = ct.class_obj
        if not kelas:
            continue
        students = User.query.filter_by(class_id=kelas.id, level=0).order_by(User.full_name).all()
        if not students:
            continue

        student_grades = []
        for s in students:
            progress_map = {r.material_key: r for r in s.learning_progress}
            scores = {}
            total = 0
            count = 0
            for key in material_keys:
                p = progress_map.get(key)
                scores[key] = p.score if p else None
                if p:
                    total += p.score
                    count += 1
            avg = round(total / count) if count > 0 else 0
            student_grades.append({
                'id': s.id,
                'full_name': s.full_name,
                'pretest_done': s.pretest == 1,
                'scores': scores,
                'total': total,
                'avg': avg,
            })

        recap.append({
            'class_id': kelas.id,
            'class_name': kelas.name,
            'school': kelas.school,
            'students': student_grades,
        })

    return recap, material_labels, material_keys