# Sarflog Mobile Agent Rules

These instructions apply to every file under `mobile/`. They are the default engineering contract for human maintainers and coding agents. A task-specific approved spec or ticket may add stricter requirements, but it must not silently weaken these rules.

`CLAUDE.md` imports this file, so this is also the canonical rulebook for Claude Code and any model used through it. Do not create a competing mobile instruction file.

## 1. Start every implementation here

Before editing:

1. Read this file completely.
2. Read the approved spec, ticket, and nearby documentation for the feature.
3. Inspect the current implementation, tests, and `git status`; do not assume the docs describe unfinished code accurately.
4. State the narrow behavior being changed and what must remain unchanged.
5. Identify the tests that will prove the behavior before implementing it.

The active project is the repository opened on `D:`. Do not edit, install into, or execute project code from the retired `C:` clone. Resolve project paths from the current repository root instead of copying old absolute paths. External skills or tools installed under a user profile are not project copies, but they must never be mistaken for the active source tree.

Preserve unrelated user changes in the dirty worktree. Do not delete, reset, reformat, or “clean up” files outside the requested slice.

## 2. Use the installed mobile stack

This project is Expo SDK 57 with React Native 0.86 and TypeScript. Expo has changed: before writing Expo-specific code, read the exact versioned documentation at <https://docs.expo.dev/versions/v57.0.0/>. Do not rely on remembered APIs from older Expo releases.

- Run mobile npm and Expo commands from `mobile/`, not the repository root.
- Use the existing `npm` lockfile. Do not introduce Yarn, pnpm, or another lockfile.
- Check `package.json` before adding a dependency; do not install a second library for a problem the stack already solves.
- Use `npx expo install` for Expo or React Native native dependencies so Expo selects compatible versions.
- Use `npm install` for ordinary JavaScript-only dependencies.
- Run the Expo dependency compatibility check after dependency changes.
- A package that adds native Android/iOS code requires a new development build. Batch justified native dependencies rather than repeatedly rebuilding.
- Never run `npm audit fix --force` or accept an Expo/React Native downgrade merely to silence advisories.
- Never edit `node_modules`, generated native folders, caches, build output, or package-manager internals.

## 3. Follow feature-first architecture

Expo Router owns routes and navigation layouts. Route modules stay thin: they select and render a feature screen and do not contain feature business logic.

Feature modules own their own behavior and presentation. Use these responsibilities when they exist:

- `api/`: feature-specific HTTP contracts using the shared API client; no rendering or navigation.
- `schemas/`: Zod input rules and inferred input types; no network or visual behavior.
- `hooks/`: form/query/session orchestration and screen-facing commands; no component styling.
- `components/`: reusable feature presentation with state and callbacks; no direct API calls.
- `screens/`: complete destinations that compose hooks and components; no duplicated infrastructure.
- `preview/`: inert development fixtures that render real production components; production code never imports preview code.

Keep dependencies flowing from routes to screens to hooks/components to API/schemas/shared infrastructure. Do not create reverse imports, circular dependencies, catch-all `utils` folders, or barrel files without a demonstrated benefit.

Extract a component or helper only when it hides meaningful behavior, is reused, or materially improves locality. Do not create one file for every visible label or wrapper.

## 4. HeroUI Native is the component foundation

- Start with the matching HeroUI Native component for buttons, fields, cards, dialogs, alerts, and other supported controls.
- Before using an unfamiliar HeroUI component or guessing a prop, variant, anatomy, theme variable, or composition pattern, query the connected HeroUI Native MCP. If the MCP is unavailable, use the current official HeroUI Native documentation; do not invent an API from memory.
- The MCP provides documentation to the agent. Runtime components still come from the installed `heroui-native` package.
- Prefer granular imports such as `heroui-native/button` rather than a package-wide import.
- Use HeroUI variants and composition APIs before adding custom overrides.
- Never copy HeroUI source into a feature, edit the installed package, or create feature-specific replacements for base controls.
- Keep feature-specific compositions in the feature. Promote a composition to shared UI only after at least two independent features genuinely need the same Sarflog behavior.
- Implement every relevant default, focused, pressed, disabled, busy, selected, success, error, and destructive state.

The detailed ownership contract is in `src/theme/LIBRARY-INTEGRATION.md` and is mandatory.

## 5. Use Uniwind for utility styling

- Use Uniwind `className` utilities for Tailwind-like layout and supported styling in React Native components.
- Do not install or mix NativeWind, React Native Reusables, web Tailwind runtimes, CSS modules, or a second utility-style system.
- `StyleSheet` and direct React Native style objects remain acceptable for genuinely dynamic native values, complex performance-sensitive structures, platform APIs, and behavior that Uniwind cannot express cleanly.
- Do not use web-only CSS properties or assume DOM layout behavior.
- Avoid arbitrary values when an approved Sarflog token or HeroUI variant exists.

