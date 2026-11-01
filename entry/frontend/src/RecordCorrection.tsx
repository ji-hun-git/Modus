import { useState, useSyncExternalStore } from "react";
import { api, post } from "./api";
import { factKindLabels, type HistoryFact, type HistoryView, type ReviewedFact } from "./historyTypes";
import { timeLabel } from "./ui";

import { correctionSession, type Revision, type Preview } from "./correctionSession";
const fields = ["label", "value", "unit", "occurred_on", "facility"] as const;
const names = { label: "Recorded name", value: "Value or wording", unit: "Unit", occurred_on: "Recorded date", facility: "Place" };

export default function RecordCorrection({ fact, scope, onRefreshAnswer }: { fact: HistoryFact; scope: HistoryView["scope"]; onRefreshAnswer?: () => void }) {
  useSyncExternalStore(correctionSession.subscribe, correctionSession.getSnapshot, correctionSession.getSnapshot);
  const { versions, request, preview, pending, busy, error, confirmed, savedAt, originScope, versionsScope } = correctionSession.get(fact.id);
  const patch = (update: Parameters<typeof correctionSession.patch>[1]) => correctionSession.patch(fact.id, update);
  const [resumeLatest, setResumeLatest] = useState(false);

  async function load(edit: boolean) {
    if (correctionSession.get(fact.id).busy || correctionSession.get(fact.id).pending) return;
    patch({ busy: true, error: "" });
    try {
      const query = new URLSearchParams();
      if (!edit) {
        query.set("known_at", scope.known_at);
        if (scope.as_of) query.set("as_of", scope.as_of);
      }
      const result = await api<{ versions: Revision[] }>(`/history/facts/${encodeURIComponent(fact.id)}/revisions?${query}`);
      patch({ versions: result.versions, versionsScope: scope.scope_id });
      if (edit) {
        const current = result.versions.at(-1)?.fact;
        if (!current || current.value === null) throw new Error("The latest saved record is unavailable.");
        patch({ request: { expected_revision_id: current.revision_id || current.id, reason: "",
          corrected: { id: current.id, kind: current.kind, label: current.label, value: current.value,
            unit: current.unit, occurred_on: current.occurred_on, facility: current.facility } },
          originScope: scope.scope_id, preview: null, confirmed: false, savedAt: null, acknowledged: true, rejected: false });
      }
    } catch (err) { patch({ error: (err as Error).message }); }
    finally { patch({ busy: false }); }
  }

  async function review() {
    if (!request || correctionSession.get(fact.id).busy || correctionSession.get(fact.id).pending) return;
    patch({ busy: true, error: "" });
    try { patch({ preview: await post<Preview>("/history/amendments/preview", request), confirmed: false }); }
    catch (err) { patch({ error: (err as Error).message }); }
    finally { patch({ busy: false }); }
  }

  async function save() {
    await correctionSession.save(fact.id, body => post("/history/amendments/commit", body));
  }

  // A resumed current-version edit must not silently expose its values in a
  // newly selected historical scope. The recovery notice can check its receipt.
  if (request && originScope !== scope.scope_id && !resumeLatest) return <section className="record-correction" aria-label="Saved record corrections">
    <p>You have an unfinished correction to the latest saved version.</p>
    <button className="secondary" onClick={() => setResumeLatest(true)}>Continue latest correction</button>
  </section>;

  return <section className="record-correction" aria-label="Saved record corrections">
    {savedAt && <div role="status">
      <strong>Correction saved</strong>
      <p>Available in Modus from {timeLabel(savedAt)}. Your original and earlier history are preserved.</p>
      {onRefreshAnswer ? <button className="secondary" onClick={onRefreshAnswer}>Ask original question with updated records</button>
        : <button className="secondary" onClick={() => window.dispatchEvent(new Event("modus:show-current-history"))}>Open updated history</button>}
    </div>}
    <>
      {!request && <div className="import-queue-actions">
        <button className="secondary" disabled={busy} onClick={() => void load(true)}>Correct saved record</button>
        <button className="text-button" disabled={busy} onClick={() => void load(false)}>View saved versions</button>
      </div>}
      {request && <>
        <h4>Correct your saved record</h4>
        <p>You are editing the latest saved version. This creates a new revision; the original file and your earlier view stay intact.</p>
        <blockquote>{versions?.at(-1)?.fact.source_quote || "No original excerpt available."}</blockquote>
        {!preview && !pending ? <form onSubmit={event => { event.preventDefault(); void review(); }}>
          <fieldset disabled={busy}>
            <label>Record type<select value={request.corrected.kind} onChange={event => patch({ request: { ...request, corrected: { ...request.corrected, kind: event.target.value as ReviewedFact["kind"] } } })}>
              {Object.entries(factKindLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select></label>
            {fields.map(field => <label key={field}>{names[field]}
              <input value={request.corrected[field] || ""} required={field === "label" || field === "value"}
                maxLength={field === "value" ? 16000 : field === "unit" ? 80 : field === "occurred_on" ? 100 : 200}
                onChange={event => patch({ request: { ...request, corrected: { ...request.corrected, [field]: event.target.value || (field === "label" || field === "value" ? "" : null) } } })} />
            </label>)}
            <label>Reason for this correction<input required maxLength={500} value={request.reason} onChange={event => patch({ request: { ...request, reason: event.target.value } })} /></label>
            <button className="primary" type="submit">Review correction</button>
            <button className="text-button" type="button" onClick={() => patch({ request: null, versions: null, error: "" })}>Cancel</button>
          </fieldset>
        </form> : <div>
          <h4>Review the changes</h4>
          <dl>{Object.entries(preview?.changes || {}).map(([key, change]) => <div key={key}>
            <dt>{key === "kind" ? "Record type" : names[key as keyof typeof names]}</dt>
            <dd>{change.before ?? "Not recorded"} → <strong>{change.after ?? "Not recorded"}</strong></dd>
          </div>)}</dl>
          <p>Reason: {request.reason}</p>
          {!pending && <label><input type="checkbox" checked={confirmed} disabled={busy} onChange={event => patch({ confirmed: event.target.checked })} /> I reviewed this correction.</label>}
          {pending && <p role="status">The save has not been confirmed. Retry this same correction to check its result.</p>}
          <div className="import-queue-actions">
            <button className="primary" disabled={busy || (!pending && !confirmed)} onClick={() => void save()}>{pending ? "Check save result" : "Save correction"}</button>
            {!pending && <button className="text-button" disabled={busy} onClick={() => patch({ preview: null, confirmed: false })}>Edit correction</button>}
          </div>
        </div>}
      </>}
      {versions && versionsScope === scope.scope_id && !request && <ol>{versions.map(({ fact: version, reason }) => <li key={version.revision_id || version.id}>
        <strong>{version.value_withheld ? "Hidden by date filter" : version.value}{!version.value_withheld && version.unit ? ` ${version.unit}` : ""}</strong>
        <p>Recorded {version.occurred_on || "date unknown"} · Available {timeLabel(version.available_at)}</p>
        {reason && <p>Correction reason: {reason}</p>}
      </li>)}</ol>}
    </>
    {busy && <p role="status">Working…</p>}
    {error && <div role="alert"><p>{error}</p>{request && !pending && <button className="secondary" disabled={busy} onClick={() => void load(true)}>Reload latest record</button>}</div>}
  </section>;
}
