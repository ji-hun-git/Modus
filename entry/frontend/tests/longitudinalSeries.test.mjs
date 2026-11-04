import test from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { build } from 'esbuild';

const compiled=await build({stdin:{contents:[
  'export * from "./longitudinalSeries";',
  'export {default as SeriesChart} from "./SeriesChart";',
  'export {default as SeriesObservationList} from "./SeriesObservationList";',
  'export {default as SourceCubeEvidence} from "./SourceCubeEvidence";',
  'export {default as LongitudinalWorkspace} from "./LongitudinalWorkspace";',
].join('\n'),resolveDir:fileURLToPath(new URL('../src/',import.meta.url)),loader:'ts'},
  bundle:true,write:false,format:'esm',platform:'node',target:'es2022',jsx:'automatic',loader:{'.css':'empty'},
  plugins:[{name:'shared-react',setup(builder){builder.onResolve({filter:/^(react(?:\/.*)?|react-dom(?:\/.*)?|lucide-react)$/},args=>({path:import.meta.resolve(args.path),external:true}));}}]});
const {seriesMatches,seriesGeometry,selectedSeriesDifference,hasNewSeriesCorrection,SeriesChart,SeriesObservationList,SourceCubeEvidence,LongitudinalWorkspace}=await import('data:text/javascript;base64,'+Buffer.from(compiled.outputFiles[0].text).toString('base64'));
const scope={scope_id:'scope-a',known_at:'2026-11-02T00:00:00Z',as_of:null,captured_at:'2026-11-02T00:00:00Z'};
const row=(id,date,value,extra={})=>({id,source_id:`source-${id}`,kind:'measurement',label:'HbA1c',value,unit:'%',date,occurred_on:date,
  date_precision:'day',available_at:'2026-11-01T00:00:00Z',source_quote:`HbA1c ${value} %`,page:1,revision_id:`revision-${id}`,
  reference_range:'4.0–6.0 %',specimen:'Whole blood',test_method:'HPLC',...extra});
function fixture(){
  const observations=[row('a','2024-04-12','5.7'),row('b','2025-04-12','5.9'),row('c','2026-04-12','6.1')];
  const sources=observations.map(fact=>({id:fact.source_id,title:`Checkup ${fact.date}.pdf`,type:'pdf',date:fact.date,available_at:fact.available_at,original_available:true}));
  return {format:'modus-longitudinal-series-v1',snapshot_id:'snapshot-a',scope:structuredClone(scope),policy_version:'context-v1',anchor_id:'c',label:'HbA1c',kind:'measurement',
    observations,plot_points:observations.map(fact=>({fact_id:fact.id,date:fact.date,value:Number(fact.value),unit:fact.unit})),
    edges:[{from_id:'a',to_id:'b',status:'comparable',connectable:true,difference:'0.2',unit:'%',notes:[],reason_codes:[]},
      {from_id:'b',to_id:'c',status:'not_comparable',connectable:false,difference:null,unit:'%',notes:['Test methods differ.'],reason_codes:['METHOD_MISMATCH']}],
    observation_notes:observations.map(fact=>({fact_id:fact.id,notes:[],reason_codes:[]})),
    history_evidence:{scope:structuredClone(scope),facts:structuredClone(observations),undated_facts:[],sources,conflicts:[],
      counts:{facts:3,sources:3,conflicts:0,undated_facts:0,measurements:3}},
    page:{offset:0,limit:30,returned:3,total:3,next_offset:null,previous_offset:null},counts:{dated:3,undated:0,sources:3,conflicts:0},limitations:['Missing records do not establish missing care.']};
}
const matches=series=>seriesMatches(series,'snapshot-a','c',scope,0);
const render=(component,props)=>renderToStaticMarkup(createElement(component,props));
const noop=()=>{};

