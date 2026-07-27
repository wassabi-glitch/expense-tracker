# Sarflog Mobile Accessibility Contract

This is the plain-language implementation checklist for Sarflog mobile accessibility. It applies to every shared component and screen on Android and iOS, in light and dark mode, and in Uzbek, Russian, and English.

Routine accessibility requirements are approved by default. They do not need a separate product discussion for every button, input, card, or screen. Escalate only when a real product tradeoff, platform limitation, or justified exception appears.

## Goal

A user must be able to complete Sarflog's important money tasks if they:

- need larger or higher-contrast text;
- cannot distinguish information by color;
- use TalkBack or VoiceOver instead of looking at the screen;
- have difficulty tapping small targets or performing precise gestures;
- reduce motion;
- use Uzbek, Russian, or English.

Accessibility is part of the normal app, not a separate accessible version.

## Required behavior

### Seeing and reading

- Normal text reaches at least `4.5:1` contrast; large text and meaningful non-text indicators reach at least `3:1`.
- Check every real foreground/background pair in both light and dark mode.
- Never communicate status, error, selection, or meaning through color alone. Add text, an icon, a shape, position, or another structural cue.
- Follow the phone's text-size setting. Do not disable font scaling globally or shrink essential text merely to preserve a compact layout.
- Core flows remain usable at `200%` text and at the platform's largest accessibility text setting.
- Text wraps, containers grow, button groups stack, and screens scroll instead of clipping or overlapping important content.

### Touching and controlling

- Every interactive element has at least a `48 x 48` touch target, even when its visible icon is smaller.
- Touch targets do not overlap, and related controls have enough separation to avoid accidental taps.
- Important actions do not depend only on swipe, drag, long press, or another precise gesture. Provide a visible control or named accessibility action too.
- Native controls and familiar platform behavior are preferred when they meet Sarflog's design and product needs.

### Hearing and navigating

- Every meaningful control exposes a concise localized name, the correct role, its current state, and its value when relevant.
- Use hints only when the result is not already clear from the name and role.
- Do not write role or state words such as `button`, `checked`, or `disabled` inside the label; TalkBack and VoiceOver announce them.
- Decorative icons, dividers, animations, and duplicate visual children are hidden from the accessibility tree.
- Reading order follows the task. Users can move forward and backward without skipped elements, loops, or focus entering invisible content.
- Headings are identified as headings.
- Opening a screen, menu, sheet, or dialog moves focus to a logical starting point. Closing it restores focus when possible.
- Background refreshes and pagination do not unexpectedly reset the user's reading position.

### Understanding and recovering

- Controls use clear action-and-object wording, especially for dangerous actions: `Delete groceries expense`, not only `Delete`.
- Fields have persistent labels. A placeholder is never the only label.
- Instructions and validation errors identify the exact problem and how to fix it.
- Loading, success, failure, and important status changes are announced once at an appropriate time without creating repeated noise.
- Destructive and difficult-to-reverse actions receive a clear confirmation and a safe way to cancel.
- Haptics, sound, animation, and color may reinforce meaning but never carry the only copy of the meaning.

### Motion

- Respect the Android and iOS Reduce Motion preference.
- Replace unnecessary translation, scaling, bounce, parallax, animated blur, and celebration with a short fade, a static state change, or no motion.
- Keep progress and state feedback available when motion is reduced.
- Gesture-driven elements may follow the user's finger, but unnecessary overshoot and settling are removed.

### Money and data

- Screen-reader text gives financial context instead of reading disconnected numbers and symbols.
- Amounts identify their meaning when the surrounding context is insufficient: spent, received, remaining, owed, paid, or budgeted.
- Dates, currencies, percentages, decimal separators, plurals, and number pronunciation follow the active locale.
- Charts provide a useful text summary and access to the underlying values.
- Ordinary expenses and negative values are not described as errors unless they truly represent failure or danger.

## Component checklist

Shared components enforce the common behavior below. Screens provide only their specific content and context.

