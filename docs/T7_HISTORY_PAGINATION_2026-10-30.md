# Whole-history pagination and bounded rendering — 30 October 2026

T7 addresses F03 from the [service audit](T5_SERVICE_AUDIT_2026-10-30.md). Normal browsing now requests bounded pages instead of downloading and mounting the entire archive. The orbit design, source evidence, append-only corrections and occurrence/availability boundaries remain intact. This is offline engineering verification, not a model-quality evaluation or production capacity claim.

## Service and interface changes

- New `/api/history/page` returns at most 50 facts, source summaries or field names. Each response identifies an immutable captured history; subsequent pages keep its two time bounds. Search, type/facility filters and field selection operate over the capture, not merely the visible page.
- Home requests 12 source summaries and lazily loads the selected file's records. The orbit shows the complete file count with a paged set of satellites. Records, Documents, Trends, Earlier results and Brief use bounded pages. Brief retains up to its existing 80 selected records across pages.
- Source inspection and Replay lists render bounded windows. A large conflict remains accessible through its own paged lookup. Trends explicitly says its chart shows the displayed page and keeps units separate; no hidden sample is presented as the whole trend.
- A process-local, single-flight cache avoids repeatedly projecting the same history for browsing and offline Ask. SQLite generation triggers invalidate new lookups after committed history changes, including writes from another connection. Old captured pages remain stable. Audit-log writes do not invalidate history.
- Captures expire after 10 minutes, process restart or eviction. HTTP 410 requires explicit reopening; a stale token cannot silently become a newer history. Reopening with the same explicit time bounds reconstructs that historical view. A latest-history refresh is a separate owner action.

The cache retains at most four captures with a 48 MiB approximate encoded-record budget. This is **not** a hard resident-memory limit. The initial capture still reads and projects the complete eligible history, and filtering scans that capture. This implementation is not database-level keyset pagination. Explicit full export and the comparison API still return complete responses, although their interactive rendering is bounded. Those are the next scale limits, not claims already solved here.

## Offline measurements

Same authored data as T5/T6: **5,009 facts in 53 files**, copied into an isolated database. Requests alternate history GET and deterministic offline Ask, with no provider access. The T7 normal-browsing workload changes GET from `/history/view` to `/history/page?limit=50`; it also benefits from the new shared cache. This is not an isolated measurement of pagination alone. Concurrent batches follow a sequential warm-up; machine load was not controlled.

| Run | Workers / requests | HTTP 200 | p50 | p95 | Wall time |
| --- | --- | --- | --- | --- | --- |
| T6 full history | 8 / 32 | 32 | 7,220 ms | 14,202 ms | 33.78 s |
| T6 full history, extended | 8 / 80 | 80 | 6,971 ms | 14,136 ms | 82.59 s |
| T7 paged, final sequential | 1 / 10 | 10 | 46 ms | 678 ms | 1.09 s |
| T7 paged, final concurrent | 8 / 32 | 32 | 434 ms | 542 ms | 1.78 s |
| T7 paged, final extended | 8 / 80 | 80 | 398 ms | 524 ms | 4.04 s |

All **122 final requests succeeded**. An earlier independent paged pass also succeeded, with 8-worker p95 of 669/674 ms. For comparison, retaining the legacy full GET on the new warmed cache produced 32/32 successes, p95 3,528 ms and wall time 8.87 s. Caching helps the legacy route, but transferring the full payload remains expensive.

- Complete view: **7,092,060 bytes**. First 50-record page: **71,869 bytes**. Maximum observed across the complete page walk: **72,276 bytes**.
- Home's first 12 source summaries: **5,631 bytes**, one warm request measured 10 ms. This single timing is not a percentile or cold-start claim.
- Records DOM: **50 articles / 1,809 elements**, compared with T5's 5,009 articles / 160,462 elements. These are DOM counts, not a browser-memory benchmark.
- Complete traversal: **101 fact pages**, exactly 5,009 unique IDs; **2 source pages** at limit 50, exactly 53 unique IDs. Both match the full captured view with no missing or duplicate IDs.

