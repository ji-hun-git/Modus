import { useState } from "react";
import { AlertCircle, ArrowUpRight, Plus } from "lucide-react";
import type { Page } from "./Shell";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { Modal, dateLabel } from "./ui";
import { scopedDifferences } from "./overviewRecords";
import { reportSummaries } from "./homeReportData";
import { recordedDate } from "./sourceDisplay";
import HomeReportReadings, { friendlyRecordName } from './HomeReportReadings';
import HomeRecordJourney from './HomeRecordJourney';
import HomeAskBar from './HomeAskBar';
import OrbitMap from "./OrbitMap";
import OverviewRecordDetails from "./OverviewRecordDetails";
import RecordConflictComparison from "./RecordConflictComparison";
import HomeIntegrityTools, { type KnowledgeMode } from "./HomeIntegrityTools";
import "./health-record-overview.css";
import './home-report-focus.css';
import useHistoryView from './useHistoryView';
import HistoryPager from './HistoryPager';
import PagedRecordList from './PagedRecordList';

export default function HealthRecordOverview({
  view, hasDraft, onImport, onNavigate, dates, currentDay, knowledge, pendingCount, onDate,
}: {
  view: HistoryView;
  hasDraft: boolean;
  onImport: () => void;
  onNavigate: (page: Page) => void;
  dates: string[];
  currentDay: string;
  knowledge: KnowledgeMode;
  pendingCount: number;
  onDate: (date: string, knowledge: KnowledgeMode) => void;
}) {
  const [sourceId, setSourceId] = useState<string | null>(null);
  const [anchorId, setAnchorId] = useState<string | null>(null);
  const [inspected, setInspected] = useState<HistoryFact | null>(null);
  const [comparison, setComparison] = useState<string | null>(null);
  const reports = reportSummaries(view);
  const report = reports.find((item) => item.source.id === sourceId) || reports[0];
  const detail = useHistoryView(view.scope, view.scope.as_of === null, { snapshot_id: view.page?.snapshot_id,
    source_id: report?.source.id, enabled: !!view.page && !!report, limit: 50 });
  const detailView = view.page ? detail.view : view;
  const reportFacts = view.page ? (detailView ? [...detailView.facts, ...detailView.undated_facts] : []) : report?.facts || [];
  const facts = report ? [...reportFacts].sort((a, b) => a.label.localeCompare(b.label) ||
    (b.date || "").localeCompare(a.date || "") || a.id.localeCompare(b.id)) : [];
  const anchor = facts.find((fact) => fact.id === anchorId) || facts[0];
  const differences = scopedDifferences(detailView || view);
  const differenceCount = view.page ? view.counts.conflicts : differences.length;
  const selectReport = (id: string) => { setSourceId(id); setAnchorId(null); setInspected(null); };
  return (
    <div className="health-record-overview orbit-overview report-first-home">
      <header className="orbit-hero">
        <div><span className="orbit-eyebrow">{dateLabel(currentDay)}</span><h1>Your history, together.</h1></div>
        <button className="primary orbit-add" onClick={onImport}>
          <Plus size={16} strokeWidth={1.25} aria-hidden="true" />
          {hasDraft ? "Continue review" : "Add records"}
        </button>
      </header>
      {!!differenceCount && <div className="overview-conflict-banner">
        <AlertCircle size={16} aria-hidden="true" />
        <p>{differenceCount === 1 ? "Recorded values differ." : `${differenceCount} recorded differences to review.`}</p>
        <button className="text-button" onClick={() => setComparison(view.page ? 'all' : differences[0].id)}>Compare <ArrowUpRight size={14} /></button>
      </div>}
      <div className="orbit-workspace">
        <section className="report-focus" aria-label="Selected report">
          {report ? <>
            <header className="report-focus-heading"><div>
              <span className="report-section-label">Your selected report</span>
              <h2>{report.latestDate ? dateLabel(report.latestDate) : 'Date not fully recorded'}</h2>
              <p>{report.source.title}</p>
            </div><span className="report-item-count">{report.count ?? facts.length} {(report.count ?? facts.length)===1?'item':'items'}</span></header>
            {view.page && !detailView && <div role={detail.error ? 'alert' : 'status'}><p>{detail.error || 'Opening your report…'}</p>
              {detail.error && <button onClick={detail.refresh}>Reload report</button>}</div>}
            {detailView && <HistoryPager view={detailView} onPage={detail.setOffset} noun="items" />}
            <HomeReportReadings facts={facts} selected={anchor} onSelect={fact=>setAnchorId(fact.id)} />
            {facts.length>4 && <label className="report-more-items">More from this report
              <select value={anchor?.id || ''} onChange={event=>setAnchorId(event.target.value)}>
                {facts.map(fact=><option key={fact.id} value={fact.id}>{friendlyRecordName(fact.label)} · {recordedDate(fact)} · {fact.value_withheld?'Hidden by date filter':fact.value ?? 'Not recorded'}</option>)}
              </select></label>}
            {anchor && <HomeRecordJourney key={anchor.id} parent={detailView || view} anchor={anchor} onOpenCurrent={()=>setInspected(anchor)} />}
            {detailView && !facts.length && <p>No recorded items are visible from this file.</p>}
          </> : <div className="orbit-empty-proof"><h2>Your first record starts here.</h2><p>Add a report to keep its dates, results and original together.</p></div>}
        </section>
        <aside className="report-orbit-navigator" aria-label="Choose another report">
          <OrbitMap reports={reports} total={view.page?.total} selectedId={report?.source.id} onSelect={selectReport} compact />
          <p className="report-orbit-instruction">Choose a file to see where it fits in your history.</p>
        </aside>
      </div>
      <div className="sr-only" role="status">{report ? !detailView && view.page ? `Opening ${report.source.title}.` : `Selected file: ${report.source.title}. ${facts.length} recorded items.` : 'No source files in this view.'}</div>
      <HomeAskBar view={view} />
      <HomeIntegrityTools scope={view.scope} dates={dates} currentDay={currentDay}
        knowledge={knowledge} pendingCount={pendingCount} onDate={onDate}
        onNavigate={onNavigate} onReview={onImport} orbit />
      <OverviewRecordDetails view={detailView || view} selection={null} inspected={inspected} onInspect={setInspected}
        onCloseSource={() => setInspected(null)} onCloseSelection={() => {}} />
      {comparison && <Modal title="Compare recorded values" onClose={() => setComparison(null)} wide>
        {differences.length > 1 && <div className="home-integrity-actions" aria-label="Choose a conflict">
          {differences.map((item, index) => <button key={item.id} type="button" className="secondary"
            aria-pressed={comparison === item.id} onClick={() => setComparison(item.id)}>Conflict {index + 1}</button>)}
        </div>}
        {view.page ? <PagedRecordList parent={view} filters={{conflicts_only:true}} /> : <RecordConflictComparison view={view} conflictId={comparison} />}
      </Modal>}
    </div>
  );
}
