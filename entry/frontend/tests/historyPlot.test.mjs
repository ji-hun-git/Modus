import assert from "node:assert/strict";
import { test } from "node:test";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(
  new URL("../src/historyGeometry.ts", import.meta.url),
  "utf8",
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ESNext,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;
const { buildHistorySeries } = await import(
  "data:text/javascript;base64," + Buffer.from(compiled).toString("base64")
);
const row = (id, date, value, unit = "%") => ({
  id,
  date,
  value,
  unit,
  source_id: `source-${id}`,
  metric: "hba1c",
});

test("plot uses elapsed days rather than evenly spaced dates", () => {
  const [{ points }] = buildHistorySeries([
    row("late", "2020-04-10", 6),
    row("first", "2020-01-01", 5),
    row("near", "2020-01-11", 5.5),
  ]);
  assert.deepEqual(
    points.map((point) => point.date),
    ["2020-01-01", "2020-01-11", "2020-04-10"],
  );
  assert.equal(points[0].x, 9);
  assert.equal(points[2].x, 91);
  assert.ok(Math.abs(points[1].x - 17.2) < 1e-10);
});

test("same-day differing readings remain distinct and break both adjacent connections", () => {
  const [{ points, segments }] = buildHistorySeries([
    row("first", "2020-01-01", 5),
    row("a", "2021-01-01", 5.2),
    row("b", "2021-01-01", 6.1),
    row("last", "2022-01-01", 5.6),
  ]);
  assert.equal(points.length, 4);
  assert.equal(points[1].x, points[2].x);
  assert.notEqual(points[1].y, points[2].y);
  assert.equal(points.filter((point) => point.disputed).length, 2);
  assert.deepEqual(segments, []);
});

test("backend conflict membership breaks a line even with one visible value", () => {
  const [{ segments, points }] = buildHistorySeries(
    [row("a", "2020-01-01", 5), row("b", "2021-01-01", 6)],
    new Set(["b"]),
  );
  assert.equal(points[1].disputed, true);
  assert.equal(segments.length, 0);
});

test("units get separate scales and are never bridged across an intervening incompatible record", () => {
  const series = buildHistorySeries([
    row("a", "2020-01-01", 5),
    row("b", "2021-01-01", 40, "mmol/mol"),
    row("c", "2022-01-01", 6),
  ]);
  assert.deepEqual(
    series.map((item) => item.unit),
    ["%", "mmol/mol"],
  );
  assert.equal(series.flatMap((item) => item.segments).length, 0);
  assert.equal(series[1].points[0].value, 40);
});

test("equal readings from different sources share geometry but preserve every source", () => {
  const [{ points }] = buildHistorySeries([
    row("a", "2020-01-01", 5.123456789),
    row("b", "2020-01-01", 5.123456789),
  ]);
  assert.equal(points.length, 1);
  assert.equal(points[0].value, 5.123456789);
  assert.deepEqual(
    points[0].observations.map((item) => item.id),
    ["a", "b"],
  );
  assert.equal(points[0].disputed, false);
});

test("single-date and constant values have finite centered geometry", () => {
  let [{ points }] = buildHistorySeries([row("a", "2020-01-01", 5)]);
  assert.equal(points[0].x, 50);
  assert.equal(points[0].y, 50);
  [{ points }] = buildHistorySeries([
    row("a", "2020-01-01", 5),
    row("b", "2021-01-01", 5),
  ]);
  assert.deepEqual(
    points.map((point) => point.y),
    [50, 50],
  );
});

test("invalid dates and values do not generate guessed geometry", () => {
  for (const item of [
    row("a", "2020-02-30", 5),
    row("a", "2020-1-1", 5),
    row("a", "2020-01-01", NaN),
    row("a", "2020-01-01", Infinity),
  ])
    assert.deepEqual(buildHistorySeries([item]), []);
  assert.deepEqual(buildHistorySeries([]), []);
});

test("geometry does not mutate original values, source membership or order", () => {
  const source = [row("b", "2021-01-01", 6), row("a", "2020-01-01", 5)];
  const original = structuredClone(source);
  const [series] = buildHistorySeries(source);
  assert.equal(series.segments.length, 1);
  assert.deepEqual(source, original);
});
