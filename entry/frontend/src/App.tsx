import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  Clock3,
  Download,
  FileText,
  GitCompareArrows,
  LoaderCircle,
  X,
} from "lucide-react";
import Shell, { type Page } from "./Shell";
import ImportWorkflow from "./ImportWorkflow";
import SourceCubeHome from "./SourceCubeHome";
import MeasurementsWorkspace from "./MeasurementsWorkspace";
import HistoryReplayWorkspace from "./HistoryReplayWorkspace";
import type { HistoryComparison, HistoryView } from "./historyTypes";
import { replayRequest, replayMatchesRequest } from "./historyReplay.mjs";
import ChangesWorkspace from "./ChangesWorkspace";
import HistoryTimeline from "./HistoryTimeline";
import RecordBrief from "./RecordBrief";
import HistoryQuestionPanel from "./HistoryQuestionPanel";
import useHistoryView from "./useHistoryView";
import { api, post } from "./api";
import { Modal, dateLabel, timeLabel, endOfDay } from "./ui";
import {
  metricLabel,
  type Change,
  type Commit,
  type Health,
  type Source,
  type View,
} from "./types";

type Inspector = { view: View; ids: string[] };
const originalUrl = (view: View, source: Source) =>
  "/api/records/" +
  encodeURIComponent(source.id) +
  "/original?as_of=" +
  view.scope.as_of +
  "&known_at=" +
  encodeURIComponent(view.scope.known_at);
function EvidenceInspector({
  value,
  onClose,
}: {
  value: Inspector;
  onClose: () => void;
}) {
  const { view, ids } = value;
  const expanded = new Set(
    ids.flatMap(
      (id) =>
        view.conflicts
          .find((c) => c.id === id)
          ?.observations.map((o) => o.id) || [id],
    ),
  );
  const observations = view.observations.filter(
    (o) => expanded.has(o.id) || expanded.has(o.source_id),
  );
  const sources = view.sources.filter(
    (s) => expanded.has(s.id) || observations.some((o) => o.source_id === s.id),
  );
  return (
    <Modal title="Source details" onClose={onClose}>
      <p className="modal-copy">
        Measured through {dateLabel(view.scope.as_of)} · Records available
        through {timeLabel(view.scope.known_at)}.
      </p>
      {sources.map((source) => (
        <section key={source.id}>
          <div className="draft-header">
            <FileText size={23} />
            <div>
              <strong>{source.title}</strong>
              <small>
                {source.provider} ·{" "}
                {source.type === "lab_report" ? "Lab report" : source.type}
              </small>
            </div>
          </div>
          {observations
            .filter((o) => o.source_id === source.id)
            .map((o) => (
              <article key={o.id}>
                <div className="evidence-value">
                  {o.value}
                  <span>{o.unit}</span>
                </div>
                <span className="evidence-label">
                  {metricLabel(o.metric)} · recorded fact
                  {o.page ? ` · page ${o.page}` : ""}
                </span>
                <div className="evidence-times">
                  <div>
                    <span>Measured</span>
                    <strong>{dateLabel(o.date)}</strong>
                  </div>
                  <div>
                    <span>Report issued</span>
                    <strong>
                      {o.reported_at
                        ? timeLabel(o.reported_at)
                        : o.reported_at_raw
                          ? `Unresolved: ${o.reported_at_raw}`
                          : "Not recorded"}
                    </strong>
                  </div>
                  <div>
                    <span>Added to Modus</span>
                    <strong>
                      {timeLabel(o.available_at || source.available_at)}
                    </strong>
                  </div>
                </div>
                <blockquote className="evidence-excerpt">
                  {o.source_span || "No source excerpt is available."}
                </blockquote>
                {!!o.reviewed_fields?.length && (
                  <p className="safe-note">
                    Edited during review: {o.reviewed_fields.join(", ")}. The
                    excerpt preserves the original proposal.
                  </p>
                )}
                <details className="exact-time">
                  <summary>Exact dates and provenance</summary>
                  <code>
                    Measured: {o.date}
                    <br />
                    Report issued:{" "}
                    {o.reported_at || o.reported_at_raw || "Not recorded"}
                    <br />
                    Available: {o.available_at || source.available_at}
                    <br />
                    Observation: {o.id}
                    <br />
                    Source: {source.id}
                  </code>
                </details>
              </article>
            ))}
          {!observations.some((o) => o.source_id === source.id) && (
            <blockquote className="evidence-excerpt">
              {source.content ||
                "Full source text is not available in this view."}
            </blockquote>
          )}
          <p className="safe-note">
            {source.availability_basis?.includes("synthetic") ||
            source.availability_basis?.includes("authored")
              ? "This example uses authored availability dates, not historical system logs."
              : "Availability is recorded when reviewed measurements enter Modus."}
          </p>
          {source.original_available ? (
            <a className="secondary" href={originalUrl(view, source)} download>
              Download original in this scope <Download size={15} />
            </a>
          ) : (
            <p className="safe-note">
              The full original is not available in this view. It may not have
              been supplied, or may contain measurements outside the selected
              period.
            </p>
          )}
          <hr
            style={{
              border: 0,
              borderTop: "1px solid var(--line)",
              margin: "24px 0",
            }}
          />
        </section>
      ))}
      {!sources.length && (
        <div className="empty">
          No supporting record was found within this evidence view.
        </div>
      )}
    </Modal>
  );
}

