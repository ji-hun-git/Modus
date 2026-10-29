import { useId, useState } from "react";
import { ArrowUpRight, FileText } from "lucide-react";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { sourceDateRange, sourceExcerpt, sourceTitle } from "./sourceDisplay";
import SourceCubeEvidence from "./SourceCubeEvidence";
import { Modal } from "./ui";

function recordedYears(facts: HistoryFact[]): string {
  const yearFor = (fact: HistoryFact) => {
    if (fact.date) return fact.date.slice(0, 4);
    const recorded = fact.occurred_on || "";
    return /^(?!0000)\d{4}(?:-(?:0[1-9]|1[0-2]))?$/.test(recorded)
      ? recorded.slice(0, 4) : null;
  };
  const years = [...new Set(facts.flatMap((fact) => {
    const year = yearFor(fact);
    return year ? [year] : [];
  }))].sort();
  if (!years.length) return "Undated";
  const range = years.length === 1 ? years[0] : `${years[0]}–${years.at(-1)}`;
  const undated = facts.some((fact) => !yearFor(fact));
  return range + (undated ? " · undated" : "");
}

export default function HomeEvidenceStack({
  view,
  onBrowse,
}: {
  view: HistoryView;
  onBrowse: () => void;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const selectionId = useId();
  const allFacts = [...view.facts, ...view.undated_facts];
  const factsFor = (id: string) =>
    allFacts.filter((fact) => fact.source_id === id);
  const sources = [...view.sources].sort(
    (a, b) =>
      b.available_at.localeCompare(a.available_at) || a.id.localeCompare(b.id),
  );
  const selected =
    sources.find((source) => source.id === selectedId) || sources[0];
  const selectedFacts = selected ? factsFor(selected.id) : [];
  const firstFact = selectedFacts[0];
  const excerptVisible = firstFact && !firstFact.source_quote_withheld &&
    !firstFact.value_withheld && firstFact.within_date_scope !== false &&
    !!firstFact.source_quote;
  const excerpt = excerptVisible ? Array.from(sourceExcerpt(firstFact)) : [];
  const excerptPreview = excerpt.slice(0, 100).join("") + (excerpt.length > 100 ? "…" : "");
  const select = (id: string) => {
    setSelectedId(id);
    setEvidenceOpen(false);
  };
  return (
    <aside
      className="home-evidence-stack"
      aria-label="Source files in this view"
    >
      <header className="home-evidence-map-heading">
        <h3>Your files</h3>
        <span>
          {sources.length} {sources.length === 1 ? "file" : "files"}
        </span>
      </header>
      <div
        className="home-evidence-map"
        role="group"
        aria-label="Select a source file"
      >
        {sources.map((source, index) => (
          <div className="home-evidence-cell-item" key={source.id}>
            <button
              type="button"
              className={`home-evidence-cell${source.id === selected?.id ? " is-selected" : ""}`}
              aria-pressed={source.id === selected?.id}
              aria-controls={selectionId}
              aria-label={`File ${index + 1}: ${source.title}, ${sourceDateRange(factsFor(source.id))}`}
              onClick={() => select(source.id)}
            >
              <svg className="home-evidence-hex" viewBox="0 0 48 54" aria-hidden="true">
                <path d="M24 2 46 14.5V39.5L24 52 2 39.5V14.5Z" />
              </svg>
              <FileText className="home-evidence-file-icon" size={19} aria-hidden="true" />
            </button>
            <span className="home-evidence-cell-date" aria-hidden="true">
              {recordedYears(factsFor(source.id))}
            </span>
          </div>
        ))}
        {!sources.length && (
          <p className="home-evidence-empty">No files in this view.</p>
        )}
      </div>
      {selected && (
        <section
          className="home-evidence-selected"
          id={selectionId}
          aria-label="Selected source file"
        >
          <div className="home-evidence-selected-top">
            <span>Selected file</span>
            <span>
              {selectedFacts.length}{" "}
              {selectedFacts.length === 1 ? "item" : "items"}
            </span>
          </div>
          <h4 title={selected.title}>{sourceTitle(selectedFacts)}</h4>
          <p>{sourceDateRange(selectedFacts)}</p>
          {firstFact && (
            <div className="home-evidence-preview">
              {excerptVisible ? <>
                <span>Excerpt · first recorded item</span>
                <blockquote>{excerptPreview}</blockquote>
              </> : <p>Excerpt unavailable in this view.</p>}
            </div>
          )}
          <button
            type="button"
            className="secondary"
            onClick={() => setEvidenceOpen(true)}
            aria-haspopup="dialog"
          >
            Open evidence <ArrowUpRight size={15} />
          </button>
        </section>
      )}
      <footer>
        <button className="text-button" onClick={onBrowse}>
          View all files <ArrowUpRight size={15} />
        </button>
      </footer>
      <span className="sr-only" role="status">
        {selected
          ? `Selected ${selected.title}, ${sourceDateRange(selectedFacts)}, ${selectedFacts.length} recorded items.`
          : "No source files."}
      </span>
      {selected && evidenceOpen && (
        <Modal title={selected.title} onClose={() => setEvidenceOpen(false)}>
          <SourceCubeEvidence
            source={selected}
            facts={selectedFacts}
            view={view}
          />
        </Modal>
      )}
    </aside>
  );
}
