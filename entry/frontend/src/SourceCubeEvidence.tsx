import { useEffect, useId, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowDownToLine,
  ArrowRight,
  FileText,
} from "lucide-react";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { factKindLabels } from "./historyTypes";
import { metricDescription, recordLabel } from "./types";
import { timeLabel } from "./ui";
import { unitLabel, facilityLabel } from "./recordPresentation.mjs";
import {
  originalDownloadUrl,
  recordedDate,
  reviewedFieldLabel,
  sourceDateRange,
  sourceExcerpt,
  sourceTitle,
  sourcePage,
} from "./sourceDisplay";
import RecordConflictComparison from "./RecordConflictComparison";
import "./source-cube-evidence.css";
export default function SourceCubeEvidence({
  source: requestedSource,
  facts,
  view,
  initialFactId,
}: {
  source: HistoryView["sources"][number];
  facts: HistoryFact[];
  view: HistoryView;
  initialFactId?: string;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(
    initialFactId || null,
  );
  const [comparisonId, setComparisonId] = useState<string | null>(null);
  const proofId = useId();
  const comparison = useRef<HTMLDivElement>(null);
  const comparisonTrigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    setSelectedId(initialFactId || null);
    setComparisonId(null);
  }, [requestedSource.id, initialFactId]);
  // Never trust a selection retained from a previous source or historical scope.
  const source = view.sources.find((item) => item.id === requestedSource.id);
  const requestedIds = new Set(facts.map((fact) => fact.id));
  const visibleFacts = [...view.facts, ...view.undated_facts].filter(
    (fact) =>
      fact.source_id === requestedSource.id && requestedIds.has(fact.id),
  );
  const selected =
    visibleFacts.find((fact) => fact.id === selectedId) || visibleFacts[0];
  const conflict = selected
    ? view.conflicts.find((item) => item.fact_ids.includes(selected.id))
    : null;
  const edited = selected?.reviewed_fields || [];
  const title = sourceTitle(visibleFacts);
  if (!source)
    return (
      <section className="source-cube-evidence">
        <p>This document is not available in the selected view.</p>
      </section>
    );
  return (
    <section
      className="source-cube-evidence"
      aria-label={`Evidence for ${title}`}
    >
      <header className="source-evidence-heading">
        <span className="source-evidence-icon" aria-hidden="true">
          <FileText size={18} />
        </span>
        <div>
          <h3>{title}</h3>
          <p>{sourceDateRange(visibleFacts)}</p>
        </div>
      </header>
      <div className="source-evidence-facts" aria-label="Select a record">
        {visibleFacts.map((fact) => (
          <button
            key={fact.id}
            type="button"
            className={`source-evidence-fact ${selected?.id === fact.id ? "is-selected" : ""}`}
            aria-pressed={selected?.id === fact.id}
            aria-controls={proofId}
            onClick={() => {
              setSelectedId(fact.id);
              setComparisonId(null);
            }}
          >
            <span>
              <strong>{recordLabel(fact.label)}</strong>
              <small>{recordedDate(fact)}</small>
            </span>
            <span
              className={
                fact.kind === "measurement"
                  ? "source-evidence-number"
                  : "source-evidence-text"
              }
            >
              {fact.value_withheld
                ? "Hidden by date filter"
                : (fact.value ?? "Value not recorded")}
              {!fact.value_withheld && fact.unit && (
                <small>{unitLabel(fact.unit)}</small>
              )}
            </span>
            <ArrowRight size={14} aria-hidden="true" />
          </button>
        ))}
        {!visibleFacts.length && (
          <p className="source-evidence-empty">
            No records from this document are available in the selected view.
          </p>
        )}
      </div>
      {selected && (
        <div className="source-evidence-proof" id={proofId}>
          <div className="source-evidence-result-heading">
            <div>
              <h4>{recordLabel(selected.label)}</h4>
              <p>Recorded {recordedDate(selected)}</p>
            </div>
            <span>{factKindLabels[selected.kind]}</span>
          </div>
          {metricDescription(selected.label) && (
            <p className="source-evidence-description">
              {metricDescription(selected.label)}
            </p>
          )}
          <div
            className={`source-evidence-full-value${selected.kind === "measurement" ? " is-measurement" : ""}`}
          >
            {selected.value_withheld
              ? "Hidden by date filter"
              : (selected.value ?? "Value not recorded")}
            {!selected.value_withheld && selected.unit && (
              <span>{unitLabel(selected.unit)}</span>
            )}
          </div>
          {conflict && (
            <div className="source-evidence-conflict">
              <div>
                <AlertCircle size={16} />
                <span>
                  {conflict.reason === "different_recorded_units"
                    ? "Another record uses a different unit."
                    : "Another record has a different value."}
                </span>
              </div>
              <button
                ref={comparisonTrigger}
                type="button"
                className="secondary"
                onClick={() => {
                  setComparisonId(conflict.id);
                  requestAnimationFrame(() => {
                    comparison.current?.focus({ preventScroll: true });
                    comparison.current?.scrollIntoView({
                      block: "nearest",
                      behavior: "instant",
                    });
                  });
                }}
              >
                Compare records <ArrowRight size={14} />
              </button>
            </div>
          )}
          <div className="source-evidence-proof-heading">
            <span>Source excerpt</span>
            {sourcePage(selected, source) != null && (
              <span>Page {sourcePage(selected, source)}</span>
            )}
          </div>
          <blockquote>{sourceExcerpt(selected)}</blockquote>
          <div className="source-evidence-proof-meta">
            {selected.age_years != null && (
              <span>Age {selected.age_years}</span>
            )}
            {facilityLabel(selected.facility) && (
              <span>{facilityLabel(selected.facility)}</span>
            )}
          </div>
          {!!edited.length && (
            <p className="source-evidence-note">
              Edited during review: {edited.map(reviewedFieldLabel).join(", ")}.
              The excerpt retains the original wording.
            </p>
          )}
        </div>
      )}
      <footer className="source-evidence-footer">
        {source.original_available ? (
          <a
            className="secondary"
            href={originalDownloadUrl(source.id, view.scope)}
            download
          >
            <ArrowDownToLine size={14} /> Download original
          </a>
        ) : (
          <span className="source-evidence-original-missing">
            Original unavailable in this view
          </span>
        )}
        <details className="source-evidence-details">
          <summary>Source details</summary>
          <dl>
            <div>
              <dt>Filename / source title</dt>
              <dd>{source.title}</dd>
            </div>
            <div>
              <dt>Source note</dt>
              <dd>{source.provider || "Not recorded"}</dd>
            </div>
            <div>
              <dt>Added to Modus</dt>
              <dd>{timeLabel(source.available_at)}</dd>
            </div>
            {selected?.unit && (
              <div>
                <dt>Unit as recorded</dt>
                <dd>{selected.unit}</dd>
              </div>
            )}
            {selected?.facility && (
              <div>
                <dt>Facility / source note as recorded</dt>
                <dd>{selected.facility}</dd>
              </div>
            )}
            {selected?.occurred_on && (
              <div>
                <dt>Date as recorded</dt>
                <dd>{selected.occurred_on}</dd>
              </div>
            )}
          </dl>
        </details>
      </footer>
      {comparisonId && (
        <div ref={comparison} tabIndex={-1}>
          <RecordConflictComparison
            view={view}
            conflictId={comparisonId}
            onClose={() => {
              setComparisonId(null);
              requestAnimationFrame(() => comparisonTrigger.current?.focus());
            }}
          />
        </div>
      )}
      <span role="status" className="sr-only">
        {selected
          ? `Showing the source excerpt for ${recordLabel(selected.label)}, ${recordedDate(selected)}.`
          : "No record selected."}
      </span>
    </section>
  );
}
