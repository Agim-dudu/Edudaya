from app import app, response, csrf
from app.controller import UserController
from flask import request, jsonify,render_template
from flask_login import current_user, login_required, logout_user
from flask_jwt_extended import jwt_required, get_jwt_identity

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/list_course', methods=['GET'])
def list_course():
    return render_template('list_course.html')

@app.route('/instruction', methods=['GET'])
def instruction():
    return render_template('instruction.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        return UserController.login_siswa()
    
@app.route("/logout")
@login_required
def logout():
    return UserController.logout()

@app.route('/register', methods=['GET'])
def register_page():
	return render_template("register.html")

# @app.route('/createadmin', methods=['POST'])
# def admins():
#     return UserController.CreateAdmin()

@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return response.success(current_user, 'Sukses')

# @app.route('/login', methods=['POST'])
# def logins():
#     return UserController.login()