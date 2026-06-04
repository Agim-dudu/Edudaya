from app import app
from app.controller import *
from app.decorator.utils import level_required
from flask_login import current_user, login_required
from app.controller.PretestController import QUESTIONS_PRETEST
from flask import Flask, render_template, request, redirect, url_for


@app.route("/")
def index():
    
    amount_classes=get_amount_classes()
    amount_teacher=get_amount_teacher()
    amount_student=get_amount_student()

    from app.controller.LearningController import MATERIAL_CATALOG
    from app.model import User, LearningProgress
    from app import db
    
    total_materi = len(MATERIAL_CATALOG)
    
    top_students = db.session.query(
        User.full_name, User.class_id,
        db.func.coalesce(db.func.sum(LearningProgress.score), 0).label('total_score')
    ).outerjoin(LearningProgress, LearningProgress.user_id == User.id
    ).filter(User.level == 0
    ).group_by(User.id
    ).order_by(db.func.sum(LearningProgress.score).desc()
    ).limit(5).all()
    
    leaderboard = []
    for rank, row in enumerate(top_students, 1):
        kelas_name = ''
        if row.class_id:
            from app.model import Classes
            k = Classes.query.get(row.class_id)
            if k:
                kelas_name = k.name
        leaderboard.append({
            'rank': rank,
            'name': row.full_name,
            'kelas': kelas_name,
            'score': int(row.total_score),
        })
    
    return render_template("index.html", ac=amount_classes, at=amount_teacher, ast=amount_student, total_materi=total_materi, leaderboard=leaderboard)

@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")

@app.route("/list-course", methods=["GET"])
def list_course():
    return render_template("list_course.html")

@app.route("/instruction", methods=["GET"])
def instruction():
    return render_template("instruction.html")

# Login Handle ====================================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        return UserController.login_siswa()

@app.route("/login/teacher", methods=["GET", "POST"])
def login_teacher():
    if request.method == "GET":
        return render_template("login_teacher.html")
    else:
        return UserController.login_teacher()

@app.route("/login/admin", methods=["GET", "POST"])
def login_admin():
    if request.method == "GET":
        return render_template("login_admin.html")
    else:
        return UserController.login_admin()

@app.route("/logout")
@login_required
def logout():
    return UserController.logout()

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        return UserController.register()

# End Login Handle ===============================================================================


# Pretest Handle ===============================================================================

@app.route("/pretest/<int:user_id>", methods=["GET"])
@login_required
def pretest(user_id):
    if user_id != current_user.id:
        return render_template("403.html")
    
    return render_template("pretest/preparation.html", user_id=user_id)

@app.route("/pretest/start/<int:user_id>", methods=["GET"])
@login_required
def pretest_start(user_id):
    if user_id != current_user.id:
        return render_template("403.html")
    
    safe_questions = [
        {k: v for k, v in q.items() if k != "correct"}
        for q in QUESTIONS_PRETEST
    ]
    return render_template("pretest/pretest_start.html", questions=safe_questions, user_id=user_id)

@app.route("/pretest/submit/<int:user_id>", methods=["POST"])
@login_required
def submit_pretest(user_id):
    if user_id != current_user.id:
        return render_template("403.html")

    data = request.get_json()

    return save_pretest(data, user_id)

@app.route("/api/pretest/analyze/<int:user_id>", methods=["POST"])
@login_required
def api_analyze_pretest(user_id):
    if user_id != current_user.id:
        return render_template("403.html")

    data = request.get_json()

    return analyze_pretest(data)

@app.route("/pretest/finish/<int:user_id>", methods=["GET"])
@login_required
def finish_pretest(user_id):
    if user_id != current_user.id:
        return render_template("403.html")

    # Jika akses diizinkan, render halaman ini
    return render_template("pretest/finish_pretest.html", user_id=user_id)

# End Pretest Handle ===============================================================================


# Routing Learning Bab 1 ====================================================================================

