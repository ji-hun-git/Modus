import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  ArrowUp,
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
import AnswerScope from "./AnswerScope";
import MeasurementsWorkspace from "./MeasurementsWorkspace";
import ReplayWorkspace from "./ReplayWorkspace";
import ChangesWorkspace from "./ChangesWorkspace";
import HistoryTimeline from "./HistoryTimeline";
import RecordBrief from "./RecordBrief";
import HistoryQuestionPanel from "./HistoryQuestionPanel";
import useHistoryView from "./useHistoryView";
import { api, post } from "./api";
import { Modal, dateLabel, timeLabel, endOfDay } from "./ui";
import {
  metricLabel,
  type Answer,
  type Change,
  type Commit,
  type Comparison,
  type Health,
  type Observation,
  type ScopeRequest,
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
}: {
  view: View;
  historical: boolean;
}) {
  const history = useHistoryView(view.scope, !historical);
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
    data: Comparison;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState("");
  const [comparisonError, setComparisonError] = useState("");
  const [inspector, setInspector] = useState<Inspector | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [hasDraft, setHasDraft] = useState(false);
  const [saved, setSaved] = useState<Commit | null>(null);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [questionError, setQuestionError] = useState("");
  const [exporting, setExporting] = useState(false);
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
  const displayed = pair?.after || view;
  const ready = !!displayed && !loading && !comparing;
  const scopeExpanded = page === "Replay" || scopeOpen;
  const canCompare = mode !== "latest" || !!saved;
  const today = new Date();
  const currentDay = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
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
    setLoading(true);
    setError("");
    setComparison(null);
    setComparing(false);
    setComparisonError("");
    setAnswer(null);
    setQuestionError("");
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
  async function compareCurrent() {
    if (!view || loading || comparing) return;
    const requestKey = key,
      currentEpoch = ++epoch.current;
    setComparison(null);
    setComparing(true);
    setComparisonError("");
    setAnswer(null);
    setInspector(null);
    try {
      const result = await post<Comparison>("/records/compare", {
        as_of: view.scope.as_of,
        before_known_at: view.scope.known_at,
        after_known_at: null,
      });
      if (currentEpoch === epoch.current && requestKey === keyRef.current)
        setComparison({ key: requestKey, data: result });
    } catch (e) {
      if (currentEpoch === epoch.current)
        setComparisonError((e as Error).message);
    } finally {
      if (currentEpoch === epoch.current) setComparing(false);
    }
  }
  const scopeRequest = (): ScopeRequest | null =>
    displayed
      ? {
          as_of: displayed.scope.as_of,
          known_at: displayed.scope.known_at,
          ...(pair ? { compare_from: pair.before.scope.known_at } : {}),
        }
      : null;
  async function ask(text = question) {
    const scope = scopeRequest();
    if (!scope || !ready || asking || !text.trim()) return;
    const currentEpoch = epoch.current;
    setQuestion(text);
    setAsking(true);
    setAnswer(null);
    setQuestionError("");
    try {
      const result = await post<Answer>("/agent/chat", {
        ...scope,
        message: text,
      });
      if (currentEpoch === epoch.current) setAnswer(result);
    } catch (e) {
      if (currentEpoch === epoch.current)
        setQuestionError((e as Error).message);
    } finally {
      setAsking(false);
    }
  }
  async function exportView() {
    const scope = scopeRequest();
    if (!ready || !scope || exporting) return;
    setExporting(true);
    try {
      const data = await post<unknown>("/records/export", scope);
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = `modus-records-${scope.as_of}-${pair ? "comparison" : "snapshot"}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setComparisonError(`Export failed. ${(e as Error).message}`);
    } finally {
      setExporting(false);
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
    setAnswer(null);
    setComparing(false);
    epoch.current++;
  }
  const executionLabel = !health
    ? "Connection status unavailable"
    : health.provider.mode === "meta"
      ? "Meta configured · execution shown with each result"
      : "Local · no model call";
  const questions = (
    <section className="panel question-panel">
      <div className="assistant-heading">
        <h2>Ask about a result</h2>
        {page === "Home" && (
          <span className="execution-label">{executionLabel}</span>
        )}
      </div>
      <form
        className="question-form"
        onSubmit={(e) => {
          e.preventDefault();
          void ask();
        }}
      >
        <label className="sr-only" htmlFor="record-question">
          Your question
        </label>
        <textarea
          id="record-question"
          placeholder="Find a recorded value, its source, or a disagreement…"
          maxLength={2000}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button
          aria-label="Send record question"
          disabled={!ready || asking || !question.trim()}
        >
          {asking ? (
            <LoaderCircle className="spin" size={16} />
          ) : (
            <ArrowUp size={17} />
          )}
        </button>
      </form>
      <div className="question-suggestions">
        {[
          { label: metricLabel("hba1c"), query: "Find HbA1c values" },
          { label: "Disagreements", query: "Which recorded values disagree?" },
          {
            label: "Arrivals",
            query: "Which records arrived after this date?",
          },
        ].map(({ label, query: q }) => (
          <button
            key={q}
            aria-label={
              q.includes("arrived") && !pair
                ? "Compare record arrivals in Replay"
                : q === "Find HbA1c values"
                  ? `Find ${label} values`
                  : q
            }
            disabled={!ready || asking}
            title={
              q.includes("arrived") && !pair
                ? "Choose comparison dates in Replay"
                : undefined
            }
            onClick={() =>
              q.includes("arrived") && !pair ? setPage("Replay") : void ask(q)
            }
          >
            {label}
            <ArrowUpRight size={14} />
          </button>
        ))}
      </div>
      {page !== "Home" && <p className="execution-label">{executionLabel}</p>}
      <div className="sr-only" role="status">
        {asking
          ? "Finding supported record facts."
          : answer
            ? "Record response ready."
            : ""}
      </div>
      {questionError && (
        <div role="alert" className="error-banner">
          {questionError}
        </div>
      )}
      {answer && (
        <div className="answer-block">
          <span className="tag">
            {answer.mode === "meta"
              ? "Meta selected record findings"
              : "Local deterministic result"}
          </span>
          <AnswerScope
            scope={answer.scope}
            saved={saved}
            onLatest={() => {
              setMode("latest");
              if (mode === "latest") void refresh();
            }}
          />
          {answer.claims.length ? (
            answer.claims.map((claim) => (
              <article key={claim.id}>
                <p>{claim.text}</p>
                <button
                  className="text-button"
                  onClick={() =>
                    displayed && inspect(displayed, claim.evidence_ids)
                  }
                >
                  <FileText size={13} />
                  View evidence <ArrowUpRight size={12} />
                </button>
              </article>
            ))
          ) : (
            <p>
              No supported record finding was returned. Ask about recorded
              values, arrivals, or source dates.
            </p>
          )}
          <details>
            <summary>How this result was made</summary>
            <p>
              Measured through {dateLabel(answer.scope.as_of)} · Available
              through {timeLabel(answer.scope.known_at)}
            </p>
            {answer.trace.map((trace, i) => (
              <details className="trace" key={i}>
                <summary>
                  {trace.name} · {trace.status} · {trace.duration_ms.toFixed(0)}{" "}
                  ms
                </summary>
                <pre>
                  {JSON.stringify(
                    {
                      executor: trace.executor,
                      arguments: trace.arguments,
                      result: trace.result,
                    },
                    null,
                    2,
                  )}
                </pre>
              </details>
            ))}
            <pre>
              {JSON.stringify(
                { execution: answer.execution, telemetry: answer.telemetry },
                null,
                2,
              )}
            </pre>
          </details>
        </div>
      )}
    </section>
  );
  return (
    <>
      <Shell
        page={page}
        setPage={setPage}
        onImport={() => setImportOpen(true)}
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
                  disabled={!ready}
                  onClick={() => {
                    setPage("Replay");
                    void compareCurrent();
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
        {page !== "Home" && (
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
                  Measurements through
                  <input
                    aria-label="Measurements through"
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
                    <option value="then">End of measurement period</option>
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
                  Measurements through sets when measurements happened. Records
                  available by sets when reviewed evidence entered this history.{" "}
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
                      onClick={() => void compareCurrent()}
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
                onNavigate={setPage}
                onImport={() => setImportOpen(true)}
                hasDraft={hasDraft}
                historical={mode !== "latest" || !!pair || asOf !== currentDay}
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
                view={displayed}
                historical={mode !== "latest" || !!pair || asOf !== currentDay}
              />
            )}
            {page === "Brief" && displayed && (
              <RecordBrief
                scope={displayed.scope}
                historical={mode !== "latest" || !!pair || asOf !== currentDay}
                onImport={() => setImportOpen(true)}
              />
            )}
            {page === "Timeline" && displayed && (
              <HistoryTimeline
                scope={displayed.scope}
                onLatest={() => {
                  setMode("latest");
                  if (mode === "latest") void refresh();
                }}
              />
            )}
            {page === "Replay" && (
              <ReplayWorkspace
                view={view}
                pair={pair}
                current={mode === "latest"}
                canCompare={canCompare}
                exporting={exporting}
                onExport={() => void exportView()}
                onInspect={inspect}
              >
                {questions}
              </ReplayWorkspace>
            )}
            {page === "Records" && displayed && (
              <>
                <HistoryTimeline
                  scope={displayed.scope}
                  viewMode="files"
                  onImport={() => setImportOpen(true)}
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
