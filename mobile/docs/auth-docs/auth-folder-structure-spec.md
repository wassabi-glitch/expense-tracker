# Specification: Mobile Authentication Module Structure

**Status:** Approved architecture reference for Round 0 and authentication Rounds 1-5  
**Audience:** Human maintainers and coding agents, including DeepSeek  
**Scope:** Expo mobile source structure, dependency direction, HeroUI ownership, and the development-only authentication state gallery

## Problem Statement

Sarflog's mobile authentication module has empty `api`, `components`, `hooks`, `schemas`, and `screens` directories, but their ownership rules are not yet concrete enough for implementation agents. Without an explicit structure, auth work could accumulate route logic, duplicate HeroUI wrappers, oversized screens, tiny pass-through files, feature-specific copies of shared controls, or a second fake UI inside a preview area.

Authentication also has many states that are difficult or costly to reproduce manually: pending requests, duplicate submission, delivery failure, resend cooldown, offline behavior, invalid or expired links, session restoration, provider cancellation, and long Uzbek/Russian copy. The team needs a low-cost way to inspect these states before every backend round is functional without creating throwaway screens.

## Solution

Use one feature-first authentication module whose real screens and components survive from Round 0 through release. Expo Router owns routes and navigation layouts; `features/auth` owns authentication UI and client behavior; shared infrastructure remains outside the feature.

Round 0 will include a small development-only auth state gallery. The gallery imports the exact production auth components and supplies fixtures and callback adapters. It is not a draft implementation, does not duplicate screens, performs no real network or secret-storage work, and is never reachable from customer navigation.

Later authentication rounds progressively replace fixture adapters with real hooks, API calls, deep-link inputs, and session infrastructure while preserving the approved presentational UI.

## User Stories

1. As a new mobile developer, I want every auth directory to have one clear responsibility, so that I know where new code belongs.
2. As a coding agent, I want an explicit dependency direction, so that I do not introduce circular imports or mix routing, networking, and presentation.
3. As a designer, I want all auth screens to share one visual structure, so that the journey feels cohesive.
4. As a user on a compact phone, I want every auth screen to handle safe areas, keyboard movement, and scrolling consistently, so that fields and actions remain reachable.
5. As a user, I want signup, sign-in, verification, and recovery screens to use consistent fields, actions, errors, and typography, so that the app feels trustworthy.
6. As a user, I want pending, disabled, success, error, offline, and retry states to be intentional, so that I always understand what the app is doing.
7. As a user of Uzbek, Russian, or English, I want auth layouts tested with real translated copy, so that longer text does not break the interface.
8. As a screen-reader user, I want labels, descriptions, errors, and state changes connected correctly, so that authentication is understandable without sight.
9. As a maintainer, I want feature API functions separate from screen rendering, so that backend contracts can change without redesigning the UI.
10. As a maintainer, I want validation schemas separate from visual components, so that validation can be tested directly and reused by form controllers.
11. As a maintainer, I want reusable auth-only UI kept local to the auth feature, so that unrelated features do not depend on authentication internals.
12. As a maintainer, I want truly cross-feature controls promoted to shared application directories, so that expenses, budgets, and auth do not maintain conflicting versions.
13. As a maintainer, I want HeroUI Native consumed rather than copied, so that accessibility and interaction improvements remain centralized.
14. As a maintainer, I want one state gallery that renders real components, so that difficult states can be reviewed without real emails, tokens, rate limits, or provider failures.
15. As a security reviewer, I want the state gallery to make zero live authentication calls and store zero credentials, so that development tooling cannot affect accounts.
16. As a release owner, I want preview/gallery navigation excluded or explicitly development-guarded, so that customers cannot reach internal tooling.
17. As a testing agent, I want public behavior tested at screen, route, and network seams, so that tests remain useful when implementation details change.
18. As a future maintainer, I want abstractions created only after concrete reuse or complexity appears, so that the module does not become a collection of shallow pass-through files.

## Implementation Decisions

### 1. Normative directory contract

The authentication feature uses this target structure. Directories and files are added only when their round requires them; this tree defines ownership rather than requiring empty implementations upfront.

