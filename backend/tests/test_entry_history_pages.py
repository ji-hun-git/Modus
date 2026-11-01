"""New authored pagination cases; no frozen corpora or model requests."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
import sqlite3
import pytest

from test_entry_history_compare_api import api, save, NOW
from test_entry_amendments import prepare, save as save_amendment
from modus_entry.history_pages import HistoryPages


@pytest.fixture
def history(api):
    client, store, clock = api
    for batch in range(3):
        save(client, [['measurement', f'Field{i:03}', str(i + batch), 'mmHg', f'202{batch}-01-02', 'Example']
                      for i in range(55)], filename=f'page-{batch}.csv')
    save(client, [['recorded_text','Original note','Exact undated wording',None,None,'Example']], filename='undated.csv')
    return client, store, clock


def get(client, **params):
    response=client.get('/api/history/page',params={k:v for k,v in params.items() if v is not None})
    assert response.status_code == 200, response.text
    return response.json()


def rows(view):
    return view['facts']+view['undated_facts']


def test_page_walk_exactly_matches_full_scope_and_has_no_duplicate_or_missing_facts(history):
    client, _, _ = history
    first = get(client)
    expected=client.get('/api/history/view',params={'known_at':first['scope']['known_at']}).json()
    pages=[first]; offset=first['page']['next_offset']
    while offset is not None:
        page=get(client,snapshot_id=first['page']['snapshot_id'],offset=offset)
        assert page['scope'] == first['scope']
        assert len(rows(page)) <= 50
        pages.append(page); offset=page['page']['next_offset']
    found=[r for p in pages for r in rows(p)]
    assert len(found)==166 and len({r['id'] for r in found})==166
    assert found==rows(expected)
    assert pages[-1]['undated_facts'][0]['value']=='Exact undated wording'


def test_filters_and_field_catalog_search_the_entire_capture(history):
    client, _, _ = history
    first=get(client,limit=1)
    token=first['page']['snapshot_id']
    page=get(client,snapshot_id=token,label='Field000',order='oldest')
    assert [r['date'] for r in rows(page)]==['2020-01-02','2021-01-02','2022-01-02']
    assert page['page']['total']==3
    catalog=get(client,snapshot_id=token,section='fields',offset=50)
    assert catalog['page']['total']==56 and len(catalog['fields'])==6
    assert get(client,snapshot_id=token,section='fields',query='Field054')['fields'][0]['count']==3
    assert get(client,snapshot_id=token,query='Exact undated')['page']['total']==1
    assert get(client,snapshot_id=token,facility='No such place')['page']['total']==0
    assert get(client,snapshot_id=token,query='page-0.csv')['page']['total']==55
    assert get(client,snapshot_id=token,section='sources',query='undated.csv',kind='measurement')['page']['total']==0
    assert get(client,snapshot_id=token,section='fields',facility='No such place')['page']['total']==0


def test_catalog_is_lightweight_and_all_source_fields_remain_reachable(history):
    client, _, _ = history
    catalog=get(client,section='sources',limit=2)
    assert rows(catalog)==[] and len(catalog['sources'])==2 and catalog['page']['total']==4
    source=catalog['sources'][0]
    assert source['fact_count']==55
    facts=get(client,snapshot_id=catalog['page']['snapshot_id'],source_id=source['id'])
    last=get(client,snapshot_id=catalog['page']['snapshot_id'],source_id=source['id'],offset=50)
    assert len(rows(facts))==50 and len(rows(last))==5


def test_new_commits_cannot_shift_existing_pages_and_refresh_sees_changes(history):
    client, store, clock = history
    old=get(client); token=old['page']['snapshot_id']
    old_tail=get(client,snapshot_id=token,offset=50)
    clock[0]+=timedelta(seconds=1)
    save(client,[['measurement','New arrival','999','mmHg','2025-01-01','Example']],filename='arrival.csv')
    assert get(client,snapshot_id=token,offset=50)==old_tail
    assert get(client)['page']['total']==167
    assert get(client,known_at=old['scope']['known_at'])['page']['total']==166


def test_correction_refresh_preserves_prior_pages_and_originals(history):
    client, store, clock = history
    old=get(client,label='Field000'); original=rows(old)[0]
    clock[0]+=timedelta(seconds=1)
    save_amendment(client,prepare(client,original['id'],value='998'))
    current=get(client,label='Field000')
    assert rows(current)[0]['value']=='998'
    assert rows(current)[0]['source_quote']==original['source_quote']
    assert rows(get(client,snapshot_id=old['page']['snapshot_id'],label='Field000'))[0]==original


def test_cache_invalidates_across_database_connections_and_ignores_audit_writes(history):
    client, store, _ = history
    first=get(client)
    store.save_run({'kind':'test-only'})
    assert get(client)['page']['snapshot_id']==first['page']['snapshot_id']
    with sqlite3.connect(store.path) as db:
        db.execute('INSERT INTO history_profiles(updated_at,data) VALUES (?,?)',
                   (NOW.isoformat().replace('+00:00','Z'),'{"date_of_birth":"1990-01-01","updated_at":"2026-10-29T08:00:00Z"}'))
    assert get(client)['page']['snapshot_id']!=first['page']['snapshot_id']


def test_rollback_does_not_invalidate_or_change_a_capture(history):
    client, store, _ = history
    first=get(client)
    with pytest.raises(RuntimeError):
        with store.connect() as db:
            db.execute('DELETE FROM history_facts')
            raise RuntimeError('rollback')
    assert get(client)['page']['snapshot_id']==first['page']['snapshot_id']


@pytest.mark.parametrize('params',[{'limit':0},{'limit':51},{'offset':-1},{'section':'sql'}, {'order':'arbitrary'}])
def test_invalid_page_requests_fail_closed(history,params):
    assert history[0].get('/api/history/page',params=params).status_code==422


def test_unknown_expired_and_mismatched_scope_tokens_do_not_fall_back(history):
    client, store, _ = history
    first=get(client,as_of='2020-12-31')
    token=first['page']['snapshot_id']
    assert client.get('/api/history/page',params={'snapshot_id':token,'as_of':'2025-01-01'}).status_code==422
    assert client.get('/api/history/page',params={'snapshot_id':'0'*32}).status_code==410
    store.history_pages.captures[token]['created']-=HistoryPages.TTL+1
    assert client.get('/api/history/page',params={'snapshot_id':token}).status_code==410


def test_pages_cannot_mutate_cached_evidence_and_cache_is_bounded(history):
    client, store, _ = history
    first=get(client)
    direct=store.history_pages.page(snapshot_id=first['page']['snapshot_id'])
    direct['facts'][0]['value']='mutated'
    assert rows(get(client,snapshot_id=first['page']['snapshot_id']))[0]['value']!='mutated'
    for year in range(2018,2025):
        get(client,as_of=f'{year}-12-31')
    assert len(store.history_pages.captures)<=HistoryPages.MAX_SNAPSHOTS


def test_parallel_open_is_one_capture_and_all_pages_share_exact_scope(history):
    client, store, _ = history
    store.history_pages=HistoryPages(store)
    with ThreadPoolExecutor(max_workers=8) as pool:
        pages=list(pool.map(lambda n: get(client,offset=(n%4)*50),range(32)))
    assert len({p['page']['snapshot_id'] for p in pages})==1
    assert len({p['scope']['scope_id'] for p in pages})==1


def test_future_availability_becomes_visible_without_a_database_write(api):
    client, store, clock = api
    clock[0]+=timedelta(days=1)
    save(client,[['measurement','Future arrival','22','mmHg','2020-01-01','Example']],filename='future.csv')
    clock[0]=NOW
    first=get(client); assert first['counts']['facts']==0
    clock[0]+=timedelta(days=1)
    assert get(client)['counts']['facts']==1


def test_partial_scope_and_conflict_companions_survive_page_boundaries(api):
    client, store, clock = api
    save(client,[['measurement','Pulse','70','bpm','2020-01-02','Example'],
                 ['measurement','Pulse','72','bpm','2020-01-02','Example'],
                 ['recorded_text','Later wording','Future narrative',None,'2025-01-02','Example']],filename='mixed.csv')
    page=get(client,as_of='2020-12-31',limit=1)
    assert page['facts'][0]['source_quote'] is None
    assert page['facts'][0]['original_available'] is False
    conflict=get(client,snapshot_id=page['page']['snapshot_id'],conflict_id=page['conflicts'][0]['id'])
    assert {r['value'] for r in rows(conflict)}=={'70','72'}
    assert get(client,snapshot_id=page['page']['snapshot_id'],source_id='nonexistent')['page']['total']==0
