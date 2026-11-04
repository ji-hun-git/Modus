# Third-party materials in Modus Records

Offline security regressions reuse 26 unchanged payload strings from
[NVIDIA garak](https://github.com/NVIDIA/garak) at commit
`b1681c5bf8ff71971f83848fe245c6c1550aff08`. Its Apache 2.0 license and source
notice are retained in `backend/tests/fixtures/garak/`. This is test-corpus reuse,
not a bundled scanner, product model, or claim of model jailbreak resistance.

The interface bundles unmodified Inter 4.1, copyright 2016 The Inter Project Authors, under SIL Open Font License 1.1. The font and full license are retained in `entry/frontend/public/fonts/InterVariable.woff2` and `Inter-OFL.txt`. Upstream source is the official `rsms/inter` repository at commit `e3a3d4c57d5ecc01453a575621882a384c1995a3`. No proprietary Meta font is bundled.

Application dependencies retain their own licenses. Locked runtime/build/test versions are in backend/requirements.lock.txt and entry/frontend/package-lock.json. The inventory in entry/docs/DEPENDENCIES.json records declared metadata and available notice hashes; corresponding texts are under data/licenses/dependencies. Uninstalled optional platform packages are explicitly identified. This inventory is not a legal compatibility determination.

Encrypted storage adds `sqlcipher3` 0.6.4 (SQLCipher-backed Python driver),
`keyring` 25.7.0 (native OS credential access) and `portalocker` 3.2.0
(interprocess leases). Platform dependencies are pinned in
`backend/encryption-requirements.lock.txt`, included by the backend lock.
SQLCipher uses its upstream BSD-style license; the installed driver and its
bundled cryptographic components retain their respective terms. Package notices
are retained with the dependency inventory. No model weights are added.

This entry uses authored synthetic records. It does not bundle Synthea exports, medical reference datasets, private supplied design documents, model weights, a trained adapter or the separate TeleOCR research environment. The full private Modus workspace preserves the wider research and provenance.

The optional local OCR adapter uses the separately installed XingChen-AGI/TeleOCR checkpoint pinned in config/teleocr.json, whose upstream model card declares Apache-2.0. Weights and its isolated environment are not part of the source package. scripts/requirements-ocr.lock.txt records that environment's dependencies; their own licenses apply. Optional OCR runtime qualification does not establish unrestricted production-upload suitability.

First-party Modus source is licensed under the [MIT License](LICENSE), selected
by its owner on 4 November 2026. Dependency licenses and the competition's
organizer agreement remain separate matters.

## Demonstration media

The final demonstration uses AI-generated female narration from
[Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign),
revision `5ecdb67327fd37bb2e042aab12ff7391903235d3`, with the
[Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) runtime `qwen-tts` 0.1.1.
The publisher declares Apache-2.0 for the model and runtime. Narration was
synthesized locally on an RTX 5080 as an original designed voice; no person's
voice was cloned. Model weights and the isolated media environment are not
distributed with the application. This is post-production narration, not a
non-Meta model in the product path.

The final video receipt identifies the model, revision and file hashes used.

The hero and system figures are Modus-authored SVGs, rendered with resvg 2.6.2;
the hero embeds an actual application capture of authored demo records.
No Palantir branding, proprietary artwork or interface assets are reused.

## Record terminology

The small catalog associates nine LOINC codes with their official short names, checked on 28 October 2026. The [required LOINC notice](LOINC_short_license.txt) and [LOINC license](https://loinc.org/license) apply to those materials. The catalog's version is a Modus revision, not a claimed complete LOINC release. Local concept associations, retrieval aliases (including Korean) and qualification rules are Modus-authored annotations. No full terminology database, linguistic-variant dataset, SNOMED mapping or endorsement is included.

The bounded unit lookup recognizes a few recorded identities and references [UCUM](https://ucum.org/ucum), copyright Regenstrief Institute, Inc. See its [copyright notice, license and warranty terms](https://ucum.org/license). The specification/database is not redistributed. This lookup is not a general UCUM parser, conversion engine or conformance certification.
