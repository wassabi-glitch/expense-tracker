# Sarflog — Product Roadmap & Strategy

```
                                        ███████╗
                                        ╚══════╝
                                     LAUNCH 🚀
                                          │
     ┌────────────────────────────────────┼────────────────────────────────────┐
     │                            Landing Pages                               │
     │                         Legal / ToS / Privacy                          │
     │                    App Store Listings (iOS + Android)                  │
     └────────────────────────────────────┼────────────────────────────────────┘
                                          │
     ┌────────────────────────────────────┼────────────────────────────────────┐
     │                      Uzbek Payment Integration                         │
     │                     Payme / Click / Uzcard / Humo                      │
     │                       Premium Subscription Flow                        │
     └────────────────────────────────────┼────────────────────────────────────┘
                                          │
     ┌────────────────────────────────────┼────────────────────────────────────┐
     │                           Premium Gating                               │
     │               Analyse feature gates · Free vs Premium tiers            │
     │               Keep core money-tracking open · Gate advanced            │
     └────────────────────────────────────┼────────────────────────────────────┘
                                          │
     ┌────────────────────────────────────┼────────────────────────────────────┐
     │                        Web Frontend Polish                             │
     │            True responsive design · Mobile-first layouts               │
     │              Design system audit · Accessibility pass                  │
     └────────────────────────────────────┼────────────────────────────────────┘
                                          │
     ┌────────────────────────────────────┼────────────────────────────────────┐
     │                          AI Input Layer                                │
     │    ┌──────────┐  ┌──────────────┐  ┌──────────────────────────────┐    │
     │    │ Receipt   │  │ Natural Text │  │   Voice Input                │    │
     │    │ Scanning  │  │  "Coffee     │  │   "Sarflog, add              │    │
     │    │ OCR →     │  │   15k today" │  │   expense 50k for            │    │
     │    │ expense   │  │   → expense  │  │   groceries today"           │    │
     │    └──────────┘  └──────────────┘  └──────────────────────────────┘    │
     │                        Telegram Bot UX layer                           │
     └────────────────────────────────────┼────────────────────────────────────┘
                                          │
     ┌────────────────────────────────────┼────────────────────────────────────┐
     │                         Assets Rebuild                                 │
     │              Full CRUD · Multi-currency support · Mobile + Web         │
     │              Purchase · Depreciate · Sell · Gift · Dispose             │
     └────────────────────────────────────┼────────────────────────────────────┘
                                          │
     ┌────────────────────────────────────┼────────────────────────────────────┐
     │                        Multi-Currency                                  │
     │         Schema: currency columns on wallets, expenses, goals, debts    │
     │         Exchange rate engine · Display formatting · Conversion         │
     └────────────────────────────────────┼────────────────────────────────────┘
                                          │
     ┌──────────┐  ┌──────────┐  ┌───────┴──────┐  ┌──────────┐  ┌──────────┐
     │ Settings │  │Analytics │  │  DASHBOARD   │  │  Goals   │  │  Debts   │
     │ Profile  │  │ Trends   │  │  (LAST!)     │  │Savings   │  │Payment   │
     │ App Lock │  │ Reports  │  │  Quick-add   │  │ Projects │  │ Plans    │
     │ Export   │  │          │  │  Carousel    │  │          │  │          │
     └──────────┘  └──────────┘  └──────┬───────┘  └──────────┘  └──────────┘
                                        │
     ┌──────────┐  ┌──────────┐  ┌──────┴───────┐  ┌──────────────────────────┐
     │ Wallets  │  │Money In  │  │   Budgets    │  │      Expenses            │
     │ CRUD     │  │Income    │  │   Monthly    │  │  CRUD · Filters · Split  │
     │ Transfer │  │Sources   │  │   Timeline   │  │  Templates (Quick-Add)   │
     │ Reconcil │  │Expected  │  │   Expected   │  │  Expected Outflows       │
     │          │  │ Inflows  │  │   Outflows   │  │                          │
     └──────────┘  └──────────┘  └──────────────┘  └──────────────────────────┘
                                          │
     ┌────────────────────────────────────┼────────────────────────────────────┐
     │                     Mobile Tab Navigation Skeleton                      │
     │    Dashboard · Expenses · Wallets · Budgets · Settings                 │
     │    Real icons · Real labels · Placeholder screens · 3 languages        │
     └────────────────────────────────────┼────────────────────────────────────┘
                                          │
                              ┌───────────┴───────────┐
                              │   BACKEND (80% done)  │
                              │   APIs · Auth · CI    │
                              │   900 tests · 84% cov │
                              └───────────────────────┘
```

---

