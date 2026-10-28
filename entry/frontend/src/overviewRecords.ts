import type { HistoryFact, HistoryView } from "./historyTypes";

export type MeasurementSummary = {
  label: string;
  date: string;
  latest: HistoryFact[];
  history: HistoryFact[];
  conflictIds: string[];
};

// Use the server's exact occurrence date. Upload timestamps and unresolved text
// never become dates or decide which recorded result is latest.
export function datedRecords(view: HistoryView) {
  const sources = new Set(view.sources.map((source) => source.id));
  return view.facts
    .filter((fact) => !!fact.date && sources.has(fact.source_id))
    .sort((a, b) => b.date!.localeCompare(a.date!) || a.id.localeCompare(b.id));
}

export function currentOverviewFacts(view: HistoryView, ids: string[]) {
  const selected = new Set(ids);
  const sources = new Set(view.sources.map((source) => source.id));
  return [...view.facts, ...view.undated_facts].filter(
    (fact) => selected.has(fact.id) && sources.has(fact.source_id),
  );
}

export function latestMeasurements(view: HistoryView): MeasurementSummary[] {
  const groups = new Map<string, HistoryFact[]>();
  for (const fact of datedRecords(view)) {
    if (fact.kind !== "measurement") continue;
    const records = groups.get(fact.label) || [];
    records.push(fact);
    groups.set(fact.label, records);
  }
  return [...groups]
    .map(([label, history]) => {
      const date = history[0].date!;
      const latest = history.filter((fact) => fact.date === date);
      const ids = new Set(latest.map((fact) => fact.id));
      return {
        label,
        date,
        latest,
        history,
        conflictIds: view.conflicts
          .filter((group) => group.fact_ids.some((id) => ids.has(id)))
          .map((group) => group.id),
      };
    })
    .sort(
      (a, b) => b.date.localeCompare(a.date) || a.label.localeCompare(b.label),
    );
}

export function recordDays(view: HistoryView) {
  const days = new Map<string, HistoryFact[]>();
  for (const fact of datedRecords(view)) {
    const records = days.get(fact.date!) || [];
    records.push(fact);
    days.set(fact.date!, records);
  }
  return [...days].map(([date, facts]) => ({ date, facts }));
}

export function scopedDifferences(view: HistoryView) {
  const facts = [...view.facts, ...view.undated_facts];
  return view.conflicts
    .map((group) => ({
      ...group,
      facts: facts.filter((fact) => group.fact_ids.includes(fact.id)),
    }))
    .filter((group) => group.facts.length >= 2);
}
