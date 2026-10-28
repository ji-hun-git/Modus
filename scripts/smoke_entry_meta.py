"""Opt-in, bounded synthetic entry probe. Preparation never reads credentials.

This is a development smoke, not a benchmark or a record import. Its one-page
PDF is authored here; extraction proposals are never committed or sent to the
agent. The agent reads the separate, fixed authored entry seed in a temp store.
"""
import argparse
import asyncio
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
from time import perf_counter
from uuid import uuid4
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from modus.bundle import identity
from modus.extraction import extract_document
from modus.policy import POLICY
from modus.provider import MetaRequestError, failure_kind, meta_request
from modus.record_store import RecordStore
from modus_entry import agent
from modus_entry.runtime import BUNDLE_ID, execution_context
from modus_entry.seed import initial_data
from modus_entry.tools import capture

MODEL = 'muse-spark-1.3'
DAY = '2026-10-27'
NOW = datetime(2026, 10, 28, tzinfo=timezone.utc)
QUESTION = 'How many recorded measurements and documents are in this view?'
SPAN = 'HbA1c 5.6 % 2024-02-03'
EXPECTED = {'metric': 'hba1c', 'value': 5.6, 'unit': '%', 'date': '2024-02-03',
            'source_span': SPAN, 'page': 1}
MAX_REQUESTS = 1 + POLICY.max_rounds
MAX_OUTPUT_TOKENS = 4000 + POLICY.max_rounds * POLICY.max_completion_tokens


def synthetic_pdf():
    """Stable ASCII PDF bytes; no corpus, generated data or external file read."""
    stream = ('BT /F1 14 Tf 40 740 Td (MODUS / AUTHORED SYNTHETIC RECORD) Tj '
              '0 -30 Td (No real person. Recorded facts only.) Tj '
              f'0 -30 Td ({SPAN}) Tj ET').encode('ascii')
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
               b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
    raw, offsets = b'%PDF-1.4\n', [0]
    for index, content in enumerate(objects, 1):
        offsets.append(len(raw))
        raw += f'{index} 0 obj\n'.encode() + content + b'\nendobj\n'
    start = len(raw)
    raw += b'xref\n0 6\n0000000000 65535 f \n'
    raw += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
    return raw + f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()


def plan():
    value = {'schema': 'modus-entry-meta-smoke-v1', 'model': MODEL,
             'endpoint': 'https://api.meta.ai/v1/chat/completions',
             'synthetic_only': True, 'data_origin': 'authored fixed PDF and authored entry seed',
             'document_sha256': sha256(synthetic_pdf()).hexdigest(),
             'smoke_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
             'bundle_id': BUNDLE_ID, 'policy': POLICY.model_dump(),
             'question': QUESTION, 'as_of': DAY, 'known_at': NOW.isoformat(),
             'max_requests': MAX_REQUESTS, 'max_reserved_output_tokens': MAX_OUTPUT_TOKENS,
             'retries': 0, 'automatic_commit': False,
             'limits': 'No input-token or monetary cap; not benchmark/clinical/held-out evidence.'}
    return {**value, 'plan_id': identity(value)}


class BoundedRequest:
    def __init__(self, request, *, max_requests=MAX_REQUESTS, max_output_tokens=MAX_OUTPUT_TOKENS):
        if type(max_requests) is not int or not 1 <= max_requests <= MAX_REQUESTS:
            raise ValueError('Request budget outside the fixed smoke maximum')
        if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= MAX_OUTPUT_TOKENS:
            raise ValueError('Output reservation outside the fixed smoke maximum')
        self.request, self.max_requests, self.max_output_tokens = request, max_requests, max_output_tokens
        self.calls, self.reserved_output_tokens, self.blocked_requests = 0, 0, 0

    async def __call__(self, payload):
        if payload.get('model') != MODEL:
            raise MetaRequestError('model_mismatch')
        reserve = payload.get('max_completion_tokens')
        if (type(reserve) is not int or reserve < 1 or self.calls >= self.max_requests
                or self.reserved_output_tokens + reserve > self.max_output_tokens):
            self.blocked_requests += 1
            raise MetaRequestError('budget_exceeded')
        self.calls += 1
        self.reserved_output_tokens += reserve
        return await self.request(payload)


