# Explore one test across your records

These six CSVs are newly authored demonstration records, not real histories or
training/evaluation inputs. Values and printed intervals are fictional software
examples, not clinical reference guidance. See [provenance](provenance.json).

After setup and the offline service check, start an isolated take:

```sh
python scripts/serve_service.py --rehearsal take-01 --port 8035
```

Open `http://127.0.0.1:8035/` and choose the access file printed by the launcher.
The normal workspace is unchanged. Reusing the take name resumes its encrypted
records; choosing another name starts fresh. Stop the earlier service before
reusing its port. No automatic reset or deletion occurs.

Files are imported through the existing review flow; this folder does not seed
or overwrite a database automatically. CSV reading uses deterministic local
parsing, not Muse. A previously saved Muse draft must be labelled as a saved
result; only a separately authorized actual model request is a fresh live call.

1. Add `2024-checkup.csv`, `2025-checkup.csv` and `2026-checkup.csv`. Review the
   dates, values, units, specimen, method and original excerpts before saving each.
2. On Home, choose `2026-checkup.csv` from the Orbit, then select Ferritin.
   Those imported files contain **58.6 → 64.2 → 71.4 ng/mL**. The starter records
   are additional authored sources; do not describe these three files as the
   entire history. Select a point or row to inspect its file and original.
3. Add and review `2025-conflicting-copy.csv`. Select TSH: both **2.5** and
   **2.9 mIU/L** on 15 March 2025 must remain visible. No winner is selected.
4. To exercise corrections, open Ferritin's 2024 evidence, expand
   **Correct saved record**, and review a correction from **58.6** to
   **58.9** with a reason. Refresh the series. The saved value changes; the
   original excerpt and file still contain **58.6**.
5. Add and review `2019-late-arriving-checkup.csv`. Current history now includes
   **49.5 ng/mL** on 12 April 2019. A knowledge cutoff before this import must
   exclude it, even though its recorded date is earlier.
6. Open **Compare reports**, choose 2026 and 2025, and inspect the original
   evidence and any withheld numerical differences. Then open **Prepare a
   summary**, choose the records, explicitly review the summary and download
   HTML or JSON. These are distinct comparison and export flows. Include both
   conflicting TSH records when demonstrating their source evidence.
7. Add `2016-pressure-record.csv`. Ask **When did I last have blood pressure of
   100?** Choose **Top number (systolic)**. The recorded match is **4 May 2016**,
   with **100/70 mmHg** in the original. Open its source; do not infer whether
   that result was healthy or represents the person's current blood pressure.

All numerical changes describe recorded values only. Missing records do not show
that a test or care never occurred. The app neither interprets these values nor
offers health advice.

An actual offline browser rehearsal reviewed and saved all six files, clarified
the pressure query, opened its original evidence and displayed both conflicting
TSH copies. Sixteen HTTP assertions covered the baseline, late availability,
conflicts and original bytes. See [verification](../../docs/VERIFICATION.md).
Full keyboard and narrow-layout qualification of this new recording setup
remain open. These checks do not demonstrate live Muse quality.

## Recorded demonstration

[Watch the 2:52 demonstration](https://ji-hun-git.github.io/Modus/)
or [open the repository copy](../Modus-demo.mp4).
[Read the narration transcript](../video-transcript.txt).
The playback page is published from the isolated `codex/demo-video` assets
branch. The application source remains on the default `main` branch.
The recording was made on 4 November 2026 from application revision
`9d8b65aefb6a5c0025b50f899db845e7e7d6072b`. Subsequent recording/documentation
commits do not change that application behavior. The saved Muse review was
opened in the preserved workspace using the same application source.

The video combines actual browser captures, a timed orbit/evidence interaction
and edited still holds. Its narration is generated offline with the Windows
speech synthesizer. The footage contains authored examples, not real personal
medical records. The first card identifies the event-built app and credits the
pre-existing Meta models and libraries.

The Meta segment reopens an actual previously generated `muse-spark-1.3` draft.
It is **not a fresh live request**, and its unavailable independent image-text
check remains visible. All other recorded reading and Ask actions are offline
and labelled accordingly. Edited playback time is not model latency. No model
credits were spent recording this video. The video demonstrates record review,
source evidence, temporal availability, conflicts and export, not medical
interpretation, held-out quality, SAM, hosted Guard, Voice or fine-tune quality.

Media integrity, duration and source identity are recorded in
[the video receipt](../video-receipt.json). This video is an artifact for the
entrant to review; publishing it does not submit the competition entry.
