import type { HistoryFact, HistoryView } from "./historyTypes";

export type HomeReportSummary = {
  source: HistoryView["sources"][number];
  facts: HistoryFact[];
  latestDate: string | null;
  count?: number;
  displayLabel?: string;
  dateRange?: string;
};

export function sourceRegion(fact: HistoryFact): number[] | null {
  const box = fact.bbox;
  if (fact.value_withheld || fact.source_quote_withheld || !box || box.length !== 4 ||
      !box.every((v) => Number.isFinite(v) && v >= 0 && v <= 1) ||
      box[0] >= box[2] || box[1] >= box[3]) return null;
  return box;
}

export function recordedDates(view: HistoryView): string[] {
  return [...new Set(view.facts.map((fact) => fact.date).filter(validDate))].sort();
}

export function orbitLayout(reports: HomeReportSummary[]) {
  const eras = [...new Set(reports.flatMap((report) => report.latestDate
    ? [Math.floor(Number(report.latestDate.slice(0, 4)) / 5) * 5] : []))].sort((a, b) => a - b);
  const rings = eras.map((era, index) => ({ era, radius: 184 - index * (72 / Math.max(1, eras.length - 1)),
    label: `${era}–${era + 4}` }));
  const nodes = reports.map((report) => {
    const era = report.latestDate ? Math.floor(Number(report.latestDate.slice(0, 4)) / 5) * 5 : null;
    const ring = rings.find((item) => item.era === era);
    const peers = reports.filter((item) => (item.latestDate ? Math.floor(Number(item.latestDate.slice(0, 4)) / 5) * 5 : null) === era)
      .sort((a, b) => a.source.id.localeCompare(b.source.id));
    const index = peers.findIndex((item) => item.source.id === report.source.id);
    const angle = ((ring ? [145, -145, -35, 45][eras.indexOf(era!) % 4] : 0) + index * 360 / peers.length) * Math.PI / 180;
    return { id: report.source.id, era, x: ring ? 300 + ring.radius * Math.cos(angle) : 90 + index * 420 / Math.max(1, peers.length - 1),
      y: ring ? 222 + ring.radius * Math.sin(angle) : 450 };
  });
  return { rings, nodes };
}

export const dateDay = (value: string) => validDate(value) ? Math.floor(Date.parse(value + 'T00:00:00Z') / 86400000) : null;
export const dayDate = (value: number) => new Date(value * 86400000).toISOString().slice(0, 10);
export function archiveElapsed(first: string | undefined, selected: string): string {
  if (!first || !validDate(first) || !validDate(selected)) return 'T+ —';
  if (selected < first) return 'BEFORE FIRST RECORD';
  const a = first.split('-').map(Number), b = selected.split('-').map(Number);
  const months = (b[0] - a[0]) * 12 + b[1] - a[1] - (b[2] < a[2] ? 1 : 0);
  return `T+ ${String(Math.floor(months / 12)).padStart(2, '0')}Y ${String(months % 12).padStart(2, '0')}M`;
}

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
  if (view.page?.section === 'sources') return view.sources.map(source => ({source, facts: [],
    latestDate: source.latest_date || null, count: source.fact_count || 0, displayLabel: source.display_label,
    dateRange: source.first_date ? `${source.first_date}${source.latest_date !== source.first_date ? ` – ${source.latest_date}` : ''}${source.has_undated ? ' · includes partial or unknown dates' : ''}` : 'Date not fully recorded'}));
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
