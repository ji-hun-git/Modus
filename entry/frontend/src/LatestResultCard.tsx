import { ArrowUpRight, Files } from "lucide-react";
import { metricDescription, recordLabel } from "./types";
import { unitLabel } from "./recordPresentation.mjs";
import type { HistoryFact } from "./historyTypes";
import type { MeasurementSummary } from "./overviewRecords";
import { dateLabel } from "./ui";
import "./latest-results.css";

export default function LatestResultCard({
  group,
  onSource,
  onHistory,
  onCompare,
}: {
  group: MeasurementSummary;
  onSource: (fact: HistoryFact) => void;
  onHistory: () => void;
  onCompare: (id: string) => void;
}) {
  const description = metricDescription(group.label);
  return (
    <article className="latest-result-card">
      <h3>{recordLabel(group.label)}</h3>
      <div className="latest-result-values">
        {group.latest.map((fact) => (
          <button
            key={fact.id}
            type="button"
            className="latest-result-value"
            onClick={() => onSource(fact)}
            aria-label={`View source for ${recordLabel(fact.label)}, ${fact.value_withheld ? "value hidden by date filter" : `${fact.value ?? "value not recorded"} ${fact.unit || ""}`}, measured ${dateLabel(group.date)}`}
          >
            <strong>
              {fact.value_withheld
                ? "Hidden by date filter"
                : (fact.value ?? "Not recorded")}
            </strong>
            {!fact.value_withheld && fact.unit && (
              <span>{unitLabel(fact.unit)}</span>
            )}
            <ArrowUpRight size={15} />
          </button>
        ))}
      </div>
      <p className="latest-result-date">
        Measured <time dateTime={group.date}>{dateLabel(group.date)}</time>
      </p>
      {description && (
        <p className="latest-result-description">{description}</p>
      )}
      {group.latest.length > 1 && (
        <p className="latest-result-multiple">
          <Files size={14} /> {group.latest.length} records on this date
        </p>
      )}
      <footer>
        {group.conflictIds.length ? (
          <button
            type="button"
            className="text-button"
            onClick={() => onCompare(group.conflictIds[0])}
          >
            Compare records <ArrowUpRight size={14} />
          </button>
        ) : (
          <button type="button" className="text-button" onClick={onHistory}>
            View history <ArrowUpRight size={14} />
          </button>
        )}
      </footer>
    </article>
  );
}
