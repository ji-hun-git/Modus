import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, Download, FileText } from "lucide-react";
import type {
  HistoryComparison,
  HistoryFact,
  HistoryView,
} from "./historyTypes";
import { factKindLabels } from "./historyTypes";
import { recordLabel } from "./types";
import { Modal, dateLabel, timeLabel } from "./ui";
import { recordedDate, reviewedFieldLabel } from "./sourceDisplay";
import { unitLabel } from "./recordPresentation.mjs";
import SourceCubeEvidence from "./SourceCubeEvidence";
import "./history-replay.css";

export default function HistoryReplayWorkspace({
  pair,
  scope,
  onReset,
}: {
  pair: HistoryComparison | null;
  scope: HistoryView["scope"];
  onReset: () => void;
}) {
  const resultHeading = useRef<HTMLHeadingElement>(null);
  const [inspected, setInspected] = useState<{
    view: HistoryView;
    fact: HistoryFact;
  } | null>(null);
  useEffect(() => {
    setInspected(null);
  }, [pair, scope.known_at, scope.as_of]);
  useEffect(() => {
    if (pair) resultHeading.current?.focus();
  }, [pair]);
  const bound = pair?.before.scope || scope;
  const source = inspected?.view.sources.find(
    (item) => item.id === inspected.fact.source_id,
  );
  const occurrence = bound.as_of
    ? `Recorded dates through ${dateLabel(bound.as_of)}`
    : "All recorded dates";
  const facts = (view: HistoryView) => [...view.facts, ...view.undated_facts];
  function rows(items: HistoryFact[], view: HistoryView) {
    return (
      <div className="history-replay-records">
        {items.map((fact) => (
          <article key={fact.id} className="history-replay-record">
            <div>
              <span className="history-replay-kind">
                {factKindLabels[fact.kind]}
              </span>
              <h3>{recordLabel(fact.label)}</h3>
              <p className="history-replay-value">
                {fact.value_withheld
                  ? "Hidden by date filter"
                  : (fact.value ?? "Value not recorded")}
                {!fact.value_withheld && fact.unit && (
                  <span> {unitLabel(fact.unit)}</span>
                )}
              </p>
              <p className="history-replay-date">
                {fact.date || fact.occurred_on
                  ? `Recorded ${recordedDate(fact)}`
                  : "Date not recorded"}
              </p>
              {!!fact.reviewed_fields?.length && (
                <p className="history-replay-edited">
                  Edited during review:{" "}
                  {fact.reviewed_fields.map(reviewedFieldLabel).join(", ")}.
                  Original wording is retained in the source.
                </p>
              )}
            </div>
            <button
              className="text-button"
              onClick={() => setInspected({ view, fact })}
              aria-label={`View source for ${recordLabel(fact.label)}, ${view.sources.find((item) => item.id === fact.source_id)?.title || fact.source_id}`}
            >
              <FileText size={15} /> View source <ArrowUpRight size={14} />
            </button>
          </article>
        ))}
      </div>
    );
  }
  function download() {
    if (!pair) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(pair, null, 2)], { type: "application/json" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "modus-history-comparison.json";
    link.click();
    URL.revokeObjectURL(url);
  }
  return (
    <div className="history-replay">
      <section className="panel history-replay-intro">
        <div>
          <h2 ref={resultHeading} tabIndex={-1}>
            {pair ? "What became available" : "Compare your record history"}
          </h2>
          <p>
            {occurrence}. Compare when records became available, keeping their
            recorded dates unchanged.
          </p>
        </div>
        {pair && (
          <button className="secondary" onClick={download}>
            <Download size={16} /> Download comparison
          </button>
        )}
        {pair && (
          <button className="text-button" onClick={onReset}>
            Change comparison dates
          </button>
        )}
        <details className="history-replay-bounds">
          <summary>Exact comparison dates</summary>
          <dl>
            <div>
              <dt>Recorded date cutoff</dt>
              <dd>
                {bound.as_of ||
                  "All recorded dates, including partial and unknown dates"}
              </dd>
            </div>
            <div>
              <dt>Earlier availability</dt>
              <dd>
                <code>{bound.known_at}</code>
              </dd>
            </div>
            {pair && (
              <>
                <div>
                  <dt>Later availability</dt>
                  <dd>
                    <code>{pair.after.scope.known_at}</code>
                  </dd>
                </div>
                <div>
                  <dt>Comparison captured</dt>
                  <dd>
                    <code>{pair.captured_at}</code>
                  </dd>
                </div>
              </>
            )}
          </dl>
        </details>
      </section>
      {pair && (
        <>
          <div className="history-replay-snapshots">
            {(["before", "after"] as const).map((side) => {
              const view = pair[side];
              return (
                <section className="panel" key={side}>
                  <span className="history-replay-kind">
                    {side === "before"
                      ? "Earlier availability"
                      : "Later availability"}
                  </span>
                  <h2>
                    {facts(view).length} records{" "}
                    <span>from {view.sources.length} documents</span>
                  </h2>
                  <p>{timeLabel(view.scope.known_at)}</p>
                  <p>
                    {view.undated_facts.length} with partial or unknown recorded
                    dates
                  </p>
                  <details>
                    <summary>View these records</summary>
                    {facts(view).length ? (
                      rows(facts(view), view)
                    ) : (
                      <p>No records were available within these bounds.</p>
                    )}
                  </details>
                </section>
              );
            })}
          </div>
          <section className="panel history-replay-arrivals">
            <header>
              <div>
                <h2>
                  {pair.added_counts.total} newly available{" "}
                  {pair.added_counts.total === 1 ? "record" : "records"}
                </h2>
                <p>
                  {pair.added_counts.dated} with an exact recorded date ·{" "}
                  {pair.added_counts.undated} with partial or unknown dates ·{" "}
                  {pair.unchanged_count} already available
                </p>
              </div>
            </header>
            {!!pair.new_conflicts.length && (
              <p className="history-replay-conflict">
                {pair.new_conflicts.length} new or expanded{" "}
                {pair.new_conflicts.length === 1
                  ? "disagreement"
                  : "disagreements"}
                . All recorded values are retained; no value is chosen as
                correct.
              </p>
            )}
            {pair.added.length ? (
              rows(pair.added, pair.after)
            ) : (
              <p>
                No additional records became available between these exact
                times.
              </p>
            )}
          </section>
        </>
      )}
      {inspected && source && (
        <Modal title="Source details" onClose={() => setInspected(null)}>
          <p className="modal-copy">
            {inspected.view.scope.as_of
              ? `Recorded dates through ${dateLabel(inspected.view.scope.as_of)}`
              : "All recorded dates"}{" "}
            · Files available through {timeLabel(inspected.view.scope.known_at)}
            .
          </p>
          <SourceCubeEvidence
            source={source}
            facts={facts(inspected.view).filter(
              (fact) => fact.source_id === source.id,
            )}
            view={inspected.view}
            initialFactId={inspected.fact.id}
          />
        </Modal>
      )}
    </div>
  );
}
