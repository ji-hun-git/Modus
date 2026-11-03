import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, FileText, GitCompareArrows, Inbox, Plus } from "lucide-react";
import type { Page } from "./Shell";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { Modal, dateLabel } from "./ui";
import { scopedDifferences } from "./overviewRecords";
import { reportSummaries } from "./homeReportData";
import HomeReportReadings from './HomeReportReadings';
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
import ReportComparison from './ReportComparison';
import LongitudinalWorkspace from './LongitudinalWorkspace';
import HomeReportEvidence from './HomeReportEvidence';

export default function HealthRecordOverview({
  view, hasDraft, onImport, onNavigate, dates, currentDay, knowledge, pendingCount, onDate,
  requestedDate, updating = false, onCurrent,
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
  requestedDate?: string;
  updating?: boolean;
  onCurrent?: () => void;
}) {
  const [sourceId, setSourceId] = useState<string | null>(null);
  const [anchorId, setAnchorId] = useState<string | null>(null);
  const [expandedPage, setExpandedPage] = useState<string | null>(null);
  const [journeyOpen, setJourneyOpen] = useState(false);
  const homeRef = useRef<HTMLDivElement>(null);
  const [inspected, setInspected] = useState<HistoryFact | null>(null);
  const [comparison, setComparison] = useState<string | null>(null);
  const [reportComparisonOpen, setReportComparisonOpen] = useState(false);
  const [scrubTarget, setScrubTarget] = useState<string | null>(null);
  const timeUpdating = updating || !!scrubTarget && scrubTarget !== (view.scope.as_of || currentDay);
  useEffect(() => {
    setSourceId(null); setAnchorId(null); setExpandedPage(null); setJourneyOpen(false);
    setInspected(null); setComparison(null); setReportComparisonOpen(false);
  }, [view.scope.scope_id]);
  useEffect(() => {
    if (timeUpdating) { setInspected(null); setComparison(null); setReportComparisonOpen(false); }
  }, [timeUpdating]);
  const reports = reportSummaries(view);
  const report = reports.find((item) => item.source.id === sourceId) || reports[0];
  const detail = useHistoryView(view.scope, view.scope.as_of === null, { snapshot_id: view.page?.snapshot_id,
    source_id: report?.source.id, enabled: !!view.page && !!report, limit: 50 });
  const detailView = view.page ? detail.view : view;
  const reportFacts = view.page ? (detailView ? [...detailView.facts, ...detailView.undated_facts] : []) : report?.facts || [];
  const facts = report ? [...reportFacts].sort((a, b) => a.label.localeCompare(b.label) ||
    (b.date || "").localeCompare(a.date || "") || a.id.localeCompare(b.id)) : [];
  const anchor = facts.find((fact) => fact.id === anchorId) || facts[0];
  const reportPage = `${report?.source.id}:${detailView?.scope.scope_id}:${detailView?.page?.offset ?? 0}`;
  const differences = scopedDifferences(detailView || view);
  const differenceCount = view.page ? view.counts.conflicts : differences.length;
  const selectReport = (id: string) => {
    setSourceId(id); setAnchorId(null); setJourneyOpen(false); setInspected(null);
    requestAnimationFrame(() => {
      if (window.matchMedia('(max-width:900px)').matches) {
        const dock = homeRef.current?.querySelector<HTMLElement>('.report-focus');
        dock?.scrollIntoView({ block: 'start' });
        dock?.focus({ preventScroll: true });
      }
    });
  };
  return (
    <div ref={homeRef} className="health-record-overview orbit-overview report-first-home orbit-centered-home">
      <header className="orbit-hero">
        <div><span className="orbit-eyebrow">{dateLabel(currentDay)}</span><h1>Your medical history.</h1></div>
        <button className="primary orbit-add" onClick={onImport}
          aria-label={hasDraft && pendingCount > 0 ? `Continue review, ${pendingCount} ${pendingCount===1?'file':'files'}` : undefined}
          title={hasDraft ? 'Continue unfinished files in this tab' : undefined}>
          {hasDraft ? <Inbox size={16} strokeWidth={1.25} aria-hidden="true" /> : <Plus size={16} strokeWidth={1.25} aria-hidden="true" />}
          {hasDraft ? "Continue review" : "Add records"}
          {hasDraft && pendingCount > 0 && <span className="home-review-count" aria-hidden="true">{pendingCount}</span>}
        </button>
      </header>
      <HomeIntegrityTools scope={view.scope} dates={dates} currentDay={currentDay}
        knowledge={knowledge} pendingCount={pendingCount} onDate={onDate}
        onNavigate={onNavigate} onReview={onImport} requestedDate={requestedDate}
        updating={timeUpdating} onPreview={setScrubTarget} onCurrent={onCurrent} orbit />
      <div className={timeUpdating ? 'home-evidence-surface is-time-updating' : 'home-evidence-surface'} aria-busy={timeUpdating} inert={timeUpdating || undefined}>
      <div className="home-record-actions" role="group" aria-label="Actions for your history">
        {!!differenceCount && <button type="button" className="text-button"
          aria-label={`Review ${differenceCount} recorded ${differenceCount===1?'difference':'differences'}`}
          onClick={() => setComparison(view.page ? 'all' : differences[0].id)}>
          <GitCompareArrows size={15} aria-hidden="true" /> Review differences <span>{differenceCount}</span>
        </button>}
        <button type="button" className="text-button home-summary-action" onClick={() => onNavigate('Brief')}>
          <FileText size={15} aria-hidden="true" /> Prepare a summary
        </button>
      </div>
      {anchor && journeyOpen && anchor.kind==='measurement' ? <LongitudinalWorkspace key={`${view.page?.snapshot_id}:${anchor.id}`}
        parent={view} anchor={anchor} onCompare={()=>setReportComparisonOpen(true)} onClose={()=>{
          setJourneyOpen(false);requestAnimationFrame(()=>homeRef.current?.querySelector<HTMLElement>('.report-focus')?.focus());
        }} files={<OrbitMap reports={reports} total={view.page?.total} selectedId={report?.source.id} onSelect={selectReport} compact />} /> : <div className="orbit-workspace">
        <section className="home-orbit-stage" aria-label="Your history in orbit">
          <OrbitMap reports={reports} total={view.page?.total} selectedId={report?.source.id}
            onSelect={selectReport} prominent onOpenAll={() => onNavigate('Records')} />
          <HomeAskBar view={view} />
        </section>
        <section id="home-selected-report" className="report-focus" aria-label="Selected report" tabIndex={-1}>
          <button type="button" className="text-button report-back-to-orbit" onClick={() => {
            const selected = homeRef.current?.querySelector<SVGGElement>('.home-orbit-stage .orbit-satellite.is-selected');
            homeRef.current?.querySelector('.home-orbit-stage')?.scrollIntoView({ block: 'start' });
            selected?.focus({ preventScroll: true });
          }}>Back to files</button>
          {report ? <>
            <header className="report-focus-heading"><div>
              <span className="report-section-label">Your selected report</span>
              <h2>{report.latestDate ? dateLabel(report.latestDate) : 'Date not fully recorded'}</h2>
            </div><div className="report-focus-actions"><span className="report-item-count">{report.count ?? facts.length} {(report.count ?? facts.length)===1?'entry':'entries'}</span>
              <button type="button" className="text-button" disabled={!view.page?.snapshot_id}
                title={!view.page?.snapshot_id?'Refresh your history to compare reports':undefined}
                onClick={()=>setReportComparisonOpen(true)}>Compare reports</button>
            </div><p>{report.source.title}</p></header>
            {view.page && !detailView && <div role={detail.error ? 'alert' : 'status'}><p>{detail.error || 'Opening your report…'}</p>
              {detail.error && <button onClick={detail.refresh}>Reload report</button>}</div>}
            {detailView && <HistoryPager view={detailView} onPage={detail.setOffset} noun="items" />}
            <HomeReportReadings facts={facts} selected={anchor} onSelect={fact=>setAnchorId(fact.id)}
              expanded={expandedPage===reportPage} onToggle={()=>setExpandedPage(expandedPage===reportPage?null:reportPage)}
              paged={(detailView?.page?.total ?? facts.length)>facts.length} />
            {anchor && detailView && <>
              <HomeReportEvidence fact={anchor} view={detailView} onOpen={setInspected} />
              {!journeyOpen && <button type="button" className="text-button report-history-open"
                onClick={() => setJourneyOpen(true)}>View this record across my history <ArrowUpRight size={14} aria-hidden="true" /></button>}
            </>}
            {anchor && journeyOpen && <div className="report-expanded-history">
              <button type="button" className="text-button" onClick={()=>{
                homeRef.current?.querySelector<HTMLButtonElement>('.report-reading-choice[aria-pressed="true"]')?.focus();
                setJourneyOpen(false);
              }}>Close history</button>
              <HomeRecordJourney key={anchor.id} parent={detailView || view} anchor={anchor} onOpenCurrent={()=>setInspected(anchor)} />
            </div>}
            {detailView && !facts.length && <p>No recorded items are visible from this file.</p>}
          </> : <div className="orbit-empty-proof"><h2>Start with a medical report.</h2><p>Add a checkup, lab report or visit record. Review it once, then find it in your history.</p></div>}
        </section>
      </div>}
      </div>
      <div className="sr-only" role="status">{report ? !detailView && view.page ? `Opening ${report.source.title}.` : `Selected file: ${report.source.title}. ${facts.length} recorded items.` : 'No source files in this view.'}</div>
      <OverviewRecordDetails view={detailView || view} selection={null} inspected={inspected} onInspect={setInspected}
        onCloseSource={() => setInspected(null)} onCloseSelection={() => {}} />
      {reportComparisonOpen && report && <ReportComparison key={`${view.page?.snapshot_id}:${report.source.id}`}
        view={view} selectedSource={report.source} onClose={()=>setReportComparisonOpen(false)} />}
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
