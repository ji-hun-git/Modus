# Modus V6 — upload, review, return to your history

28 October 2026. The owner's new feedback is that the interface remains difficult: they want to upload a series of medical records and keep track of their health. This revision changes the product's information hierarchy and import flow. It is not another palette change, a claim of user validation, or an expansion of the contest entry into health advice.

## The job and the mismatch

The intended job is **bring my records together → check what was read → find my history again**. The current entry instead presents five equal workspaces, a large assistant, evidence counts, two date clocks and extraction methods. Those are implementation capabilities, not the person's natural sequence. V4/V5 improved the visual execution but did not remove this conceptual burden.

The broader build brief remains a lifelong personal health-intelligence product. The entry is presently a bounded record-reconciliation demonstration. Both statements must stay clear: simplifying navigation does not make the current schema capable of understanding any medical file, and preserving the contest boundary does not erase the broader product goal.

The owner supplied `https://github.com/ji-hun-git/dna`, then provided `dna-main.zip` after repository access failed. The designer read selected source directly from that archive with Python's ZIP reader, without extraction or execution: `README.md`, `HealthHomeConcept.tsx`, `RecordImportConcept.tsx`, `IntegratedHealthExperience.tsx`, `IntegratedRecords.tsx`, `HealthTimeline.tsx`, and relevant `globals.css` sections. This is a source review, not a rendered-screen, runtime or security audit.

DNA is an older Genome Companion Korea/앎 workspace. Its README marks real personal-data processing and hosted staging NO_GO. Useful UX principles are upload before configuration, a clear resume-review state, recorded values with their source/date on Home, grouping records by measured day and document, and optional source/version detail. The integrated flow models real server states and explicit candidate confirmation, but accepts only allowed synthetic PDFs; it does not establish broad medical-document understanding.

Do not transfer its prototype claims or placeholder behavior. `RecordImportConcept` explicitly checks file format/size/hash and then presents example fields unrelated to the selected file. `HealthHomeConcept` generates decorative month bars with fixed active months, while `HealthTimeline` uses a static demo dataset and evenly spaced record points. The large landing-page hero and prominent server/database vocabulary would also repeat Modus's current burden. Modus should retain actual extraction and evidence, then simplify their presentation.

DNA is a pre-event reference only. No source code, components, styling, assets or data from the archive are copied into the Modus contest entry. Independent implementation of the owner's desired workflow preserves the event-built source requirement; the reference is not evidence of current Modus capability or eligibility.

## Two destinations and one main action

**Your history** is the default destination. **Files** is the second. **Upload records** / **Resume review** is the primary action. Desktop and phone use the same two-destination model, with a reachable secondary **History tools** control. Keep the existing V4 neutral materials and typography; hierarchy, not additional decoration, carries this change.

History tools provides clear access to measurement history, **Compare earlier records**, **Activity**, date controls and scoped export where appropriate. Existing measurement/replay/activity pages can remain as secondary workspaces. They should have an obvious way back, without returning five equally weighted navigation choices to the main screen.

Do not erase the date model. Default current views can keep the controls collapsed. A historical or comparison view must show a persistent concise scope banner identifying its measurement period and availability boundary, plus an explicit way to return to the current view. Navigation and successful import must not silently change the selected historical scope. Exact captured timestamps remain inspectable.

## Facts before the assistant

The first screen should answer **what is already in my history?** and **how do I add more?** Place the actual upload entry first, recorded values/history next, and recent files nearby. Inventory counts become quiet supporting metadata rather than three large destination cards. Keep one page heading and avoid another explanatory slogan.

Use the existing exact observation data. A compact history section may surface each metric's latest measured date, its recorded value and unit, and source inspection, with a clear path to all dates. A latest-day disagreement must show the multiple recorded values; it cannot choose one as the person's current health state. Keep different units and unknowns separate. Do not round long values, add normal/abnormal colors, infer improvement, or fabricate trends, ranges or health scores.

The assistant is secondary to those facts: a compact entry for supported record questions, with the actual local/model execution state. Useful returned evidence can expand the surface. Do not make a large empty composer the dominant resting object or imply a model is running when only local tools execute. Keep trace details and technical provenance available on demand.

