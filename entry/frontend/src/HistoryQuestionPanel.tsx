import { useEffect, useId, useRef, useState } from "react";
import { ArrowUp, LoaderCircle } from "lucide-react";
import { api } from "./api";
import type { HistoryView } from "./historyTypes";
import { endOfDay } from "./ui";
import HistoryAnswerView, { ScopeText, type HistoryAnswer } from "./HistoryAnswerView";
import {
  historyAnswerMatches,
  historyQuestionKey,
  historyQuestionRequest,
  visibleHistoryAnswer,
} from "./historyQuestionScope.mjs";
import "./history-question.css";

export function historySuggestions(view: HistoryView): [string, string][] {
  const rows = [...view.facts, ...view.undated_facts].filter(row => !row.value_withheld && row.within_date_scope !== false);
  const kinds = new Set(view.facets?.kinds || rows.map(row => row.kind));
  const choices: [string, string][] = [];
  if (rows.some(row => row.label.toLowerCase() === "blood pressure"))
    choices.push(["Last blood pressure record", "When was Blood pressure last recorded?"]);
  if (kinds.has("encounter") && kinds.has("prescription"))
    choices.push(["Visits and prescriptions", "Show my visits and prescriptions"]);
  else if (kinds.has("encounter")) choices.push(["My visits", "Show my visit records"]);
  else if (kinds.has("prescription")) choices.push(["My prescriptions", "Show my prescription records"]);
  if (view.conflicts.length || (view.page && view.counts.conflicts)) choices.push(["Recorded differences", "Which records disagree?"]);
  if (kinds.has("vaccination")) choices.push(["Vaccination records", "Find my vaccination records"]);
  if (kinds.has("imaging_text")) choices.push(["Imaging reports", "Find my imaging reports"]);
  if (kinds.has("measurement")) choices.push(["My measurements", "Show my measurement records"]);
  return choices.slice(0, 3);
}

export default function HistoryQuestionPanel({
  view,
  compact = false,
  seed,
  onSeedUsed,
}: {
  view: HistoryView;
  compact?: boolean;
  seed?: {message: string; afterKnownAt: string} | null;
  onSeedUsed?: () => void;
}) {
  const inputId = useId();
  const [question, setQuestion] = useState("");
  const [compareDate, setCompareDate] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [returned, setReturned] = useState<{
    key: string;
    message: string;
    answer: HistoryAnswer;
  } | null>(null);
  const controller = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  const compareFrom = compareDate ? endOfDay(compareDate) : null;
  const key = historyQuestionKey(view.scope, compareFrom);
  const currentKey = useRef(key);
  currentKey.current = key;
  const answer = visibleHistoryAnswer(returned, key, question) as HistoryAnswer | null;
  const conversation = useRef<{key: string; value: HistoryAnswer['continuation']} | null>(null);
  const continuation = conversation.current?.key === key ? conversation.current.value : undefined;
  const usedSeed = useRef<string | null>(null);
  const suggestions = historySuggestions(view);

  useEffect(() => {
    controller.current?.abort();
    sequence.current++;
    setPending(false);
    setReturned(null);
    setError("");
    conversation.current = null;
    return () => {
      controller.current?.abort();
      sequence.current++;
    };
  }, [key]);

  useEffect(() => {
    if (!seed || view.scope.as_of !== null || Date.parse(view.scope.known_at) <= Date.parse(seed.afterKnownAt)) return;
    const identity = JSON.stringify(seed);
    if (usedSeed.current === identity) return;
    usedSeed.current = identity;
    setQuestion(seed.message);
    void ask(seed.message);
    onSeedUsed?.();
  }, [seed, key]);

  function editQuestion(message: string) {
    controller.current?.abort();
    sequence.current++;
    setPending(false);
    setError("");
    setQuestion(message);
  }

  async function ask(message = question) {
    if (pending || !message.trim()) return;
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
    setError("");
    try {
      const result = await api<HistoryAnswer>("/history/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          historyQuestionRequest(view.scope, message, compareFrom, continuation),
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
      setReturned({ key: requestKey, message: message.trim(), answer: result });
      conversation.current = {key: requestKey, value: result.continuation};
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
      className={`history-question-panel${compact ? " history-question-compact" : ""}`}
      aria-label="Ask about your history"
    >
      {!compact && (
        <p className="history-question-intro">Find a past result, visit or report.</p>
      )}
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
          rows={compact ? 1 : 2}
          maxLength={2000}
          placeholder={
            compact
              ? "Ask about your records…"
              : "What would you like to find in your history?"
          }
          value={question}
          onChange={(event) => editQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (
              compact &&
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();
              void ask();
            }
          }}
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
      {!compact && !answer && suggestions.length > 0 && (
        <div
          className="history-question-examples"
          aria-label="Example history questions"
        >
          {suggestions.map(([label, query]) => (
            <button
              type="button"
              key={label}
              disabled={pending}
              onClick={() => editQuestion(query)}
              aria-label={`Use question: ${query}`}
            >
              {label}
            </button>
          ))}
        </div>
      )}
      {!compact && (
        <details className="history-question-dates">
          <summary>Dates and comparison{compareDate ? " · comparison set" : ""}</summary>
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
      )}
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
      {answer && <HistoryAnswerView answer={answer} pending={pending}
        onRefreshAnswer={() => window.dispatchEvent(new CustomEvent("modus:ask-current-history", {detail: {
          message: answer.followup?.subject || answer.continuation?.subject || returned!.message,
          afterKnownAt: answer.scope.known_at,
        }}))}
        onClarify={message => { setQuestion(message); void ask(message); }} />}
      {answer?.continuation && <button className="text-button" disabled={pending}
        onClick={() => { const message = answer.continuation!.suggested_question; setQuestion(message); void ask(message); }}>
        Show the earlier record
      </button>}
    </section>
  );
}
