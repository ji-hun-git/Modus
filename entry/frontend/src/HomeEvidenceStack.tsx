import { ArrowRight } from "lucide-react";
import type { HistoryView } from "./historyTypes";
import { sourceDateRange, sourceTitle } from "./sourceDisplay";
import { reportSummaries, isLatestReport } from "./homeReportData";
import { recordLabel } from "./types";
import SourceGlyph, { sourceKind } from "./svg/SourceGlyph";

export default function HomeEvidenceStack({
  view,
  selectedId,
  onSelect,
  onBrowse,
}: {
  view: HistoryView;
  selectedId?: string;
  onSelect: (id: string) => void;
  onBrowse: () => void;
}) {
  const reports = reportSummaries(view);
  return (
    <section
      className="home-report-shelf"
      aria-label="Choose a report from your history"
    >
      <header>
        <div>
          <h2>Your reports</h2>
          <span>Open any report in context</span>
        </div>
        <button type="button" className="text-button" onClick={onBrowse}>
          All records{" "}
          <ArrowRight
            size={15}
            strokeWidth={1.5}
            aria-hidden="true"
            focusable="false"
          />
        </button>
      </header>
      <div className="home-report-files">
        {reports.map((report) => {
          const { source, facts } = report;
          return (
            <button
              type="button"
              key={source.id}
              className={
                "home-report-file" +
                (selectedId === source.id ? " is-selected" : "")
              }
              aria-pressed={selectedId === source.id}
              aria-label={
                "Open report: " +
                sourceTitle(facts) +
                ", " +
                sourceDateRange(facts) +
                ", " +
                source.title
              }
              onClick={() => onSelect(source.id)}
            >
              <span className="home-report-file-mark">
                <SourceGlyph
                  kind={sourceKind(source.type, source.title)}
                  size={26}
                />
                {isLatestReport(reports, report) && <small>Latest dated</small>}
              </span>
              <strong>{sourceDateRange(facts)}</strong>
              <span>{sourceTitle(facts)}</span>
              <small>
                {[...new Set(facts.map((fact) => recordLabel(fact.label)))]
                  .slice(0, 3)
                  .join(" · ") || "No items in this view"}
                {new Set(facts.map((f) => f.label)).size > 3 ? " …" : ""}
              </small>
            </button>
          );
        })}
      </div>
    </section>
  );
}
