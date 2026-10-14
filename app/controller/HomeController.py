from app import db
from app.model import User, Classes, Score

# Three learning topics are currently available: Bangun Datar, Bab 1, and Bab 2.
MATERIAL_TOPICS = ('Bangun Datar', 'Bab 1', 'Bab 2')


def get_total_materi():
    return len(MATERIAL_TOPICS)


def get_amount_student(user_id=None):
    return User.query.filter(User.level == 0).count()

def get_amount_teacher(user_id=None):
    return User.query.filter(User.level == 1).count()

def get_amount_classes():
    return Classes.query.count()


def get_home_leaderboard(limit=5):
    """Return students with saved scores, ordered by their average score."""
    rows = (
        db.session.query(
            User.id,
            User.full_name,
            Classes.name.label('class_name'),
            db.func.avg(Score.value).label('average_score'),
        )
        .join(Score, Score.user_id == User.id)
        .outerjoin(Classes, Classes.id == User.class_id)
        .filter(User.level == 0)
        .group_by(User.id, User.full_name, Classes.name)
        .order_by(db.func.avg(Score.value).desc(), User.full_name.asc())
        .limit(limit)
        .all()
    )

    return [
        {
            'id': row.id,
            'name': row.full_name,
            'kelas': row.class_name,
            'score': round(row.average_score),
            'rank': index,
        }
        for index, row in enumerate(rows, start=1)
    ]
