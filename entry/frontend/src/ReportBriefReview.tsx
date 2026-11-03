import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import type { Ref } from 'react';
import { api, ApiError, localRequest } from './api';
import type { HistoryFact } from './historyTypes';
import type { ReportComparisonSummary } from './reportComparisonTypes';
import type { ReportBriefData } from './reportBriefTypes';
import { reportBriefMatches, reportBriefRequest } from './reportBriefTypes';
import { correctionSession } from './correctionSession';
import { friendlyRecordName } from './HomeReportReadings';
import { recordedDate } from './sourceDisplay';
import OverviewRecordDetails from './OverviewRecordDetails';

export function ReportBriefContents({brief,page,onPage,onInspect,headingRef}: {
  brief:ReportBriefData; page:number; onPage:(page:number)=>void; onInspect:(fact:HistoryFact)=>void;
  headingRef?:Ref<HTMLHeadingElement>;
}) {
  return <>
    <h3 ref={headingRef} tabIndex={-1}>Your comparison is ready to review</h3>
    <p>{brief.counts.total} records from {brief.counts.sources} files, with the recorded differences and original excerpts.</p>
    {brief.counts.conflict_companions>0 && <p role="status">{brief.counts.conflict_companions} additional {brief.counts.conflict_companions===1?'record is':'records are'} included so a disagreement is not left out.</p>}
    <details><summary>Review included records ({brief.counts.total})</summary>
      {brief.entries.length>10 && <nav className="history-pagination" aria-label="Summary record pages">
        <button type="button" className="text-button" disabled={page===0} onClick={()=>onPage(page-1)}>Previous records</button>
        <span role="status">{page*10+1}–{Math.min((page+1)*10,brief.entries.length)} of {brief.entries.length}</span>
        <button type="button" className="text-button" disabled={(page+1)*10>=brief.entries.length} onClick={()=>onPage(page+1)}>Next records</button>
      </nav>}
      <ul className="report-brief-records">{brief.entries.slice(page*10,(page+1)*10).map(row=><li key={row.id}>
        <button type="button" className="text-button" onClick={()=>onInspect(row)}>
          <span>{friendlyRecordName(row.label)} · {row.value}{row.unit?` ${row.unit}`:''}</span>
          <small>{recordedDate(row)}{row.added_for_conflict?' · Related disagreement':''} · Open original evidence</small>
        </button>
      </li>)}</ul>
    </details>
    <details><summary>Scope and limits included in the file</summary>
      <ul>{brief.warnings.map((warning,index)=><li key={index}>{warning}</li>)}</ul>
    </details>
  </>;
}

export default function ReportBriefReview({summary,onRefresh}: {summary:ReportComparisonSummary; onRefresh:()=>void}) {
  const [brief,setBrief]=useState<ReportBriefData|null>(null);
  const [busy,setBusy]=useState(false);
  const [reviewed,setReviewed]=useState(false);
  const [format,setFormat]=useState<'html'|'json'>('html');
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [expired,setExpired]=useState(false);
  const [page,setPage]=useState(0);
  const [inspected,setInspected]=useState<HistoryFact|null>(null);
  const active=useRef<AbortController|null>(null);
  const previewHeading=useRef<HTMLHeadingElement>(null);
  const downloadButton=useRef<HTMLButtonElement>(null);
  const [initialCorrections]=useState(()=>new Map(correctionSession.getSnapshot().map(([id,state])=>[id,state.savedAt])));
  const corrections=useSyncExternalStore(correctionSession.subscribe,correctionSession.getSnapshot,correctionSession.getSnapshot);
  const stale=expired || corrections.some(([id,state])=>brief?.entries.some(row=>row.id===id) && state.savedAt && state.savedAt!==initialCorrections.get(id));
  useEffect(()=>()=>active.current?.abort(),[]);
  useEffect(()=>{if (brief) previewHeading.current?.focus();},[brief]);
  useEffect(()=>{if (notice) downloadButton.current?.focus();},[notice]);
  useEffect(()=>{if (stale) {active.current?.abort();setReviewed(false);setBusy(false);}},[stale]);

  async function prepare() {
    const controller=new AbortController();active.current?.abort();active.current=controller;
    setBusy(true);setError('');setNotice('');setReviewed(false);
    try {
      const result=await api<ReportBriefData>('/briefs/report-preview',{
        method:'POST',headers:{'Content-Type':'application/json'},signal:controller.signal,
        body:JSON.stringify(reportBriefRequest(summary)),
      });
      if (controller.signal.aborted) return;
      if (!reportBriefMatches(result,summary)) throw new Error('The summary does not match these reports. Refresh history and prepare it again.');
      setBrief(result);setPage(0);
    } catch (cause) {
      if (controller.signal.aborted) return;
      if (cause instanceof ApiError && cause.status===409) setExpired(true);
      setError((cause as Error).message);
    } finally {if (!controller.signal.aborted) setBusy(false);}
  }

  async function download() {
    if (!brief || !reviewed || stale || busy) return;
    const controller=new AbortController();active.current?.abort();active.current=controller;
    setBusy(true);setError('');setNotice('');
    try {
      const response=await localRequest('/api/briefs/report-export',{
        method:'POST',headers:{'Content-Type':'application/json'},signal:controller.signal,
        body:JSON.stringify({...reportBriefRequest(summary),preview_id:brief.preview_id,reviewed:true,format}),
      });
      if (!response.ok) {
        if (response.status===409) {setExpired(true);setReviewed(false);}
        throw new Error('The file could not be downloaded. Refresh history and review the comparison again.');
      }
      const blob=await response.blob();
      if (controller.signal.aborted) return;
      const url=URL.createObjectURL(blob);
      const link=document.createElement('a');link.href=url;link.download=`modus-checkup-comparison.${format}`;link.click();
      setTimeout(()=>URL.revokeObjectURL(url),1000);
      setNotice(format==='html'?'Download started. Open the file to read or print your comparison.':'Record data download started.');
    } catch (cause) {if (!controller.signal.aborted) setError((cause as Error).message);}
    finally {if (!controller.signal.aborted) setBusy(false);}
  }

  return <section className="report-brief-review" aria-label="Take this comparison with you">
    {stale ? <><p role="status">Records changed or this view expired. Review an updated comparison before downloading.</p>
      <button type="button" className="secondary" onClick={onRefresh}>Open updated history</button></>
    : brief ? <>
      <ReportBriefContents brief={brief} page={page} onPage={setPage} onInspect={setInspected} headingRef={previewHeading}/>
      <label className="brief-review-confirm"><input type="checkbox" checked={reviewed} disabled={busy}
        onChange={event=>setReviewed(event.target.checked)}/>I have reviewed this comparison and the included records.</label>
      <div className="report-brief-actions"><label>File format <select value={format} disabled={busy}
        onChange={event=>setFormat(event.target.value as 'html'|'json')}>
        <option value="html">Printable file (HTML)</option><option value="json">Record data (JSON)</option>
      </select></label>
        <button ref={downloadButton} type="button" className="primary" disabled={!reviewed || busy} onClick={()=>void download()}>{busy?'Preparing file…':'Download comparison'}</button>
      </div>
    </> : <button type="button" className="secondary" disabled={busy} onClick={()=>void prepare()}>{busy?'Preparing summary…':'Prepare a summary to keep'}</button>}
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    {brief && <OverviewRecordDetails view={brief.history_evidence} selection={null} inspected={inspected}
      onInspect={setInspected} onCloseSource={()=>setInspected(null)} onCloseSelection={()=>{}}/>}
  </section>;
}
