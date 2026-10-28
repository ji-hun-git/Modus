# Ontology and record retrieval development evaluation

28 October 2026. This independently authored development experiment compares the new mapper/retriever with the explicitly frozen pre-feature source. It is not a held-out assessment, clinical validation, statistical generalization claim or SOTA comparison. No provider request or model download is part of the experiment.

## Freeze before candidate results

The evaluation author wrote 24 synthetic development cases and their deterministic expected IDs/mapping dimensions before executing or inspecting candidate results. Implementation agents were instructed not to read the new fixture or grading labels while building. No private old evaluation corpus, held-out input, generator or annotation was opened, probed or enumerated for this work.

| Frozen artifact | SHA-256 / identity |
|---|---|
| `data/development/ontology_rag_v1.json` | `f8d0aee72b2b6053f688b600321c04bcbdc8a895d84fa20c5ec6718b1b7a9d5d` |
| Grading contract v1 | `0515a49e1f1edf8831a50dd1a67e1fe90a97ac61bbbc6084a67b383b75ec9e87` |
| Harness before first candidate execution | `b4bac47a44ab1533c1e6aa2aac043045148071523f151761a249703970b6e68e` |
| Named pre-feature protocol | `9a836ea436894fa59baf293abc1501c2787d2d26837a49f9fa338656271e188a` |
| Named pre-feature source identity | `a42cf926ba2ba66b64c69b1d430b5f2afecac8c7c46f043486e1993d2931ca92` |

Text fingerprints normalize CRLF to LF. The fixture and protocol fingerprints are enforced by the runner. Each report retains its grading contract, harness identity and actually loaded source/configuration hashes. The plan-only validations passed with 24 scheduled cases, no candidate imports, zero provider requests and no blocked access attempts. Nineteen artificial harness regression tests passed before the first candidate run. These tests exercise the grader and access boundary without reading any real private corpus.

Before any candidate execution, the harness changed from `f6764e7ed6f070dbd189108bc69edf3a257061486f387d6f5e737b81021f24da` to the recorded current identity solely to add an explicit candidate-only public-extract mode and its no-archive-access regression. The fixture, gold and grading contract did not change. The full pre-feature research snapshot is intentionally excluded from the bounded public entry because it contains broader application modules.

## Inputs and expected outcomes

The fixture contains six explicitly invented source documents and nine observations across HbA1c, eGFR and LDL. One late source conflicts with an earlier eGFR observation. An LDL example uses mmol/L while other LDL examples use mg/dL; the suite never converts their values. One source excerpt contains instruction-like text solely to test that imported content remains data.

Twelve mapping cases cover English/Korean concept terms, exact LOINC calculated/direct/HPLC dimensions, wrong code systems, conflicting concepts, conflicting methods, missing units and a property/unit mismatch. Twelve retrieval cases cover synonyms, source titles/quotation, late availability, measurement cutoff, exact printed unit, disagreement evidence, untrusted source text, unsupported metrics and advice/injection abstention. Nine retrieval cases have nonempty expected evidence; three require completed empty retrieval.

