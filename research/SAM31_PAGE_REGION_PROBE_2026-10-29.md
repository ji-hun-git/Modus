# SAM 3.1 page-region feasibility — 29 October 2026

**Recommendation: do not add SAM field highlights to the contest entry from this evidence.** Three initial hosted requests and one separately authorized response diagnostic completed. The diagnostic confirms one valid empty text result for the chosen concept/page; the first three remain adapter-limited. Access worked; field localization was not demonstrated. Existing excerpts, page labels, original-file download and explicit human review remain the product behavior.

## Execution evidence

The fixed concept was `text row`, chosen before execution. Inputs were page 1 of the existing authored development `update.pdf`, page 1 of `mixed.pdf`, and the existing `injection.png`. These are synthetic documents in `data/synthetic/documents`, not held-out evaluation inputs. The original bytes were preserved. Each rendered image has a source hash, raster hash, dimensions and display orientation in the plan. No model was given tools or record-writing authority.

| Input | Actual HTTP / completion | Reported image usage | Latency | Usable parsed regions |
|---|---|---:|---:|---:|
| update.pdf, page 1 | 200 / completed | 1 | 809.04 ms | 0 |
| mixed.pdf, page 1 | 200 / completed | 1 | 1,715.19 ms | 0 |
| injection.png, page 1 | 200 / completed | 1 | 2,349.68 ms | 0 |

All three responses reported `sam-3.1`. Request and response IDs, returned usage and exact geometry-lane files are retained privately in `evaluation/sam-probe-20261029/`; the sanitized public summary is `eval/sam-probe-20261029.json`. There were **3 requests, 3 completed responses, 0 retries**. The published image-price estimate is **$0.0075**. Actual invoice, credit balance and any other charges remain unverified. A working request does not prove that the $150 credit grant is present.

**Measurement limitation:** the initial probe kept the geometry lane and allowlisted telemetry, not the complete provider envelopes. Its narrow output adapter does not distinguish an absent `output` from an empty one. Report those three as **no usable parsed regions**, not as a validated zero-detection benchmark. Their files were retained unchanged by the separately authorized diagnostic below.

All three upright source pages were visually inspected. There were no boxes to overlay or compare against text. No IoU, per-field correctness, general SAM failure claim, clinical result, security-guard success or workflow improvement is established. The adversarial image is source content only; segmentation without tools is not an injection-defense evaluation.

Commands run:

```powershell
.\.venv\Scripts\python.exe scripts/probe_sam_regions.py
.\.venv\Scripts\python.exe scripts/probe_sam_regions.py --execute
```

Five local parser checks passed: empty output, inclusive-to-half-open coordinates, invalid frame, out-of-bounds box and bare-frame rejection. The bare-frame bug was corrected before any provider request; the original prepare-only plan was retained. A second `--execute` was deliberately invoked to verify the single-use guard: it stopped with a local `ValueError`, and the request count stayed at three. No application or frontend code changed, so this probe makes no new application release-gate claim. Parent integration owns the full regression gate.

## One additional envelope diagnostic

After the initial adapter limitation was reported, the parent explicitly authorized one additional request. `scripts/diagnose_sam_response.py` reused the identical prepared `update.pdf` page, `text row` prompt and request controls. It retained the complete bounded synthetic response body, without HTTP headers, auth or input image payload, in `evaluation/sam-probe-20261029/diagnostic-4/response-envelope.json`. Exact-key redaction was checked and was not needed.

The actual response is HTTP 200, model `sam-3.1`, status `completed`, `error:null`, `incomplete_details:null`. The path is **`output[0].content[0].text`**, with a `message` output item and an `output_text` content part. Its value is the empty string. This is a **valid empty text lane**, distinct from missing/malformed output or refusal. Reported usage is one processed image; latency is **1,233.81 ms**. There was no provider refusal. The independent diagnostic does not retroactively validate the first three stored envelopes, which were not retained.

The stricter adapter separately distinguishes missing output, an empty output array with no lane, a valid empty text lane, refusal and malformed geometry. Five offline envelope classification checks passed. The single-use diagnostic guard also refused a repeat invocation before credentials/network. No fifth call was made.

Final reproducible probe tests: **22 passed in 0.38 seconds** with `.\.venv\Scripts\python.exe -m pytest evaluation/sam-probe-20261029/test_probe.py -q`. They cover coordinate normalization, invalid/mismatched geometry, distinct envelope states, exact saved diagnostic evidence and both execution guards. Every test blocks dotenv loading and network-client creation; geometry literals are clearly marked unit fixtures, never live results. No application tests or frontend build were rerun for these local research scripts.

