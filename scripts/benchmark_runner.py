"""Append-only attempt ledger, source fingerprints and bounded transport."""
import asyncio
from copy import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter
from uuid import uuid4
from benchmark_common import Budget, BudgetExceeded, canonical, event, fingerprint, PRICING, COST_BASIS, STANDARD_MODEL
from benchmark_grading import aggregate, paired_summary, markdown_report, WORKFLOW_RESPONSE_FORMAT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from modus.policy import POLICY
from modus.provider import meta_request, MetaRequestError, failure_kind, safe_identifier, validate_completion
from modus.bundle import hashes, installed_environment


def source_hashes(root=ROOT):
    paths = list((root / 'backend/modus_entry').glob('*.py'))
    paths += [root / 'backend/modus' / name for name in ('__init__.py', 'record_models.py', 'record_store.py', 'record_conflicts.py', 'ontology.py', 'record_retrieval.py', 'ingest.py', 'temporal.py', 'provider.py', 'extraction.py', 'policy.py', 'bundle.py', 'local_ocr.py', 'ocr_text.py',
        'record_history.py', 'record_history_view.py', 'record_history_models.py', 'record_units.py',
        'history_ingest.py', 'record_extraction.py', 'record_extraction_models.py', 'record_document_input.py')]
    paths += list((root / 'scripts').glob('benchmark_*.py'))
    paths += [root / 'scripts/compare_workflows.py', root / 'scripts/evaluate_heldout_documents.py',
        root / 'entry/prompts/records.md', root / 'entry/prompts/history.md', root / 'prompts/extract.md', root / 'config/agent-policy.json', root / 'backend/requirements.lock.txt']
    paths += [root / name for name in ('scripts/compare_development.py', 'scripts/development_guard.py', 'config/teleocr.json', 'scripts/teleocr_runtime.py',
        'scripts/teleocr_document_worker.py', 'scripts/teleocr_assets.py', 'scripts/requirements-ocr.lock.txt')]
    return hashes(root, paths)


def make_schedule(cases, methods, repeats):
    if not 1 <= repeats <= 10 or not methods or len(methods) != len(set(methods)):
        raise ValueError('Invalid repeat count or methods')
    schedule = []
    for repeat in range(1, repeats + 1):
        # Prespecified rotation counters order effects without selecting survivors.
        ordered = cases[repeat - 1:] + cases[:repeat - 1]
        for index, case in enumerate(ordered):
            shift = (index + repeat - 1) % len(methods)
            for method in methods[shift:] + methods[:shift]:
                schedule.append({'case_id': case['id'], 'repeat': repeat, 'method': method})
    return schedule


