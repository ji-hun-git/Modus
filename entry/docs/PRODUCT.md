# Modus record reconciliation

This entry helps a person review a record, inspect disagreement and replay what was available at an earlier time. It uses authored synthetic examples. Record reconciliation here means preserving and comparing evidence; it does not mean deciding which conflicting value is medically correct.

This document is the acceptance brief for the independent entry. Verification results belong in the README and generated reports; a design requirement below is not a claim that its test passed. The wider personal lifelong health-intelligence project remains intact outside this bounded source extract.

## A simple Home with working services

28 October owner correction: the five workspaces below describe retained capabilities, not equal primary destinations. The current experience is **Your history → Upload records → review each file → updated history**, with **Files** as the second primary destination. Measurement detail lives with the history; comparison and activity are secondary tools. [Product design v6](../../docs/PRODUCT_DESIGN_V6.md) supersedes the earlier navigation hierarchy. The supplied DNA archive was reviewed for product structure; no source code or assets were imported.

The upload queue selects up to ten supported files locally before any request. Each file has its own explicit read, review and save action, original evidence and receipt. A failed file can be retried or skipped; an uncertain save retains its exact submitted payload and cannot advance until resolved. Pending reviews are retained only in the open tab. The queue does not add new medical concepts or make unsupported documents understandable.

| Destination | Main question | Useful result |
|---|---|---|
| **Home** | What can I do with my records? | A working scoped question composer, actual record counts, recent sources and direct actions. |
| **Measurements** | Where are the recorded values over time? | Metric-specific dated values, exact units, source links and preserved disagreements. |
| **Records** | Where did this field come from? | Original source, proposed/reviewed fields, dates, units and preserved disagreement. |
| **Replay** | What records were available then, and what arrived later? | Two snapshots with the same measurement cutoff and explicit availability bounds. |
| **Changes** | What did this review add? | Actual commit identity/time and affected records; no invented resolution or completeness claim. |

Open on **Your history** with upload, dated measurement cards, recent files and a scoped assistant. The owner's supplied four visual references now define the visual system: charcoal canvas, layered inset charts, compact rounded panels, legible muted labels, monospaced numbers and restrained mint accents. Desktop navigation is a compact top bar; phone navigation stays at the bottom. The actual execution mode remains visible beside the assistant. **Demo data** holds the provenance explanation without repeated subtitles. [Product design v7](../../docs/PRODUCT_DESIGN_V7.md) supersedes the prior color/layout guidance; v6's review queue and human gate remain intact.

Keep the two clocks understandable across destinations, with detailed controls expanded in Replay. Use amber with text for a record disagreement, not a medical risk category. Factual measurement histories may show exact dated observations without inferred clinical trends, risk scores, reference thresholds or care recommendations. Do not connect incompatible units or choose one conflicting value. Progressive disclosure may move technical details into an inspector, but it cannot hide a required scope, provenance, review or commit decision.

## Plain-language measurement names

Use the everyday description first and the original medical abbreviation in parentheses throughout navigation, cards, filters and review: **Average blood sugar (HbA1c)**, **Kidney filtering (eGFR)** and **Cholesterol (LDL)**. These are display labels. Retain stored metric IDs, source wording, exact numbers and printed units; HbA1c is not converted to estimated average glucose, and eGFR is not a percentage or overall health score.

