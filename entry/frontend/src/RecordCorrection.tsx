import { useState } from "react";
import { api, ApiError, post } from "./api";
import { factKindLabels, type HistoryFact, type HistoryView, type ReviewedFact } from "./historyTypes";
import { timeLabel } from "./ui";

type Revision = { fact: HistoryFact; reason: string | null };
type Preview = { preview_id: string; changes: Record<string, { before: string | null; after: string | null }> };
type Request = { expected_revision_id: string; corrected: ReviewedFact; reason: string };
type Commit = Request & { preview_id: string; reviewed: true };
const fields = ["label", "value", "unit", "occurred_on", "facility"] as const;
const names = { label: "Recorded name", value: "Value or wording", unit: "Unit", occurred_on: "Recorded date", facility: "Place" };

export default function RecordCorrection({ fact, scope }: { fact: HistoryFact; scope: HistoryView["scope"] }) {
  const [versions, setVersions] = useState<Revision[] | null>(null);
  const [request, setRequest] = useState<Request | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [pending, setPending] = useState<Commit | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  async function load(edit: boolean) {
    setBusy(true); setError("");
    try {
      const query = new URLSearchParams();
      if (!edit) {
        query.set("known_at", scope.known_at);
        if (scope.as_of) query.set("as_of", scope.as_of);
      }
      const result = await api<{ versions: Revision[] }>(`/history/facts/${encodeURIComponent(fact.id)}/revisions?${query}`);
      setVersions(result.versions);
      if (edit) {
        const current = result.versions.at(-1)?.fact;
        if (!current || current.value === null) throw new Error("The latest saved record is unavailable.");
        setRequest({ expected_revision_id: current.revision_id || current.id, reason: "",
          corrected: { id: current.id, kind: current.kind, label: current.label, value: current.value,
            unit: current.unit, occurred_on: current.occurred_on, facility: current.facility } });
        setPreview(null); setConfirmed(false);
      }
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  async function review() {
    if (!request) return;
    setBusy(true); setError("");
    try { setPreview(await post<Preview>("/history/amendments/preview", request)); setConfirmed(false); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  async function save() {
    if (!pending && (!request || !preview || !confirmed)) return;
    const body: Commit = pending || { ...request!, preview_id: preview!.preview_id, reviewed: true };
    setPending(body); setBusy(true); setError("");
    try {
      const receipt = await post<{ available_at: string }>("/history/amendments/commit", body);
      setSavedAt(receipt.available_at); setPending(null); setRequest(null); setVersions(null);
    } catch (err) {
      if (err instanceof ApiError && err.status < 500) { setPending(null); setPreview(null); setConfirmed(false); }
      setError((err as Error).message);
    } finally { setBusy(false); }
  }

  return <section className="record-correction" aria-label="Saved record corrections">
    {savedAt ? <div role="status">
      <strong>Correction saved</strong>
      <p>Available in Modus from {timeLabel(savedAt)}. Your original and earlier history are preserved.</p>
      <button className="secondary" onClick={() => window.dispatchEvent(new Event("modus:show-current-history"))}>Open updated history</button>
    </div> : <>
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
            <label>Record type<select value={request.corrected.kind} onChange={event => setRequest({ ...request, corrected: { ...request.corrected, kind: event.target.value as ReviewedFact["kind"] } })}>
              {Object.entries(factKindLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select></label>
            {fields.map(field => <label key={field}>{names[field]}
              <input value={request.corrected[field] || ""} required={field === "label" || field === "value"}
                maxLength={field === "value" ? 16000 : field === "unit" ? 80 : field === "occurred_on" ? 100 : 200}
                onChange={event => setRequest({ ...request, corrected: { ...request.corrected, [field]: event.target.value || (field === "label" || field === "value" ? "" : null) } })} />
            </label>)}
            <label>Reason for this correction<input required maxLength={500} value={request.reason} onChange={event => setRequest({ ...request, reason: event.target.value })} /></label>
            <button className="primary" type="submit">Review correction</button>
            <button className="text-button" type="button" onClick={() => { setRequest(null); setVersions(null); }}>Cancel</button>
          </fieldset>
        </form> : <div>
          <h4>Review the changes</h4>
          <dl>{Object.entries(preview?.changes || {}).map(([key, change]) => <div key={key}>
            <dt>{key === "kind" ? "Record type" : names[key as keyof typeof names]}</dt>
            <dd>{change.before ?? "Not recorded"} → <strong>{change.after ?? "Not recorded"}</strong></dd>
          </div>)}</dl>
          <p>Reason: {request.reason}</p>
          {!pending && <label><input type="checkbox" checked={confirmed} disabled={busy} onChange={event => setConfirmed(event.target.checked)} /> I reviewed this correction.</label>}
          {pending && <p role="status">The save has not been confirmed. Retry this same correction to check its result.</p>}
          <div className="import-queue-actions">
            <button className="primary" disabled={busy || (!pending && !confirmed)} onClick={() => void save()}>{pending ? "Check save result" : "Save correction"}</button>
            {!pending && <button className="text-button" disabled={busy} onClick={() => setPreview(null)}>Edit correction</button>}
          </div>
        </div>}
      </>}
      {versions && !request && <ol>{versions.map(({ fact: version, reason }) => <li key={version.revision_id || version.id}>
        <strong>{version.value_withheld ? "Hidden by date filter" : version.value}{!version.value_withheld && version.unit ? ` ${version.unit}` : ""}</strong>
        <p>Recorded {version.occurred_on || "date unknown"} · Available {timeLabel(version.available_at)}</p>
        {reason && <p>Correction reason: {reason}</p>}
      </li>)}</ol>}
    </>}
    {busy && <p role="status">Working…</p>}
    {error && <div role="alert"><p>{error}</p>{request && !pending && <button className="secondary" disabled={busy} onClick={() => void load(true)}>Reload latest record</button>}</div>}
  </section>;
}
