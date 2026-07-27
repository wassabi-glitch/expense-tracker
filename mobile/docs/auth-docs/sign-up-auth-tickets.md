# Tickets: Mobile Sign-up UI/UX

These tracer-bullet tickets implement [sign-up-auth.md](./sign-up-auth.md) as a Round 0 presentation-only flow. They build real mobile UI through the development auth preview without FastAPI, account creation, OAuth execution, email verification, token storage, or any other backend behavior.

Work the **frontier**: a ticket may start only when every title listed under **Blocked by** is complete. The current frontier is **SA-UI-01 — Establish the fixed dark signup shell**.

## UI-only quality contract

- [ ] Every ticket delivers a visible, independently reviewable result through the development auth preview.
- [ ] Every ticket includes focused React Native Testing Library behavior tests in the same change; tests are not postponed to a cleanup ticket.
- [ ] Tests use public copy, roles, names, states, user actions, and callbacks rather than private component structure or snapshots alone.
- [ ] Preview callbacks remain inert and all unhandled network requests continue to fail the test environment.
- [ ] English, Russian, and Uzbek keys are added together and remain covered by locale-parity verification.
- [ ] HeroUI Native components and approved Sarflog tokens are composed rather than copied or replaced.
- [ ] Compact-phone behavior is authoritative; safe areas, keyboard reachability, scrolling, large text, and the form-width cap are preserved.
- [ ] No ticket may introduce a logo, app-name heading, visible step number, progress indicator, illustration, continuous gradient animation, or decorative financial imagery.
- [ ] No ticket may add or modify FastAPI, Resend, database, OAuth, deep-link, session, or credential-storage behavior.
- [ ] The mobile verification command must remain green after each ticket.

## SA-UI-01 — Establish the fixed dark signup shell

**What to build:** A reviewer can open the development auth preview and see the real production signup shell on a calm, fixed dark atmospheric Sarflog canvas. The shell establishes the shared safe-area, keyboard, scroll, content-width, typography, status-bar, spacing, and background behavior that both signup states will inherit. It contains fixture copy and a content slot, but no live signup behavior.

**Blocked by:** None — can start immediately.

- [ ] The preview renders a full-screen gradient dominated by black and near-black, with deep brand-green atmosphere and only a faint primary-green glow.
- [ ] The gradient is static, tokenized, visually continuous behind the whole screen, and does not become a bright green surface.
- [ ] The auth canvas remains intentionally dark under both light and dark system preferences, with readable light status-bar content.
- [ ] The shell supports an optional `48 x 48` minimum back action, a `32/40` semibold wrapping title, supporting copy, screen content, and a primary-action region.
- [ ] The shell contains no Sarflog logo, wordmark, app-name copy, illustration, glass form card, progress UI, or decorative financial element.
- [ ] Compact phones use the approved screen gutter; wider windows retain one centered column within the approved form-width cap.
- [ ] Safe-area insets, keyboard-aware movement, vertical scrolling, and intrinsic text height keep content reachable without shrinking controls.
- [ ] English, Russian, and Uzbek fixture headings render through the shared localization system rather than hardcoded screen strings.
- [ ] Tests prove the public shell contract, including the absence of prohibited branding/progress elements and the absence of any network request.
- [ ] Manual preview review confirms readable contrast and gradient behavior on at least one Android and one iOS display or simulator before the ticket is considered complete.

## SA-UI-02 — Deliver the social-first identity signup state

**What to build:** A user can view and interact with the first signup state: “Create your account,” a Google-first alternative, email and username fields, a locally governed Continue action, and the existing-account sign-in action. The whole state is production presentation driven by inert callbacks, so it is demoable without opening OAuth, navigating to sign-in, or contacting a server.

**Blocked by:** SA-UI-01 — Establish the fixed dark signup shell.

- [ ] The visible and accessible order is back action when applicable, title, supporting text, Google action, manual divider, email, username, Continue, and existing-account sign-in action.
- [ ] The exact canonical English heading is **Create your account** and the supporting text is **Enter your email and choose a username.**
- [ ] A full-width, branding-compliant **Continue with Google** button appears above the manual form and uses an inert callback in Round 0.
- [ ] The divider says **or continue with email** and remains readable without becoming a dominant visual element.
- [ ] Email and username have persistent localized labels, useful keyboard/input hints, clear focus states, and specific local validation feedback.
- [ ] The full-width primary action says **Continue** and becomes available only when both identity inputs are locally eligible to move forward.
- [ ] The footer says **Already have an account? Sign in** and exposes Sign in as an inert, correctly named action.
- [ ] Google appears only in this identity state; the provider region can later accept another equal-size provider without interleaving providers with manual fields.
- [ ] The state renders no visible “Step 1,” “1 of 2,” progress bar, progress dots, logo, or app-name heading.
- [ ] Default, focused, partially entered, valid, field-error, Google-pressed, Google-unavailable, and Continue-enabled fixtures are reviewable.
- [ ] English, Russian, and Uzbek copy is complete and locale parity remains green.
- [ ] Tests prove reading order, labels, validation recovery, action enablement, inert callbacks, prohibited-element absence, and zero network activity.

