import { useEffect } from "react";
import { AlertCircle, LoaderCircle } from "lucide-react";
import type { HistoryView } from "./historyTypes";
import type { Page } from "./Shell";
import type { View } from "./types";
import HealthRecordOverview from "./HealthRecordOverview";
import useHistoryView from "./useHistoryView";
import { recordedDates } from "./homeReportData";
import type { KnowledgeMode } from "./HomeIntegrityTools";
import HistoryPager from './HistoryPager';

export default function SourceCubeHome({
  view,
  onImport,
  hasDraft,
  historical,
  onCurrent,
  onNavigate,
  onScope,
  dates, currentDay, knowledge, pendingCount, onDate, onDates, requestedDate, loadingScope = false,
}: {
  view: View;
  onImport: () => void;
  hasDraft: boolean;
  historical: boolean;
  onCurrent: () => void;
  onNavigate: (page: Page) => void;
  onScope: (scope: HistoryView["scope"]) => void;
  dates: string[];
  currentDay: string;
  knowledge: KnowledgeMode;
  pendingCount: number;
  onDate: (date: string, knowledge: KnowledgeMode) => void;
  onDates: (dates: string[]) => void;
  requestedDate?: string;
  loadingScope?: boolean;
}) {
  // Generic facts use the same captured availability as the existing tools.
  // An earlier date view never silently expands to all recorded dates.
  const history = useHistoryView(view.scope, !historical, { section: 'sources', limit: 12, enabled: !loadingScope });
  const shown = history.view || history.retainedView;
  const updating = loadingScope || !history.view;
  useEffect(() => {
    if (history.view && !loadingScope) onScope(history.view.scope);
  }, [history.view, loadingScope, onScope]);
  useEffect(() => {
    if (history.view && !historical) onDates(history.view.facets?.date_bounds || recordedDates(history.view));
  }, [history.view, historical, onDates]);
  if (history.error)
    return (
      <section className="panel empty" role="alert">
        <AlertCircle strokeWidth={1.5} aria-hidden="true" focusable="false" size={24} />
        <h2>Your records could not be loaded</h2>
        <p>{history.error}</p>
        <button className="secondary" onClick={history.refresh}>
          Try again
        </button>
      </section>
    );
  if (!shown)
    return (
      <section className="panel loading" role="status">
        <LoaderCircle strokeWidth={1.5} aria-hidden="true" focusable="false" size={24} className="spin" /> Loading your records…
      </section>
    );
  return (
    <div className="health-record-home">
      <HealthRecordOverview
        view={shown}
        onImport={onImport}
        hasDraft={hasDraft}
        onNavigate={onNavigate}
        dates={dates} currentDay={currentDay} knowledge={knowledge}
        pendingCount={pendingCount} onDate={onDate}
        requestedDate={requestedDate} updating={updating} onCurrent={onCurrent}
      />
      <div inert={updating || undefined}><HistoryPager view={shown} onPage={history.setOffset} noun="files" /></div>
    </div>
  );
}
