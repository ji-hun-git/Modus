import type { Observation } from "./types";

export type HistoryPoint = {
  key: string;
  date: string;
  value: number;
  unit: string;
  x: number;
  y: number;
  disputed: boolean;
  observations: Observation[];
};

export type HistorySeries = {
  unit: string;
  points: HistoryPoint[];
  segments: { from: HistoryPoint; to: HistoryPoint }[];
};

const day = (value: string) => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return NaN;
  const timestamp = Date.parse(`${value}T00:00:00Z`);
  return Number.isFinite(timestamp) &&
    new Date(timestamp).toISOString().slice(0, 10) === value
    ? timestamp
    : NaN;
};

/** Display geometry only: preserve every source, never convert units or infer a reading. */
export function buildHistorySeries(
  observations: Observation[],
  disputedIds: ReadonlySet<string> = new Set(),
): HistorySeries[] {
  if (!observations.length) return [];
  // An invalid record is left to the text/source view rather than drawn at a guessed position.
  if (
    observations.some(
      (item) =>
        !Number.isFinite(item.value) || !Number.isFinite(day(item.date)),
    )
  )
    return [];
  const ordered = [...observations].sort(
    (a, b) => a.date.localeCompare(b.date) || a.id.localeCompare(b.id),
  );
  const first = day(ordered[0].date);
  const last = day(ordered[ordered.length - 1].date);
  const byDate = new Map<string, Set<string>>();
  for (const item of ordered) {
    const values = byDate.get(item.date) || new Set<string>();
    values.add(JSON.stringify([item.value, item.unit]));
    byDate.set(item.date, values);
  }
  const allDates = [...byDate.keys()];
  const units = [...new Set(ordered.map((item) => item.unit))];
  return units.map((unit) => {
    const rows = ordered.filter((item) => item.unit === unit);
    const low = Math.min(...rows.map((item) => item.value));
    const high = Math.max(...rows.map((item) => item.value));
    const groups = new Map<string, Observation[]>();
    for (const item of rows) {
      const key = JSON.stringify([item.date, item.value, item.unit]);
      groups.set(key, [...(groups.get(key) || []), item]);
    }
    const points = [...groups.entries()].map(([key, items]): HistoryPoint => {
      const item = items[0];
      return {
        key,
        date: item.date,
        value: item.value,
        unit,
        x:
          first === last
            ? 50
            : 9 + ((day(item.date) - first) / (last - first)) * 82,
        y: low === high ? 50 : 20 + ((high - item.value) / (high - low)) * 60,
        disputed:
          (byDate.get(item.date)?.size || 0) > 1 ||
          items.some((row) => disputedIds.has(row.id)),
        observations: items,
      };
    });
    const segments: HistorySeries["segments"] = [];
    for (let index = 1; index < points.length; index++) {
      const from = points[index - 1];
      const to = points[index];
      // Never draw through a disagreement, mixed-unit date or intervening incompatible record.
      if (
        !from.disputed &&
        !to.disputed &&
        allDates.indexOf(to.date) === allDates.indexOf(from.date) + 1
      )
        segments.push({ from, to });
    }
    return { unit, points, segments };
  });
}
