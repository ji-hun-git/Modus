import { useState } from "react";
import {
  AlertCircle,
  ArrowDownToLine,
  ArrowRight,
  FileText,
} from "lucide-react";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { factKindLabels } from "./historyTypes";
import { metricLabel } from "./types";
import { dateLabel, timeLabel } from "./ui";
import "./source-cube-evidence.css";

const friendlyLabel = (label: string) => {
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

export default function SourceCubeEvidence({
  source,
  facts,
  view,
}: {
  source: HistoryView["sources"][number];
  facts: HistoryFact[];
  view: HistoryView;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = facts.find((fact) => fact.id === selectedId) || facts[0];
  const conflict = selected
    ? view.conflicts.find((item) => item.fact_ids.includes(selected.id))
    : null;
  const edited = selected?.reviewed_fields || [];
  const query = new URLSearchParams({ known_at: view.scope.known_at });
  if (view.scope.as_of !== null) query.set("as_of", view.scope.as_of);
  return (
    <section
      className="source-cube-evidence"
      aria-label={`Evidence from ${source.title}`}
    >
      <header className="source-evidence-heading">
        <span className="source-evidence-icon">
          <FileText size={18} />
        </span>
        <div>
          <span className="source-cube-kicker">Inside this file</span>
          <h3>{source.title}</h3>
        </div>
      </header>
      <div className="source-evidence-facts" aria-label="Recorded entries">
        {facts.map((fact) => (
          <button
            key={fact.id}
            type="button"
            className={`source-evidence-fact ${selected?.id === fact.id ? "is-selected" : ""}`}
            aria-pressed={selected?.id === fact.id}
            aria-controls="source-cube-quote"
            onClick={() => setSelectedId(fact.id)}
          >
            <span>
              <strong>{friendlyLabel(fact.label)}</strong>
              <small>
                {fact.date
                  ? dateLabel(fact.date)
                  : fact.occurred_on || "Date not recorded"}
              </small>
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
                : (fact.value ?? "Not recorded")}
              {!fact.value_withheld && fact.unit && <small> {fact.unit}</small>}
            </span>
            <ArrowRight size={14} />
          </button>
        ))}
        {!facts.length && (
          <p>No entries are available from this file in the selected view.</p>
        )}
      </div>
      {selected && (
        <div className="source-evidence-proof" id="source-cube-quote">
          <div className="source-evidence-proof-heading">
            <span>From the file</span>
            <span>
              {selected.page ? `Page ${selected.page}` : "Page not recorded"}
            </span>
          </div>
          <blockquote>
            {selected.source_quote ||
              (selected.source_quote_withheld
                ? "This excerpt may include records outside the date filter. Open the complete history to read it."
                : "No excerpt was saved. The original file may contain more detail.")}
          </blockquote>
          <div className="source-evidence-proof-meta">
            <span>{factKindLabels[selected.kind]}</span>
            {selected.age_years != null && (
              <span>Age {selected.age_years}</span>
            )}
            {selected.facility && <span>{selected.facility}</span>}
          </div>
          {edited.length > 0 && (
            <p className="source-evidence-note">
              Edited during review: {edited.join(", ")}. The excerpt keeps the
              original wording.
            </p>
          )}
          {conflict && (
            <p className="source-evidence-conflict">
              <AlertCircle size={14} />{" "}
              {conflict.reason === "different_recorded_units"
                ? "Another entry records a different unit."
                : "Another entry records a different value."}{" "}
              Both remain in your history.
            </p>
          )}
        </div>
      )}
      <footer className="source-evidence-footer">
        <span>
          Available in Modus
          <br />
          <strong>{timeLabel(source.available_at)}</strong>
        </span>
        {source.original_available ? (
          <a
            className="secondary"
            href={`/api/history/sources/${encodeURIComponent(source.id)}/original?${query}`}
            download
          >
            <ArrowDownToLine size={14} /> Original
          </a>
        ) : (
          <span className="source-evidence-original-missing">
            Original not available
            <br />
            in this view
          </span>
        )}
      </footer>
      <span role="status" className="sr-only">
        Showing {facts.length} entries from {source.title}.{" "}
        {selected
          ? `Source excerpt for ${friendlyLabel(selected.label)} selected.`
          : ""}
      </span>
    </section>
  );
}
