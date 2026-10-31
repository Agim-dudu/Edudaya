from pathlib import Path
import re
import unittest

from app import app


ROOT = Path(__file__).resolve().parents[1]
LEARNING = ROOT / 'resources' / 'views' / 'learning'
LEVELS = {'low': 0, 'medium': 1, 'high': 2}
PAGES = {
    'low': ('01.html', '01_d.html', '02.html', '03.html', '04.html',
            '05.html', '05_2.html', '05_3.html', '06.html', '06_2.html', '06_3.html'),
    'medium': ('01.html', '02.html', '03.html'),
    'high': ('01.html', '02.html', '03.html'),
}


class BangunDatarFlowTests(unittest.TestCase):
    def test_material_pages_exist_for_each_classification(self):
        for level, pages in PAGES.items():
            for page in pages:
                with self.subTest(level=level, page=page):
                    self.assertTrue((LEARNING / level / 'bangun_datar' / page).is_file())
            for page in ('quiz.html', 'quiz_start.html'):
                self.assertTrue((LEARNING / level / 'bangun_datar' / page).is_file())

    def test_learning_and_quiz_routes_exist(self):
        rules = {rule.rule for rule in app.url_map.iter_rules()}
        for path in ('/learning/bangun_datar/<int:user_id>/<int:klasifikasi>',
                     '/quiz/bangun_datar/<int:user_id>/<int:klasifikasi>',
                     '/quiz/bangun_datar/start/<int:user_id>/<int:klasifikasi>'):
            self.assertIn(path, rules)
        for page in PAGES['low'][1:]:
            suffix = page.removesuffix('.html')
            self.assertIn(f'/learning/bangun_datar/{suffix}/<int:user_id>/<int:klasifikasi>', rules)
        for level in LEVELS.values():
            self.assertIn(f'/api/bangun_datar/quiz/<int:user_id>/{level}', rules)

    def test_quiz_submit_urls_match_each_classification(self):
        for level, number in LEVELS.items():
            page = (LEARNING / level / 'bangun_datar' / 'quiz_start.html').read_text()
            self.assertRegex(page, rf"fetch\('/api/bangun_datar/quiz/\{{\{{ (?:user_id|current_user.id) \}}\}}/{number}'")
            self.assertIn('X-CSRFToken', page)

    def test_low_navigation_references_existing_pages(self):
        sidebar = (LEARNING / 'partial' / 'sidebar.html').read_text()
        app.jinja_env.from_string(sidebar)
        for page in PAGES['low'][1:]:
            suffix = page.removesuffix('.html')
            self.assertIn(f'/learning/bangun_datar/{suffix}/', sidebar)

    def test_medium_and_high_navigation_end_at_quiz(self):
        for level in ('medium', 'high'):
            page = (LEARNING / level / 'bangun_datar' / '03.html').read_text()
            self.assertIn('/quiz/bangun_datar/', page)

    def test_quiz_answer_keys_match_frontend_preview(self):
        routes = (ROOT / 'app' / 'routes.py').read_text()
        for level, number in LEVELS.items():
            page = (LEARNING / level / 'bangun_datar' / 'quiz_start.html').read_text()
            preview = re.search(r'const kunciPreview = \{([^}]+)\}', page)
            self.assertIsNotNone(preview)
            answers = re.findall(r'(\d+):"(soal\d+-[a-d])"', preview.group(1))
            self.assertEqual(len(answers), 10)
            for question, answer in answers:
                self.assertIn(f'"{question}": "{answer}"', routes)


if __name__ == '__main__':
    unittest.main()
