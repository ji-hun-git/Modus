import { useId, useState } from "react";
import { ArrowUpRight, FileText } from "lucide-react";
import type { HistoryView } from "./historyTypes";
import { sourceDateRange, sourceTitle } from "./sourceDisplay";
import SourceCubeEvidence from "./SourceCubeEvidence";
import { Modal } from "./ui";

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
        <h3>Evidence</h3>
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
          <button
            key={source.id}
            type="button"
            className={`home-evidence-cell${source.id === selected?.id ? " is-selected" : ""}`}
            aria-pressed={source.id === selected?.id}
            aria-controls={selectionId}
            aria-label={`File ${index + 1}: ${source.title}, ${sourceDateRange(factsFor(source.id))}`}
            onClick={() => select(source.id)}
          >
            <svg viewBox="0 0 48 54" aria-hidden="true">
              <path d="M24 2 46 14.5V39.5L24 52 2 39.5V14.5Z" />
            </svg>
            <span aria-hidden="true">{index + 1}</span>
          </button>
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
            <FileText size={16} aria-hidden="true" />
            <span>
              File{" "}
              {sources.findIndex((source) => source.id === selected.id) + 1}
            </span>
            <span>
              {selectedFacts.length}{" "}
              {selectedFacts.length === 1 ? "item" : "items"}
            </span>
          </div>
          <h4>{sourceTitle(selectedFacts)}</h4>
          <p>{sourceDateRange(selectedFacts)}</p>
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
      {!!sources.length && (
        <details className="home-evidence-list">
          <summary>File list</summary>
          <ul>
            {sources.map((source, index) => (
              <li key={source.id}>
                <button
                  type="button"
                  onClick={() => select(source.id)}
                  aria-pressed={source.id === selected?.id}
                  aria-controls={selectionId}
                >
                  <span>{index + 1}</span>
                  <span>
                    <strong>{source.title}</strong>
                    <small>{sourceDateRange(factsFor(source.id))}</small>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </details>
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
