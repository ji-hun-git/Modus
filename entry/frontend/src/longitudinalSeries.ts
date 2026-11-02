import type { HistoryFact, HistoryView } from './historyTypes';

export type SeriesPoint = {fact_id:string; date:string; value:number; unit:string};
export type SeriesEdge = {from_id:string; to_id:string; status:'comparable'|'not_comparable';
  connectable:boolean; difference:string|null; unit:string|null; reason_codes:string[]; notes:string[]};
export type LongitudinalSeries = {
  format:'modus-longitudinal-series-v1'; snapshot_id:string; scope:HistoryView['scope'];
  policy_version:string; anchor_id:string; label:string; kind:HistoryFact['kind'];
  observations:(HistoryFact & {date_precision?:string})[];
  plot_points:SeriesPoint[]; edges:SeriesEdge[];
  observation_notes:{fact_id:string; reason_codes:string[]; notes:string[]}[];
  history_evidence:HistoryView;
  page:{offset:number;limit:number;returned:number;total:number;next_offset:number|null;previous_offset:number|null};
  counts:{dated:number;undated:number;sources:number;conflicts:number}; limitations:string[];
};

export function seriesMatches(result:LongitudinalSeries, snapshot:string, anchor:string,
  scope:HistoryView['scope'], offset:number) {
  try {
    const facts=[...result.history_evidence.facts,...result.history_evidence.undated_facts];
    const evidence=new Map(facts.map(fact=>[fact.id,fact]));
    const rows=new Map(result.observations.map(fact=>[fact.id,fact]));
    const points=new Map(result.plot_points.map(point=>[point.fact_id,point]));
    const sources=new Set(result.history_evidence.sources.map(source=>source.id));
    const sameSavedRecord=(fact:HistoryFact)=>{
      const saved=evidence.get(fact.id);
      return saved && ['source_id','kind','label','value','unit','date','occurred_on','revision_id','source_quote',
        'available_at','reference_range','specimen','test_method'].every(key=>
          JSON.stringify(saved[key as keyof HistoryFact])===JSON.stringify(fact[key as keyof HistoryFact])) &&
        !saved.value_withheld && saved.within_date_scope!==false;
    };
    return result.format==='modus-longitudinal-series-v1' && result.snapshot_id===snapshot && result.anchor_id===anchor &&
      result.kind==='measurement' && evidence.has(anchor) &&
      [result.scope,result.history_evidence.scope].every(value=>value.scope_id===scope.scope_id && value.known_at===scope.known_at && value.as_of===scope.as_of) &&
      result.page.offset===offset && Number.isInteger(offset) && offset>=0 && result.page.returned===result.observations.length && Number.isInteger(result.page.limit) && result.page.limit>=1 && result.page.limit<=50 &&
      result.observations.length<=result.page.limit && result.page.total>=result.page.returned && facts.length<=120 &&
      evidence.size===facts.length && rows.size===result.observations.length && points.size===result.plot_points.length &&
      result.observations.every(fact=>sameSavedRecord(fact) && sources.has(fact.source_id) && fact.kind==='measurement' &&
        !fact.value_withheld && fact.within_date_scope!==false) &&
      result.plot_points.every(point=>Number.isFinite(point.value) && rows.has(point.fact_id) &&
        /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(String(rows.get(point.fact_id)?.value)) &&
        Number(rows.get(point.fact_id)?.value)===point.value &&
        point.date===rows.get(point.fact_id)?.date && point.unit===rows.get(point.fact_id)?.unit &&
        !!point.unit && /^\d{4}-\d{2}-\d{2}$/.test(point.date) && new Date(`${point.date}T00:00:00Z`).toISOString().slice(0,10)===point.date) &&
      result.edges.every(edge=>rows.has(edge.from_id) && rows.has(edge.to_id) && edge.from_id!==edge.to_id &&
        (!edge.connectable || (edge.status==='comparable' && points.has(edge.from_id) && points.has(edge.to_id) &&
          points.get(edge.from_id)?.unit===points.get(edge.to_id)?.unit && points.get(edge.from_id)!.date<points.get(edge.to_id)!.date))) &&
      result.observation_notes.every(note=>rows.has(note.fact_id) && Array.isArray(note.notes)) && Array.isArray(result.limitations);
  } catch { return false; }
}

// Screen geometry only. No comparability decisions, conversions or result deltas.
export function seriesGeometry(series:LongitudinalSeries, unit:string) {
  const points=series.plot_points.filter(point=>point.unit===unit);
  if (!points.length) return {points:[],edges:[],low:null,high:null,first:null,last:null};
  const times=points.map(point=>Date.parse(`${point.date}T00:00:00Z`));
  const minTime=Math.min(...times), maxTime=Math.max(...times);
  const low=Math.min(...points.map(point=>point.value)), high=Math.max(...points.map(point=>point.value));
  // Normalize only drawing coordinates so two finite extremes cannot overflow the SVG range.
  const scale=Math.max(Math.abs(low),Math.abs(high),1);
  const span=high/scale-low/scale;
  const positioned=points.map((point,index)=>({...point,
    x:minTime===maxTime?50:8+(times[index]-minTime)/(maxTime-minTime)*84,
    y:span===0?50:82-(point.value/scale-low/scale)/span*64,
  }));
  const byId=new Map(positioned.map(point=>[point.fact_id,point]));
  const edges=series.edges.filter(edge=>edge.connectable && edge.status==='comparable' &&
    byId.has(edge.from_id) && byId.has(edge.to_id) && byId.get(edge.from_id)!.date<byId.get(edge.to_id)!.date)
    .map(edge=>({from:byId.get(edge.from_id)!,to:byId.get(edge.to_id)!}));
  return {points:positioned,edges,low:points.find(point=>point.value===low)!,high:points.find(point=>point.value===high)!,
    first:points.map(point=>point.date).sort()[0],last:points.map(point=>point.date).sort().at(-1)!};
}
