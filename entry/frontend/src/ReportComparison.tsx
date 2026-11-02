import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { api, ApiError } from './api';
import { Modal, dateLabel, timeLabel } from './ui';
import type { HistoryFact, HistoryView, PagedSource } from './historyTypes';
import type { ReportComparisonSummary } from './reportComparisonTypes';
import { reportIdentity, matchesReportSummary } from './reportComparisonTypes';
import { correctionSession } from './correctionSession';
import ReportComparisonPicker from './ReportComparisonPicker';
import ReportComparisonRows from './ReportComparisonRows';
import OverviewRecordDetails from './OverviewRecordDetails';
import ReportBriefReview from './ReportBriefReview';
import './report-comparison.css';

export default function ReportComparison({view, selectedSource, onClose}: {
  view:HistoryView; selectedSource:PagedSource; onClose:()=>void;
}) {
  const snapshotId=view.page?.snapshot_id || '';
  const [previous,setPrevious]=useState<PagedSource|null>(null);
  const [choosing,setChoosing]=useState(true);
  const [retry,setRetry]=useState(0);
  const [page,setPage]=useState(0);
  const [inspected,setInspected]=useState<HistoryFact|null>(null);
  const [loaded,setLoaded]=useState<{key:string;summary:ReportComparisonSummary}|null>(null);
  const [failure,setFailure]=useState<{key:string;message:string;expired:boolean}|null>(null);
  const [invalidated,setInvalidated]=useState(false);
  const resultsHeading=useRef<HTMLHeadingElement>(null);
  const focusResults=useRef(false);
  const [initialCorrections]=useState(()=>new Map(correctionSession.getSnapshot().map(([id,state])=>[id,state.savedAt])));
  const corrections=useSyncExternalStore(correctionSession.subscribe,correctionSession.getSnapshot,correctionSession.getSnapshot);
  const key=JSON.stringify([snapshotId,view.scope.as_of,view.scope.known_at,selectedSource.id,previous?.id,retry]);
  const summary=loaded?.key===key ? loaded.summary : null;
  const error=failure?.key===key ? failure : null;
  const correctedIds=new Set(summary ? [...summary.history_evidence.facts,...summary.history_evidence.undated_facts].map(f=>f.id) : []);
  const stale=invalidated || corrections.some(([id,state])=>correctedIds.has(id) && state.savedAt && state.savedAt!==initialCorrections.get(id));
  useEffect(()=>{
    if (!focusResults.current) return;
    focusResults.current=false;
    resultsHeading.current?.focus();
    resultsHeading.current?.scrollIntoView({block:'start'});
  },[page]);
  useEffect(()=>{
    if (stale) setInvalidated(true);
  },[stale]);
  useEffect(()=>{
    if (!previous || !snapshotId || stale) return;
    const controller=new AbortController();
    void api<ReportComparisonSummary>('/history/report-summary',{
      method:'POST',headers:{'Content-Type':'application/json'},signal:controller.signal,
      body:JSON.stringify({snapshot_id:snapshotId,selected_source_id:selectedSource.id,comparison_source_id:previous.id}),
    }).then(result=>{
      if (controller.signal.aborted) return;
      if (!matchesReportSummary(result,snapshotId,view.scope,selectedSource.id,previous.id))
        throw new Error('The comparison does not match the selected reports and history view. Close and reopen it.');
      setLoaded({key,summary:result});
    }).catch((err:Error)=>{
      if (!controller.signal.aborted) setFailure({key,message:err.message,expired:err instanceof ApiError && err.status===409});
    });
    return ()=>controller.abort();
  },[key,stale]);
  function selectComparison(source:PagedSource) {
    setLoaded(null);setFailure(null);setInspected(null);setPage(0);
    setPrevious(source);setChoosing(false);
  }
  function changePage(next:number) {
    focusResults.current=true;setPage(next);setInspected(null);
  }
  return <Modal title="Compare reports" onClose={onClose} wide>
    <div className="report-comparison">
      {!previous && <p className="report-comparison-intro">Choose a second report to compare its recorded values.</p>}
      <div className="report-comparison-sources">
        <section aria-label="Selected report"><span>Selected report</span><h3>{selectedSource.title}</h3>
          <p>{reportIdentity(selectedSource)}</p></section>
        <section aria-label="Comparison report"><span>Compare with</span>
          {previous ? <><h3>{previous.title}</h3><p>{reportIdentity(previous)}</p>
            {!choosing && !stale && <button type="button" className="text-button" onClick={()=>{setChoosing(true);setInspected(null);}}>Choose another report</button>}
          </> : <p>Choose a report from your history below.</p>}
        </section>
      </div>
      <p className="report-comparison-scope">Recorded through {view.scope.as_of?dateLabel(view.scope.as_of):'all recorded dates'}.
        {' '}Available in Modus by {timeLabel(view.scope.known_at)}.</p>
      {stale && <div role="status" className="report-comparison-error"><p>A record in this comparison was corrected. Open updated history to compare the revised records. The original evidence remains preserved.</p>
        <button type="button" className="secondary" onClick={()=>{onClose();window.dispatchEvent(new Event('modus:show-current-history'));}}>Open updated history</button></div>}
      {!snapshotId && <p role="alert">Close this comparison and refresh your history to capture the reports first.</p>}
      {choosing && snapshotId && !stale && <>
        <ReportComparisonPicker snapshotId={snapshotId} selectedId={selectedSource.id} scope={view.scope} onSelect={selectComparison} />
        {previous && <button type="button" className="text-button" onClick={()=>setChoosing(false)}>Keep current comparison</button>}
      </>}
      {!choosing && previous && !summary && !error && !stale && <p role="status">Comparing the selected reports…</p>}
      {!choosing && error && !stale && <div className="report-comparison-error" role="alert"><p>{error.message}</p>
        {error.expired ? <p>Close this comparison and refresh your history before trying again.</p>
          : <button type="button" className="text-button" onClick={()=>{setFailure(null);setRetry(value=>value+1);}}>Retry comparison</button>}</div>}
      {!choosing && summary && !stale && <>
        <header className="report-comparison-result-heading"><h3 ref={resultsHeading} tabIndex={-1}>
          {summary.counts.comparable || summary.counts.not_comparable ? 'Recorded differences' : 'Report summary'}</h3>
          <span>Calculated from saved records · No model used</span></header>
        <p className="report-comparison-counts">{[
          summary.counts.comparable ? `${summary.counts.comparable} with recorded differences` : '',
          summary.counts.not_comparable ? `${summary.counts.not_comparable} need context` : '',
          summary.counts.only_selected ? `${summary.counts.only_selected} only in the selected report` : '',
          summary.counts.only_comparison ? `${summary.counts.only_comparison} only in the comparison report` : '',
        ].filter(Boolean).join(' · ')}</p>
        {!summary.rows.length && <p>There are no visible entries to compare in these two reports.</p>}
        {summary.rows.length>10 && <nav className="history-pagination" aria-label="Comparison result pages">
          <button className="text-button" disabled={page===0} onClick={()=>changePage(page-1)}>Previous results</button>
          <span role="status">{page*10+1}–{Math.min((page+1)*10,summary.rows.length)} of {summary.counts.rows} comparisons</span>
          <button className="text-button" disabled={(page+1)*10>=summary.rows.length} onClick={()=>changePage(page+1)}>Next results</button>
        </nav>}
        <ReportComparisonRows summary={summary} rows={summary.rows.slice(page*10,(page+1)*10)} onInspect={setInspected} />
        {!!summary.limitations.length && <details className="report-comparison-limitations"><summary>What this comparison can show</summary>
          <ul>{summary.limitations.map((limitation,index)=><li key={index}>{limitation}</li>)}</ul>
          <p>Comparison policy: {summary.policy_version}</p>
        </details>}
        <ReportBriefReview key={key} summary={summary} onRefresh={()=>{onClose();window.dispatchEvent(new Event('modus:show-current-history'));}}/>
      </>}
      {summary && !choosing && <OverviewRecordDetails view={summary.history_evidence} selection={null} inspected={inspected}
        onInspect={setInspected} onCloseSource={()=>setInspected(null)} onCloseSelection={()=>{}} />}
    </div>
  </Modal>;
}
