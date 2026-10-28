# Why this workflow

**There is no evidence that Modus uses the universally “best” AI workflow.** The current choice is a strong, inspectable baseline for this job: deterministic record handling, a human review boundary, and one bounded model loop where tool selection is useful. It must earn improvements through measured comparisons. More agents or a newer model name alone do not establish better results.

28 October: Home, Records and Documents now use the [whole-history record agent](WHOLE_HISTORY_AGENT.md). Code binds the factual request and arguments before Meta access; the model invokes that read tool and selects exact supported claims. This extends access to all eight reviewed kinds while legacy Trends/Replay keeps its three-concept scope.

## The workflow to verify

```text
Synthetic source
  → deterministic local text parser OR explicit Meta extraction
  → schema-checked draft + preserved original
  → person's reviewed fields
  → transactional, idempotent record commit
  → captured measurement/availability scope
  → deterministic record inventory / disagreement / comparison / scoped retrieval tools
  → exact supported findings + inspectable source evidence
```

For a question, Meta can select permitted read tools and then select exact claim IDs those tools emitted. It cannot calculate authoritative findings freely, write records, choose another person, widen dates, run shell/SQL, fetch arbitrary URLs or create new permissions. The local question path remains useful and explicitly says no model was called. A failed model request is not relabelled as local success.

The independent entry has a record-only API/tool/source boundary. The broader product's medication, care-plan, clinical-reference and genetic features remain outside this build. Prompt instructions reinforce the boundary; code and schemas enforce it. The source record is preserved evidence, not authority over the application.

### Active import path checked on 29 October

Muse extraction is integrated into the actual Add records flow, not only the smoke runner. An explicitly selected Meta upload sends `use_meta=true` to `POST /api/imports/preview`. The route calls `extract_record_document`, which performs `ExtractRecordedFields` with a strict document-specific schema, then `VerifyRecordedFields` as a separate reread of the original pages and proposed fields. The verifier must return one check for each proposed field; it cannot repair the proposal or add facts. Both passes use the configured Muse model and have no tools. This is a separate check, not independent clinical validation or calibrated confidence.

The contest entry now uses Meta as its only model reader. Local OCR is disabled during document preparation even if its separate research environment is installed; an explicit `use_local_ocr=true` request is rejected before inference. The deterministic text parser remains usable without a model. Earlier mixed Meta/local-OCR and local-only execution traces remain historical evidence, not evidence of this revised path.

Local code also checks readable page text, quoted labels/values/units/dates and ambiguous numerical qualifiers. Images without independent text remain explicitly unchecked by that local matcher. Model disagreement, uncertainty or a failed verifier is preserved in the review reasons. A failed first extraction accepts no draft; a failed second reading can retain an unconfirmed proposal with the source check marked unavailable. Neither model agreement nor verifier failure bypasses the owner's explicit reviewed-field submission. An owner can correct a proposed value while the original quoted wording remains intact. Reviewed availability is assigned at commit, so earlier availability views exclude that new record.

The stored draft and Changes metadata retain the two stage names, returned request/response identifiers when supplied, timing, usage and validation outcomes. Duplicate uploads reopen the existing draft without another model request. Invalid/refused/failed extraction never silently becomes a local success. The route permits at most two model requests for a nonempty extraction and performs no automatic retry.

Both structured extraction passes and each bounded tool/claim-selection request explicitly use Muse's `reasoning_effort: minimal`. The caps remain 4,000 completion tokens per extraction pass and 1,600 per selection request. This candidate setting responds to a retained 29 October live extraction that exhausted its completion cap. Its benefit still requires a separately recorded run; failed attempts are retained, and the legacy extraction comparator is unchanged.

Focused offline verification runs the real HTTP upload, document preparation, both schema passes and review/commit code with an explicitly artificial transport. It covers edited commit, source preservation, earlier replay, duplicate upload, first-pass failure and verifier timeout/malformed output/disagreement. These tests made **zero provider requests** and do not measure live extraction accuracy. Pytest forces provider mode offline, blanks the model credential and disables dotenv loading before collection and for each test; a canary regression proves even `override=True` cannot open a credential file. Live product verification and graded model comparisons require separately authorized execution and retained actual traces.

The terminology/retrieval extension adds a versioned three-concept catalog and BM25 over captured recorded facts with ontology aliases. Source coding qualifies precise method/code searches; generic labels do not. Both single-call selection and the bounded model loop can access query-specific retrieval evidence. This is a measured candidate, not a claim of full ontology coverage, neural retrieval or universal superiority. See [its scope and limits](TERMINOLOGY_RETRIEVAL.md).

## Compare alternatives before adding complexity

