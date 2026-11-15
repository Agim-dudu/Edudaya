import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from app import app
import app.routes as routes
from app.controller.dashboard import TeacherDashboardController
from app.excel_export import workbook_bytes
from app.excel_import import SpreadsheetError, read_student_rows


def shared_string_workbook():
    output = io.BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('xl/workbook.xml',
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Siswa" sheetId="1" r:id="rId1"/></sheets></workbook>')
        archive.writestr('xl/_rels/workbook.xml.rels',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>')
        archive.writestr('xl/sharedStrings.xml',
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<si><t>Nama</t></si><si><t>Username</t></si><si><t>Password</t></si>'
            '<si><t>Siswa A</t></si><si><t>siswa.a</t></si><si><t>rahasia</t></si></sst>')
        archive.writestr('xl/worksheets/sheet1.xml',
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
            '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c>'
            '<c r="C1" t="s"><v>2</v></c></row>'
            '<row r="2"><c r="A2" t="s"><v>3</v></c><c r="B2" t="s"><v>4</v></c>'
            '<c r="C2" t="s"><v>5</v></c></row>'
            '</sheetData></worksheet>')
    return output.getvalue()


class StudentImportParserTests(unittest.TestCase):
    def test_reads_inline_string_template(self):
        data = workbook_bytes([
            ['Nama', 'Username', 'Password', 'Jenis Kelamin (L/P)'],
            ['Siswa Satu', 'siswa1', 'rahasia', 'P'],
        ])
        self.assertEqual(read_student_rows(io.BytesIO(data)), [{
            'row': 2,
            'full_name': 'Siswa Satu',
            'username': 'siswa1',
            'password': 'rahasia',
            'gender': 'P',
        }])

    def test_reads_shared_strings_from_excel(self):
        self.assertEqual(read_student_rows(io.BytesIO(shared_string_workbook())), [{
            'row': 2,
            'full_name': 'Siswa A',
            'username': 'siswa.a',
            'password': 'rahasia',
            'gender': '',
        }])

    def test_missing_required_header_is_rejected(self):
        data = workbook_bytes([['Nama', 'Username'], ['Siswa A', 'siswa.a']])
        with self.assertRaisesRegex(SpreadsheetError, 'Password'):
            read_student_rows(io.BytesIO(data))


class StudentImportControllerTests(unittest.TestCase):
    def setUp(self):
        self.teacher = SimpleNamespace(
            id=3,
            is_authenticated=True,
            level=1,
            teacher_classes=[SimpleNamespace(class_id=10)],
        )

    def test_valid_rows_are_added_and_duplicate_rows_are_skipped(self):
        data = workbook_bytes([
            ['Nama', 'Username', 'Password'],
            ['Siswa A', 'siswa.a', 'rahasia'],
            ['Siswa B', 'SISWA.A', 'rahasia'],
            ['Siswa C', 'siswa.c', '12345'],
        ])
        with app.app_context(), \
                patch.object(TeacherDashboardController, 'current_user', self.teacher), \
                patch.object(TeacherDashboardController.Classes, 'query') as class_query, \
                patch.object(TeacherDashboardController.User, 'query') as user_query, \
                patch.object(TeacherDashboardController.db.session, 'add') as add, \
                patch.object(TeacherDashboardController.db.session, 'commit') as commit:
            class_query.get.return_value = SimpleNamespace(id=10)
            user_query.filter_by.return_value.first.return_value = None
            created, errors = TeacherDashboardController.import_students_from_excel(
                3, 10, io.BytesIO(data)
            )

        self.assertEqual(created, 2)
        self.assertEqual(len(errors), 1)
        self.assertIn('Baris 3', errors[0])
        self.assertEqual(add.call_count, 2)
        commit.assert_called_once_with()

    def test_teacher_cannot_import_to_another_class(self):
        with app.app_context(), patch.object(TeacherDashboardController, 'current_user', self.teacher):
            with self.assertRaises(PermissionError):
                TeacherDashboardController.import_students_from_excel(
                    3, 11, io.BytesIO(workbook_bytes([['Nama', 'Username', 'Password']]))
                )


class StudentImportRouteTests(unittest.TestCase):
    def test_template_is_downloadable_only_for_own_class(self):
        teacher = SimpleNamespace(
            id=3,
            is_authenticated=True,
            level=1,
            teacher_classes=[SimpleNamespace(class_id=10)],
        )
        with app.test_request_context('/'), patch.object(routes, 'current_user', teacher):
            response = routes.teacher_students_import_template.__wrapped__.__wrapped__(3, 10)
            self.assertEqual(response.mimetype,
                             'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.assertIn('.xlsx', response.headers['Content-Disposition'])
            self.assertEqual(
                routes.teacher_students_import_template.__wrapped__.__wrapped__(3, 11)[1],
                403,
            )

    def test_my_classes_page_has_import_controls(self):
        markup = Path('resources/views/dashboard/teacher/my_classes.html').read_text(encoding='utf-8')
        self.assertIn('openImportModal(this)', markup)
        self.assertIn('/import/template', markup)
        self.assertIn('Download Template Excel', markup)

    def test_students_page_has_class_scoped_import_controls(self):
        markup = Path('resources/views/dashboard/teacher/students.html').read_text(encoding='utf-8')
        self.assertIn('openImportModal(this)', markup)
        self.assertIn('data-class-id="{{ kelas.class_id }}"', markup)
        self.assertIn('/import/template', markup)
        self.assertIn('Import Siswa', markup)
        self.assertIn('name="return_to" value="students"', markup)


if __name__ == '__main__':
    unittest.main()
