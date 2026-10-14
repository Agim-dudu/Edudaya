from pathlib import Path
from types import SimpleNamespace
import unittest

from jinja2 import Environment, select_autoescape


ROOT = Path(__file__).resolve().parents[1]


class QuizAnswerKeyPrivacyTests(unittest.TestCase):
    def test_answer_keys_are_rendered_only_for_teacher_and_admin_preview(self):
        env = Environment(autoescape=select_autoescape(["html"]))
        env.globals.update(
            csrf_token=lambda: "test-csrf",
            url_for=lambda *args, **kwargs: "/resources/test.css",
            current_user=SimpleNamespace(id=12, klasifikasi=0),
        )

        templates = [
            ROOT / "resources" / "views" / "learning" / level / subject / "quiz_start.html"
            for level in ("low", "medium", "high")
            for subject in ("bangun_datar",)
        ]
        for path in templates:
            template = env.from_string(path.read_text())
            for level in (0, 1, 2):
                with self.subTest(template=path, level=level):
                    html = template.render(
                        user_level=level,
                        user_id=12,
                        user_kkm=75,
                        sisa_detik=900,
                        klasifikasi=0,
                    )
                    self.assertEqual("const kunciPreview" in html, level != 0)


if __name__ == "__main__":
    unittest.main()
