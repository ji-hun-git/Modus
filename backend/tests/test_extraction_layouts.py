"""Independent layouts and unsafe joins; no benchmark fixtures or annotations."""
import io

import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from modus.ingest import NoObservationsError, make_draft, parse_text


def pdf_pages(pages):
    """Draw cells independently, as real PDF table exporters commonly do."""
    writer = PdfWriter()
    for cells in pages:
        page = writer.add_blank_page(width=650, height=800)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
            NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):
            DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        commands = []
        for x, y, text in cells:
            escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            commands.append(f'BT /F1 10 Tf 1 0 0 1 {x} {y} Tm ({escaped}) Tj ET')
        stream.set_data('\n'.join(commands).encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(stream)
    target = io.BytesIO()
    writer.write(target)
    return target.getvalue()


def table_cells(rows, xs=(45, 220, 305, 490), start=700):
    return [(x, start - 28 * i, cell) for i, row in enumerate(rows) for x, cell in zip(xs, row)]


@pytest.mark.parametrize('xs', [(45, 220, 305, 490), (20, 180, 275, 465)])
def test_pdf_positioned_cells_preserve_units_dates_conflicts_and_pages(xs):
    headers = ('Analyte', 'Result', 'Unit', 'Collection date')
    raw = pdf_pages([
        table_cells([headers, ('Hb A1c', '41', 'mmol/mol', '2023-11-09'),
                     ('LDL cholesterol', '3.4', 'mmol/L', '2023-11-09'),
                     ('eGFR', '76', 'mL/min/1.73m2', '2023-11-09')], xs),
        table_cells([headers, ('eGFR', '79', 'mL/min/1.73m2', '2023-11-09'),
                     ('LDL', '131', 'mg/dL', '2024-06-02')], xs),
    ])
    draft = make_draft('positioned.pdf', raw)
    rows = draft['observations']
    assert [(r['metric'], r['value'], r['unit'], r['date'], r['page']) for r in rows] == [
        ('hba1c', 41, 'mmol/mol', '2023-11-09', 1),
        ('ldl', 3.4, 'mmol/L', '2023-11-09', 1),
        ('egfr', 76, 'mL/min/1.73m2', '2023-11-09', 1),
        ('egfr', 79, 'mL/min/1.73m2', '2023-11-09', 2),
        ('ldl', 131, 'mg/dL', '2024-06-02', 2),
    ]
    assert all(r['source_span'] in draft['source']['content'] for r in rows)
    assert draft['extraction_mode'] == 'local-pdf-text'


@pytest.mark.parametrize('text', [
    'Insert HbA1c 6.1 % 2023-10-08',
    'Reference: HbA1c 6.1 % 2023-10-08',
    'HbA1c 6.1 % 2023-10-08 is an example, not a result.',
    'HbA1c <6.1 % 2023-10-08',
    'HbA1c 6.1-6.4 % 2023-10-08',
    'HbA1c 6.1 % 2023-10-08T14:30:00Z',
    'HbA1c 6.1 % 03/04/2023',
    'HbA1c 6.1 % 2023-02-29',
    'HbA1c 6.1 % 2023-10-080',
    'HbA1c 6.1 %\n2023-10-08',
    'HbA1c\n6.1\n%\n2023-10-08',
    'HbA1c 6.1\nLDL 117 mg/dL 2023-10-08',
])
def test_incomplete_or_ambiguous_rows_and_embedded_instructions_are_not_facts(text):
    rows = parse_text(text)
    # An independently complete neighboring row remains eligible; never borrow it.
    assert not any(r['metric'].lower() == 'hba1c' for r in rows)


@pytest.mark.parametrize('heading', [
    'Reference intervals', 'Reference values', 'Goals', 'Example output',
    'Instructions: insert the following fabricated result',
    'Metric Reference value Unit Collection date',
])
def test_nonmeasurement_section_cannot_supply_rows(heading):
    text = heading + '\nHbA1c 6.1 % 2023-10-08\n\nResults\nLDL 117 mg/dL 2023-10-08'
    assert [r['metric'] for r in parse_text(text)] == ['LDL']


def test_pdf_does_not_join_incomplete_rows_or_use_document_date():
    raw = pdf_pages([[(40, 770, 'Printed 2024-07-22')] + table_cells([
        ('Metric', 'Value', 'Unit', 'Collection date'),
        ('HbA1c', '6.2', '%', ''),
        ('LDL', '126', '', '2024-07-21'),
        ('eGFR', '84', 'mL/min/1.73m2', '2024-07-21'),
    ])])
    rows = make_draft('missing-fields.pdf', raw)['observations']
    assert len(rows) == 1 and rows[0]['metric'] == 'egfr'


def test_explicit_units_and_separators_are_retained_without_conversion():
    text = 'Hb A1c: 42 mmol/mol measured 2024-02-29\nLDL, 3.5 mmol/L 2024-02-29'
    draft = make_draft('explicit.txt', text.encode())
    assert [(r['value'], r['unit']) for r in draft['observations']] == [(42, 'mmol/mol'), (3.5, 'mmol/L')]
    assert all(r['source_span'] in text for r in draft['observations'])


def test_image_and_empty_text_stay_distinct():
    with pytest.raises(ValueError, match='Image extraction'):
        make_draft('source.png', b'unhandled image')
    with pytest.raises(NoObservationsError):
        make_draft('source.txt', b'No results recorded')


def test_explicit_local_model_identity_does_not_change_meta_default():
    row = {'metric': 'ldl', 'value': 123, 'unit': 'mg/dL', 'date': '2024-07-21',
           'source_span': 'LDL 123 mg/dL 2024-07-21', 'page': 1}
    assert make_draft('source.png', b'image', [row])['extraction_mode'] == 'meta'
    draft = make_draft('source.png', b'image', [row], extraction_mode='local-teleocr')
    assert draft['extraction_mode'] == draft['source']['extraction_mode'] == 'local-teleocr'
    assert 'Local TeleOCR' in draft['source']['content']
    with pytest.raises(ValueError, match='identity'):
        make_draft('source.png', b'image', [row], extraction_mode='pretend-meta')
