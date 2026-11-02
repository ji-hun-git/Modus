# Current service candidate — 2 November 2026

## 3 November: Ask intelligence recovery

The previously failing Ferritin threshold and longitudinal questions now reach
typed, read-only operations. The same plan/executor supports other exact saved
tests and medical aliases; no model performs the authoritative arithmetic.

**Root cause at baseline `384313b`:** the first receiver is
`backend/modus_entry/app.py:390` (`history_chat`). For “last below 60”,
`investigation_policy.py:171` returned no bounds whenever latest and a numeric
literal appeared together; `history_agent.investigation_bounds` then produced
`unsupported_filter`. For “How has … changed across my checkups?”,
`history_agent.allowed_request` (`history_agent.py:58` in that baseline) rejected
the wording before routing. Neither failure reached Muse. Existing comparison
and source tools were not connected to these Ask operations. A separate
projection defect discarded range/specimen/method before Ask comparisons.

**Implemented:** `history_query_plan.py` composes exact measurement, operator,
selection and dates into a strict schema; `history_query_executor.py` executes
over the captured history using existing comparability and proof checks;
`history_query.py` connects it to Ask and the existing two-report summary;
`history_query_muse.py` provides one constrained optional interpretation pass.
The request guard still precedes the planner. Unknown filters and multi-selector
tasks clarify rather than lose conditions. Existing latest/source retrieval and
continuations remain usable. Original excerpts, amendments and availability are
preserved. Ask retains printed lab context. No new database, framework, clinical
model or training is introduced.

**Offline verification:** `python scripts/check_service.py` passed 1,223 backend
tests (2 research-wrapper skips), 195 frontend tests and the production build.
The three fresh Ask test files contain 127 cases, including operators and decimal
boundaries, wording/analyte combinations, no-match versus insufficient evidence,
unit/date uncertainty, conflicts, late availability, corrections, original file
bytes, storage-order invariance and later nonmatching observations. Seven
injected Muse cases cover success plus changed scope/metric/condition, malformed
output, refusal and timeout. The runner reported no protected-file access.

**Running service:** `http://127.0.0.1:8024/` uses the feature worktree's checked
backend and all nine matching frontend artifacts. A fresh 54-request loopback
probe (four workers; 23 authored saved facts) passed with unchanged fact content
and zero provider calls. One local run measured median 23.35 ms and p95 140.5 ms;
this is a small local service diagnostic, not production capacity or model quality.

The authored answers are: latest Ferritin 71.4; latest below 60 is corrected 58.9
on 2024-02-20; four-result history 49.5 → 58.9 → 64.2 → 71.4 with supported
first-to-last difference 21.9 ng/mL. The source excerpt/file retains the original
58.6, and the UI marks the saved correction. CRP uses the same engine and returns
a supported 0.6 mg/L difference. These are authored examples, not clinical data.

Browser verification uses a fresh isolated local Chrome context with external
requests blocked. It exercises Ask, exact source inspection and original download,
keyboard focus, associated multi-visit history and 390px layout. The browser
found a real rendering crash from missing optional terminology metadata; both
the backend contract and defensive frontend rendering now have regressions.
The final run passed **10/10 checks** at 1440/1024/390px, with four actual loopback
Ask requests, zero provider calls, zero page/console errors and zero failed
network requests. Backend bundle:
`sha256:c623d0d410dd9d629d8fda92d461421045640e383f1fcf41c723a8966aa7524e`.
[Desktop evidence](../demo/ask-query-evidence-desktop.png),
[mobile evidence](../demo/ask-query-evidence-mobile.png) and
[recorded history difference](../demo/ask-query-history-desktop.png) show the
authored examples. Run receipts remain separate from evaluation data.

**Still unproven:** live accuracy of the new Muse planner, arbitrary phrasing or
mathematics, clinical reasoning, production privacy/load, and final release
qualification. The bounded semantic fallback does not silently interpret unknown
filters. Evidence over 48 records requires narrower dates. Existing evaluation
and held-out files were not read, run or changed; no API calls, training or main
merge were performed. Historical sections below describe their own revisions.

