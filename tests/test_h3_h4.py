"""Isolated route/template regressions; never import the app or connect to MySQL.

Run: python -m unittest discover -s tests -v
"""
import ast
from functools import wraps
from html.parser import HTMLParser
from pathlib import Path
import secrets
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from flask import Flask
from flask_login import LoginManager, UserMixin, current_user, login_required
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]


def test_level_required(role):
    def decorate(function):
        @wraps(function)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.level != role:
                return 'forbidden', 403
            return function(*args, **kwargs)
        return wrapped
    return decorate


class TestUser(UserMixin):
    def __init__(self, identity, level):
        self.id = identity
        self.level = level


class Teacher(UserMixin):
    def __init__(self, identity, level, classes):
        self.id = identity
        self.level = level
        self.teacher_classes = [SimpleNamespace(class_id=c) for c in classes]


class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SECRET_KEY=secrets.token_hex(32))
        users = {
            1: Teacher(1, 1, [10, 20]),
            2: Teacher(2, 1, [30]),
            3: Teacher(3, 1, []),
            4: Teacher(4, 0, [10]),
            5: Teacher(5, 2, [10]),
            6: Teacher(6, 1, [10]),
        }
        manager = LoginManager(self.app)
        manager.user_loader(lambda identity: users.get(int(identity)))
        self.app.add_url_rule('/', 'index', lambda: 'home')
        self.readers = {kind: Mock(return_value=[]) for kind in ('pretest', 'final')}
        namespace = {
            'app': self.app, 'current_user': current_user,
            'login_required': login_required,
            'render_template': lambda template, **context: template,
            **{f'get_{kind}_analysis': reader for kind, reader in self.readers.items()},
        }
        # Use the actual role decorator and both actual route bodies/decorators.
        exec(compile((ROOT / 'app/decorator/utils.py').read_text(), 'utils.py', 'exec'), namespace)
        tree = ast.parse((ROOT / 'app/routes.py').read_text())
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name in ('dashboard_result_pretest_analysis',
                                       'dashboard_result_final_analysis')]
        exec(compile(ast.Module(body=functions, type_ignores=[]), 'routes.py', 'exec'), namespace)
        self.client = self.app.test_client()

    def test_access_matrix(self):
        cases = [
            (1, 1, 10, 200), (1, 1, 20, 200), (6, 6, 10, 200),
            (2, 2, 10, 403), (2, 1, 10, 403), (1, 2, 10, 403),
            (3, 3, 10, 403), (1, 1, 999, 403),
            (4, 4, 10, 302), (5, 5, 10, 302), (None, 1, 10, 401),
        ]
        for kind, reader in self.readers.items():
            for actor, url_user, class_id, expected in cases:
                with self.subTest(kind=kind, actor=actor, url_user=url_user, class_id=class_id):
                    reader.reset_mock()
                    with self.client.session_transaction() as session:
                        session.clear()
                        if actor is not None:
                            session['_user_id'] = str(actor)
                            session['_fresh'] = True
                    response = self.client.get(
                        f'/teacher/result/{kind}/analysis/{url_user}/{class_id}')
                    self.assertEqual(response.status_code, expected)
                    if expected == 200:
                        reader.assert_called_once_with(class_id)
                    else:
                        reader.assert_not_called()


