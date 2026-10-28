export const MAX_BRIEF_SELECTION = 80;

export function eligibleBriefFacts(view) {
  return [...view.facts, ...view.undated_facts].filter(
    (fact) =>
      !fact.value_withheld &&
      fact.value !== null &&
      fact.within_date_scope !== false,
  );
}

export function briefRequest(view, selectedIds, title, ownerNote) {
  const allowed = new Set(eligibleBriefFacts(view).map((fact) => fact.id));
  const selected = [...new Set(selectedIds)].sort();
  if (
    !selected.length ||
    selected.length > MAX_BRIEF_SELECTION ||
    selected.some((id) => !allowed.has(id)) ||
    !title.trim() ||
    title.length > 100 ||
    ownerNote.length > 1200
  )
    return null;
  return {
    as_of: view.scope.as_of,
    known_at: view.scope.known_at,
    selected_fact_ids: selected,
    title: title.trim(),
    owner_note: ownerNote,
  };
}

export function briefRequestKey(view, selectedIds, title, ownerNote) {
  return JSON.stringify([
    view.scope.as_of,
    view.scope.known_at,
    view.scope.scope_id,
    [...new Set(selectedIds)].sort(),
    title,
    ownerNote,
  ]);
}

export function briefMatchesRequest(brief, request) {
  if (!request || brief.format !== "modus-record-brief-v1") return false;
  const sameScope = (scope) =>
    scope?.as_of === request.as_of && scope?.known_at === request.known_at;
  if (
    !sameScope(brief.scope) ||
    !sameScope(brief.history_evidence?.scope) ||
    brief.title !== request.title ||
    brief.owner_note !== request.owner_note ||
    !brief.preview_id ||
    !Array.isArray(brief.entries)
  )
    return false;
  const chosen = brief.entries
    .filter((entry) => entry.selected_by_owner)
    .map((entry) => entry.id)
    .sort();
  return (
    JSON.stringify(chosen) === JSON.stringify(request.selected_fact_ids) &&
    brief.entries.length === brief.counts?.total &&
    chosen.length === brief.counts?.selected
  );
}

export function reviewedBriefExport(brief, request, reviewed, format = "html") {
  if (!reviewed || !briefMatchesRequest(brief, request)) return null;
  if (format !== "html" && format !== "json") return null;
  return { ...request, preview_id: brief.preview_id, reviewed: true, format };
}
