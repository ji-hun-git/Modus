import type { DateEvidence } from "./historyTypes";

export default function RecordDateEvidence({ evidence, currentDate, reviewing = false, hidden = false }: {
  evidence?: DateEvidence | null;
  currentDate: string | null;
  reviewing?: boolean;
  hidden?: boolean;
}) {
  if (!evidence || hidden) return null;
  return (
    <details className="timeline-source" open={reviewing}>
      <summary>Date in the original · page {evidence.page}</summary>
      <blockquote>{evidence.source_quote}</blockquote>
      {reviewing && <p>Check that this date belongs to the result before saving.</p>}
      {evidence.check.status === "mismatch" && (
        <p>This date passage could not be matched. Check the original page.</p>
      )}
      {evidence.check.status === "unavailable" && (
        <p>No independent text check is available. Check the original image.</p>
      )}
      {currentDate !== evidence.value && (
        <p>The {reviewing ? "reviewed" : "saved"} date differs. This passage keeps the original date proposal: {evidence.value}.</p>
      )}
    </details>
  );
}
