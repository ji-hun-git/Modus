import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const compile = (source) =>
  ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
const url = (source) =>
  "data:text/javascript;base64," + Buffer.from(source).toString("base64");
const geometry = url(
  compile(
    await readFile(
      new URL("../src/historyGeometry.ts", import.meta.url),
      "utf8",
    ),
  ),
);
const source = compile(
  await readFile(
    new URL("../src/homeSeriesData.ts", import.meta.url),
    "utf8",
  ),
).replace('"./historyGeometry"', JSON.stringify(geometry));
const { recordedSeries } = await import(url(source));
const row = (id, date, value, unit = "bpm") => ({
  id,
  kind: "measurement",
  label: "Pulse",
  date,
  occurred_on: date,
  value,
  unit,
  source_id: `source-${id}`,
  source_quote: `Pulse ${value}`,
  available_at: "2026-10-29T00:00:00+00:00",
});
const plot = (
  facts,
  disputed = new Set(),
  sources = new Set(facts.map((fact) => fact.source_id)),
) => recordedSeries(facts, sources, disputed);

test("generic Pulse history uses elapsed days and retains exact source value strings", () => {
  const facts = [
    row("a", "2020-01-01", "072.0"),
    row("b", "2020-01-11", "73"),
    row("c", "2020-04-10", "74"),
  ];
  const result = plot(facts);
  const points = result.series[0].points;
  assert.equal(result.plotted, 3);
  assert.ok(Math.abs(points[1].x - 17.2) < 1e-10);
  assert.equal(points[0].observations[0].fact.value, "072.0");
  assert.equal(points[0].observations[0].fact.source_quote, "Pulse 072.0");
  assert.equal(facts[0].value, "072.0");
});

test("text, comparators, ranges, nonfinite values and partial dates never become guessed points", () => {
  const facts = [
    row("a", "2020-01-01", "<70"),
    row("b", "2020-01-01", "70–80"),
    row("c", "2020-01-01", "about 72"),
    row("d", "2020-01-01", "Infinity"),
    row("e", "2020-01-01", "1e999"),
    row("f", "2020-01", "72"),
    row("g", "2020-02-30", "72"),
    row("h", null, "72"),
    row("i", "2020-01-01", ""),
  ];
  const original = structuredClone(facts);
  assert.deepEqual(plot(facts), { series: [], plotted: 0, omitted: 9 });
  assert.deepEqual(facts, original);
});

test("withheld, out-of-scope and missing-source values cannot enter a Home plot", () => {
  const facts = [
    row("a", "2020-01-01", "72"),
    { ...row("b", "2020-01-02", "73"), value_withheld: true },
    { ...row("c", "2020-01-03", "74"), within_date_scope: false },
    row("d", "2020-01-04", "75"),
  ];
  const result = plot(
    facts,
    new Set(),
    new Set(["source-a", "source-b", "source-c"]),
  );
  assert.equal(result.plotted, 1);
  assert.equal(result.omitted, 3);
  assert.equal(result.series[0].points[0].observations[0].id, "a");
});

test("same-day different values and repeated equal values preserve every source", () => {
  const result = plot([
    row("a", "2020-01-01", "72"),
    row("b", "2020-01-01", "73"),
    row("c", "2020-01-01", "73.0"),
  ]);
  assert.equal(result.plotted, 3);
  assert.equal(result.series[0].points.length, 2);
  assert.deepEqual(
    result.series[0].points.flatMap((point) =>
      point.observations.map((observation) => observation.id),
    ),
    ["a", "b", "c"],
  );
  assert.equal(result.series[0].points[0].x, result.series[0].points[1].x);
  assert.ok(result.series[0].points.every((point) => point.disputed));
});

test("exact units remain separate, and exact labels cannot be pooled", () => {
  const separate = plot([
    row("a", "2020-01-01", "72", "bpm"),
    row("b", "2020-01-02", "1.2", "Hz"),
    row("c", "2020-01-03", "72", null),
  ]);
  assert.deepEqual(
    separate.series.map((series) => series.unit),
    ["bpm", "Hz", ""],
  );
  const mixed = [
    row("a", "2020-01-01", "72"),
    { ...row("b", "2020-01-02", "73"), label: "Pulse after exercise" },
  ];
  assert.deepEqual(plot(mixed), { series: [], plotted: 0, omitted: 2 });
});

test("underflow and precision loss stay in exact source records, not rounded chart points", () => {
  const facts = [
    row("underflow", "2020-01-01", "1e-400"),
    row("negative-underflow", "2020-01-01", "-1e-400"),
    row("unsafe-integer", "2020-01-01", "9007199254740993"),
    row("large-exact-integer", "2020-01-01", "9007199254740992"),
    row("rounded-fraction", "2020-01-01", "0.10000000000000001"),
    row("ordinary-fraction", "2020-01-01", "0.1"),
    row("safe-integer", "2020-01-02", "9007199254740991"),
  ];
  const original = structuredClone(facts);
  const result = plot(facts);
  assert.equal(result.plotted, 2);
  assert.equal(result.omitted, 5);
  assert.deepEqual(result.series[0].points.map((point) => point.value), [0.1, 9007199254740991]);
  assert.deepEqual(facts, original);
});

test("equivalent decimal spelling and finite small scalars preserve original precision", () => {
  const facts = [
    row("a", "2020-01-01", "+00072.000"),
    row("b", "2020-01-02", "7.200e1"),
    row("c", "2020-01-03", ".00120"),
    row("d", "2020-01-04", "-0.000"),
    row("e", "2020-01-05", "5e-324"),
  ];
  const result = plot(facts);
  assert.equal(result.plotted, 5);
  assert.equal(result.omitted, 0);
  assert.deepEqual(
    result.series[0].points.map((point) => point.observations[0].fact.value),
    facts.map((fact) => fact.value),
  );
  assert.ok(result.series[0].points.every((point) => Number.isFinite(point.x) && Number.isFinite(point.y)));
});

test("opposing extreme magnitudes cannot overflow a plotted scale", () => {
  const facts = [
    row("a", "2020-01-01", "-1e308"),
    row("b", "2020-01-02", "1e308"),
    row("c", "2020-01-03", "72"),
    row("d", "2020-01-04", "74.5"),
  ];
  const result = plot(facts);
  assert.equal(result.plotted, 2);
  assert.equal(result.omitted, 2);
  assert.ok(result.series.every((group) => group.points.every(
    (point) => [point.value, point.x, point.y].every(Number.isFinite),
  )));
});

test("a nonfinite geometry result omits its entire unit group and counts source rows", async () => {
  const invalidGeometry = url(`export function buildHistorySeries(rows) {
    return [
      { unit: 'bpm', points: [{ value: 72, x: 50, y: NaN, observations: rows.slice(0, 2) }], segments: [] },
      { unit: 'Hz', points: [{ value: 1.2, x: 50, y: 50, observations: rows.slice(2) }], segments: [] },
    ];
  }`);
  const { recordedSeries: guarded } = await import(url(
    source.replace(JSON.stringify(geometry), JSON.stringify(invalidGeometry)),
  ));
  const facts = [
    row("a", "2020-01-01", "72"),
    row("b", "2020-01-01", "72.0"),
    row("c", "2020-01-02", "1.2", "Hz"),
  ];
  const result = guarded(facts, new Set(facts.map((fact) => fact.source_id)), new Set());
  assert.equal(result.plotted, 1);
  assert.equal(result.omitted, 2);
  assert.deepEqual(result.series.map((group) => group.unit), ["Hz"]);
});
