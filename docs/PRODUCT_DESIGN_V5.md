# Modus V5 — the four archive workspaces

28 October 2026. Extend the implemented V4 Home quality to Records, Measurements, Replay and Changes. This is a presentation specification for the record-reconciliation contest entry. Preserve the broader goals, current API behavior, explicit import review, exact evidence and historical scope rules. This document does not change evaluation sets, the frozen baseline, clinical scope or model claims.

## Basis and observed problems

Use the visual system and inspected primary references in [PRODUCT_DESIGN_V4.md](PRODUCT_DESIGN_V4.md). In particular, use the quiet file hierarchy of Yuri Gokoryan's [file workspace](https://dribbble.com/shots/26819213-Team-Workspace-Dashboard-File-Management-UI), the alignment and selective emphasis of his [light B2B workspace](https://dribbble.com/shots/26731997-B2B-sales-platform-UI-Design), and the content-shaped results in his [visual response cards](https://dribbble.com/shots/27179376-AI-Visual-Response-Card-UI-06-09). These are independently interpreted principles, not copied assets or an affiliation.

The designer inspected the actual 1280×820 baseline captures in `release/polish-before-{records,measurements,replay,changes}.png` and the corresponding components. Records already has a useful master/detail structure. Measurements is clean but repeats date labels and can better group same-day evidence. Replay repeats a disabled comparison action and devotes a large dashed pane to an unavailable next step; actual results fall below the first screen. Changes gives an empty list a large card and tells a person already viewing Now to choose Now. Preserve the successful structures and fix these concrete weaknesses.

## Shared composition

- Keep the V4 wordmark rail, one destination heading, Add a record / Resume review action, neutral canvas, white document panes and phone bottom navigation. Home keeps its charcoal assistant. Other pages do not acquire dark decorative cards.
- Use 24px workspace gaps, 16–24px pane padding, thin dividers and the existing 8px spacing rhythm. Section headings are 18–20px; body is 14–16px; metadata is at least 12px. Keep full values at readable scale, with tabular numerals. Labels are sentence case.
- Keep one scope summary on Records, Measurements and Changes. Replay exposes the actual date controls. Measured-through and available-through remain distinct. Full server-resolved dates and capture time remain in a disclosure.
- Use one restrained primary action per task. Secondary actions are quiet but have visible focus and a minimum 44px target. Amber means a recorded disagreement or a failed/pending operation, never medical severity.
- At 390px, use one scrolling page with an 18px inset and sufficient bottom padding for navigation. No nested scrolling list, clipped date input, hover-only action or horizontally scrollable value table. Exact identifiers may wrap in disclosure. Exact values and units must remain intact.

## Records — choose a document, inspect its evidence

Desktop: retain a single archive surface with approximately 42% document list and 58% selected-record detail. The toolbar contains the existing content search, captured-view document/measurement totals and Export view. Optional metric chips are local filters over the captured records; label matching results separately from the API's full-view counts. Search and filters must not imply that the export changed scope.

Document rows use a 36–40px document glyph, exact title, measured date or range, and compact metric/field metadata. Use a thin selection rail and pale neutral selected state. Long names may truncate visually only when the complete name is available to assistive technology and in the detail sheet. Disagreement remains explicit text with an icon, not color alone. Do not substitute the document/report date for the measurement date.

The detail pane has the exact document title, secondary provider/provenance, document date and availability date, followed by a flat measurement table. Each row retains metric, raw value, unit and measured date. Reduce the existing large helper paragraph to one direct **Inspect source** action; the inspector retains excerpts, report times, review history and eligible original access. Authored example provenance remains accessible without becoming a page subtitle.

Phone: retain the existing direct row-to-source-sheet behavior. Do not render a second selected detail pane below the list. Search and chips wrap compactly; the export action stays reachable. An empty filtered result offers Clear filters; a truly empty scoped archive explains that no records match these dates. Never claim that no care occurred.

## Measurements — exact recorded values in time

