"""New authored report cases with an artificial transport, never held-out data."""
import asyncio
import io
import json
import re

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from modus import provider, record_extraction as reader
from modus.record_document_input import prepare_document
from modus.whole_report import MAX_PROVIDER_CALLS


def quote(number):
    return f'Pulse {70 + number}.00 bpm 20{number:02d}-01-02'


def pdf(count):
    writer = PdfWriter()
    for number in range(1, count + 1):
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
            NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):
            DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        # Long enough for a text-only page; its unrelated words are not facts.
        text = 'Authored test report. Each printed row has its own original page. ' + quote(number)
        stream.set_data(('BT /F1 10 Tf 40 740 Td (' + text + ') Tj ET').encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def fact(number, **changes):
    return {'kind': 'measurement', 'label': 'Pulse', 'value': f'{70 + number}.00',
        'unit': 'bpm', 'occurred_on': f'20{number:02d}-01-02', 'source_quote': quote(number),
        'page': number, 'bbox': None, 'model_confidence': None, **changes}


def response(content, **message_updates):
    return {'model': 'muse-spark-1.3', 'id': 'artificial-whole-report',
        'choices': [{'finish_reason': 'stop', 'message': {
            'content': content if isinstance(content, str) else json.dumps(content), **message_updates}}],
        'usage': {'prompt_tokens': 10, 'completion_tokens': 10, 'total_tokens': 20}}


def pages_in(payload):
    return [int(found.group(1)) for part in payload['messages'][1]['content']
            if part['type'] == 'text' and
            (found := re.match(r'^UNTRUSTED SOURCE PAGE (\d+);', part['text']))]


def checked_fields(payload):
    return json.loads(payload['messages'][1]['content'][-1]['text'].split('\n', 1)[1])


class ArtificialReader:
    def __init__(self, change=None):
        self.calls = []
        self.change = change

    async def __call__(self, payload):
        self.calls.append(payload)
        stage = payload['response_format']['json_schema']['name']
        numbers = pages_in(payload)
        assert 'tools' not in payload
        if stage == 'ExtractRecordedFields':
            content = {'extraction': {'document_type': 'lab_report', 'fields': [fact(n) for n in numbers]}}
        elif stage == 'InventoryReportRows':
            content = {'pages': [{'page': n, 'readability': 'readable', 'truncated': False,
                'rows': [{k: fact(n)[k] for k in ('label','value','unit','source_quote','bbox')}]}
                for n in numbers]}
        else:
            content = {'checks': [{'field_id': field['id'], 'status': 'supported', 'reason': 'matches_source'}
                                  for field in checked_fields(payload)]}
        if self.change:
            altered = self.change(stage, numbers, content)
            if altered is not None:
                return altered
        return response(content)


@pytest.fixture(autouse=True)
def no_live_transport(monkeypatch):
    async def prohibited(*args, **kwargs):
        pytest.fail('Whole-report tests cannot invoke a provider')
    monkeypatch.setattr(provider, 'meta_request', prohibited)


def run(count, transport=None):
    transport = transport or ArtificialReader()
    telemetry = {}
    raw = pdf(count)
    result = asyncio.run(reader.extract_record_document(raw, 'whole-history.pdf', 'application/pdf',
        telemetry, request=transport))
    return result, telemetry, transport, raw


def test_twelve_pages_are_read_once_in_isolated_groups_with_global_evidence():
    result, telemetry, transport, raw = run(12)
    assert len(transport.calls) == MAX_PROVIDER_CALLS == 12
    assert [pages_in(call) for call in transport.calls] == [[1,2,3]] * 3 + [[4,5,6]] * 3 + [[7,8,9]] * 3 + [[10,11,12]] * 3
    assert [field['id'] for field in result['fields']] == [f'field-{n}' for n in range(1, 13)]
    assert [field['page'] for field in result['fields']] == list(range(1, 13))
    assert all(field['source_quote'] == quote(field['page']) for field in result['fields'])
    assert all(field['value'].endswith('.00') for field in result['fields'])
    assert all(field['local_support']['status'] == 'matched_text' for field in result['fields'])
    coverage = result['coverage']
    assert coverage == telemetry['report_coverage']
    assert coverage['processed_pages'] == coverage['page_count'] == 12
    assert coverage['completeness'] == 'not_established'
    assert coverage['request_count'] == 12
    assert all(page['status'] == 'processed' and page['field_count'] == 1 for page in coverage['pages'])
    assert all(page['readability'] == 'text_available' for page in coverage['pages'])
    assert [call['page_group'] for call in telemetry['calls']] == [1,1,1,2,2,2,3,3,3,4,4,4]
    assert [call['source_pages'] for call in telemetry['calls']] == [pages_in(call) for call in transport.calls]
    from hashlib import sha256
    assert result['extraction']['input_sha256'] == sha256(raw).hexdigest()
    assert result['review_required'] is True and result['observations'] == []  # Pulse isn't a legacy metric.


def test_preparation_keeps_trusted_page_boundaries_separate_from_source_text():
    prepared = asyncio.run(prepare_document(pdf(4), 'whole-history.pdf', 'application/pdf', {}))
    assert [item['page'] for item in prepared['page_parts']] == [1,2,3,4]
    assert prepared['parts'] == [part for item in prepared['page_parts'] for part in item['parts']]
    assert all(quote(item['page']) in item['parts'][0]['text'] for item in prepared['page_parts'])


def test_group_types_merge_to_other_without_reclassifying_fields():
    def change(stage, numbers, content):
        if stage == 'ExtractRecordedFields' and numbers == [4]:
            content['extraction'] = {'document_type': 'vaccination_card', 'fields': [fact(4,
                kind='vaccination', label='Vaccine as printed', value='Record wording only',
                unit=None, occurred_on=None, source_quote='Vaccine as printed Record wording only')]}
    result, _, _, _ = run(4, ArtificialReader(change))
    assert result['document_type'] == 'other'
    assert result['fields'][-1]['kind'] == 'vaccination'
    assert result['fields'][-1]['local_support']['status'] == 'mismatch'


def test_empty_groups_keep_coverage_without_claiming_absence_or_repeating_calls():
    def change(stage, numbers, content):
        if stage == 'ExtractRecordedFields':
            content['extraction']['fields'] = []
    result, _, transport, _ = run(7, ArtificialReader(change))
    assert len(transport.calls) == 6
    assert len(result['completeness_check']['omissions']) == 7
    assert result['fields'] == result['observations'] == []
    assert result['verification']['status'] == 'not_run'
    assert result['coverage']['processed_pages'] == 7
    assert result['coverage']['completeness'] == 'not_established'
    assert all(page['status'] == 'no_fields' and page['verification_status'] == 'not_run'
               for page in result['coverage']['pages'])


@pytest.mark.parametrize('problem,kind', [('timeout','timeout'), ('truncated','incomplete'),
    ('refused','refusal'), ('malformed','invalid_schema'), ('wrong_page','invalid_schema')])
def test_later_group_failure_aborts_draft_and_records_failed_and_unread_pages(problem, kind):
    def change(stage, numbers, content):
        if stage != 'ExtractRecordedFields' or numbers != [4,5,6]:
            return
        if problem == 'timeout':
            raise TimeoutError('PRIVATE_PROVIDER_ERROR')
        if problem == 'truncated':
            value = response(content)
            value['choices'][0]['finish_reason'] = 'length'
            return value
        if problem == 'refused':
            return response(content, refusal='PRIVATE_PROVIDER_ERROR')
        if problem == 'malformed':
            return response('PRIVATE_PROVIDER_ERROR {')
        content['extraction']['fields'][0]['page'] = 1  # Valid document page, invalid group page.
    transport, telemetry = ArtificialReader(change), {}
    with pytest.raises((ValueError, provider.MetaRequestError)):
        asyncio.run(reader.extract_record_document(pdf(7), 'failure.pdf', 'application/pdf', telemetry, request=transport))
    assert len(transport.calls) == 4
    coverage = telemetry['report_coverage']
    assert coverage['status'] == 'failed' and coverage['processed_pages'] == 3
    assert [page['status'] for page in coverage['pages']] == ['processed'] * 3 + ['failed'] * 3 + ['not_run']
    assert coverage['groups'][1]['error_kind'] == kind
    assert coverage['groups'][2]['extraction_status'] == 'not_run'
    assert 'PRIVATE_PROVIDER_ERROR' not in json.dumps(telemetry)


@pytest.mark.parametrize('problem', ['timeout','malformed','invented_id'])
def test_group_verifier_failure_is_explicit_and_cannot_repair_or_hide_fields(problem):
    def change(stage, numbers, content):
        if stage != 'VerifyRecordedFields' or numbers != [4]:
            return
        if problem == 'timeout':
            raise TimeoutError('PRIVATE_PROVIDER_ERROR')
        if problem == 'malformed':
            return response('{')
        content['checks'][0]['field_id'] = 'field-1'
    result, _, transport, _ = run(4, ArtificialReader(change))
    assert len(transport.calls) == 6
    assert result['verification']['status'] == 'unavailable'
    assert [field['verification']['status'] for field in result['fields']] == ['supported'] * 3 + ['unavailable']
    assert result['fields'][-1]['value'] == '74.00'
    assert result['coverage']['pages'][-1]['verification_status'] == 'unavailable'
    assert result['coverage']['groups'][-1]['error_kind'] == ('timeout' if problem == 'timeout' else 'invalid_schema')
    assert result['coverage']['processed_pages'] == 4 and result['review_required'] is True


def test_total_field_limit_rejects_whole_report_instead_of_accepting_a_partial_history():
    def change(stage, numbers, content):
        if stage == 'ExtractRecordedFields':
            content['extraction']['fields'] = [fact(numbers[0])] * 100
    transport, telemetry = ArtificialReader(change), {}
    with pytest.raises(ValueError, match='200 fields'):
        asyncio.run(reader.extract_record_document(pdf(7), 'dense.pdf', 'application/pdf', telemetry, request=transport))
    assert len(transport.calls) == 7  # The invalid third group is never verified, inventoried or retried.
    assert telemetry['report_coverage']['status'] == 'failed'
    assert telemetry['report_coverage']['groups'][-1]['extraction_status'] == 'failed'


def test_image_only_page_is_never_called_independently_readable():
    from PIL import Image
    raw = io.BytesIO()
    Image.new('RGB', (64,64), 'white').save(raw, format='PNG')
    transport, telemetry = ArtificialReader(), {}
    result = asyncio.run(reader.extract_record_document(raw.getvalue(), 'scan.png', 'image/png', telemetry, request=transport))
    page = result['coverage']['pages'][0]
    assert page['readability'] == 'image_only' and page['text_available'] is False and page['vision_supplied'] is True
    assert result['fields'][0]['local_support']['status'] == 'unavailable'
    assert result['coverage']['completeness'] == 'not_established'


def test_failed_later_inventory_preserves_all_fields_and_an_explicit_partial_check():
    def change(stage, numbers, content):
        if stage == 'InventoryReportRows' and numbers == [4]:
            raise TimeoutError('PRIVATE_INVENTORY_ERROR')
    result, telemetry, transport, _ = run(4, ArtificialReader(change))
    assert len(transport.calls) == 6 and len(result['fields']) == 4
    check = result['completeness_check']
    assert check['status'] == 'partial' and check['matched_rows'] == 3
    assert [p['status'] for p in check['pages']] == ['checked']*3 + ['unavailable']
    assert result['coverage']['processed_pages'] == 4
    assert 'PRIVATE_INVENTORY_ERROR' not in json.dumps((result,telemetry))
