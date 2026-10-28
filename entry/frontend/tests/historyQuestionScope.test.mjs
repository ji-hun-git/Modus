import test from "node:test";
import assert from "node:assert/strict";
import {
  historyQuestionKey,
  historyQuestionRequest,
  historyAnswerMatches,
  historyClaimEvidence,
} from "../src/historyQuestionScope.mjs";

const scope = {
  as_of: null,
  known_at: "2026-10-28T09:30:00.000000Z",
  captured_at: "2026-10-28T09:30:00.000000Z",
  scope_id: "current",
};
const history = {
  scope,
  facts: [
    { id: "fact-a", source_id: "source-a", value: "12.30" },
    { id: "fact-b", source_id: "source-b", value: null, value_withheld: true },
  ],
  undated_facts: [{ id: "fact-c", source_id: "source-c", occurred_on: "2012" }],
  sources: [{ id: "source-a" }, { id: "source-b" }, { id: "source-c" }],
};
const answer = { scope, history_evidence: history };

test("all-date requests preserve null and captured availability rather than using today", () => {
  assert.deepEqual(
    historyQuestionRequest(scope, "  Show my prescription records  "),
    {
      as_of: null,
      known_at: scope.known_at,
      message: "Show my prescription records",
    },
  );
});
test("historical requests never widen to all dates and compare only when selected", () => {
  const old = { ...scope, as_of: "2021-12-31" };
  const request = historyQuestionRequest(
    old,
    "What arrived?",
    "2020-12-31T23:59:59.999999Z",
  );
  assert.equal(request.as_of, "2021-12-31");
  assert.equal(request.known_at, scope.known_at);
  assert.equal(request.compare_from, "2020-12-31T23:59:59.999999Z");
  assert.ok(!("compare_from" in historyQuestionRequest(old, "Show records")));
});
test("request identity changes on date, availability, comparison or bundle view changes", () => {
  const key = historyQuestionKey(scope);
  for (const change of [
    { as_of: "2021-12-31" },
    { known_at: "2021-12-31T23:59:59.000000Z" },
    { scope_id: "new-bundle" },
  ])
    assert.notEqual(historyQuestionKey({ ...scope, ...change }), key);
  assert.notEqual(
    historyQuestionKey(scope, "2021-12-31T23:59:59.999999Z"),
    key,
  );
});
test("answer and evidence must match the displayed temporal bounds independently", () => {
  assert.equal(historyAnswerMatches(answer, scope), true);
  assert.equal(
    historyAnswerMatches(
      { ...answer, scope: { ...scope, as_of: "2021-12-31" } },
      scope,
    ),
    false,
  );
  assert.equal(
    historyAnswerMatches(
      {
        ...answer,
        history_evidence: {
          ...history,
          scope: { ...scope, known_at: "2026-10-29T09:30:00.000000Z" },
        },
      },
      scope,
    ),
    false,
  );
  assert.equal(
    historyAnswerMatches(
      {
        ...answer,
        scope: { ...scope, known_at: "2026-10-28T09:30:00.000001Z" },
      },
      scope,
    ),
    false,
  );
});
test("unrequested comparison or changed before bound rejects rather than relabelling a response", () => {
  const before = { ...scope, known_at: "2021-12-31T23:59:59.999999Z" };
  const compared = { ...answer, history_comparison: { before, after: scope } };
  assert.equal(historyAnswerMatches(compared, scope), false);
  assert.equal(historyAnswerMatches(compared, scope, before.known_at), true);
  assert.equal(
    historyAnswerMatches(compared, scope, "2020-12-31T23:59:59.999999Z"),
    false,
  );
});
test("source inspector uses only answer evidence and retains withholding and partial dates", () => {
  assert.deepEqual(
    historyClaimEvidence(history, ["outside-fact", "outside-source"]),
    [],
  );
  assert.deepEqual(historyClaimEvidence(history, ["fact-b"])[0].facts, [
    history.facts[1],
  ]);
  assert.equal(
    historyClaimEvidence(history, ["source-c"])[0].facts[0].occurred_on,
    "2012",
  );
  assert.deepEqual(
    historyClaimEvidence(history, ["fact-a"]).map((x) => x.source.id),
    ["source-a"],
  );
});
