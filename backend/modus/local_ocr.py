"""Opt-in local OCR adapter. The model can only return unverified page text.

No model-selected subprocess arguments, paths, networking, database or record
writes exist here. The host supplies bytes; the fixed worker receives temporary
files and an environment without provider credentials. This is not an OS sandbox.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
from time import perf_counter
from pypdf import PdfReader

from .ingest import MAX_BYTES, NoObservationsError, canonical_unit, make_draft, metric_key, parse_text, validate_document
from .record_models import ExtractedObservation
from .ocr_text import OCRTextFormatError, normalize_ocr_text

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / 'scripts/teleocr_document_worker.py'
PYTHON = ROOT / '.venv-ocr' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
CONFIG = ROOT / 'config/teleocr.json'
TIMEOUT_SECONDS = 180
MAX_PAGES = 12
MAX_OUTPUT_BYTES = 1024 * 1024
_WORKER_LOCK = threading.Lock()


class LocalOCRError(ValueError):
    """Unavailable, incomplete or invalid OCR is never a successful abstention."""
    def __init__(self, message, *, diagnostic=None):
        super().__init__(message)
        self.diagnostic = diagnostic
        self.telemetry = None


def _failure(message, result, kind):
    """Retain bounded execution evidence, never raw text or exception bodies."""
    result = result if isinstance(result, dict) else {}
    pages = result.get('pages')
    diagnostic = {'kind': kind, 'status': result.get('status') if result.get('status') in
        ('completed', 'partial', 'failed') else 'invalid',
        'page_count': min(len(pages), 1000) if isinstance(pages, list) else None, 'pages': []}
    for page in (pages[:MAX_PAGES] if isinstance(pages, list) else []):
        if not isinstance(page, dict):
            continue
        item = {name: page.get(name) if type(page.get(name)) is int and 0 <= page[name] <= 1000000
                else None for name in ('page', 'input_tokens', 'output_tokens')}
        item['stop_reason'] = page.get('stop_reason') if page.get('stop_reason') in (
            'eos', 'token_limit_or_other') else 'invalid'
        item['truncated'] = page.get('truncated') if type(page.get('truncated')) is bool else None
        diagnostic['pages'].append(item)
    return LocalOCRError(message, diagnostic=diagnostic)


def status():
    """Cheap capability probe only; full model hash verification happens in worker."""
    try:
        config = json.loads(CONFIG.read_text(encoding='utf-8'))
        snapshot = ROOT / 'release/models' / ('teleocr-' + config['revision'])
        ready = PYTHON.is_file() and WORKER.is_file() and all(
            (snapshot / item['name']).is_file() for item in config['files'])
        return {'available': bool(ready), 'mode': 'local-teleocr', 'model': config['model'],
            'revision': config['revision'], 'integrity': 'verified before each inference',
            'reason': None if ready else 'Optional local OCR environment or checkpoint is missing'}
    except (OSError, ValueError, KeyError, TypeError):
        return {'available': False, 'mode': 'local-teleocr',
            'reason': 'Optional local OCR configuration is unavailable'}


def _worker_environment(directory):
    allowed = {'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'COMSPEC', 'PATHEXT',
               'LANG', 'LC_ALL', 'NUMBER_OF_PROCESSORS'}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env.update(HF_HOME=str(directory / 'cache'), HF_MODULES_CACHE=str(directory / 'cache/modules'),
        HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
        HF_HUB_DISABLE_IMPLICIT_TOKEN='1', PYTHONNOUSERSITE='1', PYTHONUTF8='1',
        PYTHONDONTWRITEBYTECODE='1')
    return env


def _validate_output(result, raw, config, expected_pages):
    if not isinstance(result, dict) or result.get('status') != 'completed':
        raise _failure('Local OCR did not complete; no extraction draft was created', result, 'incomplete')
    if (result.get('mode') != 'local-teleocr' or result.get('model') != config['model'] or
            result.get('revision') != config['revision'] or
            result.get('input_sha256') != hashlib.sha256(raw).hexdigest()):
        raise _failure('Local OCR identity check failed', result, 'identity')
    pages = result.get('pages')
    if not isinstance(pages, list) or len(pages) != expected_pages:
        raise _failure('Local OCR returned invalid page metadata', result, 'page_metadata')
    total = 0
    for number, page in enumerate(pages, 1):
        if (not isinstance(page, dict) or type(page.get('page')) is not int or page['page'] != number or
                page.get('truncated') is not False or page.get('stop_reason') != 'eos' or
                not isinstance(page.get('text'), str) or len(page['text']) > 16000):
            raise _failure('Local OCR returned incomplete or invalid page text', result, 'page_completion')
        if re.search(r'<(?:box|label):', page['text'], re.I):
            raise _failure('Local OCR returned layout tags instead of plain transcription', result, 'layout_output')
        for name, limit in (('input_tokens', 4096), ('output_tokens', config['max_new_tokens'])):
            if type(page.get(name)) is not int or not 0 < page[name] <= limit:
                raise _failure('Local OCR returned invalid token accounting', result, 'token_accounting')
        total += len(page['text'])
    if total > 80000:
        raise _failure('Local OCR returned too much text', result, 'text_limit')
    return pages


def _identity_matches(result, raw, config):
    return (isinstance(result, dict) and result.get('mode') == 'local-teleocr' and
            result.get('model') == config['model'] and result.get('revision') == config['revision'] and
            result.get('input_sha256') == hashlib.sha256(raw).hexdigest())


def _attempt_usage(result, raw, config):
    """Count reported work only after checking source/model and bounded page data."""
    if not _identity_matches(result, raw, config) or result.get('status') not in ('completed', 'partial'):
        return {'input_tokens': None, 'output_tokens': None}
    pages = result.get('pages')
    if not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES:
        return {'input_tokens': None, 'output_tokens': None}
    counts = {'input_tokens': 0, 'output_tokens': 0}
    for number, page in enumerate(pages, 1):
        if (not isinstance(page, dict) or type(page.get('page')) is not int or page['page'] != number or
                type(page.get('truncated')) is not bool or
                page.get('stop_reason') not in ('eos', 'token_limit_or_other')):
            return {'input_tokens': None, 'output_tokens': None}
        for key, limit in (('input_tokens', 4096), ('output_tokens', config['max_new_tokens'])):
            if type(page.get(key)) is not int or not 0 < page[key] <= limit:
                return {'input_tokens': None, 'output_tokens': None}
            counts[key] += page[key]
    return counts


def _retryable(error, result, usage):
    # This decision uses execution/format evidence only, never row count, grade,
    # expected values or a document/case identity. Unknown execution cannot retry.
    if any(value is None for value in usage.values()) or not isinstance(result, dict):
        return False
    kind = (error.diagnostic or {}).get('kind')
    if result.get('status') == 'completed' and kind in ('layout_output', 'unsupported_markup'):
        return True
    return (result.get('status') in ('completed', 'partial') and kind in ('incomplete', 'page_completion') and
            any(p.get('truncated') is True for p in result.get('pages', [])))


def _run_worker(source, directory, resolution):
    output = directory / 'result.json'
    try:
        subprocess.run([str(PYTHON), str(WORKER), '--execute', '--input', str(source),
            '--output', str(output), '--resolution', resolution], check=True,
            timeout=TIMEOUT_SECONDS, cwd=ROOT, env=_worker_environment(directory),
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            shell=False, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    except subprocess.TimeoutExpired:
        raise LocalOCRError('Local OCR timed out; no extraction draft was created',
                            diagnostic={'kind': 'timeout', 'status': 'failed'}) from None
    except (OSError, subprocess.CalledProcessError):
        raise LocalOCRError('Local OCR worker failed; no extraction draft was created',
                            diagnostic={'kind': 'worker_failure', 'status': 'failed'}) from None
    if not output.is_file() or output.is_symlink() or output.stat().st_size > MAX_OUTPUT_BYTES:
        raise LocalOCRError('Local OCR returned no valid bounded result',
                            diagnostic={'kind': 'invalid_output', 'status': 'failed'})
    try:
        return json.loads(output.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        raise LocalOCRError('Local OCR returned invalid output',
                            diagnostic={'kind': 'invalid_output', 'status': 'failed'}) from None


def _execution_telemetry(config, raw, attempts, started, result, status):
    totals = {key: sum(a[key] for a in attempts) if all(a[key] is not None for a in attempts) else None
              for key in ('input_tokens', 'output_tokens')}
    verified = result if _identity_matches(result, raw, config) else {}
    return {'mode': 'local-teleocr', 'model': config['model'], 'revision': config['revision'],
        'strategy_version': config.get('strategy_version', 'single-attempt-v1'), 'status': status,
        'input_sha256': hashlib.sha256(raw).hexdigest(), 'attempts': attempts,
        'runtime': verified.get('runtime', {}), 'settings': attempts[-1]['settings'],
        'duration_ms': round((perf_counter() - started) * 1000, 3),
        'model_load_seconds': verified.get('model_load_seconds'),
        'peak_allocated_gpu_bytes': verified.get('peak_allocated_gpu_bytes'), **totals,
        'usage_verified': all(value is not None for value in totals.values()),
        'provenance': 'Unverified local model transcription; review against the original document'}


def extract_document(raw, filename):
    """At most two local attempts; valid empty extraction never triggers a retry."""
    extension = Path(filename).suffix.lower()
    if extension not in ('.pdf', '.png', '.jpg', '.jpeg'):
        raise LocalOCRError('Local OCR accepts PDF, PNG and JPEG documents')
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        raise LocalOCRError('Local OCR accepts documents up to 8 MB')
    validate_document(raw, filename)
    expected_pages = len(PdfReader(io.BytesIO(raw)).pages) if extension == '.pdf' else 1
    if not 1 <= expected_pages <= MAX_PAGES:
        raise LocalOCRError('Local OCR accepts documents with 1 to 12 pages')
    if not status()['available']:
        raise LocalOCRError('Local OCR is unavailable; the optional local environment and checkpoint are required')
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    if not _WORKER_LOCK.acquire(blocking=False):
        raise LocalOCRError('Local OCR is busy; try again when the current document finishes')
    started = perf_counter()
    attempts = []
    try:
        with tempfile.TemporaryDirectory(prefix='modus-local-ocr-') as temp:
            directory = Path(temp)
            source = directory / ('document' + extension)
            source.write_bytes(raw)
            for number, resolution in enumerate(('primary', 'fallback'), 1):
                attempt_dir = directory / f'attempt-{number}'
                attempt_dir.mkdir()
                before, result, error = perf_counter(), None, None
                settings = {key: config[key] for key in ('prompt', 'max_new_tokens')}
                settings.update(resolution=resolution,
                    max_pixels=config['max_pixels' if resolution == 'primary' else 'fallback_max_pixels'],
                    prompt_version=config.get('prompt_version', 'audited-text-v1'),
                    strategy_version=config.get('strategy_version', 'single-attempt-v1'),
                    repetition_penalty=config.get('repetition_penalty', 1.0))
                try:
                    result = _run_worker(source, attempt_dir, resolution)
                    pages = _validate_output(result, raw, config, expected_pages)
                    observations = []
                    for page in pages:
                        try:
                            normalized_text = normalize_ocr_text(page['text'])
                        except OCRTextFormatError:
                            raise _failure('Local OCR returned unsupported transcription markup', result, 'unsupported_markup') from None
                        for row in parse_text(normalized_text):
                            metric = metric_key(row['metric'])
                            try:
                                candidate = ExtractedObservation(**{**row, 'metric': metric,
                                    'unit': canonical_unit(metric, row['unit']), 'page': page['page']})
                            except ValueError:
                                continue
                            observations.append(candidate.model_dump(mode='json'))
                except LocalOCRError as exc:
                    error = exc
                usage = _attempt_usage(result, raw, config)
                attempt = {'attempt': number, 'resolution': resolution,
                    'status': 'failed' if error else 'completed', 'settings': settings,
                    'timeout_seconds': TIMEOUT_SECONDS, 'duration_ms': round((perf_counter() - before) * 1000, 3),
                    'diagnostic': error.diagnostic if error else None, **usage}
                attempts.append(attempt)
                if error is None:
                    return {'observations': observations, 'pages': pages,
                        'telemetry': _execution_telemetry(config, raw, attempts, started, result, 'completed')}
                if resolution == 'primary' and _retryable(error, result, usage):
                    continue
                error.telemetry = _execution_telemetry(config, raw, attempts, started, result, 'failed')
                error.diagnostic = {**(error.diagnostic or {}), 'attempts': attempts,
                    'input_tokens': error.telemetry['input_tokens'], 'output_tokens': error.telemetry['output_tokens'],
                    'usage_verified': error.telemetry['usage_verified']}
                raise error
    finally:
        _WORKER_LOCK.release()


def make_local_draft(raw, filename):
    result = extract_document(raw, filename)
    try:
        draft = make_draft(filename, raw, extracted=result['observations'], extraction_mode='local-teleocr')
    except NoObservationsError as exc:
        exc.telemetry = result['telemetry']
        raise
    draft['source']['content'] = 'Unverified local TeleOCR transcription. Review against the original.\n' + '\n'.join(
        f"Page {p['page']}\n{p['text']}" for p in result['pages'])
    draft['source']['ocr_pages'] = result['pages']
    draft['source']['ocr_execution'] = result['telemetry']
    draft['telemetry'] = result['telemetry']
    draft['warnings'].append('Local TeleOCR text is an unverified model transcription; check each field against the original.')
    return draft


def make_local_history_draft(raw, filename):
    """Retain the whole transcription for explicit broader-record review."""
    from .history_ingest import make_history_draft
    result = extract_document(raw, filename)
    try:
        draft = make_history_draft(filename, raw, ocr_pages=result['pages'])
    except ValueError as exc:
        exc.telemetry = result['telemetry']
        raise
    draft['source']['ocr_pages'] = result['pages']
    draft['source']['ocr_execution'] = result['telemetry']
    draft['telemetry'] = result['telemetry']
    draft['warnings'].append('Local transcription needs your review against the original file.')
    return draft
