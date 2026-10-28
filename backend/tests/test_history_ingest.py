"""Broader local drafts retain original facts without interpreting prose."""
import pytest
from pypdf import PdfWriter
import io

from modus.history_ingest import make_history_draft


def test_arbitrary_lab_csv_preserves_original_unit_and_partial_date():
    raw = 'label,value,unit,date,facility\n헤모글로빈,13.70,g/dL,2012,서울 예시 병원\n'.encode()
    draft = make_history_draft('childhood.csv', raw)
    field = draft['facts'][0]
    assert field['label'] == '헤모글로빈' and field['value'] == '13.70'
    assert field['unit'] == 'g/dL' and field['occurred_on'] == '2012'
    assert field['facility'] == '서울 예시 병원'
    assert field['source_quote'] == '헤모글로빈,13.70,g/dL,2012,서울 예시 병원'
    assert draft['observations'] == []


def test_all_record_kinds_are_explicit_csv_data_not_inferences():
    kinds = ['measurement', 'encounter', 'recorded_diagnosis', 'procedure',
             'prescription', 'vaccination', 'imaging_text', 'recorded_text']
    raw = ('kind,label,value,unit,occurred_on,facility\n' + '\n'.join(
        f'{kind},Original name,As printed,,,Example facility' for kind in kinds)).encode()
    fields = make_history_draft('history.csv', raw)['facts']
    assert [field['kind'] for field in fields] == kinds
    assert all(field['occurred_on'] is None and field['unit'] is None for field in fields)


def test_legacy_rows_and_every_unparsed_line_remain_in_draft():
    raw = b'Visit notes as written\nHbA1c 5.6 % 2024-02-03\nUnmapped test <2.0 IU/L\n'
    draft = make_history_draft('report.txt', raw)
    assert len(draft['observations']) == 1
    assert draft['facts'][0]['kind'] == 'measurement'
    text = ''.join(f['value'] for f in draft['facts'] if f['kind'] == 'recorded_text')
    assert 'Visit notes as written' in text and 'Unmapped test <2.0 IU/L' in text


def test_long_source_text_split_without_loss():
    raw = ('Original note. ' * 150).encode()
    fields = make_history_draft('notes.txt', raw)['facts']
    assert ''.join(f['value'] for f in fields) == raw.decode()
    assert all(f['source_quote'] == f['value'] and len(f['value']) <= 800 for f in fields)


def test_ocr_keeps_unmapped_facts_and_page_identity():
    draft = make_history_draft('scan.png', b'artificial', ocr_pages=[
        {'page': 1, 'text': 'Original vaccination entry'}, {'page': 2, 'text': 'Another note'}])
    assert [f['page'] for f in draft['facts']] == [1, 2]
    assert all(f['extractor'] == 'local-teleocr' for f in draft['facts'])


def test_scanned_pdf_requires_reader_without_silent_page_loss():
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.write(output)
    with pytest.raises(ValueError, match='pages without readable text'):
        make_history_draft('scan.pdf', output.getvalue())


@pytest.mark.parametrize('text', [
    'kind,label,value\nnot-a-kind,Test,3\n',
    'label,value,unit\nTest,3\n',
    'label,value\n,3\n',
])
def test_bad_rows_do_not_turn_into_partial_success(text):
    with pytest.raises(ValueError):
        make_history_draft('bad.csv', text.encode())
