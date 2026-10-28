import { useState } from "react";
import {
  AlertCircle,
  ArrowUpRight,
  FileText,
  History,
  LoaderCircle,
  MessageSquare,
  RefreshCw,
} from "lucide-react";
import { dateLabel, timeLabel } from "./ui";
import { type Change, type View } from "./types";
import CallDetails from "./CallDetails";

const changeDay = (change: Change) =>
  new Date(change.created_at).toISOString().slice(0, 10);
const modeLabel = (mode: string) =>
  ({
    meta: "Meta",
    offline: "Local tools",
    "local-teleocr": "Local OCR",
    deterministic: "Local extraction",
  })[mode] || mode;

export default function ChangesWorkspace({
  view,
  changes,
  loading,
  error,
  onRefresh,
  onInspect,
}: {
  view: View;
  changes: Change[];
  loading: boolean;
  error: string;
  onRefresh: () => void;
  onInspect: (view: View, ids: string[]) => void;
}) {
  const [filter, setFilter] = useState("all");
  const filtered = changes.filter(
    (change) => filter === "all" || change.kind === filter,
  );
  const days = [...new Set(filtered.map((change) => changeDay(change)))]
    .sort()
    .reverse();
  return (
    <section className="changes-workspace" aria-label="Record activity">
      <div className="workspace-section-heading">
        <h2>Activity log</h2>
        <button className="text-button" disabled={loading} onClick={onRefresh}>
          <RefreshCw size={15} />
          Refresh
        </button>
      </div>
      <div className="activity-toolbar">
        <div className="filter-tabs" role="group" aria-label="Activity type">
          {[
            { key: "all", label: "All activity" },
            { key: "import", label: "Records" },
            { key: "extraction", label: "Drafts" },
            { key: "question", label: "Questions" },
            { key: "extraction_failure", label: "Reading issues" },
          ].map((item) => (
            <button
              key={item.key}
              aria-pressed={filter === item.key}
              className={filter === item.key ? "selected" : ""}
              onClick={() => setFilter(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <span className="activity-order">Newest first · UTC</span>
      </div>
      {loading ? (
        <div className="panel loading" role="status">
          <LoaderCircle className="spin" size={24} />
          Loading changes…
        </div>
      ) : error ? (
        <div role="alert" className="error-banner">
          <AlertCircle size={18} />
          <div>
            {error}
            <button className="text-button" onClick={onRefresh}>
              Retry
            </button>
          </div>
        </div>
      ) : filtered.length ? (
        <div className="activity-timeline">
          {days.map((day) => (
            <section className="activity-day" key={day}>
              <h3>{dateLabel(day)}</h3>
              <div className="activity-events">
                {filtered
                  .filter((change) => changeDay(change) === day)
                  .sort((a, b) => b.created_at.localeCompare(a.created_at))
                  .map((change) => {
                    const source = view.sources.find(
                      (s) => s.id === change.source_id,
                    );
                    const title =
                      change.kind === "import"
                        ? "Reviewed record added"
                        : change.kind === "extraction"
                          ? "Document read; review pending"
                          : change.kind === "extraction_failure"
                            ? "Document reading did not finish"
                            : change.kind === "question"
                              ? "Record question"
                              : "Recorded action";
                    const count =
                      change.fact_count ?? change.observation_ids?.length ?? 0;
                    const itemLabel =
                      change.fact_count != null
                        ? "recorded fact"
                        : "measurement";
                    return (
                      <article className="activity-event" key={change.id}>
                        <span className="activity-icon">
                          {["import", "extraction"].includes(change.kind) ? (
                            <FileText size={18} />
                          ) : change.kind === "extraction_failure" ? (
                            <AlertCircle size={18} />
                          ) : change.kind === "question" ? (
                            <MessageSquare size={18} />
                          ) : (
                            <History size={18} />
                          )}
                        </span>
                        <div className="activity-main">
                          <div className="activity-title">
                            <h4>{title}</h4>
                            <span
                              className={
                                "activity-status " +
                                (change.kind === "extraction_failure"
                                  ? "issue"
                                  : "")
                              }
                            >
                              {change.status === "review_required"
                                ? "Review pending"
                                : change.status}
                            </span>
                          </div>
                          <p>
                            {change.kind === "import"
                              ? source?.title ||
                                `${count} ${itemLabel}${count === 1 ? "" : "s"} added`
                              : change.message ||
                                change.error ||
                                "Recorded workspace action"}
                          </p>
                          <div className="activity-meta">
                            <time dateTime={change.created_at}>
                              {timeLabel(change.created_at)}
                            </time>
                            {change.kind === "import" && (
                              <span>
                                {count} {itemLabel}
                                {count === 1 ? "" : "s"}
                              </span>
                            )}
                            {change.mode && (
                              <span>{modeLabel(change.mode)}</span>
                            )}
                          </div>
                          <details className="activity-details">
                            <summary>Event details</summary>
                            <dl>
                              <div>
                                <dt>Action kind</dt>
                                <dd>{change.kind}</dd>
                              </div>
                              <div>
                                <dt>Status</dt>
                                <dd>{change.status}</dd>
                              </div>
                              <div>
                                <dt>Event</dt>
                                <dd>{change.id}</dd>
                              </div>
                              <div>
                                <dt>Recorded</dt>
                                <dd>{change.created_at}</dd>
                              </div>
                              {change.available_at && (
                                <div>
                                  <dt>Available in Modus</dt>
                                  <dd>{change.available_at}</dd>
                                </div>
                              )}
                              {change.scope && (
                                <>
                                  <div>
                                    <dt>Measured through</dt>
                                    <dd>{change.scope.as_of}</dd>
                                  </div>
                                  <div>
                                    <dt>Available through</dt>
                                    <dd>{change.scope.known_at}</dd>
                                  </div>
                                </>
                              )}
                              {change.error && (
                                <div>
                                  <dt>Issue</dt>
                                  <dd>{change.error}</dd>
                                </div>
                              )}
                            </dl>
                            {change.telemetry && (
                              <CallDetails
                                calls={change.telemetry.calls || []}
                              />
                            )}
                          </details>
                        </div>
                        {source && (
                          <button
                            className="text-button activity-inspect"
                            onClick={() => onInspect(view, [source.id])}
                          >
                            View record <ArrowUpRight size={14} />
                          </button>
                        )}
                      </article>
                    );
                  })}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <div className="workspace-empty">
          <History size={28} />
          <h3>
            {changes.length
              ? "No matching activity"
              : "No recorded actions in this view"}
          </h3>
          <p>
            {changes.length
              ? "Choose another activity type to see more."
              : "An earlier availability view does not include actions recorded later."}
          </p>
          {filter !== "all" && (
            <button className="text-button" onClick={() => setFilter("all")}>
              Show all activity
            </button>
          )}
        </div>
      )}
      <p className="activity-scope-note">
        Actions available through {timeLabel(view.scope.known_at)}.
      </p>
    </section>
  );
}
