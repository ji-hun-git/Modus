import { useState } from 'react';
import type { ReportCompleteness } from './types';

const PAGE_SIZE = 6;
export type OmissionActions = {
  onReviewRow?: (id: string) => void;
  rowStates?: Record<string, 'reviewing' | 'saved'>;
  disabled?: boolean;
};

export default function ReportCompletenessReview({ check, originalHref, saved = false, onReviewRow, rowStates = {}, disabled }: {
  check: ReportCompleteness;
  originalHref?: string;
  saved?: boolean;
} & OmissionActions) {
  const [page, setPage] = useState(0);
  const count = check.omissions.length;
  const savedCount = check.omissions.filter(row => rowStates[row.id] === 'saved').length;
  const allSaved = count > 0 && savedCount === count;
  const offset = Math.min(page * PAGE_SIZE, Math.max(0, Math.ceil(count / PAGE_SIZE) - 1) * PAGE_SIZE);
  const needsLook = check.pages.filter(p => p.status !== 'checked' || p.readability !== 'readable'
    || p.truncated || !p.independent_text_available);
  return <section className="report-completeness" aria-label="Check for missing report rows">
    <h4>{allSaved ? `${count} flagged row${count === 1 ? '' : 's'} reviewed`
      : count ? `${count} possible missing row${count === 1 ? '' : 's'}`
      : check.status === 'unavailable' ? 'The missing-row check could not finish'
      : check.status === 'partial' ? 'The missing-row check is incomplete'
      : 'No additional rows flagged'}</h4>
    <p>{allSaved ? 'Your reviewed entries are saved. These original flags stay here as part of the report history.'
      : count && onReviewRow ? 'Compare each flagged row with your original. Choose a row to review, correct it below, then save it.'
      : count ? saved ? 'These rows were not included in the saved fields. Review them in the original report.'
      : 'These rows may be missing from the draft. Compare them with your original; they are not included when you save.'
      : saved ? 'This check can miss rows. The original remains available in your history.'
      : 'Review the original before saving. This check can miss rows.'}</p>
    {!!needsLook.length && <p className="extraction-review-limit">
      Check {needsLook.length === 1 ? 'page' : 'pages'} {needsLook.map(p => p.page).join(', ')} directly.
      {' '}The separate reading was unavailable, limited, or has no independent page-text check.
    </p>}
    {!!count && <details open>
      <summary>Review possible omissions</summary>
      <ol className="extraction-review-facts" start={offset + 1}>
        {check.omissions.slice(offset, offset + PAGE_SIZE).map(row => <li key={row.id}>
          <div className="extraction-review-fact-heading"><strong>{row.label}</strong><span>Page {row.page}</span></div>
          <p className="extraction-review-value">{row.value}{row.unit ? ` ${row.unit}` : ''}</p>
          <blockquote>{row.source_quote}</blockquote>
          <p className="extraction-review-limit">{row.local_support === 'matched_text'
            ? 'Excerpt located in the page text. Confirm the row and its context.'
            : row.local_support === 'mismatch' ? 'This proposed excerpt or its details could not be matched. Check the original.'
            : 'No independent text check. Compare this proposed excerpt with the original image.'}</p>
          {rowStates[row.id] === 'saved' ? <p className="extraction-review-limit">Saved after your review · original flag kept</p>
            : onReviewRow && <button type="button" className="secondary" disabled={disabled || rowStates[row.id] === 'reviewing'}
              onClick={() => onReviewRow(row.id)}>
              {rowStates[row.id] === 'reviewing' ? 'In your review below' : `Review ${row.label}`}
            </button>}
        </li>)}
      </ol>
      {count > PAGE_SIZE && <nav className="completeness-pages" aria-label="Possible omission pages">
        <button type="button" className="text-button" disabled={!offset} onClick={() => setPage(Math.max(0, page - 1))}>Previous rows</button>
        <span>{offset + 1}–{Math.min(offset + PAGE_SIZE, count)} of {count}</span>
        <button type="button" className="text-button" disabled={offset + PAGE_SIZE >= count} onClick={() => setPage(page + 1)}>Next rows</button>
      </nav>}
    </details>}
    {originalHref && (count > 0 || needsLook.length > 0 || check.status !== 'completed') &&
      <a className="text-button" href={originalHref} download>Download original to review</a>}
  </section>;
}
