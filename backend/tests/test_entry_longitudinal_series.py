"""Authored service cases for longitudinal series; no benchmark/model execution."""
from copy import deepcopy
from datetime import timedelta

from fastapi.testclient import TestClient
import pytest

from test_entry_history_api import api, NOW
from test_entry_lab_context import imported
from modus.record_history_models import ReviewedFact
from modus_entry.longitudinal_series import build_series, SeriesResponse
from modus_entry import claim_verification


def fact(identity, day, value='5.0', **updates):
    return {'id': identity, 'source_id': identity + ':source', 'revision_id': identity + ':r0',
        'kind': 'measurement', 'label': 'Novel assay', 'value': value, 'unit': 'mg/L',
        'date': day, 'occurred_on': day, 'date_precision': 'day' if day else 'unknown',
        'source_quote': f'Novel assay {value} mg/L', 'page': 1, 'bbox': None,
        'available_at': NOW.isoformat(), 'within_date_scope': True,
        'reference_range': '2–6', 'specimen': 'Serum', 'test_method': 'Method A',
        'facility': 'Example lab', **updates}


def view_of(*rows, conflicts=None):
    return {'scope': {'scope_id': 'test-capture', 'as_of': None, 'known_at': NOW.isoformat(), 'captured_at': NOW.isoformat()},
        'facts': [row for row in rows if row.get('date')], 'undated_facts': [row for row in rows if not row.get('date')],
        'sources': [{'id': sid, 'title': 'Same filename.csv', 'available_at': NOW.isoformat(), 'original_available': True}
                    for sid in sorted({row['source_id'] for row in rows})], 'conflicts': conflicts or []}


def series(view, anchor='a', offset=0, limit=50):
    result = build_series(view, 'a' * 32, anchor, offset, limit)
    SeriesResponse.model_validate(result)
    return result


def test_three_visits_exact_aliases_and_authorized_edges_keep_originals():
    a,b,c = fact('a','2020-01-01','4.00',label='HbA1c'), fact('b','2022-01-01','5.25',label='A1c'), fact('c','2024-01-01','5.25',label='HbA1c')
    unrelated = fact('other','2023-01-01','7',label='HbA1c estimated')
    view = view_of(c,a,unrelated,b)
    before = deepcopy(view)
    result = series(view)
    assert view == before
    assert [row['id'] for row in result['observations']] == ['a','b','c']
    assert [row['value'] for row in result['observations']] == ['4.00','5.25','5.25']
    assert [(edge['from_id'],edge['to_id'],edge['difference'],edge['connectable']) for edge in result['edges']] == [('a','b','1.25',True),('b','c','0.00',True)]
    assert result['counts'] == {'dated':3,'undated':0,'sources':3,'conflicts':0}
    assert len(result['plot_points']) == 3 and all(point['unit']=='mg/L' for point in result['plot_points'])
    assert {s['id'] for s in result['history_evidence']['sources']} == {'a:source','b:source','c:source'}


@pytest.mark.parametrize('updates,reason', [
    ({'unit':'g/L'},'UNIT_DIFFERS'), ({'unit':None},'UNIT_UNKNOWN'),
    ({'specimen':'Plasma'},'SPECIMEN_DIFFERS'), ({'specimen':None},'SPECIMEN_UNKNOWN'),
    ({'test_method':'B'},'TEST_METHOD_DIFFERS'), ({'test_method':None},'TEST_METHOD_UNKNOWN'),
    ({'value':'<5'},'QUALIFIED_OR_TEXT_VALUE'), ({'reference_range':'<6'},'REFERENCE_RANGE_DIFFERS'),
    ({'source_quote':None},'SOURCE_SUPPORT_MISSING'), ({'source_quote_withheld':True},'SOURCE_SUPPORT_MISSING'),
])
def test_unapproved_edges_never_connect(updates,reason):
    result=series(view_of(fact('a','2020-01-01','4'),fact('b','2022-01-01',**updates)))
    edge=result['edges'][0]
    assert not edge['connectable'] and edge['difference'] is None and reason in edge['reason_codes']


def test_same_day_ties_partial_dates_and_conflict_companions_survive_pages():
    a,b,c=fact('a','2020-01-01','4'),fact('b','2022-01-01','5'),fact('c','2022-01-01','6')
    group={'id':'conflict','fact_ids':['b','c'],'reason':'different_numeric_values'}
    result=series(view_of(a,b,c,conflicts=[group]),offset=1,limit=1)
    assert [row['id'] for row in result['observations']]==['b']
    assert {row['id'] for row in result['history_evidence']['facts']}=={'a','b','c'}
    assert result['history_evidence']['conflicts']==[group] and result['edges']==[]
    assert result['page']['next_offset']==2 and result['page']['previous_offset']==0
    complete=series(view_of(a,b,c,conflicts=[group]))
    assert not any(edge['connectable'] for edge in complete['edges'])
    partial=fact('p',None,'3',occurred_on='2019-05',date_precision='month')
    result=series(view_of(a,b,partial))
    assert result['observations'][-1]['occurred_on']=='2019-05'
    assert result['observations'][-1]['date_precision']=='month'
    assert result['counts']['undated']==1 and len(result['plot_points'])==2
    assert 'INCOMPLETE_DATE' in result['edges'][0]['reason_codes']


