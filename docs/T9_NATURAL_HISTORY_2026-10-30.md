# Natural whole-history retrieval — 30 October 2026

## Delivered

Latest-by-kind questions work across all eight saved kinds: measurements, visits, recorded diagnoses, procedures, prescriptions, vaccinations, imaging text and other recorded text. Examples: “When was my last vaccination?”, “What was my most recent prescription?” and “Show my latest imaging report”. Answers describe saved records; they do not confirm administration, current medication use or a new diagnosis.

Conversational requests such as “Have I ever had a flu shot?”, “Pull up my CAT scan” and “Tell me about my medications” work offline. Five additional naming topics cover influenza vaccination, MRI, CT, X-ray and ECG. They match saved labels of appropriate kinds, not narrative mentions or medically related conditions. Quoted strings stay literal. Unknown words, source restrictions, body-part qualifiers and time scopes cannot be silently dropped. Two explicit topics can use separate bounded reads. The existing 24 measurement concepts remain available.

Naming references were checked against MedlinePlus: [Flu](https://medlineplus.gov/flu.html), [MRI](https://medlineplus.gov/mriscans.html), [CT](https://medlineplus.gov/ctscans.html), [X-rays](https://medlineplus.gov/xrays.html), and [ECG](https://medlineplus.gov/lab-tests/electrocardiogram/). These explain names, not personal findings. Authored aliases have not been independently clinically or linguistically validated. Topics do not assert route, formulation, body part or technique equivalence.

Latest requests preserve original qualifiers, same-day ties, partial/unknown-date caveats, future-date exclusions and bounded evidence. Model arguments remain constrained by the owner's request. Fixed an existing non-raw regex string containing a backspace instead of a word boundary, which weakened unsupported-filter rejection. Tests cover each affected filter; “average blood sugar” remains a name, not a numerical aggregate. Duplicate visible labels are matched once per request instead of once per observation.

Stored labels, values, units, original files, corrections, dates and conflicts are unchanged. Original evidence and naming-reference links use the existing UI. No frontend layout, CSS or orbit code changed in this pass.

## Verification

- `.venv/Scripts/python.exe release/T9-natural-retrieval/run_regression.py`: **981 selected backend tests passed** (52 new authored regressions), **138 frontend tests passed**, `npm run build` passed. The known Starlette/httpx deprecation warning remains.
- The guarded runner strips provider credentials, disables dotenv, blocks non-loopback network and forbids evaluation/held-out/secret-file access. No blocked access attempts were logged. Artificial transports are not live-model evidence.
- Browser: uploaded a fresh three-row synthetic CSV, checked excerpts, saved reviewed vaccination/imaging/procedure fields, advanced the availability view, asked “When did I last have a flu shot?”, inspected its naming mapping and opened the original source. After restart, latest vaccination also retained the partial-date caveat. No console errors or warnings during inspection.
- HTTP integration verifies import → review → commit → natural Ask → paged alias search → byte-identical original download. A cutoff before import excludes it. Every earlier source, fact, observation, document, draft, commit and amendment row in the copied databases remains unchanged.
- `.venv/Scripts/python.exe release/T9-natural-retrieval/verify_service.py`: five service questions passed; **120/120** loopback requests passed with expected evidence over **5,009 records**, **8 workers**, median **674.47 ms**, p95 **1,501.56 ms**, max **1,961.02 ms**. T8 used a different workload. The same T9 workload before label deduplication had p95 1,666.95 ms; two local runs do not establish general performance.
- Private diagnostics/screenshots: `release/T9-natural-retrieval/`. Preview: `http://127.0.0.1:8015/`, copied synthetic data, guarded offline execution. Tested runtime: `sha256:74c69092320210eb1c0dc446fc91f03244fc5220c7ad3bc538785d4b9546726f`.

This is controlled terminology/topic retrieval plus typed history queries, not dense embeddings, a neural reranker, clinical inference or evidence of SOTA performance. No eval/held-out access, provider call, credit spend, release-gate refresh, commit or push occurred. Full release scripts were excluded because they execute protected evaluations.

## Finish line

| Outcome | Verified now | Remaining |
| --- | --- | --- |
| Import and preserve varied history | Offline reviewed path; eight kinds and arbitrary measurement names | Current whole-report Muse quality remains unproven under offline-only restrictions; unsupported formats remain explicit |
| Correct records without losing evidence | Append-only correction/recovery regressions pass | Production crash/recovery qualification |
| Natural questions with original evidence | Bounded patterns above; ambiguity clarifies | Broader paraphrases, spelling variation, numeric comparators beyond BP, follow-ups such as “the one before that”, reviewed vocabulary expansion |
| Personal continuity | Direction documented in PERSONAL_SERVICE_PLAN.md | Owner-approved persistent memory, appointment status/timezones, scheduler and notification consent |
| Consistent experience | Orbit preserved; source drill-down works | Remaining T5 usability findings: stale answers while drafting, mobile targets, date/source consistency |
| Real-history deployment | Scoped evidence and offline isolation verified here | Independent qualification of masking, authorization, encryption/recovery, erasure and deployment controls |
| Release proof | Offline regression evidence recorded | Independent quality review, authorized live and protected evaluation runs, license choice (no LICENSE present), stable gates/publication; video and organizer contact remain Jason's work |

Next service priority: bounded conversational follow-ups with explicit subject/date context and the same evidence restrictions, then appointment memory. These are unfinished features, not claims that the current build is already a lifelong health companion. Clinical interpretation remains outside the contest service.
