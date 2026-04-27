from app.model import *
from sqlalchemy import func, desc, literal_column, case
from sqlalchemy.orm import aliased
from sqlalchemy.sql import over 
from app import db

def get_user_by_id(user_id):
    user = User.query.get(user_id)
    return user