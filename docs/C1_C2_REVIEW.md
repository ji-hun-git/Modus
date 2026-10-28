## 28 October — Real Meta execution verified

The backend now uses the owner-supplied key from the ignored local `.env`; no credential is stored in frontend code or the public-source allowlist. `muse-spark-1.3` completed the authored image and PDF extraction → second-pass check → bounded record-inventory loop. The browser also completed live image upload, explicit review edit, save, historical availability isolation and a supported agent answer in a separate synthetic test store.

There were **16 real HTTP requests: 14 successful completions and 2 HTTP 400 responses**. Both failures are retained. The first smoke exposed our unsupported `tool_choice: required`; Meta's hosted endpoint accepts only `auto`. Both callers now use `auto`, while application validation still rejects responses without permitted tool calls. [Official tool-calling contract](https://dev.meta.ai/docs/tool-calling).

Successful responses reported **39,519 input + 9,691 output tokens**. Their uncached Standard-rate estimate is **$0.0905855**, not an invoice; billing/usage for the two HTTP errors is unknown. Image smoke: 4 calls, 12.16 seconds; PDF: 4 calls, 13.03 seconds. These are single authored-case probes, not accuracy or workflow superiority results.

Browser evidence deliberately changes the synthetic proposed value 5.6 to 5.8 to verify review provenance; the source quote and original proposal remain 5.6. A local OCR quote mismatch remains visible even though Spark reads the authored field correctly. Model agreement is not independent evidence of correctness. The browser's four Meta calls and saved fact live only in `release/live-browser-20261028.db`; the main service's 10 facts/4 files remain unchanged.

Current full gate: **918 backend / 802 entry / 25 frontend**, both production builds and existing deterministic/document/temporal evaluations passed. Commands: `python scripts/check.py`; `python scripts/smoke_record_extraction.py --execute --allow-network --input image|pdf` with distinct evidence paths. Evidence: `eval/live-meta-summary-20261028.json`, `eval/live-meta-browser-20261028.json`, and `release/live-api-gate-20261028.log`. No held-out data was opened or run; frozen baseline outputs remain unchanged. Historical blocked/zero-call reports below are retained evidence of earlier versions, not the current status.

Checklist delta **+1: 7/17 complete** (real Meta extraction/orchestration recorded). License, public commit/push, broad model comparisons, owner gold review and final submission remain pending. No video or native-shell work was done.

# Extraction and review milestone — 28 October 2026

Modus now produces source-linked record drafts through a two-pass extractor. This is a locally verified integration, not measured live model quality. The owner then authorized continuing directly into broader record storage.

## Implemented

- PDF text first; sparse or image-bearing pages are rendered locally, including scans beneath long text headers. Configured TeleOCR can supplement images. Original page images still reach the chosen Spark vision path when OCR is unavailable or fails.
- Seven document schemas: labs, checkups, prescriptions, discharge summaries, vaccination cards, imaging reports and other records. Required nullable fields retain unknowns. Korean/original-language labels remain verbatim.
- A separate verification call receives original source pages and every proposed field. It cannot repair fields, call tools or commit records. Failed verification retains clearly unconfirmed drafts for human review.
- Exact text checks retain mismatches, censored/negative/range values and unknown support. Numeric qualifiers cannot disappear into a positive point measurement. Text agreement and model agreement are not semantic proof.
- Proposed boxes retain transmitted image dimensions, hash and orientation; boxes and confidence are not independently calibrated or located. No SAM accuracy is claimed.
- Broader fields remain visible in review, including after a supported measurement is saved. At this milestone only three metric types can be committed; B is responsible for expanding that boundary.
- Duplicate uploads reopen their existing draft before a provider call. A local reader lock serializes requests. Successful and partial extraction traces are recorded in Activity with stage, model, IDs, latency and reported usage.

## Verification and commands

`python scripts/check.py`: **782 backend tests, 667 entry tests, 22 frontend tests**, both production builds. Deterministic scenarios **10/10**, local document fixtures **6/6** plus two explicitly unsupported cases, temporal dual-time **10/10**, entry temporal **6/6**, routing **5/5**. These are software/development checks, not new frozen-baseline or held-out scores.

Focused extraction suite **81 passed**; new smoke harness **13 passed**; HTTP integration checks **4 passed**. Independent audit found and fixed mixed text/scan page loss and dropped numeric qualifiers. Existing Starlette/httpx deprecation remains visible.

Browser fixture: two synthetic facts, artificial extraction transport explicitly disclosed, edit 5.6 to 5.8, explicit save, original 5.6 quote retained, unsaved vaccination fact retained, historical 3 files/9 measurements unchanged, current 4/10. Initial upload attempts failed because the test image was rewritten after selection; reselecting the file in a fresh test session passed. No production record was used. Evidence: `eval/step-c-browser.json`, `release/step-c-review-artificial.png`.

Exact tested identity: `eval/step-c-release-gate.json`; full output: `release/step-c-gate.log`.

## Live smoke and limits

Prepared fresh image and text-PDF plans with `python scripts/smoke_record_extraction.py --input image|pdf --out <new-path>`. Executed the credential preflight with `--execute --allow-network`; it stopped before transport: **credentials_not_configured, 0 requests, $0 spent**. Evidence: `eval/record-extraction-c1c2-credential-check.json`.

The smoke permits at most eight requests and 17,600 reserved output tokens, no retries/commits, bounded payloads. Its image variant tests Spark vision plus verification without TeleOCR; production may add available local OCR. Actual billed cost is unknown for future calls; the harness reports only an uncached-price estimate from complete reported usage. One authored fixture is not an evaluation corpus. See [primary Meta documentation review](C_EXTRACTION_RESEARCH.md).

Held-out inputs, labels, generators and previews remain untouched. Frozen baseline artifacts were neither modified nor rescored. Earlier development outcomes keep their earlier source identity. No SOTA or clinical-validation claim is made.

New runtime extraction files are each below 250 lines; review component 102 lines, component CSS 154, call details 38. Existing large components/styles remain cleanup work. Windows browser dark mode was inspected; macOS, native shell and light mode are not qualified by this milestone.

Checklist delta **0: 6/17 complete**. Jason still owns API access, license choice, organizer clarification and human gold-label review. No publication or demo/video work occurred.

Live-compatible source extract verified: `release/public-record-entry-live-20261028`, 321 manifest entries, clean frontend install, 800 backend passes + 2 expected compatibility skips, 25 frontend passes and build/evaluations green. Gate matches the workspace. Evidence: `eval/live-source-extract-20261028.json`. Python reused the workspace virtual environment; no fresh-machine or publication claim. Exact-key scanning found no credential in the 321 allowlisted files or seven selected live reports/logs.
