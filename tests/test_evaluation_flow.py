from pathlib import Path
import unittest

from unittest.mock import Mock, patch

from app import app, db
import app.controller.EvaluationController as evaluation


ROOT = Path(__file__).resolve().parents[1]


class EvaluationFlowTests(unittest.TestCase):
    def test_evaluation_uses_exact_pretest_question_bank(self):
        from app.controller.PretestController import QUESTIONS_PRETEST
        self.assertIs(evaluation.QUESTIONS_EVALUATION, QUESTIONS_PRETEST)
        self.assertEqual(len(evaluation.QUESTIONS_EVALUATION), 10)

    def test_evaluation_saves_free_text_once_without_literal_string_scoring(self):
        user = Mock(level=0, class_id=12, evaluation=0, klasifikasi=1)
        user.id = 7
        answers = {str(q["id"]): q["correct"] for q in evaluation.QUESTIONS_EVALUATION}

        with app.app_context(), app.test_request_context("/"):
            with patch.object(evaluation.User, "query") as user_query, \
                    patch.object(evaluation.EvaluationResult, "query") as result_query, \
                    patch.object(db.session, "add") as add, \
                    patch.object(db.session, "commit") as commit:
                user_query.get.return_value = user
                result_query.filter_by.return_value.first.side_effect = [None, object()]
                first = evaluation.save_evaluation({"answers": answers, "time_taken": 120}, user.id)
                second, status = evaluation.save_evaluation({"answers": answers}, user.id)

        self.assertEqual(first.json["status"], "success")
        self.assertEqual(status, 409)
        self.assertEqual(second.json["error"], "Evaluasi sudah dikirim.")
        self.assertEqual(add.call_count, 1)
        commit.assert_called_once()

    def test_all_evaluation_pages_collect_free_text(self):
        for path in (ROOT / "resources/views/learning").glob("*/evaluation/evaluation_start.html"):
            markup = path.read_text()
            self.assertIn('id="answerIsianBox"', markup)
            self.assertIn('duration: {{ sisa_detik | default(1200) }}', markup)



if __name__ == "__main__":
    unittest.main()
