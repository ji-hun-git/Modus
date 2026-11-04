import type { HistoryFact } from './historyTypes';
import type { LongitudinalSeries } from './longitudinalSeries';
import { recordedDate } from './sourceDisplay';

export default function SeriesObservationList({series,selectedId,onSelect}:{
  series:LongitudinalSeries;selectedId:string;onSelect:(id:string)=>void;
}) {
  const sources=new Map(series.history_evidence.sources.map(source=>[source.id,source]));
  const conflicts=new Set(series.history_evidence.conflicts.flatMap(conflict=>conflict.fact_ids));
  const notes=new Map(series.observation_notes.map(note=>[note.fact_id,note]));
  const stateLabel=(fact:HistoryFact)=>conflicts.has(fact.id)?'Records differ':
    notes.get(fact.id)?.reason_codes.includes('INCOMPLETE_DATE') || !fact.date?'Date incomplete':notes.get(fact.id)?.reason_codes.some(code=>['QUALIFIED_OR_TEXT_VALUE','PLOT_PRECISION_UNSUPPORTED','UNIT_UNKNOWN'].includes(code))?'List only':
    fact.previous_revision_id?'Corrected record':'';
  return <div className="series-observation-list" role="group" aria-label="Recorded observations">
    <div className="series-list-columns" aria-hidden="true"><span>Recorded</span><span>Value</span><span>Original source</span></div>
    {series.observations.map(fact=><button key={fact.id} type="button" className="series-observation-row"
      aria-pressed={selectedId===fact.id} onClick={()=>onSelect(fact.id)}
      aria-label={`${recordedDate(fact)}, ${fact.value ?? 'Value not recorded'} ${fact.unit || ''}, ${sources.get(fact.source_id)?.title || 'Source record'}. Inspect evidence.`}>
      <span className="series-list-date">{recordedDate(fact)}<small>{stateLabel(fact)}</small></span>
      <span className="series-list-value">{fact.value ?? 'Not recorded'}<small>{fact.unit}</small></span>
      <span className="series-list-source">{sources.get(fact.source_id)?.title || 'Source record'}<small>Open evidence</small></span>
    </button>)}
    {!series.observations.length && <p className="series-list-empty">No observations on this page. Previous records remain available through the page controls.</p>}
  </div>;
}