class GuardedTransport:
    def __init__(self, global_budget, model, ledger, attempt_id, *, max_request_output=None, max_context_bytes=128000, max_requests=None, transport=None):
        self.global_budget, self.model, self.ledger, self.attempt_id = global_budget, model, ledger, attempt_id
        cap = max_request_output or POLICY.max_completion_tokens
        self.per_request_output = cap
        request_cap = POLICY.max_rounds if max_requests is None else max_requests
        self.local = Budget(request_cap, request_cap * cap, max_context_bytes)
        self.transport = transport or meta_request
        self.calls = []
        self.global_budget_exhausted = False

    async def __call__(self, payload):
        if (payload.get('model') != self.model or type(payload.get('max_completion_tokens')) is not int
                or payload['max_completion_tokens'] > self.per_request_output):
            event(self.ledger, {'event': 'request_denied', 'attempt_id': self.attempt_id,
                'reason': 'locked_request_mismatch', 'error_kind': 'budget_exceeded'})
            raise BudgetExceeded('Model or per-request output cap differs from the locked plan')
        # Validate both budgets before mutating either reservation.
        try:
            copy(self.local).reserve(payload)
        except BudgetExceeded:
            event(self.ledger, {'event': 'request_denied', 'attempt_id': self.attempt_id,
                'reason': 'attempt_budget_exhausted', 'error_kind': 'budget_exceeded'})
            raise
        try:
            copy(self.global_budget).reserve(payload)
        except BudgetExceeded:
            self.global_budget_exhausted = True
            event(self.ledger, {'event': 'request_denied', 'attempt_id': self.attempt_id,
                'reason': 'global_budget_exhausted', 'error_kind': 'budget_exceeded',
                'estimated_usd_accounted': float(self.global_budget.estimated_usd_accounted),
                'max_estimated_usd': self.global_budget.max_estimated_usd})
            raise
        local_reservation = self.local.reserve(payload)
        reservation = self.global_budget.reserve(payload)
        number = self.local.calls
        event(self.ledger, {'event': 'request_started', 'attempt_id': self.attempt_id, 'number': number,
            'model': self.model, 'payload_sha256': fingerprint(payload), 'reserved_output_tokens': payload['max_completion_tokens'],
            'serialized_request_bytes': len(canonical(payload).encode('utf-8')),
            'reserved_estimated_usd': float(reservation) if reservation is not None else None, 'cost_reservation_basis': COST_BASIS})
        started = perf_counter()
        item = {'number': number, 'status': 'failed', 'usage': None, 'model': self.model,
            'response_id': None, 'request_id': None, 'http_status': None, 'error_kind': None,
            'reserved_estimated_usd': float(reservation) if reservation is not None else None}
        try:
            response = await self.transport(payload)
            if not isinstance(response, dict):
                raise MetaRequestError('invalid_envelope')
            http_status = getattr(response, 'http_status', None)
            item.update(response_id=safe_identifier(response.get('id')),
                request_id=safe_identifier(getattr(response, 'request_id', None)),
                http_status=http_status if type(http_status) is int and 100 <= http_status <= 599 else None)
            usage = response.get('usage') if isinstance(response.get('usage'), dict) else {}
            item.update(response_sha256=fingerprint(response), usage={k: v for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')
                if type(v := usage.get(k)) is int and v >= 0} or None)
            returned = response.get('model')
            if isinstance(returned, str):
                item['returned_model'] = safe_identifier(returned)
                if returned != self.model:
                    raise MetaRequestError('model_mismatch')
            choices = response.get('choices')
            finishes = [c.get('finish_reason') for c in choices if isinstance(c, dict)] if isinstance(choices, list) else []
            item['finish_reasons'] = [reason if reason is None or isinstance(reason, str)
                and reason in {'stop', 'tool_calls', 'function_call', 'length', 'content_filter'} else 'unrecognized' for reason in finishes]
            validate_completion(response)
            choices = choices or []
            # Retain tool names/argument hashes for failures without raw errors or prose.
            allowed_names = {tool.get('function', {}).get('name') for tool in payload.get('tools', []) if isinstance(tool, dict)}
            messages = [c.get('message', {}) for c in choices if isinstance(c, dict)]
            item['tool_requests'] = []
            for message in messages:
                for call in message.get('tool_calls', []) if isinstance(message.get('tool_calls', []), list) else []:
                    function = call.get('function', {}) if isinstance(call, dict) else {}
                    if isinstance(function, dict):
                        name = function.get('name')
                        item['tool_requests'].append({'name': name if isinstance(name, str) and name in allowed_names else 'not_allowlisted',
                            'arguments_sha256': fingerprint(function.get('arguments'))})
            item['status'] = 'completed'
            return response
        except Exception as error:
            item['error_kind'] = failure_kind(error)
            if item['error_kind'] == 'incomplete':
                item['response_rejected'] = 'incomplete_or_filtered_output'
            elif item['error_kind'] == 'refusal':
                item['response_rejected'] = 'provider_refusal'
            if isinstance(error, MetaRequestError):
                if error.http_status is not None:
                    item['http_status'] = error.http_status
                if error.request_id is not None:
                    item['request_id'] = error.request_id
            raise
        finally:
            settlement_usage = item['usage'] if item['error_kind'] != 'model_mismatch' else None
            item.update(self.global_budget.settle(reservation, settlement_usage))
            self.local.settle(local_reservation, settlement_usage)
            if item['error_kind'] == 'model_mismatch':
                item['cost_basis'] = 'preflight_reservation_retained_returned_model_price_unqualified'
            if item.get('estimated_cost_limit_exceeded'):
                self.global_budget_exhausted = True
            item['duration_ms'] = round((perf_counter() - started) * 1000, 3)
            self.calls.append(item)
            event(self.ledger, {'event': 'request_finished', 'attempt_id': self.attempt_id, **item})


