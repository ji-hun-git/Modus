// Preserve server-captured timestamps verbatim, including microseconds.
export function replayRequest(scope) {
  return {
    as_of: scope.as_of,
    before_known_at: scope.known_at,
    after_known_at: null,
  };
}

export function replayMatchesRequest(comparison, request) {
  return (
    comparison?.format === "modus-history-comparison-v1" &&
    comparison.before?.scope?.as_of === request.as_of &&
    comparison.after?.scope?.as_of === request.as_of &&
    comparison.before?.scope?.known_at === request.before_known_at &&
    comparison.after?.scope?.known_at === comparison.captured_at
  );
}