def test_qualified_precision_and_missing_units_stay_as_exact_evidence():
    rows=[fact('a','2020-01-01','9007199254740993'),fact('b','2021-01-01','trace'),
          fact('c','2022-01-01','5,2'),fact('d','2023-01-01','5',unit=None)]
    result=series(view_of(*rows))
    assert result['plot_points']==[]
    assert [row['value'] for row in result['observations']]==[row['value'] for row in rows]
    codes={note['fact_id']:note['reason_codes'] for note in result['observation_notes']}
    assert 'PLOT_PRECISION_UNSUPPORTED' in codes['a']
    assert 'QUALIFIED_OR_TEXT_VALUE' in codes['b'] and 'QUALIFIED_OR_TEXT_VALUE' in codes['c']
    assert 'UNIT_UNKNOWN' in codes['d']


def test_single_empty_page_and_unavailable_anchors_are_explicit():
    view=view_of(fact('a','2020-01-01'))
    one=series(view)
    assert len(one['observations'])==1 and one['edges']==[]
    empty=series(view,offset=50)
    assert empty['observations']==[] and empty['plot_points']==[] and empty['edges']==[]
    assert empty['page']['total']==1 and len(empty['history_evidence']['facts'])==1
    with pytest.raises(ValueError,match='unavailable'):
        series(view,anchor='missing')
    with pytest.raises(ValueError,match='measurement'):
        series(view_of(fact('a','2020-01-01',kind='recorded_text')))


def test_no_cross_page_edges_and_global_duplicate_detection():
    rows=[fact(f'r{i:03}','2020-01-%02d'%(i+1),str(i)) for i in range(30)]
    rows.append(fact('tie','2020-01-16','99'))
    result=series(view_of(*rows),anchor='r000',offset=14,limit=2)
    assert len(result['edges'])==1 and not result['edges'][0]['connectable']
    assert 'SELECTED_DATE_TIE' in result['edges'][0]['reason_codes']
    assert {edge['from_id'] for edge in result['edges']} <= {row['id'] for row in result['observations']}


def test_evidence_bounds_fail_without_truncating_companions():
    rows=[fact(str(i),'2020-01-01') for i in range(121)]
    group={'id':'huge-conflict','fact_ids':[row['id'] for row in rows]}
    with pytest.raises(ValueError,match='120-record'):
        series(view_of(*rows,conflicts=[group]),anchor='0',limit=1)
    with pytest.raises(ValueError,match='size limit'):
        series(view_of(fact('a','2020-01-01',source_quote='x'*1_100_000)))


def test_withheld_content_and_outside_scope_do_not_enter_series():
    visible=fact('a','2020-01-01')
    hidden=fact('hidden',None,'SECRET VALUE',occurred_on='2025',value_withheld=True,within_date_scope=False)
    result=series(view_of(visible,hidden))
    assert 'SECRET VALUE' not in str(result) and result['page']['total']==1
    with pytest.raises(ValueError,match='unavailable'):
        series(view_of(visible,hidden),anchor='hidden')


def test_one_context_for_all_pairs_in_large_history(monkeypatch):
    calls=[]
    original=claim_verification.comparison_context
    def counted(view):
        calls.append(1)
        return original(view)
    monkeypatch.setattr(claim_verification,'comparison_context',counted)
    rows=[fact(f'r{i:02}',f'20{i:02}-01-01') for i in range(30)]
    rows += [fact(f'x{i}','2000-01-01',label=f'Unrelated {i}') for i in range(2000)]
    result=series(view_of(*rows),anchor='r00')
    assert calls==[1] and result['page']['total']==30 and len(result['edges'])==29


def import_result(client,day,value,extra=''):
    raw=('kind,label,value,unit,date,facility,reference_range,specimen,test_method\n'
         f'measurement,Novel assay,{value},mg/L,{day},Example lab,2-6,Serum,Method A\n'+extra).encode()
    return raw,imported(client,raw)[2]


def captured_series(client,**params):
    page=client.get('/api/history/page',params={'label':'Novel assay',**params}).json()
    request={'snapshot_id':page['page']['snapshot_id'],'fact_id':page['facts'][0]['id']}
    response=client.get('/api/history/series',params=request)
    assert response.status_code==200,response.text
    return request,response.json()


