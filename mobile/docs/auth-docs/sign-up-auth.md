# Specification: Mobile Sign-up UI/UX

**Status:** Approved for Round 0 UI implementation  
**Audience:** Product owner, designers, maintainers, and coding agents  
**Scope:** Presentational mobile sign-up experience only; no backend, OAuth, account creation, or email-verification implementation

## Problem Statement

Sarflog needs a mobile sign-up experience that feels deliberate, premium, and native without becoming decorative or noisy. A conventional single-page form would place social authentication, email, username, password, password guidance, validation feedback, and account switching in one vertically crowded phone screen. That would make the password guidance difficult to understand when the keyboard is open and would weaken the simple visual hierarchy established by the Revolut-inspired direction.

The current design direction also needs to be concrete enough that implementation agents do not introduce a logo above the form, visible step counters, progress bars, generic illustrations, unrelated animations, random green shades, different layouts for each part, or premature backend behavior.

## Solution

Create one cohesive mobile sign-up flow with two internal presentation states:

1. An identity state for Google, email, and username.
2. A password state for one password field and a live requirement checklist.

The flow does not display “Step 1,” “Step 2,” “1 of 2,” progress dots, or a progress bar. Progress is communicated implicitly: the first primary action is **Continue**, and the second is **Create account**. The second state has a back action that returns to the identity state without losing entered values.

Both states use the same fixed dark Sarflog auth canvas: a restrained atmospheric gradient built from black, near-black neutrals, deep brand-green shades, and a faint primary-green glow. Large left-aligned copy, generous spacing, large rounded controls, and subtle state transitions provide the premium character. The screen contains no Sarflog logo, app name, illustration, mascot, decorative financial imagery, or continuous animation.

Round 0 renders the real production presentation through inert preview fixtures and callbacks. It does not call FastAPI, start Google OAuth, create an account, store credentials, send email, or design the email-verification screen.

## User Stories

1. As a new user, I want the sign-up screen to feel calm and trustworthy, so that I am comfortable beginning a financial account journey.
2. As a new user, I want one obvious task at a time, so that the form does not feel crowded.
3. As a new user, I want to begin with Google when I prefer the shortest path, so that I can avoid unnecessary typing later when that integration becomes functional.
4. As a new user, I want Google presented before the manual form, so that the fastest option is easy to discover.
5. As a new user, I want a clear divider between Google and manual registration, so that I understand they are alternative paths.
6. As a new user, I want to enter my email and username together, so that related identity information is collected in one place.
7. As a new user, I want the first action labeled “Continue,” so that I understand more information follows without seeing a mechanical step counter.
8. As a new user, I want password creation on a focused second view, so that the keyboard and guidance do not compete with unrelated fields.
9. As a new user, I want password requirements to update while I type, so that I can correct my password before submission.
10. As a new user, I want satisfied password requirements to be visibly distinct from unmet requirements, so that progress is easy to scan.
11. As a new user, I want unmet requirements to remain neutral while I am typing, so that the interface guides me without treating unfinished input as failure.
12. As a new user, I want to reveal or hide my password, so that I can correct typing mistakes safely.
13. As a new user, I want the final action labeled “Create account,” so that I understand this is the end of the sign-up form.
14. As a new user, I want the create-account action unavailable until the visible password requirements are met, so that submission readiness is predictable.
15. As a new user, I want to return to the identity view without losing my email or username, so that correcting earlier input is inexpensive.
16. As an existing user, I want an obvious sign-in link on the identity view, so that I do not complete the wrong journey.
17. As a user on a compact phone, I want fields, requirements, and actions to remain reachable with the keyboard open, so that I can finish without layout obstruction.
18. As a tablet user, I want the focused form to stay comfortably narrow, so that controls do not stretch across the entire screen.
19. As an English, Russian, or Uzbek user, I want all copy localized from the first implementation, so that no language becomes a later retrofit.
20. As a user with large text enabled, I want headings, labels, requirements, and actions to wrap and scroll without clipping, so that the flow remains usable.
21. As a screen-reader user, I want fields, instructions, password-rule states, and actions announced in a logical order, so that I can complete sign-up without sight.
22. As a user who reduces motion, I want the same state changes without unnecessary translation or scaling, so that the flow remains comfortable.
23. As a user on a slow device, I want motion to remain short and smooth, so that polish never becomes delay.
24. As a product reviewer, I want all important states available in the auth preview, so that I can approve the design without real accounts or services.
25. As a maintainer, I want both presentation states to share one visual shell and form controller, so that values, behavior, and styling do not drift.
26. As a future OAuth implementer, I want the social-provider area to accept an inert callback now and real behavior later, so that backend wiring does not require a redesign.
27. As a testing agent, I want the flow verified through public labels, actions, visible states, and accessibility output, so that tests survive internal refactoring.
28. As a release owner, I want the preview implementation to make no network or credential-storage calls, so that design work cannot mutate development accounts.