Terminology checked on 28 October 2026 against [NIDDK on A1C](https://www.niddk.nih.gov/health-information/diagnostic-tests/a1c-test), [NIDDK on kidney filtering tests](https://www.niddk.nih.gov/health-information/kidney-disease/chronic-kidney-disease-ckd/tests-diagnosis) and [CDC on LDL cholesterol](https://www.cdc.gov/cholesterol/about/ldl-and-hdl-cholesterol-and-triglycerides.html). This provides naming context, not personalized interpretation or thresholds.

## Data identity

The entry starts with **3 authored synthetic documents and 9 measurements** from `backend/modus_entry/seed.py`: HbA1c, eGFR and LDL cholesterol measured on 9 April 2018, 8 April 2021 and 20 October 2026. They are invented facts, not a real person's records and not Synthea output. These are clean-seed counts; the UI must use the scoped API counts because reviewed additions and date filters change the current view. The 2021 source title/date is 9 April, which must not replace its 8 April measurement date or imply a report-issued time.

The broader project separately contains an authored longitudinal fixture, a generated Synthea FHIR cohort, training-data preparation and evaluation material. They are not all one dataset, are not automatically loaded into this entry, and do not establish clinical validation. Training preparation does not mean a model was trained. The entry's first-release importer does not accept FHIR. No real personal health records or credentialed clinical dataset is used in this demonstration. See [data provenance](../../data/README.md).

Keep the invented-data explanation in **Demo data / About this demo** and the required upload confirmation. Remove the repeated synthetic subtitle from ordinary pages. Label local deterministic tools, actual local OCR and actual Meta requests separately at the interaction and result. A provider configuration badge cannot establish that a model request succeeded. Do not imply all operations remain local when an explicit Meta path is available.

## The principal flow

1. **Inspect an earlier replay.** “Measurements through” controls the event period; “Records available by” controls eligible reviewed evidence. Display the resolved server timestamp as well as the human date. “Now” becomes a captured instant.
2. **Add a synthetic document.** State actual extraction mode. Local parsing is not a model response. A configured Meta provider is not proof that a request succeeded.
3. **Review beside the original.** Preserve the proposal, source excerpt/page, printed unit and measurement date. Mark edited fields and excluded rows. Missing report issue time stays unknown. No model may commit or set availability.
4. **Add the selected rows.** Name the row count and persistence consequence. While pending, retain the request and prevent accidental repeat submission/dismissal. An uncertain outcome retries the identical draft and reviewed payload; a confirmed rejection permits correction.
5. **See exactly what changed.** Preserve the person's chosen historical replay. Offer **View what changed** and **Open updated view** rather than silently jumping to today. Duplicate confirmation identifies the original commitment and adds nothing again.
6. **Compare and carry the evidence forward.** The comparison freezes both availability views from one captured record set. A scoped export and eligible original links match those views. A file containing later measurements must not bypass the selected scope.

The demonstration uses the delayed 2021 source: measured on 8 April, reported on 10 April, available only after the new review commit. The earlier replay remains unchanged. Current availability reveals the 82-versus-96 same-day disagreement. Both original records remain visible; neither is declared false, and the app does not infer kidney condition or care quality.

## Evidence that is quick to check

An inspector shows value **with unit**, measured date, report-issued time or **Not recorded**, and **Available in Modus** with its provenance basis. Authored fixture availability must say it is authored; unknown historical availability cannot be inferred from the measurement. Preserve exact timestamp precision in API/download parameters even when the label is shorter.

Count documents and observations separately. Two observations from one source are “2 measurements · 1 document.” Equal readings from separate files preserve their separate provenance; equality alone does not prove specimen identity. Disagreements show both values, units and sources without a Resolve button until an audited resolution operation exists.

**How this result was made** is secondary disclosure: actual tool input/output, mode, model when used, request identity, captured scope and available timing/usage. It is not a simulated multi-agent control room or a display of hidden reasoning. Claim IDs provide navigation; support also depends on the tool computation and source facts.

## States that must stay truthful

| State | Required behavior |
|---|---|
| Empty temporal view | “No reviewed records are available in this view.” Keep dates editable. Do not imply no event occurred. |
| Scope change / failed refresh | Remove former evidence and query/export actions until matching data loads. Keep a scoped retry and preserve navigation/focus where feasible. |
| Out-of-order answer | Do not attach the old answer to new date controls. A retained saved answer carries its original scope. |
| No accepted extraction | Keep the draft/original and explain ambiguity or unsupported format. No empty successful commit. |
| Report date absent or ambiguous | Preserve unknown/raw text; never copy a measurement date or guess a timezone. |
| Provider failure | Show the failed request. Any local retry is explicit and remains labelled local. |
| Uncertain commit | Keep exact submitted values fixed; do not say nothing was saved. Resolve by idempotent retry. |
| Confirmed save, failed view reload | Keep the confirmed save notice separate; retry the view without committing again. |
| Historical original withheld | Explain the scope restriction; no unscoped download shortcut. Draft review and committed-original access are distinct. |
| Unsupported question | Give a bounded inability response and supported record questions; do not redirect to health advice within this entry. |

Draft edits held only in an open tab are not durable recovery. Do not promise resumption after reload or process restart without a server-supported draft/status contract. No general commit undo, source amendment or retraction exists in this milestone.

## Boundary and verification

The entry must be a separately runnable backend, frontend and record store with explicit source/route/tool allowlists. The public candidate must build with the broader clinical modules absent. Hiding UI or adding a disclaimer is insufficient. Excluded behavior includes diagnosis, risk scoring, normal/abnormal interpretation, treatment/medication recommendations, care-plan assessment and genetic interpretation.

Check review → commit → preserved replay → current comparison → evidence → scoped export end to end in an isolated store. Challenge direct API calls, unknown tools, forged scope fields, old draft download URLs, future-containing originals, duplicate commits and failed refreshes. Rehearse keyboard-only and narrow-screen use; no hidden navigation should receive focus. This finite verification supports the tested behavior, not clinical validation or general security certification.

The participant rules exclude AI medical/health advice and several generic applications. The organizer has not confirmed this concrete record-integrity entry's eligibility. The owner attests all first-party code was created after kickoff; third-party libraries/model work remain separately attributed. The project license is undecided. See [goals and prompts](GOALS_AND_PROMPTS.md) and [workflow choices](AGENT_WORKFLOW.md).
