import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowUpRight,
  FileText,
  LoaderCircle,
  RotateCcw,
  Upload,
} from "lucide-react";
import { api, ApiError, post } from "./api";
import { Modal, dateLabel, timeLabel } from "./ui";
import {
  metricLabel,
  type Commit,
  type Draft,
  type Health,
  type ReviewRow,
} from "./types";
import {
  appendFiles,
  acceptDraft,
  beginCommit,
  beginFactCommit,
  failCommit,
  finishCommit,
  navigationLocked,
  summary,
  statusLabel,
  fileError,
  extension,
  MAX_FILES,
  type QueueItem,
  type Extraction,
} from "./importQueue";
import "./import-queue.css";
import ExtractionReviewSummary from "./ExtractionReviewSummary";
import GenericFactReview from "./GenericFactReview";
import type { FactReviewRow } from "./historyTypes";

export default function ImportWorkflow({
  open,
  onClose,
  health,
  onDraftChange,
  onCommitted,
}: {
  open: boolean;
  onClose: () => void;
  health: Health | null;
  onDraftChange: (hasDraft: boolean) => void;
  onCommitted: (result: Commit) => void;
}) {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [queueNotice, setQueueNotice] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const sourcePanel = useRef<HTMLElement>(null);
  const inFlight = useRef(false);
  const current = queue.find((item) => item.id === activeId) || queue[0];
  const draft = current?.draft || null;
  const rows = current?.rows || [];
  const selected = current?.selected || 0;
  const extraction = current?.extraction || "local";
  const attempt = current?.factAttempt || current?.attempt || null;
  const factRows = current?.factRows || [];
  const generic = !!draft?.facts;
  const error = current?.error || "";
  const busy = current?.status === "reading" || current?.status === "saving";
  const phase =
    current?.status === "reading"
      ? "reading"
      : current?.status === "saving"
        ? "adding"
        : "idle";
  const keep = rows.filter((row) => row.keep);
  const includedCount = generic
    ? factRows.filter((row) => row.keep).length
    : keep.length;
  const referenceOnly =
    draft?.extraction_review?.facts.filter((fact) => !fact.commit_supported)
      .length || 0;
  const locked = busy || !!attempt || !!draft?.already_committed;
  const queueLocked = navigationLocked(queue);
  const totals = summary(queue);
  const unconfirmedSaves = queue.filter(
    (item) => !!item.attempt || !!item.factAttempt,
  ).length;
  const finished =
    !!current && ["saved", "duplicate", "skipped"].includes(current.status);
  const localOcrAvailable = health?.local_ocr?.available === true;
  const metaAvailable = health?.provider.mode === "meta";
  const textOnly =
    !!current && ["csv", "txt"].includes(extension(current.file));
  const imageFile =
    !!current && ["png", "jpg", "jpeg"].includes(extension(current.file));
  const extractionAvailable =
    extraction === "local"
      ? !imageFile
      : extraction === "local-teleocr"
        ? localOcrAvailable
        : metaAvailable;
  const patch = (id: string, value: Partial<QueueItem>) =>
    setQueue((items) =>
      items.map((item) => (item.id === id ? { ...item, ...value } : item)),
    );
  const setSelected = (value: number) => {
    if (current) patch(current.id, { selected: value });
  };
  useEffect(() => {
    onDraftChange(totals.pending > 0);
  }, [totals.pending, onDraftChange]);
  useEffect(() => {
    if (!totals.pending && !busy) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [totals.pending, busy]);
  const close = () => {
    if (!inFlight.current) onClose();
  };
  const selectFiles = (files: File[]) => {
    if (inFlight.current || queueLocked) return;
    const appended = appendFiles(queue, files);
    setQueue(appended.items);
    if (!current) setActiveId(appended.items[0]?.id || null);
    setConfirmed(false);
    setQueueNotice(
      appended.omitted
        ? `Up to ${MAX_FILES} files fit in one queue. ${appended.omitted} additional file${appended.omitted === 1 ? " was" : "s were"} not selected.`
        : "",
    );
  };
  const discard = () => {
    if (!current || busy || attempt) return;
    patch(current.id, { status: "skipped", error: "" });
  };
  async function upload() {
    if (!current || inFlight.current || queueLocked) return;
    const invalid = fileError(current.file);
    if (invalid || !confirmed || !extractionAvailable) {
      patch(current.id, {
        status: "error",
        error:
          invalid ||
          "Confirm synthetic data and choose an available reading method.",
      });
      return;
    }
    const item = current;
    inFlight.current = true;
    patch(item.id, { status: "reading", error: "" });
    try {
      const body = new FormData();
      body.append("file", item.file);
      body.append("synthetic_confirmed", "true");
      body.append("use_meta", String(item.extraction === "meta"));
      body.append("use_local_ocr", String(item.extraction === "local-teleocr"));
      const result = await api<Draft>("/imports/preview", {
        method: "POST",
        body,
      });
      setQueue((items) =>
        items.map((entry) =>
          entry.id === item.id ? acceptDraft(entry, result) : entry,
        ),
      );
    } catch (failure) {
      patch(item.id, {
        status: "error",
        error: `This file could not be read. No records were saved. Retry this file or skip it to continue. ${(failure as Error).message}`,
      });
    } finally {
      inFlight.current = false;
    }
  }
  async function commit() {
    if (
      !current ||
      !draft ||
      inFlight.current ||
      !includedCount ||
      draft.already_committed
    )
      return;
    let submitting: QueueItem;
    try {
      submitting = generic ? beginFactCommit(current) : beginCommit(current);
    } catch (failure) {
      patch(current.id, { error: (failure as Error).message });
      return;
    }
    const wasUncertain = current.status === "uncertain";
    inFlight.current = true;
    patch(current.id, submitting);
    try {
      const result = await post<Commit>(
        generic ? "/history/commit" : "/imports/commit",
        {
          draft_id: draft.id,
          synthetic_confirmed: true,
          ...(generic
            ? { reviewed_facts: submitting.factAttempt }
            : { reviewed_observations: submitting.attempt }),
        },
      );
      setQueue((items) =>
        items.map((item) =>
          item.id === submitting.id ? finishCommit(item, result) : item,
        ),
      );
      onCommitted(result);
    } catch (failure) {
      const definitive =
        failure instanceof ApiError && [400, 404, 422].includes(failure.status);
      const message =
        definitive && !wasUncertain
          ? `The review was not accepted. No records were saved by this request. Correct the fields or skip this file. ${(failure as Error).message}`
          : "The save result is unconfirmed. These fields may already be saved. Your submitted review is locked. Retry the same fields before moving to another file.";
      setQueue((items) =>
        items.map((item) =>
          item.id === submitting.id
            ? failCommit(item, definitive, wasUncertain, message)
            : item,
        ),
      );
    } finally {
      inFlight.current = false;
    }
  }
  const update = (id: string, value: Partial<ReviewRow>) => {
    if (!current || locked) return;
    patch(current.id, {
      rows: rows.map((row) => (row.id === id ? { ...row, ...value } : row)),
    });
  };
  const updateFact = (id: string, value: Partial<FactReviewRow>) => {
    if (!current || locked) return;
    patch(current.id, {
      factRows: factRows.map((row) =>
        row.id === id ? { ...row, ...value } : row,
      ),
    });
  };
  const reviewing = !!draft && !finished;
  const inspectSource = (index: number) => {
    setSelected(index);
    requestAnimationFrame(() => {
      sourcePanel.current?.scrollIntoView({ block: "start" });
      sourcePanel.current?.focus({ preventScroll: true });
    });
  };
  const returnToMeasurement = () => {
    const row = document.getElementById(`import-measurement-${selected}`);
    row?.scrollIntoView({ block: "center" });
    row?.focus({ preventScroll: true });
  };
  if (!open) return null;
  const active = draft?.observations[selected];
  return (
    <Modal title="Add records" onClose={close} busy={busy} wide={!!draft}>
      {reviewing && (
        <div className="import-review-heading">
          <span>
            File {queue.findIndex((item) => item.id === current.id) + 1} of{" "}
            {queue.length}
          </span>
          <h3>{current.file.name}</h3>
        </div>
      )}
      <details
        className={
          "import-files-disclosure " + (reviewing ? "compact" : "expanded")
        }
        key={reviewing ? current.id : "selection"}
        open={!reviewing}
      >
        <summary>Show files</summary>
        <div className="import-queue-heading">
          <p>Choose your files, then review and save one at a time.</p>
          <button
            type="button"
            className="secondary"
            disabled={queueLocked || queue.length >= MAX_FILES}
            onClick={() => input.current?.click()}
          >
            <Upload size={16} /> {queue.length ? "Add files" : "Choose files"}
          </button>
          <input
            ref={input}
            className="sr-only"
            type="file"
            multiple
            accept=".csv,.txt,.pdf,.png,.jpg,.jpeg"
            disabled={queueLocked || queue.length >= MAX_FILES}
            onChange={(event) => {
              selectFiles(Array.from(event.target.files || []));
              event.target.value = "";
            }}
          />
        </div>
        <p className="import-queue-limits">
          Up to 10 files · 8 MB each · CSV, text, PDF, PNG or JPEG. This version
          reads recorded measurements, visits, prescriptions, vaccinations and
          other report text. Every file is reviewed before saving.
        </p>
        {queueNotice && (
          <p role="status" className="safe-note">
            {queueNotice}
          </p>
        )}
        {!!queue.length && (
          <>
            <ol className="import-queue" aria-label="Selected files">
              {queue.map((item, index) => (
                <li key={item.id}>
                  <button
                    type="button"
                    aria-current={item.id === current?.id ? "step" : undefined}
                    disabled={queueLocked && item.id !== current?.id}
                    onClick={() => {
                      if (!inFlight.current && !queueLocked)
                        setActiveId(item.id);
                    }}
                  >
                    <span className="import-queue-number">{index + 1}</span>
                    <span className="import-queue-name">
                      {item.file.name}
                      <small>{statusLabel[item.status]}</small>
                    </span>
                  </button>
                </li>
              ))}
            </ol>
            <div className="import-queue-total" role="status">
              <strong>
                {unconfirmedSaves > 0 ? "Confirmed: " : ""}
                {totals.confirmed} file{totals.confirmed === 1 ? "" : "s"} in
                your history
              </strong>
              <span>
                {[
                  totals.measurements > 0
                    ? `${totals.measurements} new field${totals.measurements === 1 ? "" : "s"} confirmed`
                    : "",
                  totals.duplicates ? `${totals.duplicates} already saved` : "",
                  totals.skipped ? `${totals.skipped} skipped` : "",
                  totals.errors ? `${totals.errors} need attention` : "",
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
              {unconfirmedSaves > 0 && (
                <span>
                  {unconfirmedSaves} save{unconfirmedSaves === 1 ? "" : "s"}{" "}
                  awaiting confirmation; fields may already be saved.
                </span>
              )}
            </div>
          </>
        )}
      </details>
      {!current ? (
        <div className="import-queue-empty">
          <FileText size={28} />
          <h3>Bring your records together</h3>
          <p>
            Select several reports from different dates. Selecting files sends
            nothing. This demo accepts synthetic examples only.
          </p>
          <div className="table-footer">
            <span>Try an authored example</span>
            <a href="/examples/delayed-history.csv" download>
              Earlier record <ArrowUpRight size={13} />
            </a>
            <a href="/examples/update.csv" download>
              New record <ArrowUpRight size={13} />
            </a>
          </div>
        </div>
      ) : finished ? (
        <section className="import-queue-result" aria-live="polite">
          <h3>
            {current.status === "skipped"
              ? "File skipped"
              : current.status === "duplicate" || current.receipt?.duplicate
                ? "Already in your history"
                : "Record saved"}
          </h3>
          <p>{current.file.name}</p>
          <p>
            {current.status === "skipped"
              ? "Nothing from this file was added. Its review stays here if you return to it."
              : current.status === "duplicate" || current.receipt?.duplicate
                ? "No records were added again. Your existing review is unchanged."
                : `${current.receipt?.inserted || 0} reviewed ${current.receipt?.fact_ids ? "fields" : "measurements"} added. Your selected history view is unchanged.`}
          </p>
          {referenceOnly > 0 && current.status !== "skipped" && (
            <p className="safe-note">
              {referenceOnly} other field
              {referenceOnly === 1 ? " was" : "s were"} not added to your
              history. Their source excerpts remain in this draft below.
            </p>
          )}
          {draft?.extraction_review && referenceOnly > 0 && (
            <ExtractionReviewSummary review={draft.extraction_review} />
          )}
          <div className="import-queue-actions">
            {current.status === "skipped" && (
              <button
                type="button"
                className="secondary"
                onClick={() =>
                  patch(current.id, {
                    status: draft
                      ? "review"
                      : fileError(current.file)
                        ? "error"
                        : "selected",
                    error: fileError(current.file),
                  })
                }
              >
                Return to this file
              </button>
            )}
            {totals.pending > 0 && (
              <button
                type="button"
                className="primary"
                onClick={() => {
                  const next = queue.find(
                    (item) =>
                      !["saved", "skipped", "duplicate"].includes(item.status),
                  );
                  if (next) setActiveId(next.id);
                }}
              >
                Next file
              </button>
            )}
            <button
              type="button"
              className={totals.pending ? "secondary" : "primary"}
              onClick={close}
            >
              {totals.pending ? "Continue later" : "Done"}
            </button>
            {totals.pending === 0 && (
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setQueue([]);
                  setActiveId(null);
                  setConfirmed(false);
                  setQueueNotice("");
                }}
              >
                Start another upload
              </button>
            )}
          </div>
        </section>
      ) : !draft ? (
        <section className="import-queue-read">
          <h3>{current.file.name}</h3>
          <label className="check-row">
            <input
              type="checkbox"
              checked={confirmed}
              disabled={busy}
              onChange={(event) => setConfirmed(event.target.checked)}
            />
            These files contain synthetic example data only.
          </label>
          {textOnly ? (
            <p className="safe-note">
              CSV and text are read on this computer. No model is called.
            </p>
          ) : (
            <details open={imageFile || extraction !== "local"}>
              <summary>
                {imageFile
                  ? "Choose how to read this image"
                  : "Reading method · local text by default"}
              </summary>
              <label className="field">
                Read this file with
                <select
                  value={extraction}
                  disabled={busy}
                  onChange={(event) =>
                    patch(current.id, {
                      extraction: event.target.value as Extraction,
                      error: "",
                    })
                  }
                >
                  <option value="local" disabled={imageFile}>
                    Local text · no model
                  </option>
                  <option value="local-teleocr" disabled={!localOcrAvailable}>
                    Local OCR{localOcrAvailable ? "" : " · unavailable"}
                  </option>
                  <option value="meta" disabled={!metaAvailable}>
                    Meta{metaAvailable ? "" : " · not configured"}
                  </option>
                </select>
              </label>
              <p className="safe-note">
                {extraction === "meta"
                  ? "Meta reads this synthetic file, then checks the proposed fields against the source. You review everything before saving."
                  : extraction === "local-teleocr"
                    ? "Reads this file on this computer with the TeleOCR model. Up to 12 pages; every field still needs review."
                    : "Reads explicit text rows locally. Up to 30 PDF pages. Scans may need an available OCR method."}
              </p>
            </details>
          )}
          {imageFile && !extractionAvailable && (
            <p className="safe-note">
              Choose an available OCR or Meta method to read this image, or skip
              it and continue.
            </p>
          )}
          <p className="progress-note" role="status">
            {phase === "reading"
              ? "Reading this file… No measurements have been saved."
              : "Reading creates a draft. You decide what to save."}
          </p>
          <div className="import-queue-actions">
            <button
              type="button"
              className="secondary"
              disabled={busy}
              onClick={discard}
            >
              Skip file
            </button>
            <button
              type="button"
              className="primary"
              disabled={
                !confirmed ||
                busy ||
                !extractionAvailable ||
                !!fileError(current.file)
              }
              onClick={() => void upload()}
            >
              {busy ? (
                <>
                  <LoaderCircle className="spin" size={16} /> Reading…
                </>
              ) : current.status === "error" ? (
                "Retry reading this file"
              ) : (
                "Read this file"
              )}
            </button>
          </div>
        </section>
      ) : (
        <>
          <p className="import-review-status" role="status">
            <span>
              {generic ? factRows.length : draft.observations.length}{" "}
              {generic ? "field" : "measurement"}
              {(generic ? factRows.length : draft.observations.length) === 1
                ? ""
                : "s"}{" "}
              ·{" "}
              {draft.extraction_mode === "local-teleocr"
                ? "Local OCR model draft"
                : draft.extraction_mode === "meta"
                  ? "Meta model draft"
                  : ["local", "local-pdf-text"].includes(draft.extraction_mode)
                    ? "Local text · no model"
                    : "Extraction draft"}
            </span>
            <strong>
              {phase === "adding"
                ? "Saving… Keep this tab open."
                : attempt
                  ? "Save unconfirmed · Retry the same fields."
                  : (generic ? factRows.length : rows.length)
                    ? "Review the fields, then save this file."
                    : "Read the source excerpts. These fields cannot be saved yet."}
            </strong>
          </p>
          {draft.warnings.map((warning, i) => (
            <p className="safe-note" key={i}>
              <AlertCircle size={13} /> {warning}
            </p>
          ))}
          {draft.extraction_review && (
            <ExtractionReviewSummary review={draft.extraction_review} />
          )}
          {generic ? (
            <GenericFactReview
              draft={draft}
              rows={factRows}
              locked={locked}
              busy={busy}
              uncertain={!!attempt}
              onChange={updateFact}
              onSave={() => void commit()}
              onSkip={discard}
            />
          ) : (
            <form
              className="import-review-form"
              onSubmit={(e) => {
                e.preventDefault();
                void commit();
              }}
            >
              <div className="review-layout import-review-layout">
                <div className="import-review-editor">
                  {rows.map((row, index) => {
                    const original = draft.observations[index];
                    return (
                      <article
                        key={row.id}
                        id={`import-measurement-${index}`}
                        tabIndex={-1}
                        aria-label={`Measurement ${index + 1}`}
                        className={
                          "review-card " +
                          (selected === index ? "selected " : "") +
                          (!row.keep ? "excluded" : "")
                        }
                      >
                        <div className="review-card-top">
                          <strong>Measurement {index + 1}</strong>
                          <label className="check-row">
                            <input
                              type="checkbox"
                              aria-label={`Include measurement ${index + 1}`}
                              disabled={locked}
                              checked={row.keep}
                              onChange={(e) =>
                                update(row.id, { keep: e.target.checked })
                              }
                            />
                            {row.keep ? "Include" : "Excluded"}
                          </label>
                        </div>
                        <div className="review-fields">
                          <label className="field metric-field">
                            Recorded metric
                            <select
                              disabled={locked || !row.keep}
                              value={row.metric}
                              aria-label={`Metric ${index + 1}`}
                              onChange={(e) =>
                                update(row.id, {
                                  metric: e.target.value as ReviewRow["metric"],
                                })
                              }
                            >
                              <option value="egfr">
                                {metricLabel("egfr")}
                              </option>
                              <option value="hba1c">
                                {metricLabel("hba1c")}
                              </option>
                              <option value="ldl">{metricLabel("ldl")}</option>
                            </select>
                            {row.metric !== original.metric && (
                              <small>Was {metricLabel(original.metric)}</small>
                            )}
                          </label>
                          <label className="field">
                            Recorded value
                            <input
                              aria-label={`Value ${index + 1}`}
                              type="number"
                              step="any"
                              min="0"
                              required
                              value={row.valueText}
                              disabled={locked || !row.keep}
                              onChange={(e) =>
                                update(row.id, { valueText: e.target.value })
                              }
                            />
                            {row.valueText !== String(original.value) && (
                              <small>Edited · was {original.value}</small>
                            )}
                          </label>
                          <label className="field">
                            Printed unit
                            <input
                              aria-label={`Unit ${index + 1}`}
                              required
                              maxLength={80}
                              value={row.unit}
                              disabled={locked || !row.keep}
                              onChange={(e) =>
                                update(row.id, { unit: e.target.value })
                              }
                            />
                            {row.unit !== original.unit && (
                              <small>Edited · was {original.unit}</small>
                            )}
                          </label>
                          <label className="field">
                            Measured on
                            <input
                              aria-label={`Measured on ${index + 1}`}
                              type="date"
                              required
                              value={row.date}
                              disabled={locked || !row.keep}
                              onChange={(e) =>
                                update(row.id, { date: e.target.value })
                              }
                            />
                            {row.date !== original.date && (
                              <small>
                                Edited · was {dateLabel(original.date)}
                              </small>
                            )}
                          </label>
                        </div>
                        <div className="review-card-footer">
                          <button
                            type="button"
                            className="text-button"
                            onClick={() => inspectSource(index)}
                          >
                            Inspect source <ArrowUpRight size={13} />
                          </button>
                          <button
                            type="button"
                            className="text-button"
                            disabled={locked}
                            onClick={() =>
                              update(row.id, {
                                ...original,
                                keep: true,
                                valueText: String(original.value),
                              })
                            }
                          >
                            <RotateCcw size={12} />
                            Restore proposal
                          </button>
                        </div>
                      </article>
                    );
                  })}
                  <p className="safe-note">
                    {keep.length} included · {rows.length - keep.length}{" "}
                    excluded. Saving keeps the selected measurements and your
                    review locally. This prototype has no undo.
                  </p>
                  <div className="review-actions">
                    <p>
                      Originals and disagreements
                      <br />
                      stay preserved.
                    </p>
                    <div>
                      <button
                        className="secondary"
                        type="button"
                        disabled={busy || !!attempt}
                        onClick={discard}
                      >
                        Skip file · keep review
                      </button>
                      <button
                        className="primary"
                        disabled={
                          busy || !!draft.already_committed || keep.length === 0
                        }
                      >
                        {busy
                          ? "Saving…"
                          : draft.already_committed
                            ? "Already added"
                            : attempt
                              ? "Retry the same measurements"
                              : `Save ${keep.length} reviewed measurement${keep.length === 1 ? "" : "s"}`}
                      </button>
                    </div>
                  </div>
                </div>
                <aside
                  className="source-panel import-review-source"
                  ref={sourcePanel}
                  tabIndex={-1}
                  aria-label="Original source for selected measurement"
                >
                  {active && (
                    <button
                      type="button"
                      className="text-button import-source-return"
                      onClick={returnToMeasurement}
                    >
                      Back to measurement {selected + 1}
                    </button>
                  )}
                  <span className="eyebrow">Original source</span>
                  <h3>
                    {active
                      ? `Measurement ${selected + 1} · ${metricLabel(active.metric)}`
                      : "Original document"}
                  </h3>
                  {active && (
                    <>
                      <div className="source-meta">
                        Measured: {dateLabel(active.date)}
                        <br />
                        Report issued:{" "}
                        {active.reported_at
                          ? timeLabel(active.reported_at)
                          : active.reported_at_raw
                            ? `Unresolved: ${active.reported_at_raw}`
                            : "Not recorded"}
                        {active.page && (
                          <>
                            <br />
                            Page {active.page}
                          </>
                        )}
                      </div>
                      <blockquote>
                        {active.source_span ||
                          "No excerpt was extracted for this measurement."}
                      </blockquote>
                    </>
                  )}
                  {draft.source.original_available &&
                    !attempt &&
                    !draft.already_committed && (
                      <a
                        className="text-button"
                        href={
                          "/api/drafts/" +
                          encodeURIComponent(draft.id) +
                          "/original"
                        }
                        download
                      >
                        Download original <ArrowUpRight size={14} />
                      </a>
                    )}
                  <p className="safe-note">
                    Availability begins when your reviewed measurements are
                    added. It is separate from the measurement and report dates.
                  </p>
                  <details className="exact-time">
                    <summary>Full extracted text</summary>
                    <blockquote>{draft.source.content}</blockquote>
                  </details>
                </aside>
              </div>
            </form>
          )}
        </>
      )}
      {error && !finished && (
        <div role="alert" className="error-banner">
          <AlertCircle size={17} />
          <div>{error}</div>
        </div>
      )}
      {!!queue.length && (
        <p className="import-queue-memory">
          Files and unsaved reviews stay in this tab while you close and reopen
          this window. Reloading or closing the tab loses the queue. Files
          without supported recorded fields cannot be saved here.
        </p>
      )}
    </Modal>
  );
}