## Implementation Decisions

### 1. Scope boundary

This specification defines only the mobile presentation and local interaction contract. The implementation uses inert callbacks and fixture state in the development auth preview.

The following actions are represented visually but do not perform production work in this slice:

- Continue with Google.
- Continue from identity to password, except for local UI validation and internal state transition.
- Create account.
- Navigate to sign in.

No request or response schema, FastAPI endpoint, OAuth callback, token, session, Resend behavior, email deep link, or account state is introduced here.

### 2. One route-level screen with two internal states

The sign-up experience remains one route-level screen and one logical form. It has two internal states named by meaning rather than number:

```text
identity -> password
identity <- password
```

The identity state owns email and username input. The password state owns password input and the live requirement presentation. Moving backward preserves all values. Returning forward restores the password value for the current in-memory preview session.

The UI must not render:

- “Step 1” or “Step 2.”
- “1 of 2” or “2 of 2.”
- A progress bar, progress dots, segmented progress, or numbered headings.
- Copy promising that only two total account-creation stages exist, because email verification follows in a later product slice.

### 3. Identity-state content and order

The accessible and visual reading order is:

1. Optional back control when navigation has somewhere meaningful to return.
2. Title: **Create your account**.
3. Supporting text: **Enter your email and choose a username.**
4. Full-width **Continue with Google** button.
5. Divider labeled **or continue with email**.
6. Persistently labeled email field.
7. Persistently labeled username field.
8. Full-width **Continue** button.
9. **Already have an account? Sign in** footer action.

Google appears above the manual fields because it is the shortest sign-up path and is intentionally given first discovery. It appears only in the identity state. The button uses an approved full Google treatment rather than a standalone logo, monochrome imitation, or custom brand-green Google button.

The current design displays Google as the only social provider. The provider region must be able to become a vertical equal-prominence provider stack later without restructuring the form. Adding or implementing Apple authentication is not authorized by this specification.

### 4. Password-state content and order

The accessible and visual reading order is:

1. Back control returning to the identity state.
2. Title: **Create a password**.
3. Supporting text: **Use a strong password to protect your account.**
4. Persistently labeled password field.
5. Password visibility action labeled according to its result: **Show password** or **Hide password**.
6. Live password-requirement group.
7. Full-width **Create account** button.

The password state does not repeat Google, email, username, the sign-in footer, a logo, or the app name. Its only job is password creation.

### 5. Password requirement presentation

The visible UI contract mirrors the useful behavior of the existing web signup while making every enforced rule visible:

- 8–64 characters.
- Includes a lowercase letter.
- Includes an uppercase letter.
- Includes a number.
- Includes a special character.
- Contains no spaces.
- Does not contain the email name before `@` when that comparison is applicable.

Before typing, every requirement is neutral. While typing, satisfied requirements use the approved success color and a check icon; unmet requirements remain neutral. Unmet requirements do not become destructive red merely because the user has not finished typing. A destructive treatment is reserved for an attempted invalid action or a specific field error.

Icons reinforce the text but never carry the only meaning. Screen-reader output communicates each requirement and whether it is satisfied without repeatedly announcing every keystroke. The group may expose a concise progress summary after a short settled change rather than producing seven simultaneous live-region announcements.

### 6. Action behavior

The identity **Continue** action is disabled until the locally entered email and username are syntactically eligible for the next presentation state. Activating it moves to the password state; it does not create an account or call a service.

The **Create account** action is disabled until every visible password requirement is satisfied. In preview scenarios, activating it calls an inert observer so reviewers and tests can confirm the interaction. Separate preview fixtures show enabled, pressed, and pending visual states without performing work.

Busy actions block duplicate activation and expose both busy and disabled state accessibly. The pending label is **Creating account…**. This is presentation copy only in Round 0.

### 7. Visual direction

