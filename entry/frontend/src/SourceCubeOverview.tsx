import { useRef, useState } from "react";
import { AlertCircle, ArrowUpRight, FileText, Plus } from "lucide-react";
import type { HistoryView } from "./historyTypes";
import { recordLabel } from "./types";
import { unitLabel } from "./recordPresentation.mjs";
import SourceCubeEvidence from "./SourceCubeEvidence";
import RecordConflictComparison from "./RecordConflictComparison";
import { sourceDateRange, sourceTitle } from "./sourceDisplay";
import "./source-cubes.css";
export default function SourceCubeOverview({
  view,
  onImport,
  hasDraft,
  onNavigate,
  showImport = true,
  sourceIds,
}: {
  view: HistoryView;
  onImport: () => void;
  hasDraft: boolean;
  onNavigate?: (page: "Timeline" | "Records") => void;
  showImport?: boolean;
  sourceIds?: string[];
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [comparisonId, setComparisonId] = useState<string | null>(null);
  const [limit, setLimit] = useState(12);
  const evidence = useRef<HTMLDivElement>(null);
  const comparison = useRef<HTMLDivElement>(null);
  const comparisonTrigger = useRef<HTMLButtonElement | null>(null);
  const allFacts = [...view.facts, ...view.undated_facts];
  const factsFor = (id: string) =>
    allFacts.filter((fact) => fact.source_id === id);
  const latestRecorded = (id: string) =>
    factsFor(id)
      .flatMap((fact) =>
        fact.date
          ? [fact.date]
          : /^(?!0000)\d{4}(?:-(?:0[1-9]|1[0-2]))?$/.test(
                fact.occurred_on || "",
              )
            ? [fact.occurred_on!]
            : [],
      )
      .sort()
      .at(-1) || "";
  const sources = view.sources
    .filter(
      (source) => sourceIds === undefined || sourceIds.includes(source.id),
    )
    .sort(
      (a, b) =>
        latestRecorded(b.id).localeCompare(latestRecorded(a.id)) ||
        a.id.localeCompare(b.id),
    );
  const selected =
    sources.find((source) => source.id === selectedId) || sources[0];
  const selectedFacts = selected ? factsFor(selected.id) : [];
  const reveal = (element: HTMLDivElement | null) => {
    element?.focus({ preventScroll: true });
    element?.scrollIntoView({
      block: "start",
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
    });
  };
  const select = (id: string) => {
    setSelectedId(id);
    setComparisonId(null);
    if (window.matchMedia("(max-width: 760px)").matches)
      requestAnimationFrame(() => reveal(evidence.current));
  };
  return (
    <section
      className="source-cube-workspace"
      aria-label="Documents and source evidence"
    >
      <div className="source-cube-heading">
        <div>
          <h2>Documents</h2>
          <p>
            {sources.length} document{sources.length === 1 ? "" : "s"} in this
            view
          </p>
        </div>
        {showImport && (
          <button className="primary" onClick={onImport}>
            <Plus size={17} /> {hasDraft ? "Continue review" : "Add files"}
          </button>
        )}
      </div>
      {comparisonId && (
        <div
          ref={comparison}
          tabIndex={-1}
          className="source-document-comparison"
        >
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
      {!sources.length ? (
        <div className="source-cube-empty">
          <FileText size={32} strokeWidth={1.4} />
          <h3>
            {view.sources.length
              ? "No documents match this search"
              : "No documents in this view"}
          </h3>
          <p>
            {view.sources.length
              ? "Try a different name or clear your search."
              : "Add a document or check the selected dates to see your records."}
          </p>
          {!view.sources.length && (
            <button className="secondary" onClick={onImport}>
              Choose a file
            </button>
          )}
        </div>
      ) : (
        <div className="source-cube-layout">
          <section className="source-cube-shelf" aria-label="Choose a document">
            <div className="source-cube-shelf-caption">
              <span>By recorded date</span>
              <span>Newest first</span>
            </div>
            <div className="source-document-list">
              {sources.slice(0, limit).map((source) => {
                const facts = factsFor(source.id);
                const conflict = view.conflicts.find((item) =>
                  facts.some((fact) => item.fact_ids.includes(fact.id)),
                );
                const title = sourceTitle(facts);
                return (
                  <article
                    className={`source-document-card${selected.id === source.id ? " is-selected" : ""}`}
                    key={source.id}
                  >
                    <button
                      type="button"
                      className="source-document-choose"
                      aria-pressed={selected.id === source.id}
                      aria-controls="source-cube-evidence"
                      onClick={() => select(source.id)}
                    >
                      <div className="source-document-date">
                        <span>{sourceDateRange(facts)}</span>
                        <FileText size={16} aria-hidden="true" />
                      </div>
                      <h3>{title}</h3>
                      <div className="source-document-preview">
                        {facts.slice(0, 2).map((fact) => (
                          <div key={fact.id}>
                            <span>{recordLabel(fact.label)}</span>
                            <span>
                              {fact.value_withheld
                                ? "Hidden by date filter"
                                : (fact.value ?? "Value not recorded")}
                              {!fact.value_withheld && fact.unit && (
                                <small>{unitLabel(fact.unit)}</small>
                              )}
                            </span>
                          </div>
                        ))}
                      </div>
                      <span className="source-document-count">
                        {facts.length} recorded{" "}
                        {facts.length === 1 ? "item" : "items"}
                        <ArrowUpRight size={14} aria-hidden="true" />
                      </span>
                    </button>
                    {conflict && (
                      <button
                        type="button"
                        className="source-document-discrepancy"
                        onClick={(event) => {
                          comparisonTrigger.current = event.currentTarget;
                          setComparisonId(conflict.id);
                          requestAnimationFrame(() =>
                            reveal(comparison.current),
                          );
                        }}
                      >
                        <AlertCircle size={14} />
                        <span>
                          {conflict.reason === "different_recorded_units"
                            ? "Different recorded units"
                            : "Different recorded values"}
                        </span>
                        <span>
                          Compare <ArrowUpRight size={12} />
                        </span>
                      </button>
                    )}
                  </article>
                );
              })}
            </div>
            {sources.length > limit && (
              <button
                className="text-button source-cube-show-more"
                onClick={() => setLimit((value) => value + 12)}
              >
                Show {Math.min(12, sources.length - limit)} more documents
              </button>
            )}
            {onNavigate && (
              <div className="source-cube-shelf-actions">
                <button
                  className="text-button"
                  onClick={() => onNavigate("Timeline")}
                >
                  View record history <ArrowUpRight size={13} />
                </button>
              </div>
            )}
          </section>
          <div
            id="source-cube-evidence"
            ref={evidence}
            tabIndex={-1}
            className="source-cube-evidence-anchor"
          >
            <SourceCubeEvidence
              key={selected.id}
              source={selected}
              facts={selectedFacts}
              view={view}
            />
          </div>
        </div>
      )}
    </section>
  );
}
