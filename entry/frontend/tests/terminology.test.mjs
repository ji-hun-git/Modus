import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {fileURLToPath} from 'node:url';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
const bundle=await build({stdin:{contents:`export {default as Terms, RetrievalFeedback} from './TerminologyDetails';
  export {default as Answer} from './HistoryAnswerView';`,resolveDir:fileURLToPath(new URL('../src/',import.meta.url)),loader:'ts'},
  bundle:true,write:false,format:'esm',platform:'node',jsx:'automatic',loader:{'.css':'empty'},
  plugins:[{name:'react',setup(b){b.onResolve({filter:/^(react(?:\/.*)?|react-dom(?:\/.*)?|lucide-react)$/},a=>({path:import.meta.resolve(a.path),external:true}));}}]});
const {Terms,RetrievalFeedback,Answer}=await import('data:text/javascript;base64,'+Buffer.from(bundle.outputFiles[0].text).toString('base64'));
const term={concept_id:'pulse',medical_name:'Pulse',display_name:'Heart rate (Pulse)',requested_terms:['heart rate'],matched_labels:['Pulse'],
  catalog_version:'record-terms-test',reference:{publisher:'MedlinePlus',title:'Pulse',url:'https://medlineplus.gov/ency/article/003399.htm',checked_on:'2026-10-30'}};
test('terminology has an explicit mapping and a general reference with no referrer',()=>{
  const html=renderToStaticMarkup(createElement(Terms,{mappings:[term]}));
  assert.match(html,/How I matched your words/);assert.match(html,/heart rate/);assert.match(html,/→ Pulse/);
  assert.match(html,/referrerPolicy="no-referrer"/);assert.match(html,/noopener noreferrer/);
  assert.match(html,/Your results come from your source records/);
});
test('unknown or injected reference URLs never become links',()=>{
  for(const url of ['javascript:alert(1)','https://evil.example/','https://medlineplus.gov.evil.example/',
    'https://user:pass@medlineplus.gov/','https://medlineplus.gov/?record=private']){
    const html=renderToStaticMarkup(createElement(Terms,{mappings:[{...term,reference:{...term.reference,url}}]}));
    assert.doesNotMatch(html,/<a /);
  }
});
test('plain words and stored labels are escaped instead of rendered as markup',()=>{
  const html=renderToStaticMarkup(createElement(Terms,{mappings:[{...term,matched_labels:['<img src=x onerror=alert(1)>']}]}));
  assert.doesNotMatch(html,/<img/);assert.match(html,/&lt;img/);
});
test('ambiguity exposes all supplied choices rather than an unexplained empty list',()=>{
  const html=renderToStaticMarkup(createElement(RetrievalFeedback,{retrieval:{status:'clarify',mappings:[],
    clarification:{question:'Which recorded test?',choices:[{label:'HbA1c',message:'Find HbA1c'},{label:'Glucose',message:'Find Glucose'}]}},onChoose:()=>{}}));
  assert.match(html,/Which recorded test/);assert.match(html,/>HbA1c<\/button>/);assert.match(html,/>Glucose<\/button>/);
});
test('terminology never replaces a personal finding or its source button',()=>{
  const scope={as_of:null,known_at:'2026-10-30T00:00:00Z'};
  const fact={id:'f1',source_id:'s1',label:'Pulse',value:'72',kind:'measurement'};
  const answer={mode:'offline',scope,claims:[{id:'c1',text:'Recorded Pulse: 72 bpm.',evidence_ids:['f1','s1']}],trace:[],terminology:[term],
    history_evidence:{scope,facts:[fact],undated_facts:[],sources:[{id:'s1',title:'Original.csv'}],conflicts:[]}};
  const html=renderToStaticMarkup(createElement(Answer,{answer,pending:false,onClarify:()=>{}}));
  assert.match(html,/Recorded Pulse: 72 bpm/);assert.match(html,/Open evidence for finding 1/);assert.match(html,/Offline · no model called/);
  assert.match(html,/How I matched your words/);
});
test('no mappings adds no terminology panel',()=>{
  assert.equal(renderToStaticMarkup(createElement(Terms,{mappings:[]})),'');
});

test('catalog-only mappings cannot crash an otherwise supported Ask answer or invent requested terms',()=>{
  const {requested_terms,...catalogTerm}=term;
  const scope={as_of:null,known_at:'2026-11-03T00:00:00Z'};
  const answer={mode:'offline',scope,claims:[{id:'c1',text:'Reviewed record: Pulse 72 bpm.',evidence_ids:['f1']}],trace:[],terminology:[catalogTerm],
    history_evidence:{scope,facts:[{id:'f1',source_id:'s1',label:'Pulse',value:'72',kind:'measurement'}],undated_facts:[],sources:[{id:'s1',title:'Original.csv'}],conflicts:[]}};
  const html=renderToStaticMarkup(createElement(Answer,{answer,pending:false,onClarify:()=>{}}));
  assert.match(html,/Reviewed record: Pulse 72 bpm/);assert.match(html,/Open evidence for finding 1/);
  assert.match(html,/<summary>Medical terminology<\/summary>/);assert.match(html,/Recorded as Pulse/);
  assert.doesNotMatch(html,/How I matched your words|undefined/);
});
