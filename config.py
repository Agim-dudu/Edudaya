import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    DATABASE_URL = os.environ.get("DATABASE_URL")
    HOST = os.environ.get("DB_HOST")
    PORT = os.environ.get("DB_PORT")
    DATABASE = os.environ.get("DB_DATABASE")
    USERNAME = os.environ.get("DB_USERNAME")
    PASSWORD = os.environ.get("DB_PASSWORD")

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET")

    # Secret Key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or f'mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = os.environ.get('SQLALCHEMY_RECORD_QUERIES', 'false').lower() == 'true'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', '280')),
        'pool_size': int(os.environ.get('DB_POOL_SIZE', '10')),
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', '20')),
        'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', '15')),
    }
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_SAMESITE = 'Lax'

    @classmethod
    def validate(cls):
        required = {
            'SECRET_KEY': cls.SECRET_KEY,
            'JWT_SECRET': cls.JWT_SECRET_KEY,
        }
        if not cls.DATABASE_URL:
            required.update({
                'DB_HOST': cls.HOST,
                'DB_PORT': cls.PORT,
                'DB_DATABASE': cls.DATABASE,
                'DB_USERNAME': cls.USERNAME,
            })
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(f"Konfigurasi wajib belum diisi: {', '.join(missing)}")
