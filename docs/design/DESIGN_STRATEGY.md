# Modus design strategy — 29 October 2026

The owner’s current direction is a personal health-history service with the black-and-white orbit Home. The orbit represents real source files; selecting one exposes the recorded content and original evidence. This document is the active design working agreement for Home, import, review and Ask. Earlier V2–V7 design files and supplied references remain context, not simultaneous requirements to stack on the screen. Owner feedback takes precedence.

## Why the earlier iterations kept failing

The product repeatedly changed colors, cards, visual metaphors and typography while keeping the same crowded task hierarchy. Add, Ask, Replay, Brief, queue, dates, availability, counters and technical status all competed for attention. Applying another visual reference did not fix that.

The references work because one meaningful result dominates, its evidence is nearby, and secondary actions are quiet. We copied some surface traits without consistently protecting that hierarchy. More explanatory text then tried to compensate for the unclear layout. The result made the person operate a record system before seeing their own health history.

“Personal” must come from the person’s actual reports, dates, chosen questions and corrections. It cannot be supplied by a fabricated name, a health score, a generic greeting, or a model pretending to know how someone feels.

## The product job to preserve

**See what my report recorded, connect it to my earlier records, and check the original.**

Home should make this job recognizable before explaining the software. The value, unit, recorded date and source carry the page. The current contest service preserves facts and differences; it does not generate medical interpretation, diagnosis or advice. Familiar medical wording is appropriate when supported by the record. Unknown terms keep their original spelling; plain-language labels must be reviewed mappings, not guesses.

## One hierarchy across future iterations

1. **Home:** one Add/Continue review action, one direct Ask action, selected report content with evidence, and the working timeline. Orbit satellites remain file selectors. Choose a field through one control instead of a strip of repeated buttons. Past-view settings and exports live in History options. Show a conflict entry point only when the scoped records actually conflict.
2. **Import and review:** one current decision at a time. State what was read and what needs attention, put the source beside the proposed fact, and keep the explicit save consequence visible. Coverage, failures, changed values, exclusions and uncertainty are functional information, not decorative status badges. Never shorten copy by hiding a failure or pretending the report is complete.
3. **Ask:** lead with the answer or one necessary clarification. Dates and citations remain attached to the statement. The model/tool trace belongs in a disclosure. A failed or offline run keeps its actual identity; a conversational tone cannot relabel execution.
4. **Source:** preserve the original quotation and download, recorded date, availability scope and any reviewed edit. Full metadata can be one level deeper. Evidence must not be hidden behind a decorative visualization or replaced by a summary.

Use sentence case and ordinary language for primary controls. Reserve monospaced type for values and precise dates. Keep the current palette and orbit geometry stable while testing this hierarchy. Do not introduce a new illustration, anatomy view, card collection, color theme, score or agent panel unless an observed task failure requires it.

## Three task-based acceptance checks

These are acceptance criteria, not a claim of observed user-study success.

| Task | Required outcome |
| --- | --- |
| Find a result and check it | From Home, choose a file and field; see its exact value/unit/date and source excerpt without navigating to another workspace. Open the full permitted source from that evidence. Same-date disagreements and review edits must remain visible. |
| Ask about an earlier record | Ask a factual history question, clarify an ambiguous number once when necessary, then open the supporting record from the answer. The source must match the answer’s occurrence and availability scope. No result may be invented when the history does not support it. |
| Add a mixed report | Read, inspect uncertainties, edit/exclude a field and save the explicit selection. Confirm the new record appears in history while the original stays unchanged. A failed page must not be presented as successfully read. |

Check each at desktop and 390 px, with mouse and keyboard. Check an empty history, a long report, a partial date, a conflict and a historical cutoff. Record an actual screenshot and the task result. Build/test counts alone cannot establish design quality.

## Stewardship

The design agent has a separate responsibility during this task: identify the largest task friction, make a restrained change, inspect the actual result, and report what remains. It is a development collaborator, not another model in the shipped product or an autonomous background service.

Each subsequent pass should name one problem and its expected observable improvement before editing. Prefer removing a duplicate action or clarifying a decision over adding another panel. Keep a screenshot of the actual result; preserve source and date behavior; seek the owner’s feedback on the working flow. Do not claim “best design” from a reference match or a synthetic judge score.

## T3 Home changes in this pass