Keep the three supported metric choices in one segmented control. A choice changes the displayed series, not the global scope. Use the metric name as the series heading and a quiet newest-first indicator. Do not add scorecards, normal ranges, inferred trends or charts.

Group entries by measurement date, newest first. On desktop, use a narrow date column and rows aligned across value/unit, source title, availability and Source action. On phone, date becomes the group heading; each row shows the full value and adjacent unit, then source title and availability, with a clear source action. Values may use 24–28px type but must shrink or wrap as a whole readable fact when precision and a long unit require it. Never round `79.1234567` to fit.

Keep every same-day conflicting observation as its own row. Give the group a restrained disagreement marker and the existing uncertainty about whether the records describe the same specimen. Do not average values, choose the newest as correct, join them with a trend line, or label a difference an improvement or decline. Source actions use the exact captured view and observation identity.

An empty metric state says there are no matching measurements in this view. It should occupy roughly one or two rows, not a hero panel. A metric unavailable in a filtered archive must not be described as missing care.

## Replay — the same measurement period, two availability views

The scope block is the primary control: **Measurements through**, **Records available by**, optional custom availability date and the existing **Compare with now** action. Retain the full-day UTC behavior and captured-now semantics. Keep the explanatory disclosure secondary. When comparison is unavailable, explain the required earlier availability beside this control; do not repeat a disabled button in a large placeholder.

Below the controls, show one shared band stating the measurement cutoff. When compared, use two equal white columns labelled **Available then** and **Available now**, each with its resolved availability timestamp. These labels describe evidence availability, not the measurement date or a continuously refreshing live state. Counts are actual API record and measurement counts, visually unboxed within each pane. Use aligned source previews and scoped inspection actions.

Without a comparison, render the selected snapshot at a sensible width and a compact next-step message. With a comparison, distinguish the columns using headings and time, not green/red or winner/loser semantics. Preserve full scope details for each snapshot. Keep Export this view / Export this comparison next to the result heading, and preserve the existing readiness guards.

Below the pair, show a slim count strip for additional records, additional measurements and unchanged measurements. Counts come from the existing comparison response. Then list actual later-arriving sources with their availability timestamps and inspection action. A measurement can be old while its source arrived later; do not call the measurement itself new. No later arrivals is a quiet result, not a success badge.

Show actual disagreements next, with both raw values, units, measurement date and distinct source actions. Keep the existing uncertainty and no automatic resolution. Place the scoped question workflow below the comparison/evidence, so it does not compete with the page's primary comparison task.

Phone: stack the two columns in the same order, preserve their explicit timestamps, and keep the shared cutoff before both. Date controls fit the viewport with 44px targets. Allow natural vertical scrolling rather than reducing facts to small text. Comparison loading/error states retain the existing selected data truthfully; never replace a failed comparison with a completed visual.

## Changes — an honest activity ledger

Use a compact heading row with the resolved availability boundary and Refresh history. The API-provided actions form a flat chronological list separated by rules. Each item has time, a small type glyph, a human-readable action and its actual status. Use exact record identity or submitted question text when the payload supplies it. An import can show its actual measurement count and availability time; an extraction failure shows its actual error state. Render an unknown kind honestly rather than guessing that it was a record question.

Optional All / Records / Questions / Issues filters operate only on the loaded scoped activity. They must not fabricate categories, replace source state, or hide a real error as success. Distinguish an empty filter from a scope with no recorded actions. Preserve the original event kind/status in a compact event-details disclosure together with exact times, IDs and scope when supplied. A successful local deterministic question must not be labelled a model response.

Use **Inspect record** only when the source exists in the displayed captured view. Do not leak a later source from a historical activity row. Question execution details stay optional; this page does not expose hidden reasoning or imply that an agent is working in the background.

Phone: time is a 12px secondary line above the action; body and status wrap naturally; any source action remains at least 44px. The empty state is a small left-aligned block such as **No activity in this view**, with a relevant next step. If already viewing Now, do not suggest choosing Now. Loading, refresh failure, stale-scope protection and Retry retain their existing behavior.

## Verification required

