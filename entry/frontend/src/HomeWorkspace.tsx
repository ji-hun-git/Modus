import { useState } from "react";
import {
  AlertCircle,
  Activity,
  ArrowRight,
  ArrowUpRight,
  ChevronRight,
  FileText,
  Upload,
  X,
} from "lucide-react";
import { dateLabel, timeLabel } from "./ui";
import { metricLabel, type Observation, type View } from "./types";
import { type Page } from "./Shell";
import HistoryPlot from "./HistoryPlot";

const metrics = ["hba1c", "egfr", "ldl"] as const;

export default function HomeWorkspace({
  view,
  onInspect,
  onNavigate,
  onImport,
  hasDraft,
  historical,
  onCurrent,
  children,
}: {
  view: View;
  onInspect: (view: View, ids: string[]) => void;
  onNavigate: (page: Page) => void;
  onImport: () => void;
  hasDraft: boolean;
  historical: boolean;
  onCurrent: () => void;
  children: React.ReactNode;
}) {
  const [selectedMetric, setSelectedMetric] = useState<
    Observation["metric"] | null
  >(null);
  const recent = [...view.sources]
    .sort((a, b) => b.date.localeCompare(a.date) || a.id.localeCompare(b.id))
    .slice(0, 3);
  const readings = selectedMetric
    ? view.observations
        .filter((o) => o.metric === selectedMetric)
        .sort(
          (a, b) => b.date.localeCompare(a.date) || a.id.localeCompare(b.id),
        )
    : [];
  const dates = [...new Set(readings.map((o) => o.date))];
  const disputedIds = new Set(
    view.conflicts.flatMap((conflict) =>
      conflict.observations.map((item) => item.id),
    ),
  );
  const openHistory = (metric: Observation["metric"]) => {
    setSelectedMetric(metric);
    requestAnimationFrame(() => {
      const history = document.getElementById("home-measurement-history");
      history?.focus({ preventScroll: true });
      history?.scrollIntoView({ block: "nearest", behavior: "instant" });
    });
  };
  return (
    <div className="consumer-home">
      {historical && (
        <div className="history-scope-banner">
          <div>
            <strong>You’re viewing a dated history</strong>
            <span>
              Measured through {dateLabel(view.scope.as_of)} · Files available{" "}
              {timeLabel(view.scope.known_at)}
            </span>
          </div>
          <button className="text-button" onClick={onCurrent}>
            Return to current <ArrowRight size={14} />
          </button>
        </div>
      )}
      <section
        className="history-upload"
        aria-label="Add records to your history"
      >
        <span className="history-upload-icon">
          <Upload size={23} strokeWidth={1.6} />
        </span>
        <div>
          <h2>
            {hasDraft
              ? "Your uploads are ready to continue"
              : "Add to your history"}
          </h2>
          <p>
            Upload reports, review the recorded facts, and keep them with their
            source files.
          </p>
        </div>
        <button className="primary" onClick={onImport}>
          <Upload size={17} />
          {hasDraft ? "Resume uploads" : "Upload records"}
        </button>
      </section>
      <section
        className="history-metrics"
        aria-label="Latest recorded measurements"
      >
        <div className="home-section-heading">
          <div>
            <h2>Featured measurements</h2>
            <p className="measurement-totals">
              {view.counts.documents}{" "}
              {view.counts.documents === 1 ? "file" : "files"} ·{" "}
              {view.counts.measurements}{" "}
              {view.counts.measurements === 1 ? "measurement" : "measurements"}{" "}
              in this view
            </p>
          </div>
          <div className="history-heading-actions">
            <details className="home-date-details">
              <summary>View dates</summary>
              <div>
                <p>
                  Measurements through{" "}
                  <strong>{dateLabel(view.scope.as_of)}</strong>
                  <br />
                  Files available through{" "}
                  <strong>{timeLabel(view.scope.known_at)}</strong>
                </p>
                <code>
                  Measured: {view.scope.as_of}
                  <br />
                  Available: {view.scope.known_at}
                  <br />
                  Captured: {view.scope.captured_at}
                </code>
                <button
                  className="text-button"
                  onClick={() => onNavigate("Replay")}
                >
                  Change dates <ArrowRight size={14} />
                </button>
              </div>
            </details>
            <button
              className="text-button"
              onClick={() => onNavigate("Timeline")}
            >
              All your recorded history <ArrowRight size={14} />
            </button>
          </div>
        </div>
        <div className="metric-summary-grid">
          {metrics.map((metric) => {
            const all = view.observations
              .filter((o) => o.metric === metric)
              .sort(
                (a, b) =>
                  b.date.localeCompare(a.date) || a.id.localeCompare(b.id),
              );
            const latestDate = all[0]?.date;
            const latest = all.filter((o) => o.date === latestDate);
            const disputed = view.conflicts.some(
              (c) => c.metric === metric && c.date === latestDate,
            );
            return (
              <article
                className={
                  "metric-summary " +
                  (selectedMetric === metric ? "expanded" : "")
                }
                key={metric}
              >
                <header>
                  <div className="metric-title-row">
                    <span className="metric-symbol" aria-hidden="true">
                      <Activity size={16} strokeWidth={1.6} />
                    </span>
                    <h3>{metricLabel(metric)}</h3>
                  </div>
                  <span>
                    {latestDate
                      ? `Measured ${dateLabel(latestDate)}`
                      : "No recorded values in this view"}
                  </span>
                </header>
                <div className="metric-latest-values">
                  {latest.map((o) => (
                    <button
                      key={o.id}
                      className="metric-latest-value"
                      onClick={() => onInspect(view, [o.id])}
                      aria-haspopup="dialog"
                      aria-label={`View source for ${metricLabel(metric)} ${o.value} ${o.unit} measured ${dateLabel(o.date)}`}
                    >
                      <span className="metric-latest-fact">
                        <strong>{o.value}</strong>
                        <span>{o.unit}</span>
                        <ArrowUpRight size={14} />
                      </span>
                      <span className="metric-latest-source">
                        {view.sources.find((s) => s.id === o.source_id)
                          ?.title || "Recorded source"}
                      </span>
                    </button>
                  ))}
                </div>
                {disputed && (
                  <span className="metric-disagreement">
                    <AlertCircle size={13} />
                    Different values recorded
                  </span>
                )}
                <HistoryPlot
                  observations={all}
                  disputedIds={disputedIds}
                  label={metricLabel(metric)}
                  onInspect={(ids) => onInspect(view, ids)}
                />
                <button
                  className="metric-history-action"
                  id={`history-trigger-${metric}`}
                  onClick={() => openHistory(metric)}
                  aria-expanded={selectedMetric === metric}
                  aria-controls="home-measurement-history"
                >
                  View history <ChevronRight size={15} />
                </button>
              </article>
            );
          })}
        </div>
      </section>
      {selectedMetric && (
        <section
          className="home-measurement-history"
          id="home-measurement-history"
          tabIndex={-1}
          aria-label={`${metricLabel(selectedMetric)} recorded history`}
        >
          <div className="home-section-heading">
            <h2>{metricLabel(selectedMetric)} history</h2>
            <button
              className="icon-button"
              onClick={() => {
                document
                  .getElementById(`history-trigger-${selectedMetric}`)
                  ?.focus();
                setSelectedMetric(null);
              }}
              aria-label="Close measurement history"
            >
              <X size={18} />
            </button>
          </div>
          <div className="home-history-list">
            {dates.map((date) => (
              <div className="home-history-day" key={date}>
                <div className="home-history-date">
                  <span>Measured</span>
                  <strong>{dateLabel(date)}</strong>
                </div>
                <div className="home-history-readings">
                  {readings
                    .filter((o) => o.date === date)
                    .map((o) => (
                      <button
                        className="home-history-reading"
                        key={o.id}
                        onClick={() => onInspect(view, [o.id])}
                        aria-haspopup="dialog"
                      >
                        <span className="home-history-fact">
                          <strong>{o.value}</strong>
                          <span>{o.unit}</span>
                        </span>
                        <span className="home-history-source">
                          <strong>
                            {view.sources.find((s) => s.id === o.source_id)
                              ?.title || "Recorded source"}
                          </strong>
                          <small>
                            Available {timeLabel(o.available_at)}
                            {view.conflicts.some((c) =>
                              c.observations.some((item) => item.id === o.id),
                            ) && (
                              <span className="metric-disagreement">
                                Different values recorded
                              </span>
                            )}
                          </small>
                        </span>
                        <ArrowUpRight size={15} />
                      </button>
                    ))}
                </div>
              </div>
            ))}
            {!readings.length && (
              <p className="workspace-empty-line">
                No {metricLabel(selectedMetric)} measurements are available in
                this view.
              </p>
            )}
          </div>
        </section>
      )}
      <div className="history-support-grid">
        <section className="home-records" aria-label="Recent files">
          <div className="home-section-heading">
            <h2>Recent files</h2>
            <button
              className="text-button"
              onClick={() => onNavigate("Records")}
            >
              All files <ArrowRight size={14} />
            </button>
          </div>
          <div className="home-document-list">
            {recent.map((source) => (
              <button
                className="home-document"
                key={source.id}
                onClick={() => onInspect(view, [source.id])}
                aria-haspopup="dialog"
              >
                <span className="document-icon">
                  <FileText size={20} strokeWidth={1.6} />
                </span>
                <span className="home-document-title" title={source.title}>
                  <strong>{source.title}</strong>
                  <span className="home-document-date">
                    Document date · {dateLabel(source.date)}
                  </span>
                </span>
                <ChevronRight size={16} />
              </button>
            ))}
            {!recent.length && (
              <p className="workspace-empty-line">
                No reviewed files are available in this view.
              </p>
            )}
          </div>
        </section>
        <div className="home-assistant-secondary">{children}</div>
      </div>
    </div>
  );
}
