import { AlertCircle, ArrowRight, History, LoaderCircle } from "lucide-react";
import type { Page } from "./Shell";
import type { View } from "./types";
import HealthRecordOverview from "./HealthRecordOverview";
import HistoryQuestionPanel from "./HistoryQuestionPanel";
import useHistoryView from "./useHistoryView";
import { dateLabel, timeLabel } from "./ui";

export default function SourceCubeHome({
  view,
  onImport,
  hasDraft,
  historical,
  onCurrent,
  onNavigate,
}: {
  view: View;
  onImport: () => void;
  hasDraft: boolean;
  historical: boolean;
  onCurrent: () => void;
  onNavigate: (page: Page) => void;
}) {
  // Generic facts use the same captured availability as the existing tools.
  // An earlier date view never silently expands to all recorded dates.
  const history = useHistoryView(view.scope, !historical);
  if (history.error)
    return (
      <section className="panel empty" role="alert">
        <AlertCircle size={24} />
        <h2>Your records could not be loaded</h2>
        <p>{history.error}</p>
        <button className="secondary" onClick={history.refresh}>
          Try again
        </button>
      </section>
    );
  if (!history.view)
    return (
      <section className="panel loading" role="status">
        <LoaderCircle size={24} className="spin" /> Loading your records…
      </section>
    );
  return (
    <div className="health-record-home">
      {historical && (
        <div className="historical-notice" role="status">
          <History size={17} />
          <span>
            Records through {dateLabel(view.scope.as_of)}. Files available
            through {timeLabel(view.scope.known_at)}.
          </span>
          <button className="text-button" onClick={onCurrent}>
            Return to today <ArrowRight size={14} />
          </button>
        </div>
      )}
      <HealthRecordOverview
        key={history.view.scope.scope_id}
        view={history.view}
        onImport={onImport}
        hasDraft={hasDraft}
        onNavigate={onNavigate}
      />
      <HistoryQuestionPanel view={history.view} />
      <div className="overview-followup">
        <button
          className="text-button"
          onClick={() => onNavigate("Measurements")}
        >
          View measurements <ArrowRight size={15} />
        </button>
      </div>
    </div>
  );
}
