# NVIDIA open-source tools in Modus

Reviewed official repositories on 3 November 2026. This is a targeted selection
for document integrity, privacy and local development, not an exhaustive list of
NVIDIA projects. Meta remains the only model family in the contest product path.

| Project | Modus use | Status |
| --- | --- | --- |
| [garak](https://github.com/NVIDIA/garak) | SQL, Python-execution and browser-script payloads test whether imported text can cross record-write or rendering boundaries. | Applied: 26 upstream strings pinned at `b1681c5bf8ff71971f83848fe245c6c1550aff08`. Original Apache license and provenance included with fixtures. |
| [NeMo Retriever](https://github.com/NVIDIA/NeMo-Retriever), formerly nv-ingest | Candidate for offline page/table extraction experiments, retaining page regions and literal text before any reviewed import. | Reviewed, not installed. Its specialized NIM services are a separate deployment; this is not a drop-in change to Muse or a verified single-RTX configuration. |
| [Data Designer](https://github.com/NVIDIA-NeMo/DataDesigner) | Candidate for generating mixed-test synthetic development reports with explicit distributions, dependencies and deterministic field validation. | Reviewed, not installed. No generation calls or training data changes in this pass. Keep generated examples separate from frozen evaluation inputs. |
| [NeMo Curator](https://github.com/NVIDIA-NeMo/Curator) | Candidate for deduplication/quality filtering when a larger licensed development corpus is introduced. | Reviewed, not installed. Do not deduplicate conflicting original owner records; curation would apply to training copies only. |
| [NeMo Anonymizer](https://github.com/NVIDIA-NeMo/Anonymizer) | Candidate for redacted export copies, with a private mapping to untouched originals. | Reviewed, not installed. Any implementation must measure missed identifiers and preserve dates/units/meaning. It cannot guarantee anonymity. |
| [NeMo Guardrails](https://github.com/NVIDIA-NeMo/Guardrails) | Candidate for an additional input/output policy layer around the existing bounded reader. | Reviewed, not installed. It would supplement typed tools and explicit owner commits; it must not acquire write permissions or trigger hidden model calls. |

The garak integration reuses test data, not its scanner or models. Offline
regressions verify that these strings remain literal document content, cannot
save themselves, retain evidence, and render without executable browser markup.
They do not measure Muse jailbreak resistance, OCR quality, clinical accuracy or
general security. Existing model prompts, budgets and read-only tool permissions
remain unchanged. Larger NVIDIA runtimes are not installed merely for branding.

The upstream Data Designer documentation describes telemetry opt-out using
`NEMO_TELEMETRY_ENABLED=false`. Guardrails documents
`NEMO_GUARDRAILS_NO_USAGE_STATS=1` before initialization. These are requirements
for a future local probe; no runtime from either project is loaded here.
