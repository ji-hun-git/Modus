# Modus service audit — 30 October 2026

Follow-up: [T6 recovery and contention verification](T6_CORRECTION_RECOVERY_2026-10-30.md) addresses F01 within the current tab and removes reproduced F02 failures. [T7 pagination](T7_HISTORY_PAGINATION_2026-10-30.md) addresses F03 for normal browsing and bounded rendering; cold capture and complete comparison/export payloads remain scale limits. Findings below remain the original baseline; F04–F13 remain open. Paging reduces orbit density but does not independently close F05's mobile hit-target audit.

[T8 terminology retrieval](T8_MEDICAL_TERMINOLOGY_2026-10-30.md) improves F04 for 24 named medical concepts and selected English/Korean aliases, with ambiguity clarification and source-linked proof. Uncovered conversational, numeric and relative-date requests remain open; the original issue register below is retained.

The current build preserves records well on the normal path, but is not ready to promise effortless whole-history use. Passing regression tests concealed failure recovery, scaling, question-routing and cross-screen provenance defects. Fix those before adding another feature or visual theme.

This audit makes no application-code changes. It records the faults for revision. The design agent reviewed the active interfaces independently; the integration audit exercised the browser and service with newly authored synthetic data. This is an agent-driven walkthrough, not a human usability study, medical validation or live-model benchmark.

## What was examined

- Inventoried and fingerprinted 124 Python, TypeScript, JavaScript and CSS source files, 23,469 lines, under `backend/modus`, `backend/modus_entry` and `entry/frontend/src`. Python syntax was parsed; the active frontend passed TypeScript/build. Inventory is not a claim of line-by-line semantic review of every file. Dependencies, archived applications, training code and evaluation corpora were outside this audit.
- Reviewed the active import → draft → review → commit → corrections → typed Ask → source → replay paths. The design audit covers Home, Records, Documents, Trends, Ask, Replay, Changes, Brief and shared dialogs.
- Ran 35 selected backend runtime test modules under an access guard that rejects evaluation/held-out/secret-file reads and non-loopback networking. **864 passed**, one existing Starlette/httpx deprecation warning. No protected-file access attempts were recorded.
- Ran **110 frontend tests**, all passing, and `npm run build`, passing.
- Entered a fresh 17-field, eight-kind CSV through the browser. Edited Pulse `70.00` to `71.00`, explicitly saved, inspected original evidence, downloaded the original, searched the history, exercised ambiguous BP lookup, viewed Trends and Replay, exported a view and a reviewed Brief.
- Ran 25 newly authored exploratory questions and 18 service edge-check groups. These are diagnostic cases outside `eval/`, not frozen-set scores or independently human-reviewed labels.
- Imported 50 authored files with 100 fields each into a separate scale database: **5,009 facts, 53 files** including the standard seed. Measured in-process and real loopback behavior; inspected dense Home on desktop and at 390px.

The normal preview at 8012 and its database were preserved. Temporary audit servers used 8013/8014 and isolated databases under `release/T5-audit/`. Both audit servers and tabs were closed after verification; databases and artifacts remain for reproduction. No API credentials, paid requests, frozen evaluation runs, held-out access, commits or pushes were used. No release-gate stamp was regenerated.

## Ranked issue register

Priority means revision order for this local prototype. P1 blocks a dependable whole-history service; P2 creates misleading or difficult interactions; P3 is polish. No new P0 data-corruption defect was demonstrated.

| ID | Priority | Finding | Evidence status |
| --- | --- | --- | --- |
| F01 | P1 | Closing a source dialog discards an unconfirmed correction and its exact retry payload | Browser reproduced |
| F02 | P1 | Parallel history reads/Ask fail with database locks | In-process and real HTTP reproduced |
| F03 | P1 | A whole history is returned/rendered in one large response and list | HTTP and DOM measured |
| F04 | P1 | Natural wording produces false-negative searches despite existing records | Offline HTTP reproduced |
| F05 | P1 | Dense orbit files cannot reliably be selected at their visible centers | Desktop/mobile screenshot and DOM hit-testing |
| F06 | P2 | Records omits the explanation for an edited value versus its original | Browser reproduced |
| F07 | P2 | Changes cannot open evidence for the new mixed generic import | Browser reproduced; legacy route confirmed |
| F08 | P2 | The prior answer stays beneath a newly typed, unrelated question | Browser reproduced |
| F09 | P2 | Collapsed date chip conceals the retained occurrence cutoff | Browser reproduced; scope itself is correct |
| F10 | P2 | UTC/local-date and midnight rollover can change default all-date visibility | Source-confirmed; clock-controlled browser test pending |
| F11 | P2 | Long CSV narrative rejects while the same text imports as chunks; error gives no useful cause | HTTP and source confirmed |
| F12 | P2 | Ordinary error/answer copy exposes generic failures or internal tool vocabulary | Browser and HTTP reproduced |
| F13 | P3 | Brief shows singular/plural errors such as “1 documents” and “1 records have” | Browser reproduced |

