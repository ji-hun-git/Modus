import { useEffect, useId, useRef, useState } from "react";
import { ArrowUp, ArrowUpRight, FileText, LoaderCircle } from "lucide-react";
import { api } from "./api";
import type { Answer, Claim } from "./types";
import type { HistoryView } from "./historyTypes";
import { Modal, dateLabel, endOfDay, timeLabel } from "./ui";
import SourceCubeEvidence from "./SourceCubeEvidence";
import {
  historyAnswerMatches,
  historyClaimEvidence,
  historyQuestionKey,
  historyQuestionRequest,
} from "./historyQuestionScope.mjs";
import "./history-question.css";

type HistoryAnswer = Omit<Answer, "scope" | "comparison"> & {
  scope: HistoryView["scope"];
  history_evidence: HistoryView;
  history_comparison?: {
    before: HistoryView["scope"];
    after: HistoryView["scope"];
  } | null;
};

const suggestions = [
  ["Prescriptions", "Show my prescription records"],
  ["Vaccinations", "Find my vaccination records"],
  ["Imaging reports", "Find my imaging reports"],
  ["Visits", "Show my visit records"],
  ["A measurement", 'Find records mentioning "Height"'],
];

function ScopeText({ scope }: { scope: HistoryView["scope"] }) {
  return (
    <>
      {scope.as_of
        ? `Records through ${dateLabel(scope.as_of)}`
        : "All recorded dates"}
      {" · "}Files available through {timeLabel(scope.known_at)}
    </>
  );
}

