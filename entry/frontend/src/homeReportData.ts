import type { HistoryFact, HistoryView } from "./historyTypes";

export type HomeReportSummary = {
  source: HistoryView["sources"][number];
  facts: HistoryFact[];
  latestDate: string | null;
};

function validDate(value: string | null | undefined): value is string {
  if (!value || !/^(?!0000)\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const time = Date.parse(`${value}T00:00:00Z`);
  return (
    Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === value
  );
}

function scopedFacts(view: HistoryView): HistoryFact[] {
  const sourceIds = new Set(view.sources.map((source) => source.id));
  const seen = new Set<string>();
  return [...view.facts, ...view.undated_facts].filter((fact) => {
    // A retained duplicate cannot restore fields hidden in the current view.
    if (seen.has(fact.id)) return false;
    seen.add(fact.id);
    return sourceIds.has(fact.source_id) && fact.within_date_scope !== false;
  });
}

export function reportSummaries(view: HistoryView): HomeReportSummary[] {
  const visible = scopedFacts(view);
  return view.sources
    .map((source) => {
      const facts = visible.filter((fact) => fact.source_id === source.id);
      const dates = facts.flatMap((fact) =>
        validDate(fact.date) ? [fact.date] : [],
      );
      return { source, facts, latestDate: dates.sort().at(-1) ?? null };
    })
    .sort((a, b) => {
      if (a.latestDate === null && b.latestDate !== null) return 1;
      if (a.latestDate !== null && b.latestDate === null) return -1;
      return (
        (b.latestDate ?? "").localeCompare(a.latestDate ?? "") ||
        a.source.id.localeCompare(b.source.id)
      );
    });
}

export function isLatestReport(
  reports: readonly HomeReportSummary[],
  report: HomeReportSummary | null | undefined,
): boolean {
  const current =
    report && reports.find((item) => item.source.id === report.source.id);
  return !!current?.latestDate && current.latestDate === reports[0]?.latestDate;
}

// Chronological order, including every source on a date. Comparison remains
// exact-label/exact-kind; unit differences and withheld values stay visible.
export function recordHistory(
  view: HistoryView,
  fact: HistoryFact,
): HistoryFact[] {
  const visible = scopedFacts(view);
  const current = visible.find(
    (item) => item.id === fact.id && item.source_id === fact.source_id,
  );
  if (!current || !validDate(current.date)) return [];
  const date = current.date;
  return visible
    .filter(
      (item) =>
        item.label === current.label &&
        item.kind === current.kind &&
        validDate(item.date) &&
        item.date <= date,
    )
    .sort((a, b) => a.date!.localeCompare(b.date!) || a.id.localeCompare(b.id));
}

export function previousRecords(
  view: HistoryView,
  fact: HistoryFact,
): HistoryFact[] {
  const history = recordHistory(view, fact);
  const current = history.find(
    (item) => item.id === fact.id && item.source_id === fact.source_id,
  );
  if (!current) return [];
  const earlier = history.filter((item) => item.date! < current.date!);
  const previousDate = earlier.at(-1)?.date;
  return previousDate
    ? earlier.filter((item) => item.date === previousDate)
    : [];
}