The implementation owner and coordinating agent retain behavior verification and full release-gate ownership. Visual acceptance requires actual new desktop and 390px phone captures for each page, plus populated Replay and Changes states; an empty seeded ledger alone does not verify activity design.

- Records: filtering and clearing; selected document; phone source sheet; matching counts versus full-view counts/export; long title and exact evidence.
- Measurements: each metric, same-day disagreement, full-precision value/unit, source inspection and a genuine empty metric.
- Replay: selected-only state, unavailable comparison, actual historical/now pair, late-arriving record, unchanged measurement cutoff, disagreements, source actions, scoped export and failed/loading state.
- Changes: real import/question/failure where available in the isolated test store, exact event disclosure, source action restricted to the view, filtering, historical empty state and refresh failure.
- Shared: no horizontal overflow or bottom-navigation occlusion at 390px; metadata at least 12px; visible keyboard focus and 44px targets; scope changes remove stale answers and keep exports/source actions guarded.

No fake records or activity may be inserted into the person's main store to improve screenshots. Use the coordinating agent's isolated disposable test store for actual review/import/question actions. No new backend or evaluation-set changes are required by this design specification.

## Independent review of the first implementation

The designer inspected all eight actual `release/polish-{records,measurements,replay,changes}-{desktop,mobile}.png` captures: 1280×820 desktop and 390×844 phone, using the coordinating agent's isolated seed store. The quieter scope summary, useful record filters, exact measurement emphasis, single Replay comparison control and flat Changes empty state follow the intended hierarchy. No clipping or contrast blocker was visible in these captured states. The coordinator separately checked page overflow and found a small metric-filter target, which the implementation owner reports correcting to 44×44px.

One action-placement correction was requested: move the existing desktop Records **Inspect source** action near the selected document's header/date area. With the larger value rows, its old footer position falls below the 820px initial viewport. Removing Measurements' redundant **Recorded measurement history** eyebrow is an optional density cleanup. Neither change affects source identity or scope.

These screenshots cover a three-document/nine-measurement seed view and an empty activity ledger. They do not establish the quality of populated comparisons, conflicting measurements or real activity rows; those states require the subsequent interaction captures. This review is a visual inspection, not a user study or a complete accessibility audit.

## Populated-state review

The designer subsequently inspected `release/polish-replay-populated-{desktop,mobile}.png` and `release/polish-changes-populated-{desktop,mobile}.png`. The coordinating agent created these through an actual reviewed import and a scoped record question in the isolated store, not fabricated ledger entries. The desktop comparison makes the shared 28 October 2021 measurement cutoff and the differing 2021/2026 availability timestamps clear. Its actual two-document/six-measurement and three-document/seven-measurement counts remain distinct.

The populated Changes screenshots show the submitted question, reviewed source title, actual completion status, timestamp and local execution mode. The phone layout includes both events and the source action above the bottom navigation without visible clipping. Exact event disclosures remain secondary. No additional visual correction was requested for these states.

The first-viewport Replay captures do not show the lower later-arrival or disagreement sections. The designer subsequently inspected `release/polish-replay-scrolled-mobile.png` and `release/polish-replay-conflict-mobile.png`. The current snapshot shows three documents and seven measurements with explicit availability time and a separate exact-scope disclosure. Later arrivals shows one actual additional measurement, six unchanged measurements, one new disagreement and the imported document's availability timestamp.

The disagreement pane displays the full `80.1234567` and `96` values with their units and distinct source titles. It preserves the 8 April 2021 measurement date and states that whether they describe the same specimen is unknown. Both source actions are visible and the pane fits the phone width. No additional visual correction is required for the reviewed lower Replay sections.

Independent visual review is complete for the captured seed and populated desktop/phone states. The final source-action placement and minimum-target corrections are recorded by the implementation owner, with the coordinating agent responsible for the final rebuilt-page check. Interaction correctness, scope isolation and exported values are verified separately; screenshot inspection alone does not prove them. These results establish the quality of the reviewed states, not clinical validity, live-model performance or a universal accessibility certification.