## 6. Themes and design tokens are mandatory

Sarflog owns product identity; HeroUI owns component-level polish.

- Use semantic colors, typography, spacing, radii, sizes, elevation, and motion from `src/theme/`.
- `src/global.css` is the HeroUI/Uniwind theme adapter. When changing a value duplicated in TypeScript and CSS variables, update and review both sides together.
- Do not hardcode feature-local hex colors, random spacing, radii, control heights, font sizes, shadows, or animation durations.
- Raw palette shades remain private to the theme layer. Feature code consumes semantic roles.
- Use the bundled Inter family and approved weights unless a design decision explicitly changes the type system.
- Use Lucide React Native for ordinary icons when HeroUI or the platform does not already provide the correct control. Icons must have a clear semantic purpose.
- Respect system light/dark preference unless an approved screen specification deliberately defines a fixed appearance.
- Use the approved motion tokens and respect Reduce Motion. No arbitrary bounce, parallax, animated blur, or celebration.

Before building a screen, read its approved UI/UX specification. Do not replace deliberate design decisions with generic template UI.

## 7. Mobile layout is fluid first

This is a React Native mobile application, not a responsive website.

- Build the compact-phone experience first with Flexbox, intrinsic content size, wrapping, safe-area insets, keyboard-aware behavior, scrolling, and content-width caps.
- Do not add random media queries, device-model checks, `isTablet` guesses, or one-off `Dimensions` thresholds.
- Use the canonical adaptive-layout utilities and metrics under `src/layout/`.
- The only approved width transitions are `600` and `840`; the only approved height guard is `480`. New thresholds require a documented structural reason and updates to the layout verification contract.
- A breakpoint may change high-level structure; it does not randomly resize every font, field, card, or button.
- Forms remain within the approved form-width cap on larger windows.
- Controls use minimum heights and are allowed to grow with content. Never lock text-containing controls or screens to a fragile fixed height.
- Compact phones stay portrait through the existing orientation policy. Tablets must remain usable in portrait, landscape, and resized windows.

Read `src/layout/README.md` before changing responsive structure or orientation behavior.

## 8. Localize every user-facing word immediately

Sarflog supports English, Russian, and Uzbek from the beginning of every feature.

- No user-visible text may be hardcoded in components, hooks, schemas, route titles, alerts, validation messages, loading states, empty states, errors, accessibility labels, hints, or announcements.
- Add the English, Russian, and Uzbek translations in the same change. Do not leave placeholder English in another locale.
- Translate complete messages or templates; do not assemble sentences from separately translated fragments.
- Use natural grammar and word order in each language rather than forcing word-for-word equality.
- Run locale-key parity tests in the same change.
- Verify real layouts with all three languages, including long copy and large text.
- Format dates, times, numbers, currencies, percentages, and plurals through locale-aware helpers.
- User-facing dates must use the effective user timezone. Do not introduce naive “today” logic or date-only parsing that can shift the day.

## 9. Use the correct state and form tool

- Use React Hook Form for nontrivial form state and submission behavior.
- Use Zod for client input schemas and localized validation keys. Client validation improves UX; the backend remains authoritative for security and business rules.
- Use TanStack Query for server state, mutations, caching, invalidation, retries, and request lifecycle.
- Use Zustand only for genuine client-side/global UI state that is not server cache and does not belong to a component or route.
- Do not duplicate TanStack Query records in Zustand.
- Use the shared Axios/API boundary rather than ad hoc `fetch` calls scattered through screens.
- UI components receive state and callbacks; they do not contact FastAPI, Resend, OAuth providers, or storage directly.

## 10. Treat security and privacy as product behavior

- Never place secrets, private API keys, service credentials, or privileged endpoints in mobile source or `EXPO_PUBLIC_*` values.
- Store authentication credentials only through the approved SecureStore/session boundary. Never put tokens in AsyncStorage, Zustand persistence, logs, fixtures, screenshots, or error reports.
- Treat deep-link, clipboard, notification, and external-browser inputs as untrusted.
- Prevent duplicate submissions while an action is pending.
- Do not log passwords, tokens, verification links, reset links, personal financial records, or raw provider responses.
- Preview/gallery fixtures are inert: no live network, OAuth launch, SecureStore access, account mutation, or production navigation.
- Development-only routes and galleries must be guarded and excluded from customer navigation.

## 11. Accessibility is part of every implementation

`src/theme/ACCESSIBILITY.md` is mandatory, not optional polish.

At minimum:

- Every interactive control has at least a `48 x 48` touch target.
- Every meaningful control exposes a localized name, correct role, state, and value when applicable.
- Fields use persistent labels; placeholders are never the only label.
- Headings expose heading semantics and focus moves logically after navigation/state changes.
- Loading, error, success, disabled, selected, and busy states are communicated through text/semantics, not color alone.
- Important actions are not gesture-only.
- Text scales, wraps, and scrolls at large accessibility sizes without clipping or hiding actions.
- TalkBack and VoiceOver reading order follows the visible task order.
- Reduced-motion users receive equivalent state feedback without unnecessary movement.

