from app import app, response
from app.controller import UserController
from flask import request, jsonify,render_template
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

@app.route('/login', methods=['POST'])
def logins():
    return UserController.login()

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