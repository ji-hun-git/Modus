import type { HistoryFact } from "./historyTypes";
import { buildHistorySeries } from "./historyGeometry";

export type RecordedPlotRow = {
  id: string;
  date: string;
  value: number;
  unit: string;
  source_id: string;
  fact: HistoryFact;
};

// Compare decimal meaning without expanding exponents or changing the saved text.
// Ordinary decimals can use Number geometry, but a conversion must not round away
// printed digits, turn a nonzero value into zero, or exceed safe integer precision.
function decimalIdentity(raw: string): string | null {
  const match = raw.match(
    /^([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d+))?$/,
  );
  if (!match) return null;
  const fraction = match[3] ?? match[4] ?? "";
  const digits = ((match[2] ?? "") + fraction).replace(/^0+/, "");
  if (!digits) return "0";
  const exponent = Number(match[5] ?? "0");
  if (!Number.isSafeInteger(exponent)) return null;
  const significant = digits.replace(/0+$/, "");
  const scale = exponent - fraction.length + digits.length - significant.length;
  return `${match[1] === "-" ? "-" : ""}${significant}e${scale}`;
}

// The fact retains its printed precision. Values unsuitable for numeric geometry,
// inequalities, text, partial dates and withheld fields remain in the history.
export function recordedSeries(
  facts: HistoryFact[],
  sourceIds: ReadonlySet<string>,
  disputedIds: ReadonlySet<string>,
) {
  if (new Set(facts.map((fact) => fact.label)).size > 1)
    return { series: [], plotted: 0, omitted: facts.length };
  const rows: RecordedPlotRow[] = [];
  for (const fact of facts) {
    if (
      fact.kind !== "measurement" ||
      !sourceIds.has(fact.source_id) ||
      fact.value_withheld ||
      fact.within_date_scope === false ||
      !fact.date ||
      !/^(?!0000)\d{4}-\d{2}-\d{2}$/.test(fact.date) ||
      fact.value == null ||
      !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(fact.value.trim())
    )
      continue;
    const date = Date.parse(`${fact.date}T00:00:00Z`);
    const value = Number(fact.value);
    if (
      !Number.isFinite(date) ||
      new Date(date).toISOString().slice(0, 10) !== fact.date ||
      !Number.isFinite(value) ||
      (Number.isInteger(value) && !Number.isSafeInteger(value)) ||
      decimalIdentity(fact.value.trim()) !== decimalIdentity(String(value))
    )
      continue;
    rows.push({
      id: fact.id,
      date: fact.date,
      value,
      unit: fact.unit ?? "",
      source_id: fact.source_id,
      fact,
    });
  }
  const series = buildHistorySeries(rows, disputedIds).filter(
    (group) =>
      group.points.length > 0 &&
      group.points.every(
        (point) =>
          Number.isFinite(point.value) &&
          Number.isFinite(point.x) &&
          Number.isFinite(point.y),
      ),
  );
  const plotted = series.reduce(
    (total, group) =>
      total + group.points.reduce((count, point) => count + point.observations.length, 0),
    0,
  );
  return { series, plotted, omitted: facts.length - plotted };
}
