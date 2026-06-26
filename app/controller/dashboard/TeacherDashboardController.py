import os
import secrets
import string
import json
from sqlalchemy import case
from app import db
from app.model import User, Classes, ClassTeachers, FinalResult, EvaluationResult, PretestResult, Score
from flask_login import current_user
from flask import abort, current_app, flash, redirect, url_for, request
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

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

        sudah_pretest = PretestResult.query.join(User).filter(
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

def get_final_analysis(class_id: int) -> list[dict]:
    results = (
        db.session.query(
            User.id.label('user_id'),
            User.full_name,
            PretestResult.answer_details.label('pretest_details'),
            EvaluationResult.answer_details.label('eval_details'),
            FinalResult.ai_analysis.label('final_analysis')
        )
        # Join ke tabel PretestResult
        .outerjoin(PretestResult, PretestResult.user_id == User.id)
        # Join ke tabel EvaluationResult
        .outerjoin(EvaluationResult, EvaluationResult.user_id == User.id)
        # Join ke tabel FinalResult
        .outerjoin(FinalResult, FinalResult.user_id == User.id)
        .filter(
            User.class_id == class_id,   # Filter sesuai id kelas
            User.level == 0,             # 0 = siswa
        )
        .order_by(
            # Urutkan: Siswa yang sudah punya final analysis ditaruh di atas
            case((FinalResult.ai_analysis == None, 1), else_=0).asc(),  
            User.full_name.asc(),
        )
        .all()
    )

    return [
        {
            'user_id'             : row.user_id,
            'full_name'           : row.full_name,
            # True jika kolom answer_detail di PretestResult tidak None / tidak kosong
            'pretest_done'        : row.pretest_details is not None,
            # True jika kolom answer_detail di EvaluationResult tidak None / tidak kosong
            'evaluation_done'     : row.eval_details is not None,
            # True jika kolom ai_analysis di FinalResult tidak None / tidak kosong
            'final_analysis_done' : row.final_analysis is not None,
        }
        for row in results
    ]

def get_student_final_analysis_detail(teacher_id, user_id):
    if teacher_id != current_user.id:
        abort(403)

    # 1. Validasi siswa dan kelas guru
    student = User.query.filter_by(id=user_id, level=0).first_or_404()
    teacher_class_ids = [ct.class_id for ct in current_user.teacher_classes]
    if student.class_id not in teacher_class_ids:
        abort(403)

    # 2. Ambil data murni dari FinalResult saja
    final_test = FinalResult.query.filter_by(user_id=user_id).first()
    if not final_test:
        return None

    # 3. Return data student dan ai_analysis saja
    return {
        'student':     student,
        'ai_analysis': json.loads(final_test.ai_analysis) if final_test.ai_analysis else None
    }

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
        if not students:
            continue

        student_ids = [s.id for s in students]
        all_scores = Score.query.filter(Score.user_id.in_(student_ids)).all()

        scores_by_user = {}
        all_chapters = set()
        for sc in all_scores:
            scores_by_user.setdefault(sc.user_id, []).append(sc)
            if sc.chapter:
                all_chapters.add(sc.chapter)
        total_bab = max(len(all_chapters), 1)

        student_list = []
        for s in students:
            user_scores = scores_by_user.get(s.id, [])
            quiz_val = None
            chapters_done = set()
            total_val = 0
            for sc in user_scores:
                if sc.score_type == 'quiz' and quiz_val is None:
                    quiz_val = sc.value
                if sc.chapter:
                    chapters_done.add(sc.chapter)
                total_val += sc.value

            student_list.append({
                'id': s.id,
                'full_name': s.full_name,
                'gender': s.gender,
                'pretest_done': s.pretest_result is not None,
                'quiz_score': quiz_val,
                'materi_selesai': len(chapters_done),
                'total_bab': total_bab,
                'total_score': total_val,
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
        return [], [], []

    class_ids = [ct.class_id for ct in teacher.teacher_classes]
    if not class_ids:
        return [], [], []

    all_student_ids = []
    for cid in class_ids:
        ids = [row[0] for row in User.query.filter_by(class_id=cid, level=0).with_entities(User.id).all()]
        all_student_ids.extend(ids)

    if not all_student_ids:
        return [], [], []

    chapters = db.session.query(Score.chapter).filter(
        Score.user_id.in_(all_student_ids),
        Score.chapter.isnot(None)
    ).distinct().order_by(Score.chapter).all()
    chapter_list = [row.chapter for row in chapters]
    material_keys = chapter_list
    material_labels = chapter_list

    all_scores = Score.query.filter(
        Score.user_id.in_(all_student_ids),
        Score.chapter.isnot(None),
        Score.score_type == 'quiz'
    ).all()

    scores_by_user = {}
    for sc in all_scores:
        scores_by_user.setdefault(sc.user_id, {})[sc.chapter] = sc.value

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
            user_scores = scores_by_user.get(s.id, {})
            scores_dict = {}
            total = 0
            count = 0
            for ch in chapter_list:
                val = user_scores.get(ch)
                scores_dict[ch] = val
                if val is not None:
                    total += val
                    count += 1
            avg = round(total / count) if count > 0 else 0
            student_grades.append({
                'id': s.id,
                'full_name': s.full_name,
                'pretest_done': s.pretest_result is not None,
                'scores': scores_dict,
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


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def teacher_profile(user_id):
    user = User.query.get_or_404(user_id)
    return user


def update_teacher_profile(user_id):
    if user_id != current_user.id:
        abort(403)

    user = User.query.get_or_404(user_id)

    if 'avatar' in request.files:
        file = request.files['avatar']
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                ext = filename.rsplit('.', 1)[-1].lower()
                project_root = os.path.dirname(current_app.root_path)
                upload_folder = os.path.join(project_root, 'resources', 'images', 'avatars')
                os.makedirs(upload_folder, exist_ok=True)
                new_filename = f"teacher_{user_id}.{ext}"
                file.save(os.path.join(upload_folder, new_filename))
                user.image = new_filename

    password = request.form.get('password', '').strip()
    password_confirm = request.form.get('password_confirm', '').strip()
    if password and password == password_confirm:
        user.set_password(password)
    elif password and password != password_confirm:
        flash("Password tidak cocok.", "danger")
        return redirect(url_for('teacher_profile_route', user_id=user_id))

    db.session.commit()
    flash("Profil berhasil diperbarui.", "success")
    return redirect(url_for('teacher_profile_route', user_id=user_id))