from pathlib import Path
import unittest

from app import app


ROOT = Path(__file__).resolve().parents[1]


class LegacyLearningModulesRemovedTests(unittest.TestCase):
    def test_bab1_and_bab2_routes_are_removed(self):
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        self.assertFalse(any("bab1" in rule or "bab2" in rule for rule in rules))
        self.assertIn("/learning/bangun_datar/<int:user_id>/<int:klasifikasi>", rules)
        self.assertIn("/quiz/bangun_datar/<int:user_id>/<int:klasifikasi>", rules)

    def test_only_active_learning_modules_remain_in_level_folders(self):
        learning_root = ROOT / "resources" / "views" / "learning"
        for level in ("low", "medium", "high"):
            level_root = learning_root / level
            self.assertFalse((level_root / "bab1").exists())
            self.assertFalse((level_root / "bab2").exists())
            self.assertTrue((level_root / "bangun_datar" / "01.html").is_file())
            self.assertTrue((level_root / "evaluation" / "evaluation.html").is_file())

    def test_evaluation_and_course_preview_no_longer_link_to_legacy_material(self):
        legacy_references = []
        for path in (ROOT / "resources").rglob("*"):
            if path.is_file() and path.suffix in {".html", ".py", ".js"}:
                content = path.read_text(errors="ignore")
                if "/learning/bab1" in content or "/learning/bab2" in content:
                    legacy_references.append(str(path.relative_to(ROOT)))
        self.assertEqual(legacy_references, [])


if __name__ == "__main__":
    unittest.main()
