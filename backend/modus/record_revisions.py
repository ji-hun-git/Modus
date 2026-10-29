"""Read-only revision projection shared by whole-history and legacy tools."""
from copy import deepcopy
import json


def read_amendments(db, cutoff):
    return [json.loads(row[0]) for row in db.execute(
        'SELECT data FROM history_amendments WHERE available_at<=? ORDER BY available_at,sequence', (cutoff,))]


def revised_facts(facts, amendments):
    rows = {row['id']: {**deepcopy(row), 'revision_id': row.get('revision_id', row['id']),
                     'first_available_at': row.get('first_available_at', row['available_at'])} for row in facts}
    for amendment in amendments:
        if amendment['fact_id'] in rows:
            rows[amendment['fact_id']] = deepcopy(amendment['fact'])
    return list(rows.values())


def revised_observations(observations, amendments, cutoff):
    rows = {row['id']: deepcopy(row) for row in observations}
    for amendment in amendments:
        if amendment['available_at'] > cutoff:
            continue
        for identity in amendment['replaced_observation_ids']:
            rows.pop(identity, None)
        if amendment['observation'] is not None:
            row = deepcopy(amendment['observation'])
            rows[row['id']] = row
    return list(rows.values())
