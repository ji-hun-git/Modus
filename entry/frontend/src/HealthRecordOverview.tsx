import { useRef, useState } from "react";
import { AlertCircle, ArrowRight, CalendarDays, Plus } from "lucide-react";
import type { Page } from "./Shell";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { recordLabel } from "./types";
import { dateLabel, timeLabel } from "./ui";
import { latestMeasurements, scopedDifferences } from "./overviewRecords";
import LatestResultCard from "./LatestResultCard";
import HomeEvidenceStack from "./HomeEvidenceStack";
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
  const sourceIds = new Set(view.sources.map((source) => source.id));
  const allFacts = [...view.facts, ...view.undated_facts].filter((fact) =>
    sourceIds.has(fact.source_id),
  );
  const measurements = latestMeasurements(view).map((group) => ({
    ...group,
    history: allFacts.filter(
      (fact) => fact.kind === "measurement" && fact.label === group.label,
    ),
  }));
  const differences = scopedDifferences(view);
  const recordedDates = allFacts
    .filter((fact) => !fact.value_withheld && fact.within_date_scope !== false)
    .flatMap((fact) => fact.date ? [fact.date] : [])
    .sort();
  const firstYear = recordedDates[0]?.slice(0, 4);
  const disputedIds = new Set(
    view.conflicts.flatMap((group) => group.fact_ids),
  );
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
        <div>
          <h1>Your record</h1>
          <p>{firstYear ? `Since ${firstYear} · ` : ""}{view.sources.length} source {view.sources.length === 1 ? "file" : "files"}</p>
        </div>
        <button className="primary" onClick={onImport}>
          <Plus size={17} />
          {hasDraft ? "Continue review" : "Add records"}
        </button>
      </div>
      {hasDraft && (
        <p className="overview-review-reminder">
          Your review is still open. Continue when you’re ready.
        </p>
      )}
      {differences.length > 0 && (
        <div className="overview-conflict-banner">
          <AlertCircle size={17} aria-hidden="true" />
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
                    {recordLabel(group.facts[0].label)} ·{" "}
                    {group.facts[0].date
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
      <div className="home-workbench">
        <section
          className="home-workbench-results"
          aria-label="Latest recorded results and history"
        >
          <header className="home-workbench-section-heading">
            <div>
              <h3>Recorded results</h3>
              <p>Select a point to open its source.</p>
            </div>
            <span>
              {Math.min(4, measurements.length)} of {measurements.length}{" "}
              measures
            </span>
          </header>
          {measurements.slice(0, 4).map((group) => (
            <LatestResultCard
              key={group.label}
              group={group}
              sourceIds={sourceIds}
              disputedIds={disputedIds}
              onSource={setInspected}
              onCompare={compare}
              onHistory={() =>
                setSelection({
                  title: `${recordLabel(group.label)} history`,
                  facts: group.history,
                })
              }
              onPoints={(facts) =>
                facts.length === 1
                  ? setInspected(facts[0])
                  : setSelection({
                      title: `${recordLabel(group.label)} · ${dateLabel(facts[0].date!)}`,
                      facts,
                    })
              }
            />
          ))}
          {!measurements.length && (
            <div className="overview-empty">
              <CalendarDays size={28} aria-hidden="true" />
              <h3>
                {view.sources.length
                  ? "Your records are ready to explore"
                  : "Start with one report"}
              </h3>
              <p>
                {view.sources.length
                  ? "Visits, prescriptions and other recorded details are available in Records."
                  : "Add a report, check the details, and keep its original connected to your history."}
              </p>
            </div>
          )}
          <footer className="home-workbench-results-footer">
            <span>
              {view.undated_facts.length
                ? `${view.undated_facts.length} records have partial or unknown dates`
                : "Points show recorded observations, not a continuous trend."}
            </span>
            <button
              className="text-button"
              onClick={() => onNavigate("Timeline")}
            >
              All records <ArrowRight size={15} />
            </button>
          </footer>
        </section>
        <HomeEvidenceStack view={view} onBrowse={() => onNavigate("Records")} />
      </div>
      <details className="home-captured-scope">
        <summary>
          {view.scope.as_of
            ? `Recorded dates through ${dateLabel(view.scope.as_of)}`
            : "All recorded dates"}{" "}
          · Available through {timeLabel(view.scope.known_at)}
        </summary>
        <p>
          Availability is when a reviewed record entered Modus. Each result
          keeps its own recorded date.
        </p>
        <code>{view.scope.known_at}</code>
      </details>
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