- “Your health history” replaces archive-oriented headline copy, with the real current date.
- A labeled field selector replaces the horizontal strip of every recorded item; all fields remain accessible.
- The orbit, selected record, exact source evidence and conflict comparison remain intact.
- Timeline and Ask remain directly visible. Exact date/availability, past-view comparison and brief preparation move into History options.
- Empty queue action, repeated archive totals and repeated availability text are removed from the main reading path. Pending reviews remain available through Continue review and the disclosed count.
- No clinical claim, personal identity, provider call, evaluation run or model-quality assertion is introduced.

Remaining design work is targeted rather than another reskin: validate the T3 report-coverage and clarification flow in the actual app, then use the three tasks above with the owner. The permanent top-level navigation and whole-app visual unification need a separate reviewed pass; this small Home change does not claim to solve them.

## Local check in this pass

The frontend TypeScript/Vite build passed before integrated T3 completion. In a separate offline browser tab, the 16-entry authored report remained one orbit satellite; the field selector exposed all 16 entries. Selecting Pulse displayed the reviewed `73.00 bpm` beside the original `72.00` excerpt, and Inspect source opened the correct full evidence view. Escape returned to Home. History options opened and closed by keyboard and retained the exact date, availability, comparison and brief actions. No browser console warnings or errors were observed in this path.

The captured desktop result is `release/T3-design-home.png` (local artifact). At a 390 px viewport, the DOM reported 375 px document width and all 16 options with History options collapsed; that check found no horizontal overflow. The browser screenshot API failed after the viewport override, so this pass does **not** claim completed mobile visual verification. The override was reset and the isolated tab closed. The integration owner should inspect a final mobile screenshot after the combined build. No import, Ask submission, model request or data write was performed during this design check.

Integrated follow-up: the root agent captured and inspected the actual 390 px orbit and lower evidence/timeline screens (`release/T3-home-mobile.png`, `release/T3-evidence-mobile.png`). The field selector, reviewed value, original excerpt, source action and History options remain reachable, with no visible horizontal clipping. The viewport was reset. Desktop compound Ask, clickable evidence and blood-pressure clarification were exercised in offline mode. This closes the mobile screenshot gap above; it does not replace owner usability feedback or establish whole-app visual consistency.

## Next service pass — import, review and Ask

The friction addressed here is the shift from a focused orbit Home into a crowded administration form. The expected improvement is one recognizable next action at each stage: choose a file, read it, check the recorded fields, then explicitly save the selection. This is a task-hierarchy pass, not a new visual direction.

- The selected filename leads every stage. The file queue and example downloads are disclosures; oversize/omitted file notices remain visible. File selection still sends nothing, and model reading still requires its existing explicit choice.
- Review places editable names, exact values, printed units and recorded dates beside the original excerpt. All source excerpts are visible, including for excluded fields. Required name/value inputs stay outside closed disclosures so browser validation can focus them.
- Type, facility and the original proposal are secondary details. Restore is shown only when the proposal has changed or the field was excluded. The original evidence is never edited by these controls.
- Field concerns, unsupported fields, failed source checks and failed/unread/no-field page counts remain visible. Page processing never claims that every detail was extracted. Full page and source-check ledgers remain available.
- One explicit save action shows the included count and original-preservation consequence. Saving, uncertain saves, identical retries, exclusion, skip and queue recovery retain their existing behavior. Closing a tab still loses unsaved reviews; the notice remains on screen.
- Import uses the same monochrome tokens as Home, thin rules and restrained corners. Desktop review uses two columns for the proposal and source; narrow screens stack them within each field. No added cards, personal identity, care claim or animated ornament is part of this pass.
- Ask follows the same question → answer or clarification → evidence sequence. Exact tool claims and scoped evidence remain authoritative; model/tool execution details are secondary. The integration owner owns that implementation and integrated verification.

Build checks and the offline desktop/mobile task walkthrough are reported by the integration owner after the combined service pass. These choices alone are not a verification result or a claim of user-study success. Evaluation sets, API calls and publishing remain outside this pass.

Integrated verification: 110 frontend and 100 focused backend tests passed, plus the frontend build. Two fresh authored files passed local read → edit/Restore/exclude → explicit save → next-file flow. Closing/reopening review preserved edits. Ask retrieved the corrected 71.00 value alongside its original 70.00 quotation; the original download matched byte-for-byte. The blood-pressure ambiguity still required top/bottom clarification. At 390px, Ask's document width was 375px and the review dialog's scroll width equalled its 353px client width; both were visually inspected. Required-name validation focused its visible header input; exclusion disabled it. No console warnings/errors were observed. The viewport was reset. Screenshots and details are in `release/T4-*`. Owner usability feedback and consistency of the remaining secondary workspaces are still outstanding.
