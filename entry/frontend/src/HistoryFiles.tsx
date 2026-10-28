import { useState, type ReactNode } from "react";
import { Download, FileText, Search } from "lucide-react";
import type { HistoryView } from "./historyTypes";
import TimelineFact from "./TimelineFact";
import { timeLabel } from "./ui";

export default function HistoryFiles({
  view,
  dateControl,
}: {
  view: HistoryView;
  dateControl: ReactNode;
}) {
  const [query, setQuery] = useState("");
  const facts = [...view.facts, ...view.undated_facts];
  const needle = query.trim().toLocaleLowerCase();
  const sources = view.sources.filter((source) =>
    [
      source.title,
      source.provider,
      source.date,
      ...facts
        .filter((fact) => fact.source_id === source.id)
        .flatMap((fact) => [fact.label, fact.value, fact.occurred_on]),
    ]
      .filter(Boolean)
      .join(" ")
      .toLocaleLowerCase()
      .includes(needle),
  );
  const conflictIds = new Set(
    view.conflicts.flatMap((conflict) => conflict.fact_ids),
  );
  function exportView() {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(view, null, 2)], { type: "application/json" }),
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `modus-history-${view.scope.as_of || "all-dates"}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }
  return (
    <section className="history-timeline" aria-label="All source files">
      <header className="timeline-heading">
        <div>
          <h2>Your files</h2>
          <p>
            {view.counts.sources} files · {facts.length} recorded fields in this
            view
          </p>
        </div>
        <button className="text-button" onClick={exportView}>
          <Download size={15} /> Export view
        </button>
      </header>
      {dateControl}
      <label className="search-box history-file-search">
        <Search size={17} />
        <input
          aria-label="Search all records"
          value={query}
          placeholder="Find a file, name or recorded value"
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      {!sources.length && (
        <div className="workspace-empty">
          <FileText size={28} />
          <h3>No files match this view</h3>
          <p>Try another search or change the date filter.</p>
        </div>
      )}
      <div className="history-files-list">
        {sources.map((source) => {
          const fields = facts.filter((fact) => fact.source_id === source.id);
          return (
            <details className="history-file" key={source.id}>
              <summary>
                <FileText size={19} />
                <span>
                  <strong>{source.title}</strong>
                  <small>
                    {source.provider || "Facility not recorded"} ·{" "}
                    {fields.length} fields
                  </small>
                </span>
              </summary>
              <div className="timeline-facts">
                {fields.map((fact) => (
                  <TimelineFact
                    key={fact.id}
                    fact={fact}
                    view={view}
                    conflict={conflictIds.has(fact.id)}
                    conflictReason={
                      view.conflicts.find((item) =>
                        item.fact_ids.includes(fact.id),
                      )?.reason
                    }
                  />
                ))}
              </div>
            </details>
          );
        })}
      </div>
      <p className="timeline-scope">
        {view.scope.as_of
          ? `Recorded through ${view.scope.as_of}`
          : "All recorded dates"}{" "}
        · Files available through {timeLabel(view.scope.known_at)}
      </p>
    </section>
  );
}
