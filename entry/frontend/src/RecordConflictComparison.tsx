import { useId } from "react";
import { AlertCircle, ArrowDownToLine, X } from "lucide-react";
import type { HistoryView } from "./historyTypes";
import { recordLabel } from "./types";
import { timeLabel } from "./ui";
import {
  originalDownloadUrl,
  recordedDate,
  reviewedFieldLabel,
  sourceExcerpt,
  sourceTitle,
  sourcePage,
} from "./sourceDisplay";
import { unitLabel, facilityLabel } from "./recordPresentation.mjs";
import "./record-conflict-comparison.css";
export default function RecordConflictComparison({
  view,
  conflictId,
  onClose,
}: {
  view: HistoryView;
  conflictId: string;
  onClose?: () => void;
}) {
  const heading = useId();
  const group = view.conflicts.find((item) => item.id === conflictId);
  const scopedFacts = [...view.facts, ...view.undated_facts];
  const facts = group
    ? scopedFacts.filter((fact) => group.fact_ids.includes(fact.id))
    : [];
  return (
    <section className="record-comparison" aria-labelledby={heading}>
      <header className="record-comparison-heading">
        <div>
          <span className="record-comparison-eyebrow">
            <AlertCircle size={15} /> Record discrepancy
          </span>
          <h3 id={heading}>
            {group?.reason === "different_recorded_units"
              ? "Different recorded units"
              : "Compare records"}
          </h3>
        </div>
        {onClose && (
          <button
            type="button"
            className="record-comparison-close"
            aria-label="Close record comparison"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        )}
      </header>
      {!group || facts.length < 2 ? (
        <p className="record-comparison-intro">
          Both records are not available in this selected view.
        </p>
      ) : (
        <>
          <p className="record-comparison-intro">
            {facts.length} records have different{" "}
            {group.reason === "different_recorded_units" ? "units" : "values"}.
            Each is preserved separately. Compare their dates, units and
            original wording.
          </p>
          <div className="record-comparison-grid">
            {facts.map((fact, index) => {
              const source = view.sources.find(
                (item) => item.id === fact.source_id,
              );
              const title = sourceTitle(
                scopedFacts.filter((item) => item.source_id === fact.source_id),
              );
              return (
                <article className="record-comparison-item" key={fact.id}>
                  <span className="record-comparison-record">
                    Record {index + 1}
                  </span>
                  <h4>{recordLabel(fact.label)}</h4>
                  <p className="record-comparison-date">
                    Recorded {recordedDate(fact)}
                  </p>
                  <div className="record-comparison-value">
                    {fact.value_withheld
                      ? "Hidden by date filter"
                      : (fact.value ?? "Value not recorded")}
                    {!fact.value_withheld && fact.unit && (
                      <span>{unitLabel(fact.unit)}</span>
                    )}
                  </div>
                  {!fact.unit && !fact.value_withheld && (
                    <p className="record-comparison-unknown">
                      Unit not recorded
                    </p>
                  )}
                  {facilityLabel(fact.facility) && (
                    <p className="record-comparison-facility">
                      {facilityLabel(fact.facility)}
                    </p>
                  )}
                  <div className="record-comparison-excerpt">
                    <div>
                      <span>Source excerpt</span>
                      {sourcePage(fact, source) != null && (
                        <span>Page {sourcePage(fact, source)}</span>
                      )}
                    </div>
                    <blockquote>{sourceExcerpt(fact)}</blockquote>
                  </div>
                  {!!fact.reviewed_fields?.length && (
                    <p className="record-comparison-edit">
                      Edited during review:{" "}
                      {fact.reviewed_fields.map(reviewedFieldLabel).join(", ")}.
                      The excerpt retains the original wording.
                    </p>
                  )}
                  <div className="record-comparison-source">
                    <strong>{title}</strong>
                    {source?.original_available ? (
                      <a
                        href={originalDownloadUrl(source.id, view.scope)}
                        download
                      >
                        <ArrowDownToLine size={14} /> Download original
                      </a>
                    ) : (
                      <span>Original unavailable in this view</span>
                    )}
                  </div>
                  <details className="record-comparison-details">
                    <summary>Source details</summary>
                    <dl>
                      {source && (
                        <>
                          <div>
                            <dt>Filename / source title</dt>
                            <dd>{source.title}</dd>
                          </div>
                          <div>
                            <dt>Added to Modus</dt>
                            <dd>{timeLabel(source.available_at)}</dd>
                          </div>
                        </>
                      )}
                      {fact.unit && (
                        <div>
                          <dt>Unit as recorded</dt>
                          <dd>{fact.unit}</dd>
                        </div>
                      )}
                      {fact.facility && (
                        <div>
                          <dt>Facility / source note as recorded</dt>
                          <dd>{fact.facility}</dd>
                        </div>
                      )}
                      {fact.occurred_on && (
                        <div>
                          <dt>Date as recorded</dt>
                          <dd>{fact.occurred_on}</dd>
                        </div>
                      )}
                    </dl>
                  </details>
                </article>
              );
            })}
          </div>
          {facts.length < group.fact_ids.length && (
            <p className="record-comparison-footnote">
              Some records in this discrepancy are unavailable in the selected
              view.
            </p>
          )}
          <p className="record-comparison-footnote">
            Different records can refer to different samples or methods. This
            comparison does not choose a result or assess health.
          </p>
        </>
      )}
    </section>
  );
}