The author independently checked the exact coding dimensions against [LOINC 13457-7](https://loinc.org/13457-7/) for calculated LDL mass concentration, [LOINC 18262-6](https://loinc.org/18262-6/) for direct-assay LDL mass concentration, and [LOINC 17856-6](https://loinc.org/17856-6/) for HbA1c by HPLC. These references establish coding distinctions, not clinical interpretation or conversion rules. An exact code's dimensions are separate from its coarse Modus metric category.

Each method receives identical authored source/observation inputs, explicit event and availability bounds, a fixed capture time and limit 5. The harness uses the respective source version's actual `RecordStore` and `capture` projection. It records whether projected evidence and resolved bounds match across methods; a source-bundle-derived scope ID may differ. Gold fields are stripped from worker payloads and never passed into the application modules.

## Comparators and fairness limits

| Method | Actual executed behavior | Interpretation |
|---|---|---|
| Frozen mapping | Named pre-feature `metric_key` for terms and `parse_fhir` for coded observations. | Tests actual old coarse recognition/parser acceptance. It never returned a formal mapping status or method/property/specimen object. Missing dimensional output is coverage absence, not an execution error or a fabricated old API. |
| Frozen retrieval | Actual old `offline_route` followed by its permitted typed-tool `dispatch`; normalize returned claim evidence IDs in their original order to top 5. | This was a bounded router/inventory/conflict tool workflow, not a ranked RAG endpoint. An unsupported title or Korean query is recorded as old-router abstention. |
| Plain lexical | Independent token-overlap ranking over scoped metric, unit, source span and title; deterministic ID tie-break. | A deliberately simple reference without ontology expansion, unsafe-query filtering or conflict expansion. Its failure on advice/injection queries is visible and should not be presented as a production design recommendation. |
| Candidate mapping | `resolve_concepts` and `resolve_codings` in `modus.ontology`. | Grades the declared mapping status, coarse category, printed-unit identity and expected exact dimensions. |
| Candidate retrieval | `retrieve_record_evidence(view, query, limit=5)` in `modus.record_retrieval`. | Grades the IDs and factual hit fields, not a free-text response or hidden reasoning. |

The frozen source is read only through its exact manifest: protocol plus 31 named files under `evaluation/ontology-rag-baseline-v1/source`. All hashes are verified before copying those files into a temporary source tree. The old code then runs in an isolated subprocess from that copy. The runner never invokes an archived evaluation CLI or a split validator. It never enumerates the parent evaluation directory. Candidate and lexical runs are separate isolated subprocesses; network operations are blocked.

## Grading

- **Comparable mapping outcome:** exact concept set for terms, or exact coarse metric plus whether the result is qualified. Candidate qualification means mapping status `resolved`; old parser qualification means it returned a row. This compares observable acceptance behavior while retaining the interface difference.
- **Mapping contract and dimensions:** candidate status, unit identity and expected code dimensions are checked separately. Report expected, available and correct dimensional fields; missing output and runtime errors stay in their scheduled denominators. The old mapper's absent dimensions are labelled explicitly.
- **Retrieval exactness:** returned unique observation-ID set equals the frozen relevant set at k=5. No desired ordering is invented when multiple records are equally relevant.
- **Precision/recall:** record per-case precision and recall, macro values across all 12 cases, and answerable-only recall across the nine positive cases. Correct completed empty results receive abstention credit on the three negative cases. Errors receive zero credit, never successful-empty credit.
- **Factual support:** every returned observation/source ID, metric, value, exact unit, measured date, source title/span, availability and report-issued time matches the scoped input. This is factual hit support, not proof that arbitrary generated prose is supported.
- **Temporal and scope safety:** returned scope equals the captured input scope; unknown/out-of-scope IDs and future event/availability evidence are leaks. Duplicates and exceeding top-k also fail exact support.
- **Complete accounting:** scheduled, completed and error counts remain visible. Retain raw outputs, returned routes, warnings, support failures and per-case timings. Local timings are observations, not a controlled latency comparison.

## Access protection and regression checks

The path tripwire blocks open, stat/lstat, access, directory enumeration and readlink attempts for protected evaluation paths other than the exact named manifest files. It also denies held-out directory components. Paths are checked lexically before any resolve/probe. Python audit hooks cover import/file-open paths that could bypass normal wrappers; subprocess network audit blocks connections. Artificial tests verify these cases, fixture/protocol/source fingerprint rejection, unsupported or future evidence, changed scopes, duplicate/over-limit hits, error-vs-abstention accounting, dimension denominators and removal of gold from runtime payloads.

This is a bounded regression mechanism, not an OS sandbox or a general security certification. A blocked attempt is reported explicitly. The experiment's trusted orchestration code must still be reviewed; it does not accept model-issued paths, commands or URLs.

## Run and retained evidence

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_ontology_rag.py --plan
.\.venv\Scripts\python.exe scripts/evaluate_ontology_rag.py

# In the public extract, which intentionally omits the broader baseline archive:
.\.venv\Scripts\python.exe scripts/evaluate_ontology_rag.py --candidate-only
```

From `backend`, run the artificial harness tests with `..\.venv\Scripts\python.exe -m pytest tests/test_ontology_rag_evaluation.py -q`.

Candidate-only mode reads no baseline protocol or source, sets `comparison_mode` to `candidate_only_no_baseline`, and reports only current-source performance on the frozen development gold. It cannot establish an improvement over old code. Default comparative mode still requires the named archive and fails honestly when it is absent; it does not invent a baseline or silently switch modes.

Every execution writes a unique timestamped `eval/ontology-rag-development-v1-<timestamp>.json`. `eval/ontology-rag-development-v1.json` is only the latest-result copy; earlier raw outputs, including initial failures, remain in their unique files. A follow-up after implementation changes is development tuning. Do not call these cases held out or change the gold/grading rules to fit a failed candidate. If a real harness defect needs repair, preserve the first report and record the changed harness identity and reason.

## Initial measured result

The first comparative execution is retained at `eval/ontology-rag-development-v1-20261027T162044958823Z.json`. Its UTC timestamp falls on 27 October; this review is dated 28 October in Korea. Both implementation owners reported a code freeze before the run. The fixture and grading contract were unchanged. All methods completed their scheduled cases with zero runtime errors, zero provider requests and no blocked private-corpus access attempts. All 12 retrieval inputs had matching resolved bounds and projected source evidence across methods.

| Mapping outcome | Frozen coarse mapper/parser | Initial candidate |
|---|---:|---:|
| Comparable concept/category + qualification outcomes | 4/12 | 12/12 |
| Exact declared mapper contract | Not an old capability | 12/12 |
| Expected method/property/specimen dimensions available | 0/11 | 11/11 |
| Expected dimensions correct | Not reported by old API | 11/11 |
| Runtime errors | 0/12 | 0/12 |

The formal mapping contract is new, so its absence in the frozen parser is not described as an execution failure. The comparable 4/12 → 12/12 result measures the shared concept/category and accepted-vs-unqualified outcomes defined before execution; dimensional coverage is a separate added capability.

| Retrieval outcome, k=5 | Frozen router/tool evidence | Plain lexical | Initial candidate |
|---|---:|---:|---:|
| Exact relevant ID set | 7/12 | 3/12 | 8/12 |
| Macro precision across 12 cases | 58.3% | 45.0% | 82.5% |
| Macro recall across 12 cases | 58.3% | 66.7% | 100% |
| Recall across 9 answerable cases | 44.4% | 77.8% | 100% |
| Correct completed abstentions | 3/3 | 1/3 | 3/3 |
| Factually supported returned hits | 8/8 | 22/22 | 23/23 |
| Temporal leaks | 0 | 0 | 0 |
| Returned scope matches input | 12/12 | 12/12 | 12/12 |
| Runtime errors | 0/12 | 0/12 | 0/12 |

Four candidate retrieval cases failed exact relevance despite complete expected-evidence recall:

- **r03, named source:** both expected source observations were returned, alongside an unrelated conflict companion and additional rows sharing a generic title word.
- **r04, quoted source:** the intended late source was returned with a nonmatching source's conflict companion. A precise source constraint and a conflict-expansion policy need a deliberate boundary.
- **r08, disagreements:** both disagreeing values were retained, but a nonconflicting older eGFR observation was also returned.
- **r09, source containing an untrusted footer:** the correct source was returned without following its embedded instructions, but other records sharing one title token and their companion were included.

These are initial precision failures, not unsupported-value, missing-evidence or temporal-access failures. They remain in the exact-case and precision denominators. Subsequent fixes are development tuning against these disclosed outcomes. The initial report must remain unchanged, and fixture/grading changes must not be used to make these failures disappear. This small authored result does not establish clinical utility, held-out performance or a generally superior retrieval architecture.

## Development-tuned result and independent comparison

The implementation owner ran the revised candidate after generic precision fixes and retained `eval/ontology-rag-development-v1-20261027T163445624357Z.json`. This reviewer compared both reports without rerunning the experiment or changing code, fixture, labels or grading. The first report still contains its four initial precision failures.

The following comparison checks passed:

- Fixture, grading contract, harness and baseline source identities are identical between reports. Recomputing the current fixture/harness text hashes and the canonical stored grading-contract hash reproduces those recorded identities.
- The frozen baseline's loaded source hashes and every summary result are unchanged. The independent plain-lexical summaries are also unchanged.
- Scheduled case IDs and all denominators match. Each comparative run schedules 24 baseline cases, 12 lexical retrieval cases and 24 candidate cases; candidate mapping remains 12 cases and retrieval remains 12, including nine answerable and three abstention cases.
- Every retrieval case has matching captured bounds and source evidence across methods in both runs. The second run reports no errors, provider requests or blocked private-corpus accesses.
- Candidate fingerprints change for `backend/modus/record_retrieval.py`, `backend/modus_entry/agent.py`, `backend/modus_entry/tools.py` and `entry/prompts/records.md`. The change is in the candidate, not the frozen baseline or grading rules.

| Candidate outcome | Initial | After development tuning |
|---|---:|---:|
| Comparable mapping outcome | 12/12 | 12/12 |
| Exact mapper contract | 12/12 | 12/12 |
| Expected dimensions correct | 11/11 | 11/11 |
| Exact retrieval ID set | 8/12 | 12/12 |
| Macro precision at 5 | 82.5% | 100% |
| Macro recall at 5 | 100% | 100% |
| Answerable-case recall | 100% | 100% |
| Correct abstentions | 3/3 | 3/3 |
| Supported answer hits | 23/23 | 16/16 |
| Scope matches | 12/12 | 12/12 |
| Temporal leaks / execution errors | 0 / 0 | 0 / 0 |

The retained baseline remains 4/12 for comparable mapping and 7/12 for exact retrieval; plain lexical remains 3/12 exact retrieval. The final 12/12 retrieval result is explicitly **development-tuned**, after the first run exposed the precision failures. It is not a fresh independent test result.

The revised retriever narrows named/quoted source matches and disagreement intent, and separates nonmatching conflicting observations into `conflict_context` rather than treating them as answer hits. That preserves disagreement context while keeping the query's relevant-hit set precise. The frozen scorer evaluates answer hits; it does **not** automatically grade this newly added context field. As a separate output review, this reviewer inspected both returned context observations in r03/r04: they match their scoped source IDs, values, units, measured/report/availability dates and excerpts, and are labelled context-only with a source-filter warning. This limited inspection does not extend the frozen benchmark's safety coverage to every possible context-expansion case.

Current raw-file digests, recorded for future integrity checks:

| Retained report | SHA-256 of raw bytes |
|---|---|
| `ontology-rag-development-v1-20261027T162044958823Z.json` | `987257ef71ede38e3e71da9555fd6a8133fbe657f9421e18ae1bb0e737f06bc0` |
| `ontology-rag-development-v1-20261027T163445624357Z.json` | `dced96a6b36c88566a901b04adc312e6effd96ef34fd3046f3f359ecbd563b59` |

Remaining evidence gaps include independently curated unseen terms/layouts, broader terminology, richer unit/method ambiguity, multilingual relevance beyond these examples, adversarial context-expansion coverage, and actual provider performance. Software gates, browser integration checks and old workflow/parser regressions are separate evidence owned by the delivery workstream. No real-world medical accuracy, clinical usefulness, held-out generalization or SOTA status is established by this small development suite.

## Final runtime regression check

A full backend gate exposed an overbroad date-language guard: the established arrival question “after this date” must remain valid when its comparison is already server-bound. Independent review also found negated source/unit filters were being treated as positive filters. Both received artificial regressions and were corrected without changing the development fixture or grader. The final runtime is retained in `eval/ontology-rag-development-v1-20261027T163848580055Z.json`: mapping 12/12, retrieval 12/12, supported hits 16/16, abstentions 3/3 and zero temporal leaks. Earlier attempts remain unchanged. All 637 backend tests passed on this runtime before the subsequent frontend redesign.

The final existing-suite comparison is `evaluation/comparisons/20261027T164024Z-0b24fef81c`: frozen routing 3/8 versus 8/8 (24/24 candidate attempts), parser 1/4 versus 2/4 (6/12 candidate attempts). The earlier run in this milestone also measured actual parser/local-OCR at 4/4 (12/12 attempts), retaining three failed primary inferences; that report keeps its pre-precision source identity. These are separate development protocols, not held-out performance.
