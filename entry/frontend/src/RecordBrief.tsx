import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Check,
  Download,
  FileText,
  LoaderCircle,
  Search,
} from "lucide-react";
import { api } from "./api";
import type { Scope } from "./types";
import { recordLabel } from "./types";
import type { FactKind, HistoryFact, HistoryView } from "./historyTypes";
import { factKindLabels } from "./historyTypes";
import type { BriefRequest, RecordBriefData } from "./briefTypes";
import { Modal, dateLabel, timeLabel } from "./ui";
import { recordedDate, sourceDateRange, sourceTitle } from "./sourceDisplay";
import { unitLabel } from "./recordPresentation.mjs";
import useHistoryView from "./useHistoryView";
import SourceCubeEvidence from "./SourceCubeEvidence";
import {
  MAX_BRIEF_SELECTION,
  briefMatchesRequest,
  briefRequest,
  briefRequestKey,
  eligibleBriefFacts,
  reviewedBriefExport,
} from "./briefSelection.mjs";
import "./record-brief.css";

function BriefScope({ scope }: { scope: HistoryView["scope"] }) {
  return (
    <span>
      {scope.as_of
        ? `Records through ${dateLabel(scope.as_of)}`
        : "All recorded dates"}
      {" · "}Files available through {timeLabel(scope.known_at)}
    </span>
  );
}

function FactValue({ fact }: { fact: HistoryFact }) {
  return (
    <span className="brief-fact-value">
      {fact.value ?? "Value unavailable"}
      {fact.unit ? (
        <span className="brief-unit"> {unitLabel(fact.unit)}</span>
      ) : null}
    </span>
  );
}

export default function RecordBrief({
  scope,
  historical,
  onImport,
}: {
  scope: Scope;
  historical: boolean;
  onImport: () => void;
}) {
  const { view, error, refresh } = useHistoryView(scope, !historical);
  if (error)
    return (
      <section className="panel empty" role="alert">
        <AlertCircle size={24} />
        <h2>Your records could not be loaded</h2>
        <p>{error}</p>
        <button className="secondary" onClick={refresh}>
          Try again
        </button>
      </section>
    );
  if (!view)
    return (
      <section className="panel loading" role="status">
        <LoaderCircle className="spin" size={24} /> Loading records for your
        brief…
      </section>
    );
  // A new captured view starts a new selection and cancels the old draft.
  return (
    <BriefBuilder key={view.scope.scope_id} view={view} onImport={onImport} />
  );
}

