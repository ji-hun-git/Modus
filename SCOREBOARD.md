# Modus evaluation scoreboard — 29 October 2026

Modus runs entirely on Meta models. Its evaluation uses a cross-provider judge panel (Meta Muse, Anthropic Claude, OpenAI) to avoid single-model self-preference.

This refers to model execution in the contest product. Deterministic parsers, typed tools and the known-pattern injection screen remain ordinary software. Hosted Guard and reliable SAM field crops are not demonstrated.

## Five-case browser pilot

Five fresh synthetic cases cover Home, scan review, an answer about a reviewed correction, an injection refusal and source evidence. They are development artifacts, not held-out data or a study with real users. The product remains frozen across the judge configuration correction.

| Stage | New calls | Outcome |
|---|---:|---|
| [Initial run](eval/jury-2f11a8454b954f7eb76d6138c9a262d0.md) | 15 | Five Muse + five OpenAI judgments; five Claude HTTP400 failures; **2-judge jury** |
| [Corrected run](eval/jury-33711e09458d437faffe4b5972d875f9.md) | 5 | Five Claude judgments; ten exact cached Muse/OpenAI judgments; full three-family panel |
| [Exact cache rerun](eval/jury-b86bf354013644bcabd96443b2676432.md) | 0 | All15 judgments reused; no new cost |

The initial Claude adapter used an unsupported thinking setting. The corrected Sonnet5.5 configuration uses `between_tools` and low effort, as required by the vendor's current API. Original failures, configurations and conservative unknown-cost reservations are retained.

All15 case/criterion majorities passed. Design means range4.00–4.33/5; task/trace means4.00–5.00/5; safety votes are unanimously passing on these five cases. No disagreement rule triggered. This small, mostly successful sample is weak evidence of judge sensitivity; it does not establish safety or a best workflow. The code separately passed one three-field tuple check and one exact typed-claim composition check. Neither establishes general source entailment.

For the two Muse-produced artifacts, Claude and OpenAI independently agree on passing A/B/D. Their A/B scores are4/5, with safety5/5. Full per-juror scores, mean/spread and non-Muse consensus are in the corrected report; [bounded feedback](eval/jury-feedback-20261029.json) retains their criticisms.

## Agreement and human calibration

Pairwise binary Cohen κ is **undefined** for all three pairs because all five binary outcomes are passing. Ordinal κ and sample counts are retained in the report; constant-margin values are not presented as perfect agreement. Jason has not supplied human labels, so judge-vs-Jason agreement and the best-aligned judge are **not measured**. Zero queue triggers is not human approval. Exact human-label schema and escalation rules: [protocol](eval/judges/PROTOCOL.md).

## Provider costs and limits

| Provider | Successful jury usage estimate | Retained unknown failure reservations | Cumulative accounted including earlier product work | Ceiling |
|---|---:|---:|---:|---:|
| Meta | $0.026807 | $0 in this jury | $0.572474 after held-out run | $10 |
| Anthropic | $0.061482 | $0.827850 | $0.889332 | $10 |
| OpenAI | $0.094460 | $0 | $0.094460 | $10 |

These are conservative estimates, not invoices. Claude's reservation is not a claim that HTTP400 responses were billed. Earlier Meta estimates include unsuccessful product requests and four SAM probes; older HTTP400 billing is unknown. Every explicit request has a private ledger entry. Each [run configuration](eval/jury-runs/33711e09458d437faffe4b5972d875f9/config.json) records model settings, implementation/prompt/schema hashes and input/image hashes. Credentials and raw medical histories are excluded.

## Product evidence and remaining gaps

[Actual browser evidence](eval/product-meta-only-browser-20261029.json): pure Meta extract+verify, three reviewed fields saved, intentional Pulse72→73 correction preserved beside the original72 quote, original download byte match, two-call bounded Ask and zero-call injection refusal. The first mixed local-OCR run and the later token-limit failure remain failures/qualified evidence; they are not relabelled as current success.

Replay's legacy comparison at the jury snapshot supported only three metrics. A subsequent revision adds exact eight-kind comparisons; its browser/regression verification is separate from these jury scores. Human annotation review, representative difficult/adversarial judge controls, responsive/accessibility qualification, production privacy, license choice and final contest eligibility remain open. The jury used no held-out inputs or labels.

## Separate frozen held-out result

The subsequently authorized once-only run measured workflow Muse17/24 versus fixed local5/24. Documents: single-pass Muse8/8, extract+verify8/8, local parser1/8. There is no measured verifier accuracy advantage. This added67 successful Muse requests and an estimated$0.308662. Labels remain AI-authored, and the suites cover the legacy workflow/three-metric contract. [Results and retained failures](eval/heldout-contest-20261029.md). The sets are closed to reruns and panel tuning; later UI/replay changes do not inherit these quality scores.

The five original synthetic pilot screenshots, authored source image and artifact manifest are published in [eval/jury-pilot-20261029](eval/jury-pilot-20261029/manifest.json). A default `python -m eval.judges.cli --input eval/jury-pilot-20261029/manifest.json` prepares hashes/configuration with zero calls. Network evaluation requires explicit flags and process credentials. These inputs are independent of the closed held-out sets.
