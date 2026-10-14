import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
QUIZ_ROUTE_NAMES = (
    "api_bangun_datar_quiz_submit_low",
    "api_bangun_datar_quiz_submit_medium",
    "api_bangun_datar_quiz_submit_high",
)


class QuizBestScoreTests(unittest.TestCase):
    def test_lower_or_equal_attempt_does_not_insert_duplicate_score(self):
        tree = ast.parse((ROOT / "app/routes.py").read_text())
        functions = {
            node.name: node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name in QUIZ_ROUTE_NAMES
        }
        self.assertEqual(set(functions), set(QUIZ_ROUTE_NAMES))

        for name, function in functions.items():
            with self.subTest(route=name):
                existing_branch = next(
                    node for node in ast.walk(function)
                    if isinstance(node, ast.If)
                    and isinstance(node.test, ast.Name)
                    and node.test.id == "existing_score"
                )
                update_branch = next(
                    node for node in existing_branch.body
                    if isinstance(node, ast.If)
                    and isinstance(node.test, ast.Compare)
                    and ast.unparse(node.test) == "score > existing_score.value"
                )
                self.assertTrue(any(
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add"
                    for node in ast.walk(ast.Module(body=existing_branch.orelse, type_ignores=[]))
                ))
                self.assertEqual(len(update_branch.body), 3)


if __name__ == "__main__":
    unittest.main()
