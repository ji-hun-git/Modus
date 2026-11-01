import test from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
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
      'export { default as HomeIntegrityTools } from "./HomeIntegrityTools";',
      'export { default as OrbitMap } from "./OrbitMap";',
      'export { historyFields } from "./historyFields";',
      'export { HistoryTrends } from "./MeasurementsWorkspace";',
      'export { default as GenericFactReview } from "./GenericFactReview";',
      'export { default as ReportCoverageSummary } from "./ReportCoverageSummary";',
      'export { default as ExtractionReviewSummary } from "./ExtractionReviewSummary";',
      'export { default as HistoryAnswerView } from "./HistoryAnswerView";',
      'export { default as HistoryQuestionPanel, historySuggestions } from "./HistoryQuestionPanel";',
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
const { HomeReportComparison, HomeHistoryTrail, HomeSourceEvidence, HomeIntegrityTools, OrbitMap, historyFields, HistoryTrends, GenericFactReview, ReportCoverageSummary, ExtractionReviewSummary, HistoryAnswerView, HistoryQuestionPanel, historySuggestions } =
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
  assert.match(html,/Ask about your history/);
  assert.match(html,/<details class="orbit-history-options"><summary>History options/);
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
  assert.match(html, />YOU<\/text>/);
  assert.match(html, />UNDATED<\/text>/);
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
