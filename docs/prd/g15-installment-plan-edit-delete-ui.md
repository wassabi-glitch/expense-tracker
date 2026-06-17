# PRD: G15 - Installment Plan Edit and Delete UI

Labels: `ready-for-agent`

## Problem Statement

While the backend infrastructure and API client fully support editing and deleting installment plans (and appropriately enforce G1 pristine guardrails), the frontend UI completely lacks the controls to trigger these actions. Users currently cannot edit safe metadata, correct setup fields, or delete a mistakenly created payment plan because the necessary React hooks, context menus, and modals are missing from the `InstallmentsTab` components.

## Solution

Wire up the existing backend capabilities to the frontend by adding "Edit" and "Delete" actions to the installment plan UI. The UI must respect the G1 guardrails: pristine plans can be deleted and their financial setup edited, while non-pristine plans (plans with payments or charges) should only allow safe metadata edits (like renaming). Delete actions for non-pristine plans should be explicitly disabled with a tooltip explaining that real activity prevents deletion.

## User Stories

1. As a payment-plan user, I want an "Edit" button on my installment plans, so that I can correct mistakes made during creation.
2. As a payment-plan user, I want to edit safe metadata (like the item name or store) at any time, so that I can fix typos without touching financial history.
3. As a payment-plan user, I want to edit financial setup fields (like price, frequency, or months) only when the plan is pristine, so that I don't accidentally corrupt an active payment schedule.
4. As a payment-plan user, I want the UI to clearly disable setup field edits after I record a payment, so that I understand why the fields are locked.
5. As a payment-plan user, I want a "Delete" option in the plan's context menu or details modal, so that I can remove a test or erroneous plan.
6. As a payment-plan user, I want to see a confirmation dialog before deleting a plan, so that I do not delete it by accident.
7. As a payment-plan user, I want the "Delete" button to be disabled and explain why if the plan is no longer pristine, so that I know I must archive or undo payments instead.
8. As a developer, I want the UI to use standard React Query mutation hooks (`useUpdateInstallmentPlanMutation`, `useDeleteInstallmentPlanMutation`), so that the caching and loading states are handled cleanly.
9. As a developer, I want the existing `deleteInstallmentPlan` and `updateInstallmentPlan` API client functions wired correctly, so that we don't duplicate network logic.
10. As a tester, I want the UI to visually distinguish pristine from non-pristine states for the edit/delete buttons, so that I can verify the G1 guardrails from the browser.

## Implementation Decisions

- **Hooks:** Implement `useDeleteInstallmentPlanMutation` and `useUpdateInstallmentPlanMutation` inside a new or existing hooks file (e.g., `useInstallmentsMutations.js`). Ensure they invalidate the appropriate installment plan lists/details on success.
- **UI Placement:** Add "Edit" and "Delete" options to the context menu of the installment plan card (e.g., three-dot menu) or as buttons within the plan details modal.
- **Delete Guarding:** Expose a `Delete` button that checks if the plan is pristine. Since pristine status implies no `payments` with `paid_amount > 0` or charges, the UI can disable the delete button if the plan's `paid_amount > 0` or `status != ACTIVE`, rendering a tooltip: "Cannot delete: Plan has recorded activity."
- **Edit Modal:** Create an `EditInstallmentPlanModal` (or adapt a creation modal). The modal must lock or hide financial setup fields (total price, down payment, months, frequency) if the plan is not pristine, but allow editing the `item_name` and `store_or_bank_name`.
- **Localization:** Add new keys for the edit/delete modals and tooltips in the `i18n` locale files (`en.json`, etc.).
- **Consistency:** Follow the pattern used in the `DebtsTab` for editing and deleting regular debts (which checks `isDeleteDisabled` and shows `deleteDisabledReason`).

## Testing Decisions

- **Focus:** Test the UI components and custom hooks, as the backend is already thoroughly tested for G1 guardrails.
- **Seams:** Mock the `apiClient` endpoints to verify that `useDeleteInstallmentPlanMutation` and `useUpdateInstallmentPlanMutation` correctly call the backend and trigger cache invalidations.
- **Visual/State Testing:** If component tests are added, mock a pristine plan and verify the delete/edit setup buttons are enabled. Mock a non-pristine plan and verify they are disabled or locked.

## Out of Scope

- Modifying the backend endpoints `PATCH /installments/{plan_id}` or `DELETE /installments/{plan_id}`.
- Changing backend G1 pristine logic.
- Adding "Archive" functionality for payment plans (this belongs in a separate feature).
- Rescheduling or restructuring non-pristine plans.

## Further Notes

This PRD addresses a missing frontend implementation layer for guardrails that were fully baked into the backend during G1. Completing this will align the user experience with the established domain rules.
