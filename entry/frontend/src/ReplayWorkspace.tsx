import { type ReactNode } from "react";
import {
  AlertCircle,
  ArrowUpRight,
  Clock3,
  Download,
  FileText,
  GitCompareArrows,
} from "lucide-react";
import { dateLabel, timeLabel } from "./ui";
import {
  metricLabel,
  type Comparison,
  type Conflict,
  type View,
} from "./types";

const countLabel = (count: number, word: string) =>
  `${count} ${word}${count === 1 ? "" : "s"}`;

function Snapshot({
  view,
  label,
  onInspect,
}: {
  view: View;
  label: string;
  onInspect: (view: View, ids: string[]) => void;
}) {
  const sources = [...view.sources].sort(
    (a, b) => b.date.localeCompare(a.date) || a.id.localeCompare(b.id),
  );
  return (
    <section className="snapshot-card" aria-label={label}>
      <header className="snapshot-heading">
        <span className="eyebrow">{label}</span>
        <h3>{dateLabel(view.scope.known_at)}</h3>
        <span className="snapshot-time">
          Available through {timeLabel(view.scope.known_at)}
        </span>
      </header>
      <div className="snapshot-counts">
        <div>
          <strong>{view.counts.documents}</strong>
          <span>document{view.counts.documents === 1 ? "" : "s"}</span>
        </div>
        <div>
          <strong>{view.counts.measurements}</strong>
          <span>measurement{view.counts.measurements === 1 ? "" : "s"}</span>
        </div>
      </div>
      <div className="snapshot-sources">
        {sources.slice(0, 3).map((source) => (
          <button
            key={source.id}
            onClick={() => onInspect(view, [source.id])}
            aria-haspopup="dialog"
          >
            <FileText size={17} strokeWidth={1.6} />
            <span>
              <strong>{source.title}</strong>
              <small>
                {countLabel(
                  view.observations.filter((o) => o.source_id === source.id)
                    .length,
                  "measurement",
                )}{" "}
                · Document date {dateLabel(source.date)}
              </small>
            </span>
            <ArrowUpRight size={14} />
          </button>
        ))}
        {!sources.length && (
          <p className="snapshot-empty">
            No reviewed records were available within these dates.
          </p>
        )}
        {sources.length > 3 && (
          <span className="count-label">
            {countLabel(sources.length - 3, "more document")} in this snapshot
          </span>
        )}
      </div>
      <details className="exact-time">
        <summary>Exact captured scope</summary>
        <code>
          Measured through {view.scope.as_of}
          <br />
          Available through {view.scope.known_at}
          <br />
          Captured {view.scope.captured_at}
        </code>
      </details>
    </section>
  );
}