class Tags(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.tags = []
        self.feed(markup)

    def handle_starttag(self, tag, attributes):
        self.tags.append((tag, dict(attributes)))


class AdminXssTests(unittest.TestCase):
    def test_names_remain_data_in_all_confirmation_forms(self):
        env = Environment(loader=FileSystemLoader(ROOT / 'resources/views'),
                          autoescape=select_autoescape(['html']))
        env.globals.update(
            url_for=lambda endpoint, **kw: '/resources/' + kw['filename']
            if endpoint == 'static' else '/' + endpoint,
            current_user=SimpleNamespace(id=1), csrf_token=lambda: 'test-csrf',
            get_flashed_messages=lambda **kw: [],
        )
        payloads = ["O'Connor & kelas 6", "'+(globalThis.XSS_EXECUTED=true)+'",
                    '\"><img src=x onerror="globalThis.XSS_EXECUTED=true">',
                    '</script><script>globalThis.XSS_EXECUTED=true</script>']
        for section, collection, prefix in (
            ('siswa', 'siswa', 'Hapus siswa '), ('guru', 'teachers', 'Hapus guru '),
            ('kelas', 'classes', 'Hapus kelas '),
            ('token', 'tokens', 'Generate ulang token untuk '),
        ):
            for name in payloads:
                with self.subTest(section=section, name=name):
                    row = dict(id=7, full_name=name, name=name, kelas=name,
                               username='student', gender='L', school='school',
                               avg_score=80, progress=10, teachers='teacher',
                               token='token', kkm=75, student_count=1, is_active=True)
                    markup = env.get_template(f'dashboard/admin/{section}/index.html').render(
                        **{collection: [row]})
                    tags = Tags(markup).tags
                    forms = [attrs for tag, attrs in tags if tag == 'form' and 'data-confirm' in attrs]
                    self.assertEqual(len(forms), 1)
                    self.assertEqual(forms[0]['data-confirm'], prefix + name + '?')
                    self.assertNotIn('onsubmit', forms[0])
                    self.assertFalse(any('XSS_EXECUTED' in value for _, attrs in tags
                                         for key, value in attrs.items()
                                         if key.startswith('on') and value))
                    self.assertNotIn('<script>globalThis.XSS_EXECUTED', markup)
                    self.assertTrue(any(tag == 'script' and attrs.get('src') ==
                                        '/resources/js/admin_confirm.js' for tag, attrs in tags))


class QuizEndpointAuthenticationTests(unittest.TestCase):
    def test_quiz_submit_routes_require_authenticated_student_role(self):
        tree = ast.parse((ROOT / 'app/routes.py').read_text())
        routes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                  and node.name.startswith('api_bangun_datar_quiz_submit_')]

        for route in routes:
            with self.subTest(route=route.name):
                decorators = [ast.unparse(decorator) for decorator in route.decorator_list]
                self.assertIn('login_required', decorators)
                source = ast.unparse(route)
                self.assertIn('current_user.level != 0', source)


