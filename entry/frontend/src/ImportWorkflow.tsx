import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowUpRight,
  FileText,
  LoaderCircle,
  Upload,
} from "lucide-react";
import { api, ApiError, post } from "./api";
import ReportCoverageSummary from "./ReportCoverageSummary";
import { Modal } from "./ui";
import { type Commit, type Draft, type Health } from "./types";
import {
  appendFiles,
  acceptDraft,
  beginFactCommit,
  failCommit,
  finishCommit,
  navigationLocked,
  summary,
  statusLabel,
  fileError,
  extension,
  readingOptions,
  previewReaderFields,
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
  onDraftChange: (hasDraft: boolean, pendingCount: number) => void;
  onCommitted: (result: Commit) => void;
}) {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [queueNotice, setQueueNotice] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const inFlight = useRef(false);
  const current = queue.find((item) => item.id === activeId) || queue[0];
  const draft = current?.draft || null;
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
  const includedCount = factRows.filter((row) => row.keep).length;
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
  const metaAvailable = health?.provider.mode === "meta";
  const textOnly =
    !!current && ["csv", "txt"].includes(extension(current.file));
  const imageFile =
    !!current && ["png", "jpg", "jpeg"].includes(extension(current.file));
  const readers = current ? readingOptions(current.file, metaAvailable) : [];
  const extractionAvailable = readers.some(
    (reader) => reader.value === extraction && reader.available,
  );
  const patch = (id: string, value: Partial<QueueItem>) =>
    setQueue((items) =>
      items.map((item) => (item.id === id ? { ...item, ...value } : item)),
    );
  useEffect(() => {
    onDraftChange(totals.pending > 0, totals.pending);
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
    patch(item.id, { status: "reading", error: "", reportCoverage: undefined });
    try {
      const body = new FormData();
      body.append("file", item.file);
      body.append("synthetic_confirmed", "true");
      const readerFields = previewReaderFields(
        item.file,
        item.extraction,
        metaAvailable,
      );
      body.append("use_meta", readerFields.use_meta);
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
        reportCoverage:
          failure instanceof ApiError ? failure.reportCoverage : undefined,
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
      submitting = beginFactCommit(current);
    } catch (failure) {
      patch(current.id, { error: (failure as Error).message });
      return;
    }
    const wasUncertain = current.status === "uncertain";
    inFlight.current = true;
    patch(current.id, submitting);
    try {
      const result = await post<Commit>("/history/commit", {
        draft_id: draft.id,
        synthetic_confirmed: true,
        reviewed_facts: submitting.factAttempt,
      });
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
  const updateFact = (id: string, value: Partial<FactReviewRow>) => {
    if (!current || locked) return;
    patch(current.id, {
      factRows: factRows.map((row) =>
        row.id === id ? { ...row, ...value } : row,
      ),
    });
  };
  const reviewing = !!draft && !finished;
  if (!open) return null;
  return (
    <Modal title="Add records" onClose={close} busy={busy} wide={!!draft}>
      <div className="import-workflow">
        <input
          ref={input}
          hidden
          type="file"
          multiple
          accept=".csv,.txt,.pdf,.png,.jpg,.jpeg"
          disabled={queueLocked || queue.length >= MAX_FILES}
          onChange={(event) => {
            selectFiles(Array.from(event.target.files || []));
            event.target.value = "";
          }}
        />
        {current && (
          <div className="import-review-heading">
            <span>
              File {queue.findIndex((item) => item.id === current.id) + 1} of{" "}
              {queue.length} ·{" "}
              {reviewing ? "Review" : statusLabel[current.status]}
            </span>
            <h3>{current.file.name}</h3>
          </div>
        )}
        {!!queue.length && (
          <details className="import-files-disclosure" key={current?.id}>
            <summary>
              {queue.length === 1
                ? "Selected file"
                : `All ${queue.length} files`}
              {totals.errors > 0 ? ` · ${totals.errors} need attention` : ""}
            </summary>
            <div className="import-queue-heading">
              <p>Review and save one file at a time.</p>
              <button
                type="button"
                className="secondary"
                disabled={queueLocked || queue.length >= MAX_FILES}
                onClick={() => input.current?.click()}
              >
                <Upload size={16} /> Add files
              </button>
            </div>
            <p className="import-queue-limits">
              Up to 10 files · 8 MB each · CSV, text, PDF, PNG or JPEG.
            </p>
            {!!queue.length && (
              <>
                <ol className="import-queue" aria-label="Selected files">
                  {queue.map((item, index) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        aria-current={
                          item.id === current?.id ? "step" : undefined
                        }
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
                    {totals.confirmed} file{totals.confirmed === 1 ? "" : "s"}{" "}
                    in your history
                  </strong>
                  <span>
                    {[
                      totals.measurements > 0
                        ? `${totals.measurements} new field${totals.measurements === 1 ? "" : "s"} confirmed`
                        : "",
                      totals.duplicates
                        ? `${totals.duplicates} already saved`
                        : "",
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
        )}
        {queueNotice && (
          <p role="status" className="safe-note">
            {queueNotice}
          </p>
        )}
        {!current ? (
          <div className="import-queue-empty">
            <FileText size={28} />
            <h3>Start with a report</h3>
            <p>
              Bring its results, dates and original into your history. You
              review everything before saving.
            </p>
            <button
              type="button"
              className="primary"
              onClick={() => input.current?.click()}
            >
              <Upload size={16} /> Choose files
            </button>
            <p className="import-queue-limits">
              Up to 10 files · 8 MB each · CSV, text, PDF or images.
            </p>
            <p className="safe-note">
              Selecting sends nothing. This demo accepts synthetic examples
              only.
            </p>
            <details className="import-examples">
              <summary>Try an example report</summary>
              <a href="/examples/checkup-october-2026.csv" download>Checkup · 8 tests with lab details</a>
              <div className="table-footer">
                <a href="/examples/whole-history.csv" download>
                  Mixed history <ArrowUpRight size={13} />
                </a>
                <a href="/examples/delayed-history.csv" download>
                  Earlier record <ArrowUpRight size={13} />
                </a>
                <a href="/examples/update.csv" download>
                  New record <ArrowUpRight size={13} />
                </a>
              </div>
            </details>
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
            <p>
              {current.status === "skipped"
                ? "Nothing from this file was added. Its review stays here if you return to it."
                : current.status === "duplicate" || current.receipt?.duplicate
                  ? "No records were added again. This file is already in your history."
                  : `${current.receipt?.inserted || 0} reviewed ${current.receipt?.fact_ids ? "field" : "measurement"}${current.receipt?.inserted === 1 ? "" : "s"} added. Your selected history view is unchanged.`}
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
                        !["saved", "skipped", "duplicate"].includes(
                          item.status,
                        ),
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
                    ? "How to read this image"
                    : extraction === "meta"
                      ? "Reading with Meta"
                      : "Reading on this computer"}
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
                    {readers.map((reader) => (
                      <option
                        key={reader.value}
                        value={reader.value}
                        disabled={!reader.available}
                      >
                        {reader.label}
                      </option>
                    ))}
                  </select>
                </label>
                <p className="safe-note">
                  {extraction === "meta"
                    ? "Meta reads up to 12 pages in groups, then checks the proposed fields. At most 8 model requests per file. Page details show what was processed; you review before saving."
                    : "Structured CSV keeps named fields. Unrecognized prose stays editable source text. Up to 30 PDF pages; scanned pages require Meta."}
                </p>
              </details>
            )}
            {imageFile && !extractionAvailable && (
              <p className="safe-note">
                {metaAvailable
                  ? "Choose Meta to read this image, or skip it and continue."
                  : "Meta must be configured to read this image. You can skip it and continue."}
              </p>
            )}
            <p className="progress-note" role="status">
              {phase === "reading"
                ? "Reading this file… No records have been saved."
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
              <strong>
                {phase === "adding"
                  ? "Saving… Keep this tab open."
                  : attempt
                    ? "Save unconfirmed · Retry the same fields."
                    : factRows.length
                      ? "Check these against your report."
                      : "No fields are available to save. Review the source below."}
              </strong>
              <span>
                {draft.extraction_mode === "local-teleocr"
                  ? "Local OCR model draft"
                  : draft.extraction_mode === "meta"
                    ? "Meta model draft"
                    : ["local", "local-pdf-text"].includes(
                          draft.extraction_mode,
                        )
                      ? "Local text · no model"
                      : "Extraction draft"}
              </span>
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
              <p role="alert">
                This older draft cannot be reviewed by this reader. Reopen it
                with the current service; no records have been saved.
              </p>
            )}
          </>
        )}
        {current?.reportCoverage && (
          <ReportCoverageSummary coverage={current.reportCoverage} />
        )}
        {error && !finished && (
          <div role="alert" className="error-banner">
            <AlertCircle size={17} />
            <div>{error}</div>
          </div>
        )}
        {!!queue.length && (
          <p className="import-queue-memory">
            You can close this window and continue in this tab. Reloading or
            closing the tab loses unsaved reviews.
          </p>
        )}
      </div>
    </Modal>
  );
}
