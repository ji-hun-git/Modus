export function historyQuestionKey(scope, compareFrom = null) {
  return JSON.stringify([
    scope.as_of,
    scope.known_at,
    scope.scope_id,
    compareFrom,
  ]);
}

export function historyQuestionRequest(scope, message, compareFrom = null) {
  return {
    as_of: scope.as_of,
    known_at: scope.known_at,
    ...(compareFrom ? { compare_from: compareFrom } : {}),
    message: message.trim(),
  };
}

// Bounds come from server-captured views, in the server's canonical form.
// Do not accept a response with broader dates or a different availability.
export function historyAnswerMatches(answer, scope, compareFrom = null) {
  const same = (other) =>
    other?.as_of === scope.as_of && other?.known_at === scope.known_at;
  if (!same(answer.scope) || !same(answer.history_evidence?.scope))
    return false;
  if (!compareFrom) return !answer.history_comparison;
  return (
    same(answer.history_comparison?.after) &&
    answer.history_comparison?.before?.as_of === scope.as_of &&
    answer.history_comparison?.before?.known_at === compareFrom
  );
}

export function historyClaimEvidence(view, evidenceIds) {
  const ids = new Set(evidenceIds);
  const facts = [...view.facts, ...view.undated_facts].filter(
    (fact) => ids.has(fact.id) || ids.has(fact.source_id),
  );
  const sourceIds = new Set(facts.map((fact) => fact.source_id));
  return view.sources
    .filter((source) => sourceIds.has(source.id))
    .map((source) => ({
      source,
      facts: facts.filter((fact) => fact.source_id === source.id),
    }));
}