def write_new(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')


def load_live_configuration():
    """Called only after real network opt-in; existing environment wins."""
    load_dotenv(ROOT / '.env', override=False)


async def run(output, *, execute=False, allow_network=False, request=None,
              max_requests=MAX_REQUESTS, max_output_tokens=MAX_OUTPUT_TOKENS):
    """Injected transports are always labelled mocks, never measured Meta work."""
    output = Path(output)
    if output.exists():
        raise ValueError('Evidence path already exists; choose a new run path')
    prepared = plan()
    report = {**prepared, 'run_id': str(uuid4()), 'tested_at': datetime.now(timezone.utc).isoformat(),
              'status': 'prepared', 'execution_class': 'preparation', 'provider_requests_made': 0,
              'model_performance_measured': False, 'live_path_verified': False,
              'committed_imports': 0, 'stages': []}
    if not execute:
        write_new(output, report)
        return report
    if request is None and not allow_network:
        report.update(status='blocked', error_kind='network_not_authorized')
        write_new(output, report)
        return report
    mocked = request is not None
    report['execution_class'] = 'mock_transport_test' if mocked else 'live_provider_smoke'
    bounded = BoundedRequest(request or meta_request, max_requests=max_requests, max_output_tokens=max_output_tokens)
    report['execution_limits'] = {'max_requests': max_requests, 'max_reserved_output_tokens': max_output_tokens}
    started = perf_counter()
    try:
        if not mocked:
            load_live_configuration()
        extraction = {'kind': 'document_extraction', 'status': 'failed',
                      'telemetry': {'execution': execution_context('meta', MODEL)}}
        report['stages'].append(extraction)
        rows = await extract_document(synthetic_pdf(), 'authored-entry-smoke.pdf', 'application/pdf',
                                      extraction['telemetry'], request=bounded)
        exact = len(rows) == 1 and all(rows[0].get(key) == value for key, value in EXPECTED.items())
        extraction['exact_authored_fields_and_span'] = exact
        if not exact:
            raise ValueError('Extraction did not match the fixed authored source')
        extraction.update(status='passed', observations=rows, review_required=True, committed=False)
        tool_stage = {'kind': 'record_tool_loop', 'status': 'failed', 'telemetry': {}}
        report['stages'].append(tool_stage)
        with tempfile.TemporaryDirectory(prefix='modus-entry-smoke-') as temp:
            store = RecordStore(Path(temp) / 'authored.db', seed_provider=initial_data, clock=lambda: NOW)
            context = capture(store, DAY, NOW.isoformat())
            before = context['view']
            try:
                response = await agent.live_chat(context, QUESTION, tool_stage['telemetry'], request=bounded)
                inventory = next((step for step in response.get('trace', []) if step['name'] == 'record_inventory'), None)
                expected_text = 'This view contains 9 recorded measurements from 3 documents.'
                valid = (response.get('scope') == context['view']['scope'] and inventory is not None
                         and any(c.get('id') == 'inventory-all' and c.get('text') == expected_text
                                 for c in response.get('claims', [])))
                if not valid:
                    raise ValueError('The fixed record inventory path was not demonstrated')
                tool_stage.update(status='passed', claims=response['claims'], trace=response['trace'], scope=response['scope'])
            finally:
                report['records_unchanged'] = capture(store, DAY, NOW.isoformat())['view'] == before
                with store.connect() as db:
                    report['committed_imports'] = db.execute('SELECT COUNT(*) FROM record_commits').fetchone()[0]
                if not report['records_unchanged'] or report['committed_imports'] != 0:
                    raise ValueError('Read-only smoke boundary was violated')
        report.update(status='passed', live_path_verified=not mocked)
    except Exception as error:
        report.update(status='failed', error_kind=failure_kind(error) if isinstance(error, MetaRequestError) else 'validation_failed')
        if report['stages'] and report['stages'][-1]['status'] == 'failed':
            report['stages'][-1]['error_kind'] = report['error_kind']
    finally:
        report.update(duration_ms=round((perf_counter() - started) * 1000, 2),
                      transport_requests=bounded.calls, provider_requests_attempted=0 if mocked else bounded.calls,
                      provider_requests_made=0 if mocked else None,
                      request_count_basis='Adapter attempts; successful network transmission cannot be established for every failure.',
                      reserved_output_tokens=bounded.reserved_output_tokens, blocked_requests=bounded.blocked_requests)
        write_new(output, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--allow-network', action='store_true', help='Authorize this fixed, potentially billable synthetic smoke')
    parser.add_argument('--out', type=Path, default=ROOT / 'eval' / ('entry-meta-smoke-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json'))
    args = parser.parse_args(argv)
    report = asyncio.run(run(args.out, execute=args.execute, allow_network=args.allow_network))
    print(json.dumps({'status': report['status'], 'execution_class': report['execution_class'], 'report': str(args.out)}))
    return 0 if report['status'] in {'prepared', 'passed'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