Cumulative probe evidence is now **4 actual requests / 4 HTTP 200 completed responses / 4 reported processed images**, with a published image-rate estimate of **$0.0100**. Actual billing and account credits remain unknown. One concept on one validated page cannot establish SAM's general document capability. The integration decision is **deferred for insufficient reliable geometry**. Stop at four calls; no further tuning, model-general failure claim or UI integration. Public-safe local summaries: `eval/sam-diagnostic-20261029.json` and `eval/sam-feasibility-20261029.json`. They are not added to the public source allowlist or published by this task.

```powershell
.\.venv\Scripts\python.exe scripts/diagnose_sam_response.py
.\.venv\Scripts\python.exe scripts/diagnose_sam_response.py --execute
```

## Verified hosted contract

Use `POST https://api.meta.ai/v1/responses`, Bearer authentication and the API model ID **`sam-3.1`**. The marketing URL uses `sam-3-1`; it is not the request ID. One user message pairs an `input_text` concept with `input_image.image_url`. A base64 image data URI is documented. Non-streaming is supported. The probe used `stream:false`, `store:false`, and metadata `mask_encoding:"one_bit"`, `include_confidence:"true"`. [SAM overview](https://dev.meta.ai/docs/sam/overview), [prompt and image input contract](https://dev.meta.ai/docs/sam/segmenting), [Responses API](https://dev.meta.ai/docs/protocols/responses).

SAM locates visual concepts; it does not reason about a scene or establish what a numeric result means. A single short noun concept is supported per request. Missing matches may produce empty output. Box/point prompting is also supported, but refining another model's guessed box would not independently verify the field association. [Prompt guidance](https://dev.meta.ai/docs/sam/segmenting).

Output is special-token text carrying object IDs, boxes and masks, not ordinary JSON boxes. Coordinates refer to the display-oriented source image. The protocol specifies inclusive `x2/y2`; normalized UI boxes should use `(x2+1)/width` and `(y2+1)/height` for half-open right/bottom edges. Confidence is optional model output, not field correctness. The probe retained encoded masks and inspected boxes only; it did not install a decoder. [Output documentation](https://dev.meta.ai/docs/sam/reading-segmentation), [official protocol](https://github.com/meta-models/meta-sam/blob/main/protocol/sam3.md).

The published SAM price is $2.50 per 1,000 images and $0.20 per 1,000 video frames; video has a minimum 50-frame billing unit. Image streaming and non-streaming cost the same. SAM is image/frame billed and has no token-per-minute limit. This three-image probe used no video and no Contributor model. A generic Responses token cap exists, but SAM-specific documentation does not establish its effect on geometry; this probe bounded image count, wall time and response bytes instead. [Pricing and rate limits](https://dev.meta.ai/docs/pricing-rate-limits).

An open-weight alternative exists, but is not a useful automatic fallback here. Official prerequisites are Python 3.12+, PyTorch 2.7+, and CUDA 12.6+ GPU support; the repository has a separate SAM license and checkpoint access process. SAM 3.1's highlighted changes concern shared-memory multi-object video tracking, not a demonstrated document-row OCR gain. No weights were downloaded, license accepted, environment installed or GPU run performed. [Official repository](https://github.com/facebookresearch/sam3), [3.1 release](https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md).

## Existing contracts and smallest useful future design

`backend/modus/record_document_input.py` already produces bounded upright JPEGs, including EXIF transpose for images, source SHA-256, raster SHA-256, dimensions and orientation. Dense text-only PDFs normally use their text without a page raster; a future preview would need bounded on-demand rendering. Fact boxes are normalized `[left,top,right,bottom]`. Current metadata explicitly identifies them as `model_proposed_not_independently_located`. Preserve that distinction.

`entry/frontend/src/GenericFactReview.tsx` already has per-field excerpts and a draft-original link. `SourceCubeEvidence.tsx` supports source inspection and availability-scoped originals. Do not introduce another Home panel.

If a later independent text-alignment or human-region study succeeds, the minimum useful interaction is selecting a reviewed field and seeing its exact row in a page preview, with an original-page toggle. A row must include the relevant label, value, unit and recorded date or explicitly link the separate date region. A page/table outline alone adds no field evidence.

The optional region record must bind fact ID, original hash, page, raster hash/dimensions, normalized box, producer/model/request and association status. A SAM object ID alone cannot bind a field. Until checked, label the region as suggested; never show a verified badge based solely on model confidence.

Any preview route should be server-owned, for example a proposed `GET /api/drafts/{draft_id}/pages/{page}` after validating the current uncommitted draft. It must not accept arbitrary paths or URLs. Committed previews need the same `as_of`/`known_at` visibility checks as `/api/history/sources/{source_id}/original`, including withholding source material with later facts. This proposed route is **not implemented**.

Fallback is the current source excerpt, page label and permitted original download. Missing, invalid, ambiguous or unavailable geometry must never change extraction values, the ability to review, commit requirements or conflict handling. No geometry feature is warranted by the current probe.
