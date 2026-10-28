"""Default is a count/hash-only plan. Network and held-out access are explicit."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4
from benchmark_common import (Budget, event, fingerprint, require_execution, validate_suite,
    safe_path, PRICING, COST_BASIS, STANDARD_MODEL)
from benchmark_runner import ROOT, make_plan, prepare_run
from modus.policy import POLICY
from modus.provider import meta_credential


def arguments(kind, methods, argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, default=ROOT / 'evaluation' / ('workflow_v1' if kind == 'workflow' else 'documents_v1'))
    parser.add_argument('--split', choices=['dev', 'holdout'], default='dev')
    parser.add_argument('--methods', default=','.join(methods))
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--allow-network', action='store_true')
    parser.add_argument('--max-requests', type=int, default=0)
    parser.add_argument('--max-output-tokens', type=int, default=0)
    parser.add_argument('--max-estimated-usd', type=float, default=None,
        help='Optional Standard-price estimate ceiling; byte-proxy reservation, not an invoice guarantee')
    parser.add_argument('--model', default=None)
    parser.add_argument('--unlock-holdout', action='store_true')
    parser.add_argument('--holdout-reason', default='')
    parser.add_argument('--reuse-holdout', action='store_true')
    parser.add_argument('--out', type=Path, default=ROOT / 'evaluation/results' / kind)
    args = parser.parse_args(argv)
    args.methods = args.methods.split(',')
    if not set(args.methods) <= set(methods) or len(args.methods) != len(set(args.methods)) or not 1 <= args.repeats <= 10:
        raise ValueError('Choose known distinct methods and 1–10 repetitions')
    require_execution(args)
    return args


def _admit_holdout(args, kind, model, budget):
    """Read freeze metadata only, then persist admission before selected inputs."""
    freeze_id = hashlib.sha256(safe_path(args.suite, 'freeze.json').read_bytes()).hexdigest()
    access = ROOT / 'evaluation/holdout-access.jsonl'
    access.parent.mkdir(parents=True, exist_ok=True)
    lock = access.with_name('.holdout-admission.lock')
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError('Another or interrupted holdout admission exists; inspect its ledger before any retry') from None
    try:
        previous = [json.loads(line) for line in access.read_text(encoding='utf-8').splitlines()] if access.exists() else []
        exposures = [row for row in previous if row.get('freeze_id') == freeze_id
            and row.get('event') in {'holdout_opened', 'holdout_opening_started'}]
        if exposures and not args.reuse_holdout:
            raise ValueError('This holdout was already admitted; failed admissions also count. Reuse requires an explicit recorded override.')
        admission = {'admission_id': uuid4().hex, 'freeze_id': freeze_id,
            'kind': kind, 'methods': args.methods, 'repeats': args.repeats, 'model': model, 'budget': budget,
            'at': datetime.now(timezone.utc).isoformat(), 'reason': args.holdout_reason[:1000],
            'prior_exposures': len(exposures), 'gold_review_status': 'AI-authored; independent human review pending'}
        event(access, {'event': 'holdout_opening_started', **admission})
    finally:
        os.close(handle)
        lock.unlink()
    return access, admission


def _make_ready_plan(args, kind, model, budget, admission):
    suite = validate_suite(args.suite, kind, selected_split=args.split,
        expected_freeze_id=admission['freeze_id'] if admission else None)
    if admission and suite['freeze_id'] != admission['freeze_id']:
        raise ValueError('Freeze metadata changed after admission')
    data = suite[args.split]
    plan = make_plan(kind, suite, args.split, data['cases'], args.methods, args.repeats, model, budget)
    plan['dataset_version'] = data['version']
    plan['gold_review_status'] = 'AI-authored; independent human review pending'
    if admission:
        plan.update(holdout_admission_id=admission['admission_id'], prior_holdout_exposures=admission['prior_exposures'])
    if kind == 'documents':
        plan['grading_scope'] = 'Legacy three-metric observation contract; broader generic fields from meta_record_review are retained but not graded as eight-kind extraction accuracy.'
    families = {s['id']: s['family_id'] for s in data.get('scenarios', [])}
    plan['case_families'] = {case['id']: families[case['scenario_id']] if kind == 'workflow' else case['family_id'] for case in data['cases']}
    plan['plan_id'] = fingerprint({k: v for k, v in plan.items() if k != 'plan_id'})
    public_plan = {'mode': 'execute' if args.execute else 'plan_only', 'plan_id': plan['plan_id'],
        'split': args.split, 'cases': len(data['cases']), 'repeats': args.repeats, 'methods': args.methods,
        'scheduled_attempts': len(plan['schedule']), 'budget': budget, 'freeze_id': suite['freeze_id'],
        'model': model, 'network_requests_made': 0,
        'possible_max_requests': sum(0 if m in {'local_fixed', 'local_parser', 'local_hybrid'}
            else 1 if m in {'meta_single', 'meta_direct'} else 2 if m == 'meta_record_review'
            else POLICY.max_rounds for m in args.methods) * len(data['cases']) * args.repeats}
    if kind == 'workflow':
        public_plan['response_format'] = plan['response_format']
    if not args.execute:
        if 'local_model' in plan:
            public_plan['local_model'] = plan['local_model']
        return plan, data, None, public_plan
    return plan, data, prepare_run(args.out, plan), public_plan


def plan_run(args, kind):
    # No selected inputs may be read before execution, budget, model and access
    # preflight succeeds. Failed admission is durably retained, not a fresh retry.
    require_execution(args)
    if args.execute and any(m.startswith('meta') for m in args.methods):
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env')
        if not meta_credential():
            raise ValueError('Configure server API access locally before live evaluation')
    model = args.model or os.getenv('MODUS_MODEL', 'muse-spark-1.3')
    if args.execute:
        os.environ['MODUS_MODEL'] = model
    per_output = 4000 if kind == 'documents' else POLICY.max_completion_tokens
    context_bytes = 12 * 1024 * 1024 if kind == 'documents' else 128000
    estimate_limit = getattr(args, 'max_estimated_usd', None)
    Budget(args.max_requests, args.max_output_tokens, context_bytes, max_estimated_usd=estimate_limit)
    if estimate_limit is not None and model != STANDARD_MODEL:
        raise ValueError('Estimated-dollar cap requires muse-spark-1.3 Standard with the verified price')
    budget = {'max_requests': args.max_requests, 'max_output_tokens': args.max_output_tokens,
        'max_estimated_usd': estimate_limit, 'estimate_pricing': PRICING if model == STANDARD_MODEL else None, 'cost_reservation_basis': COST_BASIS,
        'max_context_bytes': context_bytes, 'per_request_output_tokens': per_output,
        'method_request_limits': {method: 0 if method in {'local_fixed', 'local_parser', 'local_hybrid'}
            else 1 if method in {'meta_single', 'meta_direct'} else 2 if method == 'meta_record_review'
            else POLICY.max_rounds for method in args.methods},
        'max_requests_per_attempt': POLICY.max_rounds, 'max_tool_calls_per_attempt': POLICY.max_tool_calls,
        'interpretation': 'Hard request-count/reserved-output/context-byte caps plus optional estimated-dollar admission cap. Unknown usage retains its full cost reservation; this is not an invoice/tokenizer guarantee.'}
    access, admission = None, None
    if args.split == 'holdout':
        access, admission = _admit_holdout(args, kind, model, budget)
    try:
        result = _make_ready_plan(args, kind, model, budget, admission)
    except Exception as error:
        if admission:
            event(access, {'event': 'holdout_opening_failed', 'admission_id': admission['admission_id'],
                'freeze_id': admission['freeze_id'], 'error_type': type(error).__name__,
                'at': datetime.now(timezone.utc).isoformat(), 'input_access_may_have_occurred': True})
        raise
    if admission:
        event(access, {'event': 'holdout_opening_completed', 'admission_id': admission['admission_id'],
            'freeze_id': admission['freeze_id'], 'plan_id': result[0]['plan_id'],
            'at': datetime.now(timezone.utc).isoformat()})
    return result
