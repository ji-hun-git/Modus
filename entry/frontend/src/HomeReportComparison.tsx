import { useRef } from "react";
import { ArrowRight, ChevronRight } from "lucide-react";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { recordLabel } from "./types";
import { unitLabel } from "./recordPresentation.mjs";
import { recordedDate } from "./sourceDisplay";
import { previousRecords } from "./homeReportData";
import HomeSourceEvidence from "./HomeSourceEvidence";
import HomeHistoryTrail from "./HomeHistoryTrail";

function Reading({
  fact,
  selected,
  onSelect,
}: {
  fact: HistoryFact;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      className={"home-reading" + (selected ? " is-selected" : "")}
      aria-pressed={selected}
      onClick={onSelect}
      aria-label={
        "Show source: " +
        recordLabel(fact.label) +
        ", " +
        (fact.value_withheld
          ? "value hidden by date filter"
          : (fact.value ?? "value not recorded")) +
        " " +
        (!fact.value_withheld ? (fact.unit ?? "") : "") +
        ", " +
        recordedDate(fact)
      }
    >
      <span>
        <strong>
          {fact.value_withheld
            ? "Hidden by date filter"
            : (fact.value ?? "Not recorded")}
        </strong>
        {!fact.value_withheld && fact.unit && (
          <small>{unitLabel(fact.unit)}</small>
        )}
      </span>
      <time dateTime={fact.date || undefined}>{recordedDate(fact)}</time>
    </button>
  );
}

export default function HomeReportComparison({
  facts,
  view,
  anchor,
  evidence,
  onSelect,
  onOpen,
  onCompare,
}: {
  facts: HistoryFact[];
  view: HistoryView;
  anchor?: HistoryFact;
  evidence?: HistoryFact;
  onSelect: (anchor: HistoryFact, evidence: HistoryFact) => void;
  onOpen: (fact: HistoryFact) => void;
  onCompare: (id: string) => void;
}) {
  const mobileProof = useRef<HTMLDivElement>(null);
  return (
    <div className="home-report-workspace">
      <section
        className="home-report-values"
        aria-label="This report compared with earlier records"
      >
        <header className="home-report-values-heading">
          <h2>What changed</h2>
          <span>
            Select a value to see its source{" "}
            <ArrowRight
              size={14}
              strokeWidth={1.5}
              aria-hidden="true"
              focusable="false"
            />
          </span>
        </header>
        <div className="home-comparison-head" aria-hidden="true">
          <span>Recorded item</span>
          <span>Earlier</span>
          <span>This report</span>
        </div>
        {facts.map((fact) => {
          const previous = previousRecords(view, fact);
          const unitsDiffer = previous.some((item) => item.unit !== fact.unit);
          const conflict = view.conflicts.find((group) =>
            [fact, ...previous].some((item) =>
              group.fact_ids.includes(item.id),
            ),
          );
          const active = anchor?.id === fact.id;
          return (
            <div
              key={fact.id}
              className={"home-comparison-item" + (active ? " is-active" : "")}
            >
              <div className="home-comparison-row">
                <button
                  type="button"
                  className="home-comparison-label"
                  aria-pressed={active}
                  onClick={() => onSelect(fact, fact)}
                >
                  {recordLabel(fact.label)}
                </button>
                <div className="home-comparison-earlier">
                  {previous.length ? (
                    previous.map((item) => (
                      <Reading
                        key={item.id}
                        fact={item}
                        selected={active && evidence?.id === item.id}
                        onSelect={() => onSelect(fact, item)}
                      />
                    ))
                  ) : (
                    <p className="home-no-earlier">
                      {fact.date
                        ? "No earlier dated record"
                        : "Date not recorded"}
                    </p>
                  )}
                </div>
                <div className="home-comparison-current">
                  <Reading
                    fact={fact}
                    selected={active && evidence?.id === fact.id}
                    onSelect={() => onSelect(fact, fact)}
                  />
                </div>
              </div>
              {(unitsDiffer || previous.length > 1 || conflict) && (
                <div className="home-comparison-note">
                  {unitsDiffer && <span>Different recorded units.</span>}
                  {previous.length > 1 && (
                    <span>
                      {previous.length} earlier records share this date; all
                      shown.
                    </span>
                  )}
                  {conflict && (
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => onCompare(conflict.id)}
                    >
                      Records differ{" "}
                      <ChevronRight
                        size={14}
                        strokeWidth={1.5}
                        aria-hidden="true"
                        focusable="false"
                      />
                    </button>
                  )}
                </div>
              )}
              {active && evidence && (
                <div className="home-proof-mobile" ref={mobileProof}>
                  <HomeSourceEvidence
                    fact={evidence}
                    view={view}
                    onOpen={onOpen}
                  />
                </div>
              )}
            </div>
          );
        })}
        {!facts.length && (
          <p className="home-no-facts">
            No recorded items are available from this file in this view.
          </p>
        )}
        {anchor && (
          <HomeHistoryTrail
            anchor={anchor}
            view={view}
            selectedId={evidence?.id}
            onSelect={(fact) => {
              onSelect(anchor, fact);
              if (window.matchMedia("(max-width:767px)").matches)
                requestAnimationFrame(() =>
                  mobileProof.current?.scrollIntoView({ block: "nearest" }),
                );
            }}
          />
        )}
      </section>
      <aside className="home-proof-desktop">
        {evidence ? (
          <HomeSourceEvidence fact={evidence} view={view} onOpen={onOpen} />
        ) : (
          <p>Select a recorded item to see its source.</p>
        )}
      </aside>
      <span className="sr-only" role="status">
        {evidence
          ? "Showing source evidence for " +
            recordLabel(evidence.label) +
            ", " +
            recordedDate(evidence)
          : ""}
      </span>
    </div>
  );
}
