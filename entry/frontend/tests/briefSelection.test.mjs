import test from "node:test";
import assert from "node:assert/strict";
import {
  briefRequest,
  briefRequestKey,
  briefMatchesRequest,
  reviewedBriefExport,
  eligibleBriefFacts,
} from "../src/briefSelection.mjs";

const scope = {
  as_of: null,
  known_at: "2026-10-28T12:00:00.123456Z",
  scope_id: "captured",
};
const view = {
  scope,
  facts: [
    { id: "height", value: "112.50", unit: "cm" },
    { id: "hidden", value: null, value_withheld: true },
  ],
  undated_facts: [
    { id: "vaccine", occurred_on: "2012", value: "Recorded dose" },
  ],
};
const request = briefRequest(
  view,
  ["height", "vaccine"],
  "My records",
  "A note from me",
);
const brief = {
  format: "modus-record-brief-v1",
  preview_id: "sha256:example",
  scope,
  title: "My records",
  owner_note: "A note from me",
  history_evidence: { scope },
  entries: [
    { id: "height", selected_by_owner: true },
    { id: "vaccine", selected_by_owner: true },
    { id: "companion", selected_by_owner: false, added_for_conflict: true },
  ],
  counts: { selected: 2, total: 3, conflict_companions: 1 },
};

test("selection starts empty and unavailable facts cannot enter a brief", () => {
  assert.equal(briefRequest(view, [], "Record brief", ""), null);
  assert.equal(briefRequest(view, ["hidden"], "Record brief", ""), null);
  assert.equal(briefRequest(view, ["another-view"], "Record brief", ""), null);
  assert.deepEqual(
    eligibleBriefFacts(view).map((fact) => fact.id),
    ["height", "vaccine"],
  );
});

test("visible values outside the captured date scope cannot be selected", () => {
  const boundedView = {
    ...view,
    scope: { ...scope, as_of: "2020-12-31" },
    undated_facts: [
      ...view.undated_facts,
      {
        id: "unknown-date",
        value: "Recorded visit",
        occurred_on: null,
        within_date_scope: false,
      },
    ],
  };
  assert.deepEqual(
    eligibleBriefFacts(boundedView).map((fact) => fact.id),
    ["height", "vaccine"],
  );
  assert.equal(
    briefRequest(boundedView, ["height", "unknown-date"], "Record brief", ""),
    null,
  );
  assert.ok(briefRequest(boundedView, ["height"], "Record brief", ""));
});

test("request keeps all-date and exact availability bounds with explicit IDs", () => {
  assert.equal(request.as_of, null);
  assert.equal(request.known_at, scope.known_at);
  assert.deepEqual(request.selected_fact_ids, ["height", "vaccine"]);
  assert.deepEqual(
    briefRequest(view, ["height", "height"], " Record brief ", "")
      .selected_fact_ids,
    ["height"],
  );
  assert.equal(view.facts[0].value, "112.50");
  assert.equal(view.undated_facts[0].occurred_on, "2012");
});

test("preview accepts explicit conflict companions but rejects a changed selection", () => {
  assert.ok(briefMatchesRequest(brief, request));
  assert.equal(
    briefMatchesRequest(
      {
        ...brief,
        entries: [
          ...brief.entries,
          { id: "unselected", selected_by_owner: true },
        ],
      },
      request,
    ),
    false,
  );
  assert.equal(
    briefMatchesRequest(
      { ...brief, counts: { ...brief.counts, total: 5 } },
      request,
    ),
    false,
  );
});

test("review and exact preview are required before download", () => {
  assert.equal(reviewedBriefExport(brief, request, false), null);
  assert.equal(
    reviewedBriefExport(brief, { ...request, owner_note: "Changed" }, true),
    null,
  );
  assert.equal(
    reviewedBriefExport(brief, { ...request, title: "Changed" }, true),
    null,
  );
  assert.deepEqual(reviewedBriefExport(brief, request, true), {
    ...request,
    reviewed: true,
    preview_id: brief.preview_id,
    format: "html",
  });
});

test("scope changes and delayed response bounds invalidate the brief", () => {
  const earlier = { ...view, scope: { ...scope, as_of: "2021-12-31" } };
  assert.notEqual(
    briefRequestKey(view, ["height"], "Record brief", ""),
    briefRequestKey(earlier, ["height"], "Record brief", ""),
  );
  assert.equal(
    briefMatchesRequest(
      { ...brief, scope: { ...scope, known_at: "2026-10-29T12:00:00Z" } },
      request,
    ),
    false,
  );
  assert.equal(
    briefMatchesRequest(
      {
        ...brief,
        history_evidence: { scope: { ...scope, as_of: "2025-01-01" } },
      },
      request,
    ),
    false,
  );
});

test("selection and text limits reject oversized requests instead of truncation", () => {
  const largeView = {
    scope,
    facts: Array.from({ length: 81 }, (_, i) => ({
      id: String(i),
      value: "1",
    })),
    undated_facts: [],
  };
  assert.equal(
    briefRequest(
      largeView,
      largeView.facts.map((f) => f.id),
      "Record brief",
      "",
    ),
    null,
  );
  assert.equal(briefRequest(view, ["height"], " ", ""), null);
  assert.equal(briefRequest(view, ["height"], "x".repeat(101), ""), null);
  assert.equal(
    briefRequest(view, ["height"], "Record brief", "x".repeat(1201)),
    null,
  );
});
