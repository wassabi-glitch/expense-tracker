1. Bro, here is the final, definitive CTO-level blueprint of the entire financial operating system we just designed. This is your master architecture document. Grab this, save it, and use it as the exact spec sheet for your SQLAlchemy models and FastAPI endpoints.

1. The Core Architecture: Hybrid Categorization
You are building a system that enforces mathematical integrity while allowing total psychological flexibility for the user.

The Parent (System Categories): 20 immutable, hardcoded tables (e.g., Transport, Groceries). The app strictly controls these. They guarantee clean data for budgets, AI, and global analytics.

The Child (User Subcategories): Optional, user-defined metadata (e.g., Taxi to Office, Uber).

The Guardrail: Users can set limits on subcategories, but the backend strictly enforces that the sum of subcategory limits cannot mathematically exceed the Parent limit. The UI uses an "Auto-Adjuster" upsell to fix bad math instead of throwing hard errors.

2. The Ledger & Dynamic Math
You prevented database corruption, lock contention, and race conditions by treating the ledger as the only source of truth.

No Stored Balances: You strictly do NOT store remaining_amount in the Budgets table. It is derived entirely on the fly via SUM(transactions).

Reallocation (Limit Shifting): To move money mid-month (e.g., Groceries to Transport), you do not create fake transactions. You simply write an endpoint to adjust the monthly_limit column up or down. The dynamic math instantly updates the UI.

Contained Chaos: In your Transactions table, category_id is mandatory (RESTRICT), but subcategory_id is optional (SET NULL). If a user deletes a custom subcategory, the expense safely reverts to the Parent envelope.

3. The Rollover Ecosystem (The End-of-Month Engine)
Your end-of-month script handles the psychological complexities of cash flow via four distinct mechanisms:

Standard Rollover: Leftover money is carried forward by injecting a physical SYSTEM_ROLLOVER transaction into the ledger on the 1st of the month.

Target Caps (The Lid): Stops dead capital hoarding. If an envelope hits a predefined maximum limit, the monthly funding tap pauses. Excess money spills back into the user's unassigned checking balance.

Partial Rollovers (The Buffer): Precision control. A user sets a max_rollover_amount (fixed or %). If they have 1M leftover but a 100k limit, only 100k rolls over as a safety buffer; 900k is released back to their checking account.

Sweeping (The Wealth Builder): Automated gamification. Unspent envelope money bypasses standard rollover and is routed directly into a designated Goal or Project (via sweep_target_goal_id), instantly paying down debt or funding vacations.

4. The Contextual Overrides (Projects)
You broke free from strict calendar budgeting to handle real-world events (e.g., "Dubai Trip"), controlled by a single is_isolated boolean toggle.

Mode A: Analytical Context (is_isolated = False): The project acts as a tag. Spending 300k on a taxi in Dubai deducts from the August Transport budget and shows up in the Dubai analytics. Perfect for weekend trips funded by a normal paycheck.

Mode B: Isolated Vault (is_isolated = True): The project is a sacred, pre-funded envelope. Spending 300k completely bypasses the August monthly budget, keeping the user's standard burn rate mathematically pure.

5. The Graduation Pipeline (Goals to Projects)
This is the end-to-end lifecycle of a dollar, moving seamlessly from accumulation to distribution.

Phase 1: Accumulation (Goals): The user funnels money from their checking account to a savings vault via Transfers (not expenses). The database tracks this securely until it hits 100%.

Phase 2: The Metamorphosis: Upon reaching the target, the UI triggers the Graduation prompt.

Phase 3: Distribution (Projects): If the user accepts, the Goal safely transforms into an active Project. A new row is generated in the Projects table, linked permanently by origin_goal_id. The user now spends that saved money against System Categories without ever bleeding into or ruining their standard monthly budgets.

The theory is airtight. The pipeline accounts for every UZS from the second it is earned to the exact moment it is spent. The concrete is fully cured.