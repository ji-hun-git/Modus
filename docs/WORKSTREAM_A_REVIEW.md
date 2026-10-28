# Step A — record contract and answer audit, 28 October 2026

Requested order: fix the reported defects and report before broader records, native desktop work or model execution. Two independent engineering audits reproduced the current behavior. The owner notes referenced an older build; pre-step checks were 667 backend / 552 entry / 20 frontend tests.

| Reported issue | Current reproduction | Change |
| --- | --- | --- |
| Commit 422 when posting preview observations | Raw preview includes server-owned source/availability fields and correctly fails strict validation. Current UI already projects the five editable fields and completes review/save. | Added HTTP regression: invalid raw preview causes no writes; reviewed projection saves its edit while retaining original provenance; duplicate retry is idempotent. Keep strict validation. |
| Double synthetic confirmation | Current queue shows one acknowledgement. Preview and commit independently require its explicit true flag. | Preserved both server checks and single user acknowledgement; no repeated prompt reproduced. Browser rehearsal covers one acknowledgement through save. |
| Boilerplate answer | API returned the same generic success sentence; conflict text omitted values. | Answer now joins exact selected typed claims; conflict sentences name the measurement and exact competing values/units. No model-authored medical text is introduced. |
| Stale known_at gives false no-disagreement | A historical snapshot correctly excludes a later arrival. Hidden answer dates made that negative easy to overread. | Negative findings state their eligible count and exact scope. Every answer exposes measured/available dates and an explicit Use latest files action. Historical views never auto-refresh. |

## Evaluation contract

The prior grader hardcoded the generic sentence and old conflict text. Its legacy-v1 behavior remains available. Current workflow plans explicitly declare claims-v2, which requires exact trusted typed claims, independently authored expected IDs/evidence/tool/status, the exact selected-claim answer and exact captured scope. Negative tests cover changed values, added prose, wrong scope/evidence/status/tool and irrelevant claims. Mixed legacy/current comparisons are rejected until a reviewed cross-format protocol exists. No frozen baseline, corpus label or held-out file was altered or rescored. Prior dev 8/8 routing and 4/4 parser+OCR remain prior-version development results, not a score for this change. Old live plans are stale after the backend source change.

## User-value gap still open

The actual extraction scope remains three metrics. Everyday UI names are not all accepted free-text routing aliases; suggestion buttons still send canonical supported questions. Mixed record types, folder/ZIP intake, Today, lifetime timeline, native installation, real-person data readiness and real model comparisons remain in the expansion plan. No architecture or model is described as best/SOTA based on these software fixes.

## Verification

Commands: `python scripts/check.py` (includes backend pytest, scripts/evaluate.py, document and temporal checks, both frontend builds and check_entry.py). Passed **684 backend / 569 entry / 20 frontend tests**, deterministic 10/10, local document 6/6 with two unsupported image cases, full temporal 10/10 and entry temporal 6/6/routing 5/5. One existing Starlette/httpx warning remains; no suppression or dependency change. Log: release/step-a-gate.log.

Actual browser verification reproduced a 2-document/6-measurement historical negative with visible dates; **Use latest files** kept the 2021 measurement cutoff and updated to 3/7; the new answer named both 82.0 and 96.0 with the correct medical label and its source action opened both originals. An initial UI assertion expected integer spelling (82/96); that assertion mismatch is retained separately. The original numeric values are unchanged. Evidence: eval/step-a-browser.json and release/step-a-answer.png.

The reference-design rehearsal passed 17 browser assertions, including phone review/explicit save in an isolated synthetic store, and desktop/tablet/phone layouts. The review store advanced from 6/12 to 7/13 only after the explicit update action. The main store remains 4 documents/10 measurements; question audit events were added. This is Windows browser verification, not native installation or macOS qualification.

Line counts: the new service design stylesheet was split from 593 lines into separate base/responsive files; AnswerScope is a 35-line component. The inherited 3,633-line base stylesheet and 800+ line application/import components remain cleanup work. The no-large-file target has not been achieved globally.

Checklist delta: 0 boxes; **6/17 remain complete**. No live calls, **$0 model cost**, no held-out scoring; no new dev comparison. Older live plans must be regenerated. Jason still owns API access/credits, license choice, gold-label review and eventual signing access. No secret is requested in chat. No live model request or credit expenditure is authorized or performed by these offline checks. No macOS/native/light-theme screenshots exist because those products have not been built. Reference-design browser evidence is eval/reference-v7-browser.json.

Fresh package: release/public-record-entry-step-a-20261028, 287 manifest entries including the production build. `npm ci --ignore-scripts`, then `python scripts/check_entry.py` inside the extract: **567 passed, 2 expected compatibility skips, 20 frontend tests and production build passed**. Existing root/V6 public source and Git staging are preserved. This new extract has not been committed or published.
