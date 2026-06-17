# Multiplayer & Households Vision (V2)

## Every Real Household Financial Scenario

### Couple Type 1: Fully Merged Finances
- "Everything is ours, nothing is mine/yours"
- One joint account
- All expenses shared
- All budgets shared
- All goals shared
- Complete financial transparency

### Couple Type 2: Partially Merged (Most Common)
- "We have joint expenses but personal spending too"
- **Joint:** Rent, utilities, groceries, shared vacation goal, household budget
- **Personal:** My clothes (private), his hobbies (private), her personal savings (private), personal spending money

### Couple Type 3: Independent But Transparent
- "We track separately but want to see combined picture"
- Each has own finances
- But can see combined: Total household spending, Are we saving enough together?, Contribution balance

### Roommates
- "We share costs but finances are separate"
- **Shared:** Rent split, Utility split, Shared supplies
- **Personal:** Everything else
- **Need:** Split tracking, Settlement ("you owe me X"), Shared expense log

### Family (Parents + Children)
- "Parents manage household, kids have allowances"
- **Parents:** Full access to everything, Set budgets for kids, See all spending
- **Kids:** Own pocket money wallet, Limited budget, Parents can see their spending

---

## The Core Insight
Every household type needs:
1. **VISIBILITY CONTROL** (What can each member see?)
2. **CONTRIBUTION TRACKING** (Who paid what?)
3. **SPLIT LOGIC** (How is shared cost divided?)
4. **SETTLEMENT** (Who owes who?)
5. **COMBINED ANALYTICS** (What does household look like together?)
6. **ROLE SYSTEM** (Who can do what?)

---

## The Full Architecture

### Layer 1: The Household Entity
```sql
CREATE TABLE households (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,        -- "Akbar & Kamola's Home"
  currency TEXT DEFAULT 'UZS',
  created_by INT NOT NULL,
  created_at TIMESTAMP,
  
  -- Settings
  default_split_method TEXT, -- 'equal', 'percentage', 'custom'
  settlement_reminder_day INT, -- day of month to remind
  visibility_mode TEXT        -- 'full', 'shared_only', 'contributions_only'
);
```

### Layer 2: Membership & Roles
```sql
CREATE TABLE household_members (
  id SERIAL PRIMARY KEY,
  household_id INT NOT NULL,
  user_id INT,               -- null if invited but not joined yet
  
  -- Identity
  display_name TEXT,         -- "Kamola" or "Mom"
  invite_email TEXT,
  invite_phone TEXT,
  
  -- Role
  role TEXT NOT NULL,        -- 'owner', 'admin', 'member', 'viewer', 'child'
  
  -- Split configuration
  split_percentage DECIMAL,  -- their default share %
  
  -- Status
  status TEXT DEFAULT 'invited', -- 'invited', 'active', 'left', 'removed'
  joined_at TIMESTAMP,
  left_at TIMESTAMP,
  
  FOREIGN KEY (household_id) REFERENCES households(id),
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Layer 3: Role Permissions
- **OWNER:** ✅ See everything ✅ Create/edit shared resources ✅ Invite/remove members ✅ Manage splits
- **ADMIN:** ✅ See everything shared ✅ Create/edit shared resources ✅ Invite members ❌ Remove members
- **MEMBER:** ✅ See shared resources ✅ Add expenses to shared wallets ✅ See own contribution ❌ See others' private finances
- **VIEWER:** ✅ See shared resources (read only) ❌ Add anything
- **CHILD:** ✅ See their own wallet/budget ✅ Add expenses from their wallet ❌ See parents' finances

### Layer 4: Resource Ownership
- **PERSONAL (private):** `wallet.ownership = 'personal'` (Only owner sees it)
- **SHARED (household):** `wallet.ownership = 'shared'` (All members see it)
- **CONTRIBUTED (personal but visible):** `wallet.ownership = 'contributed'` (Owner's wallet, but used for a household payment)

### Layer 5: Split System
```sql
CREATE TABLE expense_splits (
  id SERIAL PRIMARY KEY,
  financial_event_id INT NOT NULL,
  household_id INT NOT NULL,
  split_method TEXT NOT NULL, -- 'equal' | 'percentage' | 'exact' | 'shares' | 'payer_only'
  paid_by_member_id INT NOT NULL,
  total_amount DECIMAL NOT NULL,
  created_at TIMESTAMP
);

CREATE TABLE expense_split_lines (
  id SERIAL PRIMARY KEY,
  split_id INT NOT NULL,
  member_id INT NOT NULL,
  owed_amount DECIMAL NOT NULL,
  percentage DECIMAL,
  shares INT,
  is_settled BOOLEAN DEFAULT false,
  settled_at TIMESTAMP,
  settlement_event_id INT  -- links to actual payment
);
```

### Layer 6: Settlement System
```sql
CREATE TABLE settlements (
  id SERIAL PRIMARY KEY,
  household_id INT NOT NULL,
  from_member_id INT NOT NULL,  -- who pays
  to_member_id INT NOT NULL,    -- who receives
  amount DECIMAL NOT NULL,
  currency TEXT DEFAULT 'UZS',
  settlement_type TEXT,
  payment_method TEXT,
  status TEXT DEFAULT 'pending',
  confirmed_by_receiver BOOLEAN DEFAULT false,
  confirmed_at TIMESTAMP,
  created_at TIMESTAMP,
  financial_event_id INT
);
```

### Layer 7: Household Analytics
- Shows Total Household Spending.
- Shows By Member Contribution (e.g., Akbar 54%, Kamola 46%).
- Shows combined Category spending, Shared Goals, and Settlement Balances.

### Layer 8: Household Budgets
- **Household budget:** Covers shared expenses. Both members' spending counts against it.
- **Personal budget:** Private. Only the individual's spending counts.

### Layer 9: Household Goals
1. **Pooled Goal:** Both contribute, used together (e.g., Vacation Fund).
2. **Target Goal:** Doesn't matter who contributes, just need to reach total (e.g., New Sofa).
3. **Split Goal:** Each tracks own progress, combined view shows total (e.g., Emergency Fund).

---

## The Privacy Model
1. **Full Transparency:** All expenses, wallets, and goals visible.
2. **Shared + Totals:** Partner sees shared expenses and total spending, but not individual transactions.
3. **Shared Only:** Personal is completely private. Only explicitly shared items are visible.
4. **Contributions Only:** Partner only sees how much you contribute, not what you spend on.

---

## The ROI & Viral Growth
- **Market Expansion:** Shifts TAM from individuals to couples, families, and roommates.
- **Revenue:** Couples convert at higher rates because a shared problem creates shared motivation.
- **Forced Viral Growth:** To use the feature, User A *must* invite User B. This mirrors Splitwise and WhatsApp's organic growth engines.

## Verdict & Timeline
- Do NOT build before V1.
- Launch the 1-player mode first, get 100 users, and ensure the core ledger is bug-free.
- Release this 1-2 months after launch as "Sarflog 2.0: Now with Households" for a massive marketing moment.
