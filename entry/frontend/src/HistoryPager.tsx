import type { HistoryView } from './historyTypes';

export default function HistoryPager({ view, onPage, noun = 'records' }: {
  view: HistoryView; onPage: (offset: number) => void; noun?: string;
}) {
  const page = view.page;
  if (!page || page.total <= page.limit) return null;
  return <nav className="history-pagination" aria-label={`${noun} pages`}>
    <button className="text-button" disabled={page.previous_offset === null}
      onClick={() => onPage(page.previous_offset!)}>Previous {noun}</button>
    <span role="status">{page.offset + (page.returned ? 1 : 0)}–{page.offset + page.returned} of {page.total} {noun}</span>
    <button className="text-button" disabled={page.next_offset === null}
      onClick={() => onPage(page.next_offset!)}>Next {noun}</button>
  </nav>;
}
