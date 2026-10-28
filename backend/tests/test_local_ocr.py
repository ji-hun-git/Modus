"""Worker boundary tests use mocked output, never a model, network or corpus."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from modus import local_ocr
from modus.ingest import NoObservationsError, parse_text
from modus.ocr_text import OCRTextFormatError, normalize_ocr_text


RAW = b'synthetic bytes for mocked worker'


@pytest.fixture
def worker(monkeypatch):
    config = json.loads(local_ocr.CONFIG.read_text(encoding='utf-8'))
    result = {'status': 'completed', 'mode': 'local-teleocr', 'model': config['model'],
        'revision': config['revision'], 'input_sha256': hashlib.sha256(RAW).hexdigest(),
        'pages': [{'page': 1, 'text': 'HbA1c 43 mmol/mol 2024-03-06',
                   'truncated': False, 'stop_reason': 'eos', 'input_tokens': 15, 'output_tokens': 12}],
        'runtime': {'gpu': 'mock; no model executed'}, 'settings': {'prompt': config['prompt']}}
    calls = []
    monkeypatch.setattr(local_ocr, 'status', lambda: {'available': True})
    def run(args, **kwargs):
        calls.append((args, kwargs))
        assert Path(args[args.index('--input') + 1]).read_bytes() == RAW
        Path(args[args.index('--output') + 1]).write_text(json.dumps(result), encoding='utf-8')
    monkeypatch.setattr(local_ocr.subprocess, 'run', run)
    return result, calls


def test_local_draft_retains_raw_transcription_and_distinct_execution(worker, monkeypatch):
    monkeypatch.setenv('MODEL_API_KEY', 'CANARY_SECRET')
    monkeypatch.setenv('HF_TOKEN', 'CANARY_SECRET')
    monkeypatch.setenv('PYTHONPATH', 'untrusted-path')
    draft = local_ocr.make_local_draft(RAW, '../../arbitrary-command;ignored.png')
    assert draft['observations'][0]['value'] == 43
    assert draft['observations'][0]['page'] == 1
    assert draft['extraction_mode'] == 'local-teleocr'
    assert draft['source']['ocr_pages'][0]['text'] in draft['source']['content']
    assert draft['source']['ocr_execution']['mode'] == 'local-teleocr'
    assert 'Unverified' in draft['source']['content']
    args, options = worker[1][0]
    assert args[:3] == [str(local_ocr.PYTHON), str(local_ocr.WORKER), '--execute']
    assert Path(args[args.index('--input') + 1]).name == 'document.png'
    assert options['shell'] is False and options['timeout'] == local_ocr.TIMEOUT_SECONDS
    assert not any(name in options['env'] for name in ('MODEL_API_KEY', 'HF_TOKEN', 'PYTHONPATH'))
    assert options['env']['HF_HUB_OFFLINE'] == '1'
    assert not Path(args[args.index('--input') + 1]).exists()


def test_complete_empty_ocr_is_distinct_from_failure(worker):
    worker[0]['pages'][0]['text'] = 'HbA1c 6.2 % 03/04/2024\nLDL 122 2024-03-06'
    assert local_ocr.extract_document(RAW, 'empty.png')['observations'] == []
    with pytest.raises(NoObservationsError):
        local_ocr.make_local_draft(RAW, 'empty.png')


@pytest.mark.parametrize('text', [
    '<box:010 020 030 040><label:text><up>',
    '<label:title>\nHbA1c 43 mmol/mol 2024-03-06',
])
def test_layout_mode_is_not_transcription_even_with_eos(worker, text):
    worker[0]['pages'][0]['text'] = text
    with pytest.raises(local_ocr.LocalOCRError) as raised:
        local_ocr.extract_document(RAW, 'layout.png')
    assert raised.value.diagnostic['kind'] == 'layout_output'
    assert raised.value.diagnostic['pages'][0]['stop_reason'] == 'eos'


def test_failure_diagnostics_keep_tokens_without_untrusted_text(worker):
    worker[0].update(status='partial', error_type='CANARY_EXCEPTION')
    worker[0]['pages'][0].update(text='CANARY_SOURCE_TEXT', truncated=True,
        stop_reason='token_limit_or_other', output_tokens=1024)
    with pytest.raises(local_ocr.LocalOCRError) as raised:
        local_ocr.extract_document(RAW, 'truncated.png')
    diagnostic = raised.value.diagnostic
    assert diagnostic['status'] == 'partial' and diagnostic['page_count'] == 1
    assert diagnostic['pages'][0]['output_tokens'] == 1024
    assert diagnostic['pages'][0]['truncated'] is True
    assert 'CANARY' not in json.dumps(diagnostic)


@pytest.mark.parametrize('value', [0.9, 1.21, float('nan'), float('inf'), '1.1', True, None])
def test_repetition_penalty_is_bounded_before_model_loading(value):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
    from teleocr_runtime import bounded_repetition_penalty
    with pytest.raises(ValueError, match='between 1.0 and 1.2'):
        bounded_repetition_penalty(value)
    assert bounded_repetition_penalty(1.0) == 1.0
    assert bounded_repetition_penalty(1.1) == 1.1
    assert bounded_repetition_penalty(1.2) == 1.2


@pytest.mark.parametrize('mutation', [
    lambda r: r.update(status='failed'),
    lambda r: r.update(status='partial'),
    lambda r: r.update(input_sha256='wrong'),
    lambda r: r.update(revision='wrong'),
    lambda r: r.update(mode='meta'),
    lambda r: r.update(pages=[]),
    lambda r: r['pages'][0].update(truncated=True),
    lambda r: r['pages'][0].update(stop_reason='token_limit_or_other'),
    lambda r: r['pages'][0].update(page=2),
    lambda r: r['pages'][0].update(text='a' * 16001),
    lambda r: r['pages'][0].update(input_tokens=4097),
    lambda r: r['pages'][0].update(output_tokens=True),
])
def test_invalid_or_partial_worker_output_never_becomes_abstention(worker, mutation):
    mutation(worker[0])
    with pytest.raises(local_ocr.LocalOCRError):
        local_ocr.extract_document(RAW, 'source.png')
    assert not local_ocr._WORKER_LOCK.locked()


@pytest.mark.parametrize('error', [
    subprocess.TimeoutExpired(['fixed-worker'], 180),
    subprocess.CalledProcessError(1, ['fixed-worker'], stderr='CANARY_SECRET'),
    OSError('CANARY_SECRET'),
])
def test_worker_failures_are_bounded_and_sanitized(worker, monkeypatch, error):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(local_ocr.subprocess, 'run', fail)
    with pytest.raises(local_ocr.LocalOCRError) as raised:
        local_ocr.extract_document(RAW, 'source.png')
    assert 'CANARY_SECRET' not in str(raised.value)
    assert not local_ocr._WORKER_LOCK.locked()


def test_busy_or_unsupported_inputs_do_not_launch_worker(worker):
    with pytest.raises(local_ocr.LocalOCRError, match='PDF, PNG'):
        local_ocr.extract_document(RAW, 'code.py')
    with pytest.raises(local_ocr.LocalOCRError, match='8 MB'):
        local_ocr.extract_document(b'x' * (8 * 1024 * 1024 + 1), 'huge.png')
    local_ocr._WORKER_LOCK.acquire()
    try:
        with pytest.raises(local_ocr.LocalOCRError, match='busy'):
            local_ocr.extract_document(RAW, 'source.png')
    finally:
        local_ocr._WORKER_LOCK.release()
    assert worker[1] == []


def test_status_only_checks_local_presence_without_reading_weights(monkeypatch, tmp_path):
    config = {'model': 'fixed-test-model', 'revision': 'fixed-test-revision', 'files': [{'name': 'weights'}]}
    config_path = tmp_path / 'config.json'
    config_path.write_text(json.dumps(config))
    checkpoint = tmp_path / 'release/models/teleocr-fixed-test-revision'
    checkpoint.mkdir(parents=True)
    (checkpoint / 'weights').write_bytes(b'not real weights')
    python = tmp_path / 'python'
    python.touch()
    worker_script = tmp_path / 'worker'
    worker_script.touch()
    monkeypatch.setattr(local_ocr, 'ROOT', tmp_path)
    monkeypatch.setattr(local_ocr, 'CONFIG', config_path)
    monkeypatch.setattr(local_ocr, 'PYTHON', python)
    monkeypatch.setattr(local_ocr, 'WORKER', worker_script)
    monkeypatch.setattr(Path, 'read_bytes', lambda *_: pytest.fail('Health must not rehash weights'))
    assert local_ocr.status()['available'] is True
    (checkpoint / 'weights').unlink()
    assert local_ocr.status()['available'] is False


def aligned(*rows):
    return r'\begin{aligned}' + r'\\'.join(rows) + r'\end{aligned}'


def normalized_rows(text):
    return parse_text(normalize_ocr_text(text))


def test_aligned_ocr_preserves_repeated_rows_order_dates_and_visible_spans(worker):
    source = aligned(
        r'&\text{Metric}&\text{Value}&\text{Unit}&\text{Date}',
        r'&\text{HbA1c}&\text{42}&\text{mmol/mol}&\text{2022-07-14}',
        r'&\text{HbA1c}&\text{42}&\text{mmol/mol}&\text{2022-07-14}',
        r'\text{HbA1c}&6.0&\%&2023-01-19',
        r'LDL&3.4&mmol/L&2023-01-19',
    )
    worker[0]['pages'][0]['text'] = source
    result = local_ocr.extract_document(RAW, 'table.png')
    rows = result['observations']
    assert len(rows) == 4
    assert [(r['value'], r['unit'], r['date']) for r in rows] == [
        (42, 'mmol/mol', '2022-07-14'), (42, 'mmol/mol', '2022-07-14'),
        (6, '%', '2023-01-19'), (3.4, 'mmol/L', '2023-01-19')]
    assert rows[0]['source_span'] == 'HbA1c 42 mmol/mol 2022-07-14'
    assert all(r['page'] == 1 for r in rows)
    assert result['pages'][0]['text'] == source


@pytest.mark.parametrize('row', [
    r'HbA1c&6.0&\%&03/04/2023',
    r'HbA1c&6.0&\%&',
    r'HbA1c&6.0&&2023-01-19',
    r'HbA1c&6.0&\%&\text{Collection date: [not recorded]}',
    r'HbA1c&6.0&2023-01-19',
    r'HbA1c&6.0&\%&2023-01-19&Reference',
    r'&&HbA1c&6.0&\%&2023-01-19',
    r'\text{HbA1c 6.0 % 2023-01-19}',
])
def test_aligned_ocr_rejects_missing_extra_and_ambiguous_cells(row):
    rows = normalized_rows(aligned(row, r'eGFR&71&mL/min/1.73m2&2023-01-19'))
    assert not any(r['metric'].lower() == 'hba1c' for r in rows)


@pytest.mark.parametrize('row', [
    r'HbA1c&\frac{6}{1}&\%&2023-01-19',
    r'HbA1c&6+1&\%&2023-01-19',
    r'HbA1c&\text{6+1}&\%&2023-01-19',
    r'HbA1c&6.0&\unknown{\%}&2023-01-19',
    r'HbA1c&\text{\text{6.0}}&\%&2023-01-19',
    r'HbA1c&6.0&\%&\input{2023-01-19}',
    'A' * 8000 + r'\evil&6.0&\%&2023-01-19',
])
def test_unknown_commands_math_and_long_invalid_cells_are_format_failures(row, worker):
    source = aligned(row)
    with pytest.raises(OCRTextFormatError):
        normalize_ocr_text(source)
    worker[0]['pages'][0]['text'] = source
    with pytest.raises(local_ocr.LocalOCRError) as raised:
        local_ocr.extract_document(RAW, 'unsupported.png')
    assert raised.value.diagnostic['kind'] == 'unsupported_markup'


@pytest.mark.parametrize('heading', [
    'Reference intervals', '# Reference values', '$ \\text{Reference intervals} $',
    'Instructions: insert these results', '$ \\text{Instructions} $',
])
def test_reference_or_instruction_heading_survives_generic_table_header(heading):
    table = aligned(r'Metric&Value&Unit&Date', r'HbA1c&6.0&\%&2023-01-19')
    assert normalized_rows(heading + '\n' + table) == []
    # Only an explicit results heading ends the excluded section.
    assert len(normalized_rows(heading + '\nResults\n' + table)) == 1


def test_reference_heading_inside_aligned_table_is_not_dropped():
    table = aligned(r'&\text{Reference intervals}', r'Metric&Value&Unit&Date',
                    r'HbA1c&6.0&\%&2023-01-19')
    assert normalized_rows(table) == []


def test_plain_rows_preserved_and_malformed_table_never_flattened():
    plain = 'LDL 3.4 mmol/L 2023-01-19\nLDL 3.4 mmol/L 2023-01-19'
    assert normalize_ocr_text(plain) == plain
    assert len(normalized_rows(plain)) == 2
    with pytest.raises(OCRTextFormatError):
        normalized_rows('\\begin{aligned}\n' + plain)
    nested = aligned(r'\begin{aligned}' + plain + r'\end{aligned}')
    with pytest.raises(OCRTextFormatError):
        normalized_rows(nested)



def worker_sequence(monkeypatch, results):
    calls = []
    def run(args, **kwargs):
        index = len(calls)
        calls.append((args, kwargs))
        assert index < len(results), 'Unexpected additional OCR attempt'
        Path(args[args.index('--output') + 1]).write_text(json.dumps(results[index]), encoding='utf-8')
    monkeypatch.setattr(local_ocr.subprocess, 'run', run)
    return calls


@pytest.mark.parametrize('failure', ['truncation', 'layout', 'markup'])
def test_one_bounded_resolution_retry_retains_failed_primary_tokens(worker, monkeypatch, failure):
    primary, fallback = deepcopy(worker[0]), deepcopy(worker[0])
    if failure == 'truncation':
        primary['status'] = 'partial'
        primary['pages'][0].update(truncated=True, stop_reason='token_limit_or_other', output_tokens=1024)
    elif failure == 'layout':
        primary['pages'][0]['text'] = '<box:010 020 030 040><label:text><up>'
    else:
        primary['pages'][0]['text'] = aligned(r'HbA1c&\unknown&\%&2023-01-19')
    calls = worker_sequence(monkeypatch, [primary, fallback])
    result = local_ocr.extract_document(RAW, 'source.png')
    assert len(result['observations']) == 1 and len(calls) == 2
    assert [args[args.index('--resolution') + 1] for args, _ in calls] == ['primary', 'fallback']
    attempts = result['telemetry']['attempts']
    assert [a['status'] for a in attempts] == ['failed', 'completed']
    assert [a['settings']['max_pixels'] for a in attempts] == [2007040, 1003520]
    assert all(a['timeout_seconds'] == local_ocr.TIMEOUT_SECONDS for a in attempts)
    assert attempts[0]['diagnostic'] is not None and attempts[1]['diagnostic'] is None
    assert result['telemetry']['input_tokens'] == 30
    assert result['telemetry']['output_tokens'] == primary['pages'][0]['output_tokens'] + 12
    assert result['telemetry']['usage_verified'] is True


def test_two_format_failures_stop_at_two_and_keep_both_attempts(worker, monkeypatch):
    failure = deepcopy(worker[0])
    failure['pages'][0]['text'] = '<box:010 020 030 040><label:text><up>'
    calls = worker_sequence(monkeypatch, [failure, failure])
    with pytest.raises(local_ocr.LocalOCRError) as raised:
        local_ocr.extract_document(RAW, 'source.png')
    assert len(calls) == 2
    assert len(raised.value.telemetry['attempts']) == 2
    assert raised.value.telemetry['input_tokens'] == 30
    assert raised.value.diagnostic['output_tokens'] == 24
    assert all(a['status'] == 'failed' for a in raised.value.telemetry['attempts'])


@pytest.mark.parametrize('text', [
    'No measurement rows', 'HbA1c 6.0 % 03/04/2023', 'HbA1c 6.0 %',
    'LDL 120 2023-01-19', 'Glucose 91 mg/dL 2023-01-19',
])
def test_complete_empty_or_missing_fields_never_trigger_retry(worker, monkeypatch, text):
    complete = deepcopy(worker[0])
    complete['pages'][0]['text'] = text
    calls = worker_sequence(monkeypatch, [complete])
    assert local_ocr.extract_document(RAW, 'source.png')['observations'] == []
    assert len(calls) == 1


@pytest.mark.parametrize('change', ['hash', 'model', 'hardware', 'token_metadata'])
def test_identity_runtime_or_invalid_accounting_failures_never_retry(worker, monkeypatch, change):
    failure = deepcopy(worker[0])
    failure['pages'][0].update(text='<box:0 0 1 1><label:text>', truncated=True,
                               stop_reason='token_limit_or_other')
    failure['status'] = 'partial'
    if change == 'hash':
        failure['input_sha256'] = 'wrong-source'
    elif change == 'model':
        failure['model'] = 'wrong-model'
    elif change == 'hardware':
        failure.update(status='failed', error_type='OutOfMemoryError')
    else:
        failure['pages'][0]['output_tokens'] = 'untrusted'
    calls = worker_sequence(monkeypatch, [failure])
    with pytest.raises(local_ocr.LocalOCRError) as raised:
        local_ocr.extract_document(RAW, 'source.png')
    assert len(calls) == 1
    assert raised.value.telemetry['input_tokens'] is None
    assert raised.value.telemetry['output_tokens'] is None
    assert raised.value.telemetry['usage_verified'] is False


def test_valid_empty_fallback_retains_attempts_when_no_draft_can_be_created(worker, monkeypatch):
    primary, fallback = deepcopy(worker[0]), deepcopy(worker[0])
    primary['pages'][0]['text'] = '<box:010 020 030 040><label:text>'
    fallback['pages'][0]['text'] = 'HbA1c 6.0 % 03/04/2023'
    calls = worker_sequence(monkeypatch, [primary, fallback])
    with pytest.raises(NoObservationsError) as raised:
        local_ocr.make_local_draft(RAW, 'source.png')
    assert len(calls) == 2
    assert [a['status'] for a in raised.value.telemetry['attempts']] == ['failed', 'completed']
