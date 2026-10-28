# What data does Modus use?

## The records you see in the entry

The starting history is an **authored synthetic example**. It contains three invented documents and nine measurements: HbA1c, eGFR and LDL on three dates. The dates and values were chosen to exercise record review and historical availability. The fictional profile is not a real person, a hospital export or Synthea output.

The source is `backend/modus_entry/seed.py`. Its three measurement dates are 9 April 2018, 8 April 2021 and 20 October 2026. The second record became available on 9 April 2021, a day after its measurements. This is an authored timeline, not a claim about when a real person knew something.

Displayed counts come from the current database and selected date bounds. Reviewed synthetic imports can increase those counts; the starting nine measurements are not a hardcoded dashboard total. Imported facts retain the original file, measurement date, unit, source excerpt and review-commit availability time. A synthetic-data confirmation is a user assertion, not a detector that can prove a file contains no personal information.

## Separate development and research data

| Data | Purpose | What it does not establish |
|---|---|---|
| Authored entry records | Demonstrate review, source inspection, conflicts and replay | A representative medical history or clinical outcome |
| Eight older authored PDF/image documents | Extraction regression and local OCR experiments | Independent generalization or a reproduced public leaderboard |
| Frozen development questions and documents | Compare routing, supported answers and linked-field extraction | Human-reviewed clinical truth; these labels were separately model-authored |
| Private held-out suites | A later, explicitly authorized frozen comparison | Current model quality; they remain untouched during this milestone |
| Synthea histories in the broader workspace | Reproducible synthetic FHIR and training-data preparation | Data shown in the entry, real-world prevalence or a trained model |

The recorded Synthea preparation generated 12 histories. Six compatible histories supplied 42 supported observations and 46 prepared examples (28 training, nine validation, nine test), with disjoint subject splits. Those are prior preparation counts from `eval/data-preparation.json`; no training run has occurred. The entry source extract does not bundle that broader research cohort. Those prepared examples are not part of this development-annotation review.

## What the model sees

Local text extraction uses deterministic code and makes no model request. Explicit local TeleOCR runs a separately installed pinned model on the selected document; its transcription remains an unverified draft. Explicit Meta extraction would send the selected synthetic document to the configured official service. The question workflow would receive scoped synthetic evidence through bounded read tools. API credentials remain on the server. Real Meta comparison runs have not occurred.

Original records, model transcription and numerical findings are different things: typed tools compute counts and comparisons, and a person reviews proposed rows before they become persistent records. Source IDs alone do not prove an answer is supported.

No real personal health records, hospital integration, raw DNA or credentialed research dataset is used by this local demonstration. Broader reference summaries and fictional genetic examples belong to the full research product, not this record-reconciliation entry. All ten original product goals remain in `entry/docs/GOALS_AND_PROMPTS.md`; this narrower entry does not mark the remaining goals complete.
