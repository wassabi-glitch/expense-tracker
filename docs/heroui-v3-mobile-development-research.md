# HeroUI v3 for Sarflog Mobile: Suitability Research

Date: 2026-07-18

## Decision

HeroUI is a good candidate for Sarflog's native mobile UI, with one important naming distinction:

- `@heroui/react` is HeroUI v3 for browser-based React applications. Use it for responsive web or a PWA.
- `heroui-native` is the separate React Native implementation for real Android/iOS apps built with Expo. This is the package that suits Sarflog's `mobile/` application.

HeroUI officially describes both the web and native libraries as production-ready. The native library is attractive for Sarflog because it provides polished form controls, cards, tabs, dialogs, bottom sheets, menus, select controls, toasts, touch feedback, theming, animation, and accessibility-aware behavior. However, it should be adopted through Sarflog-owned wrappers and a deliberate theme adapter, not imported indiscriminately throughout feature screens.

The recommendation is **adopt HeroUI Native incrementally**, starting with a small proof of concept for `Button`, `Input`/`TextField`, `Select`, `Dialog`, and one bottom-sheet flow. Keep Sarflog's semantic TypeScript theme and accessibility contract as the authority. Pin HeroUI Native to an exact version, validate on both Android and iOS, and retain native or specialist components for gaps such as date pickers.

