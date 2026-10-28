import { useState } from "react";
import { api } from "./api";

export default function TimelineSettings({
  dateOfBirth,
  onLatest,
}: {
  dateOfBirth: string | null;
  onLatest: () => void;
}) {
  const [value, setValue] = useState(dateOfBirth || "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function save() {
    if (busy) return;
    setBusy(true);
    setMessage("");
    setError("");
    try {
      await api("/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date_of_birth: value || null }),
      });
      setMessage(
        "Birth date saved. Your selected history dates are still in place.",
      );
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="timeline-settings">
      <summary>Timeline settings</summary>
      <p>
        Use your birth date to show your age on dated records. It stays on this
        computer.
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <label className="field">
          Birth date
          <input
            type="date"
            value={value}
            max={new Date().toISOString().slice(0, 10)}
            disabled={busy}
            onChange={(event) => setValue(event.target.value)}
          />
        </label>
        <button className="secondary" disabled={busy}>
          {busy ? "Saving…" : "Save birth date"}
        </button>
        <button
          className="text-button"
          type="button"
          disabled={busy || !value}
          onClick={() => {
            setValue("");
            setMessage("");
          }}
        >
          Clear field
        </button>
      </form>
      {error && (
        <p role="alert" className="error-banner">
          {error}
        </p>
      )}
      {message && (
        <div className="timeline-profile-saved" role="status">
          <p>{message}</p>
          <button className="text-button" onClick={onLatest}>
            Use latest files and profile
          </button>
        </div>
      )}
    </details>
  );
}
