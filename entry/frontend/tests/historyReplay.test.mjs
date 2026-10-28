import test from "node:test";
import assert from "node:assert/strict";
import { replayRequest, replayMatchesRequest } from "../src/historyReplay.mjs";

const scope = {
  as_of: null,
  known_at: "2026-10-29T03:14:15.123456+00:00",
  scope_id: "before",
};
const captured = "2026-10-29T03:14:15.123457+00:00";
const result = () => ({
  format: "modus-history-comparison-v1",
  before: { scope: { ...scope } },
  after: { scope: { ...scope, known_at: captured } },
  captured_at: captured,
});

test("save comparison retains the captured microsecond and all-recorded-dates bound", () => {
  const displayed = { ...scope };
  const request = replayRequest(displayed);
  displayed.known_at = captured;
  assert.deepEqual(request, {
    as_of: null,
    before_known_at: scope.known_at,
    after_known_at: null,
  });
  assert.equal(replayMatchesRequest(result(), request), true);
});

test("a refreshed later view cannot silently replace the pre-save baseline", () => {
  const request = replayRequest(scope);
  const refreshed = result();
  refreshed.before.scope.known_at = captured;
  assert.equal(replayMatchesRequest(refreshed, request), false);
});

test("comparison rejects a changed occurrence cutoff on either side", () => {
  for (const side of ["before", "after"]) {
    const changed = result();
    changed[side].scope.as_of = "2026-10-29";
    assert.equal(replayMatchesRequest(changed, replayRequest(scope)), false);
  }
  const bounded = { ...scope, as_of: "2020-12-31" };
  assert.equal(replayRequest(bounded).as_of, "2020-12-31");
});

test("the later side must be the captured availability returned for a now request", () => {
  const changed = result();
  changed.after.scope.known_at = "2026-10-30T00:00:00.000000+00:00";
  assert.equal(replayMatchesRequest(changed, replayRequest(scope)), false);
});
