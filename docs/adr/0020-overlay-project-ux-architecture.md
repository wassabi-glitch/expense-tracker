# 20. Overlay Project UX Architecture: Two-Layer Disclosure & Just-In-Time Onboarding

Date: 2026-07-03

## Status

Accepted

## Context

Financial software can rapidly become overwhelming due to the sheer volume of data, especially when advanced tracking features (like Overlay Projects) are introduced. 

In our earlier iterations, the Budgets screen was becoming cluttered. Overlay project cards were acting as "mini details pages," displaying too much historical information, and we were attempting to stuff complex editing flows (like the `ProjectStructureDialog`) directly into inline modals on the main Budgets page. 

Furthermore, we recognized a significant onboarding risk: asking brand-new users to set up Overlay Projects before they have even established their core global categories or wallets creates cognitive overload and guarantees churn.

## Decision

We adopt a strict **Two-Layer UX Architecture** and a **Just-In-Time (JIT) Onboarding Philosophy** for all Project-related features.

### 1. Just-In-Time (JIT) Onboarding
- **Hide from Onboarding:** Overlay Projects are an advanced architectural concept. They must be completely hidden during the new-user onboarding flow.
- **Core Loop First:** Onboarding must strictly focus on the core loop: Creating a Wallet, creating 2-3 global categories (e.g., Food, Rent), and logging a first expense.
- **Discovery:** Overlay Projects are only introduced via a "Create Project" button on the Budgets screen *after* a user has established their baseline budgets, allowing them to carve out slices when they naturally decide to plan a specific event (e.g., an "Anniversary Party").

### 2. Layer 1: The Budgets Screen (Minimal & Actionable)
- **Primary Goal:** The Budgets screen must only answer one question: *"What needs my attention this month?"*
- **Minimal Cards:** Overlay project cards on the Budgets screen act solely as status summaries. They display current-month progress and quick-glance health, stripping out dense historical data or heavy configuration UI.

### 3. Layer 2: The Dedicated Project Details Page (`/projects/:id`)
- **Deep Dive Isolation:** When a user needs to edit, analyze, or view the entire lifecycle of a project, they click the minimal card to navigate to a dedicated Details page.
- **Heavy Logic Relocation:** All complex configurations—such as editing target dates, re-allocating category slices, viewing the full cross-month expense ledger, triggering the Auto-Sweep (Issue 9), or executing a Pristine Deletion / Resolution (Issue 8)—are exclusively housed on this dedicated page. 

## Consequences

- **Frictionless Onboarding:** New users experience a dramatically simplified "time to value," preventing cognitive overload.
- **Cleaner Dashboards:** The Budgets screen remains performant and visually clean, focused strictly on monthly operational execution.
- **Scalable Architecture:** By moving complex operations (like the `ProjectStructureDialog`) to a dedicated URL route, we decouple the heavy data fetching and state management from the Budgets screen, allowing the Details page to scale independently as we add more advanced analytical charts or ledger tables in the future.