The signup flow uses the approved **Sarflog Dark Minimal** direction:

- A full-screen dark atmospheric gradient.
- Black and near-black as the dominant canvas.
- Deep forest-green shades providing atmosphere.
- Primary green appearing as a restrained low-opacity glow and as meaningful action/status color.
- White primary text and muted light supporting text.
- Dark neutral fields with clear boundaries and focus treatment.
- Large rounded controls with a calm, tactile appearance.
- Generous negative space and left-aligned hierarchy.

The gradient is static in the initial implementation. It is composed from shared semantic design decisions, not screen-local arbitrary colors. It must settle toward near-black rather than becoming a bright green background, and it must preserve readable contrast behind every possible text position.

The auth canvas remains deliberately dark even when the rest of the application follows a light system preference. Status-bar content and navigation controls use a light-content treatment appropriate to the fixed dark canvas.

### 8. Prohibited visual elements

The signup screen contains none of the following:

- Sarflog logo or wordmark.
- App name in the title or supporting text.
- Illustration, mascot, piggy bank, wallet, coin, banknote, chart, or decorative finance icon.
- Glass cards around the whole form.
- Bright multicolor aurora treatment.
- Continuous gradient animation, particles, parallax, confetti, bounce, or celebratory effects.
- Decorative copy, marketing carousel, feature list, testimonial, or operational-status panel.
- Per-state backgrounds that make the two parts feel like different products.

### 9. Typography

The screen uses the existing Inter family and approved regular and semibold weights. The auth title uses a reusable display role at `32/40` semibold without amount-specific numeric behavior. Body, supporting, and button copy reuse the established type scale.

Titles are allowed to wrap naturally. No fixed title height is permitted. English, Russian, and Uzbek must fit without reducing font size per locale.

### 10. Spacing, sizing, and adaptive layout

The compact-phone layout is authoritative:

- Screen gutters use the shared compact metric.
- Controls use at least the approved standard minimum height; primary and provider actions may use the approved large control height.
- Touch targets remain at least `48 x 48` density-independent layout units.
- Spacing follows the existing four-point base and eight-point primary rhythm.
- Related label/input/error content stays closer than separate content groups.

The screen uses safe-area insets, keyboard-aware movement, vertical scrolling, and intrinsic content height. The keyboard must not cover the active field, password requirements, or current primary action. Content may scroll; text and controls may not be compressed to avoid scrolling.

On wider windows the form remains a focused single column and respects the approved form-width cap. This flow does not introduce phone breakpoints, two-pane signup, or device-model branches.

### 11. Motion and feedback

Motion exists only to explain state and confirm interaction:

- Entering content may fade in once.
- Identity-to-password transition uses a short directional fade/translation no larger than `8–12` layout units and the approved standard duration.
- Returning reverses the directional cue.
- Field focus, validation color, and password-rule icon changes use approved fast feedback durations.
- Buttons use HeroUI Native press feedback and block repeated activation while busy.
- The static gradient does not drift or pulse.

When Reduce Motion is active, state changes use a short fade or immediate replacement without directional translation or scale. Motion never delays field focus or action availability.

### 12. HeroUI Native and styling ownership

HeroUI Native provides supported text-field and button anatomy, interaction feedback, disabled/busy states, and component-level visual polish. Sarflog supplies the fixed auth gradient, semantic colors, copy, layout, password meaning, localization, and accessibility acceptance criteria.

Uniwind utilities may compose layout and apply approved theme variables. Implementers must prefer HeroUI variants and composition APIs before adding one-off overrides. No auth-specific replacement for the global base button or text field is introduced.

### 13. Localization

All visible and accessible copy is supplied through the shared English, Russian, and Uzbek localization system from the first implementation. Complete sentences are translated as complete messages; the interface does not concatenate fragments.

The canonical English decisions are:

| Element | Copy |
| --- | --- |
| Identity title | Create your account |
| Identity supporting text | Enter your email and choose a username. |
| Google action | Continue with Google |
| Manual divider | or continue with email |
| Identity primary action | Continue |
| Existing-account prompt | Already have an account? |
| Existing-account action | Sign in |
| Password title | Create a password |
| Password supporting text | Use a strong password to protect your account. |
| Password primary action | Create account |
| Password pending action | Creating account… |

Translations may use natural grammar rather than word-for-word structure, but they must preserve the same meaning and restrained tone.

