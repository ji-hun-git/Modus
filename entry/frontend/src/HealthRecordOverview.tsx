import { useRef, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  CalendarDays,
  Plus,
} from "lucide-react";
import type { Page } from "./Shell";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { recordLabel } from "./types";
import { dateLabel } from "./ui";
import {
  latestMeasurements,
  scopedDifferences,
} from "./overviewRecords";
import LatestResultCard from "./LatestResultCard";
import OverviewRecordDetails from "./OverviewRecordDetails";
import RecordConflictComparison from "./RecordConflictComparison";
import "./health-record-overview.css";

export default function HealthRecordOverview({
  view,
  hasDraft,
  onImport,
  onNavigate,
}: {
  view: HistoryView;
  hasDraft: boolean;
  onImport: () => void;
  onNavigate: (page: Page) => void;
}) {
  const [inspected, setInspected] = useState<HistoryFact | null>(null);
  const [selection, setSelection] = useState<{
    title: string;
    facts: HistoryFact[];
  } | null>(null);
  const [comparison, setComparison] = useState<string | null>(null);
  const comparisonPanel = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  const measurements = latestMeasurements(view);
  const differences = scopedDifferences(view);
  const compare = (id: string) => {
    previousFocus.current = document.activeElement as HTMLElement | null;
    setComparison(id);
    requestAnimationFrame(() => {
      comparisonPanel.current?.scrollIntoView({ block: "nearest" });
      comparisonPanel.current?.focus({ preventScroll: true });
    });
  };
  const closeComparison = () => {
    setComparison(null);
    previousFocus.current?.focus();
  };
  return (
    <div className="health-record-overview">
      <div className="health-overview-toolbar">
        <h2>{measurements.length ? "Latest results" : "Your history"}</h2>
        <button className="primary" onClick={onImport}>
          <Plus size={17} /> {hasDraft ? "Continue review" : "Add records"}
        </button>
      </div>
      {hasDraft && (
        <p className="overview-review-reminder">
          Your review is still open. Continue when you’re ready.
        </p>
      )}
      {differences.length > 0 && (
        <div className="overview-conflict-banner">
          <AlertCircle size={18} aria-hidden="true" />
          <p>Some records don’t match.</p>
          <button
            className="text-button"
            onClick={() => compare(differences[0].id)}
          >
            Compare <ArrowRight size={15} />
          </button>
        </div>
      )}
      {comparison && (
        <div
          ref={comparisonPanel}
          tabIndex={-1}
          className="overview-comparison-panel"
        >
          {differences.length > 1 && (
            <label className="field overview-comparison-select">
              Records to compare
              <select
                value={comparison}
                onChange={(event) => setComparison(event.target.value)}
              >
                {differences.map((group) => (
                  <option key={group.id} value={group.id}>
                    {recordLabel(group.facts[0].label)} · {group.facts[0].date
                      ? dateLabel(group.facts[0].date)
                      : "Date not recorded"}
                  </option>
                ))}
              </select>
            </label>
          )}
          <RecordConflictComparison
            view={view}
            conflictId={comparison}
            onClose={closeComparison}
          />
        </div>
      )}
      {measurements.length > 0 && (
        <section aria-label="Latest recorded results">
          <div className="overview-result-grid">
            {measurements.slice(0, 4).map((group) => (
              <LatestResultCard
                key={group.label}
                group={group}
                onSource={setInspected}
                onCompare={compare}
                onHistory={() =>
                  setSelection({
                    title: `${recordLabel(group.label)} history`,
                    facts: group.history,
                  })
                }
              />
            ))}
          </div>
        </section>
      )}
      {!measurements.length && (
        <section className="overview-empty">
          <CalendarDays size={28} aria-hidden="true" />
          <h3>{view.sources.length ? "Your records are ready to explore" : "Bring your history together"}</h3>
          <p>
            {view.sources.length
              ? "Open Records to browse your files and their recorded details."
              : "Add a report to see its results here and keep the original close by."}
          </p>
        </section>
      )}
      <div className="overview-records-link">
        <span>{view.sources.length} {view.sources.length === 1 ? "file" : "files"} in this view</span>
        <button className="text-button" onClick={() => onNavigate("Timeline")}>
          See all records <ArrowRight size={16} />
        </button>
      </div>
      <OverviewRecordDetails
        view={view}
        selection={selection}
        inspected={inspected}
        onInspect={setInspected}
        onCloseSource={() => setInspected(null)}
        onCloseSelection={() => setSelection(null)}
      />
    </div>
  );
}
