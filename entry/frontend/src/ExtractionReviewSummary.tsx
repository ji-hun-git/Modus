import { AlertCircle, FileCheck2 } from "lucide-react";
import { metricLabel, type ExtractionReview } from "./types";
import "./extraction-review.css";
import ReportCoverageSummary from "./ReportCoverageSummary";
import ReportCompletenessReview, { type OmissionActions } from './ReportCompletenessReview';

const documentLabels: Record<string, string> = {
  lab: "Lab report",
  lab_report: "Lab report",
  checkup: "Checkup report",
  prescription: "Prescription",
  discharge: "Discharge summary",
  discharge_summary: "Discharge summary",
  vaccination: "Vaccination record",
  vaccination_card: "Vaccination record",
  imaging: "Imaging report",
  imaging_report: "Imaging report",
  other: "Document",
};

const checkLabels: Record<string, string> = {
  completed: "Source check completed. Review the fields before saving.",
  passed: "Source check completed. Review the fields before saving.",
  failed:
    "The source check could not finish. Check each field against the original.",
  unavailable:
    "The source check is unavailable. Check each field against the original.",
  partial: "Some fields need another look at the original.",
  not_run:
    "The source check has not run. Check each field against the original.",
};

function fieldLabel(label: string) {
  const known: Record<string, string> = {
    hba1c: "hba1c",
    egfr: "egfr",
    ldl: "ldl",
    "ldl-c": "ldl",
  };
  const metric = known[label.trim().toLowerCase()];
  return metric ? metricLabel(metric) : label || "Recorded field";
}

export default function ExtractionReviewSummary({
  review,
  originalHref,
  omissionActions,
}: {
  review: ExtractionReview;
  originalHref?: string;
  omissionActions?: OmissionActions;
}) {
  const unsupported = review.facts.filter((fact) => !fact.commit_supported);
  const flagged = review.facts.filter((fact) => fact.review_reasons.length > 0);
  const count = review.facts.length;
  return (
    <section
      className="extraction-review"
      aria-label="Extracted fields and source checks"
    >
      <header>
        <div>
          <h3>
            {count
              ? `${count} field${count === 1 ? "" : "s"} found`
              : "No fields found"}
          </h3>
          <p>{documentLabels[review.document_type] || "Document"}</p>
        </div>
        {flagged.length > 0 && (
          <span className="extraction-review-count">
            <AlertCircle size={14} /> {flagged.length}{" "}
            {flagged.length === 1 ? "needs" : "need"} a closer look
          </span>
        )}
      </header>
      <div className="extraction-review-inner">
        {review.completeness_check && <ReportCompletenessReview key={originalHref || 'saved'}
          check={review.completeness_check} originalHref={originalHref} {...omissionActions} />}
        {review.coverage && (
          <ReportCoverageSummary coverage={review.coverage} />
        )}
        <p className="extraction-review-check">
          {flagged.length ? (
            <AlertCircle size={15} />
          ) : (
            <FileCheck2 size={15} />
          )}
          {count === 0 ? 'There are no proposed fields to verify. Inspect the original and any possible omissions.' : checkLabels[review.verification_status] ||
            "Compare the proposed fields with the original before saving."}
        </p>
        {unsupported.length > 0 && (
          <p className="extraction-review-limit">
            {unsupported.length} field
            {unsupported.length === 1 ? " is" : "s are"} shown here for
            reference. This version cannot add{" "}
            {unsupported.length === 1 ? "it" : "them"} to your history yet. Only
            the editable fields below can be saved.
          </p>
        )}
        {count > 0 && <details>
          <summary>All source checks and excerpts</summary>
          <ol className="extraction-review-facts">
            {review.facts.map((fact) => (
              <li key={fact.id}>
                <div className="extraction-review-fact-heading">
                  <strong>{fieldLabel(fact.label)}</strong>
                  <span>
                    {fact.page ? `Page ${fact.page}` : "Page unknown"}
                  </span>
                </div>
                <p className="extraction-review-value">
                  {fact.value ?? "Not extracted"}
                  {fact.unit ? ` ${fact.unit}` : ""}
                  {fact.date && <span>{fact.date}</span>}
                </p>
                {!fact.commit_supported && (
                  <p className="extraction-review-unsaved">
                    Not available to save yet
                  </p>
                )}
                {fact.review_reasons.length > 0 && (
                  <ul className="extraction-review-reasons">
                    {fact.review_reasons.map((reason, i) => (
                      <li key={i}>{reason}</li>
                    ))}
                  </ul>
                )}
                <blockquote>
                  {fact.source_quote ||
                    "No source excerpt was returned. Check the original file."}
                </blockquote>
              </li>
            ))}
          </ol>
        </details>}
      </div>
    </section>
  );
}
