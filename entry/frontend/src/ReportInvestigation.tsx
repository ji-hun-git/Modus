import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { api } from './api';
import HistoryAnswerView, { type HistoryAnswer } from './HistoryAnswerView';
import type { ReportComparisonSummary } from './reportComparisonTypes';
import { historyAnswerMatches } from './historyQuestionScope.mjs';
import { correctionSession } from './correctionSession';

export function reportInvestigationMatches(answer: HistoryAnswer, summary: ReportComparisonSummary) {
  const pair = answer.report_investigation;
  return historyAnswerMatches(answer, summary.scope) &&
    answer.scope.scope_id === summary.scope.scope_id &&
    answer.history_evidence.scope.scope_id === summary.scope.scope_id &&
    pair?.snapshot_id === summary.snapshot_id &&
    pair.selected_source_id === summary.current_source.id &&
    pair.comparison_source_id === summary.previous_source.id;
}

export default function ReportInvestigation({summary, onRefresh}: {
  summary: ReportComparisonSummary; onRefresh: () => void;
}) {
  const [answer, setAnswer] = useState<HistoryAnswer | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [invalidated, setInvalidated] = useState(false);
  const [initialCorrections] = useState(() => new Map(correctionSession.getSnapshot().map(([id, state]) => [id, state.savedAt])));
  const corrections = useSyncExternalStore(correctionSession.subscribe, correctionSession.getSnapshot, correctionSession.getSnapshot);
  const ids = new Set(answer ? [...answer.history_evidence.facts, ...answer.history_evidence.undated_facts].map(row => row.id) : []);
  const stale = invalidated || corrections.some(([id, state]) => ids.has(id) && state.savedAt && state.savedAt !== initialCorrections.get(id));
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => { if (stale) { setInvalidated(true); controller.current?.abort(); } }, [stale]);

  async function investigate() {
    if (pending) return;
    const active = new AbortController();
    controller.current?.abort(); controller.current = active;
    setPending(true); setError(''); setAnswer(null);
    try {
      const result = await api<HistoryAnswer>('/history/report-investigation', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, signal: active.signal,
        body: JSON.stringify({snapshot_id: summary.snapshot_id,
          selected_source_id: summary.current_source.id, comparison_source_id: summary.previous_source.id}),
      });
      if (active.signal.aborted) return;
      if (!reportInvestigationMatches(result, summary))
        throw new Error('The answer does not match these reports and dates. Close and reopen the comparison.');
      setAnswer(result);
    } catch (cause) {
      if (!active.signal.aborted) setError((cause as Error).message || 'The investigation could not be completed.');
    } finally {
      if (!active.signal.aborted) setPending(false);
    }
  }

  if (stale) return <section className="report-investigation" role="status">
    <p>A source in this explanation was corrected. Open updated history to investigate the revised records.</p>
    <button type="button" className="secondary" onClick={onRefresh}>Open updated history</button>
  </section>;

  return <section className="report-investigation" aria-label="Investigate selected reports">
    {!answer && <>
      <button type="button" className="secondary" disabled={pending} onClick={() => void investigate()}>
        {pending ? 'Checking the reports…' : 'Explain changes and discrepancies'}
      </button>
      <p>Check recorded changes, context and related copies. Your records stay unchanged.</p>
    </>}
    {pending && <p role="status">Inspecting the selected reports and their source evidence…</p>}
    {error && <p role="alert">{error}</p>}
    {answer && <>
      <HistoryAnswerView answer={answer} pending={pending} onClarify={() => void investigate()} onRefreshAnswer={onRefresh} />
      <button type="button" className="text-button" onClick={() => setAnswer(null)}>Close explanation</button>
    </>}
  </section>;
}
