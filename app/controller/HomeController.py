from app.model import User, Classes

def get_amount_student(user_id=None):
    return User.query.filter(User.level == 0).count()

def get_amount_teacher(user_id=None):
    return User.query.filter(User.level == 1).count()

def get_amount_classes():
    return Classes.query.count()