### F01 — Preserve correction transactions outside a dismissible inspector

Reproduction: Home → imported report → Pulse 71.00 → Inspect source → Correct saved record → change to 72.00 → reason → Review correction. Stop only the isolated audit server, confirm review and Save. The UI correctly says the save is unconfirmed and offers **Check save result**. Close the dialog and reopen Inspect source: the retry action and edited payload are gone; only **Correct saved record** and **View saved versions** remain.

This particular disconnected request did not reach the server: the stored value remained 71.00. It proves loss of client recovery state, not a demonstrated committed-but-unacknowledged write. The same local `pending` state also handles uncertain server responses. `RecordCorrection.tsx:17,54` owns it inside a component that `SourceCubeEvidence.tsx:199` can unmount. Parent dialogs and source selectors do not receive its transaction state.

Acceptance: pending corrections survive attempted close/source switch, or those actions are safely prevented. Recovery resubmits the identical payload; successful or stale responses resolve explicitly. Test both failure before acceptance and lost acknowledgement after acceptance.

Proof: [unconfirmed save](../release/T5-audit/correction-unconfirmed.png), [retry lost after reopening](../release/T5-audit/correction-retry-lost.png).

### F02/F03 — Bound history work and repair concurrency

`backend/modus/record_history_view.py:81` starts `BEGIN IMMEDIATE` even for captured reads. Its read phase loads/parses all eligible facts. `record_store.py:134` uses a 15-second SQLite timeout. The server log records `sqlite3.OperationalError: database is locked` at that read transaction. `app.py:152` does not translate this into a recoverable response. The offline Ask path also performs synchronous analysis and logging inside its async handler; this is a candidate contributor requiring profiling, not a measured sole cause.

At 5,009 facts, one full view was 7,092,060 bytes. Records created 5,009 articles and 160,462 DOM elements; document height was 1,159,106 px. `HistoryTimeline.tsx:194` renders the entire list. Source counts also rescan facts per source in `record_history_view.py:131`. This makes cost grow with the archive rather than the visible task.

Acceptance: the same eight-worker diagnostic completes without 500s/connection errors; queries and rendered records are bounded/paged; users can still reach every source. Preserve one consistent snapshot, both time bounds, conflicts, corrections and original restrictions. Changing transaction mode or enabling WAL alone is not sufficient proof of correctness. Add concurrent read/write and replay invariants before changing locking.

### F04 — Parse the task or clarify it; do not search unsupported grammar as literal medical evidence

The fixture contains BP 100/70 on 2022-06-02, BP 120/100 on 2020-06-02 and reviewed Pulse 71.00on2023-03-01.

| Question | Observed result |
| --- | --- |
| “When did I last have blood pressure of 100?” | Correctly asks top versus bottom |
| “When did I last have systolic blood pressure of 100 mmHg?” | Correct latest match:2022-06-02,100/70 |
| “When did I last have diastolic blood pressure of 100 mmHg?” | Correct latest match:2020-06-02,120/100 |
| “When was my top blood pressure number 100?” | No literal match, despite the BP record |
| “When was my pulse 71?” | No literal match, despite reviewed 71.00 |
| “마지막으로 수축기 혈압이100이었던 때는 언제야?” | Generic request for a recorded name/phrase |
| “When was my last vaccination?” | Generic name/phrase clarification despite a 2013 year-only entry |
| “What changed in my history?” | Generic capability text instead of asking for a comparison boundary |
| “What did I ask you before?” | Searches medical facts and reports no match instead of stating the memory boundary |

The raw artifact preserves the exact spacing of each submitted question. The table is for reading, not a replacement fixture.

`blood_pressure.py:17–48` recognizes narrow full-match forms. `history_agent.py:61–100` can route other grammar into literal search; `history_tools.py:306` then reports an empty result. The live selector uses code-bound arguments too (`history_agent.py:213–230`), so improving the parser/clarification contract matters to the Muse integration. No live result was measured here.

