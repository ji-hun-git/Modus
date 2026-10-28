"""Independent evaluation runner; callers must explicitly opt into network."""
from datetime import datetime, timezone
import os
from pathlib import Path
from uuid import uuid4

from .aggregate import agreement, case_report, scoreboard
from .budget import Book, BudgetDenied, write_new
from .prompts import cache_identity, prompt
from .schema import Assessment, ModelLock, canonical, fingerprint, json_loads, load_inputs, output_schema, validate_judgement, checked_path
from .transport import JudgeError, parse, payload, send
from .repro import snapshot
from . import code_checks


def scrub(value, secret):
    if isinstance(value, str):
        return value.replace(secret, '[REDACTED]') if secret else value
    if isinstance(value, list):
        return [scrub(v, secret) for v in value]
    if isinstance(value, dict):
        return {k: scrub(v, secret) for k, v in value.items()}
    return value


def read_human(path, case_ids):
    if path is None:
        return None
    body = json_loads(checked_path(path).read_text(encoding='utf-8'))
    if set(body) != {'reviewer', 'source', 'labels'} or body['reviewer'] != 'Jason' or body['source'] != 'human':
        raise ValueError('Human agreement requires explicitly supplied Jason labels')
    found, labels = set(), []
    for row in body['labels']:
        if not isinstance(row, dict) or row.get('case_id') not in case_ids:
            raise ValueError('Unknown human-labelled case')
        parsed = Assessment.model_validate({k: v for k, v in row.items() if k != 'case_id'})
        key = row['case_id'], parsed.criterion
        if key in found:
            raise ValueError('Duplicate human label')
        found.add(key)
        labels.append({'case_id': row['case_id'], **parsed.model_dump()})
    if not labels:
        raise ValueError('An empty file is not supplied human agreement evidence')
    return labels


def load_cache(path, key, provider, criteria, execution_class):
    value = json_loads(path.read_text(encoding='utf-8'))
    if (value.get('cache_key') != key or value.get('provider') != provider.provider
            or value.get('model') != provider.model or value.get('execution_class') != execution_class
            or value.get('status') != 'completed'
            or fingerprint(value.get('judgement')) != value.get('judgement_sha256')):
        raise ValueError('Cached judgement identity mismatch')
    validate_judgement(canonical(value['judgement']), criteria)
    return {**value, 'status': 'cache_hit', 'new_provider_requests': 0}


async def judge(provider, case, images, lock, root, book, run_id, execution_class, transport):
    system, user, criteria = prompt(case, images, lock.rubric_version)
    schema = output_schema(criteria)
    key = cache_identity(provider, system, user, images, lock.rubric_version, schema, execution_class)
    cache = root / 'cache' / (key + '.json')
    result = {'provider': provider.provider, 'family': provider.family, 'model': provider.model,
        'execution_class': execution_class, 'cache_key': key, 'status': 'failed', 'new_provider_requests': 0}
    if cache.exists():
        try:
            return load_cache(cache, key, provider, criteria, execution_class)
        except (ValueError, OSError):
            return {**result, 'status': 'invalid_cache', 'error_kind': 'invalid_cache_no_automatic_retry'}
    secret = os.getenv(provider.env_key, '') if transport is None else 'explicit-mock-not-a-secret'
    if not secret:
        return {**result, 'status': 'unavailable', 'error_kind': 'missing_process_credential'}
    request = payload(provider, system, user, images, schema)
    try:
        request_id, reserved = book.reserve(provider, run_id, key, request, len(images))
    except BudgetDenied as error:
        return {**result, 'status': 'budget_denied', 'error_kind': str(error)}
    result.update(new_provider_requests=1 if transport is None else 0, request_attempted=True,
                  reservation_id=request_id, reserved_estimated_usd=float(reserved))
    usage = None
    try:
        envelope = await (transport(provider, request, secret) if transport else send(provider, request, secret))
        judgement, metadata = parse(provider, envelope, criteria)
        usage = metadata['usage']
        result.update(status='completed', judgement=judgement, telemetry=metadata)
    except JudgeError as error:
        usage = error.metadata.get('usage')
        result.update(status='failed', error_kind=error.kind, telemetry=error.metadata)
    except Exception as error:
        result.update(status='failed', error_kind='unexpected_' + type(error).__name__)
    result = scrub(result, secret)
    # A settle failure leaves the original durable reservation in force. Never
    # cache such a result as completed or spend again to repair it automatically.
    try:
        result['estimated_cost_usd'] = book.settle(provider, request_id, reserved, usage, result['status'])
    except Exception:
        result.update(status='failed', error_kind='settlement_failed_reservation_retained')
    if result['status'] == 'completed':
        result['judgement_sha256'] = fingerprint(result['judgement'])
        try:
            write_new(cache, result)
        except OSError:
            result.update(status='failed', error_kind='cache_persistence_failed_no_retry')
    write_new(root / 'attempts' / (request_id + '.json'), result)
    return result


