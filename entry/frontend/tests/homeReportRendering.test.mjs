import test from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { readFile } from 'node:fs/promises';
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { build } from "esbuild";

// Compile the real components in memory. React remains external so renderer and
// components share one hooks runtime; static markup never fetches source URLs.
const result = await build({
  stdin: {
    contents: [
      'export { default as HomeReportComparison } from "./HomeReportComparison";',
      'export { default as HomeHistoryTrail } from "./HomeHistoryTrail";',
      'export { default as HomeSourceEvidence } from "./HomeSourceEvidence";',
      'export { default as SourceCubeEvidence } from "./SourceCubeEvidence";',
      'export { default as HomeIntegrityTools } from "./HomeIntegrityTools";',
      'export { default as OrbitMap } from "./OrbitMap";',
      'export { default as HomeReportReadings, friendlyRecordName, readingChoices, groupReportFacts } from "./HomeReportReadings";',
      'export { default as HomeReportEvidence } from "./HomeReportEvidence";',
      'export { default as MedicalTestReference } from "./MedicalTestReference";',
      'export { default as LabContext, LabContextReview } from "./LabContext";',
      'export { default as CheckupComparison } from "./CheckupComparison";',
      'export { default as ReportComparisonRows } from "./ReportComparisonRows";',
      'export { matchesReportSummary } from "./reportComparisonTypes";',
      'export { reportBriefMatches } from "./reportBriefTypes";',
      'export { default as ReportBriefReview, ReportBriefContents } from "./ReportBriefReview";',
      'export { default as HomeAskBar } from "./HomeAskBar";',
      'export { default as HealthRecordOverview } from "./HealthRecordOverview";',
      'export { historyFields } from "./historyFields";',
      'export { HistoryTrends } from "./MeasurementsWorkspace";',
      'export { default as GenericFactReview } from "./GenericFactReview";',
      'export { default as ReportCoverageSummary } from "./ReportCoverageSummary";',
      'export { default as ExtractionReviewSummary } from "./ExtractionReviewSummary";',
      'export { default as ReportCompletenessReview } from "./ReportCompletenessReview";',
      'export { default as HistoryAnswerView } from "./HistoryAnswerView";',
      'export { default as HistoryQuestionPanel, historySuggestions, continuationLabel } from "./HistoryQuestionPanel";',
    ].join("\n"),
    resolveDir: fileURLToPath(new URL("../src/", import.meta.url)),
    sourcefile: "home-rendering-test.ts",
    loader: "ts",
  },
  bundle: true,
  write: false,
  format: "esm",
  platform: "node",
  target: "es2022",
  jsx: "automatic",
  loader: { ".css": "empty" },
  plugins: [
    {
      name: "shared-react-runtime",
      setup(builder) {
        builder.onResolve(
          { filter: /^(react(?:\/.*)?|react-dom(?:\/.*)?|lucide-react)$/ },
          (args) => ({ path: import.meta.resolve(args.path), external: true }),
        );
      },
    },
  ],
});
const { ReportCompletenessReview, HomeReportEvidence, ReportBriefReview, ReportBriefContents, reportBriefMatches, ReportComparisonRows, matchesReportSummary, SourceCubeEvidence, HealthRecordOverview, HomeReportComparison, HomeHistoryTrail, HomeSourceEvidence, HomeIntegrityTools, OrbitMap, HomeReportReadings, friendlyRecordName, readingChoices, groupReportFacts, HomeAskBar, LabContext, LabContextReview, CheckupComparison, MedicalTestReference, historyFields, HistoryTrends, GenericFactReview, ReportCoverageSummary, ExtractionReviewSummary, HistoryAnswerView, HistoryQuestionPanel, historySuggestions, continuationLabel } =
  await import(
    "data:text/javascript;base64," +
      Buffer.from(result.outputFiles[0].text).toString("base64")
  );

const row = (id, date, extra = {}) => ({
  id,
  source_id: `source-${id}`,
  kind: "measurement",
  label: "HbA1c",
  value: "5.7",
  unit: "%",
  date,
  occurred_on: date,
  facility: null,
  available_at: "2026-10-29T00:00:00Z",
  source_quote: "HbA1c 5.7 %",
  page: 1,
  ...extra,
});

test('flagged rows expose review actions and retain original proposals after edits', () => {
  const candidate = {id:'inventory-1-1',label:'Ferritin',value:'29.40',unit:'ng/mL',page:1,
    source_quote:'Ferritin 29.40 ng/mL',bbox:null,local_support:'matched_text'};
  const check = {status:'completed',omissions:[candidate],pages:[]};
  const active = render(ReportCompletenessReview,{check,onReviewRow:noop,rowStates:{}});
  assert.match(active,/Review Ferritin/);
  const saved = render(ReportCompletenessReview,{check,onReviewRow:noop,rowStates:{'inventory-1-1':'saved'}});
  assert.match(saved,/Saved after your review/);
  assert.doesNotMatch(saved,/Review Ferritin<\/button>/);
  const fact = {...candidate,kind:'measurement',occurred_on:null,facility:null,keep:true,value:'30.00'};
  const html = render(GenericFactReview,{draft:{id:'d',facts:[],source:{},extraction_review:{facts:[],completeness_check:check}},
    rows:[fact],locked:false,busy:false,uncertain:false,onChange:noop,onSave:noop,onSkip:noop});
  assert.match(html,/Original proposal: Ferritin/);
  assert.match(html,/29.40/);
  assert.match(html,/>30.00<\/textarea>/);
  assert.match(html,/A blank date stays unknown/);
  assert.match(html,/Save 1 reviewed field/);
});

