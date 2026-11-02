import type { HistoryFact } from './historyTypes';
import type { ReportClaim, ReportComparisonRow, ReportComparisonSummary } from './reportComparisonTypes';
import { friendlyRecordName } from './HomeReportReadings';
import { recordedDate } from './sourceDisplay';
import LabContext from './LabContext';

const statusLabel: Record<ReportComparisonRow['status'],string> = {
  comparable:'Recorded difference available', not_comparable:'Comparison needs context',
  only_selected:'Only in the selected report', only_comparison:'Only in the comparison report',
};
const verificationLabel = {
  CONTRADICTED:'The proposed comparison conflicts with its evidence.',
  INSUFFICIENT_EVIDENCE:'There is not enough evidence to state this comparison.',
  OUT_OF_SCOPE:'The proposed comparison is outside this history view.',
};
function withheldLabel(claim:ReportClaim) {
  if (claim.type==='record') {
    if (claim.verification.reason_codes.includes('SOURCE_EXCERPT_UNAVAILABLE'))
      return 'The original excerpt is unavailable for this saved record.';
    return 'The saved-record statement could not be verified against its source evidence.';
  }
  return claim.verification.status==='SUPPORTED' ? '' : verificationLabel[claim.verification.status];
}

export default function ReportComparisonRows({summary, rows, onInspect}: {
  summary:ReportComparisonSummary; rows:ReportComparisonRow[]; onInspect:(fact:HistoryFact)=>void;
}) {
  const facts = new Map([...summary.history_evidence.facts,...summary.history_evidence.undated_facts].map(f=>[f.id,f]));
  const claims = new Map(summary.claims.map(claim=>[claim.id,claim]));
  return <div className="report-comparison-rows">{rows.map(row=>{
    const rowClaims = row.claim_ids.map(id=>claims.get(id)).filter(claim=>claim!==undefined);
    const recordClaims = rowClaims.filter(claim=>claim.type==='record' && claim.verification.status==='SUPPORTED');
    const withheldMessages = [...new Set(rowClaims.filter(claim=>claim.verification.status!=='SUPPORTED').map(withheldLabel))];
    const reasons = [...new Set([...row.reason_codes,...rowClaims.flatMap(claim=>claim.verification.reason_codes)])];
    const notes = row.notes.filter(note=>!(row.reason_codes.includes('NO_MATCH_IN_OTHER_REPORT') &&
      note==='No matching reviewed item in the other selected report. This does not establish that a test or care was missed.'));
    return <article key={row.id} className="report-comparison-row">
      <header><h3>{friendlyRecordName(row.label)}</h3><span>{statusLabel[row.status]}</span></header>
      <div className="report-comparison-values">{[
        {label:'Selected report',ids:row.current_ids}, {label:'Comparison report',ids:row.previous_ids},
      ].map(side=><section key={side.label} aria-label={`${row.label}: ${side.label}`}>
        <h4>{side.label}</h4>
        {!side.ids.length && <p className="report-comparison-missing">No matching entry in this report.</p>}
        {side.ids.map(id=>{
          const fact=facts.get(id);
          if (!fact) return <p key={id}>Source evidence is unavailable for this entry.</p>;
          return <div key={id} className="report-comparison-fact">
            <p className="report-comparison-value">{fact.value_withheld?'Hidden by date filter':fact.value ?? 'Not recorded'}
              {!fact.value_withheld && fact.unit && <span> {fact.unit}</span>}</p>
            <p>{recordedDate(fact)}</p>
            <button type="button" className="text-button" onClick={()=>onInspect(fact)}
              aria-label={`Original evidence: ${fact.label}, ${recordedDate(fact)}, ${side.label}, record ${fact.id}`}>
              Original evidence
            </button>
            {fact.kind==='measurement' && !fact.value_withheld &&
              [fact.reference_range,fact.specimen,fact.test_method].some(value=>!!value?.trim()) && <details className="report-comparison-lab">
              <summary>Range, specimen &amp; method</summary><LabContext fact={fact} />
            </details>}
          </div>;
        })}
      </section>)}</div>
      {rowClaims.filter(claim=>claim.type==='difference' && claim.verification.status==='SUPPORTED')
        .map(claim=><p key={claim.id} className="report-comparison-supported">{claim.text}</p>)}
      {withheldMessages.map(message=><p key={message} className="report-comparison-withheld">{message}</p>)}
      {!!notes.length && <ul className="report-comparison-notes">{notes.map((note,index)=><li key={index}>{note}</li>)}</ul>}
      {(!!recordClaims.length || !!reasons.length) && <details className="report-comparison-reasons"><summary>Source checks</summary>
        {recordClaims.map(claim=><p key={claim.id}>{claim.text}</p>)}
        {!!reasons.length && <p>{reasons.join(', ')}</p>}
      </details>}
    </article>;
  })}</div>;
}