function AskWorkspace({
  view,
  historical,
  onScope,
}: {
  view: View;
  historical: boolean;
  onScope: (scope: HistoryView["scope"]) => void;
}) {
  const history = useHistoryView(view.scope, !historical);
  useEffect(() => {
    if (history.view) onScope(history.view.scope);
  }, [history.view, onScope]);
  if (history.error)
    return (
      <section className="panel empty" role="alert">
        <AlertCircle size={24} />
        <h2>Your records could not be loaded</h2>
        <p>{history.error}</p>
        <button className="secondary" onClick={history.refresh}>
          Try again
        </button>
      </section>
    );
  if (!history.view)
    return (
      <section className="panel loading" role="status">
        <LoaderCircle size={24} className="spin" /> Loading your records…
      </section>
    );
  return (
    <div className="ask-workspace">
      <HistoryQuestionPanel view={history.view} />
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>("Home");
  const [asOf, setAsOf] = useState(() => {
    const today = new Date();
    return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  });
  const [mode, setMode] = useState<"then" | "latest" | "custom">("latest");
  const [knownDate, setKnownDate] = useState("2021-12-31");
  const [scopeOpen, setScopeOpen] = useState(false);
  const recordedDateInput = useRef<HTMLInputElement>(null);
  const requestedKnown =
    mode === "latest" ? null : endOfDay(mode === "then" ? asOf : knownDate);
  const key = JSON.stringify([asOf, requestedKnown]);
  const keyRef = useRef(key);
  keyRef.current = key;
  const [health, setHealth] = useState<Health | null>(null);
  const [loaded, setLoaded] = useState<{ key: string; view: View } | null>(
    null,
  );
  const [comparison, setComparison] = useState<{
    key: string;
    data: HistoryComparison;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState("");
  const [comparisonError, setComparisonError] = useState("");
  const [inspector, setInspector] = useState<Inspector | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [hasDraft, setHasDraft] = useState(false);
  const [saved, setSaved] = useState<Commit | null>(null);
  const displayedHistory = useRef<{
    key: string;
    page: Page;
    scope: HistoryView["scope"];
  } | null>(null);
  const importBaseline = useRef<HistoryView["scope"] | null>(null);
  const [savedBaseline, setSavedBaseline] = useState<
    HistoryView["scope"] | null
  >(null);
  const comparisonBaseline = useRef<HistoryView["scope"] | null>(null);
  const [loadedChanges, setLoadedChanges] = useState<{
    key: string;
    items: Change[];
  } | null>(null);
  const [changesLoading, setChangesLoading] = useState(false);
  const [changesError, setChangesError] = useState("");
  const sequence = useRef(0),
    epoch = useRef(0);
  const view = loaded?.key === key ? loaded.view : null;
  const pair = comparison?.key === key ? comparison.data : null;
  const displayed = view;
  const ready = !!displayed && !loading && !comparing;
  const scopeExpanded = page === "Replay" || scopeOpen;
  const canCompare = mode !== "latest" || !!saved;
  const today = new Date();
  const currentDay = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  const captureDisplayedScope = useCallback(
    (scope: HistoryView["scope"]) => {
      displayedHistory.current = { key, page, scope };
    },
    [key, page],
  );
  function currentHistoryScope(): HistoryView["scope"] | null {
    if (page === "Replay" && pair) return pair.after.scope;
    const current = displayedHistory.current;
    if (
      current?.key === key &&
      current.page === page &&
      current.scope.known_at === view?.scope.known_at
    )
      return current.scope;
    if (!view) return null;
    return {
      ...view.scope,
      as_of:
        (page === "Home" || page === "Ask" || page === "Brief") &&
        mode === "latest" &&
        asOf === currentDay
          ? null
          : view.scope.as_of,
    };
  }
  function openImport() {
    importBaseline.current = currentHistoryScope();
    setImportOpen(true);
  }
  const inspect = (scopeView: View, ids: string[]) =>
    setInspector({ view: scopeView, ids });
  useEffect(() => {
    void api<Health>("/health")
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);
  async function refresh() {
    const requestKey = key,
      request = ++sequence.current;
    epoch.current++;
    displayedHistory.current = null;
    comparisonBaseline.current = null;
    setLoading(true);
    setError("");
    setComparison(null);
    setComparing(false);
    setComparisonError("");
    setInspector(null);
    try {
      const result = await api<View>(
        "/records/view?as_of=" +
          asOf +
          (requestedKnown
            ? "&known_at=" + encodeURIComponent(requestedKnown)
            : ""),
      );
      if (request === sequence.current && requestKey === keyRef.current)
        setLoaded({ key: requestKey, view: result });
    } catch (e) {
      if (request === sequence.current) {
        setLoaded(null);
        setError((e as Error).message);
      }
    } finally {
      if (request === sequence.current) setLoading(false);
    }
  }
  useEffect(() => {
    void refresh();
  }, [key]);
  async function compareCurrent(baseline = currentHistoryScope()) {
    if (!view || !baseline || loading || comparing) return;
    comparisonBaseline.current = baseline;
    const requestBody = replayRequest(baseline);
    const requestKey = key,
      currentEpoch = ++epoch.current;
    setComparison(null);
    setComparing(true);
    setComparisonError("");
    setInspector(null);
    try {
      const result = await post<HistoryComparison>(
        "/history/compare",
        requestBody,
      );
      if (!replayMatchesRequest(result, requestBody))
        throw new Error(
          "The comparison did not match the requested dates. Please try again.",
        );
      if (currentEpoch === epoch.current && requestKey === keyRef.current)
        setComparison({ key: requestKey, data: result });
    } catch (e) {
      if (currentEpoch === epoch.current)
        setComparisonError((e as Error).message);
    } finally {
      if (currentEpoch === epoch.current) setComparing(false);
    }
  }
  const changesKey = displayed?.scope.known_at || "";
  const changes = loadedChanges?.key === changesKey ? loadedChanges.items : [];
  async function loadChanges() {
    if (!changesKey || !ready) return;
    const currentEpoch = epoch.current;
    setChangesLoading(true);
    setChangesError("");
    setLoadedChanges(null);
    try {
      const result = await api<{ changes: Change[] }>(
        "/changes?known_at=" + encodeURIComponent(changesKey),
      );
      if (currentEpoch === epoch.current)
        setLoadedChanges({ key: changesKey, items: result.changes });
    } catch (e) {
      if (currentEpoch === epoch.current) setChangesError((e as Error).message);
    } finally {
      setChangesLoading(false);
    }
  }
  useEffect(() => {
    if (page === "Changes" && ready) void loadChanges();
  }, [page, changesKey, ready]);
  function committed(result: Commit) {
    setSaved(result);
    setSavedBaseline(importBaseline.current);
    setComparison(null);
    setComparing(false);
    epoch.current++;
  }
  return (
    <>
      <Shell
        page={page}
        setPage={setPage}
        onImport={openImport}
        hasDraft={hasDraft}
      >
        {saved && (
          <div className="success-banner" role="status">
            <Check size={18} />
            <div className="banner-content">
              <strong>
                {saved.duplicate
                  ? "This file was already saved."
                  : "Record saved."}
              </strong>
              <p>
                {saved.duplicate
                  ? "No records were added again. Original availability: "
                  : `${saved.inserted} reviewed ${saved.fact_ids ? "record" : "measurement"}${saved.inserted === 1 ? "" : "s"} saved · Added to Modus: `}
                {timeLabel(saved.available_at)}
              </p>
              {(mode !== "latest" || !!pair || asOf !== currentDay) && (
                <p>Your selected dates are still in place.</p>
              )}
              <div className="banner-actions">
                <button
                  className="text-button"
                  onClick={() => {
                    setMode("latest");
                    setPage(saved.fact_ids ? "Timeline" : "Home");
                    if (mode === "latest") void refresh();
                  }}
                >
                  View updated history <ArrowRight size={14} />
                </button>
                <button
                  className="text-button"
                  disabled={!ready || !savedBaseline}
                  onClick={() => {
                    setPage("Replay");
                    void compareCurrent(savedBaseline);
                  }}
                >
                  Compare with previous view <ArrowUpRight size={14} />
                </button>
              </div>
            </div>
            <button
              className="icon-button"
              aria-label="Dismiss saved notice"
              onClick={() => setSaved(null)}
            >
              <X size={17} />
            </button>
          </div>
        )}
        {page !== "Home" && !(page === "Replay" && pair) && (
          <section
            className={
              "scope-panel " +
              (!scopeExpanded ? "scope-compact" : "") +
              (page === "Replay" ? " scope-replay" : "")
            }
            aria-label="View dates"
          >
            {page !== "Replay" && (
              <div className="scope-summary scope-summary-chip">
                <button
                  className="scope-chip"
                  aria-expanded={scopeExpanded}
                  aria-controls="view-date-controls"
                  onClick={() => setScopeOpen(!scopeOpen)}
                >
                  <Clock3 size={15} />
                  <span>
                    View as of{" "}
                    <strong>
                      {displayed
                        ? dateLabel(displayed.scope.known_at.slice(0, 10))
                        : mode === "latest"
                          ? "now"
                          : dateLabel(mode === "then" ? asOf : knownDate)}
                    </strong>
                  </span>
                  <ChevronDown size={14} aria-hidden="true" />
                </button>
              </div>
            )}
            <div id="view-date-controls" hidden={!scopeExpanded}>
              <div className="scope-form">
                <label className="field">
                  Recorded dates through
                  <input
                    ref={recordedDateInput}
                    aria-label="Recorded dates through"
                    type="date"
                    value={asOf}
                    onChange={(e) => {
                      if (e.target.value) setAsOf(e.target.value);
                    }}
                  />
                </label>
                <label className="field">
                  Records available by
                  <select
                    aria-label="Records available by"
                    value={mode}
                    onChange={(e) => setMode(e.target.value as typeof mode)}
                  >
                    <option value="then">End of recorded period</option>
                    <option value="latest">Now</option>
                    <option value="custom">Choose availability date</option>
                  </select>
                </label>
                {mode === "custom" && (
                  <label className="field">
                    Availability date (UTC)
                    <input
                      aria-label="Availability date"
                      type="date"
                      value={knownDate}
                      onChange={(e) => {
                        if (e.target.value) setKnownDate(e.target.value);
                      }}
                    />
                  </label>
                )}
                <button
                  className="secondary"
                  disabled={!view || loading || comparing || !canCompare}
                  aria-describedby={
                    !canCompare ? "compare-date-help" : undefined
                  }
                  onClick={() => {
                    setPage("Replay");
                    void compareCurrent();
                  }}
                >
                  {comparing ? (
                    <LoaderCircle className="spin" size={16} />
                  ) : (
                    <GitCompareArrows size={17} />
                  )}
                  Compare with now
                </button>
              </div>
              {!canCompare && (
                <p className="scope-note" id="compare-date-help">
                  Choose an earlier availability date to compare with records
                  available now.
                </p>
              )}
              <details className="scope-note">
                <summary>How these dates work</summary>
                <p>
                  Recorded dates through sets when events were recorded as
                  happening. Records available by sets when reviewed evidence
                  entered this history.{" "}
                  {mode === "latest"
                    ? "“Now” is captured once by the server for this view."
                    : "Availability dates include the full selected day in UTC."}{" "}
                  Report issue time is separate. Replays use current code;
                  fixture availability is authored.
                </p>
              </details>
            </div>
          </section>
        )}
        {comparisonError &&
          (page === "Replay" ||
            (page === "Records" &&
              comparisonError.startsWith("Export failed."))) && (
            <div role="alert" className="error-banner">
              <AlertCircle size={17} />
              <div>
                {comparisonError}
                {!comparisonError.startsWith("Export failed.") && (
                  <>
                    <br />
                    <button
                      className="text-button"
                      onClick={() =>
                        void compareCurrent(
                          comparisonBaseline.current || currentHistoryScope(),
                        )
                      }
                      disabled={!view || comparing}
                    >
                      Retry comparison
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
        {loading || comparing || (!view && !error) ? (
          <div className="panel loading" role="status">
            <LoaderCircle className="spin" size={25} />
            <span>
              {comparing
                ? "Capturing both sides of the comparison…"
                : "Loading records for the selected dates…"}
            </span>
          </div>
        ) : !view ? (
          <div role="alert" className="panel empty">
            <AlertCircle size={26} />
            <strong>This evidence view could not be loaded.</strong>
            <p>{error}</p>
            <p>No previous records are shown under these dates.</p>
            <button className="secondary" onClick={() => void refresh()}>
              Retry this view
            </button>
          </div>
        ) : (
          <>
            {page === "Home" && displayed && (
              <SourceCubeHome
                view={displayed}
                onScope={captureDisplayedScope}
                onNavigate={setPage}
                onImport={openImport}
                hasDraft={hasDraft}
                historical={mode !== "latest" || asOf !== currentDay}
                onCurrent={() => {
                  setAsOf(currentDay);
                  setMode("latest");
                  if (asOf === currentDay && mode === "latest") void refresh();
                }}
              />
            )}
            {page === "Measurements" && displayed && (
              <MeasurementsWorkspace view={displayed} onInspect={inspect} />
            )}
            {page === "Ask" && displayed && (
              <AskWorkspace
                onScope={captureDisplayedScope}
                view={displayed}
                historical={mode !== "latest" || asOf !== currentDay}
              />
            )}
            {page === "Brief" && displayed && (
              <RecordBrief
                scope={displayed.scope}
                historical={mode !== "latest" || asOf !== currentDay}
                onImport={openImport}
              />
            )}
            {page === "Timeline" && displayed && (
              <HistoryTimeline
                onScope={captureDisplayedScope}
                scope={displayed.scope}
                onLatest={() => {
                  setMode("latest");
                  if (mode === "latest") void refresh();
                }}
              />
            )}
            {page === "Replay" && (
              <HistoryReplayWorkspace
                pair={pair}
                scope={
                  pair?.before.scope || comparisonBaseline.current || view.scope
                }
                onReset={() => {
                  setComparison(null);
                  comparisonBaseline.current = null;
                  requestAnimationFrame(() =>
                    recordedDateInput.current?.focus(),
                  );
                }}
              />
            )}
            {page === "Records" && displayed && (
              <>
                <HistoryTimeline
                  onScope={captureDisplayedScope}
                  scope={displayed.scope}
                  viewMode="files"
                  onImport={openImport}
                  hasDraft={hasDraft}
                  onLatest={() => {
                    setMode("latest");
                    if (mode === "latest") void refresh();
                  }}
                />
              </>
            )}
            {page === "Changes" && displayed && (
              <ChangesWorkspace
                view={displayed}
                changes={changes}
                loading={
                  changesLoading ||
                  (!changesError && loadedChanges?.key !== changesKey)
                }
                error={changesError}
                onRefresh={() => void loadChanges()}
                onInspect={inspect}
              />
            )}
          </>
        )}
      </Shell>
      <ImportWorkflow
        open={importOpen}
        onClose={() => setImportOpen(false)}
        health={health}
        onDraftChange={setHasDraft}
        onCommitted={committed}
      />
      {inspector && ready && !importOpen && (
        <EvidenceInspector
          value={inspector}
          onClose={() => setInspector(null)}
        />
      )}
    </>
  );
}
