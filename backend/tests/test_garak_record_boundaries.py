"""Pinned NVIDIA garak payloads remain data across explicit missing-row review.

This tests software boundaries, not model resilience; no scanner/model is run.
"""
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from modus.history_ingest import make_history_draft
from modus.record_history import commit_history, history_view
from modus.record_omissions import omission_proposals
from modus.record_store import RecordStore

FIXTURES = Path(__file__).parent / 'fixtures' / 'garak'
CASES = [(name, index, text)
         for name in ('sql_injection', 'python_code_execution', 'markdown_js')
         for index, text in enumerate(json.loads((FIXTURES / (name + '.json')).read_text(encoding='utf-8'))['payloads'])]


@pytest.mark.parametrize('family,index,payload', CASES, ids=[f'{name}-{i}' for name,i,_ in CASES])
def test_untrusted_payload_cannot_authorize_writes_or_change_evidence(tmp_path, monkeypatch, family, index, payload):
    import os
    import subprocess
    def forbidden(*args, **kwargs):
        pytest.fail('Document content attempted process execution')
    monkeypatch.setattr(os, 'system', forbidden)
    monkeypatch.setattr(os, 'popen', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    store = RecordStore(tmp_path / 'records.db', seed_provider=lambda:([], []),
        clock=lambda:datetime(2026,11,3,11,tzinfo=timezone.utc))
    raw = ('Authored boundary test report\n' + payload).encode()
    draft = make_history_draft('authored-boundary.txt', raw)
    draft.update(facts=[], observations=[], extraction_review={'completeness_check':{
        'version':'report-row-inventory-v1', 'omissions':[{
            'id':'inventory-1-1', 'label':'Untrusted source text', 'value':payload, 'unit':None,
            'source_quote':payload, 'page':1, 'bbox':None, 'local_support':'matched_text', 'reason':'not_in_proposal',
        }]}})
    draft['source']['unresolved_row_inventory'] = True
    store.add_draft(draft, raw=raw, filename='authored-boundary.txt', mime='text/plain')
    assert history_view(store)['counts']['facts'] == 0
    proposal = omission_proposals(store.draft(draft['id']))['inventory-1-1']
    assert proposal['value'] == payload and proposal['source_quote'] == payload
    with pytest.raises(ValueError):
        commit_history(store, draft['id'], [])
    assert history_view(store)['counts']['facts'] == 0
    reviewed = {key:proposal.get(key) for key in ('id','kind','label','value','unit','occurred_on','facility')}
    # Only this explicit owner review can add a literal text row; the payload
    # cannot supply source evidence, a timestamp, a tool or a SQL statement.
    receipt = commit_history(store, draft['id'], [], reviewed_omissions=[reviewed])
    view = history_view(store)
    fact, = view['undated_facts']
    assert fact['value'] == payload and fact['source_quote'] == payload
    assert fact['source_proposal']['value'] == payload
    assert fact['available_at'] == receipt['available_at']
    assert store.document(draft['id'])['raw'] == raw
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM history_facts').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM sources').fetchone()[0] == 1
    assert commit_history(store,draft['id'],[],reviewed_omissions=[reviewed])['duplicate']
