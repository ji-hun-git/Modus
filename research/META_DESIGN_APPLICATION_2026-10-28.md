# Meta design research applied to Modus

Research and implementation date: 28 October 2026. Scope: the shared visual system in `entry/frontend`. Modus retains its own name, evidence cubes, dark reference design, and record-review workflow. This is an independent adaptation, not an official Meta design system or endorsement.

## What the primary sources actually say

| Source and context | Relevant finding | Application in Modus |
| --- | --- | --- |
| [Designing the Facebook company brand](https://www.meta.com/design-at-meta/blog/designing-the-facebook-company-brand/), 4 November 2019; historical company identity | The named behaviors are clarity, empathy, and creating space. Open letterforms and restrained motion support people's content. | A legible screen typeface, stronger text hierarchy, more space between cards, and controls that support evidence review. |
| [Designing our new company brand: Meta](https://www.meta.com/design-at-meta/blog/designing-our-new-company-brand-meta/), 28 October 2021; company identity | A simple, adaptable wordmark works at different sizes; the blue gradient connects the company identity to its products. The symbol is designed for motion and three-dimensional contexts. | Keep a distinct Modus mark and the user's evidence cubes. Blue marks actions and selection; the interface does not adopt Meta's logo or add decorative animation. |
| [Redefining Facebook's brand identity](https://www.meta.com/design-at-meta/blog/redefining-facebooks-brand-identity/), 20 September 2023; Facebook app identity | An accessible palette anchored in blue and coordinated typography improve consistency. Facebook Sans is a custom typeface. | A consistent blue action/focus palette with measured text contrast. Facebook Sans is not bundled. |
| [Horizon OS typography](https://developers.meta.com/vr/design/styles_typography/), updated 19 April 2026; VR interface guidance | High x-height and open counters aid reading; use a limited hierarchy and reserve strong weights for emphasis. Inter is available to developers on Meta VR devices. | Use open-source Inter for Modus's web UI, regular body text, stronger headings, and a 16 px base. This adapts the reading principles; VR-specific distances and type sizes are not asserted as a web specification. |

These sources describe different contexts. They do not establish a universal Meta web UI kit, a universally prescribed hex palette, or redistribution permission for proprietary company fonts. All hex values below are Modus choices.

## Applied visual decisions

- Self-host Inter 4.1 so the font renders consistently without a runtime font CDN. System fonts remain fallbacks, including Korean system fonts for characters not covered by Inter.
- Use a 16 px base and 16 px main input/assistant text. Supporting shared actions and content use 14 px; subordinate metadata uses 12–13 px. This is not a claim that every pre-existing component has been fully normalized.
- Retain monospaced tabular readings for precise numerical comparison. Use restrained regular and strong weights in the shared hierarchy.
- Use cool neutral surfaces: canvas `#171C24`, card `#222A35`, inset `#131922`. The evidence content remains the visual focus.
- Use `#1769E0` for primary actions with white labels; `#8DB7FF` for links, active navigation, and focus outlines. Blue does not encode a medical judgment. Existing explicit disagreement/review warnings retain their labeled treatment.
- Expose shared spacing tokens (4, 8, 12, 16, 24, 32, 48, and 64 px), 24 px card radii, and 12 px control radii. Update existing rules instead of introducing a competing theme layer.
- Preserve source cube geometry and existing direct evidence interactions. No decorative anatomy illustration or replacement visual metaphor was added.
- Main actions, navigation, and question suggestions have at least 44 px targets. Following the product review, the primary navigation is Home, Records, and Ask. A separate More menu exposes the other views without adding a fourth primary destination.
- Preserve the global reduced-motion behavior and visible keyboard focus ring.

### Token contrast checks

Calculated from the exact CSS hex values with the WCAG relative-luminance formula. These are token-pair checks, not a claim of complete WCAG conformance or a substitute for interaction testing.

| Foreground / background | Contrast |
| --- | ---: |
| Main text `#F4F7FA` / card `#222A35` | 13.46:1 |
| Supporting text `#B6C2D0` / card `#222A35` | 8.01:1 |
| Link `#8DB7FF` / card `#222A35` | 7.13:1 |
| White / primary action `#1769E0` | 5.08:1 |
| White / hovered primary action `#125BC7` | 6.27:1 |
| Focus `#8DB7FF` / canvas `#171C24` | 8.43:1 |
| Control border `#708198` / inset `#131922` | 4.44:1 |
| Control border `#708198` / card `#222A35` | 3.64:1 |
| Selected text `#8DB7FF` / selected surface `#263B58` | 5.60:1 |

## Font provenance and redistribution

The font is the unmodified official Inter variable web font, distributed under SIL Open Font License 1.1. Its license permits bundling with software with the copyright notice and license retained; the font is not sold separately. No proprietary Meta or Facebook font files were obtained.

- Upstream: [rsms/inter](https://github.com/rsms/inter).
- Release: [Inter 4.1](https://github.com/rsms/inter/releases/tag/v4.1).
- Tag `v4.1` resolved through the official GitHub API to immutable commit `e3a3d4c57d5ecc01453a575621882a384c1995a3`.
- Exact font source: [InterVariable.woff2 at the pinned commit](https://raw.githubusercontent.com/rsms/inter/e3a3d4c57d5ecc01453a575621882a384c1995a3/docs/font-files/InterVariable.woff2).
- Exact license source: [LICENSE.txt at the same commit](https://raw.githubusercontent.com/rsms/inter/e3a3d4c57d5ecc01453a575621882a384c1995a3/LICENSE.txt).
- Bundled font: `entry/frontend/public/fonts/InterVariable.woff2`; 352,240 bytes; SHA-256 `693b77d4f32ee9b8bfc995589b5fad5e99adf2832738661f5402f9978429a8e3`.
- Bundled license, copied byte-for-byte: `entry/frontend/public/fonts/Inter-OFL.txt`; 4,380 bytes; SHA-256 `262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a`.
- Copyright: 2016 The Inter Project Authors. The pinned license includes the standard OFL conditions, including its conditions for modified versions; the bundled font is unmodified. This particular license file does not declare a reserved name after its copyright notice.
- CSS uses `font-display: swap`. There is no runtime request to Google Fonts or another font CDN. The local asset ships in Vite's production output.

The application's unresolved project license is independent of this third-party font license. Packaging must retain both font and font license.

## Implementation and verification

Changed shared styles: `styles.css`, `service-design.css`, and `service-responsive.css`. No additional stylesheet import is needed. The Brief frontend uses the same semantic tokens. The subsequent Home simplification changes `HealthRecordOverview.tsx` and `health-record-overview.css`: four latest result groups maximum, a conditional comparison banner, one upload action, and a link to the complete record view. Tied results remain together; the full comparison opens on demand. The design agent made no changes to backend behavior, prompts, held-out sets, source records, or credentials, and made no provider calls.

- `npm run build` in `entry/frontend`: passed (`tsc -b` and Vite production build).
- The font's WOFF2 signature, pinned source, byte length, and SHA-256 were checked. The production build contains `dist/fonts/InterVariable.woff2` and the license.
- The shared color pairs above were calculated programmatically.
- Full flow, browser font loading, viewport inspection, and release identity checks belong to the integrated milestone verification; this document does not claim those checks solely from a successful build.

Integrated viewport coverage: 320, 390, 768, and 1280 px. Check keyboard focus, mobile navigation labels, record/review input legibility, cube-to-source interaction, and Brief selection/export.