def combined_usage(calls):
    if not calls:
        return None
    return {key: sum(c['usage'][key] for c in calls)
            if all(isinstance(c.get('usage'), dict) and type(c['usage'].get(key)) is int for c in calls) else None
            for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')}


def prepare_run(output_root, plan):
    folder = Path(output_root) / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid4().hex[:10])
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    return folder


async def execute_schedule(plan, folder, execute, *, transport=None, verify=None):
    global_budget = Budget(plan['budget']['max_requests'], plan['budget']['max_output_tokens'], plan['budget']['max_context_bytes'],
        max_estimated_usd=plan['budget'].get('max_estimated_usd'))
    attempts, ledger = [], folder / 'events.jsonl'
    initial = source_hashes()
    if initial != plan['source_sha256']:
        raise ValueError('Benchmark code changed after plan creation')
    for spec in plan['schedule']:
        attempt_id = uuid4().hex
        event(ledger, {'event': 'attempt_started', 'attempt_id': attempt_id, **spec})
        guarded = GuardedTransport(global_budget, plan['model'], ledger, attempt_id,
            max_request_output=plan['budget']['per_request_output_tokens'], max_context_bytes=plan['budget']['max_context_bytes'],
            max_requests=plan['budget'].get('method_request_limits', {}).get(spec['method']), transport=transport)
        item = {**spec, 'attempt_id': attempt_id, 'status': 'failed'}
        started = perf_counter()
        method_started = None
        try:
            if source_hashes() != initial:
                raise ValueError('Benchmark source changed during execution')
            if verify is not None:
                verify()
            method_started = perf_counter()
            value, grade = await execute(spec, guarded)
            item.update(status='completed', result=value, grade=grade)
        except Exception as error:
            item.update(error_type=type(error).__name__, error='Attempt did not produce a validated result. See bounded request metadata.', grade={'passed': False})
            from modus.local_ocr import LocalOCRError
            if isinstance(error, LocalOCRError) and isinstance(getattr(error, 'diagnostic', None), dict):
                item['local_model_diagnostic'] = error.diagnostic
            if isinstance(error, LocalOCRError) and isinstance(getattr(error, 'telemetry', None), dict):
                item['local_model_telemetry'] = error.telemetry
        finished = perf_counter()
        item.update(duration_ms=round((finished - method_started) * 1000, 3) if method_started is not None else None,
                    integrity_check_ms=round(((method_started or finished) - started) * 1000, 3),
                    total_attempt_ms=round((finished - started) * 1000, 3), requests=guarded.local.calls,
                    global_budget_exhausted=guarded.global_budget_exhausted,
                    reserved_output_tokens=guarded.local.output_reserved, usage=combined_usage(guarded.calls), provider_calls=guarded.calls,
                    estimated_cost_usd=float(guarded.local.estimated_usd_accounted)
                        if plan['model'] == STANDARD_MODEL or not guarded.calls else None)
        if spec['method'] == 'local_hybrid' and item['status'] == 'completed':
            telemetry = item['result'].get('telemetry', {})
            if item['result'].get('mode') == 'local-teleocr':
                input_count, output_count = telemetry.get('input_tokens'), telemetry.get('output_tokens')
                if all(type(n) is int and n >= 0 for n in (input_count, output_count)):
                    item['usage'] = {'prompt_tokens': input_count, 'completion_tokens': output_count, 'total_tokens': input_count + output_count}
            else:
                item['usage'] = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        attempts.append(item)
        event(ledger, {'event': 'attempt_finished', **item})
        # Retain a useful partial report even if a later attempt/process is interrupted.
        report = {'status': 'running', 'plan_id': plan['plan_id'], 'summary': aggregate(plan['schedule'], attempts), 'paired': paired_summary(plan['schedule'], attempts)}
        (folder / 'summary.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    valid = source_hashes() == initial
    dataset_valid = True
    try:
        if verify is not None:
            verify()
    except Exception:
        dataset_valid = False
    report.update(status='completed' if valid else 'invalid_source_changed',
        source_unchanged=valid, dataset_unchanged=dataset_valid, requests_reserved=global_budget.calls, output_tokens_reserved=global_budget.output_reserved,
        estimated_cost_usd=float(global_budget.estimated_usd_accounted)
            if plan['model'] == STANDARD_MODEL or not global_budget.calls else None,
        max_estimated_usd=global_budget.max_estimated_usd,
        cost_reservation_basis=COST_BASIS, estimate_pricing=PRICING if plan['model'] == STANDARD_MODEL else None,
        provider_requests_made=0 if transport is not None else sum(len(a['provider_calls']) for a in attempts),
        execution_class='mock_transport_test' if transport is not None else 'provider_or_local',
        model_performance_measured=transport is None and any(m.startswith('meta') for m in plan['methods']) and any(c['status'] == 'completed' for a in attempts for c in a['provider_calls']))
    if not dataset_valid:
        report['status'] = 'invalid_dataset_changed'
    report['local_model_attempts_completed'] = sum(a.get('result', {}).get('mode') == 'local-teleocr' and a.get('result', {}).get('telemetry', {}).get('status') == 'completed' for a in attempts)
    local_calls = [call for a in attempts for call in a.get('result', {}).get('telemetry', a.get('local_model_telemetry', {})).get('attempts', [])]
    report['local_inference_attempts'] = len(local_calls)
    report['local_inference_failures_retained'] = sum(call.get('status') != 'completed' for call in local_calls)
    report['model_performance_measured'] = report['model_performance_measured'] or (transport is None and bool(report['local_model_attempts_completed']))
    report['global_budget_exhausted'] = any(a['global_budget_exhausted'] for a in attempts)
    report['eligible_for_paired_interpretation'] = len(plan['methods']) > 1 and valid and dataset_valid and not report['global_budget_exhausted'] and report['summary']['all_attempts_retained']
    (folder / 'summary.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (folder / 'report.md').write_text(markdown_report(report, plan, attempts), encoding='utf-8')
    return report


def make_plan(kind, suite, split, cases, methods, repeats, model, budget):
    plan = {'format': 'modus-benchmark-plan-v1', 'kind': kind, 'freeze_id': suite['freeze_id'], 'dataset_files_sha256': {**suite['files_sha256'], 'freeze.json': suite['freeze_id']}, 'split': split,
        'methods': methods, 'repeats': repeats, 'model': model, 'budget': budget,
        'schedule': make_schedule(cases, methods, repeats), 'source_sha256': source_hashes(),
        'runtime': installed_environment(), 'model_version_basis': 'mutable provider alias; returned identifiers retained when supplied',
        'interpretation': 'No model winner inferred without completed paired real runs; model-authored gold awaits independent human review.'}
    if kind == 'workflow':
        plan['response_format'] = WORKFLOW_RESPONSE_FORMAT
    if 'local_hybrid' in methods:
        config = json.loads((ROOT/'config/teleocr.json').read_text(encoding='utf-8'))
        plan['local_model'] = {key:config[key] for key in ('model','revision','prompt_version','max_pixels','max_input_pixels','max_new_tokens','repetition_penalty')}
        plan['local_model'].update(strategy_version=config.get('strategy_version'), fallback_max_pixels=config.get('fallback_max_pixels'), max_local_attempts_per_document=2)
        plan['local_model'].update(max_input_tokens_per_page=4096, max_pages=12, worker_timeout_seconds=180,
            max_document_bytes=8*1024*1024, route='PDF text parser; image inputs use explicit local model')
    plan['plan_id'] = fingerprint(plan)
    return plan
