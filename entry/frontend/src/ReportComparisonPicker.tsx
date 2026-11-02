import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from './api';
import type { HistoryView, PagedSource } from './historyTypes';
import { reportIdentity } from './reportComparisonTypes';
import HistoryPager from './HistoryPager';

export default function ReportComparisonPicker({ snapshotId, selectedId, scope, onSelect }: {
  snapshotId: string; selectedId: string; scope: HistoryView['scope'];
  onSelect: (source: PagedSource) => void;
}) {
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [offset, setOffset] = useState(0);
  const [retry, setRetry] = useState(0);
  const [loaded, setLoaded] = useState<{key:string; view:HistoryView} | null>(null);
  const [failure, setFailure] = useState<{key:string; message:string; expired:boolean} | null>(null);
  const resultsHeading=useRef<HTMLHeadingElement>(null);
  const focusAfterLoad=useRef(false);
  const key = JSON.stringify([snapshotId, selectedId, scope.as_of, scope.known_at, query, offset, retry]);
  const view = loaded?.key === key ? loaded.view : null;
  const error = failure?.key === key ? failure : null;
  useEffect(()=>{
    if (!focusAfterLoad.current || (!view && !error)) return;
    focusAfterLoad.current=false;
    resultsHeading.current?.focus();
    resultsHeading.current?.scrollIntoView({block:'nearest'});
  },[view,error]);
  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({snapshot_id:snapshotId, section:'sources', limit:'12', offset:String(offset)});
    if (query) params.set('query', query);
    void api<HistoryView>(`/history/page?${params}`, {signal:controller.signal}).then(result => {
      if (controller.signal.aborted) return;
      if (result.page?.snapshot_id !== snapshotId || result.scope.known_at !== scope.known_at || result.scope.as_of !== scope.as_of)
        throw new Error('The report list no longer matches this history view. Close and reopen the comparison.');
      setLoaded({key,view:result});
    }).catch((err:Error) => {
      if (!controller.signal.aborted) setFailure({key,message:err.message,expired:err instanceof ApiError && [409,410].includes(err.status)});
    });
    return () => controller.abort();
  }, [key]);
  return <section className="report-comparison-picker" aria-label="Choose comparison report">
    <form onSubmit={event => {event.preventDefault();focusAfterLoad.current=true;setQuery(search.trim());setOffset(0);setRetry(value=>value+1);}}>
      <label htmlFor="comparison-report-search">Find a report</label>
      <div><input id="comparison-report-search" type="search" value={search} maxLength={200}
        onChange={event=>setSearch(event.target.value)} placeholder="Search recorded file names" />
      <button type="submit" className="secondary">Search</button></div>
    </form>
    <h4 ref={resultsHeading} tabIndex={-1}>Reports in this history view</h4>
    {!view && !error && <p role="status">Opening reports in this history view…</p>}
    {error && <div role="alert"><p>{error.message}</p>
      {error.expired ? <p>Close this comparison and refresh your history before trying again.</p>
        : <button className="text-button" onClick={()=>{focusAfterLoad.current=true;setRetry(value=>value+1);}}>Retry report list</button>}</div>}
    {view && <>
      <div className="report-comparison-options">{view.sources.map(source=><button key={source.id} type="button"
        disabled={source.id===selectedId} aria-label={`Compare with ${source.title}; ${reportIdentity(source)}; source ${source.id}`}
        onClick={()=>onSelect(source)}>
        <strong>{source.title}</strong><span>{reportIdentity(source)}{source.id===selectedId?' · Selected report':''}</span>
      </button>)}</div>
      {!view.sources.length && <p>No files match this search in the selected history view.</p>}
      {view.sources.length===1 && view.sources[0].id===selectedId && view.page?.total===1 && <p>Choose a history view with another report to compare.</p>}
      <HistoryPager view={view} onPage={next=>{focusAfterLoad.current=true;setOffset(next);}} noun="reports" />
    </>}
  </section>;
}
