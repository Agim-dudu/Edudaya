from app import app, response, csrf
from app.decorator.utils import level_required
from app.controller import *
from flask import request, jsonify, render_template
from flask_login import current_user, login_required, logout_user
from flask_jwt_extended import jwt_required, get_jwt_identity


@app.route("/")
def index():
    
    amount_classes=get_amount_classes()
    amount_teacher=get_amount_teacher()
    amount_student=get_amount_student()
    
    print(amount_student)
    
    return render_template("index.html", ac=amount_classes, at=amount_teacher, ast=amount_student)


@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


@app.route("/list_course", methods=["GET"])
def list_course():
    return render_template("list_course.html")


@app.route("/instruction", methods=["GET"])
def instruction():
    return render_template("instruction.html")


# Login Handle ===============================================================================


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        return UserController.login_siswa()


@app.route("/login_teacher", methods=["GET", "POST"])
def login_teacher():
    if request.method == "GET":
        return render_template("login_teacher.html")
    else:
        return UserController.login_teacher()


@app.route("/login_admin", methods=["GET", "POST"])
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

# Halaman Khusus Dashboard Students ==============================================================


@app.route("/dashboard_student/<int:user_id>", methods=["GET"])
@login_required
@level_required(0)
def dashboard_student(user_id):
    if user_id != current_user.id:
        return render_template("403.html")

    user = get_user_by_id(user_id)
    # top_scores = get_top_quiz_scores_per_chapter(user_id)

    if user:
        return render_template("dashboard/student/dashboard.html", user=user)
    else:
        return "User tidak ditemukan", 404


# End Dashboard Students =========================================================================


# Halaman Khusus Dashboard Guru ==================================================================


@app.route("/dashboard_teacher/<int:user_id>", methods=["GET"])
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
    )


# End Dashboard Guru ===========================================================================

# Halaman Khusus Dashboard Guru ==================================================================


@app.route("/dashboard_admin/<int:user_id>", methods=["GET"])
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
