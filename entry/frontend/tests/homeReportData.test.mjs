import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(
  new URL("../src/homeReportData.ts", import.meta.url),
  "utf8",
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ESNext,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;
const { reportSummaries, isLatestReport, previousRecords, recordHistory, sourceRegion, recordedDates, orbitLayout, dateDay, dayDate, archiveElapsed } =
  await import(
    "data:text/javascript;base64," + Buffer.from(compiled).toString("base64")
  );

test("source region rejects invalid geometry and withheld evidence", () => {
  const fact = { bbox: [0.1, 0.2, 0.8, 0.4] };
  assert.deepEqual(sourceRegion(fact), fact.bbox);
  for (const bbox of [null, [0, 0, 1], [0.5, 0, 0.3, 1], [-1, 0, 1, 1], [0, 0, Infinity, 1]]) {
    assert.equal(sourceRegion({ bbox }), null);
  }
  assert.equal(sourceRegion({ ...fact, value_withheld: true }), null);
  assert.equal(sourceRegion({ ...fact, source_quote_withheld: true }), null);
});

test("scrub stops use only actual complete dates, deduplicated", () => {
  assert.deepEqual(recordedDates({facts: [{date:'2024-02-03'}, {date:'2016-05-04'},
    {date:'2024-02-03'}, {date:null}, {date:'2024-02-31'}, {date:'2012'}]}), ['2016-05-04', '2024-02-03']);
});

const row = (id, date, extra = {}) => ({
  id,
  source_id: `source-${id}`,
  kind: "measurement",
  label: "HbA1c",
  value: "5.70",
  unit: "%",
  date,
  occurred_on: date,
  facility: null,
  available_at: "2026-10-29T00:00:00Z",
  source_quote: "HbA1c 5.70 %",
  page: 1,
  ...extra,
});
const viewOf = (facts, extra = {}) => ({
  facts,
  undated_facts: [],
  conflicts: [],
  sources: [...new Set(facts.map((fact) => fact.source_id))].map((id) => ({
    id,
    title: id,
    date: "2099-01-01",
    available_at: "2026-10-29T00:00:00Z",
  })),
  ...extra,
});
const ids = (facts) => facts.map((fact) => fact.id);

test("orbit preserves every source, including ties and files without a complete date", () => {
  const reports = reportSummaries(viewOf([
    row('old', '2016-05-04'), row('a', '2026-10-20'), row('b', '2026-10-20'),
    row('unknown', null), row('partial', '2012'),
  ]));
  const { rings, nodes } = orbitLayout(reports);
  assert.equal(nodes.length, reports.length);
  assert.equal(new Set(nodes.map((node) => node.id)).size, reports.length);
  assert.deepEqual(rings.map((ring) => ring.label), ['2015–2019', '2025–2029']);
  assert.equal(nodes.filter((node) => node.era === null).length, 2);
  for (const node of nodes) {
    assert.ok(Number.isFinite(node.x) && Number.isFinite(node.y));
    const ring = rings.find((item) => item.era === node.era);
    if (ring) assert.ok(Math.abs(Math.hypot(node.x - 300, node.y - 222) - ring.radius) < 1e-8);
  }
  const byId = (value) => [...value].sort((a, b) => a.id.localeCompare(b.id));
  assert.deepEqual(byId(orbitLayout([...reports].reverse()).nodes), byId(nodes));
});

test("empty orbit and a single undated file cannot invent a dated ring", () => {
  assert.deepEqual(orbitLayout([]), { rings:[], nodes:[] });
  const layout = orbitLayout(reportSummaries(viewOf([row('unknown', null)])));
  assert.deepEqual(layout.rings, []);
  assert.equal(layout.nodes[0].era, null);
  assert.ok(Number.isFinite(layout.nodes[0].x));
});

test("timeline uses elapsed UTC days, retaining leap days and uneven gaps", () => {
  assert.equal(dateDay('2024-03-01') - dateDay('2024-02-28'), 2);
  assert.equal(dateDay('2024-04-01') - dateDay('2024-03-01'), 31);
  for (const date of ['1900-01-01', '2024-02-29', '2026-10-29']) assert.equal(dayDate(dateDay(date)), date);
  for (const date of ['2024', '2024-02-30', '0000-01-01', '2026-10-29T00:00:00Z']) assert.equal(dateDay(date), null);
});

test("T+ measures complete calendar months, including before-first and unknown history", () => {
  assert.equal(archiveElapsed('2018-04-09', '2026-10-29'), 'T+ 08Y 06M');
  assert.equal(archiveElapsed('2018-04-09', '2026-10-08'), 'T+ 08Y 05M');
  assert.equal(archiveElapsed('2024-02-29', '2024-02-29'), 'T+ 00Y 00M');
  assert.equal(archiveElapsed('2024-02-29', '2024-02-28'), 'BEFORE FIRST RECORD');
  assert.equal(archiveElapsed(undefined, '2024-02-29'), 'T+ —');
});

test("latest reports use recorded fact dates, never late upload times or source metadata", () => {
  const old = row("old", "2018-04-09", {
    available_at: "2026-10-29T04:00:00Z",
  });
  const recent = row("recent", "2026-10-20", {
    available_at: "2026-10-20T00:00:00Z",
  });
  const undated = row("undated", null);
  const view = viewOf([old, recent, undated]);
  const original = structuredClone(view);
  assert.deepEqual(
    reportSummaries(view).map(({ source, latestDate }) => [
      source.id,
      latestDate,
    ]),
    [
      ["source-recent", "2026-10-20"],
      ["source-old", "2018-04-09"],
      ["source-undated", null],
    ],
  );
  assert.deepEqual(view, original);
});

test("every report tied on the newest exact date is latest; older and undated reports are not", () => {
  const reports = reportSummaries(
    viewOf([
      row("same-b", "2026-10-20"),
      row("older", "2024-02-03"),
      row("undated", null),
      row("same-a", "2026-10-20"),
    ]),
  );
  assert.deepEqual(
    reports.map((report) => [
      report.source.id,
      isLatestReport(reports, report),
    ]),
    [
      ["source-same-a", true],
      ["source-same-b", true],
      ["source-older", false],
      ["source-undated", false],
    ],
  );
  const undated = reportSummaries(
    viewOf([row("unknown", null), row("partial", "2024")]),
  );
  assert.ok(undated.every((report) => !isLatestReport(undated, report)));
  assert.equal(isLatestReport([], null), false);
  assert.equal(isLatestReport(reports, undefined), false);
});

test("a mixed-date report keeps each row's own previous date", () => {
  const older = row("older", "2018-01-01");
  const middle = row("middle", "2021-01-01");
  const first = row("first", "2020-01-01", { source_id: "report" });
  const last = row("last", "2026-01-01", { source_id: "report" });
  const view = viewOf([older, middle, first, last]);
  const report = reportSummaries(view).find(
    (item) => item.source.id === "report",
  );
  assert.equal(report.latestDate, "2026-01-01");
  assert.deepEqual(ids(report.facts), ["first", "last"]);
  assert.deepEqual(ids(previousRecords(view, first)), ["older"]);
  assert.deepEqual(ids(previousRecords(view, last)), ["middle"]);
});

test("the nearest earlier record is retained when units differ, without skipping backward", () => {
  const oldest = row("oldest", "2018-01-01", { unit: "%", value: "5.1" });
  const previous = row("previous", "2024-01-01", {
    unit: "mmol/mol",
    value: "39",
  });
  const current = row("current", "2026-01-01");
  const view = viewOf([oldest, previous, current]);
  assert.deepEqual(previousRecords(view, current), [previous]);
  assert.equal(previousRecords(view, current)[0].unit, "mmol/mol");
  assert.deepEqual(
    recordHistory(view, current).map((item) => [item.value, item.unit]),
    [
      ["5.1", "%"],
      ["39", "mmol/mol"],
      ["5.70", "%"],
    ],
  );
});

test("all previous-date ties and current-date ties retain their sources and units", () => {
  const a = row("a", "2024-01-01", { value: "5.6" });
  const b = row("b", "2024-01-01", { value: "38", unit: "mmol/mol" });
  const c = row("c", "2026-01-01", { value: "5.7" });
  const d = row("d", "2026-01-01", { value: "5.8" });
  const view = viewOf([d, b, c, a]);
  assert.deepEqual(ids(previousRecords(view, c)), ["a", "b"]);
  assert.deepEqual(ids(recordHistory(view, c)), ["a", "b", "c", "d"]);
});

test("withheld newest and previous values remain in place rather than exposing older values", () => {
  const visible = row("visible", "2018-01-01");
  const hiddenPrevious = row("hidden-previous", "2024-01-01", {
    value: null,
    value_withheld: true,
    source_quote: null,
  });
  const hiddenCurrent = row("hidden-current", "2026-01-01", {
    value: null,
    value_withheld: true,
    source_quote: null,
  });
  const view = viewOf([visible, hiddenPrevious, hiddenCurrent]);
  assert.equal(reportSummaries(view)[0].source.id, "source-hidden-current");
  assert.deepEqual(previousRecords(view, hiddenCurrent), [hiddenPrevious]);
  assert.deepEqual(ids(recordHistory(view, hiddenCurrent)), [
    "visible",
    "hidden-previous",
    "hidden-current",
  ]);
  assert.equal(recordHistory(view, hiddenCurrent).at(-1).value, null);
});

test("facts from absent sources or outside the date scope cannot enter summaries or comparisons", () => {
  const previous = row("previous", "2021-01-01");
  const orphan = row("orphan", "2024-01-01");
  const outside = row("outside", "2025-01-01", { within_date_scope: false });
  const current = row("current", "2026-01-01");
  const view = viewOf([previous, orphan, outside, current]);
  view.sources = view.sources.filter((item) => item.id !== orphan.source_id);
  assert.deepEqual(
    ids(reportSummaries(view).flatMap((report) => report.facts)).sort(),
    ["current", "previous"],
  );
  assert.deepEqual(previousRecords(view, current), [previous]);
  assert.deepEqual(ids(recordHistory(view, current)), ["previous", "current"]);
  assert.deepEqual(previousRecords(view, outside), []);
  assert.deepEqual(recordHistory(view, orphan), []);
});

test("partial, unknown, impossible and timestamp dates stay in files without acquiring chronology", () => {
  const invalid = [
    null,
    "2012",
    "2012-06",
    "2024-02-30",
    "2024-13-01",
    "04/05/2020",
    "unknown",
    "0000-01-01",
    "2026-01-01T00:00:00Z",
  ].map((date, index) => row(`invalid-${index}`, date));
  const current = row("current", "2026-01-01");
  const view = viewOf([current, ...invalid]);
  const reports = reportSummaries(view);
  assert.equal(reports[0].latestDate, "2026-01-01");
  assert.ok(reports.slice(1).every((report) => report.latestDate === null));
  assert.equal(reports.flatMap((report) => report.facts).length, 10);
  assert.deepEqual(previousRecords(view, current), []);
  assert.deepEqual(recordHistory(view, current), [current]);
  for (const fact of invalid) assert.deepEqual(recordHistory(view, fact), []);
});

test("an exact leap-day date is preserved but occurred_on cannot supply a missing exact date", () => {
  const leap = row("leap", "2024-02-29");
  const unspecified = row("unspecified", null, { occurred_on: "2025-01-01" });
  const current = row("current", "2026-01-01");
  const view = viewOf([leap, unspecified, current]);
  assert.deepEqual(previousRecords(view, current), [leap]);
  assert.equal(
    reportSummaries(view).find(
      (item) => item.source.id === unspecified.source_id,
    ).latestDate,
    null,
  );
});

test("nonmeasurement records are compared only within their exact recorded kind and label", () => {
  const previous = row("previous", "2020-01-01", {
    kind: "vaccination",
    label: "MMR",
    value: "Recorded",
    unit: null,
  });
  const current = row("current", "2026-01-01", {
    kind: "vaccination",
    label: "MMR",
    value: "Recorded",
    unit: null,
  });
  const otherKind = row("other-kind", "2025-01-01", {
    kind: "recorded_text",
    label: "MMR",
  });
  const otherLabel = row("other-label", "2025-01-01", {
    kind: "vaccination",
    label: "MMR (reported)",
  });
  const view = viewOf([previous, current, otherKind, otherLabel]);
  assert.deepEqual(previousRecords(view, current), [previous]);
  assert.deepEqual(recordHistory(view, current), [previous, current]);
});

test("current view facts replace stale anchors and future records do not enter row history", () => {
  const previous = row("previous", "2020-01-01");
  const current = row("current", "2024-01-01", {
    value: null,
    value_withheld: true,
  });
  const future = row("future", "2026-01-01");
  const stale = {
    ...current,
    date: "2027-01-01",
    value: "5.7",
    value_withheld: false,
  };
  const view = viewOf([previous, current, future]);
  assert.deepEqual(recordHistory(view, stale), [previous, current]);
  assert.deepEqual(previousRecords(view, stale), [previous]);
  assert.deepEqual(recordHistory(view, { ...stale, id: "removed" }), []);
});

test("undated records remain attached to their file and duplicate retained facts do not inflate it", () => {
  const current = row("current", "2026-01-01", {
    value: null,
    value_withheld: true,
  });
  const undated = row("undated", null, {
    occurred_on: "childhood",
    source_id: current.source_id,
  });
  const view = viewOf([current], {
    undated_facts: [
      undated,
      { ...current, value: "5.7", value_withheld: false },
    ],
  });
  const report = reportSummaries(view)[0];
  assert.deepEqual(report.facts, [current, undated]);
  assert.equal(report.latestDate, "2026-01-01");
  assert.deepEqual(recordHistory(view, current), [current]);
});
