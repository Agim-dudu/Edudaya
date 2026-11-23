from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app import app, db
from app.controller.dashboard import StudentDashboardController as dashboard


class StudentDashboardQueryTests(unittest.TestCase):
    def test_overview_uses_one_aggregate_query_for_classmate_scores(self):
        current_student = SimpleNamespace(id=10, class_id=5, star=2)
        classmates = [
            SimpleNamespace(id=10, full_name="A Student", star=2),
            SimpleNamespace(id=11, full_name="B Student", star=1),
            SimpleNamespace(id=12, full_name="C Student", star=0),
        ]
        own_scores = [
            SimpleNamespace(chapter="Bangun Datar", correct=8, incorrect=2, value=70, created_at=None),
            SimpleNamespace(chapter="Bab 1", correct=9, incorrect=1, value=90, created_at=None),
        ]
        average_rows = [
            SimpleNamespace(user_id=10, average_score=80),
            SimpleNamespace(user_id=11, average_score=95),
        ]

        with app.app_context(), \
                patch.object(dashboard.User, "query") as user_query, \
                patch.object(dashboard.Score, "query") as score_query, \
                patch.object(db.session, "query") as aggregate_query:
            user_query.get.return_value = current_student
            user_query.filter_by.return_value.all.return_value = classmates
            score_query.filter_by.return_value.all.return_value = own_scores
            aggregate_query.return_value.filter.return_value.group_by.return_value.all.return_value = average_rows

            overview = dashboard.get_student_overview_stats(10)

        self.assertEqual(overview["peringkat"], 2)
        self.assertEqual(overview["total_kelas"], 3)
        self.assertEqual(
            overview["leaderboard"],
            [
                {"full_name": "B Student", "is_me": False, "score": 95},
                {"full_name": "A Student", "is_me": True, "score": 80},
                {"full_name": "C Student", "is_me": False, "score": None},
            ],
        )
        aggregate_query.assert_called_once()
        score_query.filter_by.assert_called_once_with(user_id=10)


if __name__ == "__main__":
    unittest.main()
