import type { FactKind, HistoryView, PagedSource } from './historyTypes';

export type ReportClaim = {
  id: string;
  type: 'record' | 'difference';
  text: string;
  difference?: string | null;
  evidence_ids: string[];
  verification: {
    status: 'SUPPORTED' | 'CONTRADICTED' | 'INSUFFICIENT_EVIDENCE' | 'OUT_OF_SCOPE';
    reason_codes: string[];
  };
};
export type ReportComparisonRow = {
  id: string; label: string; kind: FactKind;
  current_ids: string[]; previous_ids: string[];
  status: 'comparable' | 'not_comparable' | 'only_selected' | 'only_comparison';
  reason_codes: string[]; notes: string[];
  difference: string | null; unit: string | null; claim_ids: string[];
};
export type ReportComparisonSummary = {
  format: 'modus-report-summary-v1'; snapshot_id: string;
  scope: HistoryView['scope']; policy_version: string;
  current_source: PagedSource; previous_source: PagedSource;
  rows: ReportComparisonRow[]; claims: ReportClaim[];
  history_evidence: HistoryView;
  counts: { rows: number; comparable: number; not_comparable: number;
    only_selected: number; only_comparison: number; records: number };
  limitations: string[];
};

export function reportIdentity(source: PagedSource) {
  const dates = source.first_date || source.latest_date || source.date || 'Dates not fully recorded';
  const through = source.latest_date && source.latest_date !== source.first_date && source.first_date
    ? ` – ${source.latest_date}` : '';
  return `${dates}${through} · ${source.id.slice(-8)}`;
}

export function matchesReportSummary(result: ReportComparisonSummary, snapshotId:string,
  scope:HistoryView['scope'], selectedId:string, previousId:string) {
  try {
    const evidence=result.history_evidence;
    const facts=[...evidence.facts,...evidence.undated_facts];
    const ids=new Set(facts.map(fact=>fact.id));
    const factMap=new Map(facts.map(fact=>[fact.id,fact]));
    const claims=new Map(result.claims.map(claim=>[claim.id,claim]));
    const statuses=['SUPPORTED','CONTRADICTED','INSUFFICIENT_EVIDENCE','OUT_OF_SCOPE'];
    const rowStatuses=['comparable','not_comparable','only_selected','only_comparison'] as const;
    const scopes=[scope,result.scope,evidence.scope];
    const coveredIds=result.rows.flatMap(row=>[...row.current_ids,...row.previous_ids]);
    return selectedId!==previousId && result.format==='modus-report-summary-v1' && result.snapshot_id===snapshotId &&
      result.current_source.id===selectedId && result.previous_source.id===previousId &&
      scopes.every(s=>s.as_of===scope.as_of && s.known_at===scope.known_at && s.scope_id===scope.scope_id) &&
      Array.isArray(result.rows) && result.rows.length<=120 && facts.length<=120 && ids.size===facts.length &&
      result.counts.rows===result.rows.length && result.counts.records===facts.length &&
      new Set(result.rows.map(row=>row.id)).size===result.rows.length && claims.size===result.claims.length &&
      coveredIds.length===facts.length && new Set(coveredIds).size===facts.length &&
      rowStatuses.every(status=>result.counts[status]===result.rows.filter(row=>row.status===status).length) &&
      facts.every(fact=>[selectedId,previousId].includes(fact.source_id) && !fact.value_withheld && fact.within_date_scope!==false) &&
      result.claims.every(claim=>statuses.includes(claim.verification.status) &&
        ['record','difference'].includes(claim.type) && typeof claim.text==='string' &&
        (claim.verification.status!=='SUPPORTED' || (claim.evidence_ids.length>0 && claim.evidence_ids.every(id=>ids.has(id))))) &&
      result.rows.every(row=>rowStatuses.includes(row.status) &&
        row.current_ids.every(id=>factMap.get(id)?.source_id===selectedId) &&
        row.previous_ids.every(id=>factMap.get(id)?.source_id===previousId) &&
        row.claim_ids.every(id=>{
          const claim=claims.get(id);
          if (!claim) return false;
          if (claim.verification.status!=='SUPPORTED') return true;
          if (claim.type==='record') return claim.evidence_ids.length===1 && [...row.current_ids,...row.previous_ids].includes(claim.evidence_ids[0]);
          return row.difference!==null && claim.difference===row.difference && claim.evidence_ids.length===2 &&
            row.current_ids.length===1 && row.previous_ids.length===1 &&
            claim.evidence_ids[0]===row.current_ids[0] && claim.evidence_ids[1]===row.previous_ids[0];
        }) && Array.isArray(row.notes) && Array.isArray(row.reason_codes) &&
        (row.difference===null ? row.status!=='comparable' : row.status==='comparable' &&
          row.current_ids.length===1 && row.previous_ids.length===1 && row.claim_ids.some(id=>{
            const claim=claims.get(id)!;
            return claim.type==='difference' && claim.verification.status==='SUPPORTED' && claim.difference===row.difference &&
              claim.evidence_ids.length===2 && claim.evidence_ids[0]===row.current_ids[0] && claim.evidence_ids[1]===row.previous_ids[0];
          }))) &&
      Array.isArray(result.limitations);
  } catch { return false; }
}
