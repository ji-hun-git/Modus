# Modus Home and services — product design v3

28 October 2026. Independent product-design research and implementation brief. Primary product pages and Apple/Toss design guidance were read for this review; local participant rules were inspected. This is an expert comparison, not user research, a clinical assessment, an endorsement or a performance benchmark. No private evaluation directory, held-out input or generator was accessed.

## Updated direction

**Home becomes the starting page.** It should feel like the entrance to a useful personal service: ask about the records, review a new document, open a measurement history, or look at what changed. The user explicitly asked to remove the synthetic provenance subtitle and generic explanatory subtitles from the main interface. That supersedes v2's requirement to put a provenance sentence below the page title and its Records-first landing decision.

Keep the existing **Demo data** disclosure accessible, preserve synthetic-only import consent, and label the execution actually used for each extraction or answer. Removing repeated explanatory copy is a presentation change; it does not turn invented data into real personal records, offline tools into a model, or prepared integrations into completed connections. The broader lifelong health-intelligence goal and all registered project goals remain unchanged.

## What comparable services teach us

This comparison separates what the source describes from the Modus design inference. It does not compare clinical quality or reproduce competitors' performance claims.

| Primary source | Observed product pattern | Useful Modus application | Capability not implied for Modus |
|---|---|---|---|
| [Apple Health: view health records](https://support.apple.com/en-ph/guide/iphone/iph2b3a37ddd/ios) | Records are accessible through search, categories and source organizations, with detail views and pinned lab results. | Keep the source list and measurement history easy to reach from Home; open detail from a row without an extra explanatory screen. | Hospital-account connections, automatic sync, pinning and Apple's privacy infrastructure are not implemented by copying the layout. |
| [Apple Health: download records](https://support.apple.com/en-ie/guide/iphone/iphc30019594/ios) | Adding a supported organization is a concrete connection flow; new records can arrive after setup. | Make **Add a record** a direct review workflow and show genuine additions in Changes. | No **Connect hospital** button until an actual supported integration and consent flow exist. |
| [Guava: product guide](https://guavahealth.com/article/guava-ultimate-guide) | An accessible assistant complements a searchable record timeline and record-type views. | Place the working question composer prominently on Home, while retaining direct navigation to the evidence. Use a few supported prompts to make the first interaction obvious. | Voice logging, automated record writes, broad clinical questions, symptom tracking and connected portals are outside this entry's current tool contract. |
| [Function: how it works](https://www.functionhealth.com/how-it-works) | The service is organized around a short sequence: obtain testing, review results, and return over time. Its results workflow includes clinician review. | Make Modus's sequence equally concrete: add → review → inspect → compare. Name the next action and preserve the original record at each stage. | Testing services, clinician review, treatment/nutrition guidance and clinical results interpretation are not Modus capabilities. |
| [Oura Advisor: member guide](https://support.ouraring.com/hc/en-us/articles/39512345699219-Oura-Advisor) | An optional conversational tool sits within an existing data product. Its guide explains data context, conversation history and adjustable controls. | Let a person ask about the currently selected records and see the evidence behind the answer. A saved answer must retain its original scope. | Coaching, predictive scores, persistent conversational memory and specialist health models are not established Modus features. |

The common useful pattern is a small number of direct actions over an inspectable personal record. Our inference is to combine a simple Home with a bounded question interface and explicit evidence drill-down. More decorative service cards, more model names or more runtime agents do not establish more user value.

## Apple and Toss principles applied

[Apple's layout guidance](https://developer.apple.com/design/human-interface-guidelines/layout) emphasizes hierarchy, alignment, grouping and progressive disclosure. Put the current task near the top, keep related controls together, and move technical provenance into reachable details. Retain readable type and clear controls when the layout narrows. This web interface does not need to imitate Apple materials or assets.

[Toss's design account](https://toss.tech/article/design-motivation) describes focusing a page on one main message. Home's main purpose is to start a useful record task, not display every possible feature. [Toss's UX-writing interview](https://toss.im/tossfeed/article/uxwriter-interview) supports concise, consistent wording that removes nonfunctional words. The application can use **Home**, **Records**, **Measurements**, **Replay** and **Changes** without a paragraph under each title.

Keep the v2 white/gray canvas, system sans-serif, graphite type and restrained blue actions. Avoid promotional hero areas, pseudo-clinical illustrations, decorative score rings, gradients, specialist-agent avatars, scripted agent chatter and repeated security badges.

## Home hierarchy and copy

1. A compact greeting such as **Hi, Alex**, with **Add a record** (or **Resume review**) in the main action position. Do not add a slogan or generic service subtitle.
2. **Ask Modus** with the actual working question composer. Use a task-specific placeholder such as **Ask about records, dates or differences…**. Place the send action inside or next to the field. Keep it usable by keyboard and on a phone.
3. Two or three supported starting prompts: **Which records are available?**, **Where do records disagree?**, and **What arrived later?** The last requires a bound comparison; without it, offer a clear path to Replay rather than making an unscoped question request.
4. A compact **In this view** count strip using the server's document, measurement and disagreement counts. Each useful count can navigate to the corresponding Records, Measurements or Replay view. These are inventory facts, never a health score or a completeness rating. Avoid three oversized statistic cards.
5. Up to three real scoped source rows with an explicitly labelled document date and source inspection, followed by **View all records**. Use **Latest documents in this view** for document-date ordering. Optional measured-date metadata must be labelled separately. Do not imply clinical recency from document availability without a date label.
6. Short secondary service links when needed: **Measurements**, **Compare records**, **View changes** and **Export this view**. Prefer a compact list or toolbar over another grid of marketing cards. Do not duplicate every link if navigation and the count strip already provide it.

The question area should precede secondary content on Home. In an active question, show a real pending state, the exact supported response, evidence links and the actual execution mode. **Local record tools · no model call** is appropriate for deterministic execution. A failed Meta request remains a failed request; no silent offline success under a Meta label. Technical tool inputs/outputs and request metadata stay under a disclosure.

Call the surface **Ask Modus** rather than advertising a team of medical specialists. The implemented application has bounded tools and an optional model selector; it does not have a verified multi-agent clinical team. A service-like interface comes from useful working interactions, not a fabricated agent roster.

## Six concrete flows

| Flow | Person's action and useful result | Honest implementation scope |
|---|---|---|
| **Ask about this history** | Ask which records exist, which values disagree, or what arrived between captured availability views; open supporting evidence. | Reuse the scoped question endpoint and supported typed claims. Do not interpret risk, diagnosis, normality, treatment or care quality. |
| **Review a document** | Add a supported synthetic file, inspect the original and proposed fields, edit/exclude, then explicitly add selected rows. | Preserve extraction mode, field provenance, unknown dates and review/commit/retry controls. The model cannot commit. |
| **Inspect measurements and sources** | Choose HbA1c, eGFR or LDL; read chronological recorded values with exact units and dates; open any original/source detail. | New Measurements presentation over the existing scoped observations. Preserve multiple same-day values and API-defined disagreement labels. No client-created trend score, clinical range or silent unit conversion. |
| **Compare record availability** | Choose a measurement period and earlier availability cutoff, then compare with captured current availability. | Reuse the frozen dual-time comparison. Show actual additions and preserved disagreements; no claim about what the person or clinician knew outside Modus. |
| **See what changed** | Open a real import/question/failure event and inspect its recorded result. | Existing Changes history and commit identity. A duplicate retry adds zero rows and points to the original save. No invented audit event, automatic correction or undo. |
| **Carry the evidence forward** | Export the selected captured view, with dates and provenance retained, and download eligible source originals. | Existing scoped JSON export and original downloads. Do not label this a clinician-reviewed report, comprehensive medical summary or hospital integration. |

These flows are more useful than a static set of analysis teasers because each has a real action, a result and a route to its evidence. New clinical services are not required to make Home functional.

## Measurements service

Use one metric selector and one chronological list/table. Each row shows **Measured**, **Recorded value** with the exact unit, and **Source**. Source details preserve report-issued and Modus-availability dates separately. Use the server's conflict grouping to label disagreement; equality of values does not prove specimen identity. A source with multiple observations remains inspectable per observation.

Keep neutral value styling. Do not add up/down arrows that imply improvement, population reference bands, red/green health states, generated interpretations, or medical recommendations. This page is a way to inspect measurements over time; analysis in the contest entry remains record inventory, disagreement and availability comparison.

On a narrow screen, rows stack predictably and open the existing source dialog directly. Long printed units wrap without clipping. With five destinations, desktop can use full labels; a mobile label such as **Values** may stand for Measurements if its accessible name and page title retain **Measurements**. Do not shrink essential labels below readable size merely to fit navigation.

## What belongs now, in the broader research app, or later

| Layer | Current or proposed disposition |
|---|---|
| Home, Records, Measurements, Replay, Changes | Working entry presentation over the current bounded API; this milestone must verify actual navigation, scoped answers, source opening and review behavior. |
| Deterministic record tools | Available without credentials and labelled as such. Their purpose is inspectable record facts, not medical advice. |
| Local OCR | Optional actual local model path for supported synthetic documents. Installation/configuration alone does not prove successful inference; each operation retains actual mode/result metadata and still needs review. |
| Meta extraction/tool selection | Adapter preparation and configuration are distinct from successful real execution. Retain actual model/request/failure/usage evidence when a separately authorized live run occurs. This design review makes no provider request. |
| Broader longitudinal medical research | The wider Modus application already contains separate experimental analytical work and illustrative contexts. Preserve it and its goal registry, but do not expose excluded interpretation through the contest entry's routes or service cards. |
| Clinical interpretation, advice, treatment or risk services | Future product/clinical work with explicit intended use, qualified review, appropriate evidence and real-data controls. A disclaimer or a polished dashboard does not establish these capabilities or contest eligibility. |
| Connected records, wearables, real-data accounts and sharing | Future implemented integrations and authorization/consent work. No decorative connection buttons, fabricated sync status or security guarantee. |
| Trained model and persistent assistant memory | Prepared data or a role prompt does not establish training or memory behavior. Require actual implementation and measured evidence before claiming either. |

The data identity remains unchanged: the entry begins with three authored synthetic source documents and nine measurements; a local store may contain reviewed additions and a selected view may contain fewer records. The broader Synthea cohort, training preparation and evaluation materials remain separate. The accessible Demo data dialog should explain this without an intrusive subtitle on every page.

## What “do what Meta wants” means for this entry

The current [official event page](https://cerebralvalley.ai/e/meta-ai-developer-hackathon) asks entrants to build with Meta models and emphasizes useful domain problems and working technical execution. It does not establish a requirement to use every model, add a multi-agent council, fine-tune a model or display an AI dashboard. The recommendation is one convincing end-to-end demonstration with actual model evidence when available.

Local [participant instructions](../research/PARTICIPANT_RULES.md) record the owner's supplied exclusion of AI medical/health advice, a public event-built repository, a three-minute video and contribution disclosure. Those private participant excerpts were summarized locally but were not independently authenticated in the participant account by this reviewer. The same document states that the record-integrity entry has not received organizer eligibility confirmation. The recorded judging-weight discrepancy between participant FAQ and public rules remains unresolved. Do not advertise approval or resolve the discrepancy by choosing the convenient version.

| Evidence area | Concrete demonstration to prepare |
|---|---|
| Useful problem | A late document changes the current record reconstruction while the earlier replay remains unchanged. Explain the time/evidence problem in plain language. |
| Actual Meta use | A real authorized synthetic extraction or tool-selection request, with the returned identity, supported result and trace. A configured key, logo or model selector is insufficient. |
| Technical execution | Review-before-commit, exact scope propagation, preserved disagreements, source access, duplicate-safe retry and a runnable isolated entry. |
| Clear demo | Home question → evidence → new record review → preserved earlier replay → current comparison. Show only completed operations; disclose contributions and external components. |
| Measured evidence | Report actual development results and limitations; keep independent/held-out claims separate. A successful software gate does not establish clinical performance. |

This mapping guides preparation, not publication, spending, live model execution, organizer contact or submission authorization.

## Harness, ontology and retrieval decisions

No new runtime framework is justified by a new Home screen. The existing typed observation/source schema, fixed metric set, bounded tools and exact claims support these six flows. A formal medical ontology or graph-memory rewrite is unnecessary for three metrics and would not by itself improve source support. More complete terminology mapping may become useful when broader record types are actually supported, but ambiguous mappings must remain visible.

Likewise, retrieval should answer an identified missing-source task under the same time bounds. Source IDs alone do not support a sentence; support depends on the original facts, tool computation and claim semantics. Do not add a RAG marketing label, external clinical corpus or model-generated recommendation to make Home appear more intelligent. Retain development verification for changed behavior and do not access private evaluation inputs during product iteration. No SOTA claim follows from this design or from adopting a named technique.

## Independent review criteria

These are acceptance requests until supported by implementation evidence:

1. Home loads by default. The greeting and working composer lead; generic and synthetic provenance subtitles are absent from the main UI as requested. Demo data and import consent remain available.
2. Every visible prompt/action works or gives an accurate disabled-state explanation. A comparison question cannot run without bound comparison context. No card implies unsupported clinical or connected services.
3. Counts come from the scoped API, state **In this view**, and are kept distinct from local search matches. Home/Measurements/Records use the same resolved scope; changing it clears stale evidence/actions until matching data loads.
4. Measurements preserves all values, dates, units and API conflict labels. A row opens the correct source; unknown report issue time remains **Not recorded**. No clinical meaning is inferred from visual styling.
5. Home question responses retain exact supporting evidence, actual execution identity and captured scope. Navigation or a scope change cannot relabel an old answer as current.
6. Add/review/commit retains draft state, selected row counts, explicit review, uncertain-save identical retries and confirmed-save/failed-refresh separation. Navigation to Home cannot bypass an active commit.
7. At 390 px, the primary task is readable, all navigation remains reachable, meaningful controls have adequate targets, and no value/unit/action is clipped. Source dialogs open immediately from mobile rows and restore focus on close.
8. Keyboard navigation, focus containment, pending/empty/error states and reduced motion remain usable. Record screenshots and interaction observations separately; screenshots do not prove live behavior.
9. Report which tests and builds actually ran, with no invented human research, retention gains, trained-model results, clinical validation or eligibility claims.

Implementation screenshots and an independent visual audit will be appended after the revised Home and Measurements surfaces are available. This document alone is not a passed acceptance test.

## Implementation review

Independently inspected `entry/demo/service-home-desktop.png`. The Home composition meets the requested simpler service direction: a compact greeting and add action lead to a working-question surface, three concrete prompts, a small scoped count strip and recent documents. The repetitive main-screen provenance and generic subtitles are removed while Demo data remains accessible. The execution mode and captured dates sit with the question tool, without implying an unexecuted model or specialist-agent team. No visual blocker or additional restyling was requested for this desktop Home.

The implementation owner separately reported an actual browser question returning the clean fixture's nine measurements/three documents, nine evidence links and the correct source modal. That is attributed interaction evidence, not an execution by this visual reviewer.

Independently inspected `entry/demo/service-home-mobile.png` and `entry/demo/service-measurements-mobile.png`. Both are visually accepted. Five destinations remain readable using icon/short-label navigation, Home keeps the composer and supported actions first, and Measurements presents its metric selection, measured dates, exact value/unit and source action without visible horizontal clipping. The 2021 source-title date and its actual measurement date remain distinct. Neutral value styling avoids a health-status implication. No mobile design repair was requested.

The implementation owner separately measured a 375 px content/scroll width under a 390 px viewport override, all 14 visible measurement-view buttons at least 44 px high, and mobile navigation targets of 57 × 66 px. These are attributed browser measurements; the independent review above is visual.

Independently inspected `entry/demo/service-measurements-desktop.png`. The desktop Measurements view is accepted: the selected eGFR metric, captured scope, exact units and source actions are clear. The imported value 79 and authored value 96 are both retained for 8 April 2021 with disagreement labels; their 2026 and 2021 availability times remain separate. The older value 99 stays visible as its own dated record. No visual treatment selects a medically correct value or suggests improvement, deterioration or diagnosis.

The implementation owner reported an isolated browser rehearsal starting from a 2021 view with two documents/six measurements, uploading the late synthetic value 79, editing it to 78, leaving review for Home, resuming the edit, restoring 79 and explicitly committing. Home retained the original historical two/six counts; the updated Measurements view displayed both disagreeing values with their separate availability dates. This is attributed interaction verification of the preserved flow, not a test run by this design reviewer.

**Final design acceptance:** Home and Measurements satisfy this milestone's requested service direction on the inspected desktop/mobile screens. The main provenance subtitle is removed, the real question tool is prominent, and working record services remain connected to exact scoped evidence. No additional design blocker or cosmetic iteration is requested. Software gates and final runtime identity remain the implementation owner's delivery checks; no clinical, user-research, eligibility or model-quality claim follows from visual acceptance.
