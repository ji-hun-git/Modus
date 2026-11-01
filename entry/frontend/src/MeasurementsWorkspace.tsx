import { useEffect, useState } from "react";
import { AlertCircle, ArrowUpRight, LoaderCircle } from "lucide-react";
import { timeLabel } from "./ui";
import type { Scope } from "./types";
import { factKindLabels, type HistoryFact, type HistoryView } from "./historyTypes";
import { historyFields } from "./historyFields";
import { recordedDate } from "./sourceDisplay";
import { unitLabel } from "./recordPresentation.mjs";
import HomeRecordSeries from "./HomeRecordSeries";
import OverviewRecordDetails from "./OverviewRecordDetails";
import useHistoryView from "./useHistoryView";
import HistoryPager from './HistoryPager';
import PagedRecordList from './PagedRecordList';
import {RetrievalFeedback} from './TerminologyDetails';

export default function MeasurementsWorkspace({ scope, historical, onScope }: {
  scope: Scope;
  historical: boolean;
  onScope: (scope: HistoryView["scope"]) => void;
}) {
  const [kind, setKind] = useState('measurement');
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState('');
  const { view: loaded, metadata, error, refresh, setOffset } = useHistoryView(scope, !historical, { section:'fields', kind, query });
  const view = loaded || metadata;
  useEffect(() => { if (view) onScope(view.scope); }, [view, onScope]);
  if (error) return <section className="panel empty" role="alert"><AlertCircle size={24} />
    <h2>This history could not be loaded</h2><p>{error}</p>
    <button className="secondary" onClick={refresh}>Retry this view</button></section>;
  if (!view) return <section className="panel loading" role="status"><LoaderCircle className="spin" size={24} /> Loading your history…</section>;
  const field = view.fields?.find(f => f.label === selected) || view.fields?.[0];
  return <section className="measurements-workspace" aria-label="Recorded history trends">
    <div className="history-field-controls">
      <label>Record type<select aria-label="Trends record type" value={kind} onChange={e => {setKind(e.target.value);setSelected('');}}>
        {Object.entries(factKindLabels).map(([key,name]) => <option key={key} value={key}>{name}</option>)}</select></label>
      <label>Find a recorded field<input aria-label="Find a recorded field" value={query} onChange={e => {setQuery(e.target.value);setSelected('');}} /></label>
      <label>Recorded field<select aria-label="Trends recorded field" value={field?.label || ''} onChange={e => setSelected(e.target.value)}>
        {!view.fields?.length && <option value="">{loaded ? 'No matching fields' : 'Loading fields…'}</option>}
        {view.fields?.map(f => <option key={f.label} value={f.label}>{f.label} · {f.count} records</option>)}</select></label>
    </div>
    <HistoryPager view={view} onPage={setOffset} noun="fields" />
    <RetrievalFeedback retrieval={loaded?.retrieval} onChoose={setQuery} />
    {field && <><h2>{field.label}</h2><PagedRecordList key={`${view.scope.scope_id}|${field.kind}|${field.label}`} parent={view}
      filters={{kind:field.kind,label:field.label}} chart={field.kind === 'measurement'} /></>}
  </section>;
}

export function HistoryTrends({ view }: { view: HistoryView }) {
  const groups = historyFields(view);
  const kinds = [...new Set(groups.map((group) => group.kind))];
  const [requestedKind, setKind] = useState("measurement");
  const kind = kinds.find((item) => item === requestedKind) || kinds[0];
  const choices = groups.filter((group) => group.kind === kind);
  const [fieldKey, setFieldKey] = useState("");
  const field = choices.find((group) => group.key === fieldKey) || choices[0];
  const [inspected, setInspected] = useState<HistoryFact | null>(null);
  const [selection, setSelection] = useState<{ title: string; facts: HistoryFact[] } | null>(null);
  const sourceIds = new Set(view.sources.map((source) => source.id));
  const disputedIds = new Set(view.conflicts.flatMap((group) => group.fact_ids));
  const records = field?.facts || [];
  return <section className="measurements-workspace" aria-label="Recorded history trends">
    <div className="history-field-controls">
      <label>Record type<select aria-label="Trends record type" value={kind || ""} disabled={!kinds.length}
        onChange={(event) => { setKind(event.target.value); setFieldKey(""); }}>
        {!kinds.length && <option value="">No records in this view</option>}
        {kinds.map((item) => <option key={item} value={item}>{factKindLabels[item]}</option>)}
      </select></label>
      <label>Recorded field<select aria-label="Trends recorded field" value={field?.key || ""} disabled={!choices.length}
        onChange={(event) => setFieldKey(event.target.value)}>
        {!choices.length && <option value="">No fields in this view</option>}
        {choices.map((item) => <option key={item.key} value={item.key}>{item.label} · {item.facts.length} {item.facts.length === 1 ? 'record' : 'records'}</option>)}
      </select></label>
    </div>
    <div className="measurement-history-heading"><div><h2>{field?.label || "Your history"}</h2>
      <p>{kind === 'measurement' ? 'Recorded values. Each unit stays separate.' : 'Recorded wording, in date order.'}</p></div>
      <span>{records.length} recorded {records.length === 1 ? 'item' : 'items'}</span>
    </div>
    {field?.kind === 'measurement' && <HomeRecordSeries facts={records} label={field.label} sourceIds={sourceIds}
      disputedIds={disputedIds} onSelect={(facts) => setSelection({ title: field.label, facts })} />}
    {!records.length && <p className="empty">No recorded fields are available in this view.</p>}
    <div className="measurement-history">
      {records.map((fact) => {
        const source = view.sources.find((item) => item.id === fact.source_id)!;
        return <article className="measurement-history-row history-field-row" key={fact.id}>
          <div className="history-reading"><time dateTime={fact.date || undefined}>{recordedDate(fact)}</time>
            <strong>{fact.value_withheld ? 'Hidden by date filter' : fact.value ?? 'Not recorded'}</strong>
            {!fact.value_withheld && fact.unit && <span>{unitLabel(fact.unit)}</span>}
            {disputedIds.has(fact.id) && <small><AlertCircle size={12} /> Recorded disagreement</small>}
          </div>
          <div className="history-source"><strong>{source.title}</strong>
            <span>Available in Modus {timeLabel(fact.available_at)}</span></div>
          <button className="text-button" aria-label={`Inspect ${fact.label}, ${recordedDate(fact)}, ${source.title}`}
            onClick={() => setInspected(fact)}>View source <ArrowUpRight size={14} /></button>
        </article>;
      })}
    </div>
    {records.some((fact) => disputedIds.has(fact.id)) && <p className="measurement-history-note">Conflicting values are preserved separately. No result is chosen.</p>}
    <OverviewRecordDetails view={view} selection={selection} inspected={inspected} onInspect={setInspected}
      onCloseSource={() => setInspected(null)} onCloseSelection={() => setSelection(null)} />
  </section>;
}
