import io
from zipfile import ZipFile
from xml.etree import ElementTree
import json
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app import app, db
import app.routes as routes


def workbook_rows(response):
    assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    with ZipFile(io.BytesIO(response.get_data())) as archive:
        root = ElementTree.fromstring(archive.read('xl/worksheets/sheet1.xml'))
    ns = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    rows = []
    for row in root.findall('.//x:row', ns):
        values = []
        for cell in row.findall('x:c', ns):
            node = cell.find('x:is/x:t', ns) if cell.attrib.get('t') == 'inlineStr' else cell.find('x:v', ns)
            values.append(node.text if node is not None and node.text is not None else '')
        rows.append(values)
    return rows


class EvaluasiExportTests(unittest.TestCase):
    def test_teacher_cannot_export_another_class(self):
        teacher = SimpleNamespace(id=3, is_authenticated=True, level=1, teacher_classes=[SimpleNamespace(class_id=10)])
        with app.test_request_context('/'), patch.object(routes, 'current_user', teacher):
            response, status = routes.teacher_evaluation_export.__wrapped__.__wrapped__(3, 11)
        self.assertEqual(status, 403)

    def test_export_contains_answers_and_escapes_spreadsheet_formulas(self):
        teacher = SimpleNamespace(id=3, is_authenticated=True, level=1, teacher_classes=[SimpleNamespace(class_id=10)])
        student = SimpleNamespace(full_name='Siswa A')
        result = SimpleNamespace(
            answer_details=json.dumps([{
                'nomor': 1, 'topik': 'Sifat Bangun Datar',
                'pertanyaan': 'Bangun apakah ini?',
                'jawaban_siswa': '=HYPERLINK("https://example.com")',
                'jawaban_benar': 'trapesium',
            }]),
            created_at=datetime(2026, 11, 9, 10, 0),
        )
        query = Mock()
        query.join.return_value.filter.return_value.order_by.return_value.all.return_value = [(result, student)]
        with app.test_request_context('/'), patch.object(routes, 'current_user', teacher), \
                patch.object(db.session, 'query', return_value=query):
            response = routes.teacher_evaluation_export.__wrapped__.__wrapped__(3, 10)
        rows = workbook_rows(response)
        self.assertEqual(rows[1][0:2], ['Siswa A', '1'])
        self.assertTrue(rows[1][4].startswith("'="))
        self.assertEqual(rows[1][5], 'trapesium')


if __name__ == '__main__':
    unittest.main()

