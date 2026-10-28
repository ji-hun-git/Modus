import { ArrowUpRight } from "lucide-react";
import { Modal, dateLabel } from "./ui";
import { recordLabel } from "./types";
import { unitLabel, facilityLabel } from "./recordPresentation.mjs";
import type { HistoryFact, HistoryView } from "./historyTypes";
import SourceCubeEvidence from "./SourceCubeEvidence";
import { currentOverviewFacts } from "./overviewRecords";

export default function OverviewRecordDetails({
  view,
  selection,
  inspected,
  onInspect,
  onCloseSource,
  onCloseSelection,
}: {
  view: HistoryView;
  selection: { title: string; facts: HistoryFact[] } | null;
  inspected: HistoryFact | null;
  onInspect: (fact: HistoryFact) => void;
  onCloseSource: () => void;
  onCloseSelection: () => void;
}) {
  if (inspected) {
    const current = currentOverviewFacts(view, [inspected.id])[0];
    if (!current)
      return (
        <Modal title="Record unavailable" onClose={onCloseSource}>
          <p>This record is not available in the selected history view.</p>
        </Modal>
      );
    const source = view.sources.find((item) => item.id === current.source_id);
    const facts = [...view.facts, ...view.undated_facts].filter(
      (fact) => fact.source_id === current.source_id,
    );
    return (
      <Modal
        title={`${recordLabel(current.label)} · ${current.date ? dateLabel(current.date) : current.occurred_on || "Date not recorded"}`}
        onClose={onCloseSource}
      >
        {source ? (
          <SourceCubeEvidence
            source={source}
            facts={facts}
            view={view}
            initialFactId={current.id}
          />
        ) : (
          <p>This source is not available in the selected history view.</p>
        )}
      </Modal>
    );
  }
  if (!selection) return null;
  const visible = currentOverviewFacts(
    view,
    selection.facts.map((fact) => fact.id),
  );
  return (
    <Modal
      title={visible.length ? selection.title : "Records unavailable"}
      onClose={onCloseSelection}
    >
      <div className="overview-record-details">
        {!visible.length && (
          <p>These records are not available in the selected history view.</p>
        )}
        {visible.map((fact) => (
          <article key={fact.id}>
            <div>
              <h3>{recordLabel(fact.label)}</h3>
              <p>
                {fact.date
                  ? dateLabel(fact.date)
                  : fact.occurred_on || "Date not recorded"}
              </p>
            </div>
            <p className="overview-detail-value">
              {fact.value_withheld
                ? "Hidden by date filter"
                : (fact.value ?? "Not recorded")}
              {!fact.value_withheld && fact.unit && (
                <span> {unitLabel(fact.unit)}</span>
              )}
            </p>
            {facilityLabel(fact.facility) && (
              <p className="overview-detail-facility">
                {facilityLabel(fact.facility)}
              </p>
            )}
            <button
              type="button"
              className="text-button"
              onClick={() => onInspect(fact)}
            >
              View source <ArrowUpRight size={14} />
            </button>
          </article>
        ))}
      </div>
    </Modal>
  );
}
