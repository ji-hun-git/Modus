import { useRef, useState } from "react";
import { ArrowUpRight, Box, FileText, Plus } from "lucide-react";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { metricLabel } from "./types";
import SourceCubeEvidence from "./SourceCubeEvidence";
import "./source-cubes.css";

const sourceDates = (facts: HistoryFact[]) => {
  const years = facts
    .flatMap((fact) => {
      if (fact.date) return [fact.date.slice(0, 4)];
      const partial = /^(\d{4})(?:-(0[1-9]|1[0-2]))?$/.exec(
        fact.occurred_on || "",
      );
      return partial && Number(partial[1]) > 0 ? [partial[1]] : [];
    })
    .sort();
  if (!years.length)
    return facts.some((fact) => fact.occurred_on)
      ? "Date not fully known"
      : "Date not recorded";
  const first = years[0],
    last = years.at(-1)!;
  return first === last ? first : `${first}–${last}`;
};
const previewLabel = (label: string) => {
  const known: Record<string, string> = {
    hba1c: "hba1c",
    egfr: "egfr",
    ldl: "ldl",
    "ldl-c": "ldl",
    "ldl cholesterol": "ldl",
  };
  return known[label.trim().toLowerCase()]
    ? metricLabel(known[label.trim().toLowerCase()])
    : label;
};

export default function SourceCubeOverview({
  view,
  onImport,
  hasDraft,
  onNavigate,
}: {
  view: HistoryView;
  onImport: () => void;
  hasDraft: boolean;
  onNavigate?: (page: "Timeline" | "Records") => void;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [limit, setLimit] = useState(12);
  const evidence = useRef<HTMLDivElement>(null);
  const sources = [...view.sources].sort(
    (a, b) =>
      b.available_at.localeCompare(a.available_at) || a.id.localeCompare(b.id),
  );
  const allFacts = [...view.facts, ...view.undated_facts];
  const selected =
    sources.find((source) => source.id === selectedId) || sources[0];
  const selectedFacts = selected
    ? allFacts.filter((fact) => fact.source_id === selected.id)
    : [];
  const conflicts = new Set(view.conflicts.flatMap((item) => item.fact_ids));
  const select = (id: string) => {
    setSelectedId(id);
    if (window.matchMedia("(max-width: 760px)").matches) {
      requestAnimationFrame(() =>
        evidence.current?.scrollIntoView({
          block: "start",
          behavior: window.matchMedia("(prefers-reduced-motion: reduce)")
            .matches
            ? "instant"
            : "smooth",
        }),
      );
    }
  };
  return (
    <section
      className="source-cube-workspace"
      aria-label="Your files and their evidence"
    >
      <div className="source-cube-heading">
        <div>
          <span className="source-cube-kicker">Your record stack</span>
          <h2>
            <span>{sources.length}</span> file{sources.length === 1 ? "" : "s"}
            <small>
              {allFacts.length} saved{" "}
              {allFacts.length === 1 ? "entry" : "entries"}
            </small>
          </h2>
        </div>
        <button className="primary" onClick={onImport}>
          <Plus size={17} /> {hasDraft ? "Continue review" : "Add files"}
        </button>
      </div>
      {!sources.length ? (
        <div className="source-cube-empty">
          <Box size={34} strokeWidth={1.4} />
          <h3>Your first file starts the stack</h3>
          <p>
            Add a report, review its entries, and keep the original beside them.
          </p>
          <button className="secondary" onClick={onImport}>
            Choose a file
          </button>
        </div>
      ) : (
        <div className="source-cube-layout">
          <section
            className="source-cube-shelf"
            aria-label="Choose a source file"
          >
            <div className="source-cube-shelf-caption">
              <span>One cube, one file</span>
              <span>Latest added first</span>
            </div>
            <div className="source-cube-grid">
              {sources.slice(0, limit).map((source, index) => {
                const facts = allFacts.filter(
                  (fact) => fact.source_id === source.id,
                );
                const preview = facts.slice(0, 2);
                const hasConflict = facts.some((fact) =>
                  conflicts.has(fact.id),
                );
                return (
                  <button
                    key={source.id}
                    type="button"
                    className={`source-cube ${selected.id === source.id ? "is-selected" : ""}`}
                    aria-pressed={selected.id === source.id}
                    aria-controls="source-cube-evidence"
                    aria-label={`Open ${source.title}, ${facts.length} recorded ${facts.length === 1 ? "entry" : "entries"}${hasConflict ? ", has different recorded values" : ""}`}
                    aria-describedby={`source-cube-preview-${index}`}
                    onClick={() => select(source.id)}
                  >
                    <span className="source-cube-top" aria-hidden="true" />
                    <span className="source-cube-side" aria-hidden="true" />
                    <span className="source-cube-face">
                      <span className="source-cube-face-top">
                        <span>{sourceDates(facts)}</span>
                        <FileText size={14} strokeWidth={1.5} />
                      </span>
                      <strong className="source-cube-name" title={source.title}>
                        {source.title}
                      </strong>
                      <span
                        className="source-cube-preview"
                        id={`source-cube-preview-${index}`}
                      >
                        {preview.map((fact) => (
                          <span
                            className="source-cube-preview-row"
                            key={fact.id}
                          >
                            <span
                              className="source-cube-preview-label"
                              title={previewLabel(fact.label)}
                            >
                              {previewLabel(fact.label)}
                            </span>
                            <span
                              className={`source-cube-preview-value${fact.kind === "measurement" && !fact.value_withheld ? " is-number" : ""}`}
                              title={
                                fact.value_withheld
                                  ? "Hidden by date filter"
                                  : fact.value || "Not recorded"
                              }
                            >
                              <b>
                                {fact.value_withheld
                                  ? "Hidden by dates"
                                  : (fact.value ?? "Not recorded")}
                              </b>
                              {!fact.value_withheld && fact.unit && (
                                <small>{fact.unit}</small>
                              )}
                            </span>
                          </span>
                        ))}
                      </span>
                      <span className="source-cube-face-bottom">
                        <span>
                          <b>{facts.length}</b>{" "}
                          {facts.length === 1 ? "entry" : "entries"}
                        </span>
                        {hasConflict ? (
                          <i
                            className="source-cube-conflict"
                            title="Different recorded values"
                            aria-label="Different recorded values"
                          />
                        ) : (
                          <ArrowUpRight size={14} />
                        )}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
            {sources.length > limit && (
              <button
                className="text-button source-cube-show-more"
                onClick={() => setLimit((value) => value + 12)}
              >
                Show {Math.min(12, sources.length - limit)} more files
              </button>
            )}
            {onNavigate && (
              <div className="source-cube-shelf-actions">
                <button
                  className="text-button"
                  onClick={() => onNavigate("Timeline")}
                >
                  Open lifetime timeline <ArrowUpRight size={13} />
                </button>
                <button
                  className="text-button"
                  onClick={() => onNavigate("Records")}
                >
                  All files <ArrowUpRight size={13} />
                </button>
              </div>
            )}
          </section>
          <div
            id="source-cube-evidence"
            ref={evidence}
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
