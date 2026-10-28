"""Opt-in C1/C2 synthetic extraction, verification and record-tool smoke.

Preparation never reads credentials. This fixed development probe is neither a
benchmark nor a multimodal accuracy evaluation. Image and text-PDF are separate.
"""
import argparse
import asyncio
from datetime import datetime, timezone
from hashlib import sha256
import json
import io
from pathlib import Path
import sys
from time import perf_counter
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from modus.bundle import identity
from modus.policy import POLICY
from modus.provider import MetaRequestError, failure_kind, meta_request, provider_status
from modus.record_extraction import extract_record_document
from modus.record_store import RecordStore
from modus_entry import agent
from modus_entry.runtime import BUNDLE_ID, execution_context
from modus_entry.tools import capture
import smoke_entry_meta as legacy

MODEL = 'muse-spark-1.3'
MAX_REQUESTS = 2 + POLICY.max_rounds
MAX_OUTPUT_TOKENS = 8000 + POLICY.max_rounds * POLICY.max_completion_tokens
MAX_PAYLOAD_BYTES = 128 * 1024
PRICING = {'checked_at': '2026-10-28', 'currency': 'USD', 'input_per_million': 1.25,
           'output_per_million': 4.25, 'cached_input_per_million': 0.15,
           'source': 'https://dev.meta.ai/docs/pricing-rate-limits'}


def document(input_mode):
    if input_mode == 'pdf':
        return legacy.synthetic_pdf(), 'authored-entry-smoke.pdf', 'application/pdf'
    if input_mode != 'image':
        raise ValueError('Choose image or pdf input')
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(legacy.synthetic_pdf())
    page, bitmap = None, None
    try:
        page = pdf[0]
        bitmap = page.render(scale=1.5)
        image = bitmap.to_pil()
        output = io.BytesIO()
        image.save(output, format='PNG')
        return output.getvalue(), 'authored-entry-smoke.png', 'image/png'
    finally:
        if bitmap is not None:
            bitmap.close()
        if page is not None:
            page.close()
        pdf.close()


def plan(input_mode='image'):
    raw, filename, mime = document(input_mode)
    value = {'schema': 'modus-record-extraction-smoke-v1', 'model': MODEL,
             'endpoint': 'https://api.meta.ai/v1/chat/completions', 'synthetic_only': True,
             'data_origin': 'Fixed authored PDF, optionally rendered locally, and separate authored entry seed',
             'input_mode': input_mode, 'filename': filename, 'mime': mime, 'local_ocr_requested': False,
             'document_sha256': sha256(raw).hexdigest(),
             'authored_pdf_sha256': sha256(legacy.synthetic_pdf()).hexdigest(),
             'smoke_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
             'bundle_id': BUNDLE_ID, 'policy': POLICY.model_dump(), 'pricing_basis': PRICING,
             'max_requests': MAX_REQUESTS, 'max_reserved_output_tokens': MAX_OUTPUT_TOKENS,
             'max_payload_bytes_per_request': MAX_PAYLOAD_BYTES,
             'retries': 0, 'automatic_commit': False,
             'scope': 'Extract then verify plus a committed-record inventory question',
             'limits': 'No hard monetary/input-token cap. One authored case, no clinical, held-out or benchmark qualification. Image source support is model judgement, not independent text matching.'}
    return {**value, 'plan_id': identity(value)}


