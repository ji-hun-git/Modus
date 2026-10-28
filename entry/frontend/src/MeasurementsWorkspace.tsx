import { useState } from "react";
import { AlertCircle, ArrowUpRight } from "lucide-react";
import { dateLabel, timeLabel } from "./ui";
import { metricLabel, type Observation, type View } from "./types";

export default function MeasurementsWorkspace({
  view,
  onInspect,
}: {
  view: View;
  onInspect: (view: View, ids: string[]) => void;
}) {
  const [metric, setMetric] = useState<Observation["metric"]>("hba1c");
  const readings = view.observations
    .filter((o) => o.metric === metric)
    .sort((a, b) => b.date.localeCompare(a.date) || a.id.localeCompare(b.id));
  const dates = [...new Set(readings.map((reading) => reading.date))];
  return (
    <section
      className="measurements-workspace"
      aria-label="Recorded measurement history"
    >
      <div
        className="metric-selector"
        role="group"
        aria-label="Choose measurement"
      >
        {(["hba1c", "egfr", "ldl"] as const).map((name) => (
          <button
            key={name}
            className={metric === name ? "selected" : ""}
            aria-pressed={metric === name}
            onClick={() => setMetric(name)}
          >
            {metricLabel(name)}
          </button>
        ))}
      </div>
      <div className="measurement-history-heading">
        <div>
          <h2>{metricLabel(metric)}</h2>
        </div>
        <span>
          {readings.length} recorded value{readings.length === 1 ? "" : "s"} ·
          newest first
        </span>
      </div>
      <div className="measurement-history">
        {dates.map((date) => (
          <section className="measurement-day" key={date}>
            <div className="measurement-day-heading">
              <span>Measured</span>
              <h3>{dateLabel(date)}</h3>
            </div>
            <div className="measurement-day-readings">
              {readings
                .filter((reading) => reading.date === date)
                .map((reading) => {
                  const source = view.sources.find(
                    (s) => s.id === reading.source_id,
                  );
                  const disputed = view.conflicts.some((conflict) =>
                    conflict.observations.some((o) => o.id === reading.id),
                  );
                  return (
                    <article
                      className="measurement-history-row"
                      key={reading.id}
                    >
                      <div className="history-reading">
                        <strong>{reading.value}</strong>
                        <span>{reading.unit}</span>
                        {disputed && (
                          <small>
                            <AlertCircle size={12} />
                            Recorded disagreement
                          </small>
                        )}
                      </div>
                      <div className="history-source">
                        <strong>{source?.title || "Recorded source"}</strong>
                        <span>Available {timeLabel(reading.available_at)}</span>
                      </div>
                      <button
                        className="text-button"
                        aria-label={`Inspect ${metricLabel(metric)} ${reading.value} ${reading.unit} measured ${dateLabel(reading.date)}`}
                        onClick={() => onInspect(view, [reading.id])}
                      >
                        View source <ArrowUpRight size={14} />
                      </button>
                    </article>
                  );
                })}
            </div>
          </section>
        ))}
        {!readings.length && (
          <div className="empty">
            No {metricLabel(metric)} measurements are available in this view.
          </div>
        )}
      </div>
      {view.conflicts.some((c) => c.metric === metric) && (
        <p className="measurement-history-note">
          Conflicting values remain side by side. The records do not establish
          whether they describe the same specimen.
        </p>
      )}
    </section>
  );
}
