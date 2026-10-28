import { useEffect, useState } from "react";
import {
  AlertCircle,
  ArrowUpRight,
  ChevronRight,
  Download,
  FileText,
  Search,
} from "lucide-react";
import { dateLabel, timeLabel } from "./ui";
import { metricLabel, type Observation, type View } from "./types";

export default function RecordsWorkspace({
  view,
  exporting,
  onExport,
  onInspect,
}: {
  view: View;
  exporting: boolean;
  onExport: () => void;
  onInspect: (view: View, ids: string[]) => void;
}) {
  const [filter, setFilter] = useState("");
  const [metric, setMetric] = useState<Observation["metric"] | "all">("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [compact, setCompact] = useState(
    () => window.matchMedia("(max-width: 760px)").matches,
  );
  useEffect(() => {
    const query = window.matchMedia("(max-width: 760px)");
    const update = () => setCompact(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  const sources = [...view.sources]
    .sort((a, b) => b.date.localeCompare(a.date) || a.id.localeCompare(b.id))
    .filter((source) => {
      if (
        metric !== "all" &&
        !view.observations.some(
          (o) => o.source_id === source.id && o.metric === metric,
        )
      )
        return false;
      const scopedMeasurements = view.observations
        .filter((observation) => observation.source_id === source.id)
        .map((observation) =>
          [
            observation.metric,
            metricLabel(observation.metric),
            observation.date,
            dateLabel(observation.date),
            observation.value,
            observation.unit,
          ].join(" "),
        )
        .join(" ");
      return [
        source.title,
        source.provider,
        source.date,
        dateLabel(source.date),
        scopedMeasurements,
      ]
        .join(" ")
        .toLowerCase()
        .includes(filter.trim().toLowerCase());
    });
  const selected =
    sources.find((source) => source.id === selectedId) || sources[0];
  const observations = view.observations.filter(
    (o) => o.source_id === selected?.id,
  );
  const conflicts = view.conflicts.filter((conflict) =>
    conflict.observations.some((o) => o.source_id === selected?.id),
  );
  return (
    <section className="records-workspace" aria-label="Source records">
      <div className="records-toolbar">
        <div className="inventory-count">
          <span>In this view:</span>
          <div>
            <strong>{view.counts.documents}</strong> document
            {view.counts.documents === 1 ? "" : "s"}
          </div>
          <span className="inventory-divider" />
          <div>
            <strong>{view.counts.measurements}</strong> measurement
            {view.counts.measurements === 1 ? "" : "s"}
          </div>
        </div>
        <button
          className="text-button export-button"
          disabled={exporting}
          onClick={onExport}
          title="Export every record in this captured view, including records hidden by list filters"
        >
          <Download size={16} />
          {exporting ? "Exporting…" : "Export view"}
        </button>
      </div>
      <div className="library-filters">
        <label className="search-box">
          <Search size={17} />
          <input
            aria-label="Search records"
            placeholder="Search titles, dates or values"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </label>
        <div
          className="filter-tabs"
          role="group"
          aria-label="Filter documents by measurement"
        >
          {(["all", "hba1c", "egfr", "ldl"] as const).map((name) => (
            <button
              key={name}
              aria-pressed={metric === name}
              className={metric === name ? "selected" : ""}
              onClick={() => setMetric(name)}
            >
              {name === "all" ? "All records" : metricLabel(name)}
            </button>
          ))}
        </div>
      </div>
      <div className="records-layout">
        <div className="document-list" aria-label="Documents">
          <div className="list-label">
            <span role="status">
              {filter.trim() || metric !== "all"
                ? `${sources.length} matching document${sources.length === 1 ? "" : "s"}`
                : "Documents"}
            </span>
            <span>Document date ↓</span>
          </div>
          {sources.map((source) => {
            const fields = view.observations.filter(
              (o) => o.source_id === source.id,
            );
            const dates = [...new Set(fields.map((o) => o.date))].sort();
            const disputed = view.conflicts.some((conflict) =>
              conflict.observations.some((o) => o.source_id === source.id),
            );
            return (
              <button
                key={source.id}
                className={
                  "document-row " +
                  (!compact && selected?.id === source.id ? "selected" : "")
                }
                aria-pressed={compact ? undefined : selected?.id === source.id}
                aria-controls={compact ? undefined : "selected-record-detail"}
                aria-haspopup={compact ? "dialog" : undefined}
                onClick={() => {
                  setSelectedId(source.id);
                  if (compact) onInspect(view, [source.id]);
                }}
              >
                <span className="document-icon">
                  <FileText size={20} strokeWidth={1.6} />
                </span>
                <span className="document-summary">
                  <strong title={source.title}>{source.title}</strong>
                  <span className="document-date">
                    {dates.length
                      ? `Measured ${dateLabel(dates[0])}${dates[0] !== dates.at(-1) ? " – " + dateLabel(dates.at(-1)!) : ""}`
                      : "No measurements in this view"}
                  </span>
                  <span className="document-metrics">
                    {fields.length} measurement{fields.length === 1 ? "" : "s"}{" "}
                    ·{" "}
                    {[
                      ...new Set(fields.map((o) => metricLabel(o.metric))),
                    ].join(" · ")}
                  </span>
                  {disputed && (
                    <span className="row-disagreement">
                      <AlertCircle size={12} />
                      Recorded disagreement
                    </span>
                  )}
                </span>
                <ChevronRight className="document-chevron" size={16} />
              </button>
            );
          })}
          {!sources.length && (
            <div className="empty">
              <Search size={23} />
              <strong>
                {filter || metric !== "all"
                  ? "No matching records"
                  : "No reviewed records are available in this view."}
              </strong>
              {filter || metric !== "all" ? (
                <button
                  className="text-button"
                  onClick={() => {
                    setFilter("");
                    setMetric("all");
                  }}
                >
                  Clear filters
                </button>
              ) : (
                <p>Change the dates to explore another view.</p>
              )}
            </div>
          )}
        </div>
        <div
          className="record-detail"
          id="selected-record-detail"
          aria-label="Selected record"
        >
          {selected ? (
            <>
              <div className="detail-heading">
                <div className="detail-heading-top">
                  <span className="eyebrow">
                    <FileText size={15} />
                    {observations.length} measurement
                    {observations.length === 1 ? "" : "s"}
                  </span>
                  <button
                    className="text-button"
                    onClick={() => onInspect(view, [selected.id])}
                    aria-haspopup="dialog"
                  >
                    View source <ArrowUpRight size={15} />
                  </button>
                </div>
                <h2>{selected.title}</h2>
              </div>
              <dl className="document-meta">
                <div>
                  <dt>Document date</dt>
                  <dd>{dateLabel(selected.date)}</dd>
                </div>
                <div>
                  <dt>Available in Modus</dt>
                  <dd>{timeLabel(selected.available_at)}</dd>
                </div>
              </dl>
              <div className="detail-table-wrap">
                <table className="measurement-table">
                  <thead>
                    <tr>
                      <th>Measurement</th>
                      <th>Recorded value</th>
                      <th>Measured on</th>
                    </tr>
                  </thead>
                  <tbody>
                    {observations.map((o) => (
                      <tr key={o.id}>
                        <td>{metricLabel(o.metric)}</td>
                        <td>
                          <strong>{o.value}</strong>{" "}
                          <span className="measurement-unit">{o.unit}</span>
                        </td>
                        <td>{dateLabel(o.date)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!!conflicts.length && (
                <div className="detail-warning">
                  <AlertCircle size={16} />
                  <span>
                    {conflicts.length} same-day disagreement
                    {conflicts.length === 1 ? "" : "s"}. All values are
                    preserved.
                  </span>
                </div>
              )}
            </>
          ) : (
            <div className="empty">
              <FileText size={26} />
              <strong>Select a record to see its measurements.</strong>
            </div>
          )}
        </div>
      </div>
      <div className="inventory-scope">
        <span>
          {filter.trim() || metric !== "all"
            ? "List filters do not change the exported view."
            : "Every measurement stays linked to its source."}
        </span>
        <details className="exact-time">
          <summary>Exact view dates</summary>
          <code>
            Measurements through {view.scope.as_of}
            <br />
            Records available through {view.scope.known_at}
            <br />
            Captured {view.scope.captured_at}
          </code>
        </details>
      </div>
    </section>
  );
}
