# UI Library Integration Contract

Sarflog and HeroUI Native have separate ownership. Sarflog owns product identity and meaning. HeroUI owns the component-level visual language and interaction polish selected for the app.

```text
Sarflog brand and semantic decisions
        ->
HeroUI CSS theme adapter in global.css
        ->
HeroUI Native components and interaction behavior
        ->
Feature screens
```

## Sources of truth

- `src/theme/index.ts` remains the public doorway for React Native style objects used outside HeroUI.
- `src/global.css` adapts the approved Sarflog colors and fonts to HeroUI and Uniwind.
- Raw palette shades stay private to `src/theme`.
- HeroUI's shapes, internal spacing, label treatment, state feedback, and animations are the default. Do not reshape them to resemble the retired local Button.
- Sarflog overrides HeroUI when brand identity, semantic meaning, finance-specific behavior, contrast, localization, or the accessibility contract requires it.
- Values duplicated between the TypeScript theme and `global.css` must be reviewed together when changed. This is an explicit adapter boundary until a build-time generator is justified.

## Ownership

| Tool | It owns or may provide | Sarflog still owns |
| --- | --- | --- |
| HeroUI Native | Component composition, shape, spacing, variants, feedback animation, and built-in accessibility mechanics | Brand green, finance semantics, wording, localization, and acceptance criteria |
| Uniwind / Tailwind CSS | HeroUI class compilation, theme switching, and CSS-variable delivery to native views | Which tokens exist and their approved light/dark values |
| React Native primitives | Native text, input, layout, and accessibility mechanics for product-specific structures | Product meaning and any component not supplied by HeroUI |
| Lucide React Native | Consistent icon shapes when icons are introduced | Icon meaning, size, color, accessible label, and touch target |
| Expo UI | Familiar native controls where they materially improve platform behavior | Semantic colors, wording, state meaning, and accessibility requirements |
| Form and state libraries | Data, validation, loading, submission, and caching mechanics | Visual treatment and accessible communication of those states |

## Styling boundary

Use HeroUI Native directly for components it supports. Use its documented variants and composition API before adding `className` or `style` overrides. Feature code may use Uniwind utilities for layout, while product-specific React Native structures may continue using `StyleSheet` and the TypeScript theme.

Do not install NativeWind or React Native Reusables alongside this stack. Do not introduce random palette shades, one-off spacing, or a second component vocabulary.

HeroUI Native currently targets Android and iOS; its documentation does not recommend it for Expo web. The browser gallery is a development convenience and may use focused platform fallbacks if a component fails on web. Native behavior remains authoritative.

## Component adoption workflow

For every shared or third-party component:

1. Start with the matching HeroUI Native component and its documented variants.
2. Keep HeroUI's visual defaults unless a concrete Sarflog requirement conflicts.
3. Map brand and semantic colors through `src/global.css`, not repeated per-component overrides.
4. Implement loading, disabled, selected, error, focus, and destructive behavior when relevant.
5. Apply `ACCESSIBILITY.md` automatically.
6. Add supported variants and states to the foundation gallery.
7. Validate light/dark mode, large text, reduced motion, TalkBack/VoiceOver, and Android/iOS behavior before product use.
8. Use granular HeroUI imports such as `heroui-native/button` to keep the native bundle focused.

## Primary button example

HeroUI Native provides the button shape, internal spacing, label treatment, disabled styling, and scale/highlight feedback. Sarflog supplies:

- `--accent: #22C55E` and `--accent-foreground: #052E16` in `global.css`;
- action wording and loading/error meaning;
- any finance-specific accessible label;
- the accessibility contract for role, state, duplicate-activation prevention, and reduced motion.

The result keeps HeroUI's visual character while replacing its stock accent with Sarflog's confirmed accessible brand pair.

## Native-build rule

JavaScript, CSS tokens, and ordinary component composition use Fast Refresh. Adding a package with new Android/iOS native code requires a new development build. Batch native dependencies and create one build after the stack is settled.

The currently installed development client predates `react-native-svg`. Avoid rendering SVG icons there. Expo Go in SDK 57 already includes `react-native-svg` and may be used for interim component previews; a later Sarflog development build will include it permanently.

## Release rule

The gallery is internal development tooling. Remove it from customer navigation before production release, or guard it behind an explicit development-only route.
