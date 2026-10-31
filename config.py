import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    HOST = os.environ.get("DB_HOST")
    PORT = os.environ.get("DB_PORT")
    DATABASE = os.environ.get("DB_DATABASE")
    USERNAME = os.environ.get("DB_USERNAME")
    PASSWORD = os.environ.get("DB_PASSWORD")

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET")

    # Secret Key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_SAMESITE = 'Lax'

    @classmethod
    def validate(cls):
        missing = [name for name, value in {
            'SECRET_KEY': cls.SECRET_KEY,
            'JWT_SECRET': cls.JWT_SECRET_KEY,
            'DB_HOST': cls.HOST,
            'DB_PORT': cls.PORT,
            'DB_DATABASE': cls.DATABASE,
            'DB_USERNAME': cls.USERNAME,
        }.items() if not value]
        if missing:
            raise RuntimeError(f"Konfigurasi wajib belum diisi: {', '.join(missing)}")
