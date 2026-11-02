import type { HistoryFact, FactReviewRow } from './historyTypes';
import names from './recordNames.json';

// Exact display classification only. Never discard printed metadata or infer
// that a qualified/unknown test is a vital sign from a substring or unit.
const vitalLabels = new Set(['blood pressure','bp','혈압',
  'systolic','systolic blood pressure','blood pressure systolic','systolic bp','bp systolic','sbp','수축기 혈압','수축기혈압',
  'diastolic','diastolic blood pressure','blood pressure diastolic','diastolic bp','bp diastolic','dbp','이완기 혈압','이완기혈압',
  'respiratory rate','respiration rate','body temperature','temperature','oxygen saturation','spo2',
  'height','body height','weight','body weight','bmi','body mass index']);

export const labFields = {reference_range:'Lab’s reference range',specimen:'Specimen',test_method:'Test method'};
export default function LabContext({fact}:{fact:HistoryFact}) {
  if (fact.kind!=='measurement' || fact.value_withheld) return null;
  const label = fact.label.trim().toLowerCase();
  const isVital = vitalLabels.has(label) || (names.concept_by_alias as Record<string,string>)[label] === 'pulse';
  const fields = Object.entries(labFields).filter(([key])=>
    !isVital || !!fact[key as keyof typeof labFields]?.trim());
  if (!fields.length) return null;
  return <dl className="lab-context">{fields.map(([key,label])=><div key={key}>
    <dt>{label}</dt><dd>{fact[key as keyof typeof labFields] || 'Not recorded'}</dd>
  </div>)}</dl>;
}

export function LabContextReview({row,index,disabled,onChange}:{row:FactReviewRow;index:number;disabled:boolean;
  onChange:(id:string,patch:Partial<FactReviewRow>)=>void}) {
  return <details className="lab-context-review" open={Object.keys(labFields).some(k=>!!row[k as keyof typeof labFields]) || undefined}>
    <summary>Range, specimen &amp; method</summary>
    <fieldset disabled={disabled} className="generic-fact-fields">{Object.entries(labFields).map(([key,label])=><label className="field" key={key}>
      {label}<input aria-label={`${label} ${index+1}`} maxLength={key==='reference_range'?400:200}
        value={row[key as keyof typeof labFields] || ''} placeholder="Not printed / unknown"
        onChange={event=>onChange(row.id,{[key]:event.target.value || null})} />
    </label>)}</fieldset>
  </details>;
}