function Disagreements({
  conflicts,
  view,
  onInspect,
}: {
  conflicts: Conflict[];
  view: View;
  onInspect: (view: View, ids: string[]) => void;
}) {
  return (
    <div className="disagreement-list">
      {conflicts.map((conflict) => (
        <article className="disagreement" key={conflict.id}>
          <div className="disagreement-head">
            <AlertCircle size={18} />
            <div>
              <h3>
                {metricLabel(conflict.metric)}{" "}
                <span>· Measured {dateLabel(conflict.date)}</span>
              </h3>
              <p>
                Different recorded values. Whether these describe the same
                specimen is unknown.
              </p>
            </div>
          </div>
          <div className="disagreement-values">
            {conflict.observations.map((observation) => (
              <button
                className="value-button"
                key={observation.id}
                onClick={() => onInspect(view, [observation.id])}
                aria-haspopup="dialog"
              >
                <span className="conflict-value">
                  <strong>{observation.value}</strong>
                  <span>{observation.unit}</span>
                </span>
                <span className="conflict-source">
                  {view.sources.find((s) => s.id === observation.source_id)
                    ?.title || "Recorded source"}
                  <ArrowUpRight size={14} />
                </span>
              </button>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

export default function ReplayWorkspace({
  view,
  pair,
  current,
  canCompare,
  exporting,
  onExport,
  onInspect,
  children,
}: {
  view: View;
  pair: Comparison | null;
  current: boolean;
  canCompare: boolean;
  exporting: boolean;
  onExport: () => void;
  onInspect: (view: View, ids: string[]) => void;
  children: ReactNode;
}) {
  const displayed = pair?.after || view;
  const arrivals = pair
    ? pair.after.sources.filter((source) =>
        pair.added.some((o) => o.source_id === source.id),
      )
    : [];
  return (
    <div className="replay-workspace">
      <div className="workspace-section-heading">
        <h2>{pair ? "Then and now" : "Record snapshot"}</h2>
        <button className="text-button" disabled={exporting} onClick={onExport}>
          <Download size={16} />
          {exporting
            ? "Preparing export…"
            : pair
              ? "Export comparison"
              : "Export view"}
        </button>
      </div>
      <div className="replay-frame">
        <div className="replay-measurement-bound">
          <Clock3 size={16} />
          <span>
            Measurements through <strong>{dateLabel(view.scope.as_of)}</strong>
          </span>
          {pair && (
            <span className="replay-bound-note">
              Same measurement cutoff · different availability
            </span>
          )}
        </div>
        <div className={"comparison-grid " + (!pair ? "single-snapshot" : "")}>
          <Snapshot
            view={pair?.before || view}
            label={
              pair
                ? "Earlier availability"
                : current
                  ? "Current snapshot"
                  : "Selected availability"
            }
            onInspect={onInspect}
          />
          {pair ? (
            <Snapshot
              view={pair.after}
              label="Current availability"
              onInspect={onInspect}
            />
          ) : (
            <section className="compare-placeholder">
              <span className="comparison-symbol">
                <GitCompareArrows size={24} />
              </span>
              <h3>What arrived later?</h3>
              <p>
                {canCompare
                  ? "Keep this measurement cutoff and compare with records available now."
                  : "Choose an earlier availability date above, then compare it with now."}
              </p>
              <span className="compare-next-step">
                Use “Compare with now” in the date controls above.
              </span>
            </section>
          )}
        </div>
      </div>
      {pair && (
        <section className="replay-arrivals">
          <div className="workspace-section-heading">
            <h2>Later arrivals</h2>
            <span>{countLabel(arrivals.length, "document")}</span>
          </div>
          <div className="replay-result-counts">
            <div>
              <strong>{pair.added.length}</strong>
              <span>
                additional measurement{pair.added.length === 1 ? "" : "s"}
              </span>
            </div>
            <div>
              <strong>{pair.unchanged_count}</strong>
              <span>
                unchanged measurement{pair.unchanged_count === 1 ? "" : "s"}
              </span>
            </div>
            <div>
              <strong>{pair.new_conflicts.length}</strong>
              <span>
                new disagreement{pair.new_conflicts.length === 1 ? "" : "s"}
              </span>
            </div>
          </div>
          {arrivals.length ? (
            <div className="arrival-list">
              {arrivals.map((source) => (
                <button
                  className="arrival-source"
                  key={source.id}
                  onClick={() => onInspect(pair.after, [source.id])}
                  aria-haspopup="dialog"
                >
                  <span className="document-icon">
                    <FileText size={20} strokeWidth={1.6} />
                  </span>
                  <span>
                    <strong>{source.title}</strong>
                    <small>
                      Available {timeLabel(source.available_at)} ·{" "}
                      {countLabel(
                        pair.added.filter((o) => o.source_id === source.id)
                          .length,
                        "measurement",
                      )}
                    </small>
                  </span>
                  <ArrowUpRight size={16} />
                </button>
              ))}
            </div>
          ) : (
            <p className="workspace-empty-line">
              No later arrivals in this period.
            </p>
          )}
        </section>
      )}
      <section className="replay-conflicts">
        <div className="workspace-section-heading">
          <h2>Record disagreements</h2>
          <span
            className={displayed.conflicts.length ? "disagreement-label" : ""}
          >
            {countLabel(displayed.conflicts.length, "group")}
          </span>
        </div>
        {displayed.conflicts.length ? (
          <Disagreements
            conflicts={displayed.conflicts}
            view={displayed}
            onInspect={onInspect}
          />
        ) : (
          <p className="workspace-empty-line">
            No same-day disagreements in this view.
          </p>
        )}
      </section>
      <div className="replay-question">{children}</div>
    </div>
  );
}
