"""Compare retained baseline outputs with new development runs; never load holdout.

This regrades both outputs against identical frozen development gold. It does
not rerun the old CLI (which used to validate both splits) or compare timings
from separate runs as a controlled latency experiment.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from benchmark_common import validate_suite, fingerprint
from benchmark_grading import aggregate, paired_summary, grade_document, grade_workflow
from benchmark_runner import ROOT, source_hashes
from benchmark_workflows import build_context, candidate_bank, authenticated_claim_bank
from modus.bundle import hashes, identity
from modus_entry.runtime import BUNDLE_ID


BASELINES = {'workflow': 'evaluation/results/workflow/20261027T120250Z-315894e98c',
             'documents': 'evaluation/results/documents/20261027T120251Z-e1e6f688e7'}


def read_run(folder):
    folder = Path(folder)
    plan = json.loads((folder/'plan.json').read_text(encoding='utf-8'))
    summary = json.loads((folder/'summary.json').read_text(encoding='utf-8'))
    if plan.get('plan_id') != fingerprint({k:v for k,v in plan.items() if k != 'plan_id'}) or summary.get('plan_id') != plan['plan_id']:
        raise ValueError('Run plan identity mismatch')
    events = [json.loads(line) for line in (folder/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    if plan['split'] != 'dev' or summary['status'] != 'completed' or not summary['source_unchanged'] or not summary['dataset_unchanged'] or summary.get('global_budget_exhausted'):
        raise ValueError('Only complete, unchanged development runs can be compared')
    attempts = [{k:v for k,v in row.items() if k != 'event'} for row in events if row['event'] == 'attempt_finished']
    methods = plan.get('methods', [])
    allowed = {'local_fixed', 'meta_single', 'meta_agent'} if plan.get('kind') == 'workflow' else {'local_parser', 'local_hybrid', 'meta_direct'}
    if not methods or len(methods) != len(set(methods)) or not set(methods) <= allowed or set(methods) != {s['method'] for s in plan['schedule']}:
        raise ValueError('Invalid or mismatched declared methods')
    if not aggregate(plan['schedule'], attempts)['all_attempts_retained']:
        raise ValueError('Comparison cannot hide unfinished attempts')
    return plan, attempts


def compare(kind, candidate_folder, root=ROOT):
    root = Path(root)
    suite = validate_suite(root/'evaluation'/('workflow_v1' if kind == 'workflow' else 'documents_v1'), kind, selected_split='dev')
    data = suite['dev']
    baseline_folder = root/BASELINES[kind]
    before_plan, before = read_run(baseline_folder)
    after_plan, after = read_run(candidate_folder)
    if kind == 'workflow' and before_plan.get('response_format', 'legacy-v1') != after_plan.get('response_format', 'legacy-v1'):
        raise ValueError('Workflow response contracts differ; freeze a reviewed cross-format comparison protocol before comparing scores')
    if after_plan['source_sha256'] != source_hashes(root):
        raise ValueError('Candidate source differs from the current comparison implementation')
    protocol = json.loads((root/'evaluation/baseline-v2/protocol.json').read_text(encoding='utf-8'))
    frozen_root = root/'evaluation/baseline-v2/source'
    if before_plan['source_sha256'] != protocol['source_sha256'] or hashes(frozen_root, [frozen_root/p for p in protocol['source_sha256']]) != protocol['source_sha256']:
        raise ValueError('Baseline does not match its preserved source freeze')
    # The original runtime identity covered the backend, lock, prompts and
    # policy, excluding benchmark scripts. Scope IDs legitimately change with
    # runtime versions; recompute the expected old ID instead of ignoring it.
    baseline_bundle = identity({p:h for p,h in protocol['source_sha256'].items() if not p.startswith('scripts/')})
    for plan in (before_plan, after_plan):
        if plan['kind'] != kind or plan['freeze_id'] != suite['freeze_id'] or any(plan['dataset_files_sha256'].get(p) != h for p,h in suite['files_sha256'].items()):
            raise ValueError('Development cases, inputs or annotations differ')
    baseline_method = 'local_fixed' if kind == 'workflow' else 'local_parser'
    if before_plan['methods'] != [baseline_method] or before_plan['repeats'] != after_plan['repeats']:
        raise ValueError('Unmatched baseline method or repetitions')
    wanted = {(c['id'],r) for c in data['cases'] for r in range(1, before_plan['repeats']+1)}
    for plan in (before_plan, after_plan):
        for method in plan['methods']:
            if {(s['case_id'],s['repeat']) for s in plan['schedule'] if s['method']==method} != wanted:
                raise ValueError('Unmatched development case schedule')
    cases = {case['id']:case for case in data['cases']}
    contexts, trusted = {}, {}
    if kind == 'workflow':
        scenarios = {s['id']:s for s in data['scenarios']}
        for key,case in cases.items():
            context = build_context(scenarios[case['scenario_id']], case, data.get('captured_at','2026-10-27T12:00:00Z'))
            contexts[key] = context
            trusted[key] = candidate_bank(context, case['question'])[0]
    schedule, combined = [], []
    for label, plan, rows in [('baseline', before_plan, before), ('candidate', after_plan, after)]:
        for spec in plan['schedule']:
            schedule.append({**spec,'method':label+'_'+spec['method']})
        for original in rows:
            row = deepcopy(original)
            case = cases[row['case_id']]
            if row['status']=='completed':
                if kind=='documents':
                    grade = grade_document(case,row['result']['observations'])
                else:
                    context = contexts[row['case_id']]
                    def scope(view):
                        if label != 'baseline':
                            return view['scope']
                        bound = view['scope']
                        return {**bound,'scope_id':identity({'as_of':bound['as_of'],'known_at':bound['known_at'],
                            'observations':view['observations'],'sources':view['sources'],'bundle_id':baseline_bundle})}
                    if label == 'baseline' and row['result']['execution']['bundle_id'] != baseline_bundle:
                        raise ValueError('Unexpected original runtime identity')
                    if label == 'candidate' and row['result']['execution']['bundle_id'] != BUNDLE_ID:
                        raise ValueError('Unexpected candidate runtime identity')
                    scopes = {k:scope(context['comparison'][k]) for k in ('before','after')} if context['comparison'] is not None else None
                    authenticated = authenticated_claim_bank(context, case['question'], row['result'], trusted[row['case_id']])
                    grade = grade_workflow(case,row['result'],authenticated,scope(context['view']),scopes,
                                           response_format=plan.get('response_format', 'legacy-v1'))
                if grade['passed'] != row['grade']['passed']:
                    raise ValueError('Regrading changes a recorded outcome; investigate before comparing')
                row['grade'] = grade
            row['method'] = label+'_'+row['method']
            combined.append(row)
    return {'kind':kind,'baseline_plan_id':before_plan['plan_id'],'candidate_plan_id':after_plan['plan_id'],
        'dataset_freeze':suite['freeze_id'],'development_files_sha256':suite['files_sha256'],
        'baseline_outputs_regraded':True,'baseline_outcomes_unchanged':True,
        'summary':aggregate(schedule,combined),'paired':paired_summary(schedule,combined),
        'case_outcomes':[{k:r.get(k) for k in ('case_id','repeat','method','status','grade')} for r in combined],
        'interpretation':'Development-tuned quality comparison of preserved baseline outputs and new candidate execution. Not new blind evidence, a controlled latency comparison, statistical significance or a universal best workflow.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflow',type=Path,required=True)
    parser.add_argument('--documents',type=Path,required=True)
    parser.add_argument('--out',type=Path,default=ROOT/'evaluation/comparisons')
    args=parser.parse_args(argv)
    results=[compare('workflow',args.workflow),compare('documents',args.documents)]
    report={'at':datetime.now(timezone.utc).isoformat(),'heldout_accessed':False,'remote_requests_made':0,'comparisons':results}
    folder=args.out/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10])
    folder.mkdir(parents=True,exist_ok=False)
    (folder/'comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lines=['# Development improvement comparison','','Held-out files were not opened. Both saved baseline and candidate outputs use the same frozen development annotations and current strict grader. Original baseline pass/fail outcomes were checked unchanged.','',
        '| Suite / method | Passed attempts | All trials passed / cases |','|---|---:|---:|']
    for result in results:
        for method,score in result['summary']['methods'].items():
            lines.append(f"| {result['kind']} / {method} | {score['passed']}/{score['planned']} | {score['all_trials_passed_cases']}/{score['unique_cases']} |")
    lines.extend(['','This is development-tuned improvement, not held-out generalization. Baseline output replay is not a new execution or controlled latency comparison. Failed and unsupported attempts remain in denominators. Human annotation review and real Meta comparisons remain pending.'])
    (folder/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'comparison':str(folder),'report_id':fingerprint(report)},indent=2))


if __name__=='__main__':
    main()