## Core Strategies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DASHBOARD LAST                                       │
│                                                                             │
│   Build the engine first, then the gauges. Every module below feeds data    │
│   into the dashboard. Building it first means rebuilding it 4 times.        │
│   Building it last means you know exactly what to display and how.          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        POLISH ALONGSIDE, NOT AT THE END                     │
│                                                                             │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐                           │
│   │ Mobile   │ ──→ │  Polish  │ ──→ │  Next    │    NOT:                   │
│   │ Screen   │     │  Web     │     │  Module  │    Build 18 mobiles       │
│   └──────────┘     └──────────┘     └──────────┘    then 18 web fixes      │
│                                                                             │
│   When you finish a mobile screen, you're still in the mental model of      │
│   that data. Applying polish to web takes 1 hour now vs 1 day later.        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        CONTINUOUS STAGING DEPLOYS                           │
│                                                                             │
│   Every module → staging.sarflog.uz → use for a week → fix bugs → next     │
│                                                                             │
│   By launch day, staging has been running for months. Launch is boring.     │
│   Deploying 15 modules simultaneously on launch day = spectacular failure.  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        SHARED SPACE: MIGRATION NOW, UI LATER                │
│                                                                             │
│   ALTER TABLE wallets     ADD COLUMN group_id;  -- nullable                 │
│   ALTER TABLE budgets     ADD COLUMN group_id;  -- null = personal          │
│   ALTER TABLE expenses    ADD COLUMN group_id;  -- zero cost today          │
│   ALTER TABLE goals       ADD COLUMN group_id;  -- infinite flexibility     │
│                                                                             │
│   When you're ready to build sharing UI, the schema is already there.       │
│   No migration of production data. Cheapest insurance you'll ever buy.      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        USER IDENTITY: KEEP, DON'T GROW                       │
│                                                                             │
│   Onboarding choices set smart defaults (income sources), never restrict.   │
│   Student can add "Business income." Owner can add "Scholarship."           │
│   Defaults remove friction. Gates create resentment.                        │
│   All choices are editable and overridable. Always.                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA EXPORT & PORTABILITY                            │
│                                                                             │
│   Every module with user data → exportable.  PDF for statements.            │
│   CSV for portability.  Users own their data, can leave anytime.            │
│   It's a trust signal, not a feature.                                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        NOTIFICATIONS: REBUILD FROM ZERO                     │
│                                                                             │
│   Only push what users explicitly asked for:                                │
│   · Budget at 80%       · Goal milestone hit                                │
│   · Recurring due soon  · Shared partner added expense                     │
│                                                                             │
│   Never: "Check out this feature!" or "We haven't seen you!"                │
│   Every notification: clear trigger, direct link to relevant screen.        │
│   Mobile push notifications + in-app notification center.                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Target Timeline: ~4 Months

```
Month 1                    Month 2                    Month 3                    Month 4
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│ ██ Skeleton          │ │ ██ Budgets           │ │ ██ Goals & Savings   │ │ ██ AI Inputs         │
│ ██ Wallets           │ │ ██ Expenses          │ │ ██ Dashboard         │ │ ██ Web Polish        │
│ ██ Money In          │ │ ██ Debts & Plans     │ │ ██ Analytics         │ │ ██ Premium Gating    │
│                      │ │                      │ │ ██ Settings          │ │ ██ Uzbek Payments    │
│                      │ │                      │ │ ██ Multi-Currency    │ │ ██ Landing Pages     │
│                      │ │                      │ │ ██ Assets Rebuild    │ │ ██ Launch 🚀         │
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘ └──────────────────────┘
```

---

## Module Dependency Graph

```
                         ┌─────────────────────┐
                         │    TAB SKELETON      │
                         │  (navigation frame)  │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
     ┌────────┴────────┐   ┌───────┴────────┐   ┌───────┴────────┐
     │    WALLETS       │   │   MONEY IN     │   │   SETTINGS     │
     │  (self-contained) │   │ (needs wallets) │   │ (independent)  │
     └────────┬────────┘   └───────┬────────┘   └────────────────┘
              │                     │
              └──────────┬──────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
     ┌────────┴────────┐   ┌───────┴────────┐
     │    BUDGETS       │   │   EXPENSES     │
     │ (needs wallets,  │   │ (needs wallets, │
     │  categories)     │   │  budgets, cats) │
     └────────┬────────┘   └───────┬────────┘
              │                     │
              └──────────┬──────────┘
                         │
     ┌───────────────────┼───────────────────┐
     │                   │                   │
┌────┴──────┐   ┌────────┴────────┐   ┌──────┴──────┐
│  DEBTS &  │   │  GOALS &        │   │  ANALYTICS  │
│  PAYMENT  │   │  SAVINGS        │   │  (reads all │
│  PLANS    │   │  + PROJECTS     │   │   modules)  │
└─────┬─────┘   └────────┬────────┘   └──────┬──────┘
      │                  │                   │
      └──────────────────┼───────────────────┘
                         │
              ┌──────────┴──────────┐
              │     DASHBOARD       │
              │  (reads everything) │
              └─────────────────────┘
                         │
                         │  (foundation complete)
                         ▼
              ┌─────────────────────┐
              │   MULTI-CURRENCY    │
              │   ASSETS REBUILD    │
              │   AI INPUTS         │
              │   SHARED SPACES     │
              └─────────────────────┘
```

---

