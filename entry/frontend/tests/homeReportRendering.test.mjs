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
const { HomeReportComparison, HomeHistoryTrail, HomeSourceEvidence } =
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
