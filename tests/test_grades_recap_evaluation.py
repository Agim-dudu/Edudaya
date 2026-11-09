import json
import unittest
from types import SimpleNamespace

from app.controller.dashboard.TeacherDashboardController import _evaluation_score


class GradesRecapEvaluasiTests(unittest.TestCase):
    def test_evaluation_score_comes_from_pretest_and_final_improvement(self):
        pretest = SimpleNamespace(score=60)
        final = SimpleNamespace(ai_analysis=json.dumps({'peningkatan_skor': 25}))
        self.assertEqual(_evaluation_score(pretest, final), 85)

    def test_missing_or_invalid_analysis_has_no_evaluation_score(self):
        pretest = SimpleNamespace(score=60)
        self.assertIsNone(_evaluation_score(pretest, None))
        self.assertIsNone(_evaluation_score(pretest, SimpleNamespace(ai_analysis='invalid')))
        self.assertIsNone(_evaluation_score(pretest, SimpleNamespace(ai_analysis='{"peningkatan_skor": "20"}')))


if __name__ == '__main__':
    unittest.main()
