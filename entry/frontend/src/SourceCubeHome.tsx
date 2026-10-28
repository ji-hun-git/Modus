import type { ReactNode } from "react";
import { AlertCircle, ArrowRight, History, LoaderCircle } from "lucide-react";
import type { Page } from "./Shell";
import type { View } from "./types";
import SourceCubeOverview from "./SourceCubeOverview";
import useHistoryView from "./useHistoryView";
import { dateLabel, timeLabel } from "./ui";

export default function SourceCubeHome({
  view, onImport, hasDraft, historical, onCurrent, onNavigate, children,
}: {
  view: View;
  onImport: () => void;
  hasDraft: boolean;
  historical: boolean;
  onCurrent: () => void;
  onNavigate: (page: Page) => void;
  children: ReactNode;
}) {
  // Generic facts use the same captured availability as the existing tools.
  // An earlier date view never silently expands to all recorded dates.
  const history = useHistoryView(view.scope, !historical);
  if (history.error) return (
    <section className="panel empty" role="alert">
      <AlertCircle size={24} />
      <h2>Your files could not be loaded</h2>
      <p>{history.error}</p>
      <button className="secondary" onClick={history.refresh}>Try again</button>
    </section>
  );
  if (!history.view) return (
    <section className="panel loading" role="status">
      <LoaderCircle size={24} className="spin" /> Loading your files…
    </section>
  );
  return (
    <div className="source-home">
      {historical && (
        <div className="historical-notice" role="status">
          <History size={17} />
          <span>Records through {dateLabel(view.scope.as_of)}. Files available through {timeLabel(view.scope.known_at)}.</span>
          <button className="text-button" onClick={onCurrent}>Return to today <ArrowRight size={14} /></button>
        </div>
      )}
      <SourceCubeOverview view={history.view} onImport={onImport} hasDraft={hasDraft} onNavigate={onNavigate} />
      <div className="source-home-followup">
        <details className="source-home-assistant">
          <summary>Ask about recorded measurements <ArrowRight size={16} /></summary>
          {children}
        </details>
        <button className="text-button" onClick={() => onNavigate("Measurements")}>Open measurement charts <ArrowRight size={15} /></button>
      </div>
    </div>
  );
}
