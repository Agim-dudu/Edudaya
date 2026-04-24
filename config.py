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

    JWT_SECRET_KEY = str(os.environ.get("JWT_SECRET"))

    # Secret Key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
