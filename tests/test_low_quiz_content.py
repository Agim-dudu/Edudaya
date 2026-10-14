"""Check the low-level Bangun Datar quiz contract without importing the app."""
import ast
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ROUTE = ROOT / 'app/routes.py'
QUIZ = ROOT / 'resources/views/learning/low/bangun_datar/quiz_start.html'


class LowQuizContentTests(unittest.TestCase):
    def test_ten_questions_and_matching_server_teacher_keys(self):
        template = QUIZ.read_text()
        route_tree = ast.parse(ROUTE.read_text())
        route = next(node for node in route_tree.body if isinstance(node, ast.FunctionDef)
                     and node.name == 'api_bangun_datar_quiz_submit_low')
        server_keys = next(ast.literal_eval(node.value) for node in ast.walk(route)
                           if isinstance(node, ast.Assign)
                           and any(isinstance(target, ast.Name) and target.id == 'kunci'
                                   for target in node.targets))
        preview_source = re.search(r'const kunciPreview = (\{[^;]+\});', template).group(1)
        preview_keys = ast.literal_eval(preview_source)

        expected = {
            1: 'soal1-b', 2: 'soal2-a', 3: 'soal3-c', 4: 'soal4-b', 5: 'soal5-d',
            6: 'soal6-a', 7: 'soal7-c', 8: 'soal8-b', 9: 'soal9-d', 10: 'soal10-c',
        }
        self.assertEqual(server_keys, {str(k): v for k, v in expected.items()})
        self.assertEqual(preview_keys, expected)

        for number, answer in expected.items():
            with self.subTest(question=number):
                question = re.search(
                    rf'<div id="soal-{number}".*?(?=<!-- SOAL {number + 1} -->|<!-- Navigation buttons -->)',
                    template, re.DOTALL).group(0)
                self.assertIn(f'id="{answer}"', question)

        self.assertIn('Belah ketupat', template)
        self.assertIn('Jajar genjang', template)
        self.assertIn('trapesium', template)
        self.assertIn('keliling persegi', template)
        self.assertIn('luasnya', template)


if __name__ == '__main__':
    unittest.main()