@app.route("/learning/medium/1/1/<int:user_id>", methods=["GET"])
@login_required
def learning_medium_chapter1_1(user_id):
    if user_id != current_user.id:
        return render_template("403.html")

    return render_template("learning/medium/bab1/01.html", user_id=user_id)

@app.route("/learning/medium/1/2/<int:user_id>", methods=["GET"])
@login_required
def learning_medium_chapter1_2(user_id):
    if user_id != current_user.id:
        return render_template("403.html")

    return render_template("learning/medium/bab1/02.html", user_id=user_id)

@app.route("/learning/medium/1/3/<int:user_id>", methods=["GET"])
@login_required
def learning_medium_chapter1_3(user_id):
    if user_id != current_user.id:
        return render_template("403.html")

    return render_template("learning/medium/bab1/03.html", user_id=user_id)

@app.route("/learning/medium/1/4/<int:user_id>", methods=["GET"])
@login_required
def learning_medium_chapter1_4(user_id):
    if user_id != current_user.id:
        return render_template("403.html")

    return render_template("learning/medium/bab1/04.html", user_id=user_id)

@app.route("/learning/medium/1/quiz/<int:user_id>", methods=["GET"])
@login_required
def learning_medium_chapter1_quiz(user_id):
    if user_id != current_user.id:
        return render_template("403.html")

    return render_template("learning/medium/bab1/quiz.html", user_id=user_id)

# End Routing Learning Bab 1 ====================================================================================


# Halaman Khusus Dashboard Students ==============================================================

@app.route("/dashboard/student/<int:user_id>", methods=["GET"])
@login_required
@level_required(0)
def dashboard_student(user_id):

    user = get_user_by_id(user_id)
    stats = get_student_dashboard_stats(user_id)

    return render_template(
        "dashboard/student/dashboard.html",
        user=user,
        user_id=user_id,
        stats=stats
    )

@app.route("/api/learning/progress/save/<int:user_id>", methods=["POST"])
@login_required
def api_save_progress(user_id):
    return save_learning_progress(user_id)

@app.route("/api/learning/progress/get/<int:user_id>", methods=["GET"])
@login_required
def api_get_progress(user_id):
    return get_learning_progress(user_id)

@app.route("/api/learning/progress/all/<int:user_id>", methods=["GET"])
@login_required
def api_get_all_progress(user_id):
    return get_all_progress(user_id)