test('NVIDIA garak browser-script payloads remain escaped text in omission review', async () => {
  const fixture = JSON.parse(await readFile(new URL('../../../backend/tests/fixtures/garak/markdown_js.json',import.meta.url),'utf8'));
  for (const payload of fixture.payloads) {
    const check = {status:'completed', pages:[], omissions:[{id:'inventory-1-1',label:payload,
      value:payload,unit:null,page:1,source_quote:payload,bbox:null,local_support:'unavailable'}]};
    const html=render(ReportCompletenessReview,{check,onReviewRow:noop});
    assert.doesNotMatch(html,/<script\b|<iframe\b|<img\b|href="(?:javascript:|data:)| onerror=/i);
    assert.match(html,/No independent text check/);
  }
});
const viewOf = (facts) => ({
  facts,
  undated_facts: [],
  conflicts: [],
  scope: {
    as_of: "2026-10-20",
    known_at: "2026-10-29T00:00:00Z",
    captured_at: "2026-10-29T00:00:00Z",
    scope_id: "test-scope",
  },
  sources: [...new Set(facts.map((fact) => fact.source_id))].map((id) => ({
    id,
    title: "Uploaded report",
    type: "text",
    original_available: false,
    date: "2026-10-20",
    available_at: "2026-10-29T00:00:00Z",
  })),
});
const noop = () => {};

test('Home exposes both clocks and the scrubber while advanced history tools stay opt-in', () => {
  const html=renderToStaticMarkup(createElement(HealthRecordOverview,{
    view:viewOf([row('a','2026-10-20')]), hasDraft:false, onImport:noop, onNavigate:noop,
    dates:['2026-10-20'], currentDay:'2026-11-02', knowledge:'now', pendingCount:0, onDate:noop,
  }));
  assert.match(html,/Readings in this report/);
  assert.match(html,/Your source files in orbit/);
  assert.match(html,/Ask about your medical history/);
  assert.doesNotMatch(html,/home-timeline-disclosure/);
  assert.match(html,/Files available through<\/span><strong><time dateTime="2026-10-29T00:00:00Z"/);
  const tools=html.indexOf('<details class="orbit-history-options"');
  assert.ok(html.indexOf('aria-label="Scrub recorded history"')<tools);
  assert.ok(html.indexOf('aria-label="Home file availability"')>tools); // Precise inputs stay available without crowding the orbit.
  assert.ok(tools<html.indexOf('class="orbit-workspace"'));
  assert.doesNotMatch(html,/This reading across your history|Compare with previous checkup|Close history/);
});

test('Home names use exact catalog aliases and preserve qualified or unfamiliar labels',()=>{
  assert.equal(friendlyRecordName('HbA1c'),'Average blood sugar (HbA1c)');
  assert.equal(friendlyRecordName('Pulse'),'Heart rate (Pulse)');
  assert.equal(friendlyRecordName('eGFR'),'Kidney filtering estimate (eGFR)');
  assert.equal(friendlyRecordName('HbA1c pending'),'HbA1c pending');
  assert.equal(friendlyRecordName('Custom assay'),'Custom assay');
});

test('Home puts the file orbit before its report with direct original evidence and one Ask bar',()=>{
  const fact=row('a','2026-10-20');
  const html=render(HealthRecordOverview,{view:viewOf([fact]),hasDraft:false,onImport:noop,onNavigate:noop,
    dates:['2026-10-20'],currentDay:'2026-11-03',knowledge:'latest',pendingCount:0,onDate:noop});
  assert.ok(html.indexOf('class="home-orbit-stage"')<html.indexOf('id="home-selected-report"'));
  assert.match(html,/orbit-map-prominent/);
  assert.match(html,/aria-controls="home-selected-report"/);
  assert.match(html,/Open evidence/);
  assert.match(html,/<blockquote>HbA1c 5.7 %<\/blockquote>/);
  assert.equal((html.match(/name="history-question"/g)||[]).length,1);
});

test('Home actions expose scoped differences and summary while one header action owns the review queue',()=>{
  const view=viewOf([row('a','2026-10-20'),row('b','2026-10-20',{value:'5.9'})]);
  view.conflicts=[{id:'difference-a',fact_ids:['a','b'],reason:'different_numeric_values'}];
  const html=render(HealthRecordOverview,{view,hasDraft:true,pendingCount:2,onImport:noop,onNavigate:noop,
    dates:['2026-10-20'],currentDay:'2026-11-03',knowledge:'latest',onDate:noop});
  assert.equal((html.match(/aria-label="Continue review, 2 files"/g)||[]).length,1);
  assert.match(html,/aria-label="Review 1 recorded difference"/);
  assert.equal((html.match(/Prepare a summary/g)||[]).length,1);
  assert.doesNotMatch(html,/overview-conflict-banner|Prepare a brief|Unsaved reviews stay/);
  const disclosure=html.match(/<details class="orbit-history-options">([\s\S]*?)<\/details>/)?.[1] || '';
  assert.doesNotMatch(disclosure,/Continue review|Prepare a summary/);
  assert.match(disclosure,/Compare past views/);
  assert.ok(html.indexOf('Actions for your history')<html.indexOf('class="orbit-workspace"'));
});

test('Empty Home keeps summary access honest without fabricated conflict or review counts',()=>{
  const html=render(HealthRecordOverview,{view:viewOf([]),hasDraft:false,pendingCount:0,onImport:noop,onNavigate:noop,
    dates:[],currentDay:'2026-11-03',knowledge:'latest',onDate:noop});
  assert.match(html,/Add records/);
  assert.match(html,/Prepare a summary/);
  assert.doesNotMatch(html,/Review differences|Continue review|home-review-count|No conflicts|All clear/);
});

test('A pending scrub keeps its live date control usable and retained evidence inert',()=>{
  const html=render(HealthRecordOverview,{view:viewOf([row('a','2026-10-20')]),hasDraft:false,pendingCount:0,
    onImport:noop,onNavigate:noop,dates:['2010-04-12','2026-10-20'],currentDay:'2026-11-03',
    knowledge:'latest',onDate:noop,requestedDate:'2013-12-31',updating:true,onCurrent:noop});
  assert.match(html,/aria-label="Selected history date">Through 31 Dec 2013/);
  assert.match(html,/Updating records/);
  assert.match(html,/home-evidence-surface is-time-updating" aria-busy="true" inert=""/);
  assert.ok(html.indexOf('aria-label="Scrub recorded history"')<html.indexOf('inert=""'));
  assert.match(html,/>Today<\/button>/);
});

test('Home evidence resolves the current source and preserves corrections without trusting a stale selection',()=>{
  const original=row('a','2026-10-20');
  const corrected={...original,value:'5.9',previous_revision_id:'revision-1',reviewed_fields:['value']};
  const html=render(HomeReportEvidence,{fact:{...corrected,source_quote:'Stale fabricated quote'},view:viewOf([corrected]),onOpen:noop});
  assert.match(html,/<blockquote>HbA1c 5.7 %<\/blockquote>/);
  assert.match(html,/Corrected after saving/);
  assert.doesNotMatch(html,/Stale fabricated quote/);
  assert.equal(render(HomeReportEvidence,{fact:corrected,view:viewOf([]),onOpen:noop}),'');
  assert.equal(render(HomeReportEvidence,{fact:{...corrected,source_id:'other'},view:viewOf([corrected]),onOpen:noop}),'');
});

test('Home evidence hides original passages under either date-withholding flag and escapes document text',()=>{
  for(const flag of ['value_withheld','source_quote_withheld']) {
    const fact=row('a','2026-10-20',{source_quote:'PRIVATE EXCERPT',[flag]:true});
    const html=render(HomeReportEvidence,{fact,view:viewOf([fact]),onOpen:noop});
    assert.doesNotMatch(html,/PRIVATE EXCERPT/);
    assert.match(html,/hidden in this date view/);
  }
  const fact=row('a','2026-10-20',{source_quote:'<script>untrusted</script>'});
  assert.match(render(HomeReportEvidence,{fact,view:viewOf([fact]),onOpen:noop}),/&lt;script&gt;untrusted&lt;\/script&gt;/);
});

test('Prominent orbit retains native file selection, honest pagination and unknown dates',()=>{
  const fact=row('a',null,{occurred_on:'2016'}),view=viewOf([fact]);
  const html=render(OrbitMap,{reports:[{source:view.sources[0],facts:[fact],latestDate:null}],selectedId:fact.source_id,
    onSelect:noop,total:80,prominent:true,onOpenAll:noop});
  assert.match(html,/1 of 80/);
  assert.match(html,/<label class="orbit-file-picker">Open a report<select/);
  assert.match(html,/All files/);
  assert.match(html,/Undated/);
  assert.doesNotMatch(html,/2016-01-01/);
});

test('Home choices are bounded and keep a selected extra field without changing any record',()=>{
  const facts=Array.from({length:12},(_,i)=>row('r'+i,'2025-05-06',{label:'Field '+i}));
  const original=structuredClone(facts);
  const chosen=readingChoices(facts,'r11');
  assert.equal(chosen.length,4);
  assert.ok(chosen.some(f=>f.id==='r11'));
  assert.deepEqual(facts,original);
  const html=render(HomeReportReadings,{facts,selected:facts[11],onSelect:noop});
  assert.equal((html.match(/class="report-reading-choice"/g)||[]).length,4);
  assert.equal((html.match(/aria-pressed="true"/g)||[]).length,1);
});

test('Home reading tiles never reveal withheld values or units and escape record text',()=>{
  const facts=[row('a','2025-01-01',{value:'PRIVATE-VALUE',unit:'PRIVATE-UNIT',value_withheld:true}),row('b','2025-01-02',{label:'<script>bad()</script>',value:'<b>no</b>'})];
  const html=render(HomeReportReadings,{facts,selected:facts[0],onSelect:noop});
  assert.doesNotMatch(html,/PRIVATE-VALUE|PRIVATE-UNIT|<script>|<b>/);
  assert.match(html,/Hidden by date filter/);
  assert.match(html,/&lt;script&gt;/);
});

test('Home exposes every open-label checkup reading on request without changing saved names',()=>{
  const labels=['Glucose','Hemoglobin','White blood cells','Platelets','Ferritin','TSH','Vitamin D','ALT'];
  const facts=labels.map((label,i)=>row(`lab${i}`,'2026-10-22',{label}));
  const before=structuredClone(facts);
  const collapsed=render(HomeReportReadings,{facts,onSelect:noop,onToggle:noop});
  assert.match(collapsed,/Show all 8 entries/);
  assert.match(collapsed,/aria-expanded="false"/);
  assert.equal((collapsed.match(/class="report-reading-choice"/g)||[]).length,4);
  const expanded=render(HomeReportReadings,{facts,onSelect:noop,onToggle:noop,expanded:true});
  assert.equal((expanded.match(/class="report-reading-choice"/g)||[]).length,8);
  for(const label of labels) assert.ok(expanded.includes(friendlyRecordName(label)));
  assert.match(expanded,/aria-expanded="true"/);
  assert.match(expanded,/Show fewer entries/);
  assert.deepEqual(facts,before);
});

test('Expanded report readings remain bounded and distinguish a page from the whole report',()=>{
  const facts=Array.from({length:120},(_,i)=>row(`f${i}`,'2026-10-22',{label:`Uncatalogued test ${i}`}));
  assert.equal(readingChoices(facts,'f119',true).length,50);
  assert.ok(readingChoices(facts,'f119',true).some(f=>f.id==='f119'));
  const html=render(HomeReportReadings,{facts:facts.slice(0,50),onSelect:noop,onToggle:noop,paged:true});
  assert.match(html,/Show 50 entries on this page/);
  assert.doesNotMatch(html,/Show all/);
});

test('Home asks for missing units only on measurements, retaining printed units on other record kinds',()=>{
  const nonNumeric=row('text','2025-01-02',{kind:'recorded_text',label:'Visit note',value:'Follow-up recorded',unit:null});
  assert.doesNotMatch(render(HomeReportReadings,{facts:[nonNumeric],onSelect:noop}),/Unit not recorded/);
  assert.match(render(HomeReportReadings,{facts:[row('lab','2025-01-02',{unit:null})],onSelect:noop}),/Unit not recorded/);
  assert.match(render(HomeReportReadings,{facts:[{...nonNumeric,unit:'as printed'}],onSelect:noop}),/as printed/);
});

test('Source evidence shows original filename and distinct recorded and availability dates',()=>{
  const fact=row('dates','2016-06-02',{available_at:'2026-11-02T03:04:00Z'});
  const view=viewOf([fact]);
  view.sources[0].title='Original June report.csv';
  const html=render(SourceCubeEvidence,{source:view.sources[0],facts:[fact],view,initialFactId:fact.id});
  assert.match(html,/Original June report.csv/);
  assert.match(html,/<dt>Recorded<\/dt><dd>2 Jun 2016/);
  assert.match(html,/<dt>Available in Modus<\/dt><dd>2 Nov 2026, 03:04 UTC/);
});

test('Home has one labelled Ask input and a compact orbit with a native file selector',()=>{
  const view=viewOf([row('a','2025-01-01')]);
  const html=render(HomeAskBar,{view});
  assert.equal((html.match(/<input /g)||[]).length,1);
  assert.match(html,/name="history-question"/);
  assert.match(html,/aria-label="Ask your history"/);
  const orbit=render(OrbitMap,{reports:[{source:view.sources[0],facts:view.facts,latestDate:'2025-01-01'}],selectedId:view.sources[0].id,onSelect:noop,compact:true});
  assert.match(orbit,/<label class="orbit-file-picker">Open a report<select/);
  assert.match(orbit,/Open source file:/);
});

test('Home question is prefilled for the explicit submit action, not fabricated as a prior answer',()=>{
  const html=render(HistoryQuestionPanel,{view:viewOf([]),initialQuestion:'When was my last visit?'});
  assert.match(html,/When was my last visit\?/);
  assert.doesNotMatch(html,/History answer ready/);
});
const render = (component, props) =>
  renderToStaticMarkup(createElement(component, props));
const accessibleNames = (html) =>
  [...html.matchAll(/aria-label="([^"]*)"/g)].map((match) => match[1]);

test("whole-report coverage distinguishes processing, failed pages and unproven completeness", () => {
  const coverage={version:'whole-report-v1',status:'failed',page_count:3,processed_pages:1,request_count:2,
    pages:[{page:1,status:'processed',field_count:1,verification_status:'completed',readability:'text_available'},
      {page:2,status:'failed',field_count:0,verification_status:'not_run',readability:'image_only'},
      {page:3,status:'not_run',field_count:0,verification_status:'not_run',readability:'unreadable'}]};
  const html=render(ReportCoverageSummary,{coverage});
  assert.match(html,/1 of 3 pages processed/);
  assert.match(html,/Reading failed/); assert.match(html,/Not read/);
  assert.match(html,/does not confirm that every detail was found/);
  assert.match(html,/Image supplied; text could not be checked locally/);
  assert.match(html,/<details[^>]*open/);
  assert.doesNotMatch(html,/100%|all facts|clinically verified|complete history/i);
});

const completeness = (overrides={}) => ({version:'report-row-inventory-v1',status:'completed',
  completeness:'not_established',review_required:true,inventory_rows:2,matched_rows:1,
  pages:[{page:1,status:'checked',readability:'readable',truncated:false,independent_text_available:true}],
  omissions:[{id:'inventory-1-2',page:1,label:'Ferritin',value:'29.40',unit:'ng/mL',
    source_quote:'Ferritin 29.40 ng/mL 2024-02-03',bbox:null,local_support:'matched_text',
    matched_field_id:null,reason:'not_in_proposal'}],...overrides});

test('omitted row review remains visible even when extraction found no editable fields', () => {
  const html=render(ExtractionReviewSummary,{review:{document_type:'lab_report',verification_status:'not_run',
    facts:[],completeness_check:completeness()},originalHref:'/api/drafts/authored/original'});
  assert.match(html,/No fields found/); assert.match(html,/1 possible missing row/);
  assert.match(html,/Ferritin 29.40 ng\/mL 2024-02-03/);
  assert.match(html,/Page 1/); assert.match(html,/not included when you save/);
  assert.match(html,/href="\/api\/drafts\/authored\/original"/);
  assert.doesNotMatch(html,/<input|<textarea/); // A flag cannot become a selectable field.
});

test('failed or limited inventory is never presented as zero omissions or complete reading', () => {
  for(const status of ['unavailable','partial']) {
    const html=render(ExtractionReviewSummary,{review:{document_type:'lab_report',verification_status:'completed',
      facts:[],completeness_check:completeness({status,omissions:[],pages:[{page:2,status:'unavailable',readability:null,
        truncated:false,independent_text_available:false}]})}});
    assert.match(html,/Check page 2 directly/);
    assert.doesNotMatch(html,/No additional rows flagged|100%|all rows found/);
  }
});

test('omission list is bounded and untrusted labels or excerpts cannot inject markup', () => {
  const row=completeness().omissions[0];
  const omissions=Array.from({length:20},(_,i)=>({...row,id:`inventory-1-${i+1}`,
    label:`<script>bad${i}</script>`,source_quote:'<img src=x onerror=alert(1)>'}));
  const html=render(ExtractionReviewSummary,{review:{document_type:'other',verification_status:'completed',facts:[],
    completeness_check:completeness({omissions,inventory_rows:20,matched_rows:0})}});
  assert.match(html,/20 possible missing rows/); assert.match(html,/1–6 of 20/);
  assert.match(html,/Next rows/); assert.match(html,/Previous rows/);
  assert.doesNotMatch(html,/<script|<img|bad6/); assert.match(html,/&lt;script&gt;bad5/);
});

test('a zero-flag result still says the check can miss rows', () => {
  const html=render(ExtractionReviewSummary,{review:{document_type:'lab_report',verification_status:'completed',
    facts:[],completeness_check:completeness({omissions:[]})}});
  assert.match(html,/No additional rows flagged/); assert.match(html,/This check can miss rows/);
  assert.doesNotMatch(html,/100%|all rows found/);
});

test('saved omission warnings retain evidence without pretending fields are still editable', () => {
  const html=render(ReportCompletenessReview,{check:completeness(),saved:true,
    originalHref:'/api/history/sources/authored/original?known_at=2026-11-03T09%3A00%3A00Z'});
  assert.match(html,/These rows were not included in the saved fields/);
  assert.match(html,/Ferritin 29.40 ng\/mL 2024-02-03/);
  assert.match(html,/Download original to review/);
  assert.doesNotMatch(html,/before saving|editable fields|when you save/);
});

test("flagged fields show their source concern in the actual review, without duplicate expanded summaries", () => {
  const field={...row('flagged','2024-02-03',{label:'Pulse',value:'72.00'}),keep:true};
  const check={...field,commit_supported:true,review_reasons:['The second reading disagrees with this field.']};
  const review={document_type:'lab_report',verification_status:'completed',facts:[check]};
  const html=render(GenericFactReview,{draft:{id:'draft',source:{original_available:true},facts:[field],extraction_review:review},
    rows:[field],locked:false,busy:false,uncertain:false,onChange:noop,onSave:noop,onSkip:noop});
  assert.match(html,/Check Pulse against the original/);
  assert.match(html,/<aside class="generic-fact-source" aria-label="Original excerpt for field 1">/);
  assert.match(html,/<blockquote>HbA1c 5.7 %<\/blockquote>/);
  assert.doesNotMatch(html,/<details class="generic-fact-source"/);
  const summary=render(ExtractionReviewSummary,{review});
  assert.match(summary,/1 needs a closer look/);
  assert.doesNotMatch(summary,/<details[^>]*open/);
});

test("orbit keeps core actions visible and puts secondary history controls in a disclosure", () => {
  const html=render(HomeIntegrityTools,{scope:viewOf([]).scope,dates:['2012-01-01'],currentDay:'2026-10-29',
    knowledge:'latest',pendingCount:0,onDate:noop,onNavigate:noop,onReview:noop,orbit:true});
  assert.doesNotMatch(html,/Ask about your history/); // One Home composer owns this action.
  assert.match(html,/<details class="orbit-history-options"><summary>More history tools/);
  assert.doesNotMatch(html,/Review queue|Continue review|T\+/);
  assert.match(html,/aria-label="Home file availability"/);
});

test("field selectors use all exact labels and kinds without merging units or same-day ties", () => {
  const facts = ['Pulse','Glucose','ALT','Weight','Custom assay','혈압'].map((label, i) => row(`field-${i}`, '2024-02-03', {label}));
  facts.push(row('pulse-tie','2024-02-03',{label:'Pulse',value:'75',unit:'bpm'}));
  facts.push(row('pulse-other-kind','2024-02-03',{label:'Pulse',kind:'recorded_text',value:'As printed'}));
  const view = viewOf(facts), original = structuredClone(view);
  const groups = historyFields(view);
  assert.equal(groups.length, 7);
  const pulse = groups.find((g) => g.kind==='measurement' && g.label==='Pulse');
  assert.equal(pulse.facts.length, 2);
  assert.deepEqual(new Set(pulse.facts.map((f) => f.unit)),new Set(['%','bpm']));
  assert.deepEqual(view, original);
  const html = render(HistoryTrends, {view});
  for (const label of ['Pulse','Glucose','ALT','Weight','Custom assay','혈압']) assert.ok(html.includes(`${label} ·`));
  assert.doesNotMatch(html, /HbA1c|eGFR|LDL/);
});

test("Trends scope cannot revive future/orphan/duplicate facts or withheld values", () => {
  const hidden = row('hidden','2024-02-03',{label:'Pulse',value:null,value_withheld:true,unit:'PRIVATE-UNIT'});
  const future = row('future','2026-10-20',{label:'FUTURE-FIELD',within_date_scope:false});
  const orphan = row('orphan','2024-02-03',{label:'ORPHAN-FIELD'});
  const view = viewOf([hidden,future,orphan]);
  view.sources = view.sources.filter((s) => s.id!==orphan.source_id);
  view.undated_facts = [{...hidden,value:'PRIVATE-VALUE',value_withheld:false}];
  assert.deepEqual(historyFields(view).flatMap((g) => g.facts), [hidden]);
  const html = render(HistoryTrends,{view});
  assert.match(html,/Hidden by date filter/);
  assert.doesNotMatch(html,/PRIVATE-UNIT|PRIVATE-VALUE|FUTURE-FIELD|ORPHAN-FIELD/);
});

test("partial dates and qualified values remain source-linked history instead of fabricated points", () => {
  const facts = [row('partial',null,{label:'ALT',occurred_on:'2012',value:'<5',unit:'U/L'}),
    row('unknown',null,{label:'ALT',occurred_on:null,value:'Not detected',unit:null})];
  const html = render(HistoryTrends,{view:viewOf(facts)});
  assert.match(html,/2012/); assert.match(html,/&lt;5/); assert.match(html,/Not detected/);
  assert.equal((html.match(/class="text-button" aria-label="Inspect ALT/g)||[]).length,2);
  assert.doesNotMatch(html,/class="home-series-point/);
});

test("nonmeasurement history preserves wording and never becomes a numeric graph", () => {
  const html = render(HistoryTrends,{view:viewOf([row('visit','2024-02-03',{
    kind:'encounter',label:'Annual visit',value:'Visit documented as printed',unit:null})])});
  assert.match(html,/Visit documented as printed/);
  assert.match(html,/Inspect Annual visit/);
  assert.doesNotMatch(html,/home-record-series|home-series-point/);
});

test("review headers show every original name, exact value and immutable excerpt", () => {
  const rows = ['Pulse','ALT','Glucose','Weight','Unknown panel'].map((label,i) => ({...row(String(i),'2024-02-03',{label,value:'13.70'}),keep:true}));
  const html = render(GenericFactReview,{draft:{id:'draft',source:{original_available:true},facts:rows},rows,
    locked:false,busy:false,uncertain:false,onChange:noop,onSave:noop,onSkip:noop});
  rows.forEach((row, index) => {
    const name = html.match(new RegExp(`<input[^>]*aria-label="Name ${index + 1}"[^>]*>`))?.[0];
    assert.ok(name?.includes(`value="${row.label}"`));
    assert.ok(name?.includes('required=""'));
  });
  assert.match(html,/13.70/);
  assert.match(html,/Save 5 reviewed fields/);
  assert.doesNotMatch(html,/>Field [0-9]/);
});

test("orbit buttons preserve original file identity, keyboard access and independent same-date files", () => {
  const reports = ['a', 'b'].map((id) => ({source:{id, title:`Original ${id}.png`},
    latestDate:'2026-10-20', facts:[row(id, '2026-10-20')]}));
  reports.push({source:{id:'unknown', title:'Undated note.txt'}, latestDate:null, facts:[row('unknown', null)]});
  const html = render(OrbitMap, {reports, selectedId:'b', onSelect:noop});
  assert.equal((html.match(/role="button"/g) || []).length, 3);
  assert.equal((html.match(/tabindex="0"/g) || []).length, 3);
  assert.equal((html.match(/aria-pressed="true"/g) || []).length, 1);
  for (const title of ['Original a.png', 'Original b.png', 'Undated note.txt']) assert.ok(html.includes(`Open source file: ${title}`));
  assert.match(html, />You<\/text>/);
  assert.match(html, />Undated<\/text>/);
  assert.doesNotMatch(html, /health score|normal range/i);
});

test("empty orbit invites the first record without fabricated satellites", () => {
  const html = render(OrbitMap, {reports:[], onSelect:noop});
  assert.match(html, /0 source files — add the first/);
  assert.doesNotMatch(html, /role="button"/);
});

test("telemetry positions actual dates proportionally and keeps an explicit empty state", () => {
  const props = {scope:{...viewOf([]).scope, as_of:'2024-01-04'}, dates:['2024-01-01','2024-01-02','invalid','2025-01-01'],
    currentDay:'2024-01-04', knowledge:'then', pendingCount:0, onDate:noop, onNavigate:noop, onReview:noop, orbit:true};
  const html = render(HomeIntegrityTools, props);
  assert.match(html, /left:33\.33333333333333[0-9]*%/);
  assert.equal((html.match(/<i /g) || []).length, 3);
  assert.doesNotMatch(html, /NaN|Infinity/);
  const empty = render(HomeIntegrityTools, {...props, scope:{...props.scope,as_of:null}, dates:[]});
  assert.match(empty, /No dated records/);
  assert.match(empty, /All recorded dates/);
  assert.match(empty, /type="range"[^>]*disabled/);
  assert.doesNotMatch(empty, /NaN|Infinity/);
});

test("Home exposes real replay dates, review count, Ask and Brief without More", () => {
  const html = render(HomeIntegrityTools, { scope: viewOf([]).scope, dates: ['2016-05-04', '2024-02-03'],
    currentDay:'2026-10-29', knowledge:'latest', pendingCount:2, onDate:noop, onNavigate:noop, onReview:noop });
  assert.match(html, /aria-label="Scrub recorded history"/);
  assert.match(html, /aria-label="Home file availability"/);
  assert.match(html, /Review queue <span>2<\/span>/);
  assert.match(html, /Prepare a brief \/ export/);
  assert.match(html, /Ask your records/);
  assert.ok(!html.includes('<details'));
});

test("valid original image geometry is drawn; absent or withheld regions stay honest", () => {
  const fact = row('region', '2024-02-03', {bbox:[0.1, 0.2, 0.8, 0.4]});
  const view = viewOf([fact]);
  view.sources[0] = {...view.sources[0], title:'report.png', type:'image/png', original_available:true};
  const html = render(HomeSourceEvidence, {fact, view, onOpen:noop});
  assert.match(html, /aria-label="Recorded source region"/);
  assert.match(html, /<rect x="100" y="200" width="700/);
  for (const change of [{bbox:null}, {source_quote_withheld:true}, {page:2}]) {
    const hidden = render(HomeSourceEvidence, {fact:{...fact, ...change}, view, onOpen:noop});
    assert.ok(!hidden.includes('aria-label="Recorded source region"'));
    assert.match(hidden, /Source region (not located|cannot be previewed)/);
  }
});
const comparison = (facts, view, anchor, evidence) =>
  render(HomeReportComparison, {
    facts,
    view,
    anchor,
    evidence,
    onSelect: noop,
    onOpen: noop,
    onCompare: noop,
  });

test("comparison readings do not disclose withheld units in their accessible names", () => {
  const hidden = row("hidden", "2026-10-20", {
    value: null,
    value_withheld: true,
    unit: "WITHHELD-UNIT",
    source_quote: null,
    source_quote_withheld: true,
  });
  const html = comparison([hidden], viewOf([hidden]), hidden, hidden);
  const names = accessibleNames(html).filter((name) =>
    name.startsWith("Show source:"),
  );
  assert.equal(names.length, 1);
  assert.match(names[0], /value hidden by date filter/);
  assert.doesNotMatch(names.join("\n"), /WITHHELD-UNIT/);
});

test("history buttons keep withheld units out of accessible names while retaining the record", () => {
  const hidden = row("hidden", "2024-02-03", {
    value: null,
    value_withheld: true,
    unit: "WITHHELD-UNIT",
  });
  const current = row("current", "2026-10-20");
  const html = render(HomeHistoryTrail, {
    anchor: current,
    view: viewOf([hidden, current]),
    selectedId: hidden.id,
    onSelect: noop,
  });
  const names = accessibleNames(html).filter((name) =>
    name.startsWith("Show evidence:"),
  );
  assert.equal(names.length, 2);
  assert.ok(
    names.some(
      (name) => name.includes("value hidden") && name.includes("3 Feb 2024"),
    ),
  );
  assert.doesNotMatch(names.join("\n"), /WITHHELD-UNIT/);
});

test("a shared previous record is selected only within the active comparison row", () => {
  const previous = row("previous", "2024-02-03");
  const first = row("first", "2026-10-20", { value: "5.7" });
  const second = row("second", "2026-10-20", { value: "5.8" });
  const html = comparison(
    [first, second],
    viewOf([previous, first, second]),
    second,
    previous,
  );
  const readings = [
    ...html.matchAll(/<button\b[^>]*class="home-reading[^>]*>/g),
  ].map((match) => match[0]);
  assert.equal(readings.length, 4);
  assert.equal(
    readings.filter((tag) => /aria-pressed="true"/.test(tag)).length,
    1,
  );
  assert.deepEqual(
    readings.map((tag) => /aria-pressed="true"/.test(tag)),
    [false, false, true, false],
  );
});

test("source context excludes facts outside the selected date scope", () => {
  const visible = row("visible", "2024-02-03");
  const outside = row("outside", "2026-10-20", {
    source_id: visible.source_id,
    label: "LDL",
    within_date_scope: false,
  });
  const html = render(HomeSourceEvidence, {
    fact: visible,
    view: viewOf([visible, outside]),
    onOpen: noop,
  });
  const context = html.match(
    /<span class="home-proof-context">([\s\S]*?)<\/span>/,
  )?.[1];
  assert.ok(context);
  assert.match(context, /^HbA1c · 3 Feb 2024$/);
  assert.doesNotMatch(context, /Measurements|LDL/);
});

test("original image previews keep both temporal bounds and stay hidden with withheld excerpts", () => {
  const fact = row("image", "2024-02-03");
  const view = viewOf([fact]);
  view.sources[0] = {
    ...view.sources[0],
    title: "report.png",
    type: "image/png",
    original_available: true,
  };
  const html = render(HomeSourceEvidence, { fact, view, onOpen: noop });
  const image = html.match(/<img\b[^>]*>/)?.[0];
  assert.ok(image);
  assert.match(image, /known_at=2026-10-29T00%3A00%3A00Z/);
  assert.match(image, /as_of=2026-10-20/);
  const withheld = { ...fact, source_quote: null, source_quote_withheld: true };
  const hiddenHtml = render(HomeSourceEvidence, {
    fact: withheld,
    view: { ...view, facts: [withheld] },
    onOpen: noop,
  });
  assert.doesNotMatch(hiddenHtml, /<img\b/);
});


test("Ask suggestions use only visible history and remain capped at three", () => {
  const view = viewOf([
    row("bp", "2016-06-02", { label: "Blood pressure", value: "100/65", unit: "mmHg" }),
    row("visit", "2024-02-03", { kind: "encounter", label: "Annual visit" }),
    row("rx", "2024-02-03", { kind: "prescription", label: "Prescription entry" }),
    row("vaccine", "2024-02-03", { kind: "vaccination", label: "Vaccination entry" }),
  ]);
  const suggestions = historySuggestions(view);
  assert.equal(suggestions.length, 3);
  assert.equal(suggestions[0][1], "When was Blood pressure last recorded?");
  assert.equal(suggestions[1][1], "Show my visits and prescriptions");
  const hidden = { ...view, facts: view.facts.map(fact => ({ ...fact, value_withheld: true })) };
  assert.deepEqual(historySuggestions(hidden), []);
  const html = render(HistoryQuestionPanel, { view });
  assert.equal((html.match(/aria-label="Use question:/g) || []).length, 3);
  assert.ok(!html.includes("Find something in your history"));
});

test("Ask keeps every exact claim and time bound with source controls only for actual evidence", () => {
  const view = viewOf([row("bp", "2016-06-02", { label: "Blood pressure", value: "100/65", unit: "mmHg" })]);
  const claims = [
    { id: "dated", text: "The latest fully dated match is 2016-06-02: 100/65 mmHg.", evidence_ids: ["bp"] },
    { id: "limit", text: "Unknown-date matches prevent establishing the latest across all records.", evidence_ids: [] },
  ];
  const html = render(HistoryAnswerView, { answer: { mode: "offline", scope: view.scope, claims, trace: [], history_evidence: view }, pending: false, onClarify: noop });
  for (const claim of claims) assert.ok(html.includes(claim.text));
  assert.match(html, /Offline · no model called/);
  assert.match(html, /Files available through/);
  assert.equal((html.match(/class="history-citation"/g) || []).length, 1);
  assert.match(html, /aria-label="Open evidence for finding 1"/);
  assert.ok(!html.includes("View supporting records"));
});

test('Ask distinguishes typed no-match, insufficient evidence, clarification and unavailable search',()=>{
  const view=viewOf([]);
  for(const [status,heading] of Object.entries({answered:'From your history',no_match:'No matching record found',
    insufficient_evidence:'Not enough recorded evidence',clarification:'One detail before I look',
    unsupported:'This question is outside record search',not_understood:'Help me find the right record',planner_unavailable:'Record search is unavailable'})) {
    const html=render(HistoryAnswerView,{answer:{mode:'offline',scope:view.scope,claims:[],trace:[],history_evidence:view,
      answer:'The exact recorded response.',query_result:{status}},pending:false,onClarify:noop});
    assert.ok(html.includes(`<h3>${heading}</h3>`),status);
    assert.match(html,/The exact recorded response/);assert.doesNotMatch(html,/history-citation/);
  }
});

test('the single followup action describes history and source requests without promising an earlier record',()=>{
  assert.equal(continuationLabel('What about the one before that?'),'Show the earlier record');
  for(const question of ['Show matching history','Show its history','Where did this value come from?','Name a result to inspect its source.'])
    assert.equal(continuationLabel(question),question);
});

test("Ask clarification keeps both explicit choices and never labels a guard as Muse", () => {
  const view = viewOf([]);
  const html = render(HistoryAnswerView, { answer: { mode: "request_guard", scope: view.scope, claims: [], trace: [], history_evidence: view,
    answer: "Top or bottom number?", clarification: { kind: "blood_pressure_component", choices: [{ label: "Top number (systolic)", message: "top" }, { label: "Bottom number (diastolic)", message: "bottom" }] } },
    pending: false, onClarify: noop });
  assert.ok(html.includes("Top or bottom number?"));
  assert.ok(html.includes("Top number (systolic)"));
  assert.ok(html.includes("Bottom number (diastolic)"));
  assert.match(html, /No model called/);
  assert.ok(!html.includes("Muse · record findings"));
});


test("medical references distinguish saved names from terminology and personal evidence", () => {
  const html = render(MedicalTestReference, {fact:row('a1c','2024-02-03',{label:'A1c'})});
  assert.match(html,/In your report<\/dt><dd>A1c/);
  assert.match(html,/Medical name<\/dt><dd>Hemoglobin A1c \(HbA1c\)/);
  assert.match(html,/https:\/\/www.niddk.nih.gov\/health-information\/diagnostic-tests\/a1c-test/);
  assert.match(html,/referrerPolicy="no-referrer"/i);
  assert.match(html,/Your result and its original evidence are shown separately/);
  assert.doesNotMatch(html,/normal range|diagnosis|risk score/i);
});

test("medical references do not classify qualified assays or other record kinds", () => {
  for (const label of ['HbA1c pending','Novel assay','<script>HbA1c</script>']) {
    assert.equal(render(MedicalTestReference,{fact:row('x','2024-02-03',{label})}), '');
  }
  assert.equal(render(MedicalTestReference,{fact:row('x','2024-02-03',{label:'HbA1c',kind:'recorded_text'})}), '');
});


test("checkup groups preserve every record and keep qualified or non-measurement labels separate", () => {
  const facts=[row('a','2024-02-03',{label:'A1c'}),row('k','2024-02-03',{label:'eGFR'}),
    row('c','2024-02-03',{label:'LDL'}),row('q','2024-02-03',{label:'HbA1c pending'}),
    row('visit','2024-02-03',{label:'HbA1c',kind:'encounter'})];
  const original=JSON.stringify(facts);
  const groups=groupReportFacts(facts);
  assert.deepEqual(groups.map(g=>g.name),['Blood sugar','Cholesterol and triglycerides','Kidney tests','Other measurements','Visit']);
  assert.deepEqual(groups.flatMap(g=>g.facts.map(f=>f.id)).sort(), facts.map(f=>f.id).sort());
  assert.equal(groups[3].facts[0].id,'q');
  assert.equal(JSON.stringify(facts),original);
});


test("lab context remains verbatim, escapes markup and hides temporally withheld details", () => {
  const fact=row('lab','2025-01-01',{reference_range:'<6.0 %',specimen:'Whole blood',test_method:'<script>x</script>'});
  const html=render(LabContext,{fact});
  assert.match(html,/&lt;6.0 %/); assert.match(html,/Whole blood/);
  assert.doesNotMatch(html,/<script>/);
  assert.equal(render(LabContext,{fact:{...fact,value_withheld:true}}),'');
  const review=render(LabContextReview,{row:{...fact,keep:true},index:0,disabled:true,onChange:noop});
  assert.match(review,/disabled/); assert.match(review,/value="&lt;6.0 %"/);
});

test('known vital signs hide only empty lab fields; printed context is never discarded', () => {
  for (const label of ['Blood pressure','수축기혈압','Pulse','heart rate','Weight','BMI','Respiratory rate']) {
    const fact = row('vital','2025-01-01',{label});
    assert.equal(render(LabContext,{fact}), '');
    const printed = render(LabContext,{fact:{...fact,test_method:'Manual <recorded>'}});
    assert.match(printed,/Manual &lt;recorded&gt;/);
    assert.doesNotMatch(printed,/Not recorded|Specimen/);
  }
});

test('missing lab and unclassified-test context stays explicit without substring inference', () => {
  for (const label of ['HbA1c','Ferritin','Novel assay','Blood pressure assay']) {
    const html = render(LabContext,{fact:row('lab','2025-01-01',{label})});
    assert.equal((html.match(/Not recorded/g)||[]).length,3);
  }
});

function sourceEvidence(facts, extra = {}) {
  const view = viewOf(facts);
  view.sources[0].original_available = true;
  return render(SourceCubeEvidence,{source:view.sources[0],facts,view,initialFactId:facts[0]?.id,...extra});
}

test('single evidence shows one result heading and a direct scoped original link before the excerpt', () => {
  const html = sourceEvidence([row('bp','2025-01-01',{label:'Blood pressure',value:'100/70',unit:'mmHg',source_quote:'Printed: 100/70 mmHg'})]);
  assert.equal((html.match(/<h3>Blood pressure<\/h3>/g)||[]).length,1);
  assert.doesNotMatch(html,/Choose a record|aria-label="Select a record"|Specimen|Not recorded/);
  assert.match(html,/<blockquote>Printed: 100\/70 mmHg<\/blockquote>/);
  assert.match(html,/known_at=2026-10-29T00%3A00%3A00Z&amp;as_of=2026-10-20/);
  assert.ok(html.indexOf('Download original') < html.indexOf('<blockquote>'));
  assert.match(html,/Correct saved record/);
  assert.match(html,/View saved versions/);
});

test('multiple evidence records remain selectable in a collapsed bounded list', () => {
  const facts = Array.from({length:60},(_,i)=>row(`r${i}`,'2025-01-01',{source_id:'shared'}));
  const html = sourceEvidence(facts);
  assert.match(html,/<details class="source-evidence-picker"><summary>Choose a record \(60\)/);
  assert.equal((html.match(/aria-pressed=/g)||[]).length,50);
  assert.match(html,/Next source records/);
});

test('corrected evidence retains original quote and visible amendment notice', () => {
  const html = sourceEvidence([row('corrected','2025-01-01',{label:'Pulse',value:'73',unit:'bpm',
    source_quote:'Pulse 72 bpm',previous_revision_id:'old',reviewed_fields:['value']})]);
  assert.match(html,/is-measurement">73<span>bpm/);
  assert.match(html,/<blockquote>Pulse 72 bpm<\/blockquote>/);
  assert.match(html,/Corrected after saving/);
  assert.match(html,/The excerpt retains the original wording/);
});

test('evidence respects withheld facts, missing originals and conflict controls', () => {
  const fact = row('hidden','2025-01-01',{value:'SECRET_VALUE',unit:'SECRET_UNIT',reference_range:'SECRET_RANGE',
    source_quote:'SECRET_QUOTE',value_withheld:true,source_quote_withheld:true});
  const view = viewOf([fact]);
  view.conflicts=[{id:'conflict',fact_ids:[fact.id],reason:'different_recorded_units'}];
  const html=sourceEvidence([fact],{view,source:view.sources[0]});
  assert.doesNotMatch(html,/SECRET_VALUE|SECRET_UNIT|SECRET_QUOTE|SECRET_RANGE/);
  assert.match(html,/Hidden by date filter/);
  assert.match(html,/Original unavailable in this view/);
  assert.doesNotMatch(html,/Download original/);
  assert.match(html,/Compare records/);
});

test('inline text evidence exposes the original outside file details without irrelevant image status', () => {
  const fact=row('text','2025-01-01'); const view=viewOf([fact]);
  view.sources[0].original_available=true;
  const html=render(HomeSourceEvidence,{fact,view,onOpen:noop});
  assert.ok(html.indexOf('Download original') < html.indexOf('<details class="home-proof-details"'));
  assert.doesNotMatch(html,/Source region not located/);
});

test("checkup comparison displays both recorded contexts and server caveats without calculating", () => {
  const current=row('new','2025-01-01',{value:'5.9',reference_range:'4–6',specimen:'Serum',test_method:'B'});
  const previous=row('old','2024-01-01',{value:'5.4',reference_range:'4–5',specimen:'Serum',test_method:'A'});
  const view=viewOf([current,previous]);
  view.checkup_comparison={current,previous:[previous],previous_count:1,difference:null,unit:'%',notes:['Test method differs as printed.'],basis:'Previous fully dated result.',sources:view.sources};
  const html=render(CheckupComparison,{view});
  assert.match(html,/5.9/);assert.match(html,/5.4/);assert.match(html,/Test method differs as printed/);
  assert.doesNotMatch(html,/Recorded difference/);
  assert.match(html,/4–6/);assert.match(html,/4–5/);
  assert.match(html,/How these records were compared/);
  assert.equal((html.match(/Original evidence ·/g)||[]).length,2);
});

test("checkup comparison preserves tied previous records without inventing a difference", () => {
  const current=row('selected','2026-01-01');
  const earlier=[row('old-a','2025-01-01',{value:'5.2'}),row('old-b','2025-01-01',{value:'5.8'})];
  const view=viewOf([current,...earlier]);
  view.checkup_comparison={current,previous:earlier,previous_count:2,difference:null,unit:'%',notes:['Several results share the previous date; all remain separate.'],basis:'Previous fully dated result.',sources:view.sources};
  const html=render(CheckupComparison,{view});
  assert.match(html,/5.2/);assert.match(html,/5.8/);
  assert.equal((html.match(/Original evidence ·/g)||[]).length,3);
  assert.match(html,/Previous result 1/);assert.match(html,/Previous result 2/);
  assert.match(html,/all remain separate/);
  assert.doesNotMatch(html,/Recorded difference/);
  assert.match(html,/Reference range, specimen and test method were not recorded/);
});

function twoReportFixture() {
  const a=row('a','2025-01-01'), b=row('b','2024-01-01');
  const view=viewOf([a,b]);
  return {format:'modus-report-summary-v1',snapshot_id:'a'.repeat(32),scope:view.scope,
    policy_version:'test-policy',current_source:view.sources[0],previous_source:view.sources[1],history_evidence:view,
    rows:[{id:'pair-a',kind:'measurement',label:'HbA1c',current_ids:['a'],previous_ids:['b'],
      status:'comparable',reason_codes:[],notes:[],difference:'0.0',unit:'%',claim_ids:['difference']}],
    claims:[{id:'difference',type:'difference',difference:'0.0',text:'Recorded difference: 0.0 %',evidence_ids:['a','b'],
      verification:{status:'SUPPORTED',reason_codes:['EXACT_REVIEWED_EVIDENCE']}}],
    counts:{rows:1,records:2,comparable:1,not_comparable:0,only_selected:0,only_comparison:0},limitations:[]};
}

test('report summary rejects stale scopes, swapped sides, unverified differences and incomplete payloads',()=>{
  const fixture=twoReportFixture();
  const accepts=value=>matchesReportSummary(value,fixture.snapshot_id,fixture.scope,'source-a','source-b');
  assert.equal(accepts(fixture),true);
  for (const mutate of [
    s=>s.scope.scope_id='wrong-scope', s=>s.snapshot_id='b'.repeat(32),
    s=>s.rows[0].current_ids=['b'], s=>s.history_evidence.facts[0].value_withheld=true,
    s=>s.claims[0].verification.status='CONTRADICTED', s=>delete s.claims[0].verification,
    s=>s.claims.push({...s.claims[0]}), s=>s.counts.records=1,
  ]) {
    const value=structuredClone(fixture);mutate(value);assert.equal(accepts(value),false);
  }
});

test('report summary escapes document content and suppresses unsupported claim wording',()=>{
  const summary=twoReportFixture();
  summary.history_evidence.facts[0].value='<script>alert(1)</script>';
  summary.claims.push({id:'bad',type:'record',text:'UNSUPPORTED MEDICAL CLAIM',evidence_ids:['a'],
    verification:{status:'CONTRADICTED',reason_codes:['CLAIM_TEXT_MISMATCH']}});
  summary.rows[0].claim_ids.push('bad');
  const html=render(ReportComparisonRows,{summary,rows:summary.rows,onInspect:()=>{}});
  assert.match(html,/&lt;script&gt;/); assert.doesNotMatch(html,/<script>|UNSUPPORTED MEDICAL CLAIM/);
  assert.match(html,/Recorded difference: 0.0 %/);
  assert.equal((html.match(/Original evidence:/g)||[]).length,2);
});

const dateEvidence = {
  value:'2024-02-03',source_quote:'Collected: 2024-02-03 <script>untrusted</script>',page:2,bbox:null,
  check:{status:'matched_text',issues:[]},relation:'requires_review',
};

function reportBriefFixture(summary=twoReportFixture()) {
  const {history_evidence,...comparison}=summary;
  const facts=[...history_evidence.facts,...history_evidence.undated_facts];
  return {format:'modus-record-brief-v1',preview_id:'sha256:'+'a'.repeat(64),title:'My checkup comparison',owner_note:'',
    scope:summary.scope,comparison,history_evidence,entries:facts.map((fact,index)=>({...fact,
      citation:`R${index+1}`,source_citation:`S${index+1}`,selected_by_owner:true,added_for_conflict:false})),
    counts:{total:facts.length,selected:facts.length,conflict_companions:0,sources:history_evidence.sources.length},
    conflicts:[],warnings:['Only these selected reports are included.']};
}

test('two-report brief rejects changed numbers, selection, scope and arbitrary companion records',()=>{
  const summary=twoReportFixture();
  const fixture=reportBriefFixture(summary);
  assert.equal(reportBriefMatches(fixture,summary),true);
  for (const mutate of [
    b=>b.comparison.snapshot_id='wrong', b=>b.scope.known_at='2030-01-01T00:00:00Z',
    b=>b.entries[0].value='999', b=>b.entries[0].source_quote='Invented quote',
    b=>b.entries[0].selected_by_owner=false, b=>b.entries.push({...b.entries[0]}),
    b=>b.comparison.rows[0].difference='999', b=>b.comparison.claims[0].text='Unsourced text',
    b=>b.entries[0].value_withheld=true, b=>b.history_evidence.facts.pop(),
  ]) {const candidate=structuredClone(fixture);mutate(candidate);assert.equal(reportBriefMatches(candidate,summary),false);}
});

test('comparison export starts with one preparation action and no automatic download or checkbox',()=>{
  const html=render(ReportBriefReview,{summary:twoReportFixture(),onRefresh:noop});
  assert.match(html,/Prepare a summary to keep/);
  assert.doesNotMatch(html,/type="checkbox"|Download comparison/);
});

test('brief review renders bounded records, escapes content and exposes source evidence',()=>{
  const brief=reportBriefFixture();
  brief.entries=Array.from({length:23},(_,i)=>({...brief.entries[0],id:`record-${i}`,value:i===0?'<script>bad</script>':String(i)}));
  brief.counts.total=23;
  const html=render(ReportBriefContents,{brief,page:0,onPage:noop,onInspect:noop});
  assert.equal((html.match(/Open original evidence/g)||[]).length,10);
  assert.match(html,/&lt;script&gt;bad&lt;\/script&gt;/);assert.doesNotMatch(html,/<script>/);
  assert.match(html,/1–10 of 23/);
  const final=render(ReportBriefContents,{brief,page:2,onPage:noop,onInspect:noop});
  assert.equal((final.match(/Open original evidence/g)||[]).length,3);
});

test('review shows the separate date passage without new save confirmations or merged quotes',()=>{
  const field={...row('dated','2024-02-03'),occurred_on:'2024-02-03',keep:true,date_evidence:dateEvidence};
  const html=render(GenericFactReview,{draft:{id:'draft',source:{original_available:true},facts:[field]},
    rows:[field],locked:false,busy:false,uncertain:false,onChange:noop,onSave:noop,onSkip:noop});
  assert.match(html,/Date in the original · page 2/);
  assert.match(html,/Check that this date belongs to the result before saving/);
  assert.match(html,/&lt;script&gt;untrusted&lt;\/script&gt;/);
  assert.doesNotMatch(html,/<script>/);
  assert.equal((html.match(/type="checkbox"/g)||[]).length,1); // Existing Include field, no redundant checkbox.
});

test('saved evidence retains the original date proposal after a date correction',()=>{
  const fact=row('dated','2024-02-02',{occurred_on:'2024-02-02',date_evidence:dateEvidence});
  const view=viewOf([fact]);
  const html=render(SourceCubeEvidence,{source:view.sources[0],facts:[fact],view,initialFactId:fact.id});
  assert.match(html,/The saved date differs/);
  assert.match(html,/original date proposal: 2024-02-03/);
  assert.doesNotMatch(html,/Check that this date belongs to the result before saving/);
});

test('hidden evidence cannot leak its date passage through either inspector',()=>{
  const fact=row('dated','2024-02-03',{date_evidence:dateEvidence,source_quote:null,source_quote_withheld:true});
  const view=viewOf([fact]);
  for(const html of [render(SourceCubeEvidence,{source:view.sources[0],facts:[fact],view,initialFactId:fact.id}),
    render(HomeSourceEvidence,{fact,view,onOpen:noop})]) {
    assert.doesNotMatch(html,/Date in the original|Collected:|untrusted/);
  }
});


test('Orbit retains source formats in accessible descriptions without adding format or axis clutter',()=>{
  const formats=[['pdf','Review.pdf','PDF'],['image/png','Scan.png','IMG'],['text/csv','Labs.csv','CSV'],['text/plain','Note.txt','TXT']];
  const reports=formats.map(([type,title],i)=>({source:{id:'format-'+i,type,title},latestDate:'2024-02-20',
    facts:[row('format-'+i,'2024-02-20')]}));
  const original=structuredClone(reports);
  const html=render(OrbitMap,{reports,selectedId:'format-2',onSelect:noop,prominent:true});
  for(const [,title,format] of formats) {
    assert.ok(html.includes(`Open source file: ${title}; ${format};`));
    assert.ok(!html.includes(`>${format}</text>`));
  }
  assert.match(html,/orbit-file-relations/);
  assert.match(html,/orbit-connection/);
  assert.doesNotMatch(html,/orbit-crosshair|2020–2024|M300 18V426|Rings group recorded years/);
  assert.deepEqual(reports,original);
});

test('Twelve relational orbit files retain separate actions, the selected source and unknown precision',()=>{
  const reports=Array.from({length:12},(_,i)=>({source:{id:'same-'+i,type:'text/csv',title:'Same filename.csv'},
    latestDate:i===11?null:'2024-02-20',facts:[row('same-'+i,i===11?null:'2024-02-20')]}));
  const html=render(OrbitMap,{reports,selectedId:'same-8',total:198,onSelect:noop,onOpenAll:noop,prominent:true});
  assert.equal((html.match(/role="button"/g)||[]).length,12);
  assert.equal((html.match(/aria-pressed="true"/g)||[]).length,1);
  assert.equal((html.match(/<option value="same-/g)||[]).length,12);
  assert.match(html,/12 of 198/);
  assert.match(html,/>Undated<\/text>/);
  assert.match(html,/All files/);
  assert.doesNotMatch(html,/clinical relationship|health score|risk score/i);
});

test('Report picker distinguishes repeated filenames without renaming their sources',()=>{
  const reports = ['2024-02-03','2025-05-20','2025-05-20',null].map((date,index)=>({
    source:{id:`repeat-${index}`,title:'checkup.csv',type:'csv'},latestDate:date,
    facts:[row(`repeat-${index}`,date)],
  }));
  reports.push({source:{id:'unique',title:'unique.csv',type:'csv'},latestDate:null,facts:[]});
  const original = structuredClone(reports);
  const html = render(OrbitMap,{reports,selectedId:'repeat-2',onSelect:noop,prominent:true});
  const options = [...html.matchAll(/<option[^>]*>([^<]*)<\/option>/g)].map(match=>match[1]);
  assert.equal(new Set(options).size,5);
  assert.ok(options.includes('checkup.csv · 3 Feb 2024'));
  assert.ok(options.includes('checkup.csv · 20 May 2025 · file 1'));
  assert.ok(options.includes('checkup.csv · 20 May 2025 · file 2'));
  assert.ok(options.includes('checkup.csv · Date not recorded'));
  assert.ok(options.includes('unique.csv'));
  assert.match(html,/<option value="repeat-2" selected="">/);
  assert.deepEqual(reports,original);
});

test('Twelve same-era orbit targets have mobile touch clearance and outward date labels',()=>{
  const reports=Array.from({length:12},(_,i)=>({source:{id:'dense-'+i,type:'text/csv',title:'Same filename.csv'},
    latestDate:i===11?null:'2026-10-20',facts:[row('dense-'+i,i===11?null:'2026-10-20')]}));
  const html=render(OrbitMap,{reports,selectedId:'dense-0',onSelect:noop,prominent:true});
  const positions=[...html.matchAll(/class="orbit-satellite[^"]*" transform="translate\(([^)]+)\)"/g)]
    .map(match=>match[1].split(' ').map(Number));
  assert.equal(positions.length,12);
  for(let i=0;i<positions.length;i++) for(let j=i+1;j<positions.length;j++) {
    const distance=Math.hypot(positions[i][0]-positions[j][0],positions[i][1]-positions[j][1]);
    assert.ok(distance>76,'38-unit mobile hit areas must not overlap');
    assert.ok(distance*358/600>44,'Targets remain separately reachable in the 390px viewport');
  }
  const labels=[...html.matchAll(/class="orbit-node-date" x="([^"]+)" y="([^"]+)"/g)]
    .map(match=>[Number(match[1]),Number(match[2])]);
  assert.equal(labels.length,12);
  labels.forEach(([x,y],index)=>{
    const [nodeX,nodeY]=positions[index];
    assert.ok(x*(nodeX-300)+y*(nodeY-222)>0,'Year labels extend away from the owner and other nodes');
    assert.ok(nodeX+x>15 && nodeX+x<585 && nodeY+y>10 && nodeY+y<450);
  });
  assert.match(html,/>Undated<\/text>/);
});