Routine accessibility fixes do not require separate product approval.

## 12. Tests ship with the behavior

Testing is implementation work, not a later cleanup phase. Every functional ticket or bug fix adds or updates the tests that prove its public behavior in the same change.

Choose the highest useful seam:

| Change | Required proof |
| --- | --- |
| Pure function, formatter, token, or Zod schema | Focused Jest unit tests |
| Component or screen behavior | React Native Testing Library interaction and accessibility tests |
| API hook, mutation, or query behavior | Integration test through MSW; no live backend or internet |
| Route, redirect, deep link, or protected navigation | Expo Router harness test |
| Activated release-critical journey | Maestro end-to-end flow on Android and iOS test builds |
| Localized UI | Locale parity plus representative rendered behavior in English, Russian, and Uzbek |

Rules:

- For defined behavior and regression fixes, begin with a failing public-behavior test when practical, then implement the smallest passing change and refactor while green.
- Test happy paths and the highest-risk recovery/failure paths: invalid input, offline/network failure, pending/duplicate action, retry, unauthorized/expired state, and recovery where relevant.
- MSW is the network boundary. Unhandled requests must fail tests rather than reaching FastAPI or the internet.
- Test user-visible behavior, not private hooks, state variable names, component trees, or animation internals.
- Snapshot-only proof is not accepted.
- Never commit `.only`, skipped/disabled tests, commented-out tests, or unjustified `todo` tests.
- Never weaken or delete an assertion merely to make CI pass. Fix the defect or document a genuine blocker.
- Never lower coverage thresholds. New auth code follows its documented path-specific minimum of `90%` statements/functions/lines and `85%` branches, while still testing every enumerated security and recovery state explicitly.
- The handoff lists changed behavior, verification commands/results, and any honest follow-up risk.

### Backend Error Mapping & Testing Pattern
When introducing or handling new backend errors, messages, or features, follow this end-to-end pattern:
1. **Error Mapping:** Catch backend errors appropriately and map them to UI state (avoiding silent failures).
2. **Translations:** Translate the mapped error keys into all 3 supported languages (English, Russian, Uzbek).
3. **Unit Tests:** Write robust unit tests (Jest + `@testing-library/react-native`) verifying that the UI correctly translates and renders the mapped backend error state.
4. **End-to-End Tests:** Write or update a Maestro E2E flow (`.yaml`) simulating the error or feature flow.

**CRITICAL TESTING RULE:**
For mobile, ALWAYS write all existing tests such as Jest and Maestro, but ONLY run Jest during execution because the user's computer struggles to run Maestro every time. This does NOT give you an excuse to cut corners with writing Maestro tests!
For WEB, ALWAYS write all existing tests such as Vitest and Playwright, but ONLY run Vitest during execution because the user's computer struggles to run Playwright every time. This does NOT give you an excuse to cut corners with writing Playwright tests!

## 13. Verification is mandatory

For ordinary mobile code changes, run from `mobile/`:

```text
npm run verify
```

This covers Expo dependency compatibility, TypeScript, lint, layout-policy verification, Jest integration tests, and the coverage ratchet. Run the most focused relevant test during development, then the full verification command before handoff.

Also verify proportionally:

- UI change: Android and iOS behavior, keyboard open/closed, compact phone, wider window/form cap, light/dark or approved fixed appearance, all three languages, large text, and Reduce Motion.
- Navigation/deep-link change: cold and warm launch where relevant.
- Native dependency/config change: rebuild the affected development clients and validate the native configuration.
- Critical production journey: update and run its Maestro flow on the appropriate EAS test build.
- Documentation-only change: validate paths, links, terminology, and internal consistency; the full code suite is not required unless docs alter executable configuration.

Never claim a command passed if it was not run. Report failures, skipped verification, environment limitations, and residual risk plainly.

## 14. Definition of done

A mobile implementation is complete only when:

- It matches the approved spec and ticket without unrelated scope expansion.
- Production components—not duplicate preview versions—implement the behavior.
- HeroUI Native, Uniwind, themes, adaptive layout, localization, and accessibility contracts are followed.
- Default, focused, loading, disabled, error, offline, success, retry, and destructive states are handled when relevant.
- English, Russian, and Uzbek ship together.
- Required automated tests were written at the correct seam and pass.
- Relevant Android/iOS and accessibility checks were completed.
- `npm run verify` passes for code changes.
- No secrets, logs, generated files, unrelated formatting, or user-owned changes were introduced.
- The handoff lists changed behavior, verification commands/results, and any honest follow-up risk.

If a requirement conflicts with an approved spec, platform limitation, dependency capability, security rule, or another instruction, stop and surface the exact conflict instead of silently improvising.
