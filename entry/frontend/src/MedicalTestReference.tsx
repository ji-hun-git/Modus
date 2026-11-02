import names from './recordNames.json';
import type { HistoryFact } from './historyTypes';
import { referenceUrl } from './TerminologyDetails';

const expandedNames:Record<string,string>={
  hba1c:'Hemoglobin A1c (HbA1c)',
  egfr:'Estimated glomerular filtration rate (eGFR)',
  ldl:'Low-density lipoprotein cholesterol (LDL)',
  hdl:'High-density lipoprotein cholesterol (HDL)',
};

// Exact names only: a mention in a visit, diagnosis or qualified assay is not
// enough to assign the meaning of a measurement.
export default function MedicalTestReference({fact}:{fact:HistoryFact}) {
  if (fact.kind !== 'measurement') return null;
  const key = (names.concept_by_alias as Record<string,string>)[fact.label.trim().toLowerCase()];
  const term = names.concepts.find(item=>item.concept_id===key);
  if (!term) return null;
  const url = referenceUrl(term.reference.url);
  return <details className="medical-test-reference">
    <summary>Medical name &amp; reference</summary>
    <dl><div><dt>In your report</dt><dd>{fact.label}</dd></div>
      <div><dt>Medical name</dt><dd>{expandedNames[term.concept_id] || term.medical_name}</dd></div></dl>
    <p>Learn about the test. Your result and its original evidence are shown separately.</p>
    {url && <a href={url} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">
      {term.reference.publisher}: {term.reference.title}</a>}
  </details>;
}
