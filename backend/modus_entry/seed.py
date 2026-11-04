"""Authored checkup examples; no real records or fabricated human/model review."""
from pathlib import Path

from modus.history_ingest import make_history_draft
from modus.record_models import METRICS

ARCHIVE_AVAILABLE_AT = '2026-11-02T12:00:00Z'
ARCHIVE_FILES = tuple(f'authored-checkup-{year}.csv' for year in (2010, 2013, 2016, 2019, 2022, 2024, 2025))


def initial_data():
    sources, observations = [], []
    for day, values in [('2018-04-09', (5.4, 99, 112)), ('2021-04-09', (5.5, 96, 116)), ('2026-10-20', (5.7, 83, 119))]:
        source_id = 'record-' + day
        measured_on = '2021-04-08' if day == '2021-04-09' else day
        rows = []
        for metric, value in zip(('hba1c', 'egfr', 'ldl'), values):
            span = f"{METRICS[metric]['label']} {value} {METRICS[metric]['unit']} {measured_on}"
            rows.append(span)
            observations.append({'id': source_id + '-' + metric, 'source_id': source_id,
                'metric': metric, 'value': value, 'unit': METRICS[metric]['unit'], 'date': measured_on,
                'source_span': span, 'page': 1})
        sources.append({'id': source_id, 'title': 'Recorded measurements · ' + day,
            'provider': 'Authored synthetic example', 'type': 'lab_report', 'date': day,
            'content': 'SYNTHETIC RECORD — no real person.\n' + '\n'.join(rows), 'synthetic': True})
    documents = []
    arrivals = [('checkup-october-2026.csv', '2026-10-23T09:00:00Z')]
    # One explicitly authored archive arrival, separate from the measurement
    # dates. Actual re-imports use their reviewed commit time, never this seed date.
    arrivals.extend((filename, ARCHIVE_AVAILABLE_AT) for filename in ARCHIVE_FILES)
    for filename, available_at in arrivals:
        raw = (Path(__file__).resolve().parents[2] / 'entry/frontend/public/examples' / filename).read_bytes()
        draft = make_history_draft(filename, raw)
        draft['source']['provider'] = 'Authored synthetic example'
        documents.append({'draft': draft, 'raw': raw, 'filename': filename, 'available_at': available_at})
    return sources, observations, documents
