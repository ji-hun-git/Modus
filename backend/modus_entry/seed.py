"""Nine authored recorded facts. No care, medication, genetic or reference fixture."""
from modus.record_models import METRICS


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
    return sources, observations