@app.route("/grades/student/<int:user_id>", methods=["GET"])
@login_required
@level_required(0)
def student_grades(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403

    user = get_user_by_id(user_id)
    stats = get_student_dashboard_stats(user_id)

    return render_template(
        "dashboard/student/grades.html",
        user=user,
        user_id=user_id,
        stats=stats
    )

@app.route("/profile/student/<int:user_id>", methods=["GET"])
@login_required
@level_required(0)
def student_profile(user_id):

    data = show_student_ai_analysis(user_id)
    user = get_user_by_id(user_id)
    print(data)

    return render_template(
        'dashboard/student/student_profile.html',
        user=user,
        user_id=user_id,
        student=data['student'],
        ai_analysis=data['ai_analysis'],
    )
    
@app.route('/profile/student/update/<int:user_id>', methods=['POST'])
@login_required
@level_required(0)
def update_profile_route(user_id):

    update_student_profile(user_id)
    
    return redirect(request.referrer)

# End Dashboard Students =========================================================================


# Halaman Khusus Dashboard Guru ==================================================================


@app.route("/dashboard/teacher/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def dashboard_teacher(user_id):
    # Cegah akses user lain
    if user_id != current_user.id:
        return render_template("403.html"), 403

    # Ambil jumlah siswa
    amount_student = get_amount_student_by_teacher(user_id)
    amount_class = get_amount_class_by_teacher(user_id)

    return render_template(
        'dashboard/teacher/dashboard.html',
        amount_student=amount_student,
        amount_class=amount_class,
        user_id=user_id
    )
    
@app.route("/teacher/analysis/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def dashboard_analysis(user_id):
    # Cegah akses user lain
    if user_id != current_user.id:
        return render_template("403.html"), 403
    
    get_kelas_pretest = get_kelas_pretest_by_guru(user_id)

    return render_template(
        'dashboard/teacher/analysis.html',
        user_id=user_id,
        list_class=get_kelas_pretest
    )

@app.route("/teacher/result/analysis/<int:teacher_id>/student/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def dashboard_student_ai_analysis(teacher_id, user_id):
    if teacher_id != current_user.id:
        return render_template("403.html"), 403

    data = get_student_ai_analysis_detail(teacher_id, user_id)

    if data is None:
        return redirect(request.referrer or url_for('dashboard_result_analysis',
                                                     user_id=teacher_id,
                                                     class_id=0))

    return render_template(
        'dashboard/teacher/detail_result_analysis.html',
        student=data['student'],
        score=data['score'],
        correct=data['correct'],
        total=data['total'],
        time_taken=data['time_taken'],
        topic_scores=data['topic_scores'],
        answer_details=data['answer_details'],
        ai_analysis=data['ai_analysis'],
        teacher_id=teacher_id,
    )
   
@app.route("/teacher/result/analysis/<int:user_id>/<int:class_id>", methods=["GET"])
@login_required
@level_required(1)
def dashboard_result_analysis(user_id, class_id):
    
    pretest_analysis = get_pretest_analysis(class_id)

    return render_template(
        'dashboard/teacher/result_analysis.html',
        class_id=class_id,
        user_id=user_id,
        pretest_analysis=pretest_analysis
    )
   
@app.route("/teacher/batch/analyze/<int:teacher_id>/<int:class_id>", methods=["POST"])
@login_required
@level_required(1)
def dashboard_teacher_batch_analyze(teacher_id, class_id):
    return batch_analyze_pretest_logic(teacher_id, class_id)

@app.route("/teacher/grades/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def teacher_grades(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403

    recap, material_labels, material_keys = get_grades_recap(user_id)

    return render_template(
        'dashboard/teacher/grades.html',
        user_id=user_id,
        recap=recap,
        material_labels=material_labels,
        material_keys=material_keys
    )

@app.route("/teacher/students/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def teacher_students(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403

    students_data = get_students_by_teacher(user_id)

    return render_template(
        'dashboard/teacher/students.html',
        user_id=user_id,
        students_data=students_data
    )

@app.route("/teacher/classes/<int:user_id>", methods=["GET"])
@login_required
@level_required(1)
def my_classes(user_id):
    if user_id != current_user.id:
        return render_template("403.html"), 403

    my_classes_list = get_my_classes(user_id)

    return render_template(
        'dashboard/teacher/my_classes.html',
        user_id=user_id,
        my_classes=my_classes_list
    )

@app.route("/teacher/classes/create/<int:teacher_id>", methods=["POST"])
@login_required
@level_required(1)
def create_class_route(teacher_id):
    return create_class(teacher_id)

@app.route("/teacher/classes/edit/<int:teacher_id>/<int:class_id>", methods=["POST"])
@login_required
@level_required(1)
def edit_class_route(teacher_id, class_id):
    return edit_class(teacher_id, class_id)

# End Dashboard Guru ===========================================================================


# Halaman Khusus Dashboard Guru ==================================================================


@app.route("/dashboard/admin/<int:user_id>", methods=["GET"])
@login_required
@level_required(2)
def dashboard_admin(user_id):
    # Cegah akses user lain
    if user_id != current_user.id:
        return render_template("403.html"), 403

    # Ambil jumlah siswa
    amount_student = get_amount_student_all()
    amount_teacher = get_amount_teacher_all()
    amount_classes = get_amount_classes_all()
    
    print(amount_classes)

    return render_template(
        'dashboard/admin/dashboard.html',
        amount_student=amount_student,
        amount_teacher=amount_teacher,
        amount_classes=amount_classes
    )

# End Dashboard Guru ===========================================================================
