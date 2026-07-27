# Sarflog Adaptive Layout Foundation

Responsive layout is separate from visual themes.

- `src/theme/` answers how the interface looks: colors, typography, spacing ingredients, radii, elevation, and motion.
- `src/layout/` answers how the interface uses the space currently available to the app.

Changing from light to dark mode must not change a window's size class. Rotating a device, opening a foldable, or entering split-screen may change the size class without changing the theme.

## Fluid layout comes first

Ordinary phone screens should not branch on window width. Build them from React Native's normal adaptive tools: Flexbox, wrapping, vertical scrolling or virtualized lists, safe-area insets, keyboard-aware behavior, intrinsic content size, and maximum content widths. Add a window threshold only when the screen's high-level structure has a real alternate mode.

Sarflog currently has two justified width transitions: `600` changes shared spacing for a tablet-sized window, and `840` makes a real two-pane structure eligible. These are not instructions to resize every font, button, or card at each boundary.

## Approved mobile width classes

**Decision status:** implemented. `window-size.ts` is the canonical runtime source, and `global.css` mirrors the same two thresholds for the few places where Uniwind responsive variants are useful.

Sarflog adopts the current Android window-size class boundaries as a shared Android/iOS adaptive-layout vocabulary. React Native reports the app window in density-independent layout units, so these values classify the space available to the app rather than literal hardware pixels or a guessed device model. The web-oriented ranges in `mobile/DESIGN-revolut.md` are design-research notes and are not mobile layout authority.

| Class | Available width | Sarflog layout intent |
| --- | ---: | --- |
| Compact | below `600` | Phone-first, single-pane layout; every core task must fit without horizontal scrolling |
| Medium | `600` through `839` | Tablet portrait and unfolded-window range; remain single-pane by default |
| Expanded | `840` and above | Intentional list-detail and other two-pane structures become eligible; content caps prevent uncontrolled stretching |

These class names are layout vocabulary, not device detection. A resizable Chromebook window can move through several classes without changing devices.

## Responsive spacing

Layout spacing changes only when the available space makes the change useful:

| Class | Screen gutter | Pane gap |
| --- | ---: | ---: |
| Compact | `16` | `16` |
| Medium | `24` | `24` |
| Expanded | `32` | `24` |

These values reuse Sarflog's spacing tokens. Do not create screen-specific gutter numbers unless a real layout problem proves the shared metric is insufficient.

## TypeScript and Uniwind usage

React Native layout logic uses `useAdaptiveLayout()` and the definitions in `window-size.ts`. Uniwind components use the matching mobile-first variants:

| Range | Uniwind usage |
| --- | --- |
| Compact | Unprefixed base classes |
| Medium and above | `medium:` |
| Expanded and above | `expanded:` |

The default Tailwind breakpoint names are disabled in `global.css` so Sarflog has one responsive vocabulary. `npm run verify:layout` checks every boundary and confirms the Uniwind thresholds still match the TypeScript source.

Sarflog retains one height threshold only because a wide but very short resized window should not activate two panes:

| Class | Available height | Meaning |
| --- | ---: | --- |
| Compact | below `480` | Vertically cramped, commonly landscape; do not force a two-pane layout merely because width is large |
| Regular | `480` and above | Normal scrollable application height; no additional height tier is currently needed |

The classes describe the app's **available window**, not the physical device. Do not add `isTablet`, model-name, or orientation-specific branches when the actual available width and height answer the question.

`useAdaptiveLayout()` reads `useWindowDimensions()`, so it updates during rotation, split-screen resizing, and fold/unfold changes. The hook also exposes `fontScale`; responsive structure must still reflow correctly when the user enlarges text.

## Phone orientation policy

**Decision status:** implemented in `src/providers/phone-orientation-policy.tsx`.

Sarflog keeps compact phone-sized windows upright without disabling useful tablet behavior:

- If either available dimension is below `600`, lock the app to portrait-up.
- If both available dimensions are at least `600`, release the app lock and follow the device's orientation setting.

The rule uses the smaller current window dimension, not a device name. A `360 x 800` phone and the same phone held sideways as `800 x 360` are both compact and stay portrait. An `800 x 1200` tablet may rotate because its smaller dimension is still at least `600`.

`app.json` intentionally uses `"orientation": "default"`. Setting it to `"portrait"` would statically lock tablets as well, so the runtime policy could never release them. Do not enable `ios.requireFullScreen` merely to force an iPad orientation lock; that disables iPad multitasking. Android 16 and newer may ignore app orientation restrictions on large screens, which matches this policy's intended tablet behavior.

Orientation is not a substitute for responsive layout. Tablet screens must be verified in both portrait and landscape, including split-screen or other resized windows where the platform supports them.

## Content width caps

Large windows do not mean every element should stretch edge to edge. Choose the cap that matches the screen's job:

| Role | Maximum width | Use |
| --- | ---: | --- |
| Form | `560` | Sign-in, expense entry, settings forms, focused confirmations |
| Standard | `800` | A single dashboard/list/detail column and the foundation gallery |
| Two pane | `1200` | Real master-detail or dashboard structures that intentionally use two panes |

These caps are not breakpoints. For example, an expense form remains capped at `560` even inside a very wide expanded window.

## Decision rules

1. Design the complete compact-width experience first; every task must remain possible below `600`.
2. Prefer Flexbox, wrapping, scrolling, and content caps; use a breakpoint only for a justified high-level structural change.
3. A breakpoint makes a richer structure eligible; it does not force every screen to add columns or panes.
4. Do not use two panes when height is compact. A wide-but-short landscape window should remain simple.
5. Let content wrap and scroll. Never shrink touch targets or readable text to make a layout fit.
6. Test both sides of every active boundary: `599/600`, `839/840`, and `479/480`.
7. Keep compact phones portrait; verify tablet layouts in portrait and landscape.

Primary references: [React Native `useWindowDimensions`](https://reactnative.dev/docs/usewindowdimensions), [Android window size classes](https://developer.android.com/develop/ui/views/layout/use-window-size-classes), and [Uniwind breakpoints](https://docs.uniwind.dev/breakpoints).
