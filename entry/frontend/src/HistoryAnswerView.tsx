import { useState } from "react";
import type { Answer, Claim } from "./types";
import type { HistoryView } from "./historyTypes";
import { Modal, dateLabel, timeLabel } from "./ui";
import SourceCubeEvidence from "./SourceCubeEvidence";
import { historyClaimEvidence } from "./historyQuestionScope.mjs";
import TerminologyDetails, {type TermMapping} from './TerminologyDetails';

export type HistoryAnswer = Omit<Answer, "scope" | "comparison"> & {
  scope: HistoryView["scope"];
  history_evidence: HistoryView;
  clarification?: {
    kind: "blood_pressure_component" | "record_investigation" | "medical_term" | "history_followup";
    question: string;
    choices: { label: string; message: string }[];
  };
  terminology?: TermMapping[];
  continuation?: {token: string; subject: string; before_date: string; suggested_question: string};
  followup?: {subject: string; before_date: string};
  history_comparison?: {
    before: HistoryView["scope"];
    after: HistoryView["scope"];
  } | null;
};

export function ScopeText({ scope }: { scope: HistoryView["scope"] }) {
  return <>{scope.as_of ? `Records through ${dateLabel(scope.as_of)}` : "All recorded dates"}
    {" · "}Files available through {timeLabel(scope.known_at)}</>;
}

export default function HistoryAnswerView({ answer, pending, onClarify, onRefreshAnswer }: {
  answer: HistoryAnswer;
  pending: boolean;
  onClarify: (message: string) => void;
  onRefreshAnswer?: () => void;
}) {
  const [selection, setSelection] = useState<{ answer: HistoryAnswer; claim: Claim } | null>(null);
  // A new answer must never reopen an older answer's source or time bounds.
  const inspected = selection?.answer === answer ? selection.claim : null;
  const evidence = inspected ? historyClaimEvidence(answer.history_evidence, inspected.evidence_ids) : [];
  return <div className="history-question-answer" aria-label="History answer">
    <div className="history-answer-heading">
      <h3>{answer.clarification ? "One detail before I look" : "From your history"}</h3>
      <span>{answer.mode === "meta" ? "Muse · record findings"
        : answer.mode === "offline" ? "Offline · no model called" : "No model called"}</span>
    </div>
    <p className="history-answer-scope"><ScopeText scope={answer.scope} /></p>
    {answer.followup && <p>Following your question: {answer.followup.subject}</p>}
    {answer.history_comparison && <p className="history-answer-scope">Compared with files available through {timeLabel(answer.history_comparison.before.known_at)}.</p>}
    {answer.claims.length ? answer.claims.map((claim, index) => <article className="history-answer-claim" key={claim.id}>
      <p>{claim.text}</p>
      {!!historyClaimEvidence(answer.history_evidence, claim.evidence_ids).length && <button
        type="button" className="history-citation" aria-label={`Open evidence for finding ${index + 1}`}
        onClick={() => setSelection({ answer, claim })}>Source {index + 1}</button>}
    </article>) : <p className="history-answer-message">{answer.answer || "I could not find a supported answer in these records."}</p>}
    {answer.clarification && <div className="history-question-suggestions" aria-label={answer.clarification.kind === "blood_pressure_component" ? "Choose a blood pressure number" : "Clarify your record question"}>
      {answer.clarification.choices.map(choice => <button key={choice.message} type="button" className="secondary"
        disabled={pending} onClick={() => onClarify(choice.message)}>{choice.label}</button>)}
    </div>}
    <TerminologyDetails mappings={answer.terminology} />
    <details className="history-answer-trace">
      <summary>How this answer was made</summary>
      {answer.trace.map((step, index) => <details key={`${step.name}-${index}`}>
        <summary>{step.name} · {step.status} · {step.duration_ms.toFixed(0)} ms</summary>
        <pre>{JSON.stringify({ executor: step.executor, arguments: step.arguments, result: step.result }, null, 2)}</pre>
      </details>)}
      <pre>{JSON.stringify({ execution: answer.execution, telemetry: answer.telemetry }, null, 2)}</pre>
    </details>
    {inspected && evidence.length > 0 && <Modal title="Your source records" onClose={() => setSelection(null)} wide>
      <p className="history-answer-scope"><ScopeText scope={answer.scope} /></p>
      <p className="history-evidence-intro">{inspected.text}</p>
      <div className="history-answer-evidence">{evidence.map(({ source, facts }) => <SourceCubeEvidence
        key={source.id} source={source} facts={facts} view={answer.history_evidence} initialFactId={facts[0]?.id} onRefreshAnswer={onRefreshAnswer} />)}</div>
    </Modal>}
  </div>;
}
