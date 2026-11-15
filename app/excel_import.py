"""Read the fields needed for bulk student import from a simple XLSX file."""

from io import BytesIO
from posixpath import join as posix_join, normpath
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


class SpreadsheetError(ValueError):
    pass


HEADER_ALIASES = {
    'full_name': {'nama', 'nama lengkap', 'nama siswa', 'full name', 'fullname'},
    'username': {'username', 'user name', 'nama pengguna', 'user'},
    'password': {'password', 'kata sandi', 'sandi', 'pass'},
    'gender': {'jenis kelamin', 'jenis kelamin (l/p)', 'gender', 'l/p'},
}
REQUIRED_FIELDS = {
    'full_name': 'Nama',
    'username': 'Username',
    'password': 'Password',
}


def _local_name(tag):
    return tag.rsplit('}', 1)[-1]


def _normalize_header(value):
    return ' '.join(str(value or '').strip().lower().split())


def _column_index(reference):
    letters = ''
    for character in reference or '':
        if character.isalpha():
            letters += character.upper()
        else:
            break
    index = 0
    for character in letters:
        index = index * 26 + (ord(character) - 64)
    return index - 1


def _shared_strings(archive):
    try:
        root = ElementTree.fromstring(archive.read('xl/sharedStrings.xml'))
    except KeyError:
        return []
    return [
        ''.join(node.text or '' for node in item.iter() if _local_name(node.tag) == 't')
        for item in root
        if _local_name(item.tag) == 'si'
    ]


def _worksheet_path(archive):
    workbook = ElementTree.fromstring(archive.read('xl/workbook.xml'))
    sheet = next((node for node in workbook.iter() if _local_name(node.tag) == 'sheet'), None)
    if sheet is None:
        raise SpreadsheetError('File Excel tidak memiliki worksheet.')

    relationship_id = next(
        (value for key, value in sheet.attrib.items() if _local_name(key) == 'id'),
        None,
    )
    target = None
    try:
        relationships = ElementTree.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        for relationship in relationships.iter():
            if (
                _local_name(relationship.tag) == 'Relationship'
                and relationship.attrib.get('Id') == relationship_id
            ):
                target = relationship.attrib.get('Target')
                break
    except KeyError:
        pass

    target = (target or 'worksheets/sheet1.xml').replace('\\', '/')
    if target.startswith('/'):
        return target.lstrip('/')
    return normpath(posix_join('xl', target))


def _cell_text(cell, shared_strings):
    cell_type = cell.attrib.get('t')
    if cell_type == 'inlineStr':
        return ''.join(
            node.text or '' for node in cell.iter() if _local_name(node.tag) == 't'
        )

    value = next(
        (node.text for node in cell if _local_name(node.tag) == 'v' and node.text is not None),
        '',
    )
    if cell_type == 's':
        try:
            return shared_strings[int(value)]
        except (IndexError, TypeError, ValueError):
            return ''
    return value


def _worksheet_rows(archive):
    shared_strings = _shared_strings(archive)
    try:
        root = ElementTree.fromstring(archive.read(_worksheet_path(archive)))
    except KeyError as exc:
        raise SpreadsheetError('Worksheet Excel tidak ditemukan.') from exc

    rows = []
    for row in root.iter():
        if _local_name(row.tag) != 'row':
            continue
        cells = {}
        next_index = 0
        for cell in row:
            if _local_name(cell.tag) != 'c':
                continue
            reference = cell.attrib.get('r')
            index = _column_index(reference) if reference else next_index
            cells[index] = _cell_text(cell, shared_strings)
            next_index = index + 1
        if cells:
            rows.append((
                row.attrib.get('r'),
                [cells.get(index, '') for index in range(max(cells) + 1)],
            ))
    return rows


def read_student_rows(file_stream):
    try:
        payload = file_stream.read() if hasattr(file_stream, 'read') else file_stream
        with ZipFile(BytesIO(payload)) as archive:
            raw_rows = _worksheet_rows(archive)
    except (BadZipFile, ElementTree.ParseError, KeyError, TypeError) as exc:
        raise SpreadsheetError('File Excel tidak valid. Gunakan template .xlsx yang disediakan.') from exc

    header_position = next(
        (index for index, (_, row) in enumerate(raw_rows) if any(str(value).strip() for value in row)),
        None,
    )
    if header_position is None:
        raise SpreadsheetError('File Excel kosong. Isi data siswa terlebih dahulu.')

    header = [_normalize_header(value) for value in raw_rows[header_position][1]]
    columns = {}
    for field, aliases in HEADER_ALIASES.items():
        for index, name in enumerate(header):
            if name in aliases:
                columns[field] = index
                break

    missing = [label for field, label in REQUIRED_FIELDS.items() if field not in columns]
    if missing:
        raise SpreadsheetError(
            'Header tidak lengkap. Kolom wajib: ' + ', '.join(missing) +
            '. Gunakan template yang disediakan.'
        )

    def value_from(row, field):
        index = columns.get(field)
        if index is None or index >= len(row):
            return ''
        return str(row[index] or '').strip()

    students = []
    fallback_number = header_position + 2
    for row_number, row in raw_rows[header_position + 1:]:
        full_name = value_from(row, 'full_name')
        username = value_from(row, 'username')
        password = value_from(row, 'password')
        gender = value_from(row, 'gender')
        if not any((full_name, username, password, gender)):
            continue
        students.append({
            'row': int(row_number) if row_number and str(row_number).isdigit() else fallback_number,
            'full_name': full_name,
            'username': username,
            'password': password,
            'gender': gender,
        })
        fallback_number += 1

    if not students:
        raise SpreadsheetError('Tidak ada data siswa pada file Excel.')
    return students
