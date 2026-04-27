from app import app, response, csrf
from app.decorator.utils import level_required
from app.controller import UserController, get_user_by_id
from flask import request, jsonify, render_template
from flask_login import current_user, login_required, logout_user
from flask_jwt_extended import jwt_required, get_jwt_identity


@app.route("/")
def index():
    return render_template("index.html")


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


@app.route("/dashboard_student/setting/<int:user_id>", methods=["GET", "POST"])
@login_required
@level_required(0)
def dashboard_student_setting(user_id):
    if user_id != current_user.id:
        return render_template("403.html")

    user = get_user_by_id(user_id)

    if request.method == "POST":
        full_name = request.form.get("full_name")
        nim = request.form.get("nim")
        email = request.form.get("email")
        new_password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            flash("Password dan Konfirmasi Password tidak cocok!", "danger")
            return render_template(
                "dashboard/student/setting.html", user=user, user_id=user_id
            )

        # Update data profil
        user.full_name = full_name
        user.nim_nip = nim
        user.email = email

        # Update password jika tidak kosong
        if new_password.strip():
            user.password = generate_password_hash(new_password)

        try:
            db.session.commit()
            flash("Profil berhasil diperbarui", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Gagal memperbarui profil: {str(e)}", "danger")

        return redirect(url_for("dashboard_student_setting", user_id=user.id))

    return render_template("dashboard/student/setting.html", user=user, user_id=user_id)


@app.route("/dashboard_student/guide/<int:user_id>", methods=["GET"])
@login_required
@level_required(0)
def dashboard_student_guide(user_id):
    if user_id != current_user.id:
        return render_template("403.html")

    return render_template("dashboard/student/guide.html")


# End Dashboard Students ======================================================================