function BriefBuilder({
  view,
  onImport,
}: {
  view: HistoryView;
  onImport: () => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<FactKind | "all">("all");
  const [title, setTitle] = useState("Record brief");
  const [ownerNote, setOwnerNote] = useState("");
  const [prepared, setPrepared] = useState<{
    key: string;
    request: BriefRequest;
    brief: RecordBriefData;
  } | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [busy, setBusy] = useState<"preview" | "html" | "json" | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [inspected, setInspected] = useState<{
    fact: HistoryFact;
    view: HistoryView;
  } | null>(null);
  const sequence = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const reviewHeading = useRef<HTMLHeadingElement>(null);
  const selectionHeading = useRef<HTMLHeadingElement>(null);
  const selectedSet = new Set(selected);
  const eligible = eligibleBriefFacts(view);
  const unavailable =
    view.facts.length + view.undated_facts.length - eligible.length;
  const request = briefRequest(view, selected, title, ownerNote);
  const key = briefRequestKey(view, selected, title, ownerNote);
  const latestKey = useRef(key);
  latestKey.current = key;
  const preview = prepared?.key === key ? prepared : null;
  const filter = query.trim().toLocaleLowerCase();
  const groups = view.sources
    .map((source) => ({
      source,
      facts: eligible.filter(
        (fact) =>
          fact.source_id === source.id &&
          (kind === "all" || fact.kind === kind) &&
          (!filter ||
            [
              fact.label,
              fact.value,
              fact.unit,
              fact.occurred_on,
              fact.facility,
              source.title,
            ]
              .filter(Boolean)
              .join(" ")
              .toLocaleLowerCase()
              .includes(filter)),
      ),
    }))
    .filter((group) => group.facts.length);
  const shown = groups.reduce((sum, group) => sum + group.facts.length, 0);

  useEffect(
    () => () => {
      sequence.current++;
      controller.current?.abort();
    },
    [],
  );
  useEffect(() => {
    setReviewed(false);
    setNotice("");
    setError("");
    setInspected(null);
    sequence.current++;
    controller.current?.abort();
    setBusy(null);
  }, [key]);
  useEffect(() => {
    if (preview) reviewHeading.current?.focus();
  }, [preview]);

  function select(ids: string[], keep: boolean) {
    const next = new Set(selected);
    for (const id of ids) keep ? next.add(id) : next.delete(id);
    if (next.size > MAX_BRIEF_SELECTION) {
      setError(
        `Choose up to ${MAX_BRIEF_SELECTION} records for one brief. Your existing selection is unchanged.`,
      );
      return;
    }
    setSelected([...next]);
    setPrepared(null);
    setReviewed(false);
  }

  function editSelection() {
    setPrepared(null);
    setReviewed(false);
    setNotice("");
    setInspected(null);
    requestAnimationFrame(() => selectionHeading.current?.focus());
  }

  async function prepare() {
    if (!request || busy) return;
    const active = new AbortController();
    const attempt = ++sequence.current;
    const requestKey = key;
    controller.current?.abort();
    controller.current = active;
    setBusy("preview");
    setError("");
    setNotice("");
    setReviewed(false);
    try {
      const result = await api<RecordBriefData>("/briefs/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
        signal: active.signal,
      });
      if (
        active.signal.aborted ||
        attempt !== sequence.current ||
        requestKey !== latestKey.current
      )
        return;
      if (!briefMatchesRequest(result, request))
        throw new Error(
          "The brief did not match your selected records and dates. Please prepare it again.",
        );
      setPrepared({ key: requestKey, request, brief: result });
    } catch (cause) {
      if (
        !active.signal.aborted &&
        attempt === sequence.current &&
        requestKey === latestKey.current
      )
        setError(
          (cause as Error).message || "Your brief could not be prepared.",
        );
    } finally {
      if (attempt === sequence.current && requestKey === latestKey.current)
        setBusy(null);
    }
  }

  async function download(format: "html" | "json") {
    if (!preview || busy) return;
    const payload = reviewedBriefExport(
      preview.brief,
      preview.request,
      reviewed,
      format,
    );
    if (!payload) return;
    const active = new AbortController();
    const attempt = ++sequence.current;
    const requestKey = key;
    controller.current?.abort();
    controller.current = active;
    setBusy(format);
    setError("");
    setNotice("");
    try {
      const response = await fetch("/api/briefs/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: active.signal,
      });
      if (!response.ok) {
        let message =
          "The brief could not be downloaded. Please prepare and review it again.";
        try {
          const value = await response.json();
          if (typeof value.detail === "string") message = value.detail;
        } catch {
          /* retain safe error */
        }
        if (
          response.status === 409 &&
          !active.signal.aborted &&
          attempt === sequence.current &&
          requestKey === latestKey.current
        ) {
          // The server invalidated this preview; keep the owner's draft inputs
          // while requiring a new preview and explicit review before export.
          editSelection();
        }
        throw new Error(message);
      }
      const blob = await response.blob();
      if (
        active.signal.aborted ||
        attempt !== sequence.current ||
        requestKey !== latestKey.current
      )
        return;
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `modus-record-brief.${format}`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setNotice(
        format === "html"
          ? "Brief download started. Open the file in your browser to read or print it."
          : "Record data download started.",
      );
    } catch (cause) {
      if (
        !active.signal.aborted &&
        attempt === sequence.current &&
        requestKey === latestKey.current
      )
        setError(
          (cause as Error).message || "Your brief could not be downloaded.",
        );
    } finally {
      if (attempt === sequence.current && requestKey === latestKey.current)
        setBusy(null);
    }
  }

  const evidenceSource = inspected?.view.sources.find(
    (source) => source.id === inspected.fact.source_id,
  );
  const evidenceFacts = inspected
    ? [...inspected.view.facts, ...inspected.view.undated_facts].filter(
        (fact) => fact.source_id === inspected.fact.source_id,
      )
    : [];
  const brief = preview?.brief;
  const sections = brief
    ? [
        {
          key: "dated",
          title: "Dated records",
          entries: brief.entries.filter(
            (entry) => entry.date && entry.kind !== "prescription",
          ),
        },
        {
          key: "prescriptions",
          title: "Historical prescriptions",
          entries: brief.entries.filter(
            (entry) => entry.kind === "prescription",
          ),
        },
        {
          key: "undated",
          title: "Partial or unknown dates",
          entries: brief.entries.filter(
            (entry) => !entry.date && entry.kind !== "prescription",
          ),
        },
      ].filter((section) => section.entries.length)
    : [];

  return (
    <div className="record-brief-workspace">
      <ol className="brief-progress" aria-label="Brief preparation steps">
        <li
          className={!preview ? "is-current" : "is-complete"}
          aria-current={!preview ? "step" : undefined}
        >
          <span>{preview ? <Check size={15} /> : "1"}</span> Choose records
        </li>
        <li
          className={preview ? "is-current" : ""}
          aria-current={preview ? "step" : undefined}
        >
          <span>2</span> Review brief
        </li>
        <li>
          <span>3</span> Download
        </li>
      </ol>
      {error && (
        <p className="error-banner" role="alert">
          <AlertCircle size={18} /> {error}
        </p>
      )}
      {notice && (
        <p className="brief-notice" role="status">
          <Check size={18} /> {notice}
        </p>
      )}
      {!preview ? (
        <>
          <div className="brief-introduction">
            <h2 ref={selectionHeading} tabIndex={-1}>
              Choose what to take with you
            </h2>
            <p>
              Select the records for your brief. Their dates, original wording
              and sources stay attached.
            </p>
            <p className="brief-scope">
              <BriefScope scope={view.scope} />
            </p>
          </div>
          <div className="brief-compose-layout">
            <section
              className="brief-record-picker"
              aria-label="Choose records for your brief"
            >
              <div className="brief-filter-row">
                <label className="brief-search">
                  <Search size={18} />
                  <span className="sr-only">Find records for your brief</span>
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Find a record or document"
                  />
                </label>
                <label className="field">
                  <span className="sr-only">Record type for brief</span>
                  <select
                    aria-label="Record type for brief"
                    value={kind}
                    onChange={(event) =>
                      setKind(event.target.value as FactKind | "all")
                    }
                  >
                    <option value="all">All record types</option>
                    {Object.entries(factKindLabels).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="brief-selection-count">
                <span>
                  {selected.length} selected · {shown} shown
                </span>
                {selected.length > 0 && (
                  <button
                    className="text-button"
                    onClick={() => {
                      setSelected([]);
                      setPrepared(null);
                    }}
                  >
                    Clear selection
                  </button>
                )}
              </div>
              {unavailable > 0 && (
                <p className="brief-filter-note">
                  {unavailable}{" "}
                  {unavailable === 1 ? "record is" : "records are"} hidden by
                  this view’s date limits and cannot be included.
                </p>
              )}
              {!eligible.length ? (
                <div className="brief-empty">
                  <FileText size={28} />
                  <h3>No records to include in this view</h3>
                  <p>
                    Add a document or choose different dates to prepare a brief.
                  </p>
                  <button className="secondary" onClick={onImport}>
                    Add records
                  </button>
                </div>
              ) : !groups.length ? (
                <div className="brief-empty">
                  <Search size={24} />
                  <h3>No records match this search</h3>
                  <p>Your existing selection is still kept.</p>
                  <button
                    className="text-button"
                    onClick={() => {
                      setQuery("");
                      setKind("all");
                    }}
                  >
                    Clear filters
                  </button>
                </div>
              ) : (
                groups.map(({ source, facts }) => (
                  <article
                    key={source.id}
                    className="brief-source-group"
                    aria-label={`Records from ${source.title}`}
                  >
                    <header>
                      <div className="brief-source-heading">
                        <span className="brief-source-cube" aria-hidden="true">
                          <FileText size={20} />
                        </span>
                        <div>
                          <h3>{sourceTitle(facts)}</h3>
                          <p>{sourceDateRange(facts)}</p>
                          <small>{source.title}</small>
                        </div>
                      </div>
                      <label className="brief-group-select">
                        <input
                          type="checkbox"
                          checked={facts.every((fact) =>
                            selectedSet.has(fact.id),
                          )}
                          onChange={(event) =>
                            select(
                              facts.map((fact) => fact.id),
                              event.target.checked,
                            )
                          }
                          aria-label={`Select all shown records from ${source.title}`}
                        />
                        Select shown
                      </label>
                    </header>
                    <div>
                      {facts.map((fact) => (
                        <div
                          key={fact.id}
                          className={`brief-picker-row ${selectedSet.has(fact.id) ? "is-selected" : ""}`}
                        >
                          <label>
                            <input
                              type="checkbox"
                              checked={selectedSet.has(fact.id)}
                              onChange={(event) =>
                                select([fact.id], event.target.checked)
                              }
                              aria-label={`Include ${fact.label}, ${recordedDate(fact)}, from ${source.title}`}
                            />
                            <span>
                              <strong>{recordLabel(fact.label)}</strong>
                              <span className="brief-record-meta">
                                {recordedDate(fact)} ·{" "}
                                {factKindLabels[fact.kind]}
                              </span>
                              <FactValue fact={fact} />
                            </span>
                          </label>
                          <button
                            className="text-button"
                            aria-label={`View source for ${fact.label}, ${recordedDate(fact)}, from ${source.title}`}
                            onClick={() => setInspected({ fact, view })}
                          >
                            <FileText size={16} />
                            <span>Source</span>
                          </button>
                        </div>
                      ))}
                    </div>
                  </article>
                ))
              )}
            </section>
            <aside className="brief-setup" aria-label="Brief details">
              <span className="brief-sheet-icon" aria-hidden="true">
                <FileText size={25} />
              </span>
              <h2>Your record brief</h2>
              <p>
                A dated collection you can review, download and take to an
                appointment.
              </p>
              <label className="field">
                Brief title
                <input
                  value={title}
                  maxLength={100}
                  onChange={(event) => {
                    setTitle(event.target.value);
                    setPrepared(null);
                  }}
                />
              </label>
              <label className="field">
                Your note <span className="brief-optional">Optional</span>
                <textarea
                  rows={4}
                  maxLength={1200}
                  value={ownerNote}
                  onChange={(event) => {
                    setOwnerNote(event.target.value);
                    setPrepared(null);
                  }}
                  placeholder="What would you like to discuss?"
                />
              </label>
              <p className="brief-note-help">
                Your note stays separate from the recorded facts.
              </p>
              <div className="brief-setup-total">
                <strong>{selected.length}</strong>
                <span>
                  {selected.length === 1
                    ? "record selected"
                    : "records selected"}
                </span>
              </div>
              <p className="brief-note-help">
                If a selected measurement has conflicting records, both sides
                will appear for your review.
              </p>
              <button
                className="primary brief-prepare-button"
                disabled={!request || !!busy}
                onClick={() => void prepare()}
              >
                {busy === "preview" ? (
                  <LoaderCircle size={18} className="spin" />
                ) : (
                  <ArrowRight size={18} />
                )}{" "}
                {busy === "preview" ? "Preparing brief…" : "Review brief"}
              </button>
              <small>
                Choose up to {MAX_BRIEF_SELECTION} records. No records are
                changed.
              </small>
            </aside>
          </div>
        </>
      ) : (
        brief && (
          <div className="brief-review-layout">
            <div className="brief-review-toolbar">
              <button
                className="text-button"
                onClick={editSelection}
                disabled={!!busy}
              >
                <ArrowLeft size={17} /> Edit selection and note
              </button>
              <span>
                {brief.counts.total} records · {brief.counts.sources} documents
              </span>
            </div>
            {brief.counts.conflict_companions > 0 && (
              <div className="brief-companion-notice" role="status">
                <AlertCircle size={20} />
                <div>
                  <strong>
                    {brief.counts.conflict_companions} related{" "}
                    {brief.counts.conflict_companions === 1
                      ? "record added"
                      : "records added"}{" "}
                    to preserve a disagreement
                  </strong>
                  <p>
                    These are marked below with their sources. To leave out a
                    disagreement, return to your selection and remove all
                    records in that group.
                  </p>
                  <ul>
                    {brief.entries
                      .filter((entry) => entry.added_for_conflict)
                      .map((entry) => (
                        <li key={entry.id}>
                          {recordLabel(entry.label)} · {recordedDate(entry)} ·{" "}
                          {brief.sources.find(
                            (source) => source.id === entry.source_id,
                          )?.title || entry.source_citation}
                        </li>
                      ))}
                  </ul>
                </div>
              </div>
            )}
            <article
              className="brief-document"
              aria-label="Record brief preview"
            >
              <header className="brief-document-header">
                <span className="brief-document-kicker">
                  Selected record history
                </span>
                <h2 ref={reviewHeading} tabIndex={-1}>
                  {brief.title}
                </h2>
                <p>
                  <BriefScope scope={brief.scope} />
                </p>
              </header>
              {brief.owner_note && (
                <section className="brief-owner-note">
                  <h3>Your note</h3>
                  <p>{brief.owner_note}</p>
                </section>
              )}
              {brief.warnings.length > 0 && (
                <section className="brief-document-warnings">
                  <h3>Keep in mind</h3>
                  <ul>
                    {brief.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                </section>
              )}
              {brief.conflicts.length > 0 && (
                <section className="brief-unresolved">
                  <h3>Unresolved differences</h3>
                  <p>
                    {brief.conflicts.length}{" "}
                    {brief.conflicts.length === 1
                      ? "group contains"
                      : "groups contain"}{" "}
                    different recorded values or units. Every included value
                    remains separate; no source is selected as correct.
                  </p>
                </section>
              )}
              {sections.map((section) => (
                <section key={section.key} className="brief-record-section">
                  <h3>{section.title}</h3>
                  {section.key === "prescriptions" && (
                    <p className="brief-section-note">
                      These are prescription records. They do not establish what
                      you currently take.
                    </p>
                  )}
                  {section.entries.map((entry) => (
                    <article className="brief-preview-entry" key={entry.id}>
                      <div className="brief-entry-date">
                        {recordedDate(entry)}
                        <span>{entry.citation}</span>
                      </div>
                      <div className="brief-entry-content">
                        <div className="brief-entry-title">
                          <h4>{recordLabel(entry.label)}</h4>
                          <span>{factKindLabels[entry.kind]}</span>
                        </div>
                        <FactValue fact={entry} />
                        {entry.added_for_conflict && (
                          <p className="brief-added-label">
                            Included to show the other recorded value
                          </p>
                        )}
                        <button
                          className="text-button"
                          onClick={() =>
                            setInspected({
                              fact: entry,
                              view: brief.history_evidence,
                            })
                          }
                        >
                          <FileText size={15} />
                          {entry.source_citation} · View source
                        </button>
                      </div>
                    </article>
                  ))}
                </section>
              ))}
              <section className="brief-source-index">
                <h3>Sources included</h3>
                <ol>
                  {brief.sources.map((source) => (
                    <li key={source.id}>
                      <span>{source.citation}</span>
                      <div>
                        <strong>{source.title}</strong>
                        <small>
                          {source.provider || "Source provider not recorded"}
                        </small>
                      </div>
                    </li>
                  ))}
                </ol>
              </section>
              <footer>
                This brief collects the selected records and your note. It does
                not assess health or recommend care.
              </footer>
            </article>
            <section
              className="brief-download"
              aria-label="Review and download your brief"
            >
              <div>
                <h2>Ready to take with you</h2>
                <p>
                  Check the entries, dates and any added conflicting records
                  before downloading.
                </p>
                <label className="brief-review-confirm">
                  <input
                    type="checkbox"
                    checked={reviewed}
                    disabled={!!busy}
                    onChange={(event) => setReviewed(event.target.checked)}
                  />
                  I have reviewed this brief and the records included.
                </label>
              </div>
              <div className="brief-download-actions">
                <button
                  className="primary"
                  disabled={!reviewed || !!busy}
                  onClick={() => void download("html")}
                >
                  {busy === "html" ? (
                    <LoaderCircle className="spin" size={18} />
                  ) : (
                    <Download size={18} />
                  )}
                  Download brief
                </button>
                <p>
                  HTML file. Open it in your browser; use Print to save as PDF.
                </p>
                <button
                  className="text-button"
                  disabled={!reviewed || !!busy}
                  onClick={() => void download("json")}
                >
                  {busy === "json"
                    ? "Downloading…"
                    : "Download record data (JSON)"}
                </button>
              </div>
            </section>
          </div>
        )
      )}
      <div className="sr-only" role="status">
        {busy === "preview"
          ? "Preparing your selected records."
          : busy
            ? "Preparing download."
            : ""}
      </div>
      {inspected && evidenceSource && (
        <Modal title="Record source" onClose={() => setInspected(null)} wide>
          <p className="brief-scope">
            <BriefScope scope={inspected.view.scope} />
          </p>
          <SourceCubeEvidence
            source={evidenceSource}
            facts={evidenceFacts}
            view={inspected.view}
            initialFactId={inspected.fact.id}
          />
        </Modal>
      )}
    </div>
  );
}
