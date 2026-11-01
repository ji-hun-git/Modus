# Professional terminology and whole-history retrieval — 30 October 2026

Owner-approved scope: professional terminology, source evidence and trusted reference links. This adds a terminology foundation to the active record service. It does not add medical interpretation, diagnosis, advice, clinical-model training or a new provider. The orbit and existing styling are preserved.

## Implemented

`backend/modus_entry/medical_terms.py` defines a versioned, code-owned vocabulary of **24 local concepts**: HbA1c, glucose, fasting glucose, LDL, HDL, total cholesterol, triglycerides, eGFR, ferritin, hemoglobin, white/red blood-cell counts, platelets, hematocrit, TSH, ALT, AST, creatinine, BUN, sodium, potassium, calcium, pulse and vitamin D. English medical names, selected everyday phrases and selected Korean aliases are available. The catalog is `record-terms-2026-10-30.1`.

The registry links to NIDDK's [A1C explanation](https://www.niddk.nih.gov/health-information/diagnostic-tests/a1c-test) and MedlinePlus pages for [glucose](https://medlineplus.gov/lab-tests/blood-glucose-test/), [lipids](https://medlineplus.gov/lab-tests/cholesterol-levels/), [eGFR](https://medlineplus.gov/lab-tests/estimated-glomerular-filtration-rate-egfr-and-gfr-tests/), [ferritin](https://medlineplus.gov/lab-tests/ferritin-blood-test/), [blood counts](https://medlineplus.gov/lab-tests/complete-blood-count-cbc/), [metabolic tests](https://medlineplus.gov/lab-tests/basic-metabolic-panel-bmp/), [TSH](https://medlineplus.gov/lab-tests/tsh-thyroid-stimulating-hormone-test/), [ALT](https://medlineplus.gov/lab-tests/alt-blood-test/), [AST](https://medlineplus.gov/lab-tests/ast-test/), [pulse](https://medlineplus.gov/ency/article/003399.htm) and [vitamin D](https://medlineplus.gov/lab-tests/vitamin-d-test/). Names/reference pages were checked on 30 October. These authored mappings, especially Korean and everyday phrases, have not received independent clinician/translator validation. Website terminology does not establish universal assay equivalence.

`history_retrieval.py` applies that vocabulary inside the already captured history. Examples:

| Owner's words | Eligible recorded names | Preserved distinction |
| --- | --- | --- |
| heart rate | Pulse / Heart rate | Dates, values, revisions and units remain separate |
| average blood sugar / A1c / 당화혈색소 | HbA1c / Hemoglobin A1c | Does not retrieve hemoglobin or glucose as equivalent measurements |
| fasting blood sugar / 공복혈당 | FPG / Fasting glucose / 공복혈당 | Does not assume generic glucose was fasting |
| iron stores | Ferritin / 페리틴 | Does not substitute serum iron or infer anemia |
| kidney filtering | eGFR | Does not substitute measured GFR or creatinine |

Aliases match complete recognized measurement labels. Unrecognized method/specimen-qualified labels remain unclassified. Other record kinds keep literal matching; a narrative mention does not become an inferred measurement, diagnosis or medication relationship. Exact original names remain in answers, charts and exports. No records are renamed, merged, recoded or converted.

Quoted phrases and source-title restrictions remain literal. Date, kind and unknown-word qualifiers are retained. “White blood cell count” is recognized as a name rather than an instruction to count records. Last/latest alias queries use the existing dated lookup, including ties, future-date exclusions and incomplete-date caveats. The model cannot invent aliases or replace the owner's bound search phrase. The code performs the mapping.

Broad phrases such as **blood sugar**, **cholesterol**, **kidney tests** and **liver enzymes** return a clarification before model/read-tool execution. Choices retain the rest of the original request, including quoted source restrictions and years. A choice is a way to narrow a search, not a claim that the selected test exists. No result still means no supported match in that scope, not absent disease or missed care.

Ask now exposes **How I matched your words**, with requested phrase → recorded labels and a general naming-reference link. Personal findings retain their separate Source buttons and original excerpts/downloads. The references are fixed HTTPS links with no record/query values, no automatic fetch, and no referrer. The UI rejects unexpected reference origins, embedded credentials and query strings. These references support names, not the owner's measured result.

Records, Documents, Trends and Brief share the same alias matcher when a recognized medical concept is present. They preserve pagination and provide the same ambiguity choices. Unknown field names retain the existing literal/substring search behavior. Trends continues to show actual named fields separately and explicitly charts the displayed page; terminology matching does not make different units interchangeable.

## Verification