Official overview: [HeroUI v3 release](https://heroui.com/en/docs/react/releases/v3-0-0), [HeroUI Native introduction](https://heroui.com/en/docs/native/getting-started).

## Web mobile versus native mobile

| Target | Correct HeroUI package | Verdict |
| --- | --- | --- |
| Responsive browser UI / PWA | `@heroui/react` + `@heroui/styles` | Good fit for a React 19+ and Tailwind CSS v4 web frontend. It renders browser UI; PWA installation, caching, offline behavior, and device integrations remain application concerns. |
| Expo / React Native Android and iOS app | `heroui-native` | Correct fit. It renders native React Native views and is built on Tailwind CSS v4 through Uniwind. |
| Expo Web from the native application | Neither as a single cross-platform shortcut | HeroUI explicitly says HeroUI Native is currently not recommended for Expo Web. Use HeroUI React for web and HeroUI Native for iOS/Android. |

The official v3 announcement calls HeroUI Native a different rendering engine with the same mental model, rather than the web package reused on native. Sources: [v3 announcement](https://heroui.com/en/docs/react/releases/v3-0-0), [Native quick start and Expo Web caveat](https://heroui.com/en/docs/native/getting-started/quick-start), [Web quick start](https://heroui.com/en/docs/react/getting-started/quick-start), and [supported web frameworks](https://heroui.com/en/docs/react/getting-started/frameworks).

## Current maturity

### HeroUI v3 Web

- HeroUI v3 reached stable status in March 2026. The current documented release is v3.2.2, dated June 19, 2026.
- The official introduction says it is production-ready. It has 75+ web components and is based on React Aria Components and Tailwind CSS v4.
- Requirements are React 19+ and Tailwind CSS v4. Official framework instructions cover Next.js and Vite.

Sources: [all web releases](https://heroui.com/en/docs/react/releases), [web introduction](https://heroui.com/en/docs/react/getting-started), [web quick start](https://heroui.com/en/docs/react/getting-started/quick-start), and [framework setup](https://heroui.com/en/docs/react/getting-started/frameworks).

### HeroUI Native

- HeroUI Native graduated to its first stable release, v1.0.0, in March 2026. The current documented release is v1.0.5, dated July 2, 2026.
- HeroUI calls it production-ready and says it is actively used in production applications.
- v1.0.5 aligns the library with Expo 57, React Native 0.86, Reanimated 4.5, React Native Worklets 0.10, Tailwind CSS 4.3, and Uniwind 1.10.
- It is still a young, fast-moving library. Notably, the v1.0.5 patch release contains an explicitly labeled breaking field-border token change. This is evidence to pin versions and review every release rather than allowing unattended patch upgrades.

Sources: [Native releases](https://heroui.com/en/docs/native/releases), [v1.0.5 release notes](https://heroui.com/en/docs/native/releases/v1-0-5), and [Native introduction](https://heroui.com/en/docs/native/getting-started).

## Stack and setup requirements

For an existing Expo application, the official setup requires:

- `heroui-native`;
- Tailwind CSS v4 through Uniwind;
- `react-native-reanimated`, `react-native-gesture-handler`, `react-native-worklets`, `react-native-safe-area-context`, `react-native-svg`, `tailwind-variants`, and `tailwind-merge`;
- `GestureHandlerRootView` around `HeroUINativeProvider` at the application root;
- imports for Tailwind, Uniwind, and HeroUI Native styles plus a HeroUI source path in `global.css`;
- optionally, `react-native-screens` for several overlays and `@gorhom/bottom-sheet` for `BottomSheet` and bottom-sheet presentation modes.

HeroUI recommends keeping documented peer versions closely aligned because mismatches can cause bugs. It also warns that granular imports only save bundle size if they are used consistently; one root import from `heroui-native` defeats that optimization. Source: [HeroUI Native quick start](https://heroui.com/en/docs/native/getting-started/quick-start).

## Fit with the current Sarflog repository

The dependency decision has already been partially made in code:

- [`mobile/package.json`](../mobile/package.json) already declares HeroUI Native 1.0.5, Expo 57.0.7, React Native 0.86.0, Reanimated 4.5.0, Worklets 0.10.0, Tailwind CSS 4.3.0, Uniwind 1.10.0, and the other mandatory peers. This matches the current official v1.0.5 toolchain closely.
- The optional `react-native-screens` dependency is present. `@gorhom/bottom-sheet` is not present, so HeroUI's BottomSheet and bottom-sheet presentations are not currently available.
- [`mobile/src/global.css`](../mobile/src/global.css) does not yet include HeroUI's required Tailwind, Uniwind, HeroUI styles, and source imports.
- [`mobile/src/app/_layout.tsx`](../mobile/src/app/_layout.tsx) does not yet wrap the app in `GestureHandlerRootView` and `HeroUINativeProvider`.
- No mobile source file currently imports `heroui-native`, so the package is installed but not integrated.

There is also a real architecture decision to reconcile. [`mobile/LIBRARIES.md`](../mobile/LIBRARIES.md) currently records Uniwind as deliberately not adopted, while [`mobile/src/theme/LIBRARY-INTEGRATION.md`](../mobile/src/theme/LIBRARY-INTEGRATION.md) says Sarflog's TypeScript theme must remain the source of truth and that libraries may not become a competing visual authority. HeroUI Native necessarily brings a CSS/Uniwind token system. Adoption therefore needs a documented adapter or an explicit decision that supersedes the older library roadmap; silently maintaining two independent theme systems would violate the existing contract.

## What suits a finance app well

The native catalog covers many high-value building blocks for an expense tracker: buttons, inputs, text fields, text areas, validation descriptions/errors, checkbox/radio/switch controls, select, tabs, cards, list groups, dialogs, menus, popovers, bottom sheets, alerts, toasts, skeletons, and typography. Select can use popover, dialog, or mobile-optimized bottom-sheet presentation. Sources: [Native component catalog](https://heroui.com/en/docs/native/components) and [Native Select](https://heroui.com/en/docs/native/components/select).

The compound-component model also fits Sarflog's desire to own composition and product meaning. Component parts can be rearranged and styled rather than treated as sealed black boxes. Source: [Native design principles](https://heroui.com/en/docs/native/getting-started/design-principles).

## Gaps and caveats

1. **It is not a complete finance-app toolkit.** The current native catalog does not list a Calendar/DatePicker, Table/DataGrid, charting system, or complete navigation shell. Sarflog will still need platform or specialist solutions, especially a native date picker and accessible chart alternatives. This is an inference from HeroUI's complete published [Native component catalog](https://heroui.com/en/docs/native/components).

2. **Native Web is not the intended target.** If Sarflog wants a shared browser build, use the web package in the web frontend rather than expecting `heroui-native` to cover Expo Web. Source: [Native quick start](https://heroui.com/en/docs/native/getting-started/quick-start#running-on-web-expo).

3. **iOS native-modal overlays need care.** Menu, Popover, and Select can render vertically offset when their trigger is inside an iOS native modal. HeroUI documents a safe-area offset workaround. Source: [v1.0.4 native release notes](https://heroui.com/en/docs/native/releases/v1-0-4).

4. **Some overlay accessibility behavior is still explicitly unstable.** VoiceOver modal containment for portal overlays maps through an unstable prop and needs real-device testing. Source: [v1.0.2 native release notes](https://heroui.com/en/docs/native/releases/v1-0-2).

5. **The visual "vibrant" palette trades away some contrast.** HeroUI warns that its optional vibrant soft-foreground palette may not meet WCAG for some color combinations. Sarflog should keep the accessible default or verify every mapped pair against its own accessibility contract. Source: [Native theming](https://heroui.com/en/docs/native/getting-started/theming#vibrant-palette).

6. **Dependency and bundle discipline matter.** The native package has multiple peers, and some components add optional peers. Granular imports must be applied consistently to have an effect. Source: [Native quick start](https://heroui.com/en/docs/native/getting-started/quick-start).

## Accessibility and mobile interaction

HeroUI's accessibility foundations are a meaningful advantage, but they do not replace product-level testing:

- Web v3 is based on React Aria Components, with focus management, keyboard navigation, screen-reader behavior, and ARIA attributes built in. Source: [HeroUI v3 introduction](https://heroui.com/en/docs/react/getting-started).
- Native components claim touch accessibility, focus handling, semantic structure, and screen-reader support for VoiceOver and TalkBack. Source: [Native design principles](https://heroui.com/en/docs/native/getting-started/design-principles#2-accessibility-as-foundation).
- HeroUI Native automatically respects the device Reduce Motion setting through Reanimated. Source: [Native animation accessibility](https://heroui.com/en/docs/native/getting-started/animation#accessibility).
- v1.0.5 added iOS Dynamic Type ramps to its Typography component and provider-level font-scaling configuration for inputs. Source: [v1.0.5 release notes](https://heroui.com/en/docs/native/releases/v1-0-5).

Sarflog should still test actual money flows with maximum text size, VoiceOver/TalkBack, localized Uzbek/Russian/English text, reduced motion, and at least 48-by-48 touch targets. A library can provide sound primitives while the application remains responsible for localized labels, financial context, focus order, error recovery, and alternative access to gestures.

## Official agent skills

Yes. HeroUI provides official, installable agent skills for both products:

- `heroui-react` for HeroUI v3 web;
- `heroui-native` for React Native mobile;
- the official source repository also contains a migration skill.

For Sarflog mobile, install/use `heroui-native`:

```bash
curl -fsSL https://heroui.com/install | bash -s heroui-native
```

Or install from the official skills package:

```bash
npx skills add heroui-inc/heroui
```

Compatible assistants discover the skill automatically, or it can be invoked as `/heroui-native`. It includes installation guidance, component props/examples, Uniwind theming/styling, design principles, and documentation helper scripts. Sources: [HeroUI Native Agent Skills](https://heroui.com/en/docs/native/getting-started/agent-skills), [HeroUI React Agent Skills](https://heroui.com/en/docs/react/getting-started/agent-skills), and [official skills source](https://github.com/heroui-inc/heroui/tree/v3/skills).

The official HeroUI skill is not currently listed in this repository's [`skills-lock.json`](../skills-lock.json) or `.agents/skills/`, so it exists upstream but is not installed in this workspace yet.

## Official MCP servers

Yes. HeroUI publishes separate stdio MCP servers:

- Web: `@heroui/react-mcp`
- Native: `@heroui/native-mcp`

Both require Node.js 22 or newer. This workspace currently has Node.js 24.12.0, so it satisfies that runtime requirement. The native MCP exposes the current Native component list, component documentation, theme variables, and full guides. The React MCP additionally exposes React component source and CSS styles. Sources: [HeroUI Native MCP](https://heroui.com/en/docs/native/getting-started/mcp-server) and [HeroUI React MCP](https://heroui.com/en/docs/react/getting-started/mcp-server).

For Codex and this native application, the official project-scoped configuration is:

```toml
[mcp_servers.heroui-native]
command = "npx"
args = ["-y", "@heroui/native-mcp@latest"]
```

If the responsive web frontend also adopts HeroUI v3, add the separate web server:

```toml
[mcp_servers.heroui-react]
command = "npx"
args = ["-y", "@heroui/react-mcp@latest"]
```

## Recommended adoption guardrails

1. Resolve and document whether HeroUI Native/Uniwind supersedes the existing "no Uniwind" decision.
2. Keep `src/theme/` as the product source of truth. Build one mechanical mapping into HeroUI CSS variables rather than maintaining equivalent values independently.
3. Wrap HeroUI primitives in Sarflog-owned `components/ui` APIs so feature screens depend on product semantics, not library-specific variants.
4. Pin `heroui-native` exactly while the library is young; upgrade intentionally after reviewing release notes and testing Android/iOS.
5. Prototype the hardest pieces first: large-text forms, Select/Dialog/BottomSheet focus behavior, dark mode, screen readers, and iOS native-modal positioning.
6. Keep platform-native/specialist packages for missing components, especially date/time input.
7. Install the official `heroui-native` skill and Native MCP before implementation so agents use current APIs instead of stale v2 or web-only patterns.

## Final assessment

HeroUI Native suits Sarflog technically and aesthetically, and the current mobile dependency versions already align with its latest official release. The decisive concern is not compatibility; it is ownership of the design system. If Sarflog maps HeroUI into its existing semantic theme and accessibility contract, HeroUI can save substantial work on complex, polished, accessible interaction primitives. If HeroUI defaults are used directly everywhere, Sarflog will acquire a second theme system and stronger library coupling than its current architecture permits.