class AdminDashboardTests(unittest.TestCase):
    def test_dashboard_replaces_mockups_with_real_score_data_and_profile_form(self):
        env = Environment(loader=FileSystemLoader(ROOT / 'resources/views'),
                          autoescape=select_autoescape(['html']))
        env.globals.update(
            url_for=lambda endpoint, **kw: '/' + endpoint,
            current_user=SimpleNamespace(id=9, full_name='Admin <One>', username='admin.one'),
            csrf_token=lambda: 'test-csrf',
            get_flashed_messages=lambda **kw: [],
        )
        markup = env.get_template('dashboard/admin/dashboard.html').render(
            amount_classes=1, amount_student=1, amount_teacher=1, active_tokens=1,
            top_students=[{'full_name': '<img src=x onerror=alert(1)>', 'average_score': 80}],
            admin_scores=[(SimpleNamespace(chapter='Bab 1', score_type='quiz', value=80,
                                           created_at=None),
                           SimpleNamespace(full_name='Student', username='student'),
                           SimpleNamespace(name='Class A'))],
        )
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', markup)
        self.assertIn('name="full_name"', markup)
        self.assertIn('name="username"', markup)
        self.assertIn('/admin_scores_export', markup)
        self.assertIn('Student', markup)
        for fake in ('Ahmad Fauzi', 'SDN Banjarmasin 1', 'EDU-4A21',
                     'Aktivitas Belajar (7 Hari', 'admin@edudaya.id'):
            self.assertNotIn(fake, markup)

    def test_profile_update_route_authorization_validation_and_success(self):
        from flask import redirect, request, url_for
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY=secrets.token_hex(32))
        manager = LoginManager(app)
        users = {9: TestUser(9, 2)}
        manager.user_loader(lambda identity: users.get(int(identity)))
        manager.login_view = 'index'
        app.add_url_rule('/', 'index', lambda: 'home')
        app.add_url_rule('/dashboard/admin/<int:user_id>', 'dashboard_admin', lambda user_id: 'dashboard')
        calls = []
        namespace = {
            'app': app, 'current_user': current_user, 'login_required': login_required,
            'level_required': test_level_required,
            'render_template': lambda template, **context: template,
            'redirect': redirect, 'url_for': url_for, 'request': request,
            'flash': lambda *args: None,
            'update_admin_profile': lambda *args: (calls.append(args) or (True, 'ok')),
        }
        tree = ast.parse((ROOT / 'app/routes.py').read_text())
        route = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name == 'admin_profile_update')
        exec(compile(ast.Module(body=[route], type_ignores=[]), 'routes.py', 'exec'), namespace)
        app.add_url_rule('/admin/profile/update/<int:user_id>', 'admin_profile_update',
                         namespace['admin_profile_update'], methods=['POST'])
        client = app.test_client()

        with client.session_transaction() as session:
            session['_user_id'] = '9'
            session['_fresh'] = True
        denied = client.post('/admin/profile/update/8', data={'full_name': 'x', 'username': 'x'})
        self.assertEqual(denied.status_code, 403)
        with client.session_transaction() as session:
            session['_user_id'] = '9'
            session['_fresh'] = True
        ok = client.post('/admin/profile/update/9', data={
            'full_name': 'Admin Baru', 'username': 'admin.baru', 'password': '',
            'password_confirm': '',
        })
        self.assertEqual(ok.status_code, 302)
        self.assertEqual(calls, [(9, 'Admin Baru', 'admin.baru', None, '')])

    def test_admin_score_export_role_and_excel_formula_guard(self):
        from flask import Response
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY=secrets.token_hex(32))
        users = {9: TestUser(9, 2), 4: TestUser(4, 0), 1: TestUser(1, 1)}
        manager = LoginManager(app)
        manager.user_loader(lambda identity: users.get(int(identity)))
        manager.login_view = 'index'
        app.add_url_rule('/', 'index', lambda: 'home')
        score = SimpleNamespace(chapter='Bab 1', score_type='quiz', correct=1, incorrect=0,
                                value=100, created_at=None)
        student = SimpleNamespace(full_name='=2+2', username='@student')
        kelas = SimpleNamespace(name=' =1+1', school='School')
        namespace = {
            'app': app, 'current_user': current_user, 'login_required': login_required,
            'level_required': test_level_required, 'io': __import__('io'),
            'Response': Response,
            'workbook_bytes': __import__('app.excel_export', fromlist=['workbook_bytes']).workbook_bytes,
            'get_admin_scores': lambda: [(score, student, kelas)],
        }
        tree = ast.parse((ROOT / 'app/routes.py').read_text())
        nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in ('admin_scores_export', '_excel_safe', '_excel_response')]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), 'routes.py', 'exec'), namespace)
        app.add_url_rule('/admin/scores/export.xlsx', 'admin_scores_export',
                         namespace['admin_scores_export'], methods=['GET'])
        client = app.test_client()
        guest = client.get('/admin/scores/export.xlsx')
        self.assertEqual(guest.status_code, 302)
        with client.session_transaction() as session:
            session['_user_id'] = '4'
            session['_fresh'] = True
        self.assertEqual(client.get('/admin/scores/export.xlsx').status_code, 403)
        with client.session_transaction() as session:
            session['_user_id'] = '9'
            session['_fresh'] = True
        response = client.get('/admin/scores/export.xlsx')
        self.assertEqual(response.status_code, 200)
        from zipfile import ZipFile
        import io
        with ZipFile(io.BytesIO(response.get_data())) as archive:
            sheet = archive.read('xl/worksheets/sheet1.xml').decode()
        self.assertIn("'=2+2", sheet)
        self.assertIn("'@student", sheet)
        self.assertIn("' =1+1", sheet)


if __name__ == '__main__':
    unittest.main()
