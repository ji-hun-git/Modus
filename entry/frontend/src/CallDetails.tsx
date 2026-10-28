import type { ProviderCall } from "./types";

const stages: Record<string, string> = {
  ExtractRecordedFields: "Extract fields",
  VerifyRecordedFields: "Check fields against source",
};
const numberLabel = (value: number | null | undefined, suffix = "") =>
  typeof value === "number" && Number.isFinite(value) && value >= 0
    ? `${value.toLocaleString("en-US", { maximumFractionDigits: 2 })}${suffix}`
    : "Not reported";

export default function CallDetails({ calls }: { calls: ProviderCall[] }) {
  return (
    <section aria-label="Model call details">
      <h4>Model calls</h4>
      {!calls.length && <p>No call details were recorded.</p>}
      {calls.slice(0, 8).map((call, index) => (
        <dl key={index}>
          <div>
            <dt>Call {index + 1}</dt>
            <dd>
              {stages[call.stage || ""] || call.stage || "Stage not recorded"}
            </dd>
          </div>
          <div>
            <dt>Requested model</dt>
            <dd>
              <code>{call.model || "Not reported"}</code>
            </dd>
          </div>
          <div>
            <dt>Returned model</dt>
            <dd>
              <code>{call.returned_model || "Not reported"}</code>
            </dd>
          </div>
          <div>
            <dt>Request status</dt>
            <dd>{call.status || "Not reported"}</dd>
          </div>
          <div>
            <dt>Output checks</dt>
            <dd>{call.result_validation || "Not recorded"}</dd>
          </div>
          {call.error_kind && (
            <div>
              <dt>Failure</dt>
              <dd>{call.error_kind}</dd>
            </div>
          )}
          <div>
            <dt>Request ID</dt>
            <dd>
              <code>{call.request_id || "Not reported"}</code>
            </dd>
          </div>
          <div>
            <dt>Response ID</dt>
            <dd>
              <code>{call.response_id || "Not reported"}</code>
            </dd>
          </div>
          <div>
            <dt>Latency</dt>
            <dd>
              <code>{numberLabel(call.duration_ms, " ms")}</code>
            </dd>
          </div>
          <div>
            <dt>Input tokens</dt>
            <dd>
              <code>{numberLabel(call.usage?.prompt_tokens)}</code>
            </dd>
          </div>
          <div>
            <dt>Output tokens</dt>
            <dd>
              <code>{numberLabel(call.usage?.completion_tokens)}</code>
            </dd>
          </div>
          <div>
            <dt>Total tokens</dt>
            <dd>
              <code>{numberLabel(call.usage?.total_tokens)}</code>
            </dd>
          </div>
        </dl>
      ))}
      {calls.length > 8 && (
        <p>Showing the first 8 of {calls.length} recorded calls.</p>
      )}
    </section>
  );
}
