# Modus design direction — an archive people can use

28 October 2026. This revision responds to the owner's criticism of the interface and request to study Yuri Gokoryan's work. It supersedes v3's visual composition while preserving the existing Home, Records, Measurements, Replay, Changes, review and evidence behaviors. These are design requirements, not claims of user testing or completed implementation.

## References inspected

The designer's [own site](https://yurigok.com/), [Dribbble profile](https://dribbble.com/yurygok) and [Layers profile](https://layers.to/yuri) establish the correct person. Four original Dribbble images were inspected at useful resolution, alongside Modus's actual desktop and phone screenshots. Reference images were reviewed in an OS temporary directory, not copied into application assets or the source distribution. The observations below are our visual analysis, not the designer's stated rationale or endorsement.

| Primary reference | Observed design decision | Transfer to Modus |
|---|---|---|
| [AI Agent Observability Platform](https://dribbble.com/shots/27408472-AI-Agent-Observability-Platform-UI-Design) | A narrow navigation rail, compact controls, clearly separated dark surfaces, aligned metrics and a readable activity column create order in a dense workspace. | Give navigation a stable small footprint. Separate the assistant from the archive using surface contrast. Align labels and values rather than wrapping every item in a new panel. Do not imitate its operational charts or suggest that Modus runs an agent fleet. |
| [AI Visual Response Cards 06–09](https://dribbble.com/shots/27179376-AI-Visual-Response-Card-UI-06-09) | The response becomes a structured object: a strong primary value, contextual labels, aligned detail rows and a quiet action footer. | Make returned record facts and their sources the main response content. Keep execution details in disclosure. Preserve full values and units; use only typed returned facts. Never copy the example's advice, percentages or charts into health records. |
| [Team Workspace / File Management](https://dribbble.com/shots/26819213-Team-Workspace-Dashboard-File-Management-UI) | Files have a recognizable object treatment; compact lists carry title, activity and time. Mobile hierarchy comes from scale and proximity, not a pile of page headers. | Give source rows a consistent small document glyph and exact title/date. Make the full row an inspection target. Move mobile destinations to a bottom bar so the first screen contains useful work. |
| [B2B sales platform](https://dribbble.com/shots/26731997-B2B-sales-platform-UI-Design) | A light, largely flat composition uses strong typography, meaningful scale and thin dividing rules. The emphasis is selective. | Keep the archive light and calm. Use actual API counts as an unboxed strip. Use hierarchy and alignment to make the page distinctive without inventing analytics. |

These examples have different palettes and levels of depth. The useful commonality is deliberate composition and information hierarchy. No reference establishes usability or accessibility outcomes for Modus.

## What is wrong with the inspected Modus screen

The current desktop screenshot spends most of its upper half on an empty pale composer, three similarly styled prompt buttons and several nested boundaries. The record list starts low on the screen. Important objects, secondary metadata and primary actions have too little difference in visual weight.

The navigation says Alex's history, the breadcrumb says it again, and the page then greets Alex. The rail also repeats the product and research label at its foot. These repetitions occupy attention without helping a task. The blue treatment is applied so broadly that it feels like a default component library.

On the 390px phone screenshot, the logo, five-item top navigation, breadcrumb and heading consume the top of the page. The composer and vertically stacked prompt buttons then consume nearly all the remaining viewport. The records begin beneath the first screen. A simple service should reveal useful context before asking a person to scroll through its controls.

## Chosen composition

Use a light personal archive with a single charcoal assistant surface. The archive and the assistant have different jobs and should have different visual emphasis. Build the composition around actual records, exact results and a clear way to ask a question.

Desktop structure:

1. A 192–208px navigation rail with the Modus wordmark, one history identity and the five existing destinations. Remove the repeated research footer. Keep the actual demo-data explanation accessible from its existing control.
2. One compact heading row: **Your history** on Home, the destination name elsewhere, and **Add a record** / **Resume review**. Remove the Home breadcrumb and greeting duplication. Do not add a slogan or explanatory subtitle.
3. An unboxed strip of the current API's document, measurement and disagreement counts. Use 32px tabular numerals, short labels and light vertical dividers. Each remains a real destination action. These are record counts, not a health score or completeness assessment.
4. A two-column work area: approximately 7/12 for the charcoal question/answer surface and 5/12 for recent records. Use a 24px gutter and `minmax(0, …)` columns. The assistant can grow after an answer without forcing the document list to stretch into empty space.
5. Recent documents use compact source rows, then one useful history/replay action. Keep all titles and dates sourced from the returned view. A disagreement indicator uses amber and explicit text, without implying risk or selecting a correct source.

At a 1280×720 viewport, the page should show its heading, real counts, usable composer and recent records together. Do not add a hero illustration, decorative chart, avatar fiction, empty agent cards or a large “welcome” region to fill space.

## Visual system

| Role | Requirement |
|---|---|
| Outer archive canvas | `#F4F4F1`, a slightly warm neutral. Use white for document surfaces and sheets. |
| Main text / secondary text | `#161818` / `#626B6A`. Actual values and document titles receive the stronger color. |
| Separators | `#DFE2DF`; use rules to organize related rows. Avoid a border around every group. |
| Assistant surface | `#191A1B`; raised input `#242527`; boundary `#3A3D40`. Primary text `#F5F5F4`, secondary `#B2B5B8`. |
| Action color | Keep one restrained blue for the primary action and focus. Other actions use neutral text/surfaces. Amber is reserved for record disagreement or a pending review condition. |
| Type | Existing system sans-serif stack; no unlicensed font dependency. Title 32/38px, weight 600, approximately −1px tracking. Body 14–16px with 1.45–1.55 line height. Secondary labels at least 12px. Counts 32/36px with tabular numerals. |
| Spacing | 8px base rhythm: 8/12/16/24/32/40. Main content 32–40px inset on desktop, 18px on phone. Maximum content width approximately 1120px. |
| Shape | 16–20px radius for the main assistant surface; 10–12px for inputs/controls; rounded document glyphs. Use restrained depth only where it clarifies elevation. |
| Icons | Continue the existing icon family. Use a small native CSS/vector document treatment for sources, not copied folder art or unrelated decorative symbols. |

The table gives implementation values for a coherent starting point, not a claim that these exact values were measured from the references. Verify contrast in the implemented states, especially muted text, placeholders, disabled controls and focus rings.

## Assistant and response behavior

Keep **Ask Modus** as the functional heading. Place the true execution state next to it, in a compact secondary position. **Local · no model call** must remain legible in offline mode. A configured provider cannot be represented as a completed live request.

The composer should be 72–88px tall at rest, with a clear send target at least 44px square. Avoid making the empty input the largest object on Home. Use a short wrapping row of existing supported examples. On phones, do not turn every example into a full-width 48px row; keep the composer usable and the records close.

Preserve one visible scope summary next to the question workflow: **Measured through …** and **Available …**, with the existing **Change dates** action. Keep full resolved timestamps available and retain exact API scope values. Do not replace availability with “updated today,” collapse the two clocks into a single range, or duplicate scope controls across several surfaces.

After a request, present selected typed facts as compact answer rows with a clear source-inspection action. A source hash is not useful prose. Exact IDs remain in data and trace; people see the metric label, full recorded value/unit, measurement date and source title on inspection. Do not parse arbitrary answer strings into invented chart values.

For an existing answer, the eye should find its facts first, then source actions, then execution details. **How this result was made** stays an optional disclosure. Request failures remain explicit. Scope changes must remove stale answers and disable stale exports/source access exactly as before.

## Records and review

Recent source rows are 64–72px tall with a 36–40px document glyph, an exact title, a quiet date and a directional affordance. Title and date align across rows. Long titles truncate visually but remain available through their accessible name and inspector. The whole row opens the source, with keyboard focus visible.

The source inspector should feel like a document sheet: clear title, measured/report/availability fields, retained original excerpt and eligible original access. Preserve conflict context and unknown fields. Keep review and persistence controls distinct from inspection controls.

Import review keeps the existing original/proposed-field workflow and explicit commit consequence. Dark assistant styling must not reduce the legibility of form errors, checked selections or edited-field markers elsewhere. A pending or uncertain commit must retain its recovery behavior. No design change grants an agent a write action.

## Mobile layout

Use a compact 56px top identity bar and a fixed bottom navigation bar approximately 68–76px tall, plus the platform safe area. Every existing destination stays reachable, with at least a 44px target and a visible current-page state. Reserve bottom padding in content so the bar covers no action or source row.

The heading becomes 28px. Counts remain in one horizontal strip. The work area becomes one column with the assistant followed immediately by recent records. At 390×844, the first viewport must show useful record counts, the complete composer and the beginning of the record section. Avoid nested scrolling on the resting Home page.

When the keyboard opens, preserve input focus and a reachable send action. Modal focus containment and return focus must survive the navigation change. Hidden desktop navigation must not remain in the tab order.

## Acceptance review

The implementation owner should provide fresh 1280px desktop and 390px phone screenshots, then an independent designer should review those pixels. A passing build does not pass visual review.

- The first screen contains usable records and a usable assistant, without a repeated greeting/breadcrumb/subtitle stack.
- Title, primary action, record counts, source rows and metadata have visibly different emphasis.
- There is one intentional charcoal assistant surface, not dark colors applied indiscriminately to all controls.
- Every displayed count comes from the captured API view. There are no invented charts, medical statuses, agents working in the background or unsupported success claims.
- New record review, source inspection, phone navigation, scope changes, actual question/answer, disagreement and export still work.
- No horizontal overflow at 390px; visible focus, readable contrast and 44px primary targets are checked in the implemented page.
- The retained synthetic-data disclosure and terminology license remain accessible without occupying the main page hierarchy.

All ten product goals, nine prompt roles, contest exclusions and existing evaluation boundaries remain intact. The broader lifelong-health roadmap is not erased by this visual revision. This spec neither changes the frozen benchmark/gold nor proves that the underlying retrieval system is state of the art.

## Independent visual review of the first implementation

The independent designer inspected the actual desktop, 390px phone and phone source-sheet captures for CSS revision `index-82G-UjLT.css`. The new desktop composition shows all three recent source rows alongside the assistant. The phone capture shows two full source rows and the start of the third above the bottom navigation; the previous phone capture showed no source rows. The duplicate heading/breadcrumb stack is gone, and source inspection retains a legible light document sheet.

The source sheet preserves the full `79.1234567` recorded value and unit, visually separates measured/report/availability dates, shows the original excerpt, and offers the scoped original download. These are observed visual results. The coordinating agent owns the corresponding interaction and scope checks.

Two small revisions were requested: increase the bottom navigation's 11px labels to 12px, and rename **Find values** to expose the HbA1c filter that its immediate action actually submits. The broad label would otherwise conceal the question's selected metric.

Calculated contrast for the reviewed CSS token pairs is 4.98:1 for archive secondary text, 8.46:1 for assistant secondary text, 7.45:1 for the input placeholder and 4.89:1 for white text on the primary blue action. These checks cover those specific pairs, not all rendered states or a complete accessibility audit.

## Filled-answer review and final corrections

The designer subsequently inspected the actual 1280px desktop and 390px phone captures after a scoped source-search request. The full `79.1234567` value, unit, measured date and conflict qualification remain readable. The phone capture shows the answer and its evidence action above the bottom navigation. Desktop keeps the recent documents alongside the answer. No clipping or contrast defect was visible in these states. Longer answer sets will naturally require scrolling; the coordinating agent retains responsibility for interaction and scope verification.

The frontend owner implemented both requested corrections, and the designer checked them in source: the shortcut now says **HbA1c values**, and bottom navigation labels use 12px. The corresponding built assets are `index-CkJ6S39m.css` and `index-BP3IWkYM.js`. The screenshot review preceded these two minor label-size changes; no broader visual redesign was introduced afterward.

One nonblocking wording limitation remains: **2 evidence items** can mean an observation ID and its source ID, rather than two documents. A future copy pass should prefer **View evidence** or explicitly distinguish records from documents. The reviewed view does not claim two separate documents, but the current generic count could still be misunderstood. This finding does not require changing the frozen retrieval gold or backend factual outputs.

The reviewed implementation satisfies the intended composition and visible-state requirements for these captures. It does not establish a user-study result, full accessibility certification, mobile-keyboard behavior on every device, or a live model comparison.
