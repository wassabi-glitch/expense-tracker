# PRD: G22 - Guided Quest Log Onboarding

Labels: `ready-for-agent`

## Problem Statement

New users signing up for Sarflog face a massive abstraction cliff if presented with a generic wizard or form to setup their budget. Because Sarflog relies on a strict sequence of constraints (Wallets -> Goals -> Inflows -> Budgets), asking them to budget first results in immediate "Over-Planned" errors. Furthermore, abstracting the UI behind a wizard prevents the user from building muscle memory (the "YNAB Problem"), leaving them completely lost when the wizard ends and they are dropped into the main dashboard.

## Solution

Implement an interactive "Quest Log" widget that guides the user to interact with the *actual* UI elements of the application. This builds spatial memory and ensures the user understands how to use the app in their daily life. The onboarding must enforce the fundamental constraints of the ledger by guiding the user through a strict sequence:

1. **Reality Check**: Add a Wallet with a real balance to establish "Free Money Now".
2. **Protections**: Create and fund a Goal or declare a Debt to lock up protected money.
3. **Horizon**: Add an Expected Inflow or Recurring Expense to generate G6 category floors or G16 backing.
4. **Macro Plan**: Complete the Month Setup Draft. Because the user has no history, this must automatically default to "Option 1: Plan from scratch" (EC-155).

## User Stories

1. As a new user, I want to learn the physical location of buttons and menus, so that I build muscle memory for daily app usage.
2. As a new user, I want to be guided to enter my wallet balances first, so that my budgets are backed by actual financial reality.
3. As a new user, I want to establish my protections (goals/debts) before planning my month, so that I don't accidentally budget money I need for emergencies.
4. As a new user, I want to enter my expected inflows before planning my month, so that the system doesn't falsely warn me about being over-planned if I live paycheck to paycheck.
5. As a new user, I want my first monthly plan to start from scratch, so that I am not confused by "Copy Previous" features that depend on history I do not have.
6. As a new user, I want a floating "Quest Log" checklist instead of a locked, dimmed screen, so that I can explore the app freely without feeling trapped by a tutorial.
7. As a returning new user, I want my onboarding progress to be derived from my real data, so that if I close the app and come back tomorrow, the Quest Log knows exactly where I left off.

## Implementation Decisions

- **Widget Design**: A floating React component (Quest Log) that resides in the corner of the screen and provides a checklist.
- **UI Highlighting**: The active quest will trigger gentle visual pulses or tooltips on the real navigation sidebar items and primary Action Buttons (e.g., `+ Add Wallet`), guiding the user to the correct location.
- **Backend-Agnostic State**: Do not create a `has_completed_onboarding` flag or a `UserOnboardingState` table in the backend database. The Quest Log state will be derived entirely by polling/fetching existing ledger data.
- **EC-155 Integration**: The G6 Month Setup Screen must be updated to conditionally hide/disable "Option 2: Copy Previous" and "Option 3: Smart Auto-Fill" if the backend confirms the user has zero prior budget history.

## Testing Decisions

- **Seam**: The primary testing seam is the frontend UI state reacting to existing backend data payloads.
- **E2E Validation**: Use frontend integration tests (e.g., Cypress or Playwright) to mock empty (`[]`) and populated (`[{id: 1, ...}]`) JSON responses for `/wallets`, `/goals`, `/expected-inflows`, and `/budgets`. Verify that the Quest Log correctly checks off completed tasks and advances the active quest based solely on these mock responses.
- **No new backend tests** are required, as no new APIs or database schemas are being introduced for this flow.

## Out of Scope

- Gamification, points, or badges for completing the tutorial.
- Forced "straightjacket" tutorials that lock the screen and prevent the user from navigating elsewhere.
- Backend tracking of onboarding analytics.
- Subcategory configuration (This is an advanced feature reserved for mid-month refinement, not initial onboarding).

## Further Notes

This PRD formalizes the onboarding architecture mapped out during the EC-154 and EC-155 edge case discovery. It ensures new users initialize the Sarflog double-entry ledger in the mathematically correct sequence.
