"""Small authored workflow/temporal cases, with an event-only retrieval ablation."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from modus.record_store import RecordStore
from modus.ingest import make_draft
from modus_entry.seed import initial_data
from modus_entry.tools import capture
from modus_entry.agent import offline_chat
from modus_entry.runtime import BUNDLE_ID


def evaluate():
    with TemporaryDirectory(prefix='modus-record-eval-') as folder:
        store = RecordStore(Path(folder) / 'records.db', seed_provider=initial_data,
            clock=lambda: datetime(2026, 10, 27, 12, tzinfo=timezone.utc))
        raw = b'metric,value,unit,date\negfr,82,mL/min/1.73m2,2021-04-08\n'
        draft = make_draft('late.csv', raw)
        store.add_draft(draft, raw=raw, filename='late.csv', mime='text/csv')
        review = [{k: o[k] for k in ('id', 'metric', 'value', 'unit', 'date')} for o in draft['observations']]
        store.commit_draft(draft['id'], review)
        queries = [('before-any', '2017-12-31', '2017-12-31T23:59:59Z', 0),
                   ('early-history', '2018-12-31', '2018-12-31T23:59:59Z', 3),
                   ('as-known-2021', '2021-12-31', '2021-12-31T23:59:59Z', 6),
                   ('later-period-earlier-knowledge', '2026-10-27', '2021-12-31T23:59:59Z', 6),
                   ('2021-reconstruction', '2021-12-31', None, 7),
                   ('all-current', '2026-10-27', None, 10)]
        temporal = []
        for name, day, known, expected in queries:
            actual = capture(store, day, known)['view']['counts']['measurements']
            event_only = capture(store, day)['view']['counts']['measurements']
            temporal.append({'id': name, 'expected_count': expected, 'dual_time_count': actual,
                'event_only_count': event_only, 'passed': actual == expected, 'event_only_passed': event_only == expected})
        context = capture(store, '2021-12-31', None, '2021-12-31T23:59:59Z')
        questions = [('How many records?', 'record_inventory'), ('Which values disagree?', 'record_conflicts'),
            ('Which records arrived later?', 'compare_record_snapshots'), ('Should I change treatment?', None),
            ('What diagnosis does this prove?', None)]
        routes = []
        for message, expected in questions:
            answer = offline_chat(context, message)
            actual = answer['trace'][0]['name'] if answer['trace'] else None
            routes.append({'question': message, 'expected_tool': expected, 'actual_tool': actual,
                'passed': actual == expected and answer['mode'] == 'offline' and answer['execution']['requested_model'] is None})
        return {'status': 'passed' if all(c['passed'] for c in temporal + routes) else 'failed',
            'generated_at': datetime.now(timezone.utc).isoformat(), 'bundle_id': BUNDLE_ID,
            'scope': 'Six authored temporal and five deterministic routing development cases; no independent quality benchmark or live model call.',
            'temporal': temporal, 'routing': routes,
            'summary': {'dual_time_passed': sum(c['passed'] for c in temporal), 'event_only_passed': sum(c['event_only_passed'] for c in temporal),
                        'temporal_cases': len(temporal), 'routing_passed': sum(c['passed'] for c in routes), 'routing_cases': len(routes)},
            'live_meta': 'not run', 'model_workflow_comparison': 'fixed-route vs live selector quality/cost/reliability unmeasured'}


if __name__ == '__main__':
    report = evaluate()
    output = ROOT / 'entry/eval/results.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('status', 'scope', 'summary', 'live_meta')}, indent=2))
    raise SystemExit(0 if report['status'] == 'passed' else 1)
