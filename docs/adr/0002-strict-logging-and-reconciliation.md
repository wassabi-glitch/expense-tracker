# Strict Expense Logging & Wallet Reconciliation

Sarflog is a truth-first budgeting system. To protect the integrity of the live budget and prevent infinite historical drift, the app strictly separates "live tracking" from "fixing the past."

**Decision:** 
We are adopting a strict, multi-tiered logging and reconciliation model:

1. **Normal Add Expense/Income:** 
   - Restricted to **Today only**. Same-day order does not matter for final math.
   - Fast, frictionless, assumes high user memory accuracy.

2. **Reconciliation Flow:**
   - Used for any past/missed records. 
   - High-friction: forces the user to confront the discrepancy between the app's wallet balance and reality.
   - Can result in specific past-dated records (if known), approximate category records, or an "Unknown/Untracked" adjustment if the user doesn't know where the money went. The app never fabricates categories.

3. **Month Closing & The 5-Day Grace Window:**
   - A month does not instantly lock on the 1st of the next month. It enters a 5-day "Closing Window."
   - **Open:** Current month. Reconciliation can create past-dated records freely.
   - **Closing Window:** Days 1-5 of the new month. Users can still use Reconciliation to insert exact-dated records into the previous month to clean it up.
   - **Closed:** Day 6 onward (or if manually closed early). The month is completely sealed.
   - **Closed-Period Corrections:** If a user remembers a missed July expense on August 10th (July is closed), they CANNOT backdate it to July. They must log it as a "Current Correction" dated August 10th, which hits August's budget but includes a note referencing July.

4. **Pre-Epoch Block:** 
   - No transaction can ever be dated before the wallet's `created_at` date (established in ADR 0001).

**Why:** 
This prevents users from treating the app like a casual notebook. Infinite backdating normalizes procrastination, which causes the live budget (`free_money_now`) to lie to the user, leading to overspending. This model gives humans a reasonable 5-day grace period to do month-end cleanups, but enforces strict discipline outside that window to guarantee stable historical reports.