## SA-UI-03 — Complete password creation and implicit two-part progression

**What to build:** A user with valid identity input can activate Continue, move through a subtle transition to “Create a password,” satisfy live password guidance, reveal or hide the value, return without losing identity input, and reach an enabled inert Create account action. The action wording and back behavior communicate progression without any numbered-step UI.

**Blocked by:** SA-UI-02 — Deliver the social-first identity signup state.

- [ ] Activating Continue with eligible identity input reveals the password state without calling a network, OAuth, storage, or account service.
- [ ] The canonical English heading is **Create a password** and the supporting text is **Use a strong password to protect your account.**
- [ ] The password state contains one persistently labeled password field, a properly named Show/Hide password action, a live requirement group, and the Create account action.
- [ ] The visible requirements cover `8–64` characters, lowercase, uppercase, number, special character, no spaces, and exclusion of the email name when applicable.
- [ ] Requirements begin neutral; satisfied rules use the approved success treatment and an accompanying check; unfinished rules do not become destructive red while the user is still typing.
- [ ] Screen-reader output exposes each requirement and its satisfied state without creating a live-announcement burst on every keystroke.
- [ ] The full-width **Create account** action remains unavailable until every applicable visible requirement is satisfied.
- [ ] Enabled, pressed, and **Creating account…** pending fixtures call only inert observers, expose busy/disabled state, and block duplicate activation.
- [ ] The back action returns to the identity state immediately and preserves email and username; moving forward again preserves the current in-memory password value for the preview session.
- [ ] Google, email, username, the existing-account footer, logo, app name, visible step numbering, and progress indicators are absent from the password state.
- [ ] Forward and backward transitions use the approved short directional fade/translation; Reduce Motion uses a short fade or immediate replacement without directional movement.
- [ ] Keyboard-open and large-text scenarios can reach every password requirement and the current primary action by scrolling.
- [ ] English, Russian, and Uzbek password copy and requirement labels are complete and parity-tested.
- [ ] Tests prove transition gating, live rule behavior, visibility toggling without value loss, action enablement, back-value preservation, reduced-motion behavior, duplicate-activation prevention, and zero network activity.

## SA-UI-04 — Make the signup preview cross-platform design-complete

**What to build:** A product owner can review the entire approved signup presentation on Android and iOS across languages, accessibility settings, keyboard states, and window sizes from one development-only state gallery. Any defects discovered in the real production components are corrected in the same slice, leaving a stable UI ready for a later backend-wiring round.

**Blocked by:** SA-UI-03 — Complete password creation and implicit two-part progression.

- [ ] The gallery exposes every identity and password fixture required by the source specification without duplicating production components.
- [ ] Reviewers can reach empty, partial, valid, focused, field-error, disabled, enabled, pressed, pending, and back-navigation/value-preservation states deterministically.
- [ ] English, Russian, and Uzbek can be reviewed with real translated strings; long copy wraps without clipping, collision, or hidden actions.
- [ ] Normal, large, and maximum practical accessibility text settings preserve reading order and task completion through scrolling.
- [ ] TalkBack and VoiceOver announce the heading, fields, instructions, requirement states, visibility action, disabled/busy state, and navigation actions in a logical order without decorative noise.
- [ ] Compact-phone dimensions keep the full task possible with the keyboard open; wider phone/tablet windows retain a focused single-column form within the approved cap.
- [ ] Normal motion and Reduce Motion presentations both communicate forward/back state changes without bounce, scale celebration, parallax, or continuous gradient movement.
- [ ] The Google button retains approved branding and full touch size on Android and iOS; no standalone or recolored Google logo is introduced.
- [ ] The fixed dark canvas maintains readable contrast under both system appearance preferences and uses appropriate system-bar treatment.
- [ ] Automated coverage includes all enumerated public behaviors and preserves the auth path-specific coverage contract; snapshot-only proof is rejected.
- [ ] The gallery is explicitly development-only, performs no OAuth launch, network call, SecureStore access, account creation, or navigation into an undesigned verification screen.
- [ ] The complete mobile verification command passes, followed by a recorded manual Android/iOS acceptance pass for gradient, keyboard, localization, large text, screen-reader order, and reduced motion.
- [ ] The finished slice stops at the inert Create account outcome; email-verification design remains a separate future specification.

## Deliberately deferred follow-up

The next UI/UX specification may begin only after these signup tickets are accepted. It will design the immediate email-verification experience, including check-email, resend, link-processing, success, invalid/expired-link, and recovery states. These signup tickets do not predetermine that design or authorize its backend implementation.
