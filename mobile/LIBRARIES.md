# Mobile Library Roadmap

This document records mobile dependencies and why Sarflog needs them. Add a library only when its use case is being implemented. For native Expo packages, prefer `npx expo install` so Expo selects a compatible version.

The API, authentication, query, form, localization, client-state, and unit/component testing foundations described below were installed when real mobile feature work began. Installation does not relax the ownership rules in this document: a package may be available without being the correct owner for every kind of state.

All UI tools must follow the [UI library integration contract](src/theme/LIBRARY-INTEGRATION.md). Sarflog owns brand identity, semantic meaning, and product accessibility. HeroUI Native owns the visual and interaction defaults of the components it supplies.

The default UI approach is HeroUI Native with Uniwind for supported components, and React Native primitives for product-specific structures or gaps in the library. Do not recreate a HeroUI component with local styles unless a documented product requirement cannot be met through its public API.

## Use now

| Library | Purpose | Why Sarflog needs it |
| --- | --- | --- |
| `heroui-native` | Mobile component system | Provides the selected component visual direction, polished feedback, accessible composition, and consistent Android/iOS behavior. Sarflog maps brand and semantic tokens into HeroUI instead of restyling components from scratch. |
| `uniwind` | Native styling and theme runtime | Powers HeroUI's Tailwind classes, light/dark switching, and CSS-variable theme adapter. Use the free JavaScript version; Pro is not needed. |
| `tailwindcss` | HeroUI style compiler | Compiles HeroUI and Sarflog's CSS theme adapter through Uniwind. It is infrastructure, not permission for arbitrary feature-level values. |
| `tailwind-variants` / `tailwind-merge` | HeroUI variant mechanics | Required HeroUI peers for component variants and safe class composition. Prefer built-in variants over duplicate local ones. |
| `expo-router` | File-based navigation | Keeps routes in `src/app` and supports shared Android/iOS navigation. Already installed. |
| `axios` | HTTP client | Calls the FastAPI backend and centralizes the API URL, authentication, `X-Timezone`, timeouts, and error handling. |
| `@tanstack/react-query` | Server-state management | Caches API data and manages loading, errors, retries, refetching, mutations, and cache invalidation. It complements Axios rather than replacing it. |
| `expo-secure-store` | Secure local storage | Stores authentication tokens using Android Keystore and iOS Keychain instead of ordinary unencrypted storage. |
| `react-hook-form` | Form state | Manages values, touched fields, submission, resetting, and field errors without excessive rerenders. |
| `zod` | Runtime validation | Defines typed validation rules for forms and untrusted API data. FastAPI/Pydantic remains the final authority. |
| `@hookform/resolvers` | Form/schema integration | Connects React Hook Form to Zod through `zodResolver`. |
| `expo-localization` | Native locale and timezone information | Reads the device's language, region, calendar, 12/24-hour preference, and effective timezone. It supplies native preferences; it is not the translation engine. |
| `expo-screen-orientation` | Runtime orientation policy | Locks compact phone-sized windows to portrait while allowing tablets and unfolded large screens to follow the system orientation. The app-level orientation remains `default` so large screens are not statically blocked. |
| `i18next` | Translation engine | Owns translation resources, key lookup, fallback behavior, interpolation, pluralization, and language switching for Uzbek, Russian, and English. |
| `react-i18next` | React bindings for i18next | Exposes translated copy through React hooks and keeps mounted UI synchronized when the language changes. |
| `@react-native-async-storage/async-storage` | Non-sensitive preference storage | Persists the user's selected language and other non-secret preferences. Authentication secrets must never be stored here. |
| `zustand` | Cross-screen client state | Available for concrete client-only state such as a multi-screen draft or onboarding progress. Do not mirror FastAPI records or TanStack Query caches in Zustand. |
| `react-native-svg` | Native SVG rendering | Provides Expo-compatible SVG primitives used by Lucide. Installed with the Expo SDK 57-compatible version. |
| `lucide-react-native` | Icons | Supplies Sarflog's consistent cross-platform outline icon family. Import concrete icons rather than the complete dynamic icon map. Installed. |
| `@expo-google-fonts/inter` | Brand typography | Supplies the confirmed Inter font assets. Sarflog imports and bundles only Regular 400 and Semibold 600. Installed. |

## Already installed by the Expo project

| Library | Purpose | How we will use it |
| --- | --- | --- |
| `@expo/ui` | Native Android/iOS controls | Use selectively when a native Switch, Picker, BottomSheet, or similar control provides better platform behavior. It is not the primary design system. |
| `react-native-safe-area-context` | Safe-area handling | Keeps content away from notches, status bars, and home indicators. |
| `react-native-reanimated` | Native animations | Powers polished transitions and animations without blocking the JavaScript thread. |
| `react-native-gesture-handler` | Native gestures | Supports reliable swipes, pans, sheets, and other touch interactions. |
| `react-native-screens` | Native screen containers | Improves navigation integration and screen performance. |
| `expo-image` | Image rendering | Handles optimized images, caching, placeholders, and transitions. |