async def run(input_path, models_path, *, execute=False, allow_network=False,
              private_root, report_root, human_path=None, transport=None):
    if execute and not allow_network and transport is None:
        raise ValueError('Network execution requires --execute and --allow-network')
    models_path = checked_path(models_path)
    lock = ModelLock.model_validate(json_loads(models_path.read_text(encoding='utf-8')))
    inputs, cases = load_inputs(input_path)
    human = read_human(human_path, {c.id for c, _ in cases})
    plan = {'schema': 'modus-jury-plan-v1', 'rubric_version': lock.rubric_version,
        **snapshot(cases, lock.rubric_version),
        'model_lock': lock.model_dump(mode='json', by_alias=True),
        'model_lock_sha256': fingerprint(lock.model_dump(mode='json', by_alias=True)),
        'input_sha256': fingerprint(inputs.model_dump(mode='json', by_alias=True)),
        'cases': [{'id': c.id, 'criteria': prompt(c, images, lock.rubric_version)[2],
            'image_sha256': [i['sha256'] for i in images]} for c, images in cases],
        'max_new_requests': len(cases) * 3, 'synthetic_only': True, 'retries': 0,
        'providers': [{'provider': p.provider, 'model': p.model, 'prior_spend_usd': p.prior_spend_usd,
            'ceiling_usd': p.ceiling_usd, 'allocation_usd': p.allocation_usd} for p in lock.providers]}
    plan['plan_id'] = fingerprint(plan)
    if not execute:
        return {'mode': 'prepare_only', 'provider_requests_made': 0, **plan}
    for case, _ in cases:
        expected = {'C': code_checks.faithfulness(case.artifact), 'E': code_checks.extraction(case.artifact)}
        if any(case.deterministic[key].model_dump() != expected[key] for key in ('C', 'E')):
            raise ValueError('Supplied code verdict differs from recomputation; refresh before execution')
    execution_class = 'mock' if transport is not None else 'live'
    root = checked_path(private_root) / execution_class
    for name in ('cache', 'attempts', 'runs'):
        (root / name).mkdir(parents=True, exist_ok=True)
    book, run_id = Book(root), uuid4().hex
    run_folder = root / 'runs' / run_id
    run_folder.mkdir()
    write_new(run_folder / 'config.json', {'run_id': run_id, 'execution_class': execution_class, **plan})
    write_new(root / 'runs' / (run_id + '-plan.json'), plan)
    reports, queues, raw_results = [], [], {}
    for case, images in cases:
        results = {}
        for provider in lock.providers:
            try:
                results[provider.provider] = await judge(provider, case, images, lock, root, book, run_id, execution_class, transport)
            except Exception as error:
                results[provider.provider] = {'status': 'failed', 'error_kind': 'harness_' + type(error).__name__, 'new_provider_requests': 0}
        raw_results[case.id] = results
        report, queue = case_report(case, results, prompt(case, images, lock.rubric_version)[2])
        reports.append(report)
        queues.extend(queue)
    report = {'schema': 'modus-jury-report-v1', 'run_id': run_id, 'plan_id': plan['plan_id'],
        'created_at': datetime.now(timezone.utc).isoformat(), 'execution_class': execution_class,
        'provider_requests_made': sum(e['event'] == 'reserved' and e.get('run_id') == run_id
            for e in book.events()) if transport is None else 0,
        'cases': reports, 'human_review_queue_count': len(queues),
        'agreement': agreement(raw_results, human), 'costs': book.summary(lock.providers, run_id),
        'blinding': 'Provider/model text metadata is removed; screenshot pixels can still expose branding. Visual blinding is incomplete.',
        'scope': 'Synthetic evaluation-only jury; no clinical validation or universal best-model claim. Product remains Meta-only.'}
    write_new(root / 'runs' / (run_id + '-results.json'), raw_results)
    write_new(root / 'runs' / (run_id + '-Jason-queue.json'), queues)
    write_new(root / 'runs' / (run_id + '-report.json'), report)
    out = checked_path(report_root)
    out.mkdir(parents=True, exist_ok=True)
    write_new(out / ('jury-' + run_id + '.json'), report)
    (out / ('jury-' + run_id + '.md')).write_text(scoreboard(report), encoding='utf-8')
    return report
