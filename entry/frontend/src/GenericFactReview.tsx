import { useEffect, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, ArrowDownToLine } from 'lucide-react';
import DownloadOriginal from './DownloadOriginal';
import type { FactReviewRow } from './historyTypes';
import type { Draft } from './types';
import { omissionProposal } from './importQueue';
import ReviewFieldEditor from './ReviewFieldEditor';
import { firstInvalidReviewRow, reviewPage } from './reviewEntries';
import './generic-records.css';
import './review-workspace.css';

export default function GenericFactReview({draft, rows, locked, busy, uncertain, onChange, onSave, onSkip}: {
  draft: Draft; rows: FactReviewRow[]; locked: boolean; busy: boolean; uncertain: boolean;
  onChange: (id: string, patch: Partial<FactReviewRow>) => void; onSave: () => void; onSkip: () => void;
}) {
  const [selectedId, setSelectedId] = useState(rows[0]?.id);
  const [error, setError] = useState('');
  const previousIds = useRef(new Set(rows.map(row => row.id)));
  const form = useRef<HTMLFormElement>(null);
  const index = Math.max(0, rows.findIndex(row => row.id === selectedId));
  const selected = rows[index];
  const kept = rows.filter(row => row.keep).length;
  const page = reviewPage(rows, index);
  useEffect(() => {
    const added = rows.find(row => !previousIds.current.has(row.id));
    if (added) setSelectedId(added.id);
    previousIds.current = new Set(rows.map(row => row.id));
  }, [rows]);
  const choose = (next: number) => { if (rows[next]) { setSelectedId(rows[next].id); setError(''); } };
  const submit = () => {
    // The whole retained review is validated, including entries outside the rendered page.
    const invalid = firstInvalidReviewRow(rows);
    if (invalid && !uncertain) {
      setSelectedId(invalid.id); setError(invalid.message);
      requestAnimationFrame(() => {
        const control = form.current?.querySelector<HTMLElement>(`[aria-label="${invalid.control} ${invalid.index + 1}"]`);
        const details = control?.closest('details');
        if (details) details.open = true;
        control?.focus();
      });
      return;
    }
    setError(''); onSave();
  };
  return <form ref={form} className="generic-fact-review focused-review" noValidate onSubmit={event => { event.preventDefault(); submit(); }}>
    <header className="review-workspace-toolbar">
      <div><strong>Check against your original</strong><span>{rows.length} {rows.length === 1 ? 'entry' : 'entries'} to review</span></div>
      {draft.source.original_available && !uncertain && !draft.already_committed &&
        <DownloadOriginal href={`/api/drafts/${encodeURIComponent(draft.id)}/original`}>
          <ArrowDownToLine size={14} aria-hidden="true" /> Download original
        </DownloadOriginal>}
    </header>
    <div className="review-workspace-body">
      <nav className="review-entry-list" aria-label="Report entries">
        {page.rows.map(({row, index: rowIndex}) => <button key={row.id} type="button"
          aria-current={row.id === selected?.id ? 'true' : undefined}
          aria-label={`Review entry ${rowIndex + 1}: ${row.label || 'Unnamed entry'}`}
          onClick={() => choose(rowIndex)}>
          <span className="review-entry-name">{row.label || 'Unnamed entry'}</span>
          <span className="review-entry-value">{row.value || 'Value needed'}{row.unit ? ` ${row.unit}` : ''}</span>
          <small>{!row.keep ? 'Excluded' : omissionProposal(draft, row.id) ? 'Flagged row' : `Entry ${rowIndex + 1}`}</small>
        </button>)}
        {rows.length > page.size && <div className="review-list-pages">
          <button type="button" disabled={page.start === 0} onClick={() => choose(Math.max(0, page.start - page.size))}>Previous entries</button>
          <span>{page.start + 1}–{page.start + page.rows.length} of {rows.length}</span>
          <button type="button" disabled={page.start + page.size >= rows.length} onClick={() => choose(page.start + page.size)}>Next entries</button>
        </div>}
      </nav>
      <div className="review-selected-entry">
        {selected && <>
          <div className="review-entry-navigation">
            <span>Entry {index + 1} of {rows.length}</span>
            <div><button type="button" aria-label="Previous review entry" disabled={index === 0} onClick={() => choose(index - 1)}><ChevronLeft size={16} aria-hidden="true" /></button>
              <button type="button" aria-label="Next review entry" disabled={index + 1 >= rows.length} onClick={() => choose(index + 1)}><ChevronRight size={16} aria-hidden="true" /></button></div>
          </div>
          {error && <p className="review-validation" role="alert">{error}</p>}
          <ReviewFieldEditor key={selected.id} draft={draft} row={selected} index={index} locked={locked} onChange={onChange} />
        </>}
        {!selected && <p>No entries selected. Inspect any flagged rows above before saving.</p>}
      </div>
    </div>
      <div className="review-actions">
        <p>
          {kept} included · {rows.length - kept} excluded.
          <br />
          Saving keeps your review and the original.
          {!!draft.extraction_review?.completeness_check?.omissions.length && <>
            <br />Only flagged rows you include in this review will be saved.
          </>}
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
            disabled={busy || !kept || (!!draft.already_committed && rows.some(row => row.keep && !omissionProposal(draft, row.id)))}
          >
            {busy
              ? "Saving…"
              : uncertain
                ? "Retry the same fields"
                : `Save ${kept} reviewed field${kept === 1 ? "" : "s"}`}
          </button>
        </div>
      </div>
  </form>;
}
