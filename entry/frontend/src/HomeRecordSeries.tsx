import { useEffect, useRef, useState } from "react";
import type { HistoryFact } from "./historyTypes";
import { recordedSeries } from "./homeSeriesData";
import { dateLabel } from "./ui";
import { unitLabel } from "./recordPresentation.mjs";

export default function HomeRecordSeries({
  facts,
  label,
  sourceIds,
  disputedIds,
  onSelect,
}: {
  facts: HistoryFact[];
  label: string;
  sourceIds: ReadonlySet<string>;
  disputedIds: ReadonlySet<string>;
  onSelect: (facts: HistoryFact[]) => void;
}) {
  const [active, setActive] = useState<string | null>(null);
  const chart = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const element = chart.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) =>
      setWidth(entry.contentRect.width),
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [facts]);
  const { series, plotted, omitted } = recordedSeries(
    facts,
    sourceIds,
    disputedIds,
  );
  if (!series.length)
    return (
      <div className="home-series-empty">
        No dated numeric series. Open history for the recorded details.
      </div>
    );
  const dates = series
    .flatMap((group) => group.points.map((point) => point.date))
    .sort();
  return (
    <div
      ref={chart}
      className="home-record-series"
      aria-label={`${label} recorded history`}
    >
      {series.map((group) => {
        const selected = group.points.find((point) => point.key === active);
        const minimum = Math.min(...group.points.map((point) => point.value));
        const maximum = Math.max(...group.points.map((point) => point.value));
        const labels = group.points.map((point) => {
          const text = [
            ...new Set(point.observations.map((row) => row.fact.value!.trim())),
          ].join(" / ");
          const halfWidth = (text.length * 11 + 16) / 2;
          const center = (point.x * width) / 100;
          return {
            key: point.key,
            text,
            left: center - halfWidth,
            right: center + halfWidth,
          };
        });
        const labelKeys = new Set(
          labels
            .filter(
              (label) =>
                group.points.length <= 6 &&
                width > 0 &&
                label.left >= 0 &&
                label.right <= width &&
                labels.every(
                  (other) =>
                    other.key === label.key ||
                    label.right + 8 < other.left ||
                    other.right + 8 < label.left,
                ),
            )
            .map((label) => label.key),
        );
        return (
          <div className="home-series-unit" key={group.unit}>
            <div className="home-series-caption">
              <span>
                {group.points.length} points ·{" "}
                {unitLabel(group.unit) || "Unit not recorded"}
              </span>
              <span>
                Scale{" "}
                {minimum === maximum ? minimum : `${minimum} – ${maximum}`}
              </span>
            </div>
            <div className="home-series-canvas">
              <svg
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                aria-hidden="true"
              >
                {[20, 50, 80].map((y) => (
                  <line key={y} x1="9" x2="91" y1={y} y2={y} />
                ))}
                {group.points.map((point) => (
                  <line
                    className="home-series-stem"
                    key={point.key}
                    x1={point.x}
                    x2={point.x}
                    y1={point.y}
                    y2="94"
                  />
                ))}
              </svg>
              {group.points.map((point) => (
                <button
                  key={point.key}
                  type="button"
                  className={`home-series-point${point.disputed ? " is-disputed" : ""}${point.key === active ? " is-active" : ""}`}
                  style={{ left: `${point.x}%`, top: `${point.y}%` }}
                  onMouseEnter={() => setActive(point.key)}
                  onMouseLeave={() => setActive(null)}
                  onFocus={() => setActive(point.key)}
                  onBlur={() => setActive(null)}
                  onClick={() =>
                    onSelect(point.observations.map((row) => row.fact))
                  }
                  aria-haspopup="dialog"
                  aria-label={`${label}: ${point.observations.map((row) => `${row.fact.value} ${row.fact.unit || "unit not recorded"}`).join("; ")}, ${dateLabel(point.date)}. ${point.observations.length} source record${point.observations.length === 1 ? "" : "s"}. Open evidence.`}
                >
                  <span aria-hidden="true" />
                  {labelKeys.has(point.key) && (
                    <small
                      className="home-series-value-label"
                      aria-hidden="true"
                    >
                      {labels.find((label) => label.key === point.key)!.text}
                    </small>
                  )}
                </button>
              ))}
            </div>
            {selected && (
              <p className="home-series-readout" aria-hidden="true">
                {dateLabel(selected.date)} ·{" "}
                {selected.observations
                  .map((row) => `${row.fact.value} ${unitLabel(row.fact.unit)}`)
                  .join(" / ")}
              </p>
            )}
          </div>
        );
      })}
      <div className="home-series-dates">
        <time dateTime={dates[0]}>{dateLabel(dates[0])}</time>
        {dates.at(-1) !== dates[0] && (
          <time dateTime={dates.at(-1)}>{dateLabel(dates.at(-1)!)}</time>
        )}
      </div>
      {(omitted > 0 || series.length > 1) && (
        <p className="home-series-note">
          {plotted} plotted
          {omitted
            ? ` · ${omitted} other ${omitted === 1 ? "record" : "records"} in history`
            : ""}
          {series.length > 1 ? " · Each unit has its own scale" : ""}
        </p>
      )}
    </div>
  );
}