class OtherResultsExportTests(unittest.TestCase):
    def setUp(self):
        self.teacher = SimpleNamespace(id=3, is_authenticated=True, level=1,
                                       teacher_classes=[SimpleNamespace(class_id=10)])

    def test_other_class_and_unknown_export_are_rejected(self):
        with app.test_request_context('/'), patch.object(routes, 'current_user', self.teacher):
            response, status = routes.teacher_results_export.__wrapped__.__wrapped__(3, 11, 'pretest')
            self.assertEqual(status, 403)
            response, status = routes.teacher_results_export.__wrapped__.__wrapped__(3, 10, 'unknown')
            self.assertEqual(status, 404)

    def test_quiz_and_final_exports_include_results(self):
        quiz = SimpleNamespace(chapter='Bangun Datar', correct=8, incorrect=2, value=80,
                               created_at=datetime(2026, 11, 9, 10, 0))
        final = SimpleNamespace(ai_analysis=json.dumps({
            'peningkatan_skor': 20, 'level_akhir': {'level': 'Tinggi'},
            'perkembangan': 'Meningkat', 'analisis_perkembangan': 'Lebih baik.'
        }), created_at=datetime(2026, 11, 9, 11, 0))
        student = SimpleNamespace(full_name='Siswa A')
        pretest = SimpleNamespace(score=60)
        for kind, row, expected in [
            ('quiz', (quiz, student), 'Bangun Datar'),
            ('final', (final, student, pretest), 'Meningkat'),
        ]:
            with self.subTest(kind=kind):
                query = Mock()
                query.join.return_value.filter.return_value.order_by.return_value.all.return_value = [row]
                query.join.return_value.outerjoin.return_value.filter.return_value.order_by.return_value.all.return_value = [row]
                with app.test_request_context('/'), patch.object(routes, 'current_user', self.teacher), \
                        patch.object(db.session, 'query', return_value=query):
                    response = routes.teacher_results_export.__wrapped__.__wrapped__(3, 10, kind)
                rows = workbook_rows(response)
                self.assertIn(expected, rows[1])

    def test_pretest_export_includes_answer_and_score(self):
        result = SimpleNamespace(
            score=70,
            answer_details=json.dumps([{
                'nomor': 1, 'topik': 'Sifat Bangun Datar',
                'pertanyaan': 'Bangun apakah ini?',
                'jawaban_siswa': 'Trapesium', 'jawaban_benar': 'trapesium',
            }]),
            created_at=datetime(2026, 11, 9, 9, 0),
        )
        query = Mock()
        query.join.return_value.filter.return_value.order_by.return_value.all.return_value = [
            (result, SimpleNamespace(full_name='Siswa A'))
        ]
        with app.test_request_context('/'), patch.object(routes, 'current_user', self.teacher), \
                patch.object(db.session, 'query', return_value=query):
            response = routes.teacher_results_export.__wrapped__.__wrapped__(3, 10, 'pretest')
        rows = workbook_rows(response)
        self.assertEqual(rows[1][0:2], ['Siswa A', '70'])
        self.assertEqual(rows[1][5:7], ['Trapesium', 'trapesium'])

    def test_recap_export_includes_pretest_evaluation_and_evaluation(self):
        recap = [{
            'class_id': 10,
            'students': [{
                'full_name': 'Siswa A', 'pretest_done': True, 'pretest_score': 60,
                'scores': {'Bangun Datar': 80}, 'evaluation_done': True,
                'evaluation_score': 85, 'total': 225, 'avg': 75,
            }],
        }]
        with app.test_request_context('/'), patch.object(routes, 'current_user', self.teacher), \
                patch.object(routes, 'get_grades_recap', return_value=(recap, ['Bangun Datar'], ['Bangun Datar'])):
            response = routes.teacher_results_export.__wrapped__.__wrapped__(3, 10, 'recap')
        rows = workbook_rows(response)
        self.assertEqual(rows[0], ['Siswa', 'Status Pretest', 'Nilai Pretest', 'Bangun Datar', 'Status Evaluasi',
                                   'Nilai Evaluasi', 'Total', 'Rata-rata'])
        self.assertEqual(rows[1], ['Siswa A', 'Selesai', '60', '80', 'Selesai', '85', '225', '75'])


class StudentDataExportTests(unittest.TestCase):
    def setUp(self):
        self.teacher = SimpleNamespace(id=3, is_authenticated=True, level=1,
                                       teacher_classes=[SimpleNamespace(class_id=10)])
        self.classes = [{
            'class_id': 10, 'class_name': 'Kelas A', 'school': 'SD Satu',
            'students': [{
                'full_name': 'Siswa A', 'gender': 'P', 'pretest_done': True,
                'quiz_score': 80, 'materi_selesai': 1, 'total_bab': 2,
                'total_score': 80,
            }],
        }]

    def test_student_data_export_matches_visible_columns(self):
        with app.test_request_context('/'), patch.object(routes, 'current_user', self.teacher), \
                patch.object(routes, 'get_students_by_teacher', return_value=self.classes):
            response = routes.teacher_students_export.__wrapped__.__wrapped__(3, 10)
        rows = workbook_rows(response)
        self.assertEqual(rows[0], ['Kelas', 'Sekolah', 'No', 'Nama', 'L/P', 'Status Pretest',
                                   'Nilai Kuis', 'Materi Selesai', 'Total Materi', 'Total Nilai'])
        self.assertEqual(rows[1], ['Kelas A', 'SD Satu', '1', 'Siswa A', 'P', 'Selesai',
                                   '80', '1', '2', '80'])
        self.assertIn('.xlsx', response.headers['Content-Disposition'])

    def test_teacher_cannot_export_another_class_or_account(self):
        with app.test_request_context('/'), patch.object(routes, 'current_user', self.teacher):
            self.assertEqual(routes.teacher_students_export.__wrapped__.__wrapped__(4)[1], 403)
            self.assertEqual(routes.teacher_students_export.__wrapped__.__wrapped__(3, 11)[1], 403)
