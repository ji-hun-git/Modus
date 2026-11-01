import { useState } from 'react';
import type { HistoryView } from './historyTypes';
import { Modal } from './ui';
import PagedRecordList from './PagedRecordList';
import { api } from './api';

export default function PagedFiles({ view }: { view: HistoryView }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [exporting, setExporting] = useState(false);
  async function exportAll() {
    setExporting(true); setError('');
    try {
      const query = new URLSearchParams({known_at: view.scope.known_at});
      if (view.scope.as_of) query.set('as_of',view.scope.as_of);
      const all = await api<HistoryView>(`/history/view?${query}`);
      const url = URL.createObjectURL(new Blob([JSON.stringify(all,null,2)],{type:'application/json'}));
      const link=document.createElement('a'); link.href=url; link.download='modus-history.json'; link.click(); URL.revokeObjectURL(url);
    } catch (err) { setError((err as Error).message); } finally { setExporting(false); }
  }
  const source = view.sources.find(s => s.id === selected);
  return <section aria-label="Original documents">
    <header className="timeline-heading"><h2>{view.page?.total} source files</h2>
      <button className="text-button" disabled={exporting} onClick={() => void exportAll()}>{exporting ? 'Preparing complete export…' : 'Export complete view'}</button></header>
    {error && <p role="alert">{error}</p>}
    <div className="history-files-list">{view.sources.map(s => <article className="history-file" key={s.id}>
      <h3>{s.title}</h3><p>{s.fact_count} recorded items · {s.first_date || 'Date not fully recorded'}{s.latest_date !== s.first_date ? ` – ${s.latest_date || ''}` : ''}</p>
      <button className="text-button" onClick={() => setSelected(s.id)}>Open {s.title}</button>
    </article>)}</div>
    {source && <Modal title={source.title} onClose={() => setSelected(null)} wide>
      <PagedRecordList parent={view} filters={{source_id:source.id}} />
    </Modal>}
  </section>;
}
