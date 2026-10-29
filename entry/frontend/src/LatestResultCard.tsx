import { ArrowUpRight } from "lucide-react";
import { recordLabel } from "./types";
import { unitLabel } from "./recordPresentation.mjs";
import type { HistoryFact } from "./historyTypes";
import type { MeasurementSummary } from "./overviewRecords";
import { dateLabel } from "./ui";
import HomeRecordSeries from "./HomeRecordSeries";

export default function LatestResultCard({
  group,
  sourceIds,
  disputedIds,
  onSource,
  onHistory,
  onPoints,
  onCompare,
}: {
  group: MeasurementSummary;
  sourceIds: ReadonlySet<string>;
  disputedIds: ReadonlySet<string>;
  onSource: (fact: HistoryFact) => void;
  onHistory: () => void;
  onPoints: (facts: HistoryFact[]) => void;
  onCompare: (id: string) => void;
}) {
  return (
    <article className="home-result-row home-selected-result">
      <div className="home-result-reading">
        <div className="home-selected-heading">
          <h3>{recordLabel(group.label)}</h3>
          <p className="home-result-date">
            Latest recorded ·{" "}
            <time dateTime={group.date}>{dateLabel(group.date)}</time>
          </p>
        </div>
        <div className="home-result-values">
          {group.latest.map((fact) => (
            <button
              key={fact.id}
              type="button"
              onClick={() => onSource(fact)}
              aria-haspopup="dialog"
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
              <ArrowUpRight size={14} />
            </button>
          ))}
        </div>
        {group.latest.length > 1 && (
          <p className="home-result-tie">
            {group.latest.length} records share this latest date.
          </p>
        )}
        <div className="home-result-actions">
          <button type="button" className="text-button" onClick={onHistory}>
            Full history <ArrowUpRight size={14} />
          </button>
          {!!group.conflictIds.length && (
            <button
              type="button"
              className="text-button"
              onClick={() => onCompare(group.conflictIds[0])}
            >
              Compare records
            </button>
          )}
        </div>
      </div>
      <HomeRecordSeries
        facts={group.history}
        label={recordLabel(group.label)}
        sourceIds={sourceIds}
        disputedIds={disputedIds}
        onSelect={onPoints}
      />
    </article>
  );
}
