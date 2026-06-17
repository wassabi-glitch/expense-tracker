# Multicurrency in the Real World — A Deep Dive for Sarflog

## Part 1: How Money Actually Works Across Currencies

### The Fundamental Truth: One Wallet = One Currency

In the real world, money **always lives in a specific currency**. When you open your physical wallet, you might have a pocket for UZS bills and a separate pocket for USD bills. They don't mix. A bank account is denominated in a specific currency — your Humo card holds UZS, a Wise account might hold USD.

This is the first law of multicurrency:

> **Every container of money (wallet, account, pocket) holds exactly one currency. Always.**

You already have this in your Wallet model: `currency = Column(String(3), default="UZS")`. Good — that's the right foundation.

---

### The Second Truth: Transactions Happen in One Currency, Impact May Be Another

When you buy groceries at Korzinka, the price tag says 85,000 UZS. You pay from your UZS Humo card. Simple — one currency throughout.

But what happens when things get interesting?

**Scenario 1: Cross-border online purchase**
You buy a course on Udemy for $19.99. Your bank card is UZS. What actually happens:
1. Udemy charges $19.99 (the **original amount** in the **original currency**)
2. Your bank converts at *their* rate — say 12,750 UZS per USD
3. Your UZS account is debited 254,872 UZS (the **settled amount** in the **wallet's currency**)
4. The bank may also charge a conversion fee of, say, 1-2%

The key insight: **two amounts exist simultaneously for this one transaction**:
- The original: $19.99 USD
- The settled: 254,872 UZS

Both are true. Neither is "wrong." They represent different truths.

**Scenario 2: You hold USD cash**
You have a physical wallet with $500. You want to track it in Sarflog. This is a wallet denominated in USD. Its balance is 500 (in USD, not UZS). When you spend $20 from this wallet on dinner, the wallet goes to $480. No conversion happened — dollar in, dollar out.

**Scenario 3: Currency exchange at a bureau**
You walk into a currency exchange with 1,000,000 UZS and walk out with ~$78 USD. What happened financially?
- Your UZS wallet lost 1,000,000 UZS
- Your USD wallet gained $78
- The rate was 12,820 UZS/USD
- This is **not** an expense. It's not income. It's a **currency exchange** — money changed form but your wealth didn't change (ignoring the spread/fee)

This is one of the trickiest events for a personal finance app to handle correctly.

---

### The Third Truth: Exchange Rates Are Snapshots in Time

Exchange rates change every second. The rate you got on Monday is different from Tuesday. This creates a critical design question:

> **When you look at your "total balance" across all wallets, what rate do you use?**

There are two completely different use cases:

| Use Case | Which Rate? | Why |
|---|---|---|
| **Recording a transaction** | The rate *at the moment of the transaction* | This is historical fact — it can never change |
| **Displaying a dashboard total** | Today's rate (or a recent rate) | You want to see your *current* purchasing power |

A real-world example:
- January: You exchanged 5,000,000 UZS → $400 at rate 12,500
- June: The rate is now 12,800
- Your $400 is now "worth" 5,120,000 UZS in today's terms

The January transaction is still a fact: you paid 5,000,000 UZS and received $400. That never changes.
But your dashboard showing "Total Wealth" should use today's 12,800 rate to show what your $400 is worth *right now*.

---

## Part 2: The Core Concepts You Need

### 2.1 — Base / Reporting Currency

Every user needs a **base currency** (also called "reporting currency" or "home currency"). This is the currency they think in and want reports denominated in.

For you: probably UZS. For a user in the US: USD. For someone in Europe: EUR.

This does NOT mean all wallets must be in this currency. It means:
- When you see "Total Balance: 15,200,000" on your dashboard — that number is in your base currency
- When budget reports say "You spent 2,300,000 on Groceries" — that's in base currency
- When a goal says "Target: 5,000,000" — that's in base currency (unless the goal itself is currency-specific)

> **The base currency is the language your financial reports speak in.**

### 2.2 — Original Amount vs. Converted Amount

For every financial event that crosses currencies, you need to store **both**:

| Field | What It Means | Example |
|---|---|---|
| `original_amount` | What was actually paid/received in the wallet's currency | $19.99 |
| `original_currency` | The currency of the original amount | USD |
| `base_amount` | The same value converted to user's base currency | 254,872 UZS |
| `exchange_rate` | The rate used for conversion | 12,750 |

For transactions where wallet currency = base currency, all these are the same and the exchange rate is 1.0. Simple.

### 2.3 — Exchange Rate Source

Where does the rate come from? In a real-world personal finance app (especially manual wallets like yours), there are several options:

1. **User enters the rate manually** — "I know my bank charged me 12,750 per dollar"
2. **User enters both amounts** — "I paid $19.99 and was charged 254,872 UZS" → the app calculates the rate
3. **App provides a market rate** — you fetch a rate from an API and the user can accept or adjust it
4. **The rate is implied** — for a same-currency transaction, the rate is always 1.0

For your MVP (manual wallets), option 1 and 2 are the most honest. Option 3 is a convenience feature for later.

### 2.4 — The Golden Rule of Financial Record-Keeping

> **Never change historical amounts. Never retroactively update exchange rates on past transactions.**

If you bought something for $20 at rate 12,750 on January 15th, that record is permanent. Even if the rate is now 13,000, the January 15th transaction stays at 12,750.

This is how banks work. This is how accounting works. This is what makes your users trust that the numbers are real.

---

## Part 3: Real-World Multicurrency Scenarios

Let me walk you through every common scenario your users will encounter, and what each one means financially:

### 3.1 — Same-Currency Expense (The Simple Case)
**Example:** Buy groceries for 85,000 UZS from UZS Humo card

- Wallet currency: UZS
- User's base currency: UZS
- Amount: 85,000
- No conversion needed. Rate = 1.0
- This is how your app works today — nothing changes.

### 3.2 — Cross-Currency Expense (Foreign Purchase from Local Wallet)
**Example:** Buy a Udemy course for $19.99, paid from UZS Humo card

What the user experiences:
- They see $19.99 on the Udemy receipt
- Their bank statement shows 254,872 UZS was debited

What needs to be recorded:
- The wallet (UZS Humo) is debited **254,872 UZS** (the wallet always moves in its own currency)
- The transaction's "original amount" is $19.99 USD (what the merchant charged)
- The exchange rate used was 12,750
- The base currency amount is 254,872 UZS (same as wallet amount, since wallet is in base currency)

### 3.3 — Foreign-Currency Expense from Foreign-Currency Wallet
**Example:** You have $500 in a USD cash wallet. You spend $20 on dinner while traveling.

- Wallet currency: USD
- Wallet is debited $20
- Original amount: $20 USD
- No conversion in the wallet
- But for **reporting**, this $20 needs to be converted to UZS using a rate

Here's the subtlety: the wallet moves in USD, but your budget (which is in UZS) needs to understand this as a UZS amount for budget tracking.

### 3.4 — Currency Exchange (The Tricky One)
**Example:** Walk into a bureau and exchange 1,000,000 UZS for $78 USD

This is NOT an expense or income. Your total wealth didn't change (ideally). It's a **transfer** between two wallets of different currencies.

What needs to be recorded:
- UZS Cash wallet: -1,000,000
- USD Cash wallet: +78
- Exchange rate: 12,820 UZS per USD
- Transaction type: TRANSFER (or a new type: CURRENCY_EXCHANGE)
- This does NOT hit any budget or category — it's just money changing form

The tricky part: on your dashboard, if you convert that $78 back at today's rate (say 12,800), you get 998,400 UZS — a "loss" of 1,600 UZS. This is **exchange rate loss**. It's real, but it's unrealized (you haven't actually lost money — you still have $78).