## Verification

- `.venv/Scripts/python.exe release/T7-pagination/run_regression.py`: **888 backend tests passed** across 37 selected modules, including 17 new pagination cases. The child guard rejects evaluation/held-out/secret-file reads and external networking; no protected accesses were attempted. One existing Starlette/httpx deprecation warning remains.
- Final `npm test` in `entry/frontend`: **132 passed**. Final `npm run build`: TypeScript and Vite passed. Final browser bundle: `index-BGeKvxJ2.js`.
- Browser verified source records 51–100 in a 100-field file, global search beyond the first page, Trends fields beyond the first 50, and a Brief combining selections from different pages. Server restart produces an explicit expiry error. Final checked tabs had no console warnings/errors.
- Browser correction changed the copied synthetic Pulse 74.00 to 75.00 through preview, human-review checkbox and commit. Refresh showed 75.00 beside the original 70.00 excerpt. All five saved versions 71/72/73/74/75 remain; earlier availability restores 71.00 and 74.00.
- Downloaded original CSV bytes match the originally imported file. Ordered table hashes for sources, base facts, observations, documents, drafts and original commit receipts equal the T6 copies in both audit databases. The new correction is append-only; cache-generation metadata and audit logs may change.

Artifacts are under ignored `release/T7-pagination/`: `paged-http.json`, `paged-http-first-pass.json`, `scale-http.json`, `pagination-integrity.json`, `original-integrity.json`, `regression-guard.json`, `frontend-final.json`, `browser-observations.json`, and screenshots `paged-orbit.png`, `paged-records.png`, `correction-original-preserved.png`. The private harness used copied databases on 8013/8014; the existing workspace database was preserved. Temporary audit servers and tabs were closed after verification. No listener was running on the earlier 8012 preview port at cleanup; this report does not claim a refreshed live preview there.

The initial combined runner exposed an incorrect new frontend assertion: Replay correctly rendered two independent 50-item windows, while the assertion expected one. The assertion was corrected to 100 total; the final frontend run/build passed. No product failure is hidden by presenting that earlier run as green.

No evaluation or held-out inputs/results were read, executed or changed. Full release gates were intentionally not invoked because they execute those suites. No API credits, commit, push or release stamp. Existing unrelated working-tree changes remain intact. T6's correction recovery remains tab-lifetime only; browser crash/reload recovery is still open.

## Medical model and retrieval: actual status

Modus is a source-backed personal record service using Meta models and typed tools; it is **not a trained or clinically validated medical model**. Offline execution is deterministic software, not model output. This iteration changed no model or provider integration.

The older measurement path has BM25 retrieval and ontology aliases (`backend/modus/record_retrieval.py`). The active whole-history agent has time-scoped evidence search, source references and typed calculations in `backend/modus_entry/history_tools.py`, but its general evidence search is weighted literal word/phrase/date/source matching. It does not yet provide broad semantic medical retrieval or an external medical-guideline RAG pipeline. F04's natural-language false negatives therefore remain open.

The next retrieval work should strengthen the active whole-history path: reviewed aliases and plain-language names, hybrid lexical/semantic candidates, typed exact-number/date queries, explicit uncertainty, and sentence-to-evidence verification. It must preserve availability boundaries and conflicting values and be tested on newly authored development cases while frozen sets remain protected. A specialist checkpoint alone would not fix bad retrieval or missing evidence.

Medical interpretation is a distinct product/research capability. If pursued later, it needs separately vetted/versioned references and domain-specific evaluation and clinical review; retrieval does not establish clinical validity. The [original RAG paper](https://arxiv.org/abs/2005.11401) describes retrieval-augmented generation, while the [AMIE clinical dialogue study](https://www.nature.com/articles/s41586-025-08866-7) illustrates a separate clinical evaluation problem. Neither is evidence that Modus is clinically validated. The contest path remains record-only.
