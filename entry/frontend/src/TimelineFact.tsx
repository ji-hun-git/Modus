import { AlertCircle, ArrowUpRight, FileText } from "lucide-react";
import { useRef, useState } from "react";
import { dateLabel, timeLabel } from "./ui";
import { metricLabel } from "./types";
import { unitLabel, facilityLabel } from "./recordPresentation.mjs";
import RecordConflictComparison from "./RecordConflictComparison";
import {
  factKindLabels,
  type HistoryFact,
  type HistoryView,
} from "./historyTypes";

export const exactDate = (fact: HistoryFact) => fact.date || null;
const factLabel = (label: string) => {
  const id = label.trim().toLowerCase();
  const known: Record<string, string> = {
    hba1c: "hba1c",
    egfr: "egfr",
    ldl: "ldl",
    "ldl-c": "ldl",
    "ldl cholesterol": "ldl",
  };
  return known[id] ? metricLabel(known[id]) : label;
};

export default function TimelineFact({
  fact,
  view,
  conflict,
  conflictReason,
}: {
  fact: HistoryFact;
  view: HistoryView;
  conflict: boolean;
  conflictReason?: string;
}) {
  const source = view.sources.find((item) => item.id === fact.source_id);
  const [comparing, setComparing] = useState(false);
  const comparisonTrigger = useRef<HTMLButtonElement>(null);
  const conflictGroup = view.conflicts.find((item) =>
    item.fact_ids.includes(fact.id),
  );
  const recordedDate = exactDate(fact);
  const originalQuery = new URLSearchParams({ known_at: view.scope.known_at });
  if (view.scope.as_of !== null) originalQuery.set("as_of", view.scope.as_of);
  return (
    <article className={`timeline-fact ${conflict ? "has-conflict" : ""}`}>
      <div className="timeline-fact-top">
        <span>{factKindLabels[fact.kind] || "Recorded fact"}</span>
        {conflict && (
          <span className="timeline-conflict">
            <AlertCircle size={13} />{" "}
            {conflictReason === "different_recorded_units"
              ? "Different printed units"
              : "Different recorded values"}
          </span>
        )}
      </div>
      <h3>{factLabel(fact.label)}</h3>
      <p
        className={`timeline-recorded-value ${fact.kind === "measurement" ? "is-measurement" : "is-text"}`}
      >
        {fact.value_withheld
          ? "Hidden by date filter"
          : (fact.value ?? "Not recorded")}
        {!fact.value_withheld && fact.unit && (
          <span> {unitLabel(fact.unit)}</span>
        )}
      </p>
      <div className="timeline-fact-meta">
        <span>
          {recordedDate
            ? dateLabel(recordedDate)
            : fact.occurred_on || "Date not recorded"}
        </span>
        {facilityLabel(fact.facility) && (
          <span>{facilityLabel(fact.facility)}</span>
        )}
        {fact.age_years != null && <span>Age {fact.age_years}</span>}
      </div>
      {conflictGroup && (
        <button
          ref={comparisonTrigger}
          className="text-button"
          onClick={() => setComparing(!comparing)}
          aria-expanded={comparing}
        >
          Compare records <ArrowUpRight size={13} />
        </button>
      )}
      {comparing && conflictGroup && (
        <RecordConflictComparison
          view={view}
          conflictId={conflictGroup.id}
          onClose={() => {
            setComparing(false);
            requestAnimationFrame(() => comparisonTrigger.current?.focus());
          }}
        />
      )}
      {fact.normalization?.status === "converted" &&
        fact.normalization.normalized && (
          <p className="timeline-normalized">
            Converted:{" "}
            {fact.normalization.normalized.display_is_exact
              ? ""
              : "approximately "}
            {fact.normalization.normalized.value}{" "}
            {fact.normalization.normalized.unit}. Printed value retained above.
          </p>
        )}
      <details className="timeline-source">
        <summary>
          <FileText size={13} /> Source details
          {fact.page ? ` · p. ${fact.page}` : ""}
          <ArrowUpRight size={12} />
        </summary>
        <blockquote>
          {fact.source_quote ||
            (fact.source_quote_withheld
              ? "This excerpt may include records outside the selected dates. It is hidden in this view."
              : "No source excerpt was saved.")}
        </blockquote>
        <dl>
          <div>
            <dt>Added to Modus</dt>
            <dd>{timeLabel(fact.available_at)}</dd>
          </div>
          <div>
            <dt>Source document</dt>
            <dd>{source?.title || "Not recorded"}</dd>
          </div>
        </dl>
        {source?.original_available && (
          <a
            className="text-button"
            href={`/api/history/sources/${encodeURIComponent(source.id)}/original?${originalQuery}`}
            download
          >
            Download original <ArrowUpRight size={13} />
          </a>
        )}
      </details>
    </article>
  );
}
