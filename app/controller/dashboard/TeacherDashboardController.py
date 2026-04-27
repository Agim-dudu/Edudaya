from app.model import * 
from sqlalchemy import func, desc, literal_column, case
from sqlalchemy.orm import aliased
from sqlalchemy.sql import over 
from app import db

def get_amount_student_by_teacher(user_id):

    teacher = User.query.get(user_id)
    if not teacher:
        return 0

    class_ids = [rel.class_token for rel in teacher.class_relation]

    amount_student = (
        User.query
        .join(UserClasses)
        .filter(
            User.level == 0,
            UserClasses.class_token.in_(class_ids)
        )
        .distinct()
        .count()
    )

    return amount_student


def get_amount_class_by_teacher(user_id):
    # Ambil objek guru berdasarkan user_id
    teacher = User.query.get(user_id)
    if not teacher:
        return 0

    # Hitung jumlah kelas yang diampu
    amount_class = len(teacher.class_relation)
    
    return amount_class