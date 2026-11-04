import { ArrowUpRight } from 'lucide-react';
import type { HistoryFact, HistoryView } from './historyTypes';
import { currentOverviewFacts } from './overviewRecords';
import { sourceExcerpt } from './sourceDisplay';

export default function HomeReportEvidence({ fact, view, onOpen }: {
  fact: HistoryFact; view: HistoryView; onOpen: (fact: HistoryFact) => void;
}) {
  const current = currentOverviewFacts(view, [fact.id])[0];
  if (!current || current.source_id !== fact.source_id) return null;
  const hidden = current.value_withheld || current.source_quote_withheld;
  return <section className="report-source-excerpt" aria-label="Selected reading's original evidence">
    <header><span>From the original</span>
      <button type="button" className="text-button" onClick={() => onOpen(current)}>
        Open evidence <ArrowUpRight size={14} aria-hidden="true" />
      </button>
    </header>
    {hidden ? <p>The original excerpt is hidden in this date view.</p>
      : <blockquote>{sourceExcerpt(current)}</blockquote>}
    {!!current.reviewed_fields?.length && !hidden && <p className="report-correction-note">
      {current.previous_revision_id ? 'Corrected after saving.' : 'Edited during review.'} Original wording is preserved.
    </p>}
  </section>;
}