This is a runnable synthetic record-integrity prototype, not a finished
production health service or a final hackathon submission.

## Changes included

- Whole-history factual retrieval with everyday terminology, scoped previous
  result follow-ups, bounded paging, explicit correction recovery and SQLite
  contention handling.
- A personal source-file orbit, original-evidence inspectors and simpler
  review screens. Home retains at most four readings; deeper comparison stays
  inside the selected report flow.
- Printed lab ranges, specimen and method, explicit comparability rules and
  source/revision/scope-bound claim checks. An incompatible or unknown context
  does not silently become a numerical difference.
- Separate evidence for a date printed in a report header. Both its page and
  the result's page survive saving and corrections. A text match never proves
  that a date belongs to a particular result.
- **Compare reports → Prepare a summary to keep → review → download.** The HTML
  and JSON brief includes both reports' visible records, supported recorded
  differences, limitations, related discrepancies and original source excerpts.
  A stale capture, correction or changed preview blocks the download.
- A portable checked offline preview command. Source and build hashes must
  match the passing service check; protected evaluation artifacts are excluded.
  Eight frontend allowlist destinations were corrected so a fresh extract uses
  the same active frontend tree as the working app.

## Verification and its limits

The current offline service check passes **1,062 backend tests, 171 frontend
tests and the TypeScript/Vite build** on the development Windows machine.
The dedicated public checkout separately passes **1,060 backend tests, two
expected skips for excluded research wrappers, 171 frontend tests and the build**.
One existing Starlette test-client deprecation warning remains. Checks include
120-record exports, conflict companions, original preservation, old/corrected
history, stale review rejection, malformed request rejection, HTML escaping,
bounded rendering and 12 concurrent export requests. These tests do not measure
real-world extraction or clinical accuracy. CI independently runs the same
command on Windows and Ubuntu; consult the current commit's actual check status.

Two earlier authored live-service sessions on the same date made 10 actual
`muse-spark-1.3` requests: 26,404 input / 4,740 output tokens, estimated
$0.05315000 combined. All ten requests succeeded; this is the total for those
two sessions, not the project's lifetime usage. The larger session exercised
PDF/image import, review/save, blood-pressure clarification and dated lookup,
and factual conflict investigation. The two-call follow-up exercised separate
date/result pages. Narrow service checks passed 22/22 and 13/13 respectively.
The inputs and expectations were authored and reviewed by the assistant, not
independent human gold. The provider alias is mutable; invoice costs may differ.
No new API call is needed for the deterministic comparison export.

The browser flow was exercised with three newly authored CSV files: two checkups
and a conflicting copy. All seven fields were reviewed and saved through the
interface. The exported HTML and JSON retain seven records from three files,
including both conflicting TSH values. Differences are reported for CRP and
Ferritin; TSH has no invented winning value or numerical difference. The original
download matches the uploaded bytes. Review gating, download focus and a 390px
layout were checked; the browser reported no warnings or errors. These are fresh
development checks, not a new held-out score.

![Reviewed comparison download in the actual application](../demo/report-comparison-export.jpg)

The separate local research workspace completed a licensed Llama 3.2 3B
100-step extraction-adapter pilot. Four new authored development probes exposed
empty-report and damaged-OCR failures; exact responses were 2/4 under the
training instruction and 1/4 under a post-hoc schema control. The base was also
format-noncompliant. This is neither an optimized baseline nor a general quality
claim. The adapter, gated weights, training inputs and local credentials are not
shipped in this repository; the adapter is disabled in the product.

## Run locally

```sh
python scripts/setup_entry.py
python scripts/check_service.py
python scripts/serve_service.py --port 8011
```

The offline preview binds only to loopback and stores records in ignored
`release/offline-service/records.db`. Closing/restarting it does not delete that
database. Explicit reviewed import remains necessary to save new records.

## Still unfinished

Independent human annotation/quality review, robust local-adapter abstention,
SAM region grounding, hosted Guard, production accounts/encryption/privacy,
native desktop packaging, organizer eligibility confirmation and the final
video/submission remain separate work. The first-party LICENSE still requires
the owner's choice. Existing historical evaluation results are not rerun or
changed to qualify this new candidate.
