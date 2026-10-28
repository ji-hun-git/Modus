# Prepared live development comparisons

Rechecked 28 October 2026 after the consumer-flow revision. The UI changed; the backend/model source and plan IDs remain unchanged from the prior preparation. **No provider request has been made.** These plans use only development cases. The held-out inputs, annotations and previews remain untouched. Prior plans remain archived; provider telemetry/validation changes source identity without rewriting the frozen baseline or its results.

The candidate stays on `muse-spark-1.3` Standard with the existing fixed official endpoint. Meta's current documentation describes its chat, tool-calling and document capabilities; account access is still unverified. The model name is a mutable alias, so actual returned identity and usage must be retained. The current model page lists Muse Wonder unavailable in South Korea; no access workaround or silent model substitution is proposed. [Model availability](https://dev.meta.ai/docs/models), [Chat Completions](https://dev.meta.ai/docs/protocols/chat-completions).

## The paired runs

| Run | Methods | Repetitions | Scheduled attempts | Maximum provider requests | Reserved output-token cap |
|---|---|---:|---:|---:|---:|
| Questions: eight development cases | Fixed routing, one-call selection, bounded agent | 3 | 72 | 168 | 268,800 |
| Documents: four development cases | Deterministic parser, parser/local OCR, Meta extraction | 3 | 36 | 12 | 48,000 |

The request/output limits cover the existing worst-case schedule. They are not observed usage, a monetary estimate or authorization to spend. Input tokens and money are not pre-capped using an unverified tokenizer or price. Local OCR is a separate installed model with its own bounded two-attempt strategy; its failed subattempts remain in reported costs. Provider requests have no automatic retry.

Private full plans and readiness metadata are at `evaluation/live-preparation/20261028-consumer-v6/`. Current question plan ID: `4b993e23be81d6b7ced7ad838fc7410ca91ccdf2fc40153b0d6ed8955e59a46f`; document plan ID: `30108b84f115f922bd2560330857dcecd7172cd9bcff16de475e3cb1501c8efc`. Before a future execution, rerun the plan-only commands and match their plan IDs to these snapshots. A changed source, environment, method, budget or annotation requires a new preparation record. This is an operator preflight, not an immutable external attestation.

```text
python scripts/development_guard.py compare_workflows --split dev --methods local_fixed,meta_single,meta_agent --model muse-spark-1.3 --repeats 3 --max-requests 168 --max-output-tokens 268800
python scripts/development_guard.py evaluate_heldout_documents --split dev --methods local_parser,local_hybrid,meta_direct --model muse-spark-1.3 --repeats 3 --max-requests 12 --max-output-tokens 48000
```

These commands only prepare plans. Once the owner has configured local API access and the execution budget is authorized, adding both `--execute --allow-network` runs the corresponding schedule. Never put credentials in the command line, browser, repository or chat. An access failure is recorded as a failed attempt; it does not become a local success. The older broad-product health-question smoke script is not a prerequisite for this record-only comparison.

## Entry smoke before a batch

`python scripts/smoke_entry_meta.py` creates a new preparation report without reading credentials or making a request. Once credits/access are ready, explicitly authorized execution uses `python scripts/smoke_entry_meta.py --execute --allow-network`. Only that real execution branch loads the server `.env`, preserving existing environment variables. The fixed model is `muse-spark-1.3`; a different configured agent model fails the smoke's model check rather than being silently substituted.

The smoke sends one authored synthetic PDF to the extraction path and exercises the bounded record tool loop against a separate temporary authored history. It never commits extracted proposals. Maximum: seven adapter attempts and 13,600 reserved output tokens, no retry. This is not a monetary or input-token cap; inspect actual usage before authorizing a larger batch. Preparation evidence is `eval/entry-meta-smoke-consumer-v6-prepared.json`. Successful smoke execution would establish those two live paths, not a human-review video, general quality or a workflow winner.

Reports retain the exact plan/source identity, available response/request IDs, latency, reported/unknown usage, finish reason, failure class and all attempted stages. Explicit refusal or incomplete completion is rejected. Missing metadata remains unknown. Injected test transports are always marked `mock_transport_test`, with zero provider requests and no live verification. Thirty artificial tests cover this boundary; they are not model performance. Real delivery cannot be established for every failed network attempt, so attempted calls and confirmed/unknown provider delivery are separate fields.

## Interpretation decided before execution

Evaluate authority and scope first, then exact task success and all-trials reliability. Report support, relevance, linked document fields, incorrect additions, missing rows, failures, provider requests, verified/unknown token usage and latency separately. Keep failed and unsupported attempts in denominators. Budget exhaustion, source drift, changed annotations or missing attempts invalidate a complete paired ranking.

Retain every scheduled case and repetition. Do not remove a difficult case or retry because a score is low. Independently reviewed ambiguities must be disclosed alongside the unchanged original scores; label revisions require a separate version and cannot retroactively improve the frozen baseline. The development review is an independent AI audit, not human or clinical validation. Repeated trials on this small development set are correlated and cannot establish a universally best architecture.

All existing product goals and prompt roles remain accounted for. A successful developer comparison does not complete model adaptation, genetic context, user-value research, production readiness or contest eligibility.

## Independent development-label review

A separate reviewer first inspected the eight question scenarios and four original documents without the gold labels, code, prompts or previous outputs. Its initial conclusions were hash-frozen before releasing only the development labels for reconciliation. It found no substantive label error: all nine eligible document rows, pages and normalized spans matched. Five explicit source rows were correctly excluded for missing fields, ambiguous dates or unsupported metric scope. Original labels remain unchanged.

Two rubric limits remain visible: arrival evidence labels identify the newly arrived rows while the unchanged count also depends on earlier scoped records; and the single abstain category does not distinguish a treatment request from a question needing a missing comparison date. Thus these scores do not independently measure complete citation coverage or useful clarification. Report those dimensions descriptively in the live review without silently revising the frozen score. This was independent AI review; human review remains pending. Summary: `entry/eval/development-annotation-review.json`.

The terminology extension adds query-specific search evidence to both model comparison paths. Grading authenticates alternate search wording/limits by replaying typed read arguments in the frozen context; supplied trace results are not trusted. The existing eight-question protocol is unchanged. The separate 12-task retrieval suite currently measures local retrieval only; it is not a new live model comparison.
