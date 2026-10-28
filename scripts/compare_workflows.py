"""Compare production local routing, fixed-candidate single call and bounded agent."""
import asyncio
from copy import deepcopy
import json
from benchmark_cli import arguments, plan_run
from benchmark_common import event, verify_files
from benchmark_grading import grade_workflow, aggregate
from benchmark_runner import execute_schedule
from benchmark_workflows import METHODS, build_context, candidate_bank, authenticated_claim_bank, run_method


async def main(argv=None):
    args = arguments('workflow', METHODS, argv)
    plan, data, folder, public_plan = plan_run(args, 'workflow')
    if folder is None:
        print(json.dumps(public_plan, indent=2))
        return 0
    try:
        scenarios = {s['id']: s for s in data['scenarios']}
        cases = {case['id']: case for case in data['cases']}
        contexts = {case['id']: build_context(scenarios[case['scenario_id']], case, data.get('captured_at', '2026-10-27T12:00:00Z')) for case in data['cases']}
        trusted = {key: candidate_bank(context, cases[key]['question'])[0] for key, context in contexts.items()}
    except Exception as error:
        event(folder / 'events.jsonl', {'event': 'setup_failed', 'error_type': type(error).__name__})
        (folder / 'summary.json').write_text(json.dumps({'status': 'setup_failed', 'summary': aggregate(plan['schedule'], [])}, indent=2), encoding='utf-8')
        raise ValueError('Benchmark setup failed; no method was executed. See retained setup report.') from None
    async def execute(spec, request):
        case, context = cases[spec['case_id']], deepcopy(contexts[spec['case_id']])
        answer = await run_method(spec['method'], context, case['question'], request=request)
        comparison_scope = {key: context['comparison'][key]['scope'] for key in ('before', 'after')} if context['comparison'] is not None else None
        authenticated = authenticated_claim_bank(context, case['question'], answer, trusted[case['id']])
        return answer, grade_workflow(case, answer, authenticated, context['view']['scope'], comparison_scope,
                                      response_format=plan['response_format'])
    report = await execute_schedule(plan, folder, execute, verify=lambda: verify_files(args.suite, plan['dataset_files_sha256']))
    print(json.dumps({'results': str(folder), **report}, indent=2))
    return 0 if report['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
