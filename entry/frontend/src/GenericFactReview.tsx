import { ArrowUpRight, RotateCcw } from "lucide-react";
import {
  factKindLabels,
  type FactKind,
  type FactReviewRow,
} from "./historyTypes";
import { metricLabel, type Draft } from "./types";
import "./generic-records.css";

export default function GenericFactReview({
  draft,
  rows,
  locked,
  busy,
  uncertain,
  onChange,
  onSave,
  onSkip,
}: {
  draft: Draft;
  rows: FactReviewRow[];
  locked: boolean;
  busy: boolean;
  uncertain: boolean;
  onChange: (id: string, patch: Partial<FactReviewRow>) => void;
  onSave: () => void;
  onSkip: () => void;
}) {
  const kept = rows.filter((row) => row.keep).length;
  return (
    <form
      className="generic-fact-review"
      onSubmit={(event) => {
        event.preventDefault();
        onSave();
      }}
    >
      {draft.source.original_available &&
        !uncertain &&
        !draft.already_committed && (
          <a
            className="text-button"
            href={`/api/drafts/${encodeURIComponent(draft.id)}/original`}
            download
          >
            Download original <ArrowUpRight size={14} />
          </a>
        )}
      {rows.map((row, index) => {
        const original = draft.facts?.find((fact) => fact.id === row.id);
        return (
          <article
            className={`review-card generic-fact-card ${row.keep ? "" : "excluded"}`}
            key={row.id}
          >
            <div className="review-card-top">
              <strong>
                {["hba1c", "egfr", "ldl"].includes(
                  row.label.trim().toLowerCase(),
                )
                  ? metricLabel(row.label.trim().toLowerCase())
                  : `Field ${index + 1}`}
              </strong>
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
            <fieldset
              disabled={locked || !row.keep}
              className="generic-fact-fields"
            >
              <label className="field">
                Type
                <select
                  aria-label={`Type ${index + 1}`}
                  value={row.kind}
                  onChange={(event) =>
                    onChange(row.id, { kind: event.target.value as FactKind })
                  }
                >
                  {Object.entries(factKindLabels).map(([kind, label]) => (
                    <option key={kind} value={kind}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Name as recorded
                <input
                  aria-label={`Name ${index + 1}`}
                  required
                  maxLength={200}
                  value={row.label}
                  onChange={(event) =>
                    onChange(row.id, { label: event.target.value })
                  }
                />
              </label>
              <label className="field generic-wide-field">
                Value or text as recorded
                <textarea
                  aria-label={`Recorded value ${index + 1}`}
                  required
                  maxLength={800}
                  rows={2}
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
                  placeholder="Leave blank if not recorded"
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
              <label className="field generic-wide-field">
                Facility as recorded
                <input
                  aria-label={`Facility ${index + 1}`}
                  maxLength={200}
                  value={row.facility || ""}
                  placeholder="Leave blank if not recorded"
                  onChange={(event) =>
                    onChange(row.id, { facility: event.target.value || null })
                  }
                />
              </label>
            </fieldset>
            <details className="generic-fact-source">
              <summary>
                Source excerpt{row.page ? ` · page ${row.page}` : ""}
              </summary>
              <blockquote>
                {row.source_quote ||
                  "No excerpt was returned. Compare with the original file."}
              </blockquote>
              {original && (
                <p>
                  Original proposal: {original.label} · {original.value}
                  {original.unit ? ` ${original.unit}` : ""} ·{" "}
                  {original.occurred_on || "Date not recorded"}
                </p>
              )}
            </details>
            <button
              type="button"
              className="text-button"
              disabled={locked || !original}
              onClick={() =>
                original && onChange(row.id, { ...original, keep: true })
              }
            >
              <RotateCcw size={12} /> Restore proposal
            </button>
          </article>
        );
      })}
      <p className="safe-note">
        {kept} included · {rows.length - kept} excluded. Partial and unknown
        dates stay as recorded. Saving keeps your review and the original
        source.
      </p>
      <div className="review-actions">
        <p>
          These are recorded facts.
          <br />
          Your review decides what is added.
        </p>
        <div>
          <button
            className="secondary"
            type="button"
            disabled={busy || uncertain}
            onClick={onSkip}
          >
            Skip file · keep review
          </button>
          <button
            className="primary"
            disabled={busy || !!draft.already_committed || !kept}
          >
            {busy
              ? "Saving…"
              : uncertain
                ? "Retry the same fields"
                : `Save ${kept} reviewed field${kept === 1 ? "" : "s"}`}
          </button>
        </div>
      </div>
    </form>
  );
}
