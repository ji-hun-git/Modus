import type { RecordBriefData } from './briefTypes';
import type { ReportComparisonSummary } from './reportComparisonTypes';

export type ReportBriefData = RecordBriefData & {
  comparison: Omit<ReportComparisonSummary,'history_evidence'>;
};

export function reportBriefRequest(summary:ReportComparisonSummary) {
  return {snapshot_id:summary.snapshot_id, selected_source_id:summary.current_source.id,
    comparison_source_id:summary.previous_source.id, title:'My checkup comparison', owner_note:''};
}

export function reportBriefMatches(brief:ReportBriefData, summary:ReportComparisonSummary) {
  try {
    const original=[...summary.history_evidence.facts,...summary.history_evidence.undated_facts];
    const selected=brief.entries.filter(row=>row.selected_by_owner);
    const entries=new Map(brief.entries.map(row=>[row.id,row]));
    const evidence=[...brief.history_evidence.facts,...brief.history_evidence.undated_facts];
    const comparison=brief.comparison;
    return brief.format==='modus-record-brief-v1' && /^sha256:[0-9a-f]{64}$/.test(brief.preview_id) &&
      brief.title==='My checkup comparison' && brief.owner_note==='' &&
      [brief.scope,brief.history_evidence.scope,comparison.scope].every(scope=>
        scope.as_of===summary.scope.as_of && scope.known_at===summary.scope.known_at && scope.scope_id===summary.scope.scope_id) &&
      comparison.snapshot_id===summary.snapshot_id && comparison.policy_version===summary.policy_version &&
      comparison.current_source.id===summary.current_source.id && comparison.previous_source.id===summary.previous_source.id &&
      ['rows','claims','counts','limitations'].every(key=>JSON.stringify(comparison[key as keyof typeof comparison])===JSON.stringify(summary[key as keyof typeof summary])) &&
      brief.entries.length<=120 && entries.size===brief.entries.length && selected.length===original.length &&
      brief.counts.selected===selected.length && brief.counts.total===brief.entries.length &&
      brief.counts.conflict_companions===brief.entries.length-selected.length &&
      original.every(fact=>{
        const entry=entries.get(fact.id);
        return entry?.selected_by_owner && !entry.added_for_conflict &&
          Object.keys(fact).every(key=>JSON.stringify(entry[key as keyof typeof entry])===JSON.stringify(fact[key as keyof typeof fact]));
      }) &&
      evidence.length===brief.entries.length && new Set(evidence.map(row=>row.id)).size===entries.size &&
      evidence.every(row=>entries.has(row.id)) &&
      brief.entries.every(row=>row.value!==null && !row.value_withheld && row.within_date_scope!==false &&
        (row.selected_by_owner || (row.added_for_conflict && brief.conflicts.some(group=>group.fact_ids.includes(row.id))))) &&
      Array.isArray(brief.warnings);
  } catch { return false; }
}