class BoundedRequest:
    def __init__(self, request, *, max_requests=MAX_REQUESTS, max_output_tokens=MAX_OUTPUT_TOKENS):
        if type(max_requests) is not int or not 1 <= max_requests <= MAX_REQUESTS:
            raise ValueError('Request budget outside the fixed smoke maximum')
        if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= MAX_OUTPUT_TOKENS:
            raise ValueError('Output budget outside the fixed smoke maximum')
        self.request, self.max_requests, self.max_output_tokens = request, max_requests, max_output_tokens
        self.calls = self.responses = self.reserved_output_tokens = self.blocked_requests = 0

    async def __call__(self, payload):
        if payload.get('model') != MODEL:
            raise MetaRequestError('model_mismatch')
        reserve = payload.get('max_completion_tokens')
        size = len(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
        if (type(reserve) is not int or reserve < 1 or self.calls >= self.max_requests
                or self.reserved_output_tokens + reserve > self.max_output_tokens
                or size > MAX_PAYLOAD_BYTES):
            self.blocked_requests += 1
            raise MetaRequestError('budget_exceeded')
        self.calls += 1
        self.reserved_output_tokens += reserve
        response = await self.request(payload)
        self.responses += 1
        return response


def token_cost(stages, *, mocked, attempted):
    """Uncached-price estimate from reported usage, never a billing assertion."""
    calls = [call for stage in stages for call in stage['telemetry'].get('calls', [])]
    result = {'pricing_basis': PRICING, 'billed_cost_usd': None,
              'uncached_usage_estimate_usd': None,
              'basis': 'Unknown until all attempted requests report input/output usage; cache discount ignored.'}
    if not attempted:
        result.update(uncached_usage_estimate_usd=0, basis='No provider request attempted.')
    elif mocked:
        result['basis'] = 'Artificial transport usage is not a billable provider measurement.'
    elif len(calls) == attempted and all(isinstance(c.get('usage'), dict) and all(
            type(c['usage'].get(k)) is int and c['usage'][k] >= 0
            for k in ('prompt_tokens', 'completion_tokens')) for c in calls):
        total = sum(c['usage']['prompt_tokens'] * PRICING['input_per_million']
                    + c['usage']['completion_tokens'] * PRICING['output_per_million'] for c in calls)
        result.update(uncached_usage_estimate_usd=round(total / 1_000_000, 8),
                      basis='Reported usage at uncached Standard rates; upper estimate if cached tokens were discounted, not an invoice.')
    return result


def validate_draft(draft, input_mode):
    rows, fields = draft.get('observations', []), draft.get('fields', [])
    exact = len(rows) == 1 and all(rows[0].get(key) == value for key, value in legacy.EXPECTED.items())
    exact = exact and len(fields) == 1 and all(fields[0].get(key) == value for key, value in {
        'kind': 'measurement', 'label': 'HbA1c', 'value': '5.6', 'unit': '%',
        'occurred_on': '2024-02-03', 'source_quote': legacy.SPAN, 'page': 1}.items())
    expected_support = 'matched_text' if input_mode == 'pdf' else 'unavailable'
    verified = (len(fields) == 1 and fields[0].get('local_support', {}).get('status') == expected_support
                and fields[0].get('verification', {}).get('status') == 'supported'
                and draft.get('verification', {}).get('status') == 'completed')
    return {'extract_only_authored_fields_match': exact, 'source_and_second_pass_checks_passed': verified,
            'review_still_required': draft.get('review_required') is True}


async def inventory_stage(report, bounded):
    import tempfile
    stage = {'kind': 'record_tool_loop', 'status': 'failed', 'telemetry': {}}
    report['stages'].append(stage)
    with tempfile.TemporaryDirectory(prefix='modus-record-smoke-') as temp:
        store = RecordStore(Path(temp) / 'authored.db', seed_provider=legacy.initial_data, clock=lambda: legacy.NOW)
        context = capture(store, legacy.DAY, legacy.NOW.isoformat())
        before = context['view']
        try:
            response = await agent.live_chat(context, legacy.QUESTION, stage['telemetry'], request=bounded)
            valid = (response.get('scope') == context['view']['scope']
                     and any(s.get('name') == 'record_inventory' for s in response.get('trace', []))
                     and any(c.get('id') == 'inventory-all' and c.get('text') ==
                             'This view contains 9 recorded measurements from 3 documents.'
                             for c in response.get('claims', [])))
            if not valid:
                raise ValueError('Fixed inventory path was not demonstrated')
            stage.update(status='passed', claims=response['claims'], trace=response['trace'], scope=response['scope'])
        finally:
            report['records_unchanged'] = capture(store, legacy.DAY, legacy.NOW.isoformat())['view'] == before
            with store.connect() as db:
                report['committed_imports'] = db.execute('SELECT COUNT(*) FROM record_commits').fetchone()[0]
            if not report['records_unchanged'] or report['committed_imports']:
                raise ValueError('Read-only smoke boundary was violated')


async def run(output, *, input_mode='image', execute=False, allow_network=False, request=None,
              max_requests=MAX_REQUESTS, max_output_tokens=MAX_OUTPUT_TOKENS):
    output = Path(output)
    if output.exists():
        raise ValueError('Evidence path already exists; choose a new path')
    report = {**plan(input_mode), 'run_id': str(uuid4()), 'tested_at': datetime.now(timezone.utc).isoformat(),
              'status': 'prepared', 'execution_class': 'preparation', 'provider_requests_made': 0,
              'provider_requests_attempted': 0, 'provider_responses_received': 0,
              'live_path_verified': False, 'model_performance_measured': False,
              'committed_imports': 0, 'stages': [],
              'cost': token_cost([], mocked=False, attempted=0)}
    mocked = request is not None
    if not execute:
        legacy.write_new(output, report)
        return report
    if not mocked and not allow_network:
        report.update(status='blocked', error_kind='network_not_authorized')
        legacy.write_new(output, report)
        return report
    if not mocked:
        legacy.load_live_configuration()
        if not provider_status()['key_configured']:
            report.update(status='blocked', error_kind='credentials_not_configured')
            legacy.write_new(output, report)
            return report
    report['execution_class'] = 'mock_transport_test' if mocked else 'live_provider_smoke'
    bounded = BoundedRequest(request or meta_request, max_requests=max_requests, max_output_tokens=max_output_tokens)
    report['execution_limits'] = {'max_requests': max_requests, 'max_reserved_output_tokens': max_output_tokens}
    started = perf_counter()
    try:
        stage = {'kind': 'record_extract_then_verify', 'status': 'failed',
                 'telemetry': {'execution': execution_context('meta', MODEL)}}
        report['stages'].append(stage)
        raw, filename, mime = document(input_mode)
        draft = await extract_record_document(raw, filename, mime, stage['telemetry'], request=bounded)
        checks = validate_draft(draft, input_mode)
        stage.update(draft=draft, **checks, committed=False)
        if not all(checks.values()):
            raise ValueError('Fixed authored extraction/verification check failed')
        stage['status'] = 'passed'
        await inventory_stage(report, bounded)
        report.update(status='passed', live_path_verified=not mocked)
    except Exception as error:
        report.update(status='failed', error_kind=failure_kind(error) if isinstance(error, MetaRequestError)
                      else 'validation_failed')
        if report['stages'] and report['stages'][-1]['status'] == 'failed':
            report['stages'][-1]['error_kind'] = report['error_kind']
    finally:
        report.update(duration_ms=round((perf_counter() - started) * 1000, 2),
            transport_requests=bounded.calls, provider_requests_attempted=0 if mocked else bounded.calls,
            provider_responses_received=0 if mocked else bounded.responses,
            provider_requests_made=0 if mocked else bounded.calls if bounded.responses == bounded.calls else None,
            request_count_basis='Attempts counted before transport; responses establish returned calls, transmission on timeout remains unknown.',
            reserved_output_tokens=bounded.reserved_output_tokens, blocked_requests=bounded.blocked_requests,
            cost=token_cost(report['stages'], mocked=mocked, attempted=bounded.calls))
        legacy.write_new(output, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--input', choices=['image', 'pdf'], default='image', dest='input_mode')
    parser.add_argument('--allow-network', action='store_true', help='Authorize this fixed potentially billable synthetic smoke')
    parser.add_argument('--out', type=Path, default=ROOT / 'eval' / ('record-extraction-smoke-'
        + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json'))
    args = parser.parse_args(argv)
    report = asyncio.run(run(args.out, input_mode=args.input_mode, execute=args.execute, allow_network=args.allow_network))
    print(json.dumps({'status': report['status'], 'execution_class': report['execution_class'], 'report': str(args.out)}))
    return 0 if report['status'] in {'prepared', 'passed'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
