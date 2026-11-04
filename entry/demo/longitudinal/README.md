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

[Watch the 2:46 demonstration](https://ji-hun-git.github.io/Modus/),
[open the MP4](../Modus-demo.mp4), or [read the transcript](../video-transcript.txt).
The player is published from `codex/demo-video`; application source is on `main`.

The replacement recording captures application behavior at
`9c6dc2ccfe7092d6227f0d7571f8da674b84f84d` on 4 November UTC / 5 November KST,
before the event deadline. Later media/documentation commits do not change that
behavior. Every record shown is an authored example, not personal medical data.
The opening identifies event-built Modus work and credits existing foundations.

The new sequence includes **six fresh real Muse requests**: image extraction,
verification, source-only row inventory and a three-request bounded investigation.
All three image rows were extracted; header date and specimen were completed
explicitly during review. The limitation of the independent source check remains
visible. The investigation catches the HPLC/Immunoassay difference behind two
identical 5.6% values, with both original sources. A reviewed authored correction
then makes that prior explanation stale and preserves the original wording.
[Exact input files, per-call model/usage and limitations](../showcase/).

Ask, timeline replay and export use ordinary offline typed tools. These sequences
come from a preserved separate demonstration history. Model calls are not replayed
mock outputs. Cuts follow narration; elapsed video time is not model latency.
The original 14-case development comparison remains unchanged and distinct from
the six recording calls. No protected evaluation set was accessed or rerun.

Narration is AI-generated locally using pinned Qwen3-TTS 1.7B VoiceDesign
weights. It is one continuous, original female voice designed for this film;
no person's voice was cloned. This is post-production media, separate from the
Meta-only product path. [Third-party notices](../../../THIRD_PARTY_NOTICES.md)
credit the model and runtime. Captions are burned in and available as
[WebVTT](../captions.vtt).

The film is 166.12 seconds. Every frame decodes; its
longest measured gap below -40 dB is 0.669
seconds. Offline speech recognition checks script fidelity and caption timing;
signal checks do not establish an objective ranking of voice quality.

The [hero](../figures/hero.svg), [architecture](../figures/architecture.svg),
[investigation](../figures/investigation.svg), [two clocks](../figures/two-clocks.svg)
and [development comparison](../figures/measured.svg) are first-party editable
figures. Product imagery is actual app capture. The diagrams describe shipped
behavior; SAM, hosted Guard, Voice, medical fine-tuning and clinical interpretation
are not presented as features.

[Recording receipt](../video-receipt.json) · [Frame/decode/audio checks](../video-verification.json).
The entrant still reviews and submits the video link in the competition portal.
