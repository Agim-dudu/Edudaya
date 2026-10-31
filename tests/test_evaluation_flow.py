import ast
from datetime import datetime, timedelta
from pathlib import Path
import unittest

from unittest.mock import Mock, patch

from app import app, db
import app.controller.EvaluationController as evaluation


ROOT = Path(__file__).resolve().parents[1]


class EvaluationFlowTests(unittest.TestCase):
    def test_evaluation_answer_keys_match_correct_answers(self):
        expected = {
            1: "b",
            2: "c",
            3: "c",
            4: "c",
            5: "c",
            6: "c",
            7: "d",
            8: "c",
            9: "c",
            10: "b",
        }

        self.assertEqual(
            {question["id"]: question["correct"] for question in evaluation.QUESTIONS_EVALUATION},
            expected,
        )
        for question in evaluation.QUESTIONS_EVALUATION:
            option_ids = {option["id"] for option in question["options"]}
            self.assertIn(question["correct"], option_ids)

    def test_saved_evaluation_score_refreshes_retry_timestamp(self):
        user = Mock(level=0, class_id=12, evaluation=0, klasifikasi=1)
        user.id = 7
        existing_result = Mock()
        existing_score = Mock(
            correct=0,
            incorrect=10,
            value=0,
            created_at=datetime.utcnow() - timedelta(minutes=10),
        )

        with app.app_context(), app.test_request_context("/"):
            with patch.object(evaluation.User, "query") as user_query, \
                    patch.object(evaluation.EvaluationResult, "query") as result_query, \
                    patch.object(evaluation.Score, "query") as score_query, \
                    patch.object(db.session, "commit"):
                user_query.get.return_value = user
                result_query.filter_by.return_value.first.return_value = existing_result
                score_query.filter_by.return_value.first.return_value = existing_score

                response = evaluation.save_evaluation(
                    {
                        "answers": {
                            str(question["id"]): question["correct"]
                            for question in evaluation.QUESTIONS_EVALUATION
                        },
                        "time_taken": 120,
                    },
                    user.id,
                )

        self.assertEqual(response.json["status"], "success")
        self.assertEqual(existing_score.value, 100)
        self.assertGreater(existing_score.created_at, datetime.utcnow() - timedelta(seconds=5))

    def test_evaluation_lookup_uses_the_same_chapter_as_saved_scores(self):
        config_tree = ast.parse((ROOT / "app/controller/LearningController.py").read_text())
        save_tree = ast.parse((ROOT / "app/controller/EvaluationController.py").read_text())

        config_assignment = next(
            node for node in config_tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "BAB_CONFIG" for target in node.targets)
        )
        config = ast.literal_eval(config_assignment.value)
        saved_chapter = next(
            keyword.value.value
            for node in ast.walk(save_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Score"
            for keyword in node.keywords
            if keyword.arg == "chapter" and isinstance(keyword.value, ast.Constant)
        )

        self.assertEqual(config["evaluation"]["score_chapter"], saved_chapter)
        self.assertIn(
            '_get_last_score(user_id, "evaluation", cfg["score_chapter"])',
            (ROOT / "app/controller/LearningController.py").read_text(),
        )


if __name__ == "__main__":
    unittest.main()