## Feature: Expense Templates (Quick-Add)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   ┌─────────────────────────────────────────────────────┐                   │
│   │  DASHBOARD                                          │                   │
│   │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │                   │
│   │  │ ☕       │ │ 🚕      │ │ 🍕      │ │ 🛒      │   │  ← tap = instant  │
│   │  │ Coffee  │ │ Taxi    │ │ Lunch   │ │ Grocery │   │                   │
│   │  │ 15,000  │ │ 25,000  │ │ 45,000  │ │ 200,000 │   │                   │
│   │  └─────────┘ └─────────┘ └─────────┘ └─────────┘   │                   │
│   │  ◀────────────────── swipe ──────────────────▶      │                   │
│   └─────────────────────────────────────────────────────┘                   │
│                                                                             │
│   Template settings:                                                        │
│   ┌─────────────────────────────────────────────────────┐                   │
│   │  Name:       Coffee                                  │                   │
│   │  Category:   Dining Out                              │                   │
│   │  Amount:     15,000 UZS                              │                   │
│   │  Wallet:     [✓] Always Visa Gold  [ ] Ask each time │                   │
│   └─────────────────────────────────────────────────────┘                   │
│                                                                             │
│   Reuses existing RecurringExpense model + CycleBehavior.MANUAL             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Feature: Expected Outflows

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   Mirrors ExpectedInflows model:                                            │
│                                                                             │
│   ExpectedInflow                          ExpectedOutflow                   │
│   ──────────────                          ───────────────                   │
│   amount: int                             amount: int                       │
│   due_date: date                          due_date: date                    │
│   source_id → IncomeSource                category → ExpenseCategory        │
│   budget_year, budget_month               budget_year, budget_month         │
│   status: EXPECTED|RECEIVED               status: EXPECTED|SPENT            │
│                                                                             │
│   Monthly Timeline (Budgets page):                                          │
│   ┌─────────────────────────────────────────────────────┐                   │
│   │  THIS MONTH                                         │                   │
│   │  ████████████████████████░░░░░  Expected: 5,000,000 │                   │
│   │  ░░░░░░░░░░░░████████████░░░░░  Outflows: 3,200,000 │                   │
│   │  ░░░░░░░░░░░░░░░░░░░░░░░░████░  Free:     1,800,000 │                   │
│   └─────────────────────────────────────────────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Feature: Shared Spaces

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   SCHEMA (migrate NOW — zero cost):                                         │
│                                                                             │
│   CREATE TABLE groups (                                                     │
│     id          SERIAL PRIMARY KEY,                                         │
│     name        VARCHAR(64) NOT NULL,                                       │
│     created_by  INT REFERENCES users(id),                                   │
│     created_at  TIMESTAMPTZ DEFAULT now()                                   │
│   );                                                                        │
│                                                                             │
│   CREATE TABLE group_members (                                              │
│     group_id   INT REFERENCES groups(id),                                   │
│     user_id    INT REFERENCES users(id),                                    │
│     role       VARCHAR(16) DEFAULT 'member',  -- owner | member             │
│     joined_at  TIMESTAMPTZ DEFAULT now(),                                   │
│     PRIMARY KEY (group_id, user_id)                                         │
│   );                                                                        │
│                                                                             │
│   ALTER TABLE wallets  ADD COLUMN group_id INT REFERENCES groups(id);       │
│   ALTER TABLE budgets  ADD COLUMN group_id INT REFERENCES groups(id);       │
│   ALTER TABLE expenses ADD COLUMN group_id INT REFERENCES groups(id);       │
│   ALTER TABLE goals    ADD COLUMN group_id INT REFERENCES groups(id);       │
│                                                                             │
│   Null group_id = personal only (current behavior, zero change).            │
│   Non-null group_id = belongs to shared space.                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Deepest Background Fears (addressed)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   1. IMMUTABLE LEDGER                                                       │
│      Pattern: INSERT-only · void markers · compensating entries             │
│      Start: Expenses module first (simplest), then income, wallets          │
│      Foundation already exists: TransactionType, void_status,               │
│      linked_transaction_id, linked_event_id                                 │
│                                                                             │
│   2. PAYMENT PLANS REBUILD                                                  │
│      Model as state machine: draft → active → paid_off | defaulted          │
│      Each transition = immutable ledger entry                               │
│      Answer the domain questions first, then code                           │
│      Build AFTER immutable ledger — data integrity layer solved             │
│                                                                             │
│   DO ONE AT A TIME. Never both simultaneously.                              │
│   Immutable ledger first (foundation). Payment plans second (sits on it).   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Status: ACTIVE

| Date | Milestone | Status |
|------|-----------|--------|
| 2026-07-27 | Auth (all rounds) — backend + web + mobile | ✅ COMPLETE |
| 2026-07-27 | CI pipeline — all 3 codebases green | ✅ COMPLETE |
| — | Mobile tab navigation skeleton | ⬜ PENDING |
| — | Wallets screens (mobile + web polish) | ⬜ PENDING |
