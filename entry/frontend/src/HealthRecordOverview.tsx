import { useRef, useState } from "react";
import { AlertCircle, ArrowRight, Plus } from "lucide-react";
import type { Page } from "./Shell";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { dateLabel, timeLabel, Modal } from "./ui";
import { scopedDifferences } from "./overviewRecords";
import {
  reportSummaries,
  recordHistory,
  isLatestReport,
} from "./homeReportData";
import { sourceDateRange, sourceTitle } from "./sourceDisplay";
import HomeReportComparison from "./HomeReportComparison";
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
  const [sourceId, setSourceId] = useState<string | null>(null);
  const [anchorId, setAnchorId] = useState<string | null>(null);
  const [evidenceId, setEvidenceId] = useState<string | null>(null);
  const [inspected, setInspected] = useState<HistoryFact | null>(null);
  const [comparison, setComparison] = useState<string | null>(null);
  const reportHeading = useRef<HTMLHeadingElement>(null);
  const reports = reportSummaries(view);
  const report =
    reports.find((item) => item.source.id === sourceId) || reports[0];
  const facts = report
    ? [...report.facts].sort(
        (a, b) =>
          a.label.localeCompare(b.label) ||
          (b.date || "").localeCompare(a.date || "") ||
          a.id.localeCompare(b.id),
      )
    : [];
  const anchor = facts.find((fact) => fact.id === anchorId) || facts[0];
  const evidence = anchor
    ? [anchor, ...recordHistory(view, anchor)].find(
        (fact) => fact.id === evidenceId,
      ) || anchor
    : undefined;
  const differences = scopedDifferences(view);
  const isLatest = report ? isLatestReport(reports, report) : false;
  const selectReport = (id: string) => {
    setSourceId(id);
    setAnchorId(null);
    setEvidenceId(null);
    requestAnimationFrame(() => {
      reportHeading.current?.scrollIntoView({ block: "start" });
      reportHeading.current?.focus({ preventScroll: true });
    });
  };
  const selectEvidence = (current: HistoryFact, selected: HistoryFact) => {
    setAnchorId(current.id);
    setEvidenceId(selected.id);
  };
  return (
    <div className="health-record-overview">
      <header className="home-report-hero">
        <div>
          <span className="home-report-eyebrow">
            {report
              ? isLatest && report.latestDate
                ? "Your latest recorded results"
                : "From your history"
              : "Your history starts here"}
          </span>
          <h1 ref={reportHeading} tabIndex={-1}>
            {report ? sourceDateRange(facts) : "Bring your records together."}
          </h1>
          <p>
            {report ? (
              <>
                {sourceTitle(facts)} <span>·</span> {facts.length} recorded{" "}
                {facts.length === 1 ? "item" : "items"}
              </>
            ) : (
              "Add a report. Keep every detail connected to its source."
            )}
          </p>
        </div>
        <div className="home-report-actions">
          <button className="primary" onClick={onImport}>
            <Plus
              size={18}
              strokeWidth={1.5}
              aria-hidden="true"
              focusable="false"
            />
            {hasDraft ? "Continue review" : "Add records"}
          </button>
          <details className="home-captured-scope">
            <summary>
              View as of {dateLabel(view.scope.known_at.slice(0, 10))}
            </summary>
            <dl>
              <dt>Recorded dates</dt>
              <dd>
                {view.scope.as_of
                  ? "Through " + dateLabel(view.scope.as_of)
                  : "All recorded dates"}
              </dd>
              <dt>Files available through</dt>
              <dd>
                {timeLabel(view.scope.known_at)}
                <br />
                <code>{view.scope.known_at}</code>
              </dd>
            </dl>
          </details>
        </div>
      </header>
      {!isLatest && reports[0] && (
        <button
          className="text-button home-return-latest"
          onClick={() => selectReport(reports[0].source.id)}
        >
          Return to latest recorded results{" "}
          <ArrowRight
            size={15}
            strokeWidth={1.5}
            aria-hidden="true"
            focusable="false"
          />
        </button>
      )}
      {hasDraft && (
        <p className="overview-review-reminder">
          Your review is still open. Continue when you’re ready.
        </p>
      )}
      {!!differences.length && (
        <div className="overview-conflict-banner">
          <AlertCircle
            size={17}
            strokeWidth={1.5}
            aria-hidden="true"
            focusable="false"
          />
          <p>Some records don’t match. Both versions are preserved.</p>
          <button
            className="text-button"
            onClick={() => setComparison(differences[0].id)}
          >
            Compare{" "}
            <ArrowRight
              size={15}
              strokeWidth={1.5}
              aria-hidden="true"
              focusable="false"
            />
          </button>
        </div>
      )}
      {report && (
        <HomeReportComparison
          facts={facts}
          view={view}
          anchor={anchor}
          evidence={evidence}
          onSelect={selectEvidence}
          onOpen={setInspected}
          onCompare={setComparison}
        />
      )}
      {!!reports.length && (
        <HomeEvidenceStack
          view={view}
          selectedId={report?.source.id}
          onSelect={selectReport}
          onBrowse={() => onNavigate("Timeline")}
        />
      )}
      <OverviewRecordDetails
        view={view}
        selection={null}
        inspected={inspected}
        onInspect={setInspected}
        onCloseSource={() => setInspected(null)}
        onCloseSelection={() => {}}
      />
      {comparison && (
        <Modal
          title="Compare recorded values"
          onClose={() => setComparison(null)}
          wide
        >
          <RecordConflictComparison view={view} conflictId={comparison} />
        </Modal>
      )}
    </div>
  );
}
