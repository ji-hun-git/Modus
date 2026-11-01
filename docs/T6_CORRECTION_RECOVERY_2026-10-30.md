# Correction recovery and contention — 30 October 2026

This revision addresses F01 and F02 from the [T5 audit](T5_SERVICE_AUDIT_2026-10-30.md). The orbit, original files, reviewed base records and occurrence/availability semantics are preserved. This is offline engineering verification, not model-quality evidence or a human usability study.

## Correction recovery

The exact reviewed correction, preview identity, pending request, error and receipt now live in a tab-level store independently of the evidence dialog. Closing the dialog, switching fields or navigating workspaces does not discard the transaction. A temporary **Check save result** notice explicitly retries the identical payload; the existing idempotent server receipt prevents another revision. There is no automatic retry or model write permission.

Concurrent clicks share one operation. Network failures, HTTP 408/429 and server errors preserve retry identity. Definitive 4xx rejections retain edits but require a fresh preview/review. Async completion updates the session after a dialog closes. Saved versions and another correction remain available after success. A different historical scope hides a resumed latest-version edit until the owner explicitly resumes it; saved-version lists only render in their fetched scope.

No medical text is written to browser storage. Recovery lasts for this tab's lifetime, with a before-unload warning for unfinished work. **Recovery after reload, browser crash or reopening the browser remains unimplemented.**

Browser proof used a copied synthetic database on port 8013. Test-only middleware let an actual correction commit succeed, then replaced its acknowledgement with HTTP 503. On the final frontend (`index-B_z3aZuD.js`), Pulse 73.00 was reviewed and corrected to 74.00. Closing the dialog, selecting another field and reopening Pulse retained the exact review. Checking the result outside the dialog recovered the existing receipt. The original excerpt remained 70.00; the original reviewed value was 71.00. Earlier probe corrections 72.00 and 73.00 remained separate revisions. The first browser opening used a cached older bundle; it was reloaded and excluded from proof of the new UI. No fault middleware ships in the app.

## Database changes

History, multi-cutoff comparisons, revision history and legacy snapshots still capture their clock and eligible rows inside one `BEGIN IMMEDIATE` transaction. Records are copied as packed SQLite results, then decoded and projected outside the transaction. This removes thousands of Python/SQLite row transfers and JSON parsing from the reserved-writer interval. Moving only decoding was insufficient: the first candidate still failed one concurrent request and was rejected.

Offline Ask analysis and its audit write now run in the worker pool outside the ASGI event loop. Genuine SQLite BUSY/LOCKED errors return HTTP 503 with `Retry-After: 1`. Other SQLite errors are not mislabeled as contention. Correction recovery retains its exact request on 503. No journal-mode migration, schema change or silent overwrite was introduced.

New tests pause projection while another thread commits: the writer completes and the paused view keeps its captured state. Additional tests exercise 24 concurrent retries after a lost acknowledgement, a real external writer lock, original bytes and event-loop isolation.

## Offline measurements

Same authored scale history as T5: **5,009 facts / 53 files**. Requests alternate full-history GET and offline Ask POST on a local single-process server. These are diagnostic measurements, not frozen evaluations or production load certification. Machine load and browser activity were not controlled; runs varied.

| Run | Workers / requests | HTTP 200 | Failures | p50 | p95 | Wall time |
| --- | --- | --- | --- | --- | --- | --- |
| T5 original | 1 / 10 | 10 | 0 | 899 ms | 1,201 ms | 8.86 s |
| T5 original | 8 / 32 | 28 | 2 HTTP 500 + 2 read errors | 3,892 ms | 17,237 ms | 24.52 s |
| T6 final | 1 / 10 | 10 | 0 | 964 ms | 1,253 ms | 9.73 s |
| T6 final | 8 / 32 | 32 | 0 | 7,220 ms | 14,202 ms | 33.78 s |
| T6 extended | 8 / 80 | 80 | 0 | 6,971 ms | 14,136 ms | 82.59 s |

Final comparable and extended runs: **122/122 HTTP 200**, no observed lock failures. Throughput is not improved; projecting and returning the whole history remains slow. Paging, response size and bounded rendering remain F03. The reproduced reliability issue is resolved within these tested workloads, not at arbitrary scale.

## Verification and local artifacts

- `.venv/Scripts/python.exe release/T6-recovery/run_regression.py`: 36 selected backend modules, **871 passed**, one existing Starlette/httpx deprecation. The child guard recorded no protected evaluation/held-out/secret-file access attempts and blocks non-loopback connections.
- Final `npm test` in `entry/frontend`: **123 passed**. Final `npm run build`: TypeScript + Vite passed. These are focused checks, not the full release gate.
- `release/T6-recovery/http_stress.py` and `http_stress_extended.py`: final workload outputs are `scale-http.json` and `scale-http-extended.json`. Earlier attempts are retained separately.
- `release/T6-recovery/verify_recovery.py`: four versions, no duplicate correction, earlier availability restores 71.00 and 73.00, original download exactly matches the imported CSV.
- `original-integrity.json`: ordered table hashes for sources, facts, observations, documents, drafts and original commit receipts equal the T5 copies in both databases. Amendment history is append-only; audit logs grow.
- `browser-recovery.json`, `correction-recovery-after-close.png` and `corrected-original-preserved.png`: final browser and evidence proof.

F01 is resolved for dialog/navigation recovery within the tab; durable recovery remains open. F02 no longer reproduces on these workloads; external contention is retryable. F03–F13 remain open. No API spending, evaluation/held-out execution or artifact update, commit, push or release stamp. Temporary servers used copied databases; the 8012 workspace was not changed.

Temporary audit servers and tabs were closed after verification. `release/T6-recovery/verification.json` records the final counts and remaining limits.
