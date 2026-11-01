import type { FactKind, HistoryFact, HistoryView } from "./historyTypes";
import { reportSummaries } from "./homeReportData";

export type HistoryField = { key: string; kind: FactKind; label: string; facts: HistoryFact[] };

// Only current scoped facts can create a selector option. Keep exact labels,
// kinds, units and ties; similar wording never authorizes combining records.
export function historyFields(view: HistoryView): HistoryField[] {
  const groups = new Map<string, HistoryField>();
  for (const fact of reportSummaries(view).flatMap((report) => report.facts)) {
    const key = JSON.stringify([fact.kind, fact.label]);
    const group = groups.get(key) || { key, kind: fact.kind, label: fact.label, facts: [] };
    group.facts.push(fact);
    groups.set(key, group);
  }
  return [...groups.values()].map((group) => ({ ...group, facts: group.facts.sort((a, b) =>
    (b.date || "").localeCompare(a.date || "") || a.id.localeCompare(b.id)) }))
    .sort((a, b) => a.kind.localeCompare(b.kind) || a.label.localeCompare(b.label) || a.key.localeCompare(b.key));
}
