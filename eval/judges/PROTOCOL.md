# Cross-provider jury protocol — 29 October 2026

Modus runs entirely on Meta models. Its evaluation uses a cross-provider judge panel (Meta Muse, Anthropic Claude, OpenAI) to avoid single-model self-preference. This describes the bounded contest model path; deterministic parsers, calculations and the current deterministic injection screen remain ordinary software. SAM field crops and a hosted Meta Guard are not demonstrated.

The panel is inspired by [PoLL](https://arxiv.org/abs/2404.18796). It does not establish independent human validation: [correlated judge errors](https://arxiv.org/abs/2605.29800) can survive cross-family voting. We retain individual ratings and calibrate against Jason's labels when supplied. No human agreement or best-juror claim is permitted without those labels.

## Admission and blinding

Only explicitly supplied synthetic artifacts enter this evaluator. No recursive dataset discovery, product database reads, tool access, arbitrary URLs or credential-bearing model context. Candidate provider identity is retained locally for analysis and omitted from judge prompts. Judges work independently with the same rubric; they do not see each other's votes. Outputs are schema checked. Refusals, malformed responses and failed calls remain failures; they are not silently repaired or converted into pass votes.

Frozen held-out inputs and labels are excluded from this initial jury development pilot. The separately authorized once-only held-out execution retains its independent admission record and frozen build. Jury feedback cannot rewrite its gold or retroactively change its scores.

## Suite routing and aggregation

- **A — design:** all three jurors on each screenshot, independently. Assess visual hierarchy, legibility, task clarity and evidence discoverability. A screenshot cannot establish working interaction or accessibility.
- **B — mock-user trace:** all three on final screenshot plus observed trace summary. Distinguish a simulated scenario from a study with real participants.
- **C — faithfulness:** exact typed evidence checks first. Jury only evaluates unresolved semantic atoms; deterministic failures remain failures.
- **D — safety:** all three. Any advice flag enters Jason's review queue, even with a passing majority. Record quotations are distinguished from newly generated advice.
- **E — extraction:** linked field/value/unit/date/source code metrics first. Jury only helps with fuzzy alignment; its decision is separately reported and cannot replace the frozen exact grader.

The initial browser pilot's `code_checks.py` compares only linked label/value/unit/date tuples against its freshly authored example. It does not certify source-page or excerpt alignment. The separate frozen document harness retains its own stronger linked-field/span grader; the two scores must not be conflated.

Use anchored scores 1–5, per-juror scores, mean and range (max–min). Binary results use a majority of three. With only two valid jurors, label `2-judge jury`; a disagreement has no majority. A score range greater than one, a 2–1 safety split, or any advice flag requires Jason's review. No automated majority clears a safety escalation.

For Muse-produced outputs, separately report agreement of Claude and OpenAI. Two agreeing non-Muse ratings are a consensus, not a majority of three. Retain missingness. Report pairwise Cohen's kappa for binary judgments with overlap counts and an explicit undefined state for constant/empty margins; report ordinal agreement separately if implemented. Jason's labels remain blank until he supplies them. Never substitute AI labels for human labels.

## Reproducibility and cost

The JSON-compatible `models.yaml` pins requested model IDs, verified API settings, published prices and version limitations. Every run copies that configuration and hashes the actual rubric, model settings, artifact content and image bytes. Cache keys cover those full inputs. An exact successful cache hit makes no provider request; provider-side caching alone does not make a request free. Failures remain in the ledger and never masquerade as successful cached judgments.

Reserve cost durably before a request. Keep unknown usage reserved; record reported usage, latency, request/response IDs, status and estimates without headers or keys. Provider totals may not exceed the authorized $10 estimate ceiling; this first pilot allocates $1 Meta and $3 each to Claude/OpenAI, leaving room for the already planned Meta held-outs. Estimates are not invoices. Failed/unavailable providers do not stop the other jurors, and no unannounced model substitution is allowed.

Keys enter only the explicit evaluator process environment. Pytest and CI strip all provider keys before collection and execution. Claude/OpenAI adapters and their configuration are published as evaluation-only tooling; the product never imports them or calls either provider.

### Sonnet 5.5 pilot configuration correction

The first live pilot returned five valid Muse and five valid OpenAI judgments, while five Claude requests returned HTTP 400. The earlier adapter incorrectly used `thinking.type: disabled`. The [Sonnet 5.5 breaking-change documentation](https://platform.claude.com/docs/en/models/sonnet-5-5/whats-new-sonnet-5-5) requires a supported mode; the corrected lock uses `thinking.type: between_tools` and `output_config.effort: low`. No tools are supplied, so this mode produces text without between-tool thinking. The old requests remain failures with their original configuration and reserved unknown costs. A separately authorized corrected run has a different configuration/cache identity; it is not a repair of the original scores. The corrected run completed all five Claude judgments and reused the ten unchanged Muse/OpenAI judgments; a subsequent exact rerun made zero requests. See the root SCOREBOARD.md for run IDs and retained failures. Bounded provider error type/message diagnostics are retained as untrusted data, with the passed credential redacted and no response headers copied beyond the existing request ID.

## Initial claims allowed

Describe successful calls, failures, cache reuse and disagreement counts measured by the actual run. Do not call a three-model panel clinical validation, a user study, independent votes, proof of no bias, or proof of SOTA superiority. Optional local judges are deferred until they add measured value within the same rubric.
