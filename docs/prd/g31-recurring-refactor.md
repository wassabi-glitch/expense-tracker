# G31: Refactoring Recurring Expenses (Pure CONFIRM Architecture)

## 1. Goal
To drastically simplify the recurring expense architecture by eliminating the complex, assumption-heavy `AUTO_RECORD` mode. The system will shift entirely to a **Pure CONFIRM Architecture** where user intent drives the ledger. 

This completely removes invisible background retries, eliminates the confusing "Pay Now" function, moves "Skip" directly to the occurrence level (Inbox), and implements a mathematically flawless `MAX()` boundary rule for "Flexible" schedules to seamlessly handle chaotic, out-of-order historical bookkeeping.

---

## 2. Core Architectural Rules

### 2.1 The "Sun" (Template) is Decoupled
*   Templates never gridlock. Every night at midnight, the scheduler checks if a Template is due. If so, it drops an Occurrence (a bill) into the `NEEDS_CONFIRMATION` inbox and immediately advances the Template's `next_due_date` forward by one strict cycle.
*   The Template does not care if 15 occurrences are piling up in the inbox.

### 2.2 The `MAX()` Math Rule for Flexible Cycles
When the user resolves an Occurrence (either by clicking Confirm or Skip), the system performs the following math:
1.  **Calculate Proposed Orbit:** `Actual Date of Action + Frequency = Proposed Next Due Date`.
2.  **The Shield:** `New Template Next Due Date = MAX(Current Template Next Due Date, Proposed Next Due Date)`.

This guarantees that logging late reality pushes the Template forward, but logging old historical receipts (or typos) is safely ignored.

### 2.3 Strict Boundaries
*   **Future Dates:** Completely banned. The UI and Backend will strictly enforce that no occurrence can be confirmed or skipped using a date in the future.
*   **Past Dates:** Unlimited freedom. Users can confirm occurrences with any past date, protected by the `MAX()` mathematical shield.

---

## 3. Implementation Steps

### Phase 1: Database & Schema Purge
1. **`app/models.py`**
   - Run Alembic migration to drop columns: `recording_mode`, `failing_due_date`, `retry_count`, `last_retry_at`.
   - Remove `AUTO_POST_FAILED` from `RecurringOccurrenceStatus`.
2. **`app/schemas.py`**
   - Remove `recording_mode` from all validation schemas.

### Phase 2: Backend Engine Simplification
1. **`app/scheduler.py`**
   - Rip out all `record_automatic_due_occurrence` retry logic.
   - Scheduler strictly generates `PENDING_CONFIRMATION` occurrences and advances templates on a fixed cycle.
2. **`app/services/recurring_occurrence_service.py`**
   - Delete `record_automatic_due_occurrence`.
   - Delete `skip_next_occurrence` (Template-level skip).
   - Implement `skip_occurrence(occurrence_id, actual_date)` to mark an occurrence as skipped.
   - Update `confirm_recurring_occurrence` and `skip_occurrence` to calculate the `MAX()` orbit math for Flexible cycles at the exact moment of resolution.
3. **`app/routers/recurring.py`**
   - Delete `/{id}/skip` and `/{id}/pay-now`.
   - Add new endpoint: `POST /occurrences/{id}/skip`.

### Phase 3: UI/UX Cleanup
1. **`frontend/src/features/expenses/expenseSchemas.js`**
   - Delete `recording_mode`.
2. **`frontend/src/features/expenses/RecurringExpenses.jsx`**
   - Remove the `recording_mode` dropdowns from the Add/Edit modals.
   - Remove "Skip Next occurrence" and "Pay Now" from the 3-dot action menu.
3. **`frontend/src/features/expenses/components/NeedsConfirmationSection.jsx`**
   - Add a "Skip" (or Dismiss) button directly beside "Confirm" on each occurrence card.
   - Enforce `max={todayISO}` on the date picker.
   - Wire up the new Skip button to the `POST /occurrences/{id}/skip` API.

### Phase 4: Testing & Verification
1.  **`tests/test_recurring_expenses.py`**
    - Delete all auto-record and retry-limit tests.
    - Write robust tests proving the `MAX()` orbit logic for Flexible cycles correctly handles late logging and historical out-of-order logging.
