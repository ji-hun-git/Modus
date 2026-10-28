import { factKindLabels } from "./historyTypes";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { recordLabel } from "./types";
import { dateLabel } from "./ui";
export const recordedDate = (fact: HistoryFact) =>
  fact.date ? dateLabel(fact.date) : fact.occurred_on || "Date not recorded";
export function sourceTitle(facts: HistoryFact[]): string {
  if (!facts.length) return "Uploaded record";
  const labels = [...new Set(facts.map((fact) => recordLabel(fact.label)))];
  const kinds = [...new Set(facts.map((fact) => fact.kind))];
  if (labels.length === 1) return labels[0];
  if (kinds.length !== 1) return "Health records";
  if (kinds[0] === "measurement") return "Measurements";
  return `${factKindLabels[kinds[0]]} records`;
}
export function sourceDateRange(facts: HistoryFact[]): string {
  const dates = [
    ...new Set(
      facts.flatMap((fact) => {
        if (fact.date) return [fact.date];
        // Keep partial precision; do not assign a month/day to a year-only record.
        const raw = fact.occurred_on || "";
        return /^(?!0000)\d{4}(?:-(?:0[1-9]|1[0-2]))?$/.test(raw) ? [raw] : [];
      }),
    ),
  ].sort();
  if (!dates.length)
    return facts.length === 1
      ? recordedDate(facts[0])
      : facts.some((fact) => fact.occurred_on)
        ? "Recorded dates need review"
        : "Date not recorded";
  const label = (value: string) =>
    value.length === 10 ? dateLabel(value) : value;
  const range =
    dates.length === 1
      ? label(dates[0])
      : `${label(dates[0])} – ${label(dates.at(-1)!)}`;
  const unknown = facts.some(
    (fact) =>
      !fact.date &&
      !/^(?!0000)\d{4}(?:-(?:0[1-9]|1[0-2]))?$/.test(fact.occurred_on || ""),
  );
  return range + (unknown ? " · includes undated records" : "");
}
export function originalDownloadUrl(
  sourceId: string,
  scope: HistoryView["scope"],
): string {
  const query = new URLSearchParams({ known_at: scope.known_at });
  if (scope.as_of !== null) query.set("as_of", scope.as_of);
  return `/api/history/sources/${encodeURIComponent(sourceId)}/original?${query}`;
}
const reviewedFieldNames: Record<string, string> = {
  label: "name",
  value: "value",
  unit: "unit",
  occurred_on: "recorded date",
  facility: "facility",
  kind: "record type",
};
export const reviewedFieldLabel = (field: string) =>
  reviewedFieldNames[field] || field;
export const sourcePage = (
  fact: HistoryFact,
  source?: HistoryView["sources"][number],
) =>
  source &&
  (/\.csv$/i.test(source.title) || source.type.toLowerCase() === "csv")
    ? null
    : fact.page;
export const sourceExcerpt = (fact: HistoryFact) =>
  fact.source_quote_withheld
    ? "This excerpt may include information outside the selected dates and is hidden in this view."
    : fact.source_quote ||
      "No excerpt was saved. Check the original for more detail.";