def test_http_three_visits_correction_late_arrival_original_and_restart(api):
    client,store=api
    originals=[]
    for day,value in [('2020-01-01','4.00'),('2022-01-01','5.00'),('2024-01-01','6.00')]:
        originals.append(import_result(client,day,value))
    request,before=captured_series(client)
    assert len(before['observations'])==3 and all(edge['connectable'] for edge in before['edges'])
    oldest=before['observations'][0]
    store.clock=lambda:NOW+timedelta(seconds=10)
    corrected={key:oldest.get(key) for key in ReviewedFact.model_fields}
    corrected['value']='4.50'
    body={'expected_revision_id':oldest['revision_id'],'reason':'Correct a reviewed transcription','corrected':corrected}
    preview=client.post('/api/history/amendments/preview',json=body)
    assert preview.status_code==200,preview.text
    saved=client.post('/api/history/amendments/commit',json={**body,'preview_id':preview.json()['preview_id'],'reviewed':True})
    assert saved.status_code==200,saved.text
    assert client.get('/api/history/series',params=request).json()==before
    _,fresh=captured_series(client)
    assert fresh['observations'][0]['value']=='4.50' and '4.00' in fresh['observations'][0]['source_quote']
    assert fresh['observations'][0]['revision_id']!=oldest['revision_id']
    assert fresh['edges'][0]['difference']=='0.50'
    raw,receipt=originals[0]
    assert client.get(f"/api/history/sources/{receipt['source_id']}/original",params={'known_at':store.clock().isoformat()}).content==raw
    store.clock=lambda:NOW+timedelta(seconds=20)
    import_result(client,'2019-01-01','3.00')
    _,latest=captured_series(client)
    assert len(latest['observations'])==4 and latest['observations'][0]['date']=='2019-01-01'
    _,historical=captured_series(client,known_at=NOW.isoformat())
    assert [row['value'] for row in historical['observations']]==['4.00','5.00','6.00']
    from modus_entry.app import create_entry_app
    restarted=create_entry_app(store.path,clock=store.clock)
    with TestClient(restarted) as again:
        assert again.get('/api/history/series',params=request).status_code==409
        _,restored=captured_series(again)
        assert [(r['id'],r['revision_id'],r['value']) for r in restored['observations']]==[(r['id'],r['revision_id'],r['value']) for r in latest['observations']]


def test_http_historical_source_excerpts_remain_withheld(api):
    client,_=api
    import_result(client,'2020-01-01','4.00',
        'measurement,Novel assay,SECRET-FUTURE,mg/L,2025-01-01,Example lab,2-6,Serum,Method A\n'
        'measurement,Novel assay,SECRET-UNDATED,mg/L,,Example lab,2-6,Serum,Method A\n')
    _,result=captured_series(client,as_of='2021-01-01')
    assert len(result['observations'])==1
    assert 'SECRET-' not in str(result)
    assert result['observations'][0]['source_quote'] is None
    assert not result['history_evidence']['sources'][0]['original_available']
    assert 'SOURCE_EXCERPT_UNAVAILABLE' in result['observation_notes'][0]['reason_codes']


@pytest.mark.parametrize('change', [
    {'snapshot_id':'invalid'}, {'snapshot_id':'g'*32}, {'fact_id':''}, {'fact_id':'x'*161},
    {'offset':-1}, {'offset':100001}, {'limit':0}, {'limit':51}, {'limit':'abc'},
    {'as_of':'2020-01-01'}, {'known_at':'2099-01-01'},
])
def test_http_malformed_parameters_rejected(api,change):
    client,_=api
    params={'snapshot_id':'a'*32,'fact_id':'anchor',**change}
    assert client.get('/api/history/series',params=params).status_code==422


def test_http_missing_anchor_and_expired_snapshot(api):
    client,store=api
    import_result(client,'2020-01-01','4')
    request,_=captured_series(client)
    assert client.get('/api/history/series',params={**request,'fact_id':'missing'}).status_code==422
    with store.history_pages.lock:
        store.history_pages.captures[request['snapshot_id']]['created']-=store.history_pages.TTL+1
    assert client.get('/api/history/series',params=request).status_code==409


@pytest.mark.parametrize('name,value', [('snapshot_id','b'*32),('fact_id','other'),('offset','1'),('limit','1')])
def test_http_duplicate_parameters_rejected_before_snapshot_lookup(api,name,value):
    client,_=api
    params=[('snapshot_id','a'*32),('fact_id','anchor'),('offset','0'),('limit','50'),(name,value)]
    response=client.get('/api/history/series',params=params)
    assert response.status_code==422
    assert response.json()['detail']=='Each series parameter must be supplied once.'
