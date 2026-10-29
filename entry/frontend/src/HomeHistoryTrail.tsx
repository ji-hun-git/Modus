import { recordLabel } from "./types";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { recordHistory } from "./homeReportData";
import { dateLabel } from "./ui";
import { unitLabel } from "./recordPresentation.mjs";

export default function HomeHistoryTrail({
  anchor,
  view,
  selectedId,
  onSelect,
}: {
  anchor: HistoryFact;
  view: HistoryView;
  selectedId?: string;
  onSelect: (fact: HistoryFact) => void;
}) {
  const history = recordHistory(view, anchor);
  if (!history.length) return null;
  const disputed = new Set(view.conflicts.flatMap((group) => group.fact_ids));
  return (
    <section
      className="home-history-trail"
      aria-label={recordLabel(anchor.label) + " recorded history"}
    >
      <header>
        <h3>{recordLabel(anchor.label)} across your history</h3>
        <span>{history.length} records</span>
      </header>
      <div className="home-history-points">
        {history.map((fact) => (
          <button
            type="button"
            key={fact.id}
            className={selectedId === fact.id ? "is-selected" : ""}
            aria-pressed={selectedId === fact.id}
            onClick={() => onSelect(fact)}
            aria-label={
              "Show evidence: " +
              recordLabel(fact.label) +
              ", " +
              (fact.value_withheld
                ? "value hidden"
                : (fact.value ?? "value not recorded")) +
              " " +
              (!fact.value_withheld ? (fact.unit ?? "") : "") +
              ", " +
              dateLabel(fact.date)
            }
          >
            <time dateTime={fact.date!}>{dateLabel(fact.date)}</time>
            <span className="home-history-tick" aria-hidden="true" />
            <strong>
              {fact.value_withheld ? "Hidden" : (fact.value ?? "Not recorded")}
            </strong>
            {!fact.value_withheld && fact.unit && (
              <small>{unitLabel(fact.unit)}</small>
            )}
            {disputed.has(fact.id) && <small>Records differ</small>}
          </button>
        ))}
      </div>
    </section>
  );
}