Fresh authored diagnostic questions were run before editing retrieval and then against the revised service. The original **7/24** became **24/24** after correcting one diagnostic expectation: the standard seed also contains `LDL cholesterol`, which must remain eligible beside an authored `LDL` row. The original candidate output was retained as **23/24**; it correctly found those seed records. Applying the corrected criterion to the retained baseline leaves it at 7/24. This is a small development diagnostic with agent-authored labels, not held-out proof, clinical validation, a user study or a claim of general model superiority.

Final commands and checks:

- `.venv/Scripts/python.exe release/T8-retrieval/run_regression.py`: **929 backend tests passed**, 38 selected modules, one existing Starlette/httpx deprecation. The access guard recorded no protected-file access attempts. It blocks evaluation/held-out/secret reads and external networking.
- `npm test` in `entry/frontend`: **138 passed**. `npm run build`: TypeScript/Vite passed, bundle `index-hHBDcIgp.js`. The CSS bundle is unchanged from T7.
- New regressions cover aliases, cross-language records, exact quotations, unrelated tests, source/year qualifiers, clarification before provider calls, source-quote withholding, late availability, unknown dates/ties, medical-advice abstention, bound model arguments and reference-link safety. Artificial transport tests exercise the Meta adapter path without making provider requests.
- Browser imported/reviewed/saved a fresh ten-field synthetic CSV. “What is my latest heart rate record?” returned Pulse 72 bpm on 14 September 2025. Its Source button showed the original CSV row. The terminology disclosure linked to MedlinePlus Pulse.
- Browser “blood sugar” clarified HbA1c/glucose/fasting glucose. Selecting HbA1c retained `2025` and `source:"T8-medical-terms.csv"` and returned exactly the corresponding 5.4% entry. Records found Ferritin from “iron stores”; Trends found both FPG and 공복혈당 from “fasting blood sugar” while keeping them separately named.
- Downloaded original bytes equal the uploaded CSV. All previous T7 source/base-record/draft/receipt/amendment rows remain byte-for-byte equal in the copied stores. The browser adds one source with ten reviewed rows; the scale store has no new records. The earlier T7 correction still shows 75.00 with the original 70.00 excerpt. An availability cutoff immediately before the new upload excludes its result.

The first regression candidate had one new test that incorrectly expected an eligible dated measurement to disappear when its mixed-period source excerpt was withheld; it was corrected to assert the eligible numeric value remains while private excerpts/originals stay unavailable. The pre-existing Korean literal-only test now explicitly quotes its search phrase; a separate new test verifies the requested unquoted cross-language expansion. Another new test expected an injected-transport metadata field that the existing single-read adapter does not expose; the test now verifies injected calls and exact outputs directly. Earlier logs are retained, not relabeled as passed.

## Stress and limits

On the same copied **5,009-fact / 53-file** dataset, final requests alternating a 50-record page and offline literal Ask completed **122/122 HTTP 200**. Eight workers / 80 requests: p50 **479 ms**, p95 **638 ms**, wall **4.94 s**. The initial candidate also passed but reached p95 932 ms; avoiding unnecessary text normalization and skipping unrelated measurement labels reduced work. T7's prior 524 ms result is a different run with uncontrolled machine load; no performance improvement over T7 is claimed.

A separate eight-worker alias workload alternated paged “average blood sugar” search and offline Ask: **80/80 responses contained the expected three HbA1c records**, p95 **428 ms**. This is local synthetic engineering evidence, not production capacity certification.

Still missing: semantic embeddings/reranking, comprehensive terminology coverage, full clinical reference retrieval, clinician-reviewed mapping quality, standardized coding with method/specimen qualification, and robust interpretation of arbitrary conversational/relative/numeric filters. F04 is improved for the covered aliases but remains open for other everyday questions. The legacy three-concept BM25/LOINC path remains separate; its coding/quality claims do not transfer to this generic history path. Existing T7 cold-capture/full-export limits and T6 durable-recovery limits remain.

## Local artifacts and constraints

Private diagnostics, copied databases, logs and screenshots are in ignored `release/T8-retrieval/`. `before-questions.json` retains the original baseline; `after-candidate-questions.json` retains the initial diagnostic score; `after-verified-questions.json`, `service-verification.json`, `original-integrity.json`, `paged-http.json`, `regression-guard.json` and browser proof record the final outcome. `verification.json` binds the retained diagnostic comparison and running backend identity. No public preview/database was replaced.

The scale server on 8014 was stopped after verification. The guarded, credential-free development preview remains at **http://127.0.0.1:8013/** on the copied synthetic browser database, with its final Ask result left open for review. This is a local offline preview, not a release-gated deployment. The original 8012 workspace database remains unchanged.

No provider credits, evaluation/held-out reads/runs/changes, git commit or push. Full evaluation-writing release gates were intentionally not invoked under the owner's restriction. This milestone has no live Muse quality result or clinical-validation claim.
