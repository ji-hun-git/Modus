# C1–C2 integration research — 28 October 2026

This review checked the official interfaces and the fixed development smoke. It did not inspect held-out material, run a real provider call, install workshop code, or establish model accuracy.

## Verified vendor contract

- [Meta structured output](https://dev.meta.ai/docs/structured-output) supports `response_format.json_schema` with `strict: true`. Strict objects require `additionalProperties: false` and every property listed in `required`; nullable fields still need to be required. Nested `anyOf` is supported, but `oneOf`/`allOf` and root unions are not. Pydantic discriminated unions therefore need care. Schema validation is about shape, not factual support.
- [Image understanding](https://dev.meta.ai/docs/image-understanding) accepts inline base64 `image_url` blocks. Its suggested localization coordinates use a normalized 0–1000 grid; Modus must explicitly specify its own normalized convention and retain the exact image dimensions/orientation. Image token use varies with resolution. The guide points to `/v1/responses/input_tokens` for exact estimates; that extra endpoint is not called by this smoke.
- [File handling](https://dev.meta.ai/docs/file-handling) accepts inline PDFs, but vendor preprocessing retains only bounded page text and images. Modus should enforce its stricter page limits before transmission and reject excess pages rather than silently presenting a partial document as complete.
- [Chat Completions](https://dev.meta.ai/docs/protocols/chat-completions) uses `max_completion_tokens`; `max_output_tokens` belongs to Responses. Preserve assistant tool calls and matching tool results. Keep server-controlled model, endpoint, tool allowlist and bounds.
- [Models](https://dev.meta.ai/docs/models) recommends `muse-spark-1.3` for new Spark work. Standard mode is the chosen ID. The catalog still says Muse Wonder is unavailable in South Korea. No model substitution is appropriate here.
- [Pricing](https://dev.meta.ai/docs/pricing-rate-limits), checked today: Spark Standard costs $1.25 per million input tokens, $4.25 output, and $0.15 cached input. The smoke's usage-derived estimate charges all reported input at the uncached rate; it is not an invoice. Missing usage remains unknown.

## Useful workshop pattern

The pinned [workshop agent guide](https://github.com/meta-models/legal-agent-workshop/blob/2a8efc86c70d9a42d76db0afb6ae1511e5a86d8e/agent/README.md) separates document text, quote checking, model decisions, saved progress and human escalation. The [handbook](https://github.com/meta-models/legal-agent-workshop/blob/2a8efc86c70d9a42d76db0afb6ae1511e5a86d8e/HANDBOOK.md) explains why a real quote can still support a wrong conclusion, and why required checks belong at a boundary the model cannot skip. Apply that pattern; do not import the workshop's filesystem/write authority or its case material.

## Failure cases that matter

1. A PDF can mix text and scanned pages. Route per page; a nonempty first page must not hide the remaining scans. Reject unreadable, oversized, truncated or encrypted inputs explicitly.
2. A quote matching PDF text or OCR is not visual proof. Text layers can be wrong, and OCR is another model output. Record the support basis. Do not promote a second model's agreement to independent verification.
3. Preserve the connection between value, label, unit and date. Substring matching of a number alone can match another row, a reference range or part of a larger number.
4. A proposed box must be bounded, ordered and associated with a real page. Keep unknown boxes null. Geometric validity does not establish that a box contains the fact.
5. Verification must address every field exactly once. Missing, duplicate or unknown field IDs, unsupported statuses, refusals and timeouts must not become successful verification. Preserve the first draft for human review when the verifier fails.
6. Classification and confidence are model proposals. Confidence is uncalibrated; neither confidence nor agreement can authorize commit. Broader types remain draft-only until their reviewed storage contract exists.
7. Document instructions remain untrusted text. Extraction and verification receive no tools. Committed-record questions never inherit the unreviewed draft or its instructions.

## Readiness and smoke

Read-only boolean checks found no `MODEL_API_KEY` in the current process and no root `.env` file. No credential values were printed. Live readiness is blocked on the owner's API setup; no request or credit was spent in this review.

`scripts/smoke_record_extraction.py` prepares by default. `--input image` (default) renders the fixed authored PDF locally; `--input pdf` independently probes the text-layer route. Execution requires `--execute --allow-network`. The harness reserves at most 8 requests and 17,600 output tokens, rejects serialized requests above 128 KiB, retries zero times and never commits records. These are request/output/payload bounds, not a hard monetary or input-token cap. Each run uses one tiny authored case and a separate fixed record inventory. It is not a general performance benchmark. Regenerate plans after the final source identity is stable.
