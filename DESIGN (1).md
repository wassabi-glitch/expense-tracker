# Design System Specification: High-End Editorial Expense Tracking

## 1. Overview & Creative North Star
**Creative North Star: "The Financial Luminary"**
This design system moves away from the "generic dashboard" aesthetic and toward a high-end editorial experience. It treats financial data not as a boring spreadsheet, but as a curated gallery of personal impact. 

By leveraging a high-contrast palette of deep charcoal backgrounds and neon accents, the system creates a sense of focused urgency and premium precision. We break the "template" look by utilizing **intentional asymmetry** (e.g., staggering card layouts), **overlapping elements** (floating action buttons over glass containers), and a **sophisticated typographic scale** that prioritizes readability and authoritative hierarchy.

---

## 2. Colors: Tonal Depth & Luminous Accents
Our color strategy relies on "The Luminous Dark"—using deep blacks to make our primary neon green feel like it’s emitting light.

*   **Primary (#49fc77):** The "Pulse" of the app. Used for high-priority actions like 'Add Expense'.
*   **Surface Hierarchy:** We utilize a nesting strategy to create depth without relying on antiquated design patterns.
    *   **Background (#0e0e0e):** The base canvas.
    *   **Surface-Container-Low (#131313):** Used for large sections or page-level grouping.
    *   **Surface-Container (#1a1919):** The standard for cards and content blocks.
    *   **Surface-Container-High (#201f1f):** Reserved for hover states or active selection cards.

**The "No-Line" Rule:** 
Explicitly prohibit 1px solid borders for sectioning. Boundaries must be defined solely through background color shifts or subtle tonal transitions. A card should sit on the background because it is `surface-container`, not because it has a stroke.

**The Glass & Gradient Rule:**
Floating elements (like bottom sheets or specialized tooltips) should use **Glassmorphism**: `surface-variant` with a 60% opacity and a `20px` backdrop-blur. Main CTAs should utilize a subtle linear gradient from `primary` (#49fc77) to `primary_container` (#16de5e) at a 135-degree angle to add "visual soul."

---

## 3. Typography: Editorial Authority
We pair the geometric precision of **Manrope** for large-scale data with the functional clarity of **Inter** for utility.

*   **Display (Manrope):** Large spending amounts use `display-lg` (3.5rem). The wide letterforms of Manrope make high numbers feel significant and "expensive."
*   **Headlines (Manrope):** Used for page titles and section headers. `headline-sm` (1.5rem) provides clear navigation.
*   **Body & Titles (Inter):** All transactional data—titles of expenses, dates, and categories—use Inter. This ensures high legibility at small sizes. `body-md` (0.875rem) is our workhorse for list items.
*   **Labels (Inter):** Used for metadata. `label-sm` (0.6875rem) in `on_surface_variant` (#adaaaa) provides the necessary "quiet" information.

---

## 4. Elevation & Depth: Tonal Layering
Depth in this system is a result of light physics, not structural boxes.

*   **The Layering Principle:** Stacking determines hierarchy. Place a `surface-container-lowest` (#000000) input field inside a `surface-container` (#1a1919) card to create a "recessed" look. 
*   **Ambient Shadows:** For floating modals, use an extra-diffused shadow: `offset: 0 20px, blur: 40px, color: rgba(0, 0, 0, 0.4)`. 
*   **The Ghost Border Fallback:** If a boundary is strictly required for accessibility, use the `outline_variant` (#484847) at **15% opacity**. Never use 100% opaque borders.
*   **Dimensionality:** Use the **xl (1.5rem)** roundedness for large containers to soften the "Brutalist" dark theme, making it feel more approachable and modern.

---

## 5. Components: Precision Built

### Buttons
*   **Primary:** Background: `primary` gradient; Text: `on_primary` (#005b21); Radius: `full`.
*   **Secondary:** Background: `secondary_container` (#474747); Text: `on_secondary_container` (#d2d0cf); Radius: `full`.

### Expense Cards & Lists
*   **Forbidden:** Horizontal divider lines between expenses.
*   **Alternative:** Use `spacing-4` (0.9rem) of vertical white space or a subtle background shift to `surface_container_low` on alternating items.
*   **Category Pills:** High-saturation backgrounds with low-saturation text (e.g., Orange for Dining, Purple for Subscriptions). Radius must be `md` (0.75rem).

### Input Fields
*   **Base:** `surface_container_lowest` (#000000). 
*   **Active State:** No thick border; instead, use a 1px `ghost-border` (outline at 20%) and a subtle glow using the `surface_tint` (#49fc77) at 5% opacity.

### Navigation Sidebar
*   Use `surface_dim` (#0e0e0e) for the bar itself, but highlight the active state using a vertical "pill" of `primary` color that is only 4px wide, placed against the left edge.

---

## 6. Do's and Don'ts

### Do:
*   **Do** use `spacing-16` (3.5rem) to separate major sections. Negative space is a luxury in financial apps.
*   **Do** use `manrope` for any currency symbol or amount to elevate the "Editorial" feel.
*   **Do** use "Micro-Interactions." An expense card should subtly scale to 1.02x on hover to acknowledge the user.

### Don't:
*   **Don't** use pure white (#ffffff) for body text. Use `on_surface_variant` (#adaaaa) to reduce eye strain against the black background. Reserve pure white for Headlines.
*   **Don't** use standard Material Design drop shadows. They look "dated." Stick to tonal shifts and blur.
*   **Don't** crowd the interface. If a screen feels full, increase the `surface-container` padding using the `spacing-8` (1.75rem) token.