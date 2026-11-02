import { useRef } from 'react';
import type { LongitudinalSeries } from './longitudinalSeries';
import { seriesGeometry } from './longitudinalSeries';
import { dateLabel } from './ui';

export default function SeriesChart({series,unit,selectedId,onSelect}:{
  series:LongitudinalSeries;unit:string;selectedId:string;onSelect:(id:string)=>void;
}) {
  const geometry=seriesGeometry(series,unit);
  const facts=new Map(series.observations.map(fact=>[fact.id,fact]));
  const sourceTitles=new Map(series.history_evidence.sources.map(source=>[source.id,source.title]));
  const disputed=new Set(series.history_evidence.conflicts.flatMap(conflict=>conflict.fact_ids));
  const controls=useRef(new Map<string,HTMLButtonElement>());
  const selectedPoint=geometry.points.find(point=>point.fact_id===selectedId);
  if (!geometry.points.length) return <div className="series-chart-empty"><p>These entries stay in the record list.</p>
    <span>A chart needs a complete date, a numeric value and a recorded unit.</span></div>;
  return <div className="series-chart" aria-label={`Recorded ${series.label} observations in ${unit}`}>
    <div className="series-chart-labels"><span>{unit}</span><span>{geometry.points.length===1?'One recorded observation':'Select an observation to inspect its source'}</span></div>
    <div className="series-chart-stage">
      <div className="series-chart-scale" aria-hidden="true"><span>{facts.get(geometry.high!.fact_id)?.value}</span>
        {geometry.high!.value!==geometry.low!.value && <span>{facts.get(geometry.low!.fact_id)?.value}</span>}</div>
      <div className="series-chart-canvas">
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          {[18,50,82].map(y=><line key={y} className="series-grid-line" x1="0" x2="100" y1={y} y2={y} />)}
          {geometry.edges.map(edge=><line key={`${edge.from.fact_id}:${edge.to.fact_id}`} className="series-authorized-edge"
            x1={edge.from.x} y1={edge.from.y} x2={edge.to.x} y2={edge.to.y} />)}
        </svg>
        {geometry.points.map((point,index)=>{
          const fact=facts.get(point.fact_id)!;
          return <button key={point.fact_id} ref={node=>{if(node)controls.current.set(point.fact_id,node);else controls.current.delete(point.fact_id);}}
            type="button" className={`series-point${selectedId===point.fact_id?' is-selected':''}${disputed.has(point.fact_id)?' is-disputed':''}`}
            style={{left:`${point.x}%`,top:`${point.y}%`}} aria-pressed={selectedId===point.fact_id}
            aria-label={`${fact.value} ${point.unit}, ${dateLabel(point.date)}, ${sourceTitles.get(fact.source_id) || 'Source record'}${disputed.has(point.fact_id)?', records disagree':''}`}
            onClick={()=>onSelect(point.fact_id)} onKeyDown={event=>{
              if (!['ArrowLeft','ArrowRight'].includes(event.key)) return;
              event.preventDefault();const step=event.key==='ArrowRight'?1:-1;
              controls.current.get(geometry.points[(index+step+geometry.points.length)%geometry.points.length].fact_id)?.focus();
            }}><span /></button>;
        })}
      </div>
    </div>
    <div className="series-chart-dates"><span>{dateLabel(geometry.first!)}</span>{geometry.first!==geometry.last && <span>{dateLabel(geometry.last!)}</span>}</div>
    {selectedPoint && <p className="series-chart-selection"><strong>{facts.get(selectedId)?.value} {unit}</strong><span>{dateLabel(selectedPoint.date)}</span></p>}
    <p className="series-chart-note">{geometry.edges.length?'Lines join only records with matching comparison context.':'Observations are shown separately; no connecting line is inferred.'}
      {geometry.points.some(point=>disputed.has(point.fact_id)) && ' Square markers have conflicting records.'}</p>
  </div>;
}