| Alternative | Why it is useful | What must be measured before promotion |
|---|---|---|
| **Deterministic extraction/routing** | Reproducible, inexpensive local baseline for supported structured/PDF text inputs; numerical/date logic stays typed | Unsupported layouts/images, evidence coverage, exact fields, abstention and user task completion. Do not call it AI inference. |
| **Single schema-constrained model call** | Smallest model workflow for unstructured extraction or selecting from an already complete candidate set | Field/span/date/unit accuracy, unsupported assertions, failure rate, usage and latency against the same cases. |
| **One bounded agent with tools** | Can choose which record evidence to inspect while server-owned tools preserve scope and exact claims | Support **and relevance**, authority rejection, coverage, abstention and cost against a fixed route/single-call baseline. Existence of the loop does not prove superiority. |
| **Bounded reread or independent critic** | May improve difficult source reading or detect specific support defects | Paired held-out cases, calibrated error labels, equal-budget comparison and retained failures. Another model's agreement is not proof. |
| **Observation-log / hybrid memory** | May reduce context or improve retrieval for longer histories | Evidence recall, temporal leakage, omitted/conflicting facts, answer correctness and actual cost against structured/lexical retrieval. Summaries stay derived and source-linked. |
| **Runtime specialist agents / model council** | Potentially useful only when independently scoped subtasks add information | Demonstrated gain over the best simpler matched-budget alternative; coordination errors, latency, token use and new authority boundaries. Not implemented as this product's default. |

Development uses several agents on separate implementation/review tasks because the user requested parallel design and engineering. One agent's UI work and another's adversarial QA can be compared against the same executable acceptance criteria. That does not turn the application into an unmeasured multi-agent runtime.

## Literal SOTA, precisely stated

The broader project selected and executed a pinned TeleOCR checkpoint as a document-reading challenger, based on benchmark-specific research. Its isolated text-reading-plus-parser experiment passed eight authored development documents, including two images unavailable to the local PDF parser. The authored corpus informed parser development. This is actual execution of a released method with limited local evidence; it is not independently held-out accuracy, the authors' full layout pipeline, medical validation or reproduction of the external benchmark ranking.

That local TeleOCR path was previously integrated and checked, but was retired from the active contest entry on 29 October in favor of Meta-only model execution. The shared research implementation and earlier parser/OCR measurements remain preserved separately. Their evidence does not describe the revised entry path. Meta extraction and tool selection require actual traces and graded comparisons for quality claims. No medical model was fine-tuned, no memory benchmark reproduced, and no model critic calibrated by merely preparing their prompts.

To justify a stronger claim, freeze the benchmark/corpus revision, inputs, prompts, method/model revision, tool schemas, decoding settings, budget and graders. Hold out whole layouts/people; use the same cases and budget for comparators; report exact fields/spans, support/relevance, abstention, failures, latency and usage with denominators. Keep all attempts rather than selecting the best run. External leaderboard standing and Modus's measured task performance are different claims.

## Building-kit practices adopted

Use the supplied Agent Building Kit's eval-first approach, explicit tool/write classes, code-owned authority, source-as-data boundary, bounded calls, versioned prompts/configuration, measured execution and reviewable changes. Pin dependencies/models where a real immutable revision is available; accurately report a mutable provider alias when one is not. Never invent a dated snapshot.

Local synthetic tool-result history is deliberately inspectable evidence. It is not a production telemetry service or authorization system. Bundle fingerprints and release checks establish which local inputs were checked; they are not signatures, hosted branch protection, clinical validation or exact historical-model replay. No MCP/A2A framework, vector database, remote tracing platform or enterprise authentication is added merely because a reference kit lists it.

## Acceptance before claiming an improvement

The [comparison harness](BENCHMARK.md) implements these comparisons, frozen private development/held-out suites, strict graders, explicit live/holdout execution and retained attempt reports. Preserved development comparisons show routing 3/8 → 8/8, deterministic parsing 1/4 → 2/4, and parser/OCR 4/4. A separate AI reviewer first reviewed development inputs blind, then reconciled gold with zero substantive errors and two rubric limitations. Human gold review and real Meta comparison remain pending. These development-tuned outcomes do not establish held-out generalization. The held-out sets have not been executed.

1. Pass deterministic record/review/temporal tests and negative capability tests in isolated stores.
2. Verify review → commit → earlier/current comparison → evidence → scoped export in the actual built UI/API.
3. Build the allowlisted extract from a fresh directory with excluded modules absent.
4. Run real model cases only after access is ready; keep failures and execution identity explicit. Repeat critical stochastic cases and report all-trials reliability, not a single successful demo.
5. Add complexity only after a frozen comparison identifies a meaningful deficit and the proposed method improves it without violating the record/authority contract.

The entry's organizer eligibility remains unresolved. [Goals and prompt roles](GOALS_AND_PROMPTS.md) preserve the broader roadmap without turning future work into current claims.