```text
src/features/auth/
├── api/
│   ├── auth-api.ts
│   └── auth-types.ts
│
├── components/
│   ├── auth-screen-layout.tsx
│   ├── auth-header.tsx
│   ├── sign-up-form.tsx
│   ├── sign-in-form.tsx
│   ├── password-field.tsx
│   └── auth-status-alert.tsx
│
├── hooks/
│   ├── use-sign-up.ts
│   ├── use-sign-in.ts
│   ├── use-resend-verification.ts
│   ├── use-verify-email.ts
│   └── use-reset-password.ts
│
├── schemas/
│   ├── sign-up-schema.ts
│   ├── sign-in-schema.ts
│   └── reset-password-schema.ts
│
├── screens/
│   ├── sign-up-screen.tsx
│   ├── check-email-screen.tsx
│   ├── verify-email-screen.tsx
│   ├── sign-in-screen.tsx
│   ├── forgot-password-screen.tsx
│   └── reset-password-screen.tsx
│
└── preview/
    ├── auth-preview-screen.tsx
    └── auth-preview-fixtures.ts
```

This is an intended starting shape, not permission to create one file for every visible element. A field, label, or button remains inline when extraction would only move the same complexity behind an equally large interface. Extract a module when it hides meaningful behavior, is reused, or materially improves locality.

### 2. Directory responsibilities

#### `api`

Owns authentication-specific HTTP contracts: endpoint calls, request/response types, and translation between FastAPI responses and client-facing results. It imports the shared API client from application infrastructure. It does not render UI, navigate, read component state, or access Resend directly.

#### `schemas`

Owns client form schemas and inferred input types for signup, sign-in, and password reset. Backend validation remains authoritative. Schemas do not call APIs, navigate, or format visual errors.

#### `hooks`

Owns screen behavior that composes form state, schemas, TanStack Query mutations, session infrastructure, and navigation outcomes. Hooks expose a small screen-facing interface such as values, field errors, pending state, recoverable error state, and commands. They do not own HeroUI styling.

#### `components`

Owns reusable authentication-only presentation. `AuthScreenLayout` provides the common visual shell; forms and fields compose HeroUI Native components; auth status components communicate product-specific states. Components accept state and callbacks and do not call FastAPI or Resend directly.

#### `screens`

Owns one complete user-visible destination per module. A screen selects the appropriate hook/controller and composes auth components. Screens do not reimplement HTTP calls, theme tokens, or router infrastructure.

#### `preview`

Owns development fixtures and a state-gallery screen. It may import production auth screens/components, but production modules never import from `preview`. It contains no alternative production component implementations.

### 3. `AuthScreenLayout` ownership

`AuthScreenLayout` lives in the auth `components` directory because it is a reusable visual module, not a navigation destination. Signup, sign-in, verification, and recovery screens import it individually. It does not import or render all auth screens.

It owns repeated visual mechanics such as safe-area-aware structure, keyboard avoidance, scroll behavior, content width, standard horizontal padding, background, header position, and footer/action placement. It does not own form state, API calls, navigation decisions, or session state.

### 4. Route ownership

Expo Router route files and `_layout.tsx` files remain under the application route directory. Route files are thin adapters that render a feature screen. The root route layout composes global providers and root navigation; the auth route-group layout configures navigation among public auth routes.

```text
src/app/
├── _layout.tsx
├── (auth)/
│   ├── _layout.tsx
│   ├── sign-up.tsx
│   ├── sign-in.tsx
│   ├── check-email.tsx
│   ├── verify-email.tsx
│   ├── forgot-password.tsx
│   └── reset-password.tsx
├── (app)/
│   └── _layout.tsx
└── (dev)/
    └── auth-preview.tsx
```

The development preview route is guarded by an explicit development check and is not included in customer navigation. Production route files never import preview fixtures.

### 5. Dependency direction

Dependencies flow downward as follows:

```text
Expo routes
    → auth screens
        → auth hooks and auth components
            → auth API and auth schemas
                → shared API/query/session infrastructure

auth components
    → HeroUI Native, shared application UI, layout, and theme

auth preview
    → real auth screens/components plus inert fixtures
```

Reverse dependencies are forbidden. Shared infrastructure never imports from `features/auth`; production auth modules never import from `preview`; unrelated features never import auth-internal components.

### 6. Round 0 UI-first contract

Round 0 builds real presentational auth modules in the normal `components` and `screens` directories. The preview gallery supplies inert state and callbacks to those real modules. It must cover default, focused, validation error, pending, disabled, success, provider/server failure, rate-limited, offline, expired-link, reused-link, resend-cooldown, dark-mode, large-text, and three-language scenarios where applicable.

Later rounds replace preview inputs with real hooks and infrastructure:

