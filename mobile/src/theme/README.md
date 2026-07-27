# Sarflog Mobile Design-System Foundation

This file is the source of truth for Sarflog's confirmed mobile design-system decisions. The executable tokens live beside it in focused TypeScript modules and are exposed through `src/theme/index.ts`.

**Status:** centralized tokens, light/dark theme selection, navigation-theme adaptation, Inter Regular/Semibold loading, HeroUI Native/Uniwind integration, and the foundation gallery are implemented. Real-device visual and accessibility validation remain ongoing.

## Ownership and usage

- `src/theme/` owns mobile colors, typography, spacing, radii, shadows, and their light/dark theme mappings.
- `src/layout/` separately owns available-window classes, responsive gutters, content-width caps, and adaptive layout policy. Responsive sizes are not light/dark theme tokens.
- `src/theme/ACCESSIBILITY.md` is the plain-language implementation contract for accessibility across components and screens. Apply it by default without seeking a separate product decision for every ordinary accessibility requirement.
- Components should consume semantic roles such as `screen`, `textPrimary`, and `status.destructive`, rather than hard-coded color values.
- Light and dark modes expose the same semantic roles, but may resolve them to different values.
- `src/theme/index.ts` is the public import doorway. Raw palette shades remain private to the theme layer, and product code consumes the active semantic theme through `useTheme()`.
- `src/providers/theme-provider.tsx` follows the phone's light/dark appearance and supplies both Sarflog's complete theme and its Expo Router navigation adapter.
- The provider also supports an in-memory `System`, `Light`, or `Dark` preview used by the gallery. This preview is development tooling and intentionally resets to `System` after reload; persisted user preference remains a future product feature.
- `src/theme/LIBRARY-INTEGRATION.md` defines the ownership boundary: Sarflog owns brand and product semantics; HeroUI Native owns its component visual language and interaction defaults.
- `src/features/design-system/screens/foundation-gallery-screen.tsx` renders the active foundation for visual inspection during development. It must not remain in customer navigation for production.
- `src/global.css` is the Uniwind entry point and maps Sarflog's approved light/dark colors and fonts into HeroUI Native on Android and iOS. It also supports the development-only web gallery.
- HeroUI Native is the default component layer. `components/ui/` is reserved for thin Sarflog wrappers only when product behavior cannot be expressed cleanly through HeroUI's public API. `components/shared/` contains reusable Sarflog-specific UI.

### Executable structure

```text
src/theme/
├── palette.ts       Private raw color ingredients
├── colors.ts        Semantic light and dark color roles
├── typography.ts    Inter assets, weights, and text styles
├── spacing.ts       Spacing scale
├── radii.ts         Corner-radius scale
├── sizes.ts         Controls, touch targets, and button measurements
├── elevation.ts     Shared semantic depth vocabulary
├── motion.ts        Durations and easing curves
├── themes.ts        Complete app themes and Expo Router adapters
├── types.ts         Shared theme contracts
└── index.ts         Single public import doorway
```

### Evolution rule

Confirmed foundation values are an intentional starting baseline, not permanent constraints. Components must consume semantic theme tokens instead of hard-coded values so a later color, spacing, radius, or typography adjustment can be made centrally. Any token change must still be visually checked in every affected state, in light and dark mode, on Android and iOS, and revalidated for accessibility contrast.

### Measurement and library model

- React Native numeric dimensions are unitless, density-independent layout measurements. They are not literal physical screen pixels, percentages, or millimetres.
- A number gets its meaning from its property: `height: 48`, `padding: 24`, `borderRadius: 12`, and `fontSize: 16` measure different aspects of an element.
- Product-specific native structures may use React Native style properties. HeroUI Native uses Tailwind CSS through Uniwind, which compiles CSS variables and classes into React Native styles rather than browser DOM CSS.
- HeroUI Native and Uniwind are the confirmed default component and styling mechanics. React Native primitives remain the fallback for structures HeroUI does not supply.
- HeroUI's `sm`, `md`, and `lg` button presets resolve to `40`, `48`, and `56`, matching Sarflog's approved control-height scale.

## Color foundation

### Brand

Sarflog's primary brand green is:

| Role | HSL | Hex |
| --- | --- | --- |
| Primary brand/action | `hsl(142 71% 45%)` | `#22C55E` |

The brand green is the identity and primary-action color. It should not automatically be used for every positive value or status.

### Neutral themes

These semantic colors form the base light and dark themes:

| Semantic role | Light mode | Dark mode |
| --- | --- | --- |
| Screen background | `#FAFAFA` | `#09090B` |
| Card/surface | `#FFFFFF` | `#18181B` |
| Input/subtle surface | `#F4F4F5` | `#27272A` |
| Primary text | `#18181B` | `#FAFAFA` |
| Secondary text | `#52525B` | `#A1A1AA` |
| Subtle decorative border/divider | `#E4E4E7` | `#27272A` |
| Meaningful control border | `#71717A` | `#71717A` |

These are semantic assignments, not a complete neutral shade palette. Add raw shades only when a real component requires them.

### Destructive themes

Destructive colors are tuned separately for each appearance instead of forcing one red to work on both backgrounds:

