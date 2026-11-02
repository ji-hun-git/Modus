import { useState } from 'react';
import type { HistoryView, HistoryFact } from './historyTypes';
import { labFields } from './LabContext';
import OverviewRecordDetails from './OverviewRecordDetails';
import { recordedDate } from './sourceDisplay';

export default function CheckupComparison({view}:{view:HistoryView}) {
  const [inspected,setInspected]=useState<HistoryFact|null>(null);
  const comparison=view.checkup_comparison;
  if (!comparison) return null;
  const rows=[comparison.current,...comparison.previous];
  const evidenceView={...view,sources:comparison.sources,facts:rows.filter(r=>r.date),undated_facts:rows.filter(r=>!r.date)};
  const hasContext=rows.some(fact=>Object.keys(labFields).some(key=>fact[key as keyof typeof labFields]));
  return <details className="checkup-comparison">
    <summary><span>Compare with previous checkup</span><span className="checkup-summary-hint">Dates &amp; sources</span></summary>
    <div className="checkup-pair">{rows.map((fact,index)=><article key={fact.id}>
      <h4>{index===0?'Selected result':'Previous dated result'}{index>0&&comparison.previous_count>1?` · ${index}`:''}</h4>
      <time>{recordedDate(fact)}</time>
      <p className="checkup-value"><strong>{fact.value}</strong> <span>{fact.unit || 'Unit not recorded'}</span></p>
      <button type="button" className="checkup-source" onClick={()=>setInspected(fact)}
        aria-label={`Original evidence · ${recordedDate(fact)} · ${index===0?'Selected result':`Previous result ${index}`}`}>
        <span>{comparison.sources.find(source=>source.id===fact.source_id)?.title || 'Source record'}</span>
        <span aria-hidden="true">↗</span>
      </button>
    </article>)}</div>
    {comparison.difference!==null && <div className="checkup-difference"><span>Recorded difference</span>
      <strong>{comparison.difference} {comparison.unit}</strong><small>Selected minus previous</small></div>}
    {!!comparison.notes.length && <div className="checkup-notes"><p>{comparison.difference===null?'Before comparing these results':'Record context'}</p>
      <ul>{comparison.notes.map(note=><li key={note}>{note}</li>)}</ul></div>}
    <details className="checkup-context"><summary>How these records were compared</summary>
      <p>{comparison.basis}</p>
      {hasContext ? <div className="checkup-context-grid">{rows.map((fact,index)=><div key={fact.id}>
        <h4>{index===0?'Selected result':`Previous result${comparison.previous_count>1?` ${index}`:''}`}</h4>
        <dl>{Object.entries(labFields).map(([key,label])=><div key={key}>
          <dt>{label}</dt><dd>{fact[key as keyof typeof labFields] || 'Not recorded'}</dd>
        </div>)}</dl>
      </div>)}</div> : <p>Reference range, specimen and test method were not recorded for these results.</p>}
    </details>
    {comparison.previous_count>comparison.previous.length && <p>Showing {comparison.previous.length} of {comparison.previous_count} results on the previous date.</p>}
    <OverviewRecordDetails view={evidenceView} selection={null} inspected={inspected} onInspect={setInspected}
      onCloseSource={()=>setInspected(null)} onCloseSelection={()=>{}} />
  </details>;
}