### 3.5 — Income in Foreign Currency
**Example:** You do freelance work and receive $500 via Wise

- USD wallet: +500
- This is income of $500 USD
- For reporting: $500 × 12,750 (today's rate) = 6,375,000 UZS
- Your income reports should show this in base currency

### 3.6 — Debt in Foreign Currency
**Example:** You borrow $1,000 from a friend

- The debt is denominated in USD: $1,000
- Your USD wallet (or cash) gains $1,000
- The debt obligation is $1,000 USD
- When you repay, you must repay in USD (or the agreed equivalent)
- The UZS "value" of this debt fluctuates with the exchange rate — but the debt itself is always $1,000

This is why your Debt model already has a `currency` field — the debt lives in a specific currency.

### 3.7 — Goal in Foreign Currency
**Example:** You want to save $2,000 for a laptop

- Goal target: $2,000 USD
- Contributions come from a USD wallet
- Progress is measured in USD: saved $800 out of $2,000
- Dashboard shows: "Laptop Goal: $800 / $2,000 (40%)" + the UZS equivalent at today's rate

---

## Part 4: The Accounting Spine — What to Store

Here's the principle that makes everything work:

```
┌─────────────────────────────────────────────────────┐
│                 THE TWO-LAYER TRUTH                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Layer 1: WALLET TRUTH (always in wallet currency)  │
│  ─────────────────────────────────────────────────  │
│  "My Humo card was debited 254,872 UZS"            │
│  "My USD cash gained $78"                           │
│  This is the bank-statement-level truth.            │
│  It uses the wallet's own currency. Always.         │
│                                                     │
│  Layer 2: REPORTING TRUTH (in base currency)        │
│  ─────────────────────────────────────────────────  │
│  "This expense was worth 254,872 UZS in my books"  │
│  "My income today was 6,375,000 UZS equivalent"    │
│  This uses the base currency for comparisons,      │
│  budgets, reports, and aggregations.                │
│                                                     │
│  THE BRIDGE: exchange_rate_used                     │
│  Stored at transaction time. Never changes.         │
│  Lets you always reconstruct either layer.          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### What Fields Do You Need on Each Record?

For your **WalletLedger** (the wallet truth layer):
- `amount` — already exists, this stays in wallet currency (it already is — the wallet owns the currency)
- No changes needed here! The wallet ledger already speaks the wallet's language.

For your **FinancialEvent** or **EntityLedger** (the reporting layer):
- `amount` — the base-currency amount (what goes into budgets/reports)
- `original_amount` — the amount in the original transaction currency (if different from base)
- `original_currency` — the currency code of the original amount
- `exchange_rate_used` — the rate that was applied

For **Wallets**:
- `currency` — already exists ✓
- Each wallet always does math in its own currency

For **User/UserProfile**:
- `base_currency` — the user's chosen reporting/home currency (e.g., "UZS")

---

## Part 5: Important Design Decisions to Think About

These are questions you'll need to answer before implementation. There are no "wrong" answers — it depends on what kind of experience you want Sarflog to deliver.

### Question 1: Can budgets be in foreign currencies?
- **Simple approach:** Budgets are always in base currency. A $20 expense is converted to UZS and counted against your UZS budget. This is how most apps work.
- **Advanced approach:** Each budget can optionally be in a specific currency. Rare but powerful for expats.
- **Recommendation:** Start with base-currency-only budgets. It's simpler and covers 95% of use cases.

### Question 2: Can goals be in foreign currencies?
- You already support this (`Goals.currency` exists). A "Save $2,000" goal makes sense — you contribute in USD and track in USD.
- Key question: can you contribute to a USD goal from a UZS wallet? If yes, a conversion happens at contribution time.

### Question 3: How do you handle wallet transfers between different currencies?
Your current `WalletTransfer` has a single `amount` field. For cross-currency transfers:
- You need `from_amount` (in source wallet currency) and `to_amount` (in destination wallet currency)
- Plus `exchange_rate_used`
- Example: Transfer 1,000,000 UZS → $78 USD needs to store both amounts

### Question 4: What about unrealized exchange gains/losses?
- You have $500 saved. Dollar goes up. Your UZS-equivalent wealth increased. Show this? Ignore it?
- **Recommendation:** Show it on the dashboard as informational ("Your USD holdings are worth X UZS at today's rate") but never record it as income/expense. It's unrealized.

### Question 5: Where do exchange rates come from?
- **Phase 1 (manual):** User types the rate when doing cross-currency operations. Honest and accurate.
- **Phase 2 (assisted):** App suggests a rate from an API, user can accept or adjust.
- **Phase 3 (automatic):** App auto-fetches rates for dashboard display.

### Question 6: What about the UZS specifics?
- UZS has very large numbers (a lunch might be 50,000-100,000 UZS)
- You already use `BigInteger` — good
- Display formatting will differ: $19.99 vs 254,872 UZS (decimals vs whole numbers)
- Most currencies use 2 decimal places, UZS uses 0. This is a formatting concern, not a storage concern if you store in minor units (cents/tiyin).

---

## Part 6: What Changes in Your Existing System

Here's a high-level mapping of what multicurrency touches in your current architecture:

| Component | Current State | What Changes |
|---|---|---|
| **Wallet** | Has `currency` field (defaults to UZS) | ✅ Already correct foundation |
| **User/Profile** | No base currency concept | Needs `base_currency` field |
| **FinancialEvent** | Amounts are unitless (assumed UZS) | Needs original_amount, original_currency, exchange_rate |
| **WalletLedger** | `amount` in wallet's currency | ✅ Already correct — no change needed |
| **EntityLedger** | `amount` assumed UZS | Amounts should be in base currency; may need original fields |
| **WalletTransfer** | Single `amount` | Needs from_amount, to_amount, rate for cross-currency |
| **Budget** | Limits in assumed-UZS | Limits stay in base currency. Expenses converted before comparison |
| **Goals** | Has `currency` field | ✅ Already correct. Contribution logic needs currency awareness |
| **Debt** | Has `currency` field | ✅ Already correct. Payment logic needs currency awareness |
| **InstallmentPlan** | Has `currency` field | ✅ Already correct. Same as debt |
| **Income** | No currency awareness | Needs currency handling for foreign-currency income |
| **Dashboard/Reports** | Assumes single currency | Must aggregate using base currency, converting foreign wallets |

---

## Part 7: A Mental Model — "Think Like a Bureau de Change"

Imagine every cross-currency operation as involving an invisible currency exchange bureau sitting between your wallets:

```
┌──────────────┐                              ┌──────────────┐
│  UZS Wallet  │ ──── 254,872 UZS ──────────→ │              │
│  (Humo)      │                               │   EXCHANGE   │
│              │                               │    BUREAU    │
│  Balance:    │                               │              │
│  -254,872    │                               │  Rate: 12750 │
└──────────────┘                               │              │
                                               │  Fee: 0      │
                                               └──────┬───────┘
                                                      │
                                                 $19.99 USD
                                                      │
                                                      ▼
                                               ┌──────────────┐
                                               │   Merchant   │
                                               │   (Udemy)    │
                                               └──────────────┘
```

For a currency exchange:
```
┌──────────────┐                              ┌──────────────┐
│  UZS Wallet  │ ── 1,000,000 UZS ──────────→ │              │
│  (Cash)      │                               │   EXCHANGE   │
│              │                               │    BUREAU    │
│  Balance:    │                               │              │
│  -1,000,000  │                               │  Rate: 12820 │
└──────────────┘                               │              │
                                               │  Spread: ~1% │
                                               └──────┬───────┘
                                                      │
                                                   $78 USD
                                                      │
                                                      ▼
                                               ┌──────────────┐
                                               │  USD Wallet  │
                                               │  (Cash)      │
                                               │              │
                                               │  Balance:    │
                                               │  +$78        │
                                               └──────────────┘
```

The bureau metaphor helps you think about any cross-currency operation:
- **What goes in?** (Amount and currency)
- **What comes out?** (Amount and currency)
- **What was the rate?**
- **Was there a fee/spread?**

---

## Discussion Points for You

Before we design anything, I'd love to hear your thoughts on:

1. **Who is your primary user?** Someone living in Uzbekistan who occasionally deals with USD/EUR? Or someone who regularly juggles multiple currencies (e.g., an expat or freelancer)?

2. **How do your users currently handle multicurrency in real life?** Do they do mental math at the current rate? Do they track USD separately?

3. **What's your gut feeling on budgets — should a user budget in UZS only, or should they be able to set a budget in USD?**

4. **Currency exchange — is this something your users do frequently?** (e.g., buying/selling dollars at the bazaar or banks)

5. **Do any of your current users have debts or installments in foreign currencies?**

6. **For the MVP — are you comfortable with manual exchange rates (user types the rate), or do you want auto-fetch from day one?**

Let's discuss these before we draw up any implementation plans!