### 14. Accessibility

- Every field has a persistent localized label; placeholder text is never the only label.
- The title exposes heading semantics.
- Back, Google, password visibility, Continue, Create account, and Sign in expose accurate roles, names, and states.
- The password visibility control has a full touch target and announces the action it will perform.
- Validation identifies the affected field and explains how to recover.
- Disabled and busy actions expose their state and prevent duplicate activation.
- Visual reading order and accessibility reading order match.
- Color, icons, and motion supplement text rather than replace it.
- Large text can wrap and scroll without clipping, overlap, or unreachable actions.
- Focus moves predictably when the internal state changes and returns to the password heading or first relevant control rather than an invisible element.

### 15. Preview contract

The development auth preview renders the exact production signup presentation with inert fixtures. At minimum it exposes:

- Identity: empty, partially entered, valid, focused, field error, and Continue-enabled states.
- Identity: Google default, pressed, and unavailable/disabled visual states.
- Password: untouched, partially satisfied, fully satisfied, visible-password, field-error, and Create-account-enabled states.
- Password: create-account pending and duplicate-activation-blocked state.
- Navigation: forward transition, backward transition, and value preservation.
- Environment: English, Russian, Uzbek, large text, compact phone, wider form cap, normal motion, and reduced motion.

The preview performs no network request, opens no OAuth browser, writes no SecureStore value, and creates no account.

## Testing Decisions

1. Tests assert public behavior through visible copy, accessibility roles/names/states, user input, and callbacks rather than private state variable names or component structure.
2. The highest test seam is the rendered signup screen with inert callbacks and localization/theme providers.
3. A screen behavior test proves the identity state initially shows Google, email, username, Continue, and the sign-in action in the approved reading order.
4. A negative assertion proves no visible step number, progress indicator, Sarflog logo, or app name appears in either state.
5. A behavior test proves valid identity input activates Continue and reveals the password state without making a network request.
6. A behavior test proves returning from password to identity preserves entered email and username.
7. Password tests prove each visible rule changes from unmet to met from user input and that the final action becomes available only when all rules are satisfied.
8. A behavior test proves password visibility changes without clearing the value and exposes the correct accessible action name.
9. A pending-state test proves repeated Create account activation is blocked and busy/disabled state is exposed.
10. Localization parity tests include every new English, Russian, and Uzbek key in the same change.
11. Selected screen tests render long translated copy and verify important controls remain present and reachable; visual/manual review covers real text scaling and keyboard behavior that unit layout mocks cannot prove.
12. Reduced-motion behavior is tested at the public transition seam; implementation-specific animation values are not snapshot-tested.
13. Unhandled network requests continue to fail the mobile test environment, proving the Round 0 signup preview remains inert.
14. Snapshot-only tests are insufficient. Focused behavior assertions and on-device visual review are both required.
15. Manual acceptance covers Android and iOS, compact phone dimensions, tablet-width form capping, keyboard open/closed, light system preference with the fixed dark auth canvas, TalkBack/VoiceOver order, and all three languages.

## Out of Scope

- FastAPI routes, services, schemas, database behavior, or tests.
- Real account creation or server-side uniqueness checks.
- Google OAuth configuration, browser session, callback, account linking, or error handling.
- Apple authentication design or implementation.
- Email verification, check-email, resend, deep-link, expired-link, or verification-success design.
- Sign-in, forgot-password, reset-password, session-expired, or authenticated-app screens.
- SecureStore, access tokens, refresh tokens, cookies, or session restoration.
- Resend, SMTP, Mailtrap, email templates, or deliverability.
- A welcome/onboarding carousel or separate branded landing page.
- New mobile breakpoints, landscape-phone layouts, or two-pane auth.
- Animated gradient research or decorative auth artwork.

## Further Notes

- Email verification is the immediate product stage after account creation, but its UI/UX will receive a separate design specification after signup is approved.
- The first action and second action intentionally communicate progression without claiming how many total authentication stages remain.
- The mobile flow preserves the useful conceptual split of the web signup but does not copy its desktop card, logo, split-panel composition, or styling.
- Exact gradient calibration should be reviewed on real Android and iOS displays because desktop browser screenshots do not predict native OLED/LCD appearance reliably.
- If future product work adds another social provider, its button must join the provider region with equivalent sizing and compliant branding; it must not be inserted between manual fields.
