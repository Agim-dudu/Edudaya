from pathlib import Path
import re
import unittest

from app import app


ROOT = Path(__file__).resolve().parents[1]
LEARNING = ROOT / "resources" / "views" / "learning"


class BangunDatarFlowTests(unittest.TestCase):
    def test_low_triangle_material_matches_medium_with_animated_figures(self):
        for page in ("02.html", "03.html", "04.html", "05.html", "06.html"):
            low = (LEARNING / "low" / "bangun_datar" / page).read_text()
            medium = (LEARNING / "medium" / "bangun_datar" / page).read_text()

            def without_source_gallery(content):
                content = re.sub(
                    r"\s*<div class=\"source-gallery .*?</div>\s*</div>",
                    "",
                    content,
                    flags=re.S,
                )
                return content

            normalized_low = without_source_gallery(low)
            normalized_medium = without_source_gallery(medium)
            if page in ("02.html", "03.html", "04.html"):
                normalized_low = normalized_low.replace(
                    "/learning/low/bangun_datar/img/",
                    "/learning/medium/bangun_datar/img/",
                )
            normalized_low = normalized_low.replace(
                '<body class="low-level-material ', '<body class="', 1
            )
            normalized_low = re.sub(r"\n    <style>.*?</style>\n", "", normalized_low, count=1, flags=re.S)
            self.assertEqual(normalized_low, normalized_medium)
            self.assertIn("source-gallery", low)
            self.assertIn("source-gallery", medium)
            self.assertIn("triangle-drift", low)
            self.assertIn("prefers-reduced-motion: reduce", low)

        self.assertIn("Segitiga Sama Sisi", (LEARNING / "low" / "bangun_datar" / "02.html").read_text())
        self.assertIn("Segitiga Sama Kaki", (LEARNING / "low" / "bangun_datar" / "03.html").read_text())
        self.assertIn("Segitiga Sembarang", (LEARNING / "low" / "bangun_datar" / "04.html").read_text())
        for name in ("Persegi", "Persegi Panjang", "Jajar Genjang"):
            self.assertIn(name, (LEARNING / "low" / "bangun_datar" / "05.html").read_text())
        for name in ("Belah Ketupat", "Trapesium", "Layang-Layang"):
            self.assertIn(name, (LEARNING / "low" / "bangun_datar" / "06.html").read_text())

    def test_concept_page_is_shared(self):
        low = (LEARNING / "low" / "bangun_datar" / "01.html").read_text()
        for level in ("medium", "high"):
            page = (LEARNING / level / "bangun_datar" / "01.html").read_text()
            normalized = page.replace(
                f"/resources/views/learning/{level}/bangun_datar/img/",
                "/resources/views/learning/low/bangun_datar/img/",
            )
            normalized = re.sub(
                r"\s*<div class=\"source-gallery .*?</div>\s*</div>",
                "",
                normalized,
                flags=re.S,
            )
            shared_low = re.sub(
                r"\s*<div class=\"source-gallery .*?</div>\s*</div>",
                "",
                low,
                flags=re.S,
            )
            self.assertEqual(normalized, shared_low)
            if level == "medium":
                self.assertIn("source-gallery", page)

    def test_material_routes_follow_sections_to_quiz(self):
        rules = {rule.rule for rule in app.url_map.iter_rules()}
        for route in (
            "/learning/bangun_datar/<int:user_id>/<int:klasifikasi>",
            "/learning/bangun_datar/02/<int:user_id>/<int:klasifikasi>",
            "/learning/bangun_datar/03/<int:user_id>/<int:klasifikasi>",
            "/learning/bangun_datar/04/<int:user_id>/<int:klasifikasi>",
            "/learning/bangun_datar/05/<int:user_id>/<int:klasifikasi>",
            "/learning/bangun_datar/06/<int:user_id>/<int:klasifikasi>",
            "/quiz/bangun_datar/<int:user_id>/<int:klasifikasi>",
            "/quiz/bangun_datar/start/<int:user_id>/<int:klasifikasi>",
        ):
            self.assertIn(route, rules)

        low_page_2 = (LEARNING / "low" / "bangun_datar" / "02.html").read_text()
        low_page_3 = (LEARNING / "low" / "bangun_datar" / "03.html").read_text()
        low_page_4 = (LEARNING / "low" / "bangun_datar" / "04.html").read_text()
        self.assertIn("/learning/bangun_datar/03/{{ user_id }}/{{ klasifikasi }}", low_page_2)
        self.assertIn("/learning/bangun_datar/04/{{ user_id }}/{{ klasifikasi }}", low_page_3)
        self.assertIn("/learning/bangun_datar/05/{{ user_id }}/{{ klasifikasi }}", low_page_4)
        low_page_5 = (LEARNING / "low" / "bangun_datar" / "05.html").read_text()
        low_page_6 = (LEARNING / "low" / "bangun_datar" / "06.html").read_text()
        self.assertIn("/learning/bangun_datar/06/{{ user_id }}/{{ klasifikasi }}", low_page_5)
        self.assertIn("/quiz/bangun_datar/{{ user_id }}/{{ klasifikasi }}", low_page_6)
        for level in ("medium",):
            page_3 = (LEARNING / level / "bangun_datar" / "03.html").read_text()
            page_4 = (LEARNING / level / "bangun_datar" / "04.html").read_text()
            self.assertIn("/learning/bangun_datar/04/{{ user_id }}/{{ klasifikasi }}", page_3)
            self.assertIn("/learning/bangun_datar/05/{{ user_id }}/{{ klasifikasi }}", page_4)
            page_5 = (LEARNING / level / "bangun_datar" / "05.html").read_text()
            page_6 = (LEARNING / level / "bangun_datar" / "06.html").read_text()
            self.assertIn("/learning/bangun_datar/06/{{ user_id }}/{{ klasifikasi }}", page_5)
            self.assertIn("/quiz/bangun_datar/{{ user_id }}/{{ klasifikasi }}", page_6)

    def test_quiz_remains_level_specific(self):
        routes = (ROOT / "app" / "routes.py").read_text()
        for level in (0, 1, 2):
            self.assertIn(f"/api/bangun_datar/quiz/<int:user_id>/{level}", routes)
            start = (LEARNING / ("low", "medium", "high")[level] / "bangun_datar" / "quiz_start.html").read_text()
            self.assertIn(f"/api/bangun_datar/quiz/{{{{ user_id }}}}/{level}", start)

    def test_sidebar_exposes_topics_present_in_level_materials(self):
        sidebar = (LEARNING / "partial" / "sidebar.html").read_text()
        app.jinja_env.from_string(sidebar)
        self.assertIn("📖 Konsep Bangun Datar", sidebar)
        self.assertIn("🔺 Segitiga", sidebar)
        self.assertIn("🧩 Kuis", sidebar)
        self.assertIn("⬜ Segiempat", sidebar)
        self.assertIn(
            '/learning/bangun_datar/02/{{ current_user.id }}/{{ current_user.klasifikasi }}',
            sidebar,
        )

    def test_quadrilateral_example_answer_keys_match_documented_examples(self):
        expected = {
            "05.html": ("'pg-k1': 20", "'pp-l2': 8", "'jg-k1': 10", "'jg-l2': 6"),
            "06.html": ("'bk-k1': 20", "'tp-l1': 21", "'ll-l1': 6", "'ll-l2': 8"),
        }
        for page, values in expected.items():
            content = (LEARNING / "medium" / "bangun_datar" / page).read_text()
            for value in values:
                self.assertIn(value, content)


if __name__ == "__main__":
    unittest.main()