Acceptance: equivalent BP phrasings reach the same typed lookup; unsupported numeric predicates ask a specific clarification instead of implying absent evidence. Relative visit linkage, partial dates and prior conversational turns need explicit capabilities, not guesses. Keep all calculations and source support in typed tools.

### F05 — Keep orbit as an overview, make dense files individually reachable

With 53 files, labels and file targets overlap. DOM hit-testing found another element covering the center of 37 of 53 file targets on desktop and41 of 53at 390px. There are 53 independent Tab stops. This is more than a preference about appearance: pointing at one file can target another. The mobile page did not overflow horizontally; readability and selection still failed.

`homeReportData.ts:24–34` distributes every file around fixed rings; `OrbitMap.tsx:41,54` adds a focusable node and 23-unit hit radius for each. Use a deterministic density-aware drill-down/list while retaining one file→one source identity. Do not fix it by shrinking targets. Acceptance: 50 same-era files and an undated group remain distinguishable and reachable by pointer, touch and keyboard.

Proof: [desktop](../release/T5-audit/orbit-53-files-desktop.png), [mobile](../release/T5-audit/orbit-53-files-mobile.png), [hit tests](../release/T5-audit/orbit-dom-measurements.json).

### F06–F10 — One evidence and date contract across screens

- **F06:** Records showed reviewed Pulse 71.00 beside original 70.00 with no “Edited during review” explanation. The data are correct; the presentation obscures their relationship. `TimelineFact.tsx:66–124` never renders revision metadata or saved-version access. Home/Ask/Trends/Replay do. [Screenshot](../release/T5-audit/records-correction-missing-label.png).
- **F07:** Changes displayed “17 recorded facts added” with no source action for that mixed file. It still receives legacy observations from `App.tsx:44–206`/`ChangesWorkspace.tsx:103,227`. Use the whole-history source inspector with its captured scope. [Screenshot](../release/T5-audit/changes-no-source.png).
- **F08:** After answering “Find Pulse records,” typing “Show my vaccinations” leaves the Pulse answer beneath that new text. `HistoryQuestionPanel.tsx:151` permits editing; the answer does not display its submitted question. Bind each result visibly to its submitted question and dates. [Screenshot](../release/T5-audit/ask-answer-question-mismatch.png).
- **F09:** After a 2024-01-31 replay, the collapsed chip reads “View as of 30 Oct 2026” while Records correctly remains through 31 Jan 2024. `App.tsx:508` labels only availability as “View as of.” Show both concepts clearly. Do not silently change the selected cutoff to hide the ambiguity.
- **F10:** `HistoryTimeline.tsx:43` derives current day in UTC while App uses local components. Also, App initializes `asOf` once but recomputes `currentDay`; an open session crossing midnight can become historical on the next render. Confirm at KST 00:30 and across midnight with a partial-date record. These are source-confirmed risks, not clock-emulated browser results from this pass.

### F11–F13 — Recoverable import limits and readable copy

A 1,260-character narrative CSV field returned 422; the same narrative as TXT returned two exact chunks with no truncation. The importer has an 800-character value/quote cap (`history_ingest.py:36`), first review uses 800 (`GenericFactReview.tsx:120`), and saved corrections accept 16,000. The UI error says only to check dates, units or extraction mode. A malformed extra-column CSV receives the same vague message. Define the supported long-text contract and preserve safe parser-specific error codes/field locations.

The Pulse search answer also tells users to “inspect history_conflicts,” an internal tool name (`history_tools.py:301`). Replace implementation vocabulary with a working “Compare these records” action while retaining the typed claim's meaning. Brief grammar issues are lower priority than the recovery and retrieval faults. [Import error](../release/T5-audit/import-error.png).

## Performance measurements

Fresh synthetic data; local Windows machine; offline software only. Ten samples per stage; p95 is the observed nearest-rank value, effectively the maximum for such a small sample. These numbers are diagnostic, not capacity certification.

| Total facts | Full history p50 / p95 | Offline Ask p50 / p95 | Full history response |
| ---: | ---: | ---: | ---: |
|9|5.67 /7.93ms|8.18 /13.65ms|12,849bytes|
|109|32.96 /46.41ms|31.28 /41.93ms|154,439bytes|
|1,009|173.42 /243.17ms|177.85 /247.02ms|1,428,700bytes|
|5,009|953.67 /1,244.11ms|772.49 /991.33ms|7,092,060bytes|

Above: Starlette TestClient, without network latency. All sequential stage requests succeeded. Fifty 100-field preview+commit operations succeeded.

