from app.model import User, Classes

def get_amount_student_all(user_id=None):
    return User.query.filter(User.level == 0).count()

def get_amount_teacher_all(user_id=None):
    return User.query.filter(User.level == 1).count()

def get_amount_classes_all():
    return Classes.query.count()