- Round 1 activates signup, check-email, resend, and email verification.
- Round 2 activates sign-in, restoration, refresh, and logout.
- Round 3 activates forgot/reset password.
- Round 4 activates Google authentication and account-linking outcomes.
- Round 5 activates session-control and release-hardening experiences.

### 7. HeroUI Native ownership and adaptation

HeroUI Native remains an installed dependency and is never copied into auth, expenses, budgets, or another feature. Files inside `node_modules` are never edited.

Ownership is divided as follows:

```text
Global Sarflog theme and semantic adaptation
├── src/global.css
└── src/theme/

Thin cross-application HeroUI wrappers, only when justified
└── src/components/ui/

Cross-feature Sarflog composition
└── src/components/shared/

Feature-specific composition and meaning
├── src/features/auth/components/
├── src/features/expenses/components/
└── other feature component directories
```

Feature modules normally import HeroUI components directly through granular package exports and compose them with Uniwind layout utilities. Brand colors, typography, shared radii, and semantic state tokens are adapted globally. A feature may create an auth-specific composition such as `PasswordField`, but it does not create its own replacement `Button` or fork a HeroUI component.

A component moves to `components/shared` only after at least two independent features require the same Sarflog-specific composition. A thin wrapper moves to `components/ui` only when it centralizes a real application-wide accessibility, semantic, or integration rule that HeroUI's public API does not already express cleanly.

### 8. HeroUI MCP relationship

The HeroUI MCP server is development documentation tooling for coding agents. It does not supply runtime component code and is not bundled into the application. The installed `heroui-native` package and its compatible peer dependencies remain required. Agents use the MCP to fetch current Native component anatomy, props, examples, and theme variables before implementation.

### 9. File and export conventions

- File names use kebab case; exported React components and types use PascalCase.
- Route modules stay thin.
- Granular HeroUI imports are preferred consistently.
- Avoid feature-wide barrel exports until they provide a demonstrated navigation or import benefit.
- Do not add `types`, `utils`, `services`, or other catch-all directories without a concrete ownership need.
- Do not duplicate TanStack Query server records in Zustand.
- Authentication secrets remain in SecureStore/session infrastructure, never feature presentation or preview fixtures.

## Testing Decisions

1. Tests assert externally visible behavior rather than private hook ordering or component implementation details.
2. Zod schemas receive direct unit tests for accepted and rejected user input.
3. Auth components and screens use React Native Testing Library to cover accessible labels, validation, pending/disabled behavior, error recovery, duplicate activation prevention, and navigation commands.
4. API and TanStack Query behavior uses the installed MSW server. Unhandled network requests fail tests.
5. Router tests cover route selection, auth-route navigation, cold/warm verification links, and protected-route transitions at the Expo Router seam.
6. The preview gallery must be proven inert: it makes no real network request, reads/writes no SecureStore credential, and cannot activate backend state.
7. Preview fixtures cover states that are costly to reproduce manually, but tests remain the authoritative behavioral proof.
8. Real Uzbek, Russian, and English resources participate in locale-key parity tests; selected screens are rendered with long copy and large text.
9. Light/dark mode, reduced motion, keyboard behavior, compact phones, TalkBack/VoiceOver, Android, and iOS are included in visual/manual acceptance proportional to each round.
10. Maestro tests cover only activated production journeys; the state gallery is not treated as end-to-end proof.
11. New auth feature code follows the Round 1 path-specific coverage contract without substituting percentage for enumerated security-state tests.

## Out of Scope

- Implementing FastAPI authentication changes.
- Implementing the Round 0 screens or preview gallery.
- Connecting HeroUI MCP configuration.
- Defining final screen artwork, illustrations, or motion choreography.
- Reorganizing existing backend authentication modules.
- Creating feature-specific forks of HeroUI Native.
- Introducing Storybook or another preview framework.
- Exposing internal preview tooling in production.

## Further Notes

- The preview is expected to save time only if it renders production components with cheap fixtures. If it begins duplicating screens or accumulating business logic, delete or simplify it.
- The root application layout is the global navigation/provider parent. The auth route-group layout is the navigation parent for auth routes. `AuthScreenLayout` is only the shared visual parent used inside each auth screen.
- The architecture favors one clear implementation with multiple adapters: preview fixtures during Round 0 and real hooks/API/session adapters in later rounds.
- This local specification is the requested DeepSeek reference and intentionally contains normative paths even though general product-spec templates usually avoid them.
