# Frozen held-out comparison — 29 October 2026

Executed once after the full release gate, at source commit `b382987`. The durable admissions record zero prior exposures. Source and dataset hashes remained unchanged throughout both suites. Labels are AI-authored and await independent human review. These are small synthetic sets, not clinical validation.

| Suite / method | Exact passes | Notes |
|---|---:|---|
| Workflow: fixed local route | 5/24 |19 relevance failures |
| Workflow: bounded Muse agent |17/24 |7 relevance failures;12 additional paired successes,0 regressions vs local |
| Documents: local parser |1/8 |3 unsupported images retained as failures |
| Documents: single-pass Muse |8/8 |Frozen exact linked field/span grader |
| Documents: Muse extract + verify |8/8 |All8 verification passes completed; no measured exact-accuracy gain over single pass |

On the parser-supported PDF subset, local passed1/5 and both Muse pipelines5/5. Workflow support, scope and exact-prose checks passed24/24 for both methods; those checks do not certify semantic/clinical safety. The workflow suite exercises the legacy record agent, and document gold covers HbA1c, eGFR and LDL. These results do not establish accuracy for all eight record kinds.

The model agent improved exact workflow relevance by12 paired cases (50 percentage points). Seven cases still failed. Do not generalize that improvement to current whole-history Ask or treat the model verifier as an accuracy win: document scores tied. Preparation and reasoning settings differ, so latency differences cannot isolate the effect of verification.

67 actual Muse requests completed:43 workflow and24 document requests. Estimated usage cost was$0.30866175; cumulative Meta accounting including prior work/jury/SAM was$0.572474. Invoices are unverified. Failed parser attempts cost no model calls. [Full outcomes and failed case IDs](heldout-contest-20261029.json) · [Per-call telemetry](heldout-calls-20261029.json).

Every scheduled attempt is retained. No automatic retries, second run, post-result gold changes or tuning was performed. Subsequent UI/replay revisions do not inherit these frozen quality results; regression tests and fresh development checks are separate.
