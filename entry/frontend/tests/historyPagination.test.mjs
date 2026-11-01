import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const result=await build({stdin:{contents:`export {historyPageQuery} from './useHistoryView';
  export {default as HistoryPager} from './HistoryPager'; export {reportSummaries} from './homeReportData';
  export {default as OrbitMap} from './OrbitMap'; export {historySuggestions} from './HistoryQuestionPanel';
  export {default as SourceCubeEvidence} from './SourceCubeEvidence'; export {default as HistoryReplayWorkspace} from './HistoryReplayWorkspace';`,
  resolveDir:fileURLToPath(new URL('../src/',import.meta.url)),loader:'ts'},bundle:true,write:false,
  format:'esm',platform:'node',target:'es2022',jsx:'automatic',loader:{'.css':'empty'},
  plugins:[{name:'react',setup(b){b.onResolve({filter:/^(react(?:\/.*)?|react-dom(?:\/.*)?|lucide-react)$/},
    args=>({path:import.meta.resolve(args.path),external:true}));}}]});
const {historyPageQuery,HistoryPager,reportSummaries,OrbitMap,historySuggestions,SourceCubeEvidence,HistoryReplayWorkspace}=
  await import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].text).toString('base64'));
const scope={as_of:'2020-12-31',known_at:'2026-10-30T00:00:00Z',scope_id:'capture'};
const page={snapshot_id:'a'.repeat(32),section:'facts',offset:50,limit:50,returned:50,total:5009,next_offset:100,previous_offset:0};

test('initial page request carries both time bounds; later pages use the fixed capture',()=>{
  const first=historyPageQuery(scope,false,{kind:'measurement',limit:50},0);
  assert.equal(first.get('known_at'),scope.known_at);assert.equal(first.get('as_of'),scope.as_of);
  const next=historyPageQuery(scope,false,{kind:'measurement',limit:50},50,page.snapshot_id);
  assert.equal(next.get('snapshot_id'),page.snapshot_id);assert.equal(next.get('known_at'),null);
  assert.equal(next.get('offset'),'50');assert.equal(next.get('kind'),'measurement');
});

test('all-date browsing does not silently retain occurrence cutoff',()=>{
  assert.equal(historyPageQuery(scope,true,{},0).get('as_of'),null);
  assert.equal(historyPageQuery(scope,true,{},0).get('known_at'),scope.known_at);
});

test('filters are encoded as data and hook-only controls never reach the endpoint',()=>{
  const query=historyPageQuery(scope,false,{label:'A & B / 한글',enabled:true,unpaged:false,source_id:'one'},0);
  assert.equal(query.get('label'),'A & B / 한글');assert.equal(query.get('enabled'),null);assert.equal(query.get('unpaged'),null);
});

test('pager names partial range and keeps both directions available',()=>{
  const html=renderToStaticMarkup(createElement(HistoryPager,{view:{page},onPage:()=>{}}));
  assert.match(html,/51–100 of 5009 records/);assert.match(html,/Previous records/);assert.match(html,/Next records/);
  assert.doesNotMatch(html,/disabled/);
});

test('last page and single-page histories do not offer impossible navigation',()=>{
  const html=renderToStaticMarkup(createElement(HistoryPager,{view:{page:{...page,offset:5000,returned:9,next_offset:null}},onPage:()=>{}}));
  assert.match(html,/5001–5009 of 5009 records/);assert.match(html,/disabled=""[^>]*>Next records/);
  assert.equal(renderToStaticMarkup(createElement(HistoryPager,{view:{page:{...page,total:9}},onPage:()=>{}})),'');
});

test('source metadata drives orbit without fabricating facts or dates',()=>{
  const sources=Array.from({length:12},(_,i)=>({id:`s${i}`,title:`Report ${i}`,fact_count:100,
    latest_date:'2024-01-01',first_date:'2023-01-01',has_undated:true,display_label:'Health records'}));
  const reports=reportSummaries({sources,facts:[],undated_facts:[],page:{...page,section:'sources'}});
  assert.equal(reports.length,12);assert.equal(reports[0].facts.length,0);assert.equal(reports[0].count,100);
  const html=renderToStaticMarkup(createElement(OrbitMap,{reports,selectedId:'s0',onSelect:()=>{}}));
  assert.equal((html.match(/role="button"/g)||[]).length,12);
  assert.match(html,/100 recorded items/);assert.match(html,/includes partial or unknown dates/);
});

test('Ask suggestions use global captured kinds rather than just the displayed page',()=>{
  const suggestions=historySuggestions({facts:[],undated_facts:[],conflicts:[],counts:{conflicts:1},page,
    facets:{kinds:['encounter','prescription','measurement']}});
  assert.ok(suggestions.some(([,q])=>q==='Show my visits and prescriptions'));
  assert.ok(suggestions.some(([,q])=>q==='Which records disagree?'));assert.ok(suggestions.length<=3);
});

const source={id:'source',title:'Long authored report',type:'csv',date:'2020-01-01',available_at:scope.known_at};
const facts=Array.from({length:200},(_,i)=>({id:`f${i}`,source_id:'source',kind:'measurement',label:'Pulse',value:String(i),unit:'bpm',
  date:'2020-01-01',occurred_on:'2020-01-01',available_at:scope.known_at,source_quote:`Original ${i}`}));
const full={scope,facts,undated_facts:[],sources:[source],conflicts:[],counts:{facts:200,sources:1,conflicts:0}};

test('large source inspector renders only one window but selects the requested off-first-page evidence',()=>{
  const html=renderToStaticMarkup(createElement(SourceCubeEvidence,{source,facts,view:full,initialFactId:'f125'}));
  assert.equal((html.match(/class="source-evidence-fact /g)||[]).length,50);
  assert.match(html,/Original 125/);assert.match(html,/101–150 of 200/);
});

test('replay bounds large change lists without changing the complete comparison counts',()=>{
  const before={...full,facts:[],sources:[],counts:{facts:0,sources:0,conflicts:0}};
  const pair={before,after:full,added:facts,updated:[],removed_from_scope:[],added_counts:{total:200,dated:200,undated:0},
    unchanged_count:0,new_conflicts:[],captured_at:scope.known_at};
  const html=renderToStaticMarkup(createElement(HistoryReplayWorkspace,{pair,scope,onReset:()=>{}}));
  // The later snapshot and arrivals each have an independent 50-row window.
  assert.equal((html.match(/class="history-replay-record"/g)||[]).length,100);
  assert.match(html,/1–50 of 200/);assert.match(html.replace(/<!--.*?-->/g,''),/200 newly available/);
});
