"""Default is a count/hash-only plan. Network and held-out access are explicit."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from benchmark_common import event, fingerprint, require_execution, validate_suite
from benchmark_runner import ROOT, make_plan, prepare_run
from modus.policy import POLICY


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


def plan_run(args, kind):
    # Fail a missing unlock before loading either executable split contents.
    require_execution(args)
    suite = validate_suite(args.suite, kind, selected_split=args.split)
    data = suite[args.split]
    if args.execute and any(m.startswith('meta') for m in args.methods):
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env')
        if not os.getenv('MODEL_API_KEY'):
            raise ValueError('Configure server API access locally before live evaluation')
    model = args.model or os.getenv('MODUS_MODEL', 'muse-spark-1.3')
    if args.execute:
        os.environ['MODUS_MODEL'] = model
    per_output = 4000 if kind == 'documents' else POLICY.max_completion_tokens
    context_bytes = 12 * 1024 * 1024 if kind == 'documents' else 128000
    budget = {'max_requests': args.max_requests, 'max_output_tokens': args.max_output_tokens,
        'max_context_bytes': context_bytes, 'per_request_output_tokens': per_output,
        'max_requests_per_attempt': POLICY.max_rounds, 'max_tool_calls_per_attempt': POLICY.max_tool_calls,
        'interpretation': 'Hard request-count/reserved-output/context-byte caps; no exact input-token or monetary cap. Missing usage stays unknown.'}
    plan = make_plan(kind, suite, args.split, data['cases'], args.methods, args.repeats, model, budget)
    plan['dataset_version'] = data['version']
    families = {s['id']: s['family_id'] for s in data.get('scenarios', [])}
    plan['case_families'] = {case['id']: families[case['scenario_id']] if kind == 'workflow' else case['family_id'] for case in data['cases']}
    plan['plan_id'] = fingerprint({k: v for k, v in plan.items() if k != 'plan_id'})
    public_plan = {'mode': 'execute' if args.execute else 'plan_only', 'plan_id': plan['plan_id'],
        'split': args.split, 'cases': len(data['cases']), 'repeats': args.repeats, 'methods': args.methods,
        'scheduled_attempts': len(plan['schedule']), 'budget': budget, 'freeze_id': suite['freeze_id'],
        'model': model, 'network_requests_made': 0,
        'possible_max_requests': sum(0 if m in {'local_fixed', 'local_parser', 'local_hybrid'} else 1 if m in {'meta_single', 'meta_direct'} else POLICY.max_rounds for m in args.methods) * len(data['cases']) * args.repeats}
    if kind == 'workflow':
        public_plan['response_format'] = plan['response_format']
    if not args.execute:
        if 'local_model' in plan:
            public_plan['local_model'] = plan['local_model']
        return plan, data, None, public_plan
    access = ROOT / 'evaluation/holdout-access.jsonl'
    if args.split == 'holdout':
        previous = [json.loads(line) for line in access.read_text(encoding='utf-8').splitlines()] if access.exists() else []
        exposures = [row for row in previous if row.get('freeze_id') == suite['freeze_id']]
        if exposures and not args.reuse_holdout:
            raise ValueError('This holdout was already opened; --reuse-holdout records reuse, not a fresh test')
        plan['prior_holdout_exposures'] = len(exposures)
    plan['plan_id'] = fingerprint({k: v for k, v in plan.items() if k != 'plan_id'})
    public_plan['plan_id'] = plan['plan_id']
    folder = prepare_run(args.out, plan)
    if args.split == 'holdout':
        access.parent.mkdir(parents=True, exist_ok=True)
        event(access, {'event': 'holdout_opened', 'freeze_id': suite['freeze_id'], 'plan_id': plan['plan_id'],
            'at': datetime.now(timezone.utc).isoformat(), 'reason': args.holdout_reason[:1000],
            'prior_exposures': plan['prior_holdout_exposures']})
    return plan, data, folder, public_plan