At 1280px, the initial view should contain upload, at least one dated recorded fact with a source action, and recent files. At 390px, upload and the start of useful history should appear before a large assistant surface. The exact layout may stack naturally; do not use a miniature analytics dashboard to force every fact above the fold.

## A series of files, reviewed one at a time

Use a bounded multi-file selection and serial processing flow. Selection can happen before extraction choice, but no file is sent or processed before the required explicit action and synthetic-data confirmation. Keep actual supported formats and size limits beside the selection control. Show understandable per-file state: **Selected**, **Reading**, **Review needed**, **Saved**, or **Could not read**. Counts reflect actual files and successfully committed measurements.

Choose a supported processing method deliberately. Local text parsing is distinct from local OCR, and both are distinct from sending a document to Meta. Explain the selected path briefly where it matters. Do not force a person to study three unavailable engines before selecting a file, silently switch to remote processing, or present a failed model call as a local success.

For each file, show the original evidence and extracted fields, preserve edit/exclude controls, then offer **Save N measurements**. Save requires the person's explicit reviewed selection. A completed file advances to the next file; a failed or unsupported file can be skipped without discarding other work. Avoid repeating the entire upload setup after every save.

Switching between files or closing/reopening in the same tab must retain each draft's edits and state. Do not claim recovery after reload or process restart unless it is implemented. An uncertain commit retains that file's exact submitted payload and is resolved through its identical idempotent retry. It must never be marked saved, replaced or re-read merely to make the queue advance. Duplicate confirmation remains distinct from a new addition.

Finish with the actual saved file/measurement totals and **Open history**. A person working in an earlier replay gets an explicit updated-view action; their earlier view is preserved. A file with no supported values is not a successful saved record under the current API. Document-only retention is a real capability gap, not a copy problem.

## Actual coverage and capability gaps

This table is based on the current entry types, import component and API contract. It is deliberately narrower than the full private application.

| Area | Implemented entry | Remaining capability |
|---|---|---|
| Record contents | Numeric HbA1c, eGFR and LDL observations with units, dates, source excerpts and review | Broad laboratory panels, vitals, narrative encounters, medications, imaging findings, wearable streams and genetic data are not general supported observation types. |
| File ingestion | CSV, explicit text and text-based PDF through local parsing; explicit available local OCR or Meta path for PDF/PNG/JPEG | JSON/FHIR is excluded from this entry. Arbitrary images, scans and layouts are not established as reliably understood. Live Meta quality remains unverified. |
| Multiple documents | Existing preview/commit is per file. V6 implementation target: a serial frontend queue over that bounded API. | This is not a transactional all-or-nothing batch or durable cross-reload inbox. Do not claim those properties. |
| Original files | Original retention and scoped downloads accompany reviewed committed measurements | Saving a document with no supported observations requires a separate document-only persistence design. |
| Personal history | Exact dated values, source inspection, disagreements and historical availability comparisons | No general clinical interpretation, diagnoses, risk scores or treatment advice in the contest entry. |
| Production use | Local synthetic demonstration with explicit review | Real-person identity, consent, production security/storage, integrations and intended-use qualification remain pending. |

Do not promise **any file understood**, **all your medical data supported**, **automatic health monitoring**, or **an AI clinician**. The honest near-term promise is a simpler way to add supported records, review their facts and revisit their history. Keep concrete format and content limits close to upload rather than scattering cautionary subtitles across the home screen.

## Preserve the broader product roadmap

All ten goals in `config/goals.json` and the original prompt-role dispositions remain intact. This revision serves G02's longitudinal evidence and G04's extraction review while improving the product tasks needed to test G07. It does not complete G03's live Meta work, G05's model experiment, G06's exact-variant work, G08/G09's submission/eligibility work or G10's real-data production requirements. G01's portability and bounded agent contract remain required.

Future breadth requires explicit engineering, not a generic upload label. The next domain work should separate original-document retention from extracted facts; then add a bounded observation catalog with preserved original codes, units, methods and dates, supported by new reviewed development cases. Narrative records, FHIR, wearables and exact-variant genetics need their own typed representations and measured extraction/retrieval behavior. Clinical interpretation belongs to the separately qualified broader product and remains outside the current contest entry. Do not open or tune against the held-out sets to accelerate this UI revision.

## Acceptance and independent review

