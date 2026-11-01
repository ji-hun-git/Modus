import { useState } from 'react';
import type { HistoryFact, HistoryView } from './historyTypes';
import useHistoryView, { type PageOptions } from './useHistoryView';
import HistoryPager from './HistoryPager';
import TimelineFact from './TimelineFact';
import HomeRecordSeries from './HomeRecordSeries';
import OverviewRecordDetails from './OverviewRecordDetails';

export default function PagedRecordList({ parent, filters = {}, chart = false }: {
  parent: HistoryView; filters?: PageOptions; chart?: boolean;
}) {
  const page = useHistoryView(parent.scope, parent.scope.as_of === null,
    { snapshot_id: parent.page?.snapshot_id, ...filters, limit: 50 });
  const [inspected, setInspected] = useState<HistoryFact | null>(null);
  const [selection, setSelection] = useState<{title: string; facts: HistoryFact[]} | null>(null);
  if (page.error) return <div role="alert"><p>{page.error}</p><button onClick={page.refresh}>Try again</button></div>;
  if (!page.view) return <p role="status">Loading records…</p>;
  const view = page.view;
  const facts = [...view.facts, ...view.undated_facts];
  const disputed = new Set(view.conflicts.flatMap(c => c.fact_ids));
  return <section aria-label="Selected history records">
    <HistoryPager view={view} onPage={page.setOffset} />
    {chart && <><p>{view.page!.total} matching records. The chart shows this page; each unit stays separate.</p>
      <HomeRecordSeries facts={facts} label={filters.label || 'Recorded values'} sourceIds={new Set(view.sources.map(s => s.id))}
        disputedIds={disputed} onSelect={rows => setSelection({title: filters.label || 'Source records',facts: rows})} /></>}
    {!facts.length && <p>No matching records in this view.</p>}
    <div className="timeline-facts">{facts.map(fact => <div key={fact.id}>
      <TimelineFact fact={fact} view={view} conflict={disputed.has(fact.id)} />
      <button className="text-button" onClick={() => setInspected(fact)}>Inspect {fact.label} source</button>
    </div>)}</div>
    <HistoryPager view={view} onPage={page.setOffset} />
    <OverviewRecordDetails view={view} selection={selection} inspected={inspected} onInspect={setInspected}
      onCloseSource={() => setInspected(null)} onCloseSelection={() => setSelection(null)} />
  </section>;
}
