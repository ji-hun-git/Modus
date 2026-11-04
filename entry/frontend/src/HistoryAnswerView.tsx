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
  report_investigation?: {
    method: string; selected_source_id: string; comparison_source_id: string;
    selected_title: string; comparison_title: string; snapshot_id: string | null;
    counts: Record<string, number>; policy_version: string;
  };
  clarification?: {
    kind: "blood_pressure_component" | "record_investigation" | "medical_term" | "history_followup" | "history_query";
    question: string;
    choices: { label: string; message: string }[];
  };
  terminology?: TermMapping[];
  continuation?: {token: string; subject: string; before_date: string|null; suggested_question: string; supported_questions?:string[]};
  followup?: {subject: string; before_date: string};
  query_result?: {status:"answered"|"no_match"|"insufficient_evidence"|"clarification"|"unsupported"|"not_understood"|"planner_unavailable"};
  history_comparison?: {
    before: HistoryView["scope"];
    after: HistoryView["scope"];
  } | null;
};

function answerHeading(answer:HistoryAnswer) {
  if (answer.report_investigation && answer.claims.length) return 'What changed between these reports';
  switch(answer.query_result?.status) {
    case 'no_match': return 'No matching record found';
    case 'insufficient_evidence': return 'Not enough recorded evidence';
    case 'clarification': return 'One detail before I look';
    case 'unsupported': return 'This question is outside record search';
    case 'not_understood': return 'Help me find the right record';
    case 'planner_unavailable': return 'Record search is unavailable';
    default: return answer.clarification?'One detail before I look':'From your history';
  }
}

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
  const [expandedAnswer, setExpandedAnswer] = useState<HistoryAnswer | null>(null);
  const bounded = !!answer.report_investigation && expandedAnswer !== answer;
  const coverage = answer.report_investigation ? answer.claims.filter(claim => claim.category === 'coverage') : [];
  const primary = answer.report_investigation ? answer.claims.filter(claim => claim.category !== 'coverage') : answer.claims;
  const findings = bounded ? primary.slice(0, 6) : primary;
  // A new answer must never reopen an older answer's source or time bounds.
  const inspected = selection?.answer === answer ? selection.claim : null;
  const evidence = inspected ? historyClaimEvidence(answer.history_evidence, inspected.evidence_ids) : [];
  function renderFinding(claim: Claim) {
    const number = answer.claims.indexOf(claim) + 1;
    return <article className="history-answer-claim" key={claim.id}>
      <p>{claim.text}</p>
      {!!historyClaimEvidence(answer.history_evidence, claim.evidence_ids).length && <button
        type="button" className="history-citation" aria-label={`Open evidence for finding ${number}`}
        onClick={() => setSelection({ answer, claim })}>Source {number}</button>}
    </article>;
  }
  return <div className="history-question-answer" aria-label="History answer">
    <div className="history-answer-heading">
      <h3>{answerHeading(answer)}</h3>
      <span>{answer.mode === "meta" ? "Muse · record findings"
        : answer.mode === "offline" ? "Offline · no model called" : "No model called"}</span>
    </div>
    <p className="history-answer-scope"><ScopeText scope={answer.scope} /></p>
    {answer.followup && <p>Following your question: {answer.followup.subject}</p>}
    {answer.history_comparison && <p className="history-answer-scope">Compared with files available through {timeLabel(answer.history_comparison.before.known_at)}.</p>}
    {answer.claims.length ? findings.map(renderFinding) : <p className="history-answer-message">{answer.answer || "I could not find a supported answer in these records."}</p>}
    {!!answer.report_investigation && primary.length > 6 && <button type="button" className="text-button"
      aria-expanded={!bounded} onClick={() => setExpandedAnswer(bounded ? answer : null)}>
      {bounded ? `Show all ${primary.length} findings` : 'Show fewer findings'}
    </button>}
    {coverage.length > 0 && <details className="history-answer-trace">
      <summary>Scope and coverage</summary>
      {coverage.map(renderFinding)}
    </details>}
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
    {inspected && evidence.length > 0 && <Modal title="Original evidence" onClose={() => setSelection(null)} placement="inspector">
      <p className="history-answer-scope"><ScopeText scope={answer.scope} /></p>
      <details className="source-evidence-details"><summary>Linked finding</summary>
        <p className="history-evidence-intro">{inspected.text}</p>
      </details>
      <div className="history-answer-evidence">{evidence.map(({ source, facts }) => <SourceCubeEvidence
        key={source.id} source={source} facts={facts} view={answer.history_evidence} initialFactId={facts[0]?.id} onRefreshAnswer={onRefreshAnswer} />)}</div>
    </Modal>}
  </div>;
}
