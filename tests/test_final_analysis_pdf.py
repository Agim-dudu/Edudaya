import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app import app, db
import app.routes as routes
from app.pdf_export import final_analysis_pdf, pretest_analysis_pdf


class FinalAnalysisPdfTests(unittest.TestCase):
    def test_pretest_pdf_contains_diagnosis(self):
        pdf = pretest_analysis_pdf('Kelas A', 'SD Satu', [{
            'name': 'Siswa A', 'pretest_score': 60, 'correct': 5,
            'answers': [{'nomor': 1, 'topik': 'Sifat Bangun Datar',
                         'pertanyaan': 'Bangun apakah ini?', 'jawaban_siswa': 'Trapesium',
                         'jawaban_benar': 'trapesium'}],
            'analysis': {
                'level_kemampuan': {'level': 'Sedang', 'deskripsi': 'Dasar sudah cukup.'},
                'kekuatan': [{'topik': 'Luas', 'keterangan': 'Menguasai rumus.'}],
                'kelemahan': [{'topik': 'Keliling', 'keterangan': 'Perlu latihan.'}],
                'evaluasi_guru': [{'poin': 'Beri contoh tambahan.'}],
            },
        }])
        self.assertTrue(pdf.startswith(b'%PDF-1.4'))
        self.assertIn(b'HASIL ANALISIS PRETEST', pdf)
        self.assertIn(b'Perlu latihan.', pdf)
        self.assertIn(b'Beri contoh tambahan.', pdf)
        self.assertIn(b'JAWABAN SISWA - PRETEST', pdf)
        self.assertIn(b'Trapesium', pdf)

    def test_pretest_pdf_route_is_limited_to_assigned_class(self):
        teacher = SimpleNamespace(id=3, is_authenticated=True, level=1,
                                  teacher_classes=[SimpleNamespace(class_id=10)])
        with app.test_request_context('/'), patch.object(routes, 'current_user', teacher):
            response, status = routes.teacher_pretest_analysis_pdf.__wrapped__.__wrapped__(3, 11)
        self.assertEqual(status, 403)

    def test_pretest_pdf_route_returns_analysis(self):
        teacher = SimpleNamespace(id=3, is_authenticated=True, level=1,
                                  teacher_classes=[SimpleNamespace(class_id=10)])
        result = SimpleNamespace(score=60, correct=5, answer_details=json.dumps([{
            'nomor': 1, 'topik': 'Luas', 'pertanyaan': 'Berapa luasnya?',
            'jawaban_siswa': '12 cm2', 'jawaban_benar': '12 cm²',
        }]), ai_analysis=json.dumps({
            'level_kemampuan': {'level': 'Sedang'},
            'kelemahan': [{'topik': 'Keliling', 'keterangan': 'Perlu latihan.'}],
        }))
        query = Mock()
        query.join.return_value.filter.return_value.order_by.return_value.all.return_value = [
            (result, SimpleNamespace(full_name='Siswa A'))
        ]
        with app.test_request_context('/'), patch.object(routes, 'current_user', teacher), \
                patch.object(routes.Classes, 'query') as classes_query, \
                patch.object(db.session, 'query', return_value=query):
            classes_query.get_or_404.return_value = SimpleNamespace(name='Kelas A', school='SD Satu')
            response = routes.teacher_pretest_analysis_pdf.__wrapped__.__wrapped__(3, 10)
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertIn(b'Siswa A', response.get_data())
        self.assertIn(b'12 cm2', response.get_data())

    def test_report_contains_narrative_and_paginates(self):
        student = {
            'name': 'Siswa Contoh', 'pretest_score': 60,
            'answers': [{'nomor': 1, 'topik': 'Luas', 'pertanyaan': 'Berapa luasnya?',
                         'jawaban_siswa': '24 cm2', 'jawaban_benar': '24 cm²'}],
            'analysis': {
                'level_akhir': {'level': 'Tinggi', 'deskripsi': 'Kemampuan meningkat.'},
                'peningkatan_skor': 25,
                'perkembangan': 'Meningkat',
                'analisis_perkembangan': 'Siswa lebih memahami luas bangun datar.',
                'evaluasi_guru': [{'poin': 'Pertahankan latihan rutin.'}],
            },
        }
        pdf = final_analysis_pdf('Kelas A', 'SD Satu', [student] * 12)
        self.assertTrue(pdf.startswith(b'%PDF-1.4'))
        self.assertIn(b'ANALISIS PERKEMBANGAN', pdf)
        self.assertIn(b'Pertahankan latihan rutin.', pdf)
        self.assertIn(b'JAWABAN SISWA - EVALUASI', pdf)
        self.assertIn(b'24 cm2', pdf)
        self.assertIn(b'Halaman 2 dari', pdf)
        self.assertTrue(pdf.rstrip().endswith(b'%%EOF'))

    def test_teacher_can_only_export_assigned_class(self):
        teacher = SimpleNamespace(id=3, is_authenticated=True, level=1,
                                  teacher_classes=[SimpleNamespace(class_id=10)])
        with app.test_request_context('/'), patch.object(routes, 'current_user', teacher):
            response, status = routes.teacher_final_analysis_pdf.__wrapped__.__wrapped__(3, 11)
        self.assertEqual(status, 403)

    def test_export_returns_pdf_with_analyzed_student(self):
        teacher = SimpleNamespace(id=3, is_authenticated=True, level=1,
                                  teacher_classes=[SimpleNamespace(class_id=10)])
        analysis = {'level_akhir': {'level': 'Tinggi'}, 'analisis_perkembangan': 'Meningkat jelas.'}
        result = SimpleNamespace(ai_analysis=json.dumps(analysis))
        evaluation = SimpleNamespace(answer_details=json.dumps([{
            'nomor': 1, 'topik': 'Luas', 'pertanyaan': 'Berapa luasnya?',
            'jawaban_siswa': '24 cm2', 'jawaban_benar': '24 cm²',
        }]))
        student = SimpleNamespace(full_name='Siswa A')
        pretest = SimpleNamespace(score=70)
        query = Mock()
        query.join.return_value.outerjoin.return_value.outerjoin.return_value.filter.return_value.order_by.return_value.all.return_value = [
            (result, student, pretest, evaluation)
        ]
        with app.test_request_context('/'), patch.object(routes, 'current_user', teacher), \
                patch.object(routes.Classes, 'query') as classes_query, \
                patch.object(db.session, 'query', return_value=query):
            classes_query.get_or_404.return_value = SimpleNamespace(name='Kelas A', school='SD Satu')
            response = routes.teacher_final_analysis_pdf.__wrapped__.__wrapped__(3, 10)
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertIn('.pdf', response.headers['Content-Disposition'])
        self.assertIn(b'Siswa A', response.get_data())
        self.assertIn(b'24 cm2', response.get_data())
