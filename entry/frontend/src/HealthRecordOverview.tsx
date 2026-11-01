import { useState } from "react";
import { AlertCircle, ArrowUpRight, Plus } from "lucide-react";
import type { Page } from "./Shell";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { Modal, dateLabel } from "./ui";
import { scopedDifferences } from "./overviewRecords";
import { reportSummaries, recordHistory } from "./homeReportData";
import { recordedDate, sourceDateRange } from "./sourceDisplay";
import { recordLabel } from "./types";
import HomeReportComparison from "./HomeReportComparison";
import HomeSourceEvidence from "./HomeSourceEvidence";
import OrbitMap from "./OrbitMap";
import OverviewRecordDetails from "./OverviewRecordDetails";
import RecordConflictComparison from "./RecordConflictComparison";
import HomeIntegrityTools, { type KnowledgeMode } from "./HomeIntegrityTools";
import "./health-record-overview.css";
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
  const [evidenceId, setEvidenceId] = useState<string | null>(null);
  const [inspected, setInspected] = useState<HistoryFact | null>(null);
  const [comparison, setComparison] = useState<string | null>(null);
  const reports = reportSummaries(view);
  const report = reports.find((item) => item.source.id === sourceId) || reports[0];
  const detail = useHistoryView(view.scope, view.scope.as_of === null, { snapshot_id: view.page?.snapshot_id,
    source_id: report?.source.id, enabled: !!view.page && !!report, limit: 50 });
  const detailView = view.page ? detail.view : view;
  const [earlierOpen, setEarlierOpen] = useState(false);
  const reportFacts = view.page ? (detailView ? [...detailView.facts, ...detailView.undated_facts] : []) : report?.facts || [];
  const facts = report ? [...reportFacts].sort((a, b) => a.label.localeCompare(b.label) ||
    (b.date || "").localeCompare(a.date || "") || a.id.localeCompare(b.id)) : [];
  const anchor = facts.find((fact) => fact.id === anchorId) || facts[0];
  const evidence = anchor ? [anchor, ...recordHistory(detailView || view, anchor)].find((fact) => fact.id === evidenceId) || anchor : undefined;
  const differences = scopedDifferences(detailView || view);
  const differenceCount = view.page ? view.counts.conflicts : differences.length;
  const selectReport = (id: string) => { setSourceId(id); setAnchorId(null); setEvidenceId(null); };
  const selectEvidence = (current: HistoryFact, selected: HistoryFact) => {
    setAnchorId(current.id); setEvidenceId(selected.id);
  };
  return (
    <div className="health-record-overview orbit-overview">
      <header className="orbit-hero">
        <div><span className="orbit-eyebrow">{dateLabel(currentDay)}</span><h1>Your health history</h1></div>
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
        <OrbitMap reports={reports} total={view.page?.total} selectedId={report?.source.id} onSelect={selectReport} />
        <aside className="orbit-proof-rail" aria-label="Selected file evidence">
          <header className="orbit-proof-header"><span>In this report</span><span>{report?.count ?? facts.length} entries</span></header>
          {report ? <>
            <div className="orbit-file-heading"><h2>{report.dateRange || sourceDateRange(facts)}</h2><p title={report.source.title}>{report.source.title}</p></div>
            {view.page && !detailView && <p role={detail.error ? 'alert' : 'status'}>{detail.error || 'Loading this file…'}</p>}
            {detailView && <HistoryPager view={detailView} onPage={detail.setOffset} noun="items" />}
            <label className="orbit-record-select"><span className="sr-only">Choose a recorded item</span>
              <select aria-label="Choose a recorded item" value={anchor?.id || ''} disabled={!facts.length} onChange={(event) => {
                const selected = facts.find((fact) => fact.id === event.target.value);
                if (selected) selectEvidence(selected, selected);
              }}>
                {facts.map((fact) => <option key={fact.id} value={fact.id}>
                  {recordLabel(fact.label)}{facts.filter((other) => other.label === fact.label).length > 1 &&
                    ` · ${recordedDate(fact)} · ${fact.value_withheld ? 'Hidden by date filter' : [fact.value, fact.unit].filter(Boolean).join(' ')}`}
                </option>)}
              </select>
            </label>
            {evidence ? <div key={evidence.id} className="orbit-proof-content">
              {evidence.source_id !== report.source.id && <p className="orbit-evidence-origin">Earlier evidence · {view.sources.find((source) => source.id === evidence.source_id)?.title} · {recordedDate(evidence)}</p>}
              <HomeSourceEvidence fact={evidence} view={detailView || view} onOpen={setInspected} />
            </div> : <p className="orbit-empty-proof">No recorded items are visible from this file.</p>}
          </> : <div className="orbit-empty-proof"><h2>Your first record starts here.</h2><p>Add a report to keep its dates, results and original together.</p></div>}
        </aside>
      </div>
      <div className="sr-only" role="status">{report ? `Selected file: ${report.source.title}. ${facts.length} recorded items.` : 'No source files in this view.'}</div>
      <HomeIntegrityTools scope={view.scope} dates={dates} currentDay={currentDay}
        knowledge={knowledge} pendingCount={pendingCount} onDate={onDate}
        onNavigate={onNavigate} onReview={onImport} orbit />
      {report && <details className="orbit-report-detail" onToggle={event => setEarlierOpen(event.currentTarget.open)}><summary>Earlier results <span>Compare this report with your history</span></summary>
        {view.page ? earlierOpen && anchor && <PagedRecordList parent={view} chart={anchor.kind === 'measurement'}
          filters={{kind: anchor.kind, label: anchor.label, through: anchor.date || undefined}} /> :
          <HomeReportComparison facts={facts} view={view} anchor={anchor} evidence={evidence}
            onSelect={selectEvidence} onOpen={setInspected} onCompare={setComparison} />}
      </details>}
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
