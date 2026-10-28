import { useState } from "react";
import type { Observation } from "./types";
import { dateLabel } from "./ui";
import { buildHistorySeries } from "./historyGeometry";
import "./history-plot.css";

export default function HistoryPlot({
  observations,
  disputedIds,
  label,
  onInspect,
}: {
  observations: Observation[];
  disputedIds: ReadonlySet<string>;
  label: string;
  onInspect: (ids: string[]) => void;
}) {
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const series = buildHistorySeries(observations, disputedIds);
  const active = series
    .flatMap((item) => item.points)
    .find((point) => point.key === activeKey);
  const dates = observations.map((item) => item.date).sort();
  if (!observations.length) return null;
  if (!series.length)
    return (
      <p className="history-plot-unavailable">
        Open history to inspect the recorded values.
      </p>
    );
  const first = dates[0];
  const last = dates[dates.length - 1];
  return (
    <div className="history-plot" aria-label={`${label} recorded values`}>
      <div className="history-plot-caption">
        <span>Recorded values</span>
        <span>
          {observations.length}{" "}
          {observations.length === 1 ? "reading" : "readings"}
        </span>
      </div>
      {series.map((item) => (
        <div className="history-plot-series" key={item.unit}>
          {series.length > 1 && (
            <span className="history-plot-unit">{item.unit}</span>
          )}
          <div className="history-plot-canvas">
            <svg
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              {[20, 50, 80].map((y) => (
                <line
                  key={y}
                  x1="0"
                  x2="100"
                  y1={y}
                  y2={y}
                  className="history-plot-grid"
                />
              ))}
              {item.segments.map(({ from, to }) => (
                <line
                  key={`${from.key}-${to.key}`}
                  x1={from.x}
                  y1={from.y}
                  x2={to.x}
                  y2={to.y}
                  className="history-plot-connection"
                />
              ))}
              {item.points.map((point) => (
                <line
                  key={point.key}
                  x1={point.x}
                  x2={point.x}
                  y1={point.y}
                  y2="94"
                  className="history-plot-guide"
                />
              ))}
            </svg>
            {item.points.map((point) => (
              <button
                type="button"
                key={point.key}
                className={`history-plot-point${point.disputed ? " disputed" : ""}${active?.key === point.key ? " selected" : ""}`}
                style={{ left: `${point.x}%`, top: `${point.y}%` }}
                onMouseEnter={() => setActiveKey(point.key)}
                onMouseLeave={() => setActiveKey(null)}
                onFocus={() => setActiveKey(point.key)}
                onBlur={() => setActiveKey(null)}
                onClick={() =>
                  onInspect(point.observations.map((row) => row.id))
                }
                aria-haspopup="dialog"
                aria-label={`${label}, ${point.value} ${point.unit}, measured ${dateLabel(point.date)}${point.disputed ? ", different values recorded" : ""}. Open ${point.observations.length === 1 ? "source" : `${point.observations.length} sources`}`}
              >
                <span className="history-plot-dot" />
                {point.observations.length > 1 && (
                  <span className="history-plot-source-count">
                    {point.observations.length}
                  </span>
                )}
              </button>
            ))}
            {active?.unit === item.unit && (
              <div className="history-plot-tooltip" aria-hidden="true">
                <span>{dateLabel(active.date)}</span>
                <strong>
                  {active.value} <small>{active.unit}</small>
                </strong>
                {active.disputed && <span>Different values recorded</span>}
              </div>
            )}
          </div>
        </div>
      ))}
      <div
        className={`history-plot-dates${first === last ? " single-date" : ""}`}
      >
        <span>{dateLabel(first)}</span>
        {first !== last && <span>{dateLabel(last)}</span>}
      </div>
      {series.some((item) => item.points.some((point) => point.disputed)) && (
        <div className="history-plot-legend">
          <span aria-hidden="true" /> Different values recorded
        </div>
      )}
    </div>
  );
}
