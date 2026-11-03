"""Owner-reviewed additions from an artificial inventory, with no provider access."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from modus.record_history_models import ReviewedFact
from modus.record_omissions import commit_omissions
from test_entry_row_inventory import service, upload
from test_record_extraction import pdf
from test_record_row_inventory import SOURCE, MISSING_QUOTE


def prepare(service, *, empty=False):
    client, store, transport = service
    if empty:
        transport.proposed = []
    raw = pdf(SOURCE)
    draft = upload(client, raw).json()
    candidate = next(row for row in draft['extraction_review']['completeness_check']['omissions'] if row['label'] == 'Ferritin')
    row = {key: None for key in ReviewedFact.model_fields}
    row.update(id=candidate['id'], kind='measurement', label='Ferritin', value='29.40', unit='ng/mL', occurred_on='2024-06-01')
    body = {'draft_id': draft['id'], 'synthetic_confirmed': True,
            'reviewed_facts': [{k: f.get(k) for k in ReviewedFact.model_fields} for f in draft['facts']],
            'reviewed_omissions': [row]}
    return client, store, transport, raw, draft, row, body


def saved_fact(client, identity):
    view = client.get('/api/history/view').json()
    return next(row for row in view['facts'] + view['undated_facts'] if row['id'] == identity)


@pytest.mark.parametrize('empty', [False, True])
def test_initial_review_saves_explicit_omission_and_preserves_immutable_proposal(service, empty):
    client, store, transport, raw, draft, row, body = prepare(service, empty=empty)
    before = store.draft(draft['id'])
    body['reviewed_omissions'][0].update(value='30.00', specimen='Serum', reference_range='15–150', test_method='Method as printed')
    result = client.post('/api/history/commit', json=body)
    assert result.status_code == 200, result.text
    receipt = result.json()
    assert receipt['inserted'] == len(draft['facts']) + 1
    fact = saved_fact(client, receipt['fact_ids'][-1])
    assert fact['value'] == '30.00' and fact['source_quote'] == MISSING_QUOTE
    assert fact['source_proposal']['value'] == '29.40' and fact['source_proposal']['occurred_on'] is None
    assert fact['row_inventory']['candidate_id'] == row['id']
    assert {'value', 'occurred_on', 'specimen', 'test_method', 'reference_range'} <= set(fact['reviewed_fields'])
    after = store.draft(draft['id'])
    assert {k:v for k,v in after.items() if k != 'already_committed'} == {k:v for k,v in before.items() if k != 'already_committed'}
    assert store.document(draft['id'])['raw'] == raw
    again = client.post('/api/history/commit', json=body).json()
    assert again['duplicate'] and again['inserted'] == 0 and again['available_at'] == receipt['available_at']
    reopened = upload(client, raw).json()
    assert reopened['omission_reviews'][0]['candidate_id'] == row['id']
    assert reopened['saved_available_at'] == receipt['available_at']
    assert len(transport.calls) == (2 if empty else 3)


def test_addition_has_its_own_time_original_receipt_and_correction_history(service):
    client, store, transport, raw, draft, row, body = prepare(service)
    first = client.post('/api/history/commit', json={**body, 'reviewed_omissions': []}).json()
    captured = client.get('/api/history/page', params={'limit':50}).json()
    with store.connect() as db:
        original_source = db.execute('SELECT data FROM sources WHERE id=?', (draft['id'],)).fetchone()[0]
        original_receipt = db.execute('SELECT data FROM history_commits WHERE draft_id=?', (draft['id'],)).fetchone()[0]
    store.clock = lambda: datetime(2026,11,3,10,tzinfo=timezone.utc)
    # Deliberately use a legacy-compatible label to exercise both read APIs.
    row.update(label='HbA1c', value='6.9', unit='%')
    payload = {'draft_id': draft['id'], 'synthetic_confirmed': True, 'reviewed_omissions':[row]}
    result = client.post('/api/history/omissions/commit', json=payload)
    assert result.status_code == 200, result.text
    receipt = result.json()
    assert receipt['available_at'] > first['available_at'] and receipt['inserted'] == 1
    added_id = receipt['fact_ids'][0]
    fact = saved_fact(client, added_id)
    assert fact['availability_basis'] == 'reviewed_row_addition'
    assert fact['source_proposal']['label'] == 'Ferritin' and fact['source_quote'] == MISSING_QUOTE
    historical = client.get('/api/history/view', params={'known_at':first['available_at']}).json()
    assert added_id not in {f['id'] for f in historical['facts']}
    old_page = client.get('/api/history/page', params={'snapshot_id':captured['page']['snapshot_id'], 'limit':50}).json()
    assert old_page['counts'] == captured['counts']
    old_legacy = store.snapshot().narrow(first['available_at']).observations('2026-11-03')
    assert receipt['observation_ids'][0] not in {f['id'] for f in old_legacy}
    assert receipt['observation_ids'][0] not in {f['id'] for f in store.observations(known_at=first['available_at'])}
    assert receipt['observation_ids'][0] in {f['id'] for f in store.observations()}
    revisions = client.get(f'/api/history/facts/{added_id}/revisions').json()
    assert added_id in json.dumps(revisions) and MISSING_QUOTE in json.dumps(revisions)
    assert client.get('/api/history/sources/'+draft['id']+'/original',params={'known_at':receipt['available_at']}).content == raw
    # Omissions never grant a dated whole-document access override.
    assert client.get('/api/history/sources/'+draft['id']+'/original',params={'known_at':receipt['available_at'],'as_of':'2024-12-31'}).status_code == 404
    with store.connect() as db:
        assert db.execute('SELECT data FROM sources WHERE id=?', (draft['id'],)).fetchone()[0] == original_source
        assert db.execute('SELECT data FROM history_commits WHERE draft_id=?', (draft['id'],)).fetchone()[0] == original_receipt
    again = client.post('/api/history/omissions/commit', json=payload).json()
    assert again['duplicate'] and again['inserted'] == 0
    row['value'] = '7.0'
    assert client.post('/api/history/omissions/commit', json=payload).status_code == 409
    assert saved_fact(client, added_id)['value'] == '6.9'
    from test_entry_amendments import prepare as prepare_correction, save as save_correction
    store.clock = lambda: datetime(2026,11,3,11,tzinfo=timezone.utc)
    save_correction(client, prepare_correction(client, added_id, value='7.1'))
    revised = saved_fact(client, added_id)
    assert revised['value'] == '7.1' and revised['source_quote'] == MISSING_QUOTE
    assert revised['source_proposal']['value'] == '29.40'
    versions = client.get(f'/api/history/facts/{added_id}/revisions').json()['versions']
    assert [v['fact']['value'] for v in versions] == ['6.9', '7.1']
    previous = client.get('/api/history/view',params={'known_at':receipt['available_at']}).json()
    assert next(f for f in previous['facts'] if f['id'] == added_id)['value'] == '6.9'
    assert len(transport.calls) == 3


@pytest.mark.parametrize('patch', [
    {'id':'not-a-candidate'}, {'source_quote':'Invented evidence'}, {'available_at':'2000-01-01T00:00:00Z'},
    {'page':99}, {'bbox':[0.,0.,1.,1.]}, {'value':' '}, {'occurred_on':' '}, {'row_inventory':{'reviewed':True}},
])
def test_forged_identity_evidence_dates_and_blank_fields_never_commit(service, patch):
    client, store, _, _, draft, row, body = prepare(service)
    counts = client.get('/api/history/view').json()['counts']
    body['reviewed_omissions'] = [{**row, **patch}]
    assert client.post('/api/history/commit', json=body).status_code == 422
    assert client.get('/api/history/view').json()['counts'] == counts
    assert not store.draft(draft['id'])['already_committed']


def test_unknown_date_stays_unknown_and_duplicate_candidate_is_rejected(service):
    client, _, _, _, _, row, body = prepare(service, empty=True)
    row['occurred_on'] = None
    assert client.post('/api/history/commit', json={**body,'reviewed_omissions':[row,row]}).status_code == 422
    result = client.post('/api/history/commit', json=body).json()
    fact = saved_fact(client, result['fact_ids'][0])
    assert fact['date'] is None and fact['date_precision'] == 'unknown'


def test_concurrent_retries_append_once_and_transaction_failure_rolls_back(service):
    client, store, _, _, draft, row, body = prepare(service)
    assert client.post('/api/history/omissions/commit',json={k:v for k,v in body.items() if k != 'reviewed_facts'}).status_code == 409
    client.post('/api/history/commit',json={**body,'reviewed_omissions':[]})
    event_factory = store._commit_event_factory
    store._commit_event_factory = lambda receipt: (_ for _ in ()).throw(RuntimeError('artificial audit failure'))
    with pytest.raises(RuntimeError):
        commit_omissions(store, draft['id'], [row])
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM history_omission_reviews').fetchone()[0] == 0
    store._commit_event_factory = event_factory
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(lambda _: commit_omissions(store,draft['id'],[deepcopy(row)]), range(2)))
    assert sorted(r['inserted'] for r in receipts) == [0,1]
    assert len({r['available_at'] for r in receipts}) == 1