- There are two primary navigation destinations. Secondary capabilities remain discoverable, keyboard-accessible and reversible.
- Home exposes the real upload action and useful recorded history before technical controls or a large empty assistant. No fabricated facts, chart data or health statuses appear.
- A mixed batch can preserve successful files and edited/excluded review rows while another file fails. Queue status and final totals match actual responses.
- Method changes never silently send data to a provider. Every committed file has an explicit reviewed selection. Uncertain and duplicate outcomes retain their established recovery semantics.
- Historical scope stays visible when active. Source, question and export actions remain guarded against stale or mismatched views; imports do not silently jump to now.
- At 390px, metadata remains readable, all primary targets are at least 44px, source actions and queue controls are reachable, and neither bottom navigation nor an open sheet covers required actions.
- Independent review uses actual desktop/phone screenshots of the resting history, selected batch, edited review, mixed completion and active historical state. The coordinator verifies real browser/API behavior in an isolated store. No fake events are inserted into the person's main store for presentation.

This specification follows the owner's direct feedback and source inspection. It is not evidence from an independent user study or proof that the resulting flow is optimal. New visual and interaction evidence should be appended after implementation.

## First implementation review

The independent designer inspected the actual desktop Home, desktop selected queue, desktop edited review, phone review and phone unsupported-file captures under `release/consumer-v6-*.png`. Home now leads with upload, then real dated values/source actions, recent files and a secondary assistant. The two primary destinations are clear. This addresses the previous information-hierarchy problem rather than only changing colors.

The captured phone review still has a substantive task burden: the expanded file queue, format limits, instruction panel and repeated draft header occupy roughly 600px before original evidence; no editable field is visible in the 844px capture. The requested correction is a compact current-file/position header during review, a disclosure for the queue and limits, one concise review/status block, and a reachable save action. The full queue remains useful during selection and when deliberately opened.

A second requested correction concerns acknowledged results: after a lost response and successful idempotent retry, one row says Saved while the summary leads with zero files saved and then says one already saved. The primary total should count the acknowledged files now in history; newly inserted versus already present remains explicit supporting detail. This must not alter commit semantics or pretend an uncertain result is confirmed.

The file named `consumer-v6-completion-mobile.png` shows the unsupported-file retry/skip state, not final batch completion. Its failure explanation and actions are visible. Final completion, phone Home and active historical-scope captures remain to be reviewed. The previously identified uncertain-commit header correction is owned by the implementation team and must be checked against the rebuilt application before delivery.

The designer then inspected `consumer-v6-home-mobile.png`, `consumer-v6-historical-mobile.png` and `consumer-v6-conflict-mobile.png`. The phone history presents upload and exact recorded values before the assistant. The dated-history banner clearly distinguishes the measurement cutoff from record availability and offers **Return to current**. The disagreement card retains the full `80.1234567` and `96` values, their units, separate source titles/actions and an explicit difference marker. No additional visual correction was requested for these states. The Home and conflict images are scrolled captures, not fresh top-of-page screenshots. The revised queue review and final completion remain outstanding for independent visual inspection.

## Final independent visual acceptance

The designer inspected the final rebuilt captures `consumer-v6-review-mobile-final.png`, `consumer-v6-review-desktop-final.png` and `consumer-v6-completion-mobile-final.png`, associated with CSS `index-CSHS5Ydk.css` and JavaScript `index-DSaXkjw_.js`.

The compact review resolves the task burden identified above. The phone shows current file/position, a collapsed **Show files** control, actual extraction mode, editable metric/value/unit/date, source inspection and **Save 1 reviewed measurement** together within the captured viewport. Original evidence remains reachable below the fields with a return action. Desktop keeps original evidence and editable fields side by side, with the save action visible. No clipping or unreadable fact was visible in these captures.

The final completion screenshot correctly leads with **2 files in your history**, then distinguishes **2 already saved · 1 skipped**. It explicitly states that no measurements were added again and the existing review is unchanged. **Done** and **Start another upload** are visible. The file list reflects the individual acknowledged/skipped states; it does not turn an unresolved or failed file into a saved one.

Independent visual acceptance is complete for the reviewed V6 states. No further visual changes are requested. The coordinating agent separately verifies source/back focus, minimum targets, mixed-file outcomes, uncertain-response recovery, historical scope preservation and the full release gate. These screenshots establish observed layout and copy quality, not a user study, production readiness, clinical validity or broad medical-file support.
