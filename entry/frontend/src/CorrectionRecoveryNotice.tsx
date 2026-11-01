import { useEffect, useSyncExternalStore } from "react";
import { post } from "./api";
import { correctionSession } from "./correctionSession";

export default function CorrectionRecoveryNotice() {
  const records = useSyncExternalStore(correctionSession.subscribe, correctionSession.getSnapshot, correctionSession.getSnapshot);
  const unfinished = records.some(([, state]) => state.pending || state.request || state.busy);
  useEffect(() => {
    if (!unfinished) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [unfinished]);
  const recoverable = records.filter(([, state]) => state.pending || ((state.savedAt || state.rejected) && !state.acknowledged));
  if (!recoverable.length) return null;
  return <section className="info-banner correction-recovery" aria-label="Correction recovery">
    {recoverable.map(([id, state], index) => <div key={id}>
      {state.pending ? <>
        <p role="status">{state.busy ? "Checking your correction…" : "Your correction has not been confirmed."}</p>
        <button className="secondary" disabled={state.busy}
          aria-label={`Check save result for correction ${index + 1}`}
          onClick={() => void correctionSession.save(id, body => post("/history/amendments/commit", body))}>Check save result</button>
        {state.error && <p role="alert">{state.error}</p>}
      </> : state.rejected ? <>
        <p role="alert">Correction was not saved. {state.error} Reopen the record to review your changes.</p>
        <button className="text-button" onClick={() => correctionSession.patch(id, { acknowledged: true })}>Dismiss correction notice</button>
      </> : <>
        <p role="status">Correction saved. Your original and earlier history are preserved.</p>
        <button className="secondary" onClick={() => {
          correctionSession.patch(id, { acknowledged: true });
          window.dispatchEvent(new Event("modus:show-current-history"));
        }}>Open updated history</button>
        <button className="text-button" onClick={() => correctionSession.patch(id, { acknowledged: true })}>Dismiss correction notice</button>
      </>}
    </div>)}
  </section>;
}