| Semantic role | Light mode | Dark mode |
| --- | --- | --- |
| Main destructive | `#DC2626` | `#F87171` |
| Text/icon on solid destructive | `#FFFFFF` | `#450A0A` |
| Subtle destructive background | `#FEF2F2` | `#450A0A` |
| Text/icon on subtle destructive background | `#991B1B` | `#FCA5A5` |
| Destructive border | `#FECACA` | `#7F1D1D` |

Use destructive styling for actual danger and failure, including:

- deleting an expense, wallet, or account;
- voiding or permanently removing a record;
- validation errors;
- failed operations.

Do not automatically use destructive red for ordinary expenses, money going out, debt balances, or slightly poor budget progress. Those are financial information, not necessarily errors or dangerous actions.

### Success, warning, and information themes

Status colors use complete semantic families with separate light and dark values. A status must always include an icon, label, or explanatory text; color alone must never carry the meaning. Subtle borders are supplementary and must not be the only status indicator.

#### Success

Success uses emerald so completed outcomes remain recognizably green while staying visually distinct from Sarflog's brighter `#22C55E` action green:

| Semantic role | Light mode | Dark mode |
| --- | --- | --- |
| Main success | `#047857` | `#34D399` |
| Text/icon on solid success | `#FFFFFF` | `#022C22` |
| Subtle success background | `#ECFDF5` | `#022C22` |
| Text/icon on subtle success background | `#065F46` | `#6EE7B7` |
| Success border | `#A7F3D0` | `#065F46` |

Use success for completed outcomes such as a saved expense, recorded payment, completed import, achieved goal, or successful synchronization. Do not automatically use it for income, positive balances, or every increasing financial value.

#### Warning

Warning uses amber for conditions that need attention but have not yet failed:

| Semantic role | Light mode | Dark mode |
| --- | --- | --- |
| Main warning | `#B45309` | `#FBBF24` |
| Text/icon on solid warning | `#FFFFFF` | `#451A03` |
| Subtle warning background | `#FFFBEB` | `#451A03` |
| Text/icon on subtle warning background | `#92400E` | `#FCD34D` |
| Warning border | `#FDE68A` | `#92400E` |

Use warning for an approaching budget limit, payment due soon, incomplete information, or another recoverable condition requiring attention. Warning means "pay attention"; destructive means failed, invalid, or dangerous.

#### Information

Information uses blue for calm, neutral guidance that is distinct from Sarflog's green action language:

| Semantic role | Light mode | Dark mode |
| --- | --- | --- |
| Main information | `#2563EB` | `#60A5FA` |
| Text/icon on solid information | `#FFFFFF` | `#172554` |
| Subtle information background | `#EFF6FF` | `#172554` |
| Text/icon on subtle information background | `#1E40AF` | `#93C5FD` |
| Information border | `#BFDBFE` | `#1E40AF` |

Use information for helpful explanations, exchange-rate details, neutral account notices, onboarding guidance, and informational banners. Information blue does not automatically define links, selected controls, or primary actions; those are separate semantic roles.

The selected status foreground/background text pairs have an initial calculated contrast of at least `4.8:1`. They still require visual validation on real Android and iOS screens alongside the rest of the theme.

## Accessibility contrast foundation

### Approved contrast policy

Sarflog uses WCAG 2.2 Level AA contrast as the measurable minimum for its custom mobile theme, together with the Android and iOS platform accessibility guidance:

- normal text requires at least `4.5:1` contrast against its actual background;
- large text requires at least `3:1`; unless a concrete text style has been verified to meet the platform's large-text definition, use the safer `4.5:1` requirement;
- meaningful icons, control boundaries, focus indicators, selection indicators, and other non-text information require at least `3:1` against adjacent colors;
- every foreground/background pair is checked separately in light mode, dark mode, and each interaction state;
- color must never be the only way to communicate status, selection, error, or meaning; use an appropriate label, icon, shape, position, underline, checkmark, or other structural cue as well;
- decorative separators, supplementary borders, logos, and inactive controls may be exempt from a contrast threshold only when they are not required to understand the content, identify a control, or determine its state;
- passing a mathematical threshold is a minimum, not a substitute for testing on real Android and iOS screens, at larger text sizes, and under different lighting conditions.

