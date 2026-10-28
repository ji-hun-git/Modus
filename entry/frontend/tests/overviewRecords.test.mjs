import assert from "node:assert/strict";
import { test } from "node:test";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(
  new URL("../src/overviewRecords.ts", import.meta.url),
  "utf8",
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ESNext,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;
const {
  latestMeasurements,
  datedRecords,
  recordDays,
  scopedDifferences,
  currentOverviewFacts,
} = await import(
  "data:text/javascript;base64," + Buffer.from(compiled).toString("base64")
);

const fact = (id, date, extra = {}) => ({
  id,
  source_id: "source-1",
  kind: "measurement",
  label: "eGFR",
  value: "82",
  unit: "mL/min/1.73m2",
  date,
  occurred_on: date,
  available_at: "2026-10-28T01:00:00Z",
  source_quote: "Original text",
  ...extra,
});
const view = (facts, extra = {}) => ({
  facts,
  undated_facts: [],
  sources: [{ id: "source-1" }],
  conflicts: [],
  ...extra,
});

test("a late-added old measurement does not replace the latest occurrence date", () => {
  const records = view([
    fact("late", "2021-04-08", { available_at: "2026-10-28T02:00:00Z" }),
    fact("newer", "2026-10-20", {
      value: "83",
      available_at: "2026-10-20T00:00:00Z",
    }),
  ]);
  const result = latestMeasurements(records)[0];
  assert.equal(result.date, "2026-10-20");
  assert.deepEqual(
    result.latest.map((item) => item.id),
    ["newer"],
  );
  assert.deepEqual(
    result.history.map((item) => item.id),
    ["newer", "late"],
  );
});

test("every newest same-day record remains separate with exact saved value and unit strings", () => {
  const records = view(
    [
      fact("b", "2021-04-08", { value: "82.0" }),
      fact("a", "2021-04-08", { value: "96" }),
      fact("earlier", "2018-04-09", { value: "99" }),
    ],
    { conflicts: [{ id: "difference-1", fact_ids: ["a", "b"] }] },
  );
  const result = latestMeasurements(records)[0];
  assert.deepEqual(
    result.latest.map((item) => [item.value, item.unit]),
    [
      ["96", "mL/min/1.73m2"],
      ["82.0", "mL/min/1.73m2"],
    ],
  );
  assert.deepEqual(result.conflictIds, ["difference-1"]);
});

test("multiple readings are not labelled a discrepancy without a backend conflict group", () => {
  const result = latestMeasurements(
    view([fact("a", "2021-04-08"), fact("b", "2021-04-08", { value: "82.0" })]),
  )[0];
  assert.equal(result.latest.length, 2);
  assert.deepEqual(result.conflictIds, []);
});

test("partial, ambiguous and invalid date text never becomes a dated latest result", () => {
  const undated = [
    "2012",
    "2012-06",
    "04/05/2020",
    "2020-02-30",
    "approximately 2019",
  ].map((text, index) => fact(`unknown-${index}`, null, { occurred_on: text }));
  const records = view([fact("exact", "2011-04-08"), ...undated], {
    undated_facts: undated,
  });
  assert.deepEqual(
    datedRecords(records).map((item) => item.id),
    ["exact"],
  );
  assert.equal(latestMeasurements(records)[0].date, "2011-04-08");
  assert.deepEqual(
    records.undated_facts.map((item) => item.occurred_on),
    ["2012", "2012-06", "04/05/2020", "2020-02-30", "approximately 2019"],
  );
});

test("hidden latest values remain hidden and do not fall back to an older visible number", () => {
  const result = latestMeasurements(
    view([
      fact("latest-hidden", "2026-10-20", {
        value: null,
        value_withheld: true,
        source_quote: null,
      }),
      fact("older", "2021-04-08", { value: "96" }),
    ]),
  )[0];
  assert.equal(result.latest[0].id, "latest-hidden");
  assert.equal(result.latest[0].value, null);
  assert.equal(result.latest[0].value_withheld, true);
});

test("exact recorded labels stay distinct and mixed units are never converted or averaged", () => {
  const groups = latestMeasurements(
    view([
      fact("a", "2026-10-20", {
        label: "LDL cholesterol",
        value: "119",
        unit: "mg/dL",
      }),
      fact("b", "2026-10-20", {
        label: "LDL cholesterol",
        value: "3.08",
        unit: "mmol/L",
      }),
      fact("qualified", "2026-10-20", {
        label: "LDL cholesterol, direct",
        value: "120",
        unit: "mg/dL",
      }),
    ]),
  );
  assert.equal(groups.length, 2);
  const ordinary = groups.find((group) => group.label === "LDL cholesterol");
  assert.deepEqual(
    ordinary.latest.map((item) => [item.value, item.unit]),
    [
      ["119", "mg/dL"],
      ["3.08", "mmol/L"],
    ],
  );
});

test("current canonical facts replace retained selection objects and exclude missing sources", () => {
  const stale = fact("same", "2021-04-08", {
    value: "96",
    source_quote: "Previously visible",
  });
  const hidden = fact("same", "2021-04-08", {
    value: null,
    value_withheld: true,
    source_quote: null,
  });
  const orphan = fact("orphan", "2026-10-20", { source_id: "not-in-view" });
  const current = view([hidden, orphan]);
  const selected = currentOverviewFacts(current, [
    stale.id,
    "removed",
    orphan.id,
  ]);
  assert.deepEqual(selected, [hidden]);
  assert.equal(selected[0].value, null);
  assert.equal(selected[0].source_quote, null);
  assert.equal(latestMeasurements(current)[0].date, "2021-04-08");
});

test("recent record groups include every record kind and use occurrence dates only", () => {
  const records = view([
    fact("visit", "2026-10-01", {
      kind: "encounter",
      label: "Visit",
      available_at: "2026-10-01T00:00:00Z",
    }),
    fact("vaccine", "2012-06-01", {
      kind: "vaccination",
      label: "MMR",
      available_at: "2026-10-28T00:00:00Z",
    }),
    fact("lab", "2026-10-01"),
  ]);
  const before = JSON.stringify(records);
  const days = recordDays(records);
  assert.deepEqual(
    days.map((day) => [day.date, day.facts.length]),
    [
      ["2026-10-01", 2],
      ["2012-06-01", 1],
    ],
  );
  assert.equal(JSON.stringify(records), before);
});

test("comparison summaries resolve only facts in the captured view", () => {
  const records = view(
    [fact("a", "2021-04-08"), fact("b", "2021-04-08", { value: "96" })],
    {
      conflicts: [
        { id: "visible", fact_ids: ["a", "b"] },
        { id: "outside", fact_ids: ["a", "missing"] },
      ],
    },
  );
  const groups = scopedDifferences(records);
  assert.deepEqual(
    groups.map((group) => group.id),
    ["visible"],
  );
  assert.equal(groups[0].facts[0], records.facts[0]);
});
