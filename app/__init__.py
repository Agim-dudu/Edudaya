from flask import Flask, session, request
from config import Config
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import current_user
from flask_jwt_extended import JWTManager
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from flask_seeder import FlaskSeeder, Seeder

app = Flask(__name__,
            template_folder='../resources/views',  # Folder untuk template HTML
            static_folder='../resources')  # Folder untuk file statis seperti CSS, JS, dan gambar

application = app

app.config.from_object(Config)
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
migrate = Migrate(app, db)

# Inisialisasi Flask-Seeder
seeder = FlaskSeeder(app, db)
seeder.init_app(app, db)

# Pengaturan session cookie dan waktu kadaluarsa
app.config['SESSION_COOKIE_NAME'] = 'your_session_cookie_name'  # Nama cookie sesi
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Durasi sesi tetap aktif selama 2hari


jwt = JWTManager(app)

# Inisialisasi Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from app.model import Classes, User, Token

# from app.model.scores import Score
# from app.model.class_users import UserClasses

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from app import routes