| Component | It must do this |
| --- | --- |
| Text and heading | Scale, wrap, remain readable, and expose true heading structure where appropriate |
| Image and icon | Provide useful alternative text when meaningful; disappear from the accessibility tree when decorative |
| Button and icon button | Expose one button element with a localized action label; communicate disabled and busy states; prevent duplicate activation |
| Text input | Expose label, current value, instructions, disabled/read-only state, and specific error |
| Checkbox, radio, switch, chip, and tab | Expose the correct role and selected/checked/disabled state; never rely on color alone |
| Navigation | Use a logical order, identify the current destination, and move focus sensibly after navigation |
| Transaction row or card | Present title, amount, direction, date, and available actions in a useful order without duplicate noise |
| List | Preserve reading position during loading and expose each meaningful item and action |
| Dialog and bottom sheet | Move focus inside, hide background content, expose a title and actions, and restore focus when closed |
| Toast, banner, and alert | Show readable text and announce important changes once without unnecessary interruption |
| Loading and progress | Communicate busy state or progress value without exposing a decorative spinner as a separate control |
| Chart and visualization | Provide a concise summary and a navigable text/list alternative for the data |
| Gesture interaction | Provide a standard button, menu item, or named accessibility action for the same result |
| Destructive action | Name the affected object, confirm when necessary, and never depend on red color alone |
| Empty, error, and offline state | Explain what happened and provide a clear recovery action when one exists |

## Button reference

- Visible `Save expense` -> screen reader: `Save expense, button`.
- Icon-only back arrow -> screen reader: `Go back, button`.
- Disabled save -> screen reader communicates `Save expense` and disabled state; the reason is available when it is not obvious.
- Loading save -> visible and spoken progress wording such as `Saving expense`; busy and disabled states are exposed; repeated taps are blocked.
- Destructive icon -> screen reader: `Delete groceries expense, button`; the trash icon itself is decorative.
- Primary, secondary, ghost, and destructive styling changes visual priority, not the basic button semantics.

## Uzbek, Russian, and English

- Accessibility labels, hints, actions, errors, values, chart summaries, and announcements use the same localization system as visible copy.
- Translate complete messages or templates. Do not assemble sentences by joining separately translated fragments.
- Use natural word order, grammar, plurals, dates, currency wording, and number pronunciation in each language.
- When a visible label exists, the accessible name includes the visible words in the same order so screen-reader and voice-control users receive a consistent control name.
- Supply the active language to platform accessibility APIs where supported.
- Test layout and speech in all three languages; text length and pronunciation differ even though all three languages are left-to-right.
- Current published Apple and Google built-in screen-reader voice lists do not list Uzbek. Sarflog still supplies correct Uzbek text and tests real-device pronunciation. Do not silently substitute Russian or English.

## Definition of done

A component or screen is not finished until the relevant checks pass:

- light and dark mode;
- Android and iOS;
- normal, `200%`, and maximum accessibility text;
- TalkBack and VoiceOver navigation in both directions;
- Uzbek, Russian, and English copy and layout;
- correct name, role, state, value, grouping, focus, and available actions;
- no essential meaning available only through color, motion, sound, haptics, or a gesture;
- no clipped essential text, overlapping controls, unreachable content, or duplicate activation;
- reduced-motion behavior;
- automated accessibility checks where available and manual completion of the core flow without sight.

The first reference flow is adding an expense from start to finish. Coverage then expands to editing and deleting an expense, checking a budget, navigating dashboard data, and recovering from validation, offline, and network failures.

## Ownership

- Shared UI primitives enforce reusable accessibility behavior.
- Product screens supply context-specific localized labels, financial descriptions, errors, and focus destinations.
- A copied component or UI library is an implementation tool and must conform to this contract.
- Prefer accessible native behavior over unnecessary customization.
- Record and justify any exception. Never disable an accessibility behavior silently.
- Apply these rules automatically during implementation; do not request separate approval for ordinary accessibility compliance.

## Primary references

- [Apple accessibility guidance](https://developer.apple.com/design/human-interface-guidelines/accessibility/)
- [Apple VoiceOver evaluation criteria](https://developer.apple.com/help/app-store-connect/manage-app-accessibility/voiceover-evaluation-criteria)
- [Android accessibility principles](https://developer.android.com/guide/topics/ui/accessibility/principles)
- [React Native accessibility](https://reactnative.dev/docs/accessibility)
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)

