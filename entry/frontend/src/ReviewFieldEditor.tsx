import { RotateCcw } from 'lucide-react';
import RecordDateEvidence from './RecordDateEvidence';
import { factKindLabels, type FactKind, type FactReviewRow } from './historyTypes';
import type { Draft } from './types';
import { LabContextReview } from './LabContext';
import { omissionProposal } from './importQueue';

export default function ReviewFieldEditor({ draft, row, index, locked, onChange }: {
  draft: Draft; row: FactReviewRow; index: number; locked: boolean;
  onChange: (id: string, patch: Partial<FactReviewRow>) => void;
}) {
        const flagged = omissionProposal(draft, row.id);
        const original = draft.facts?.find((fact) => fact.id === row.id) || flagged;
        const reasons =
          draft.extraction_review?.facts.find((fact) => fact.id === row.id)
            ?.review_reasons || [];
        const changed =
          !!original &&
          (!row.keep ||
            (
              [
                "kind",
                "label",
                "value",
                "unit",
                "occurred_on",
                "facility",
                "reference_range", "specimen", "test_method",
              ] as const
            ).some((field) => (row[field] ?? "") !== (original[field] ?? "")));
  return (
          <article
            className={`review-card generic-fact-card ${row.keep ? "" : "excluded"}`} aria-label={`Review field ${index + 1}`}
            key={row.id}
          >
            <div className="review-card-top">
              <input
                className="review-name-input"
                aria-label={`Name ${index + 1}`}
                title="Name as recorded"
                placeholder={`Name of field ${index + 1}`}
                required
                maxLength={200}
                value={row.label}
                disabled={locked || !row.keep}
                onChange={(event) =>
                  onChange(row.id, { label: event.target.value })
                }
              />
              <label className="check-row">
                <input
                  type="checkbox"
                  aria-label={`Include field ${index + 1}`}
                  checked={row.keep}
                  disabled={locked}
                  onChange={(event) =>
                    onChange(row.id, { keep: event.target.checked })
                  }
                />
                {row.keep ? "Include" : "Excluded"}
              </label>
            </div>
            {reasons.length > 0 && (
              <ul
                className="extraction-review-reasons"
                aria-label={`Check ${row.label} against the original`}
              >
                {reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            )}
            <div className="review-fact-comparison">
              <div>
                <fieldset
                  disabled={locked || !row.keep}
                  className="generic-fact-fields"
                >
                  <label className="field generic-wide-field">
                    Value or text as recorded
                    <textarea
                      aria-label={`Recorded value ${index + 1}`}
                      required
                      maxLength={800}
                      rows={Math.min(
                        6,
                        Math.max(
                          1,
                          row.value.split("\n").length,
                          Math.ceil(row.value.length / 70),
                        ),
                      )}
                      value={row.value}
                      onChange={(event) =>
                        onChange(row.id, { value: event.target.value })
                      }
                    />
                  </label>
                  <label className="field">
                    Unit as printed
                    <input
                      aria-label={`Printed unit ${index + 1}`}
                      maxLength={80}
                      value={row.unit || ""}
                      placeholder="Not recorded"
                      onChange={(event) =>
                        onChange(row.id, { unit: event.target.value || null })
                      }
                    />
                  </label>
                  <label className="field">
                    Date as recorded
                    <input
                      aria-label={`Recorded date ${index + 1}`}
                      maxLength={100}
                      value={row.occurred_on || ""}
                      placeholder="Exact, partial, or leave blank"
                      onChange={(event) =>
                        onChange(row.id, {
                          occurred_on: event.target.value || null,
                        })
                      }
                    />
                  </label>
                </fieldset>
                <LabContextReview row={row} index={index} disabled={locked || !row.keep} onChange={onChange} collapsed />
                <details className="review-field-details" open={flagged ? true : undefined}>
                  <summary>
                    Type, facility and proposal{changed ? " · edited" : ""}
                  </summary>
                  <fieldset
                    disabled={locked || !row.keep}
                    className="generic-fact-fields"
                  >
                    <label className="field generic-wide-field">
                      Type
                      <select
                        aria-label={`Type ${index + 1}`}
                        value={row.kind}
                        onChange={(event) =>
                          onChange(row.id, {
                            kind: event.target.value as FactKind,
                          })
                        }
                      >
                        {Object.entries(factKindLabels).map(([kind, label]) => (
                          <option key={kind} value={kind}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field generic-wide-field">
                      Facility as recorded
                      <input
                        aria-label={`Facility ${index + 1}`}
                        maxLength={200}
                        value={row.facility || ""}
                        placeholder="Leave blank if not recorded"
                        onChange={(event) =>
                          onChange(row.id, {
                            facility: event.target.value || null,
                          })
                        }
                      />
                    </label>
                  </fieldset>
                  {original && (
                    <p>
                      Original proposal: {original.label} · {original.value}
                      {original.unit ? ` ${original.unit}` : ""} ·{" "}
                      {original.occurred_on || "Date not recorded"}
                    </p>
                  )}
                  {changed && (
                    <button
                      type="button"
                      className="text-button"
                      disabled={locked || !original}
                      onClick={() =>
                        original &&
                        onChange(row.id, { ...original, keep: true })
                      }
                    >
                      <RotateCcw size={12} aria-hidden="true" /> Restore proposal
                    </button>
                  )}
                </details>
              </div>
              <aside
                className="generic-fact-source"
                aria-label={`Original excerpt for field ${index + 1}`}
              >
                <p className="review-source-label">
                  {flagged ? 'Flagged excerpt' : 'In your original'}{row.page ? ` · page ${row.page}` : ""}
                </p>
                <blockquote>
                  {row.source_quote ||
                    "No excerpt was returned. Compare with the original file."}
                </blockquote>
                <RecordDateEvidence evidence={row.date_evidence} currentDate={row.occurred_on} reviewing />
                {flagged && <p>Confirm the entry type and date from your report. A blank date stays unknown.</p>}
              </aside>
            </div>
          </article>

  );
}