export default function HistoryQuestionPanel({ view }: { view: HistoryView }) {
  const inputId = useId();
  const [question, setQuestion] = useState("");
  const [compareDate, setCompareDate] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [returned, setReturned] = useState<{
    key: string;
    answer: HistoryAnswer;
  } | null>(null);
  const [inspected, setInspected] = useState<Claim | null>(null);
  const controller = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  const compareFrom = compareDate ? endOfDay(compareDate) : null;
  const key = historyQuestionKey(view.scope, compareFrom);
  const currentKey = useRef(key);
  currentKey.current = key;
  const answer = returned?.key === key ? returned.answer : null;
  const evidence =
    answer && inspected
      ? historyClaimEvidence(answer.history_evidence, inspected.evidence_ids)
      : [];

  useEffect(() => {
    controller.current?.abort();
    sequence.current++;
    setPending(false);
    setReturned(null);
    setInspected(null);
    setError("");
    return () => {
      controller.current?.abort();
      sequence.current++;
    };
  }, [key]);

  async function ask() {
    if (pending || !question.trim()) return;
    if (
      compareFrom &&
      Date.parse(compareFrom) > Date.parse(view.scope.known_at)
    ) {
      setError(
        "Choose a comparison date earlier than this view’s file availability.",
      );
      return;
    }
    const requestKey = key;
    const request = ++sequence.current;
    const active = new AbortController();
    controller.current?.abort();
    controller.current = active;
    setPending(true);
    setReturned(null);
    setInspected(null);
    setError("");
    try {
      const result = await api<HistoryAnswer>("/history/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          historyQuestionRequest(view.scope, question, compareFrom),
        ),
        signal: active.signal,
      });
      if (
        active.signal.aborted ||
        request !== sequence.current ||
        requestKey !== currentKey.current
      )
        return;
      if (!historyAnswerMatches(result, view.scope, compareFrom)) {
        throw new Error(
          "The answer did not match this record view. Please ask again.",
        );
      }
      setReturned({ key: requestKey, answer: result });
    } catch (cause) {
      if (
        !active.signal.aborted &&
        request === sequence.current &&
        requestKey === currentKey.current
      ) {
        setError(
          (cause as Error).message ||
            "Your record question could not be completed.",
        );
      }
    } finally {
      if (request === sequence.current && requestKey === currentKey.current)
        setPending(false);
    }
  }

  return (
    <section
      className="history-question-panel"
      aria-label="Ask about your history"
    >
      <header>
        <h2>Find something in your history</h2>
        <p>
          Search visits, prescriptions, vaccinations, reports and measurements.
        </p>
      </header>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void ask();
        }}
      >
        <label className="sr-only" htmlFor={inputId}>
          Question about your history
        </label>
        <textarea
          id={inputId}
          rows={2}
          maxLength={2000}
          placeholder="Find a record, its original wording, or what was added…"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <button
          type="submit"
          aria-label="Ask about your history"
          disabled={pending || !question.trim()}
        >
          {pending ? (
            <LoaderCircle className="spin" size={18} />
          ) : (
            <ArrowUp size={18} />
          )}
        </button>
      </form>
      <div
        className="history-question-examples"
        aria-label="Example history questions"
      >
        {suggestions.map(([label, query]) => (
          <button
            type="button"
            key={label}
            disabled={pending}
            onClick={() => setQuestion(query)}
            aria-label={`Use question: ${query}`}
          >
            {label}
            <ArrowUpRight size={13} />
          </button>
        ))}
      </div>
      <details className="history-question-dates">
        <summary>Dates used for this question</summary>
        <p>
          <ScopeText scope={view.scope} />
        </p>
        <label className="field">
          Compare additions from date
          <input
            type="date"
            aria-label="Compare additions from date"
            value={compareDate}
            onChange={(event) => setCompareDate(event.target.value)}
          />
        </label>
        <p>
          Optional. Compare records available at the end of this UTC date with
          the view above.
        </p>
        {compareDate && (
          <div className="history-question-compare-actions">
            <button
              type="button"
              className="text-button"
              disabled={pending}
              onClick={() =>
                setQuestion(
                  "Which records became available between these views?",
                )
              }
            >
              Ask what was added
            </button>
            <button
              type="button"
              className="text-button"
              onClick={() => setCompareDate("")}
            >
              Clear comparison
            </button>
          </div>
        )}
      </details>
      <div className="sr-only" role="status">
        {pending
          ? "Searching records in this view."
          : answer
            ? "History answer ready."
            : ""}
      </div>
      {error && (
        <p role="alert" className="error-banner">
          {error}
        </p>
      )}
      {answer && (
        <div className="history-question-answer" aria-label="History answer">
          <div className="history-answer-heading">
            <h3>From your records</h3>
            <span>
              {answer.mode === "meta"
                ? "Meta selected record findings"
                : "Local result · no model called"}
            </span>
          </div>
          <p className="history-answer-scope">
            <ScopeText scope={answer.scope} />
          </p>
          {answer.history_comparison && (
            <p className="history-answer-scope">
              Compared with files available through{" "}
              {timeLabel(answer.history_comparison.before.known_at)}.
            </p>
          )}
          {answer.claims.length ? (
            answer.claims.map((claim) => (
              <article key={claim.id}>
                <p>{claim.text}</p>
                {!!historyClaimEvidence(
                  answer.history_evidence,
                  claim.evidence_ids,
                ).length && (
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => setInspected(claim)}
                  >
                    <FileText size={14} /> View supporting records{" "}
                    <ArrowUpRight size={13} />
                  </button>
                )}
              </article>
            ))
          ) : (
            <p>
              {answer.answer ||
                "No supported record finding was returned for this question."}
            </p>
          )}
          <details className="history-answer-trace">
            <summary>How this answer was made</summary>
            {answer.trace.map((step, index) => (
              <details key={`${step.name}-${index}`}>
                <summary>
                  {step.name} · {step.status} · {step.duration_ms.toFixed(0)} ms
                </summary>
                <pre>
                  {JSON.stringify(
                    {
                      executor: step.executor,
                      arguments: step.arguments,
                      result: step.result,
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
      {answer && inspected && evidence.length > 0 && (
        <Modal
          title="Supporting records"
          onClose={() => setInspected(null)}
          wide
        >
          <p className="history-answer-scope">
            <ScopeText scope={answer.scope} />
          </p>
          <p className="history-evidence-intro">{inspected.text}</p>
          <div className="history-answer-evidence">
            {evidence.map(({ source, facts }) => (
              <SourceCubeEvidence
                key={source.id}
                source={source}
                facts={facts}
                view={answer.history_evidence}
                initialFactId={facts[0]?.id}
              />
            ))}
          </div>
        </Modal>
      )}
    </section>
  );
}
