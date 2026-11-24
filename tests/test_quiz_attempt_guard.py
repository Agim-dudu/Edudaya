from datetime import datetime, timedelta, timezone
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import app, db
import app.routes as routes
from app.routes import _consume_quiz_attempt
from flask import session


class QuizAttemptGuardTests(unittest.TestCase):
    def test_started_attempt_can_be_consumed_once(self):
        with app.test_request_context('/'):
            session['quiz_start_time_bangun_datar'] = datetime.now(timezone.utc).isoformat()
            self.assertTrue(_consume_quiz_attempt('quiz_start_time_bangun_datar'))
            self.assertFalse(_consume_quiz_attempt('quiz_start_time_bangun_datar'))

    def test_expired_attempt_is_rejected_and_consumed(self):
        with app.test_request_context('/'):
            session['quiz_start_time_evaluation'] = (
                datetime.now(timezone.utc) - timedelta(minutes=31)
            ).isoformat()
            self.assertFalse(_consume_quiz_attempt('quiz_start_time_evaluation'))
            self.assertNotIn('quiz_start_time_evaluation', session)

    def test_evaluation_attempt_matches_its_thirty_minute_timer(self):
        with app.test_request_context('/'):
            session['quiz_start_time_evaluation'] = (
                datetime.now(timezone.utc) - timedelta(minutes=26)
            ).isoformat()
            self.assertTrue(_consume_quiz_attempt('quiz_start_time_evaluation'))

    def test_auto_submit_is_accepted_just_after_timer_expires(self):
        with app.test_request_context('/'):
            session['quiz_start_time_bangun_datar'] = (
                datetime.now(timezone.utc) - timedelta(seconds=902)
            ).isoformat()
            self.assertTrue(_consume_quiz_attempt('quiz_start_time_bangun_datar'))

    def test_invalid_attempt_timestamp_is_rejected(self):
        with app.test_request_context('/'):
            session['quiz_start_time_bangun_datar'] = 'not-a-timestamp'
            self.assertFalse(_consume_quiz_attempt('quiz_start_time_bangun_datar'))
            self.assertNotIn('quiz_start_time_bangun_datar', session)

    def test_quiz_api_rejects_submission_without_started_attempt(self):
        user = SimpleNamespace(id=12, level=0, klasifikasi=0)
        with app.app_context(), patch.object(routes, 'current_user', user):
            with patch.object(db.session, 'add') as add, patch.object(db.session, 'commit') as commit:
                with app.test_request_context('/api/bangun_datar/quiz/12/0', method='POST', json={'jawaban': {}}):
                    response, status = routes.api_bangun_datar_quiz_submit_low.__wrapped__(12)
                self.assertEqual(status, 409)
                add.assert_not_called()
                commit.assert_not_called()

    def test_quiz_api_rejects_another_classification(self):
        user = SimpleNamespace(id=12, level=0, klasifikasi=0)
        with app.app_context(), patch.object(routes, 'current_user', user):
            with patch.object(db.session, 'add') as add, patch.object(db.session, 'commit') as commit:
                with app.test_request_context('/api/bangun_datar/quiz/12/2', method='POST', json={'jawaban': {}}):
                    session['quiz_start_time_bangun_datar'] = datetime.now(timezone.utc).isoformat()
                    response, status = routes.api_bangun_datar_quiz_submit_high.__wrapped__(12)
                self.assertEqual(status, 403)
                add.assert_not_called()
                commit.assert_not_called()

    def test_learning_url_rejects_another_classification(self):
        user = SimpleNamespace(is_authenticated=True, id=12, level=0, klasifikasi=0)
        with app.app_context(), patch.object(routes, 'current_user', user):
            with app.test_request_context('/learning/bangun_datar/12/2'):
                response, status = routes._block_student_if_waiting_analysis()
                self.assertEqual(status, 403)

    def test_pretest_retry_after_saved_result_returns_success(self):
        user = SimpleNamespace(id=12, level=0, pretest_result=object())
        with app.app_context(), patch.object(routes, 'current_user', user):
            with patch.object(routes, 'save_pretest') as save:
                with app.test_request_context('/pretest/submit/12', method='POST', json={'answers': {}}):
                    response = routes.submit_pretest.__wrapped__(12)
                self.assertEqual(response.json['status'], 'success')
                self.assertIn('/dashboard/student/12', response.json['redirect_url'])
                save.assert_not_called()

    def test_evaluation_retry_returns_saved_result(self):
        user = SimpleNamespace(id=12, level=0, evaluation_result=object(), klasifikasi=1)
        with app.app_context(), patch.object(routes, 'current_user', user):
            with patch.object(routes, 'save_evaluation') as save:
                with app.test_request_context('/evaluation/submit/12', method='POST', json={'answers': {}}):
                    response = routes.submit_evaluation.__wrapped__(12)
                self.assertEqual(response.json['status'], 'success')
                self.assertIn('/learning/evaluation/12/1', response.json['redirect_url'])
                save.assert_not_called()

    def test_evaluation_submit_consumes_attempt_only_after_success(self):
        user = SimpleNamespace(id=12, level=0, evaluation_result=None, klasifikasi=1)
        with app.app_context(), patch.object(routes, 'current_user', user):
            with patch.object(routes, 'save_evaluation') as save:
                save.return_value = routes.jsonify({'status': 'success', 'redirect_url': '/done'})
                with app.test_request_context('/evaluation/submit/12', method='POST', json={'answers': {}}):
                    session['quiz_start_time_evaluation'] = datetime.now(timezone.utc).isoformat()
                    response = routes.submit_evaluation.__wrapped__(12)
                    self.assertEqual(response.json['status'], 'success')
                    self.assertNotIn('quiz_start_time_evaluation', session)

                save.side_effect = RuntimeError('simulated database outage')
                with app.test_request_context('/evaluation/submit/12', method='POST', json={'answers': {}}):
                    session['quiz_start_time_evaluation'] = datetime.now(timezone.utc).isoformat()
                    with self.assertRaises(RuntimeError):
                        routes.submit_evaluation.__wrapped__(12)
                    self.assertIn('quiz_start_time_evaluation', session)

    def test_teacher_evaluation_preview_does_not_require_student_attempt(self):
        user = SimpleNamespace(id=12, level=1)
        with app.app_context(), patch.object(routes, 'current_user', user), \
                patch.object(routes, 'save_evaluation', return_value='preview') as save:
            with app.test_request_context('/evaluation/submit/12', method='POST', json={'answers': {}}):
                response = routes.submit_evaluation.__wrapped__(12)
            self.assertEqual(response, 'preview')
            save.assert_called_once()

    def test_failed_evaluation_save_keeps_attempt_available(self):
        user = SimpleNamespace(id=12, level=0, evaluation_result=None)
        with app.app_context(), patch.object(routes, 'current_user', user), \
                patch.object(routes, 'save_evaluation', return_value=('error', 500)):
            with app.test_request_context('/evaluation/submit/12', method='POST', json={'answers': {}}):
                session['quiz_start_time_evaluation'] = datetime.now(timezone.utc).isoformat()
                _, status = routes.submit_evaluation.__wrapped__(12)
                self.assertEqual(status, 500)
                self.assertIn('quiz_start_time_evaluation', session)

    def test_successful_evaluation_save_consumes_attempt(self):
        user = SimpleNamespace(id=12, level=0, evaluation_result=None)
        with app.app_context(), patch.object(routes, 'current_user', user), \
                patch.object(routes, 'save_evaluation') as save:
            with app.test_request_context('/evaluation/submit/12', method='POST', json={'answers': {}}):
                save.return_value = routes.jsonify({'status': 'success', 'redirect_url': '/done'})
                session['quiz_start_time_evaluation'] = datetime.now(timezone.utc).isoformat()
                response = routes.submit_evaluation.__wrapped__(12)
                self.assertEqual(response.json['status'], 'success')
                self.assertNotIn('quiz_start_time_evaluation', session)


if __name__ == '__main__':
    unittest.main()
