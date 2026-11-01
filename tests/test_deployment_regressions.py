from pathlib import Path
from types import SimpleNamespace
import re
import unittest
from unittest.mock import patch

from app import app
import app.routes as routes
from app.controller import LearningController
from app.controller.dashboard import AdminDashboardController


ROOT = Path(__file__).resolve().parents[1]
VIEWS = ROOT / 'resources' / 'views'


class DeploymentRegressionTests(unittest.TestCase):
    def test_learning_assets_are_served_but_template_sources_are_blocked(self):
        with app.test_request_context(
            '/resources/views/learning/low/bangun_datar/img/rumah_banjar.jpg'
        ):
            self.assertIsNone(routes._hide_template_sources())
        with app.test_request_context(
            '/resources/views/learning/low/bangun_datar/learning-common.js'
        ):
            self.assertIsNone(routes._hide_template_sources())
        for path in (
            '/resources/views/learning/low/bangun_datar/01.html',
            '/resources/views/learning/low/bangun_datar/05.html.bak',
            '/resources/views',
        ):
            with self.subTest(path=path), app.test_request_context(path):
                self.assertEqual(routes._hide_template_sources(), ('Not Found', 404))

    def test_every_post_form_has_a_csrf_token(self):
        missing = []
        for path in VIEWS.rglob('*.html'):
            markup = path.read_text(errors='ignore')
            for match in re.finditer(r'<form\b[^>]*>', markup, re.I):
                if 'post' not in match.group(0).lower():
                    continue
                end = markup.find('</form>', match.end())
                body = markup[match.end():end if end != -1 else len(markup)]
                if 'csrf_token' not in body:
                    line = markup[:match.start()].count('\n') + 1
                    missing.append(f'{path.relative_to(ROOT)}:{line}')
        self.assertEqual(missing, [])

    def test_quiz_pages_do_not_reference_missing_stylesheet(self):
        for path in VIEWS.glob('learning/*/bangun_datar/quiz_start.html'):
            self.assertNotIn('css/style.css', path.read_text())

    def test_learning_sidebar_and_quiz_link_to_evaluation(self):
        sidebar = (VIEWS / 'learning' / 'partial' / 'sidebar.html').read_text()
        self.assertIn('/learning/evaluation/', sidebar)
        for path in VIEWS.glob('learning/*/bangun_datar/quiz.html'):
            self.assertIn('/learning/evaluation/', path.read_text())

    def test_evaluation_page_can_collect_answers(self):
        script = (ROOT / 'resources' / 'js' / 'pretest_question_handle.js').read_text()
        self.assertIn('function renderOptions', script)
        self.assertIn("classList.toggle('selected'", script)
        for path in VIEWS.glob('learning/*/evaluation/evaluation_start.html'):
            markup = path.read_text()
            self.assertIn('id="answerIsianBox"', markup)
            self.assertIn('id="optionsList"', markup)

    def test_unclassified_student_is_redirected_not_forbidden(self):
        user = SimpleNamespace(
            is_authenticated=True,
            id=12,
            level=0,
            klasifikasi=None,
            pretest_result=SimpleNamespace(ai_analysis='{}'),
        )
        with app.app_context(), patch.object(routes, 'current_user', user):
            with app.test_request_context('/learning/bangun_datar/12/0'):
                response = routes._block_student_if_waiting_analysis()
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard/student/12', response.headers['Location'])

    def test_learning_guard_returns_forbidden_status(self):
        user = SimpleNamespace(id=12)
        with app.app_context(), patch.object(LearningController, 'current_user', user):
            with app.test_request_context('/learning/bangun_datar/99/0'):
                response, status = LearningController._guard(99)
        self.assertEqual(status, 403)

    def test_teacher_detail_routes_handle_missing_analysis(self):
        source = (ROOT / 'app' / 'routes.py').read_text()
        self.assertEqual(source.count('    if not data:'), 2)
        self.assertIn("url_for('dashboard_result_final_analysis'", source)

    def test_ai_batch_redirects_to_an_existing_endpoint(self):
        source = (ROOT / 'app' / 'controller' / 'ArtificialController.py').read_text()
        self.assertNotIn("url_for('dashboard_result_analysis'", source)

    def test_deleting_teacher_removes_class_assignments_first(self):
        teacher = SimpleNamespace(id=5)
        with app.app_context(), \
                patch.object(AdminDashboardController.ClassTeachers, 'query') as query, \
                patch.object(AdminDashboardController.User, 'query') as user_query, \
                patch.object(AdminDashboardController.db.session, 'delete') as delete, \
                patch.object(AdminDashboardController.db.session, 'commit') as commit:
            user_query.get_or_404.return_value = teacher
            AdminDashboardController.delete_teacher(5)

        query.filter_by.assert_called_once_with(teacher_id=5)
        query.filter_by.return_value.delete.assert_called_once_with()
        delete.assert_called_once_with(teacher)
        commit.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
