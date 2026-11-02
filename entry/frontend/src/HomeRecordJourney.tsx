import { useState } from 'react';
import type { HistoryFact, HistoryView } from './historyTypes';
import useHistoryView from './useHistoryView';
import HomeRecordSeries from './HomeRecordSeries';
import OverviewRecordDetails from './OverviewRecordDetails';
import HistoryPager from './HistoryPager';
import MedicalTestReference from './MedicalTestReference';
import CheckupComparison from './CheckupComparison';
import { friendlyRecordName } from './HomeReportReadings';
import { recordedDate } from './sourceDisplay';
import { unitLabel } from './recordPresentation.mjs';

export default function HomeRecordJourney({parent,anchor,onOpenCurrent}: {
  parent: HistoryView; anchor: HistoryFact; onOpenCurrent: () => void;
}) {
  const history=useHistoryView(parent.scope,parent.scope.as_of===null,{
    snapshot_id:parent.page?.snapshot_id,kind:anchor.kind,label:anchor.label,
    through:anchor.date || undefined,limit:50,
    compare_fact_id:anchor.kind==='measurement'?anchor.id:undefined,
  });
  const [inspected,setInspected]=useState<HistoryFact|null>(null);
  const [selection,setSelection]=useState<{title:string;facts:HistoryFact[]}|null>(null);
  const view=history.view;
  const rows=view ? [...view.facts,...view.undated_facts] : [];
  const disputed=new Set(view?.conflicts.flatMap(c=>c.fact_ids) || []);
  return <section className="report-journey" aria-label="This reading across your history">
    <header><div><span className="report-section-label">Across your history</span>
      <h3>{friendlyRecordName(anchor.label)}</h3></div>
      <button type="button" className="text-button" onClick={onOpenCurrent}>Open original evidence</button>
    </header>
    <MedicalTestReference fact={anchor} />
    {history.error ? <div role="alert"><p>{history.error}</p><button onClick={history.refresh}>Reload history</button></div>
      : !view ? <p role="status">Finding your earlier records…</p> : <>
        <CheckupComparison view={view} />
        <div className="report-journey-meta"><span>{view.page?.total ?? rows.length} matching {(view.page?.total ?? rows.length)===1?'record':'records'}
          {anchor.date ? ` through ${recordedDate(anchor)}` : ' · date not fully recorded in this report'}</span>
          <span>{anchor.kind==='measurement'?'Select a point for its source':'Open a record for its source'}</span></div>
        {anchor.kind==='measurement' ? <HomeRecordSeries facts={rows} label={friendlyRecordName(anchor.label)}
          sourceIds={new Set(view.sources.map(s=>s.id))} disputedIds={disputed}
          onSelect={facts=>facts.length===1?setInspected(facts[0]):setSelection({title:'Source records for this point',facts})} />
          : <div className="report-text-history">{rows.slice(0,4).map(fact=><button key={fact.id} type="button" onClick={()=>setInspected(fact)}>
            <time>{recordedDate(fact)}</time><span>{fact.value_withheld?'Hidden by date filter':fact.value ?? 'Not recorded'} {!fact.value_withheld&&unitLabel(fact.unit)}</span>
          </button>)}</div>}
        {view.page && view.page.total>rows.length && <p className="report-page-note">Showing {rows.length} of {view.page.total} records on this page.</p>}
        {!!disputed.size && <p className="report-page-note">Different recorded values remain separate. No value is chosen as correct.</p>}
        <HistoryPager view={view} onPage={history.setOffset} noun="records" />
        <details className="report-history-list"><summary>Read the source list</summary>
          {rows.map(fact=><button key={fact.id} type="button" onClick={()=>setInspected(fact)}>
            <span>{recordedDate(fact)}</span><strong>{fact.value_withheld?'Hidden by date filter':fact.value ?? 'Not recorded'} {!fact.value_withheld&&unitLabel(fact.unit)}</strong>
            <span>{view.sources.find(s=>s.id===fact.source_id)?.title || 'Source record'}</span>
          </button>)}
        </details>
        <OverviewRecordDetails view={view} selection={selection} inspected={inspected} onInspect={setInspected}
          onCloseSource={()=>setInspected(null)} onCloseSelection={()=>setSelection(null)} />
      </>}
  </section>;
}