References: [WCAG 2.2 contrast minimum](https://www.w3.org/TR/WCAG22/#contrast-minimum), [WCAG 2.2 non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast), [Android app accessibility](https://developer.android.com/guide/topics/ui/accessibility/apps), and [Apple accessibility guidance](https://developer.apple.com/design/human-interface-guidelines/accessibility/).

### Initial palette audit

Contrast is a relationship between two colors, so this audit checks the intended foreground/background pairs rather than judging isolated hex values.

| Area | Lowest relevant calculated result | Outcome |
| --- | ---: | --- |
| Light primary text on screen, card, and subtle surfaces | `16.12:1` | Pass |
| Light secondary text on screen, card, and subtle surfaces | `7.03:1` | Pass |
| Dark primary and secondary text on screen, card, and subtle surfaces | `5.81:1` | Pass |
| Primary-button label across default and pressed appearances | `4.52:1` | Pass |
| Secondary-button labels across default and pressed appearances | above `10:1` | Pass |
| Destructive-button labels across default and pressed appearances | `4.83:1` | Pass |
| Success, warning, information, and destructive solid/subtle text pairs | `4.83:1` | Pass |
| Selected text, marks, and meaningful selection boundaries | `3.00:1` | Pass; light selection boundary is exactly at the non-text minimum |
| Focus outlines against their intended screen backgrounds | `4.81:1` | Pass |
| Meaningful control borders against light and dark subtle input surfaces | `3.08:1` | Pass |
| Existing subtle neutral and status borders | approximately `1.15:1` to `2.11:1` | Allowed only as supplementary decoration; they cannot identify a control or state by themselves |
| Brand green `#22C55E` as foreground on a light screen/card | `2.18:1` to `2.28:1` | Not safe for normal text or a meaningful thin icon |

The brand green itself does not need to change. It remains suitable as a primary-action fill when paired with the confirmed dark-green label `#052E16`, which reaches approximately `6.54:1`. In light mode, meaningful green text, thin icons, and selection indicators must use the already selected darker green roles instead of the exact brand shade. A logo is treated separately from ordinary interface text and controls.

### Confirmed contrast corrections

1. Light-mode secondary text is `#52525B`. It reaches approximately `7.03:1` on the subtle surface, `7.41:1` on the screen, and `7.73:1` on white cards while remaining visually secondary to `#18181B`.
2. `#E4E4E7` in light mode and `#27272A` in dark mode are **subtle decorative divider** colors. The separate meaningful control-border role uses `#71717A` in both modes when a border is required to identify an input or control. It reaches approximately `4.40:1` against the light subtle input surface and `3.08:1` against the dark subtle input surface, exceeding the `3:1` non-text minimum.
3. Keep the existing pale status borders only as supplementary decoration alongside readable status text and an icon or label; never use those borders alone to communicate status.

## Typography foundation

### Font family and weights

- Use **Inter** across Android, iOS, and web.
- Start with **Regular 400** for normal reading text.
- Start with **Semibold 600** for titles, emphasis, and actions.
- Add **Medium 500** only if a real interface need appears; do not load every weight from 100 through 900 by default.
- Money amounts use Inter with tabular numerals so digits align cleanly. They do not need a separate monospace font.

Font weight controls stroke thickness, not text width. A weight must exist in the loaded font files before the interface can render that genuine weight reliably.

### Text hierarchy and initial scale

The hierarchy gives each piece of text a job. It is intentionally small so screens remain consistent:

| Semantic style | Size | Line height | Weight | Letter spacing | Typical use |
| --- | ---: | ---: | ---: | --- | --- |
| Display amount | `32` | `40` | `600` | Inter default | Account balance, monthly total, key money figure |
| Title | `20` | `28` | `600` | Inter default | Screen or section title |
| Body | `16` | `24` | `400` | Inter default | Main content, transaction name, form text |
| Supporting/footnote | `13` | `18` | `400` | Inter default | Date, category, helper text, secondary metadata |
| Button label foundation | `16` | `24` | `600` | Inter default | Non-HeroUI action labels and typography reference |

The button label deliberately reuses the body size; it is not a fifth size. HeroUI buttons use HeroUI's lighter `font-medium` role, currently mapped to Inter Regular 400 based on visual feedback; the 600 foundation style remains available when stronger emphasis is intentionally required. `13` is named supporting/footnote rather than caption because this information is secondary but still regularly read.

The line-height ratios intentionally become looser as text becomes smaller or more likely to wrap: display `1.25x`, title `1.4x`, body and button `1.5x`, and supporting text approximately `1.38x`. React Native receives the explicit line-height measurement shown in the table, not a CSS-style multiplier.

All styles initially use Inter's natural letter spacing with no additional positive or negative tracking. Add a tracking exception only after a real on-device typography problem demonstrates the need.

### Typography behavior

- Text must respect the user's system font-size/accessibility setting; do not disable font scaling globally.
- Hierarchy should also be communicated through size, weight, spacing, and placement, not color alone.
- Money and other numeric columns should use tabular numerals where alignment matters.
- Text and its containing layouts must be tested at larger system text sizes so confirmed line heights do not cause clipping or overlap.

### Large-text accessibility behavior

Sarflog follows the Android and iOS system text-size setting. It does not initially add a separate in-app font-size preference, disable font scaling globally, or cap scaling by default. The confirmed typography values such as body `16`, title `20`, and display amount `32` are the starting sizes at the default system setting; the platform scales them according to the user's preference.

Every core flow must remain understandable and usable with text enlarged to at least `200%`. Test the platform's intermediate and largest accessibility text settings as well, rather than treating one calculated screenshot as sufficient.

Layout rules at larger text sizes:

- essential button labels, input labels, validation errors, screen titles, amounts, and financial information must not be clipped or replaced with an ellipsis;
- text and text-containing controls may wrap and grow vertically;
- a side-by-side button group must stack vertically when its labels no longer fit comfortably;
- a horizontal label-and-value row must reflow vertically when necessary;
- cards and list rows must grow instead of allowing text to overlap neighboring content;
- screens must scroll when enlarged content no longer fits in the available height;
- the minimum `48 x 48` touch target remains in force, and a control may grow beyond its default minimum height;
- do not shrink essential text below the user's requested size merely to preserve a compact layout.

Large-text acceptance checks run at the default, an intermediate enlarged setting, `200%`, and the platform's largest supported accessibility setting. A screen passes only when there is no overlapping or clipped essential text, no hidden information or action, all controls remain usable, scrolling reaches every item, and the user can complete the flow. The initial reference flow is adding an expense from start to finish.

References: [Apple Larger Text evaluation criteria](https://developer.apple.com/help/app-store-connect/manage-app-accessibility/larger-text-evaluation-criteria), [Android 200% font scaling](https://developer.android.com/about/versions/14/features#accessibility), and [React Native Text scaling](https://reactnative.dev/docs/text#allowfontscaling).

## Screen-reader semantics foundation

Sarflog must expose a meaningful accessibility tree to Android TalkBack and iOS VoiceOver. Screen-reader support is part of the public component contract, not optional metadata added after screens are visually complete. Prefer native controls and their built-in semantics; custom React Native components must provide equivalent meaning and behavior.

### Semantic identity

Every meaningful interactive element exposes:

- a concise, localized **label** that identifies its purpose out of visual context;
- the correct **role**, such as button, heading, text input, checkbox, switch, tab, or progress bar;
- its current **state** when relevant, including disabled, selected, checked, busy, or expanded;
- its current **value** when relevant, including input content, progress, ranges, and financial values;
- a short **hint** only when the result of the action is not clear from its label and role.

Labels describe purpose rather than appearance. Use `Add expense`, `Open date picker`, or `Delete groceries expense`, not `Plus icon`, `Green button`, `Click here`, or an ambiguous `Delete`. Do not write roles or states inside labels because the screen reader announces them separately; `Delete expense, button` must not become `Delete expense button, button`.

### Component behavior

- Icon-only controls require a meaningful label that names their action.
- Visible text normally supplies its own spoken text; do not add duplicate accessibility labels without a concrete need.
- Decorative icons, dividers, sparkles, and duplicate visual children are hidden from the accessibility tree.
- A compound control is grouped into one useful accessible element when reading each decorative child separately would add noise.
- Selected, checked, disabled, loading, busy, and expanded visual states must update the corresponding accessibility state at the same time.
- Text fields expose a persistent label, current value, instructions when needed, and their specific validation error; a placeholder is not the field's only label.
- Charts and data visualizations provide a useful text summary and access to the underlying values rather than being announced only as an image.
- Any important swipe, drag, or long-press interaction also exposes a standard control or named accessibility action so the complete flow does not depend on a precise gesture.

### Accessible button contract

Primary, secondary, ghost, and destructive are visual variants of the same semantic control. Every Sarflog button exposes the button role and is presented to assistive technology as one focusable element. Decorative icons and loading spinners inside it are not separate screen-reader stops.

Label rules:

- A text button normally uses its visible text as its accessible label.
- If extra context is necessary, the accessible label keeps the visible words in the same order and adds only the missing context. For example, a visible `Delete` action in a transaction row may be announced as `Delete groceries expense`.
- An icon-only button requires a concise localized action label at the place where it is used, such as `Go back`, `Close expense details`, or `Open date picker`.
- Labels start with the action and name the affected object when ambiguity or risk exists.
- Do not include `button`, `disabled`, `busy`, or other role/state words in the label; the platform announces those separately.
- Add a hint only when the result is genuinely unclear from the label and role. Routine buttons such as `Save expense` do not need a hint like `Double tap to save`.

| Button condition | Spoken meaning | Required behavior |
| --- | --- | --- |
| Default | Localized label, button | Activates once when invoked |
| Pressed | No separate spoken state | Pressed is temporary visual/haptic feedback only |
| Disabled | Localized label, disabled button | Remains understandable, cannot activate, and has an accessible nearby reason when the reason is not obvious |
| Loading | Localized in-progress label, busy and disabled button | Blocks duplicate activation, keeps its layout stable, and hides the spinner from separate screen-reader focus |
| Destructive | Explicit action-and-object label, button | Destructive is not a role; irreversible actions receive a separate confirmation step |

For example, a normal visible `Save expense` button is announced as `Save expense, button`. While submitting, its visible and spoken label becomes a localized equivalent of `Saving expense`, and its state becomes busy and unavailable. After completion, the result `Expense saved` is announced separately or focus moves logically to the destination screen; the button does not repeat the success message itself.

A button with visible `Delete` text for a groceries transaction may use the more specific accessible label `Delete groceries expense`. A trash icon inside that button is decorative. An icon-only trash button uses the same explicit action label. A destructive color never substitutes for this wording.

Buttons that persistently represent selection, such as tabs or filter chips, use their dedicated selected/checked component contracts rather than pretending to be an ordinary action button. Every button contract is tested in Uzbek, Russian, and English with TalkBack and VoiceOver for label, role, disabled state, busy state, single activation, focus behavior, and reading order.

References: [WCAG Label in Name](https://www.w3.org/WAI/WCAG22/Understanding/label-in-name), [Apple VoiceOver evaluation criteria](https://developer.apple.com/help/app-store-connect/manage-app-accessibility/voiceover-evaluation-criteria), [Android accessibility principles](https://developer.android.com/guide/topics/ui/accessibility/principles), and [React Native accessibility state](https://reactnative.dev/docs/accessibility#accessibilitystate).

### Financial speech

Spoken financial content includes meaning and context instead of announcing disconnected numbers or symbols. For example, a budget may be expressed as `Food budget, 600,000 of 800,000 used, 75 percent`, and a transaction may identify its merchant or title, amount, direction, and date. Dates, currencies, plural forms, decimal separators, and income/expense direction follow the active locale. Destructive actions name the affected object explicitly.

### Reading order, grouping, and focus

- Default screen-reader order follows the logical task and the visible language's reading order.
- Headings are marked as headings so users can navigate by section.
- Users can move forward and backward without skipped elements, repeated loops, or focus entering invisible content.
- Related content is grouped only when grouping reduces unnecessary swipes without hiding distinct actions or values.
- When a screen or modal opens, focus moves to its logical starting point and background content is unavailable.
- When a modal closes, focus returns to the control that opened it when that control still exists.
- Background refreshes and pagination must not unexpectedly reset the user's reading position.

### Dynamic announcements

Important changes such as `Expense saved`, a validation error, a failed operation, or a meaningful loading state are announced once and at the appropriate time. Routine updates use non-interrupting announcements. Interrupting announcements are reserved for rare urgent or blocking information. Repeated animations, progress frames, and decorative changes must not create announcement noise.

### Uzbek, Russian, and English

Accessibility labels, hints, values, actions, errors, chart summaries, and dynamic announcements are localized product copy in Uzbek, Russian, and English. They must come from the same localization system as visible UI text rather than being hard-coded in a component.

- Translate complete messages or templates with named values; do not construct sentences by concatenating independently translated fragments.
- Each language receives natural word order, grammar, plurals, dates, currency wording, and number pronunciation.
- Use the active app language for accessibility copy and supply an appropriate BCP 47 language tag where the platform API supports it.
- Uzbek, Russian, and English are all left-to-right, but their different text lengths still require large-text and layout validation in every language.
- Russian and English have commonly available built-in screen-reader voices. Current published Apple and Google voice lists do not list Uzbek, so Uzbek text-to-speech quality and fallback pronunciation may vary by device, operating-system version, and installed speech engine. Sarflog still provides correct Uzbek text and tests the real result; it must not silently replace Uzbek accessibility copy with Russian or English.

### Acceptance testing

Each reusable component is checked for name, role, state, value, grouping, and available actions. Core flows are then completed without sight using TalkBack on Android and VoiceOver on iOS, moving both forward and backward through the interface. The initial flow is adding an expense; later coverage includes editing and deleting an expense, checking a budget, and recovering from validation or network errors. Test all three app languages, including announcements, modal focus, gesture alternatives, financial pronunciation, and restoration of focus after navigation. Automated scanners supplement but do not replace manual screen-reader testing.

References: [React Native accessibility](https://reactnative.dev/docs/accessibility), [Apple VoiceOver evaluation criteria](https://developer.apple.com/help/app-store-connect/manage-app-accessibility/voiceover-evaluation-criteria), [Android accessibility principles](https://developer.android.com/guide/topics/ui/accessibility/principles), [Apple VoiceOver languages](https://support.apple.com/en-gb/111748), and [TalkBack languages](https://support.google.com/accessibility/android/answer/11101402).

## Spacing foundation

Sarflog uses a **4-point base with an 8-point primary rhythm**. Use this approved scale instead of arbitrary spacing values:

| Value | Typical relationship |
| ---: | --- |
| `4` | Tiny separation between parts of the same item |
| `8` | Tight spacing between related elements |
| `12` | Icon-to-text or compact component spacing |
| `16` | Standard everyday screen and component spacing |
| `24` | Comfortable separation between groups |
| `32` | Separation between major sections |
| `48` | Large breathing room |
| `64` | Rare extra-large or hero spacing |

Related elements stay closer together; unrelated groups receive more space. The scale defines the available vocabulary, while exact component assignments should be validated in the first component gallery.

## Corner-radius foundation

Sarflog uses moderately rounded shapes to feel modern and approachable without becoming overly playful:

| Semantic size | Radius | Typical use |
| --- | ---: | --- |
| Small | `8` | Small icon containers and compact elements |
| Medium | `12` | Buttons and inputs |
| Large | `16` | Cards and primary surfaces |
| Extra large | `24` | Bottom sheets, modals, and prominent panels |
| Full | fully rounded | Pills, tags, circular buttons, and avatars |

Larger outer containers should normally have equal or greater rounding than the smaller elements nested inside them. Full rounding is a semantic shape, not an arbitrary large number exposed to product components.

## Depth, shadows, and elevation

Sarflog has one semantic depth system for both Android and iOS:

| Level | Meaning | Typical use |
| --- | --- | --- |
| Flat | Part of the normal screen plane | Transaction rows, inputs, ordinary content |
| Subtle | Slightly separated from the screen | Balance and summary cards |
| Raised | Floating above nearby content | Menus, floating actions, and date pickers |
| Overlay | Above the entire current screen | Bottom sheets and modals |

- Components request a semantic level; they do not choose an Android or iOS shadow directly.
- Android and iOS may render the same level with different native-looking shadow recipes.
- Light mode may use soft shadows and borders. Dark mode relies more on brighter surfaces and subtle borders because dark shadows are less visible.
- Depth communicates hierarchy or temporary closeness. Do not add shadows merely as decoration, and do not surround every card with a strong shadow.

The four levels are confirmed. Their exact light/dark and Android/iOS shadow parameters still require on-device visual validation.

## Control-size and touch-target foundation

### Control minimum heights

| Semantic size | Minimum height | Typical use |
| --- | ---: | --- |
| Compact | `40` | Chips, filters, and secondary compact controls |
| Standard | `48` | Normal buttons and icon buttons |
| Large | `56` | Primary buttons and form inputs |

### Interaction rules

- Every interactive element has a minimum `48 x 48` touch target across Android and iOS.
- A visible element may be smaller than its touch target. For example, a `20` or `24` icon can sit inside a `48 x 48` tappable area.
- Invisible touch targets must not overlap neighboring targets.
- Controls must grow when accessibility text would otherwise clip or become unusable.
- The values in the shared scale are minimum visible heights, not rigid boxes. Width remains flexible, and text-containing controls grow vertically when accessibility text requires it.

## Button sizing foundation

HeroUI Native implements this scale directly: `sm` is `40`, `md` is `48`, and `lg` is `56`. Sarflog normally uses `md` and `lg`; `sm` is available only where a compact control still has an effective `48 x 48` touch target.

Sarflog initially exposes only the button sizes it needs:

| Button size | Minimum dimensions | Typical use |
| --- | --- | --- |
| Standard | `48` high | Most ordinary actions; grows when its label requires it |
| Large | `56` high | Main form and bottom-of-screen actions; grows when its label requires it |
| Icon button | `48 x 48` | Back, close, menu, calendar, and similar actions; remains at least this large |

The following measurements describe the earlier custom-button exploration. HeroUI's documented presets are now authoritative for internal padding, gap, label treatment, and corner shape:

- Label: Inter `16`, weight `600`.
- Horizontal padding: `24`.
- Icon: `20` by default; `24` when the symbol requires it.
- Icon-to-label gap: `8`.
- Corner radius: `12`.
- Minimum touch target: `48 x 48`.

Do not expose a compact text button until a concrete use case requires one; the confirmed `40` minimum control height is initially for chips and compact controls. Buttons shown as a group should normally share a height when their content fits, and stack or grow when accessibility text requires it. Communicate the preferred action through visual style rather than making neighboring actions arbitrarily different sizes. A button may be full-width or content-width depending on its layout role.

## Button interaction states (legacy custom exploration)

The detailed tables in this section record the semantic intent that informed the theme. They are no longer a pixel-level component contract. HeroUI Native now owns button variants, shapes, pressed overlays, calculated hover colors, disabled opacity, and scale/highlight feedback. `src/global.css` supplies Sarflog's accent, danger, neutral, focus, and foreground values.

A button's **variant** describes the kind of action, such as primary or destructive. Its **state** describes what is happening now, such as default, pressed, loading, disabled, or focused. Destructive is therefore a variant, not an interaction state.

Sarflog owns action meaning and accessibility requirements. HeroUI Native supplies the interaction mechanics and visual state treatment, while Reanimated and Uniwind power its implementation.

### Solid primary button

| State role | Light mode | Dark mode |
| --- | --- | --- |
| Default background | `#22C55E` | `#22C55E` |
| Default label/icon | `#052E16` | `#052E16` |
| Pressed background | `#16A34A` | `#4ADE80` |
| Pressed label/icon | `#052E16` | `#052E16` |
| Loading background | `#22C55E` | `#22C55E` |
| Loading label/spinner | `#052E16` | `#052E16` |
| Focus outline | `#15803D` | `#86EFAC` |

The primary button uses dark green content rather than white because `#052E16` on `#22C55E` has approximately `6.54:1` contrast, while white on the same background has approximately `2.28:1`. The pressed background darkens in light mode and brightens in dark mode so the interaction remains perceptible against each surrounding theme.

### Soft secondary button

| State role | Light mode | Dark mode |
| --- | --- | --- |
| Default background | `#E4E4E7` | `#27272A` |
| Default label/icon | `#18181B` | `#FAFAFA` |
| Pressed background | `#D4D4D8` | `#3F3F46` |
| Pressed label/icon | `#18181B` | `#FAFAFA` |
| Loading background | `#E4E4E7` | `#27272A` |
| Loading label/spinner | `#18181B` | `#FAFAFA` |
| Focus outline | `#15803D` | `#86EFAC` |

The secondary button uses a soft neutral fill rather than green or an outline. It is a medium-emphasis alternative normally paired with a primary action, such as Back beside Continue or Not now beside Set budget. Keeping it neutral makes the green primary action unmistakable and avoids confusing brand action green with success green. Secondary and primary buttons shown as a group use the same height while their content fits comfortably; they grow or stack when accessibility text requires it.

### Solid destructive button

| State role | Light mode | Dark mode |
| --- | --- | --- |
| Default background | `#DC2626` | `#F87171` |
| Default label/icon | `#FFFFFF` | `#450A0A` |
| Pressed background | `#B91C1C` | `#FCA5A5` |
| Pressed label/icon | `#FFFFFF` | `#450A0A` |
| Loading background | `#DC2626` | `#F87171` |
| Loading label/spinner | `#FFFFFF` | `#450A0A` |
| Focus outline | `#B91C1C` | `#FCA5A5` |

The confirmed destructive text pairs have at least approximately `4.83:1` contrast in their default and pressed states. Destructive styling is reserved for dangerous or irreversible actions; it must not be used for ordinary negative financial values.

### Ghost button

| State role | Light mode | Dark mode |
| --- | --- | --- |
| Default background | transparent | transparent |
| Default label/icon | `#18181B` | `#FAFAFA` |
| Pressed background | `#F4F4F5` | `#27272A` |
| Pressed label/icon | `#18181B` | `#FAFAFA` |
| Loading background | transparent | transparent |
| Loading label/spinner | `#18181B` | `#FAFAFA` |
| Disabled background | transparent | transparent |
| Disabled label/icon | `#71717A` | `#A1A1AA` |
| Focus outline | `#15803D` | `#86EFAC` |

Ghost is Sarflog's lowest-emphasis button. Use it for quiet supporting actions such as Skip, View details, Edit, Close, Back, or More when a filled button would compete with the screen's main action. It has no visible container until pressed; the pressed surface provides immediate feedback without promoting the action to secondary importance. Ghost labels and icons remain neutral rather than green so multiple supporting actions do not compete with the primary CTA.

HeroUI's available family is primary, secondary, tertiary, outline, ghost, danger, and danger-soft. Feature screens should still choose the smallest hierarchy that communicates the decision clearly; the gallery displays representative variants for evaluation.

### Button hierarchy

- Each immediate decision area should normally have one clear high-emphasis action. Do not place two competing primary buttons beside each other.
- Primary communicates the preferred nondestructive action; secondary communicates a related medium-emphasis alternative; ghost communicates a quiet supporting action; destructive communicates genuine danger.
- Use visual style, not arbitrary size differences, to express importance. Related buttons in a group share a height while their content fits comfortably, then grow or stack when accessibility text requires it.
- A screen may contain independent local actions in cards or sections, but they must not visually compete with the screen's main CTA.
- Cancel, Back, or Not now may use secondary when the alternative needs a visible container, or ghost when it should remain deliberately quiet.
- Do not add variants merely because a source library or another app offers them. Sarflog's smaller approved family is the public component contract until a concrete product need justifies another variant.

### Shared filled-button disabled colors

All filled button variants use the same neutral disabled treatment instead of retaining their green or red action color. Ghost remains transparent while reusing the same disabled label/icon colors:

| State role | Light mode | Dark mode |
| --- | --- | --- |
| Disabled background | `#E4E4E7` | `#27272A` |
| Disabled label/icon | `#71717A` | `#A1A1AA` |

### State behavior

- Pressed feedback exists only while the control is actively being pressed.
- Loading preserves the button's dimensions and active variant colors, replaces or accompanies the label with a progress indicator, communicates a busy state to assistive technology, and blocks duplicate activation.
- Disabled buttons are visibly neutral, remain readable, communicate their disabled state to assistive technology, and cannot be activated.
- Loading and disabled behavior take precedence over pressed feedback because the button cannot accept another action in either state.
- Focus uses the confirmed theme-aware outline color. Its exact outline width, offset, and platform rendering still require component-level validation.
- Android and iOS share these semantic states. Their physical feedback may use platform-appropriate rendering, but the meaning and accessibility behavior must remain consistent.

## Selection states

Pressed is temporary feedback while a finger is down. Selected is persistent state that remains after the interaction until the user chooses something else. Sarflog uses one semantic selection family across tabs, chips, checkboxes, radios, switches, and selectable rows; each component maps the family to its own shape and anatomy.

| Semantic role | Light mode | Dark mode | Typical use |
| --- | --- | --- | --- |
| Strong selection/indicator | `#16A34A` | `#4ADE80` | Checkbox fill, radio dot, switch track, tab underline |
| Content on strong selection | `#052E16` | `#052E16` | Checkmark, inner icon, or other mark |
| Subtle selected background | `#DCFCE7` | `#14532D` | Selected chip, row, card, or tab pill |
| Selected text/icon | `#166534` | `#86EFAC` | Selected chip, tab, or navigation label/icon |
| Unselected background | transparent | transparent | Default selectable control surface |
| Unselected border/indicator | `#71717A` | `#A1A1AA` | Empty checkbox, radio ring, or chip border |

The exact brand green `#22C55E` has approximately `2.28:1` contrast against white, so it is not strong enough for every small light-mode selection indicator. The darker `#16A34A` reaches approximately `3.30:1` against white, while selected text uses the still-darker `#166534` for reading contrast. Dark mode uses brighter green roles so selection remains clear against dark surfaces.

### Component mappings

- A selected tab uses selected text/icon plus the strong selection underline. An unselected tab normally uses secondary text.
- A selected filter chip uses the subtle selected background, selected text/icon, a strong selection border, and a checkmark. An unselected chip is transparent with the unselected border.
- A selected checkbox uses the strong selection fill and an on-selection checkmark. An unselected checkbox is empty with the unselected border.
- A selected radio uses the strong selection outer ring and inner dot. An unselected radio keeps only the neutral ring.
- A selected switch uses the strong selection track and communicates state through the thumb position as well as color. Prefer platform-native switch behavior while mapping its tint to the semantic selection family.
- A selected row or card uses the subtle selected background plus a strong border, checkmark, or other persistent structural cue.

Selection must never rely on color alone. Use a checkmark, underline, filled dot, thumb position, shape, icon treatment, or weight change as appropriate. A disabled selected control must remain visibly selected while becoming muted; disabling it must not make its stored value appear unselected. Custom React Native components must communicate `selected` or `checked` state to assistive technology according to their role.

A component can be selected and pressed at the same time. The selected palette describes its persistent baseline; the temporary pressed treatment is applied on top and should be finalized when that concrete component is visually validated.

## Motion foundation

Sarflog uses a small semantic motion vocabulary for custom animation. Duration is chosen by the size, distance, and purpose of the change, not arbitrarily by each component. These durations are shared across light and dark mode.

### Duration scale

| Semantic duration | Value | Typical use |
| --- | ---: | --- |
| Feedback | `100ms` | Button press color, checkbox response, switch feedback |
| Fast | `150ms` | Chip selection, icon change, tab indicator, small fade |
| Standard | `240ms` | Menu, toast, accordion, small content reveal |
| Slow | `400ms` | Large modal, full-screen transition, important expansion |

Feedback begins immediately; the duration describes how long the visual change takes to finish and must never delay the underlying action. Larger elements and longer travel distances receive more time. Routine interactions stay fast and quiet. Rare expressive moments, such as achieving a major savings goal, may compose several approved motions, but do not receive an unrestricted custom duration merely for decoration.

### Easing curves

Easing describes how velocity changes during a duration. Sarflog initially exposes four timing curves:

| Semantic easing | Cubic Bezier | Use |
| --- | --- | --- |
| Standard | `cubic-bezier(0.2, 0, 0, 1)` | Elements that remain visible throughout a change, such as resizing or rearranging |
| Enter | `cubic-bezier(0, 0, 0, 1)` | Elements entering the view; starts quickly and settles gently |
| Exit | `cubic-bezier(0.3, 0, 1, 1)` | Elements leaving the view; accelerates away |
| Linear | `cubic-bezier(0, 0, 1, 1)` | Continuous non-spatial progress such as an indeterminate spinner; not normal interface movement |

Use Enter when content appears and Exit when it disappears. Use Standard when an element is visible at both the start and end. Avoid linear easing for ordinary movement because it feels mechanical and stops abruptly.

### Motion behavior

- Exits normally use one duration tier faster than their corresponding entrances. For example, a large sheet may enter with Slow and exit with Standard.
- Gesture-driven elements follow the user's finger directly with no fixed-duration delay. After release, a platform-appropriate, well-damped spring may settle a sheet, swipe action, or similar physical element.
- Spring motion is defined by physics rather than a fixed millisecond duration. Exact spring parameters remain component-level decisions that require on-device validation.
- Avoid decorative bounce, elastic overshoot, parallax, and repeated movement in routine finance workflows.
- Motion must be purposeful, interruptible where possible, and must not prevent the user from continuing.
- Native navigation, switches, pickers, sheets, and other platform controls may retain familiar native motion. Sarflog does not override native behavior merely to force every component onto a custom timing curve.
- Loading-spinners and real network waits are not measured by the one-shot duration scale. A spinner may repeat continuously, while the network operation finishes whenever the real work completes.

### Reduced motion

Sarflog respects the Android and iOS system Reduce Motion preference. When it is enabled:

- replace large spatial translations, scaling, depth changes, animated blur, parallax, bounce, and celebrations with a short fade, color/shape change, or immediate state update;
- keep essential state feedback through text, icons, color, shape, and position rather than animation alone;
- allow gesture-driven controls to continue following the user's finger while removing unnecessary settling or overshoot;
- do not remove progress communication merely because motion is reduced; use the least motion necessary to communicate that work is ongoing.

Reduced motion is an alternative presentation of the same state change, not a separate product behavior. It must be tested on both Android and iOS.

## Deferred implementation and validation details

The following details are intentionally resolved during component implementation and on-device validation. Apply the documented foundation and `ACCESSIBILITY.md` automatically; request another product decision only when a genuine tradeoff, platform limitation, or exception appears:

- exact component-specific spacing assignments beyond the confirmed scale;
- exact light/dark and Android/iOS shadow recipes for the confirmed depth levels;
- component-specific motion compositions and gesture spring recipes;
- reduced-motion implementation and on-device validation;
- component-specific selected-plus-pressed and disabled-selected rendering recipes;
- feature-level rules for when HeroUI's outline, tertiary, or danger-soft variants have a distinct product role;
- exact focus-outline geometry and platform rendering;
- component-specific contrast validation for opacity, translucency, overlays, imagery, and actual adjacent colors;
- component-specific large-text reflow recipes and on-device validation;
- component-specific screen-reader copy, hints, accessibility actions, and spoken financial wording;
- final focus-management behavior and VoiceOver/TalkBack validation across Uzbek, Russian, and English;
- font fallback behavior if a bundled asset fails unexpectedly.

The centralized foundation is now sufficient to implement and visually validate the first shared component gallery.
