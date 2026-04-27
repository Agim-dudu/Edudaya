from app.model import * 
from sqlalchemy import func, desc, literal_column, case
from sqlalchemy.orm import aliased
from sqlalchemy.sql import over 
from app import db

def get_amount_student(user_id=None):
    return User.query.filter(User.level == 0).count()

def get_amount_teacher(user_id=None):
    return User.query.filter(User.level == 1).count()

def get_amount_classes():
    return Classes.query.count()