## Deliberately not adopted

| Tool | Current decision | Reconsider only when |
| --- | --- | --- |
| `nativewind` | Do not install. HeroUI Native uses Uniwind, so NativeWind would duplicate the same responsibility. | Only if HeroUI drops Uniwind in a future major version and publishes an official migration path. |
| React Native Reusables | Do not install alongside HeroUI. It would introduce a second component system and conflicting visual defaults. | A required component is absent from HeroUI and cannot be built cleanly from React Native primitives. |
| Motion / Framer Motion | Do not install. It targets browser HTML/SVG and the Web Animations API, not native Android/iOS views. | Never for native UI; use it only in an independent web-only surface. |
| Moti | Do not install another abstraction over Reanimated yet. | Repeated Reanimated component code proves a wrapper would remove meaningful duplication without hiding required behavior. |
| `@react-native-vector-icons/*` | Do not mix a second general product icon family with Lucide. | A required symbol or brand mark does not exist in Lucide and cannot be supplied as a focused owned asset. |
| `react-test-renderer` | Do not install. It is deprecated for the React 19 mobile stack and is not the user-behavior testing API. | Never for new tests; use React Native Testing Library. |
| `@testing-library/jest-native` | Do not install. Current React Native Testing Library versions include the native Jest matchers. | Only if an upstream compatibility change explicitly requires it. |
| Lottie | Do not use for ordinary component feedback. | A designed celebration, onboarding illustration, or other authored animation has a concrete product role. |

## Add later when a feature requires it

| Library | Add it when | Reason |
| --- | --- | --- |
| `@react-native-community/netinfo` | We implement reconnect-aware queries | Lets TanStack Query pause/refetch based on actual network connectivity. |
| `@react-native-community/datetimepicker` | Forms require native date/time selection | Provides familiar Android and iOS date/time controls. |
| `expo-haptics` | Important actions need tactile feedback | Adds restrained feedback for successful saves, destructive confirmations, and key interactions. |
| `expo-notifications` | Reminders and due-date notifications are implemented | Supports push notifications and scheduled local notifications. |
| `expo-image-picker` | Receipt or profile image capture is implemented | Opens the camera or photo library with Expo-managed permissions. |
| `@shopify/flash-list` | Large transaction lists show performance problems | Replaces ordinary lists when profiling proves virtualization performance is needed. |
| `expo-sqlite` | Real offline-first behavior is required | Provides an on-device database for durable offline data and synchronization queues. |
| `@sentry/react-native` | We prepare production monitoring | Captures mobile crashes, native errors, and useful diagnostic context. |

## Testing foundation

| Library/tool | Role | Decision |
| --- | --- | --- |
| `jest` | JavaScript/TypeScript test runner | Installed as a development dependency. Use deterministic non-watch mode in verification and CI. |
| `jest-expo` | Expo-aware Jest preset | Installed as a development dependency. Supplies Expo/React Native transforms and native-module mocks. |
| `@testing-library/react-native` | Component and hook behavior tests | Installed as a development dependency. Prefer accessible queries and user-visible outcomes over implementation details. |
| `expo-router/testing-library` | In-memory route integration tests | Supplied by Expo Router; no additional package is required. Keep tests outside `src/app` so they are not interpreted as routes. |
| `msw` | API integration boundary | Installed. The shared Jest server rejects unhandled requests so tests cannot silently reach a real backend. |
| `eslint-plugin-jest` | Jest test linting | Installed. Focused, disabled, malformed, and unsafe test patterns fail lint. |
| `eslint-plugin-testing-library` | Testing Library linting | Installed. Enforces user-centered queries and guards against common async/test-debugging mistakes. |
| `@types/node` | Node test/tooling types | Installed at the Node 22 major used by mobile CI. |
| Maestro | Native end-to-end journeys | Configured in `.maestro/` and run for Android/iOS through EAS Workflows. It remains an external native runner, not an npm runtime dependency. |

Every product slice must add the lowest-cost test that proves its behavior. Authentication, token rotation, timezone headers, language switching, financial mutations, and navigation guards also require integration coverage at their real boundary. Snapshot-only coverage does not satisfy this rule. `npm run verify` is the local and CI quality gate; the coverage floor is a ratchet and must not be lowered to make a change pass.

## State ownership rule

Use one owner for each kind of state:

```text
Component-only state       -> React useState
Form state                 -> React Hook Form
Form/data validation       -> Zod
FastAPI/server state       -> TanStack Query
Cross-screen client state  -> Zustand, only when needed
Authentication secrets     -> Expo SecureStore
Selected app language      -> AsyncStorage
Translated product copy    -> i18next
```

Avoid putting the same data in multiple state systems. In particular, expenses, budgets, wallets, debts, and other FastAPI records belong in TanStack Query rather than Zustand.
