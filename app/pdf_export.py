"""Small PDF report writer for class analyses, without runtime packages."""

import textwrap
import unicodedata


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
LEFT = 48
RIGHT = 48


def _pdf_text(value):
    value = str(value or '')
    value = value.replace('\u2013', '-').replace('\u2014', '-').replace('\u2022', '-')
    value = unicodedata.normalize('NFKD', value)
    return value.encode('cp1252', errors='replace').decode('cp1252')


def _literal(value):
    return _pdf_text(value).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def final_analysis_pdf(class_name, school, students):
    return _analysis_pdf(class_name, school, students, 'final')


def pretest_analysis_pdf(class_name, school, students):
    return _analysis_pdf(class_name, school, students, 'pretest')


def _analysis_pdf(class_name, school, students, kind):
    """Return a printable PDF with one narrative section per analyzed student."""
    pages = []
    commands = []
    y = 720
    navy = (0.10, 0.19, 0.23)
    muted = (0.36, 0.39, 0.40)
    accent = (0.59, 0.34, 0.12)
    green = (0.12, 0.40, 0.26)
    red = (0.59, 0.18, 0.18)
    violet = (0.36, 0.20, 0.64)
    title = 'HASIL ANALISIS PRETEST' if kind == 'pretest' else 'HASIL ANALISIS AKHIR'

    def fill_rect(x, bottom, width, height, color):
        r, g, b = color
        commands.append(f'{r:.3f} {g:.3f} {b:.3f} rg {x} {bottom:.1f} {width} {height:.1f} re f')

    def draw_at(x, baseline, value, size=10, bold=False, color=navy):
        r, g, b = color
        font = 'F2' if bold else 'F1'
        commands.append(f'{r:.3f} {g:.3f} {b:.3f} rg BT /{font} {size} Tf 1 0 0 1 {x} {baseline:.1f} Tm ({_literal(value)}) Tj ET')

    def new_page(continuation=False):
        nonlocal commands, y
        if commands:
            pages.append('\n'.join(commands))
        commands = []
        fill_rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, (1, 1, 1))
        fill_rect(0, PAGE_HEIGHT - 92, PAGE_WIDTH, 92, (0.11, 0.20, 0.24))
        fill_rect(0, PAGE_HEIGHT - 96, PAGE_WIDTH, 4, accent)
        draw_at(LEFT, PAGE_HEIGHT - 40, 'EDUDAYA', 11, True, (0.91, 0.75, 0.53))
        draw_at(LEFT, PAGE_HEIGHT - 63, title, 18, True, (1, 1, 1))
        draw_at(LEFT, PAGE_HEIGHT - 112, f'{class_name}  |  {school}', 10, False, muted)
        if continuation:
            draw_at(LEFT, PAGE_HEIGHT - 131, 'Lanjutan laporan siswa', 9, False, muted)
        y = PAGE_HEIGHT - 150

    def ensure(height):
        if y - height < 62:
            new_page(continuation=True)

    def wrapped(value, width=88):
        text = _pdf_text(value)
        return textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=False) or ['-']

    def card(heading, value, color=accent, tint=(0.985, 0.978, 0.956)):
        nonlocal y
        if not value:
            return
        lines = wrapped(value)
        height = 38 + 15 * len(lines)
        ensure(height + 10)
        fill_rect(LEFT, y - height, PAGE_WIDTH - LEFT - RIGHT, height, tint)
        fill_rect(LEFT, y - height, 4, height, color)
        draw_at(LEFT + 16, y - 19, heading.upper(), 9, True, color)
        for number, line in enumerate(lines):
            draw_at(LEFT + 16, y - 39 - number * 15, line, 10, False, navy)
        y -= height + 10

    def answer_card(detail):
        nonlocal y
        number = detail.get('nomor', '-')
        topic = detail.get('topik') or 'Bangun Datar'
        fields = (
            ('Pertanyaan', detail.get('pertanyaan') or '-'),
            ('Jawaban siswa', detail.get('jawaban_siswa') or 'Belum dijawab'),
            ('Kunci jawaban', detail.get('jawaban_benar') or '-'),
        )
        prepared = [(label, wrapped(value, 85)) for label, value in fields]
        height = 31 + sum(16 + 14 * len(lines) for _, lines in prepared)
        ensure(height + 10)
        fill_rect(LEFT, y - height, PAGE_WIDTH - LEFT - RIGHT, height, (0.96, 0.97, 0.98))
        fill_rect(LEFT, y - height, 4, height, (0.10, 0.33, 0.46))
        draw_at(LEFT + 16, y - 18, f'SOAL {number} - {topic}', 9, True, (0.10, 0.33, 0.46))
        baseline = y - 39
        for label, lines in prepared:
            draw_at(LEFT + 16, baseline, label.upper(), 8, True, muted)
            baseline -= 15
            for line in lines:
                draw_at(LEFT + 16, baseline, line, 9.5, False, navy)
                baseline -= 14
            baseline -= 2
        y -= height + 10

    new_page()
    if not students:
        card('Status', 'Belum ada analisis yang tersedia untuk kelas ini.')

    for index, item in enumerate(students, 1):
        if index > 1:
            new_page()
        analysis = item['analysis']
        if kind == 'pretest':
            level = (analysis.get('level_kemampuan') or {}).get('level', '-')
            score = item.get('pretest_score')
            metrics = [
                ('SKOR PRETEST', score if score is not None else '-'),
                ('JAWABAN BENAR', item.get('correct') if item.get('correct') is not None else '-'),
                ('LEVEL AWAL', level),
            ]
            profile = (analysis.get('level_kemampuan') or {}).get('deskripsi')
            sections = (
                ('kekuatan', 'Kekuatan', green, (0.94, 0.98, 0.95)),
                ('kelemahan', 'Kelemahan', red, (1, 0.96, 0.96)),
                ('rekomendasi_siswa', 'Saran untuk siswa', accent, (0.985, 0.978, 0.956)),
                ('rekomendasi_guru', 'Saran untuk guru', accent, (0.985, 0.978, 0.956)),
                ('evaluasi_guru', 'Catatan evaluasi', violet, (0.97, 0.96, 1)),
            )
        else:
            level = (analysis.get('level_akhir') or {}).get('level', '-')
            score = item.get('pretest_score')
            metrics = [
                ('SKOR PRETEST', score if score is not None else '-'),
                ('KENAIKAN SKOR', analysis.get('peningkatan_skor', '-')),
                ('LEVEL AKHIR', level),
            ]
            profile = (analysis.get('level_akhir') or {}).get('deskripsi')
            sections = (
                ('topik_meningkat', 'Topik meningkat', green, (0.94, 0.98, 0.95)),
                ('topik_menurun', 'Topik menurun', red, (1, 0.96, 0.96)),
                ('rekomendasi_siswa', 'Saran untuk siswa', accent, (0.985, 0.978, 0.956)),
                ('rekomendasi_guru', 'Saran untuk guru', accent, (0.985, 0.978, 0.956)),
                ('evaluasi_guru', 'Kesimpulan evaluasi', violet, (0.97, 0.96, 1)),
            )

        draw_at(LEFT, y, f'{index:02d}  {_pdf_text(item["name"])}', 18, True, navy)
        y -= 28
        if kind == 'final':
            draw_at(LEFT, y, f'Perkembangan: {analysis.get("perkembangan", "-")}', 10, False, muted)
            y -= 23
        else:
            draw_at(LEFT, y, 'Profil kemampuan awal siswa', 10, False, muted)
            y -= 23

        metric_width = (PAGE_WIDTH - LEFT - RIGHT - 16) / 3
        for metric_index, (label, value) in enumerate(metrics):
            x = LEFT + metric_index * (metric_width + 8)
            fill_rect(x, y - 67, metric_width, 67, (0.97, 0.96, 0.94))
            draw_at(x + 12, y - 22, str(value), 18 if len(str(value)) < 10 else 12, True, accent)
            draw_at(x + 12, y - 46, label, 8, True, muted)
        y -= 85
        card('Profil kemampuan' if kind == 'pretest' else 'Profil akhir', profile)
        if kind == 'final':
            card('Analisis perkembangan', analysis.get('analisis_perkembangan'),
                 (0.10, 0.33, 0.46), (0.95, 0.97, 0.98))
        for key, heading, color, tint in sections:
            for entry in analysis.get(key) or []:
                if not isinstance(entry, dict):
                    continue
                topic = entry.get('topik')
                body = entry.get('keterangan') or entry.get('saran') or entry.get('poin')
                card(heading + (f' - {topic}' if topic else ''), body, color, tint)
        card('Motivasi', analysis.get('motivasi'), green, (0.94, 0.98, 0.95))
        if item.get('answers'):
            ensure(55)
            draw_at(LEFT, y - 5, 'JAWABAN SISWA - ' + ('PRETEST' if kind == 'pretest' else 'EVALUASI'),
                    12, True, navy)
            y -= 25
            for detail in item['answers']:
                if isinstance(detail, dict):
                    answer_card(detail)

    pages.append('\n'.join(commands))
    objects = [None, None, None, None]
    page_ids = []
    for page_number, content in enumerate(pages, 1):
        content += f'\n0.55 0.60 0.65 rg BT /F1 8 Tf 1 0 0 1 48 28 Tm (Halaman {page_number} dari {len(pages)}) Tj ET'
        stream = content.encode('cp1252')
        stream_id = len(objects) + 1
        objects.append(b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream')
        page_id = len(objects) + 1
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {stream_id} 0 R >>'.encode())
        page_ids.append(page_id)

    objects[0] = b'<< /Type /Catalog /Pages 2 0 R >>'
    objects[1] = ('<< /Type /Pages /Kids [' + ' '.join(f'{number} 0 R' for number in page_ids) + f'] /Count {len(page_ids)} >>').encode()
    objects[2] = b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>'
    objects[3] = b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>'

    output = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f'{number} 0 obj\n'.encode() + body + b'\nendobj\n')
    xref_offset = len(output)
    output.extend(f'xref\n0 {len(objects) + 1}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        output.extend(f'{offset:010d} 00000 n \n'.encode())
    output.extend(f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n'.encode())
    return bytes(output)