test('captured series accepts exact saved observations, keeping unsupported edges disconnected',()=>{
  const series=fixture();assert.equal(matches(series),true);
  assert.deepEqual(seriesGeometry(series,'%').edges.map(edge=>[edge.from.fact_id,edge.to.fact_id]),[['a','b']]);
});
test('response identity requires both frozen scopes, selected anchor and snapshot',()=>{
  for(const mutate of [s=>s.snapshot_id='other',s=>s.anchor_id='b',s=>s.scope.scope_id='other',s=>s.history_evidence.scope.known_at='2026-11-03T00:00:00Z',s=>s.history_evidence.scope.as_of='2020-01-01',s=>s.history_evidence.facts.pop()]){
    const series=fixture();mutate(series);assert.equal(matches(series),false);
  }
});
test('evidence cannot swap source, date, value, unit, revision, quote or lab context',()=>{
  for(const [key,value] of Object.entries({source_id:'source-b',date:'2020-01-01',occurred_on:'2020-01-01',value:'100',unit:'mmol/mol',revision_id:'old',source_quote:'Another value',reference_range:null,specimen:null,test_method:'Other',available_at:'2020-01-01T00:00:00Z'})){
    const series=fixture();series.history_evidence.facts[0][key]=value;assert.equal(matches(series),false,key);
  }
});
test('plot points must match numeric saved value, unit and canonical date',()=>{
  for(const patch of [{value:999},{unit:'mmol/mol'},{date:'2025-04-12'},{value:NaN},{value:Infinity}]){
    const series=fixture();Object.assign(series.plot_points[0],patch);assert.equal(matches(series),false);
  }
  const invalid=fixture();invalid.observations[0].date=invalid.history_evidence.facts[0].date=invalid.plot_points[0].date='2024-02-30';assert.equal(matches(invalid),false);
});
test('qualified and absent values cannot be presented as numeric plot points',()=>{
  for(const value of ['<5.7','',' ',null,'Not recorded']){
    const series=fixture();series.observations[0].value=series.history_evidence.facts[0].value=value;series.plot_points[0].value=Number(value);assert.equal(matches(series),false);
  }
});
test('scope-hidden observations, duplicate IDs and oversized evidence fail closed',()=>{
  for(const mutate of [s=>s.observations[0].value_withheld=true,s=>s.history_evidence.facts[0].within_date_scope=false,
    s=>s.observations[1].id='a',s=>s.plot_points.push({...s.plot_points[0]}),
    s=>s.history_evidence.facts.push(...Array.from({length:120},(_,i)=>({...s.observations[0],id:`extra-${i}`}))),s=>s.page.limit=0]){
    const series=fixture();mutate(series);assert.equal(matches(series),false);
  }
});
test('connecting edges cannot cross units, point sets or same-day ambiguity',()=>{
  for(const mutate of [s=>s.edges[0].to_id='offpage',s=>s.edges[0].status='not_comparable',
    s=>{s.observations[1].unit=s.history_evidence.facts[1].unit=s.plot_points[1].unit='mmol/mol';},
    s=>{s.observations[1].date=s.history_evidence.facts[1].date=s.plot_points[1].date=s.plot_points[0].date;}]){
    const series=fixture();mutate(series);assert.equal(matches(series),false);
  }
});
test('geometry excludes unrequested units and never plots evidence-only companions',()=>{
  const series=fixture();series.plot_points[2].unit='mmol/mol';series.history_evidence.facts.push(row('companion','2026-04-12','200'));
  const geometry=seriesGeometry(series,'%');assert.deepEqual(geometry.points.map(point=>point.fact_id),['a','b']);
  assert.equal(seriesGeometry(series,'mmol/mol').points.length,1);assert.equal(seriesGeometry(series,'unknown').points.length,0);
});
test('single observations have finite central coordinates and no invented line',()=>{
  const series=fixture();series.plot_points=[series.plot_points[2]];
  const geometry=seriesGeometry(series,'%');assert.equal(geometry.points[0].x,50);assert.equal(geometry.points[0].y,50);assert.equal(geometry.edges.length,0);
});
test('opposite finite extremes cannot overflow chart coordinates',()=>{
  const series=fixture();series.plot_points[0].value=-1e308;series.plot_points[1].value=1e308;
  for(const point of seriesGeometry(series,'%').points){assert.ok(Number.isFinite(point.x));assert.ok(Number.isFinite(point.y));assert.ok(point.y>=18&&point.y<=82);}
});
test('chart keeps exact source buttons and only draws authorized lines',()=>{
  const html=render(SeriesChart,{series:fixture(),unit:'%',selectedId:'c',onSelect:noop});
  assert.equal((html.match(/class="series-authorized-edge"/g)||[]).length,1);
  assert.equal((html.match(/class="series-point/g)||[]).length,3);
  assert.match(html,/aria-label="6.1 %, 12 Apr 2026, Checkup 2026-04-12.pdf"/);
  assert.match(html,/aria-pressed="true"/);
});
test('same-day conflicting points remain individually selectable without a connecting edge',()=>{
  const series=fixture();series.plot_points[1].date=series.plot_points[0].date;series.edges=[];
  series.history_evidence.conflicts=[{id:'conflict',fact_ids:['a','b']}];
  const html=render(SeriesChart,{series,unit:'%',selectedId:'a',onSelect:noop});
  assert.equal((html.match(/is-disputed/g)||[]).length,2);assert.equal((html.match(/class="series-point/g)||[]).length,3);
  assert.doesNotMatch(html,/series-authorized-edge/);assert.match(html,/records disagree/);
});
test('unplottable records stay exact and selectable in the list',()=>{
  const series=fixture();series.observations[0]=row('a',null,'<5.7',{occurred_on:'2024',date_precision:'year'});series.plot_points=[];
  series.observation_notes[0]={fact_id:'a',reason_codes:['INCOMPLETE_DATE'],notes:['The date is incomplete.']};
  const html=render(SeriesObservationList,{series,selectedId:'a',onSelect:noop});
  assert.match(html,/Date incomplete/);assert.match(html,/&lt;5.7/);assert.match(html,/Inspect evidence/);
  assert.equal((html.match(/class="series-observation-row"/g)||[]).length,3);
  assert.match(render(SeriesChart,{series,unit:'%',selectedId:'a',onSelect:noop}),/These entries stay in the record list/);
});
test('document titles and quoted values render as text, not HTML',()=>{
  const series=fixture();series.history_evidence.sources[0].title='<img src=x onerror=alert(1)>';series.observations[0].value='<script>bad</script>';
  const html=render(SeriesObservationList,{series,selectedId:'a',onSelect:noop});
  assert.match(html,/&lt;img/);assert.match(html,/&lt;script/);assert.doesNotMatch(html,/<script>|<img /);
});
test('compact inspector keeps original download, exact excerpt and progressive version access',()=>{
  const series=fixture();const fact=series.history_evidence.facts[0];
  const html=render(SourceCubeEvidence,{source:series.history_evidence.sources[0],facts:[fact],view:series.history_evidence,initialFactId:fact.id,compact:true});
  assert.match(html,/Download original/);assert.match(html,/<blockquote>HbA1c 5.7 %<\/blockquote>/);
  assert.match(html,/<details class="source-evidence-corrections"><summary>Corrections &amp; saved versions/);
  assert.match(html,/<details class="source-evidence-lab-context"><summary>Range, specimen &amp; method/);
  assert.doesNotMatch(html,/source-evidence-picker/);
});
test('compact inspector does not display irrelevant empty lab fields',()=>{
  const series=fixture();const fact=series.history_evidence.facts[0];fact.reference_range=fact.specimen=fact.test_method=null;
  const html=render(SourceCubeEvidence,{source:series.history_evidence.sources[0],facts:[fact],view:series.history_evidence,compact:true});
  assert.doesNotMatch(html,/source-evidence-lab-context|Lab’s reference range|Specimen|Test method/);
  assert.match(html,/As written in your record/);
});
test('selected workspace begins in a bounded loading state without fabricating observations',()=>{
  const series=fixture();const parent={...series.history_evidence,page:{...series.page,snapshot_id:series.snapshot_id,section:'sources'}};
  const html=render(LongitudinalWorkspace,{parent,anchor:series.observations[2],onClose:noop,onCompare:noop,files:createElement('div',null,'Orbit')});
  assert.match(html,/Selected result workspace/);assert.match(html,/Opening your recorded observations/);assert.match(html,/Your files/);
  assert.doesNotMatch(html,/series-point|Recorded change from/);
});
test('legacy views without captured snapshot offer refresh instead of an uncaptured request',()=>{
  const series=fixture();const html=render(LongitudinalWorkspace,{parent:series.history_evidence,anchor:series.observations[2],onClose:noop,onCompare:noop,files:null});
  assert.match(html,/Refresh your history before opening this series/);assert.match(html,/Open updated history/);
});

test('changing the displayed unit cannot retain a difference from another unit',()=>{
  const series=fixture();
  assert.equal(selectedSeriesDifference(series,'b','%')?.difference,'0.2');
  assert.equal(selectedSeriesDifference(series,'b','mmol/mol'),undefined);
  assert.equal(selectedSeriesDifference(series,'c','%'),undefined);
  series.plot_points=series.plot_points.filter(point=>point.fact_id!=='a');
  assert.equal(selectedSeriesDifference(series,'b','%'),undefined,'no difference without both chart observations');
});

test('a delayed correction invalidates a previously seen page while the next page loads',()=>{
  const seen=new Set(['c']);const initial=new Map([['a','2026-10-01T00:00:00Z']]);
  for(const fact of fixture().history_evidence.facts)seen.add(fact.id);
  assert.equal(hasNewSeriesCorrection(seen,[['a',{savedAt:null}]],initial),false,'uncertain request is not a confirmed save');
  assert.equal(hasNewSeriesCorrection(seen,[['a',{savedAt:'2026-10-01T00:00:00Z'}]],initial),false,'same receipt does not invalidate');
  // The old page is no longer rendered; identity tracking survives its empty loading state.
  assert.equal(hasNewSeriesCorrection(seen,[['a',{savedAt:'2026-11-03T00:00:00Z'}]],initial),true);
  assert.equal(hasNewSeriesCorrection(seen,[['unrelated',{savedAt:'2026-11-03T00:00:00Z'}]],initial),false);
});

test('long selected numeric spelling stays in a wrapping caption instead of a clipped marker label',()=>{
  const series=fixture();const exact='0'.repeat(150)+'6.1';series.observations[2].value=exact;
  const html=render(SeriesChart,{series,unit:'%',selectedId:'c',onSelect:noop});
  assert.ok(html.includes(`<p class="series-chart-selection"><strong>${exact} %</strong>`));
  assert.doesNotMatch(html,/<span><\/span><strong>/,'markers do not carry an unbounded floating label');
});

test('a chart caption never relabels a selection from an unshown unit',()=>{
  const series=fixture();series.plot_points[2].unit='mmol/mol';
  const html=render(SeriesChart,{series,unit:'%',selectedId:'c',onSelect:noop});
  assert.doesNotMatch(html,/series-chart-selection/);
  assert.match(html,/Recorded HbA1c observations in %/);
});
