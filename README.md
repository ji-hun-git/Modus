# Modus Records

**Your history, with the original beside it.**

Meta Global AI Developer Hackathon 2026 / **Indie Developer** / **Build for Your World**

Built by **Jihun Chae** (solo), during the 26 October–4 November event.

[Watch the 2:46 demonstration](https://ji-hun-git.github.io/Modus/) · [Run locally](#run-locally) · [Inspect the architecture](#a-history-system-around-the-model)

[![Offline service checks on Windows and Ubuntu](https://github.com/ji-hun-git/Modus/actions/workflows/verify.yml/badge.svg)](https://github.com/ji-hun-git/Modus/actions/workflows/verify.yml)

[![Actual Modus Home: you at the center, clickable source files, selected readings and original evidence.](entry/demo/figures/hero.png)](https://ji-hun-git.github.io/Modus/)

Find a result from years ago. See what changed between reports. Open the evidence
behind the answer. Modus connects medical records into a personal history while
preserving original files, disagreements and earlier saved versions.

Muse Spark reads and investigates. **You review every record write.** This entry
provides record integrity and source retrieval; it does not diagnose, interpret
medical meaning or give health advice.

## Watch one complete story

| In the demonstration | What you can inspect |
| --- | --- |
| **0:00 — Ask your history** | “Blood pressure of 100?” is clarified, matched to 4 May 2016, and opened as the original `100/70` record. Offline tools are labelled. |
| **0:32 — Read a report** | Fresh Muse extraction, verification and row inventory. Three rows found; header date and specimen completed during explicit review. |
| **0:50 — Find a discrepancy** | Muse follows related reports and catches different recorded methods behind identical values. Both sources open. |
| **1:25 — Keep the original** | A reviewed correction creates a version and invalidates the old explanation. Historical replay respects file availability. |
| **2:01 — Inspect the system** | Shipped architecture, bounded authority and a measured development comparison. |

The recording uses application behavior at [`9c6dc2c`](https://github.com/ji-hun-git/Modus/tree/9c6dc2ccfe7092d6227f0d7571f8da674b84f84d),
with **six fresh real `muse-spark-1.3` requests**. Playback is edited, not model
latency. The female narration is AI-generated locally for the video; it is
separate from the Meta-only product path. [Recording inputs and per-call receipts](entry/demo/showcase/) ·
[Transcript](entry/demo/video-transcript.txt) · [Provenance](entry/demo/longitudinal/README.md#recorded-demonstration).

## The same number can hide a difference

![Two July reports both show 5.6 percent; one says HPLC, the other Immunoassay. Both originals stay visible.](entry/demo/figures/investigation.png)

Choose two files in **Compare reports**, then **Explain changes and discrepancies**.
Muse requests bounded reads of the selected and related records. Typed tools
check values, dates, literal units, ranges, specimen and test methods. Findings
open the exact source records. Unknown context stays unknown; no source is
silently chosen as correct.

## A history system around the model

![Original files become Muse proposals, then human-reviewed transactions. Scoped investigation uses typed findings and opens encrypted, versioned evidence.](entry/demo/figures/architecture.png)

- **Originals survive edits.** Corrections append versions, retain reasons and
  invalidate explanations that used a changed source.
- **Two clocks preserve earlier knowledge.** A 2019 report received in 2026 can
  update today's reconstruction while remaining outside what was available in 2025.
- **Models propose; reviewed transactions save.** Muse cannot execute SQL, shell
  commands, arbitrary URLs, record writes or permission changes.
- **Answers have checkable support.** Typed tools calculate and compare within a
  captured history. A source ID alone cannot justify an unsupported sentence.

![A result recorded in 2019 and received in 2026 stays outside the view of files known in 2025.](entry/demo/figures/two-clocks.png)

Meta Muse Spark is the only hosted model in the product path. Offline record
tools remain usable without credentials and are labelled separately. The shipped
document guard is deterministic. SAM, hosted Guard, Voice and a medical fine-tune
are **not** demonstrated product features.

[Agent contract](entry/docs/AGENT_WORKFLOW.md) · [API and storage](entry/docs/API_CONTRACT.md) ·
[Editable architecture](entry/demo/figures/architecture.svg) · [Event contribution map](entry/docs/CONTRIBUTIONS.md)

## Measured, with the limits visible

| Real Muse investigation | Expected discrepancies caught | False flags | Completed cases |
| --- | ---: | ---: | ---: |
| Baseline `6b2f625` | 4/9 | 5 | 14/14 |
| Revised typed comparison rules | 9/9 | 0 | 14/14 |

The same **14 AI-authored three-report cases** were inspected and used for tuning.
Both versions made 42 real Muse requests. The improvement belongs to the typed
comparison rules; the model weights and minimal reasoning setting did not change.
This is a small development result on reviewed CSV records, **not independent,
held-out, scanned-extraction or clinical accuracy**.
[Cases, failures, source hashes and run receipts](entry/docs/VERIFICATION.md#live-cross-report-development-check--4-november-2026).

Software checks and model measurements are separate. Windows and Ubuntu CI run
offline regression checks. Historical results in [SCOREBOARD.md](SCOREBOARD.md)
remain version-specific and are not generalized to later code.

## Run locally

Requires Python 3.11+, Node.js 20.19+ or 22.12+, and an unlocked native OS
credential store: Windows Credential Manager, macOS Keychain or Linux Secret Service.

```sh
python scripts/setup_entry.py
python scripts/check_service.py
python scripts/serve_service.py --port 8011
```

Open **http://127.0.0.1:8011/**. Choose **Open access file** and select the
`Modus-8011.modus-access` file at the location printed by the launcher. Keep it
private. The checked launcher runs offline, strips model credentials, and verifies
source/build identity. It does not run protected evaluations.

For a separate persistent rehearsal, use a new take name:

```sh
python scripts/serve_service.py --rehearsal take-01 --port 8035
```

Each take gets its own encrypted history and access file. Reusing its name resumes
that take; a new name does not reset earlier workspaces. [Step-by-step walkthrough](entry/demo/longitudinal/README.md).

Supported imports include CSV, text, PDF and images through local or explicitly
selected Meta reading. Review preserves printed lab context, uncertain fields,
possible omitted rows and original bytes. Ask can retrieve measurements, visits,
prescriptions, vaccinations, procedures, diagnoses **as recorded**, imaging text
and other source text. Comparisons and reviewed HTML/JSON summaries retain sources.

## Privacy and limits

The local record database, stored originals and journals use SQLCipher with a
random 256-bit key held in the OS credential store. APIs and downloads require a
short-lived local session. Browser credentials stay in memory, outside URLs,
cookies and browser storage. Cross-origin requests are blocked; uploads and
tool arguments are bounded. Provider keys belong only on the server, never Git,
the browser, CI or pytest.

Existing plaintext stores require the explicit, verified migration described in
[storage and recovery](entry/docs/API_CONTRACT.md#encrypted-local-storage--4-november-2026).
Copying the encrypted database to another machine is insufficient: recovery
also needs its original OS-held key. Exported files are not encrypted by Modus.

This is a **local synthetic prototype**. Real-history production qualification,
multi-user accounts, portable key recovery, verified masking/deletion and durable
personal conversational memory remain unfinished. Software tests do not establish
clinical validation or model superiority. Organizer eligibility is not determined
by this repository, and publishing is not a contest submission.

## Documentation and license

[Product flow](entry/docs/PRODUCT.md) · [Verification](entry/docs/VERIFICATION.md) ·
[Data provenance](entry/docs/DATA.md) · [Terminology](entry/docs/TERMINOLOGY_RETRIEVAL.md) ·
[Reviewed summaries](entry/docs/RECORD_BRIEF.md) · [Contributions](entry/docs/CONTRIBUTIONS.md)

First-party code is [MIT licensed](LICENSE). Existing models, libraries and other
materials retain their own terms in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
