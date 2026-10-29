import { ChevronRight, FileText } from "lucide-react";
import { recordLabel } from "./types";
import { unitLabel } from "./recordPresentation.mjs";
import type { HistoryFact, HistoryView } from "./historyTypes";
import type { MeasurementSummary } from "./overviewRecords";
import { dateLabel } from "./ui";

export default function LatestResultCard({ group, sources, onSource }: {
  group: MeasurementSummary;
  sources: HistoryView["sources"];
  onSource: (fact: HistoryFact) => void;
}) {
  return <>
    {group.latest.map((fact) => {
      const source = sources.find((item) => item.id === fact.source_id);
      return <button key={fact.id} className="home-value-row" type="button" onClick={() => onSource(fact)} aria-haspopup="dialog">
        <FileText size={20} strokeWidth={1.5} aria-hidden="true" focusable="false" />
        <span className="home-value-name">{recordLabel(fact.label)}</span>
        <span className="home-value-reading"><strong>{fact.value_withheld ? "Hidden by date filter" : (fact.value ?? "Not recorded")}</strong>
          {!fact.value_withheld && fact.unit && <small>{unitLabel(fact.unit)}</small>}
        </span>
        <span className="home-value-provenance"><time dateTime={group.date}>{dateLabel(group.date)}</time>
          <span title={source?.title}>{source?.title ?? "Source not recorded"}</span>
        </span>
        <ChevronRight size={16} strokeWidth={1.5} aria-hidden="true" focusable="false" />
      </button>;
    })}
    {group.latest.length > 1 && <p className="home-result-tie">{group.latest.length} records share this latest date. All are shown.</p>}
  </>;
}
