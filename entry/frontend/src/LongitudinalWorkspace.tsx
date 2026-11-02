import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { ArrowLeft, CircleDot, GitCompareArrows } from 'lucide-react';
import type { HistoryFact, HistoryView } from './historyTypes';
import { friendlyRecordName } from './HomeReportReadings';
import { recordedDate } from './sourceDisplay';
import { timeLabel, dateLabel } from './ui';
import useLongitudinalSeries from './useLongitudinalSeries';
import SeriesChart from './SeriesChart';
import SeriesObservationList from './SeriesObservationList';
import SourceCubeEvidence from './SourceCubeEvidence';
import MedicalTestReference from './MedicalTestReference';
import HomeAskBar from './HomeAskBar';
import { correctionSession } from './correctionSession';
import './longitudinal-workspace.css';

export default function LongitudinalWorkspace({parent,anchor,onClose,onCompare,files}:{
  parent:HistoryView;anchor:HistoryFact;onClose:()=>void;onCompare:()=>void;files:React.ReactNode;
}) {
  const history=useLongitudinalSeries(parent,anchor.id);
  const series=history.series;
  const [selectedId,setSelectedId]=useState(anchor.id);
  const [chosenUnit,setChosenUnit]=useState(anchor.unit || '');
  const [invalidated,setInvalidated]=useState(false);
  const [initialCorrections]=useState(()=>new Map(correctionSession.getSnapshot().map(([id,state])=>[id,state.savedAt])));
  const corrections=useSyncExternalStore(correctionSession.subscribe,correctionSession.getSnapshot,correctionSession.getSnapshot);
  const heading=useRef<HTMLHeadingElement>(null);
  const evidenceHeading=useRef<HTMLHeadingElement>(null);
  const pageFocus=useRef(false);
  const evidence=series?.history_evidence;
  const facts=evidence?[...evidence.facts,...evidence.undated_facts]:[];
  const selected=facts.find(fact=>fact.id===selectedId) || facts.find(fact=>fact.id===anchor.id) || facts[0];
  const source=evidence?.sources.find(item=>item.id===selected?.source_id);
  const units=[...new Set(series?.plot_points.map(point=>point.unit) || [])];
  const unit=units.includes(chosenUnit)?chosenUnit:units[0] || '';
  const stale=invalidated || corrections.some(([id,state])=>facts.some(fact=>fact.id===id) && state.savedAt && state.savedAt!==initialCorrections.get(id));
  const selectedNotes=series?.observation_notes.find(note=>note.fact_id===selected?.id)?.notes || [];
  const adjacentNotes=[...new Set(series?.edges.filter(edge=>edge.from_id===selected?.id || edge.to_id===selected?.id).flatMap(edge=>edge.notes) || [])];
  const selectedDifference=series?.edges.find(edge=>edge.to_id===selected?.id && edge.connectable && edge.difference!==null);
  const previousFact=series?.observations.find(fact=>fact.id===selectedDifference?.from_id);
  useEffect(()=>{heading.current?.focus({preventScroll:true});},[]);
  useEffect(()=>{if(stale)setInvalidated(true);},[stale]);
  useEffect(()=>{
    if (pageFocus.current && (series || history.error)) {
      pageFocus.current=false;heading.current?.focus();heading.current?.scrollIntoView({block:'start'});
    }
  },[series,history.error]);
  function selectObservation(id:string) {
    setSelectedId(id);
    const next=series?.plot_points.find(point=>point.fact_id===id);
    if(next)setChosenUnit(next.unit);
    if(window.matchMedia('(max-width: 900px)').matches) requestAnimationFrame(()=>{
      evidenceHeading.current?.focus({preventScroll:true});evidenceHeading.current?.scrollIntoView({block:'start'});
    });
  }
  function updatedHistory() {window.dispatchEvent(new Event('modus:show-current-history'));onClose();}
  return <section className="longitudinal-workspace" aria-label="Selected result workspace">
    <div className="series-breadcrumb">
      <button type="button" className="text-button" onClick={onClose}><ArrowLeft size={16} aria-hidden="true" />Back to your report</button>
      <details className="series-files"><summary><CircleDot size={16} aria-hidden="true" />Your files</summary><div>{files}</div></details>
    </div>
    <header className="series-workspace-heading">
      <div><h2 ref={heading} tabIndex={-1}>{friendlyRecordName(anchor.label)}</h2>
        <p>{series?`${series.page.total} recorded observations across ${series.counts.sources} source files`:'Your recorded history, with the original beside it.'}</p></div>
      <button type="button" className="secondary" onClick={onCompare}><GitCompareArrows size={16} aria-hidden="true" />Compare reports</button>
    </header>
    <p className="series-scope">{parent.scope.as_of?`Recorded through ${dateLabel(parent.scope.as_of)}`:'All recorded dates'} · Available in Modus by {timeLabel(parent.scope.known_at)}</p>
    {stale && <div className="series-state" role="status"><strong>A saved record has changed.</strong><p>Open updated history to explore its revised series. The original evidence and this earlier snapshot remain preserved.</p>
      <button className="secondary" onClick={updatedHistory}>Open updated history</button></div>}
    {!series && !history.error && <div className="series-state" role="status">Opening your recorded observations…</div>}
    {history.error && <div className="series-state" role="alert"><p>{history.error.message}</p>
      <button className="secondary" onClick={history.error.expired?updatedHistory:history.retry}>{history.error.expired?'Open updated history':'Retry series'}</button></div>}
    {series && evidence && <div className="series-workspace-grid">
      <div className="series-analysis">
        {!stale && <>
          <section className="series-analysis-panel" aria-label="Observation chart">
            <header><h3>Across your history</h3>{units.length>1 && <label>Unit as recorded<select value={unit} onChange={event=>setChosenUnit(event.target.value)}>{units.map(item=><option key={item}>{item}</option>)}</select></label>}</header>
            <SeriesChart series={series} unit={unit} selectedId={selected?.id || ''} onSelect={selectObservation} />
            {selectedDifference && previousFact && <p className="series-recorded-change"><span>Recorded change from {recordedDate(previousFact)}</span><strong>{selectedDifference.difference} {selectedDifference.unit}</strong></p>}
            {units.length>1 && <p className="series-context-note">Each recorded unit has its own chart. No values are converted.</p>}
            {selected && !series.observations.some(fact=>fact.id===selected.id) && <p className="series-context-note">Your selected record is outside this page. Its original evidence remains open.</p>}
          </section>
          <section className="series-records-panel" aria-label="Observation records">
            <header><h3>Recorded observations</h3><span>{series.page.offset+(series.page.returned?1:0)}–{series.page.offset+series.page.returned} of {series.page.total}</span></header>
            <SeriesObservationList series={series} selectedId={selected?.id || ''} onSelect={selectObservation} />
            {(series.page.next_offset!==null || series.page.previous_offset!==null) && <nav className="history-pagination" aria-label="Series pages">
              <button className="text-button" disabled={series.page.previous_offset===null} onClick={()=>{pageFocus.current=true;history.setOffset(series.page.previous_offset!);}}>Previous observations</button>
              <button className="text-button" disabled={series.page.next_offset===null} onClick={()=>{pageFocus.current=true;history.setOffset(series.page.next_offset!);}}>Next observations</button>
            </nav>}
          </section>
          <details className="series-method"><summary>About this recorded series</summary><ul>{series.limitations.map((note,index)=><li key={index}>{note}</li>)}</ul></details>
        </>}
        <HomeAskBar view={parent} />
      </div>
      <aside className="series-evidence" aria-label="Selected observation evidence">
        <header><div><h3 ref={evidenceHeading} tabIndex={-1}>Original evidence</h3><p>{selected?recordedDate(selected):'Choose a recorded observation'}</p></div></header>
        {selected && source ? <>
          <SourceCubeEvidence key={`${selected.id}:${evidence.scope.scope_id}`} source={source} facts={[selected]} view={evidence} initialFactId={selected.id} compact />
          {!!selectedNotes.length && <div className="series-evidence-notes">{selectedNotes.map((note,index)=><p key={index}>{note}</p>)}</div>}
          {!!adjacentNotes.length && <details className="series-method"><summary>Comparison context</summary><ul>{adjacentNotes.map((note,index)=><li key={index}>{note}</li>)}</ul></details>}
          <MedicalTestReference fact={selected} />
        </> : <p>The original evidence is unavailable in this history view.</p>}
      </aside>
    </div>}
    {selected && <span className="sr-only" role="status">Selected {selected.value} {selected.unit}, {recordedDate(selected)}. Original evidence is shown beside the history.</span>}
  </section>;
}