Real loopback confirmation, same 5,009-fact database, alternating history views and Ask:

| Workers | Requests | Outcome | p50 / p95 | Wall time |
| ---: | ---: | --- | ---: | ---: |
|1|10|10HTTP200|898.66 /1,200.89ms|8.86s|
|8|32|28HTTP200,2HTTP500,2ReadError|3,891.61 /17,236.53ms|24.52s|

The earlier in-process 80-request stress attempt stopped reporting at its first propagated SQLite-lock exception. It is retained as a failed experiment, not counted as 80 completed requests. The real HTTP run catches and records every outcome. The two connection errors are reported separately; not every transport failure is independently attributed to SQLite.

## What passed end to end

- Reviewed edit 70.00→71.00 saved; source quote remained 70.00. Original download hash matched the uploaded bytes: `f643e54b6aca065be6993c45d38ee243d60636e0666d0f2d5e2378f491731b30`.
- All eight record kinds, Korean field name, `<5`, paired BP, unlike weight units, partial year and unknown dates survived the fresh import. No diagnosis or advice was generated.
- BP ambiguity, explicit top/bottom lookup and clickable evidence worked for supported wording. Compound Pulse search preserved both 74.00 and 78.00 and the conflict.
- Trends kept kg and lb scales separate. Replay recovered the earlier six seeded facts while showing late arrivals; original downloads were 404 when the requested cutoff excluded part of the source.
- Eight identical concurrent commits inserted exactly one fact with one availability timestamp.
- Unsupported/empty/malformed/oversized files rejected; a document injection string was quarantined without executing it. Failed/draft previews did not change saved counts.
- Documents search found the imported file. Export contained 26 facts and their original scope. Selecting Pulse plus vaccination for Brief added the other Pulse conflict, yielding three exported entries; vaccination stayed 2013 without an invented day.
- No React warning/error was captured. The deliberate disconnected save displayed “Failed to fetch” in the UI; server lock stack traces are retained in the stress log.

## Revision sequence after this audit

1. **Transaction recovery and service scale:** fixF01–F03 with failure-injection and concurrent snapshot/write tests. Preserve original evidence and idempotency. Add bounded views/rendering before another large-history promise.
2. **Reliable personal history questions:** fix F04 and F08 using these fresh diagnostic cases, exact typed predicates and precise clarification. Keep offline/model identity honest; live Muse verification remains a separately authorized activity.
3. **Consistent evidence and dates:** fix F06–F07 and F09–F12. The same fact must show the same revision, source and cutoff from every entry point; repair long-text/error contracts.
4. **Density-aware orbit and shared layout:** fix F05 without replacing the agreed orbit direction. Remove duplicated full Ask panels from browsing surfaces, identify files clearly, and apply shared tokens to secondary pages. Validate the actual tasks at small and large history sizes before visual polish/F13.

No new panels, appointment prompts or companion-memory claims should be used to cover these failures. Durable draft recovery, persistent conversation, appointments, consent, authentication/encryption and real-data deployment are still separate unfinished capabilities. Current tests do not qualify the app for real personal medical data.

## Evidence and reproduction

- [Design agent's source review](design/T5_DESIGN_AUDIT.md)
- [Source inventory](../release/T5-audit/source-inventory.json)
- [Regression commands/results](../release/T5-audit/regression.json), [backend log](../release/T5-audit/backend.log), [frontend log](../release/T5-audit/frontend-tests.log), [build log](../release/T5-audit/frontend-build.log), [access guard](../release/T5-audit/regression-guard.json)
- [25 exact question/response pairs](../release/T5-audit/exploratory-questions.json)
- [18 edge-check groups](../release/T5-audit/edge-probes.json)
- [In-process timings](../release/T5-audit/scale-inprocess.json), [all real HTTP outcomes](../release/T5-audit/scale-http.json), [server errors](../release/T5-audit/scale.stderr.log), [large DOM](../release/T5-audit/records-5009-dom.json)
- Local scripts: `release/T5-audit/run_regression.py`, `probe_service.py`, `http_stress.py`, `edge_probes.py`. The scale generator deliberately refuses to overwrite an existing database. Reproduction uses new isolated paths, not the ordinary preview store.

The first regression harness attempt over-blocked Windows loopback sockets required by the test event loop. It was stopped, its partial log retained, and the guard corrected to allow loopback while denying external connections. The reported 864/110 passing results are the completed corrected run. No frozen evaluation or release scripts ran. Live-model quality, all-platform CI, production security, screen-reader use and independent human acceptance remain untested in this audit.
