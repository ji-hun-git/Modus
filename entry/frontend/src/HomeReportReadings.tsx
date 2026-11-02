import type { HistoryFact } from './historyTypes';
import { factKindLabels } from './historyTypes';
import names from './recordNames.json';
import { recordedDate } from './sourceDisplay';
import { unitLabel } from './recordPresentation.mjs';

export function friendlyRecordName(label: string) {
  return (names.aliases as Record<string,string>)[label.trim().toLowerCase()] || label;
}

export function groupReportFacts(facts:HistoryFact[]) {
  const groups: {name:string;facts:HistoryFact[]}[]=[];
  const knownGroups:Record<string,string>={hba1c:'Blood sugar',glucose:'Blood sugar',fasting_glucose:'Blood sugar',
    ldl:'Cholesterol and triglycerides',hdl:'Cholesterol and triglycerides',total_cholesterol:'Cholesterol and triglycerides',triglycerides:'Cholesterol and triglycerides',
    egfr:'Kidney tests',creatinine:'Kidney tests',bun:'Kidney tests'};
  for (const fact of facts) {
    const concept=(names.concept_by_alias as Record<string,string>)[fact.label.trim().toLowerCase()];
    const name=fact.kind==='measurement' ? knownGroups[concept] || 'Other measurements' : factKindLabels[fact.kind];
    let group=groups.find(item=>item.name===name);
    if (!group) { group={name,facts:[]};groups.push(group); }
    group.facts.push(fact);
  }
  const order=['Blood sugar','Cholesterol and triglycerides','Kidney tests','Other measurements'];
  return groups.sort((a,b)=>(order.includes(a.name)?order.indexOf(a.name):4)-(order.includes(b.name)?order.indexOf(b.name):4));
}

export function readingChoices(facts: HistoryFact[], selectedId?: string) {
  const ordered = [...facts].sort((a,b) => (b.date || '').localeCompare(a.date || '') || a.label.localeCompare(b.label) || a.id.localeCompare(b.id));
  const first = ordered.slice(0,4);
  const selected = ordered.find(f => f.id === selectedId);
  return selected && !first.some(f => f.id === selected.id) ? [...first.slice(0,3),selected] : first;
}

export default function HomeReportReadings({facts,selected,onSelect}: {
  facts: HistoryFact[]; selected?: HistoryFact; onSelect: (fact: HistoryFact) => void;
}) {
  return <div className="report-reading-choices" aria-label="Readings in this report">
    {readingChoices(facts,selected?.id).map(fact => <button key={fact.id} type="button"
      className="report-reading-choice" aria-pressed={fact.id === selected?.id} onClick={() => onSelect(fact)}>
      <span className="report-reading-name">{friendlyRecordName(fact.label)}</span>
      <span className="report-reading-number">{fact.value_withheld ? 'Hidden by date filter' : fact.value ?? 'Not recorded'}</span>
      {!fact.value_withheld && (fact.unit || fact.kind==='measurement') && <span className="report-reading-unit">{unitLabel(fact.unit) || 'Unit not recorded'}</span>}
      <span className="report-reading-date">{recordedDate(fact)}</span>
    </button>)}
  </div>;
}
