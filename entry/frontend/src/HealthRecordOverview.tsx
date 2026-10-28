import { useRef, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  Plus,
} from "lucide-react";
import type { Page } from "./Shell";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { recordLabel } from "./types";
import { unitLabel } from "./recordPresentation.mjs";
import { dateLabel } from "./ui";
import {
  latestMeasurements,
  recordDays,
  scopedDifferences,
} from "./overviewRecords";
import LatestResultCard from "./LatestResultCard";
import OverviewRecordDetails from "./OverviewRecordDetails";
import OverviewRecordLists from "./OverviewRecordLists";
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
  const days = recordDays(view);
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
        <p>Results and records by date</p>
        <button className="primary" onClick={onImport}>
          <Plus size={17} /> {hasDraft ? "Continue review" : "Add records"}
        </button>
      </div>
      {hasDraft && (
        <div className="overview-review-reminder">
          <strong>Your record review is still open.</strong>
          <span>Finish checking the proposed fields before adding them.</span>
        </div>
      )}
      {differences.length > 0 && (
        <section
          className="overview-differences"
          aria-labelledby="overview-differences-title"
        >
          <div className="overview-section-heading">
            <h2 id="overview-differences-title">Records to compare</h2>
            <span>
              {differences.length}{" "}
              {differences.length === 1 ? "group" : "groups"}
            </span>
          </div>
          {differences.map((group) => (
            <article className="overview-difference" key={group.id}>
              <AlertCircle size={19} />
              <div>
                <h3>
                  {recordLabel(group.facts[0].label)}
                  <span>
                    {group.facts[0].date
                      ? dateLabel(group.facts[0].date)
                      : "Date not recorded"}
                  </span>
                </h3>
                <p>
                  {group.reason === "different_recorded_units"
                    ? "Different printed units"
                    : "Different recorded values"}
                  :{" "}
                  {group.facts.map((fact, index) => (
                    <span key={fact.id}>
                      {index > 0 ? " · " : ""}
                      {fact.value_withheld
                        ? "Hidden by date filter"
                        : (fact.value ?? "Not recorded")}
                      {!fact.value_withheld && fact.unit
                        ? ` ${unitLabel(fact.unit)}`
                        : ""}
                    </span>
                  ))}
                </p>
              </div>
              <button className="secondary" onClick={() => compare(group.id)}>
                Compare records <ArrowUpRight size={14} />
              </button>
            </article>
          ))}
        </section>
      )}
      {comparison && (
        <div
          ref={comparisonPanel}
          tabIndex={-1}
          className="overview-comparison-panel"
        >
          <RecordConflictComparison
            view={view}
            conflictId={comparison}
            onClose={closeComparison}
          />
        </div>
      )}
      {measurements.length > 0 && (
        <section aria-labelledby="overview-results-title">
          <div className="overview-section-heading">
            <h2 id="overview-results-title">Latest test results</h2>
            <span>Each result keeps its own date</span>
          </div>
          <div className="overview-result-grid">
            {measurements.slice(0, 6).map((group) => (
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
          {measurements.length > 6 && (
            <button
              className="text-button overview-more-results"
              onClick={() =>
                setSelection({
                  title: "Dated test results",
                  facts: measurements
                    .flatMap((group) => group.history)
                    .sort((a, b) => b.date!.localeCompare(a.date!)),
                })
              }
            >
              View all test results <ArrowRight size={14} />
            </button>
          )}
        </section>
      )}
      <OverviewRecordLists
        days={days}
        undated={view.undated_facts}
        onInspect={setInspected}
        onSelect={setSelection}
        onNavigate={onNavigate}
      />
      {!days.length && !view.undated_facts.length && (
        <section className="overview-empty">
          <CalendarDays size={30} />
          <h2>Your records will appear here</h2>
          <p>Add a report and review its recorded results, dates and source.</p>
          <button className="secondary" onClick={onImport}>
            Add your first record
          </button>
        </section>
      )}
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
