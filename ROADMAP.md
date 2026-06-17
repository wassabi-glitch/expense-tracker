<!-- ┌──────────────────────────────────────────────────────────────┐
│                    SARFLOG ROADMAP                           │
│        From core cleanup → mobile → AI → monetization         │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 1 — CORE FINANCIAL TRUTH CONSOLIDATION                │
│  Goal: make the existing web app logically clean and stable   │
├──────────────────────────────────────────────────────────────┤
│  1. Clean up Debts & Installments                            │
│     • Debt = obligation truth                                │
│     • Installment = contract/schedule UX                     │
│     • Ledger owns lifecycle/balance changes                  │
│                                                              │
│  2. Sync Goals → Pay Obligation                              │
│     • Goal can prepare money for debt/installment payments   │
│     • Paying obligation consumes protected goal money         │
│                                                              │
│  3. Sync Goals → Project Budgets                             │
│     • Fund Project goal can graduate into real project        │
│     • Project expenses use categories/subcategories           │
│                                                              │
│  4. Final Goals inspection                                   │
│     • Planned purchase                                       │
│     • Reserve money                                          │
│     • Pay obligation                                         │
│     • Fund project                                           │
│                                                              │
│  5. Implement Budget philosophy                              │
│     • Limit-based budgeting                                  │
│     • Budget room                                            │
│     • Realism checks                                         │
│     • Actions: expand, reduce, rebalance, warning            │
│                                                              │
│  6. Improve Income page                                      │
│     • Multi-wallet income                                    │
│     • Expected income                                        │
│     • Income → budget room                                   │
│     • Income vs other inflows                                │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  CHECKPOINT 1 — MERGE CLEAN CORE                             │
├──────────────────────────────────────────────────────────────┤
│  • Push to GitHub                                            │
│  • Merge to main                                             │
│  • Core one-currency web app should now be coherent           │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 2 — MULTICURRENCY FOUNDATION                          │
│  Goal: make Sarflog work with real-world mixed currencies    │
├──────────────────────────────────────────────────────────────┤
│  1. Start multicurrency branch                               │
│  2. Add wallet currency                                      │
│  3. Store original amount + original currency                 │
│  4. Add reporting/base currency                              │
│  5. Store exchange rate used                                 │
│  6. Support currency exchange events                         │
│  7. Make reports/budgets/goals currency-aware                 │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  CHECKPOINT 2 — MERGE MULTICURRENCY                          │
├──────────────────────────────────────────────────────────────┤
│  • Push to GitHub                                            │
│  • Merge after testing core currency flows                    │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 3 — ASSETS DOMAIN IMPROVEMENT                         │
│  Goal: make assets useful, not just stored records            │
├──────────────────────────────────────────────────────────────┤
│  • Improve asset types                                       │
│  • Link assets to purchases                                  │
│  • Link assets to loans/mortgages if needed                  │
│  • Prepare for future metals/stocks/crypto                   │
│  • Keep valuation manual first                               │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 4 — MOBILE APP FOUNDATION                             │
│  Goal: make Sarflog usable in real life, not only desktop    │
├──────────────────────────────────────────────────────────────┤
│  1. Build Expo/React Native app                              │
│  2. Auth + API client                                        │
│  3. Mobile design system                                     │
│  4. Home dashboard                                           │
│  5. Quick add expense                                        │
│  6. Wallets                                                  │
│  7. Goals                                                    │
│  8. Budgets                                                  │
│  9. Installments/obligations                                 │
│                                                              │
│  Add onboarding:                                             │
│  • Explain wallets                                           │
│  • Explain free-to-spend                                     │
│  • Explain goals/protected money                             │
│  • Explain budget room                                       │
│                                                              │
│  Add expense templates:                                      │
│  • Taxi                                                      │
│  • Food                                                      │
│  • Internet                                                  │
│  • Rent                                                      │
│  • Installment payment                                       │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  CHECKPOINT 3 — MOBILE FOUNDATION READY                      │
├──────────────────────────────────────────────────────────────┤
│  • Push to GitHub                                            │
│  • App now has real daily-use surface                         │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 5 — CAPTURE & INPUT INTELLIGENCE                      │
│  Goal: reduce manual friction                                │
├──────────────────────────────────────────────────────────────┤
│  1. Receipt scanning                                         │
│     • OCR draft                                              │
│     • User review                                            │
│     • Basket mode                                            │
│     • Category suggestions                                   │
│                                                              │
│  2. Voice input                                              │
│     • “I spent 80k on taxi from Humo”                        │
│     • Draft expense                                          │
│     • User confirms                                          │
│                                                              │
│  3. Natural language input                                   │
│     • Expense                                                │
│     • Income                                                 │
│     • Installment payment                                    │
│     • Transfer                                               │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  CHECKPOINT 4 — INPUT MAGIC READY                            │
├──────────────────────────────────────────────────────────────┤
│  • Push to GitHub                                            │
│  • Sarflog becomes faster and more delightful                 │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 6 — USEFUL AI INTEGRATION                             │
│  Goal: AI helps only where it improves money clarity          │
├──────────────────────────────────────────────────────────────┤
│  • Receipt extraction assistant                              │
│  • Smart categorization                                      │
│  • Duplicate/match detection                                 │
│  • Budget realism explanation                                │
│  • Monthly summary                                           │
│  • Goal prediction explanation                               │
│  • Financial consistency warnings                            │
│                                                              │
│  Rule:                                                       │
│  AI creates drafts/suggestions.                              │
│  User confirms financial truth.                              │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 7 — REBUILD COMMAND CENTER                            │
│  Goal: make the new system visible and understandable         │
├──────────────────────────────────────────────────────────────┤
│  1. Rebuild Dashboard                                        │
│     • Free-to-spend                                          │
│     • Budget room                                            │
│     • Protected money                                        │
│     • Upcoming obligations                                   │
│     • Goal progress                                          │
│     • Project/debt warnings                                  │
│                                                              │
│  2. Rebuild Analytics                                        │
│     • Category spending                                      │
│     • Goal-funded vs normal spending                         │
│     • Reserve-funded spending                                │
│     • Multicurrency reporting                                │
│     • Income vs spending                                     │
│     • Obligations forecast                                   │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  CHECKPOINT 5 — CORE APP READY                               │
├──────────────────────────────────────────────────────────────┤
│  • Final push to GitHub                                      │
│  • Core web + mobile app is now serious                      │
│  • Main financial model is coherent                          │
│  • User-facing value is clear                                │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 8 — BUSINESS LAYER                                    │
│  Goal: turn Sarflog from product project into startup         │
├──────────────────────────────────────────────────────────────┤
│  1. Payment gateways in Uzbekistan                           │
│  2. Pricing strategy                                         │
│     • Free tier                                              │
│     • Premium tier                                           │
│     • Maybe founding member plan                             │
│                                                              │
│  3. Marketing                                                │
│     • “Your bank shows balance. Sarflog shows meaning.”      │
│     • Goal cards                                             │
│     • Free-to-spend hook                                     │
│     • Local finance pain points                              │
│                                                              │
│  4. Beta users                                               │
│  5. Feedback loop                                            │
│  6. Play Store / App Store polish                            │
│  7. Revenue target                                           │
│     • First $50/month                                        │
│     • Then $100/month                                        │
│     • Then $500/month                                        │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    LONG-TERM VISION                          │
├──────────────────────────────────────────────────────────────┤
│  Sarflog becomes a personal finance operating system:         │
│                                                              │
│  • Wallet truth                                              │
│  • Protected money                                           │
│  • Budget room                                               │
│  • Goals                                                     │
│  • Projects                                                  │
│  • Debts/installments                                        │
│  • Assets                                                    │
│  • Multicurrency                                             │
│  • Receipt/voice/AI input                                    │
│  • Premium mobile UX                                         │
│  • Real-world financial clarity                              │
└──────────────────────────────────────────────────────────────┘ -->






┌──────────────────────────────────────────────────────────────┐
│                    SARFLOG ROADMAP                           │
│    From core cleanup → financial visibility → mobile → AI     │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 1 — CORE FINANCIAL TRUTH CONSOLIDATION                │
│  Goal: make the existing web app logically clean and stable  │
├──────────────────────────────────────────────────────────────┤
│  1. Clean up Debts & Installments                            │
│     • Debt = obligation truth                                │
│     • Installment = contract/schedule UX                     │
│     • Ledger owns lifecycle/balance changes                  │
│     • Support partial/advance installment payments           │
│                                                              │
│  2. Sync Goals → Pay Obligation                              │
│     • Goal can prepare money for debt/installment payments   │
│     • Paying obligation consumes protected goal money        │
│     • Avoid duplicate debt/payment truth                     │
│                                                              │
│  3. Sync Goals → Project Budgets                             │
│     • Fund Project goal can graduate into real project       │
│     • Reserve money can fund a more specific project         │
│     • Project expenses use categories/subcategories          │
|                                                              │
│  4. Final Goals inspection                                   │
│     • Planned purchase                                       │
│     • Reserve money                                          │
│     • Pay obligation                                         │
│     • Fund project                                           │
│     • Confirm budget-impact rules                            │
│                                                              │
│  5. Implement Budget philosophy                              │
│     • Limit-based budgeting                                  │
│     • Budget room                                            │
│     • Realism checks                                         │
│     • Actions: expand, reduce, rebalance, warning            │
│     • Goal-funded spending separated from normal limits      │
│                                                              │
│  6. Improve Income page                                      │
│     • Multi-wallet income                                    │
│     • Expected income                                        │
│     • Income → budget room                                   │
│     • Income vs other inflows                                │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  CHECKPOINT 1 — MERGE CLEAN CORE                             │
├──────────────────────────────────────────────────────────────┤
│  • Push to GitHub                                            │
│  • Merge to main                                             │
│  • Core one-currency web app should now be coherent          │
│  • Main financial laws should be documented                  │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 2 — MULTICURRENCY FOUNDATION                          │
│  Goal: make Sarflog work with real-world mixed currencies    │
├──────────────────────────────────────────────────────────────┤
│  1. Start multicurrency branch                               │
│  2. Add wallet currency                                      │
│  3. Store original amount + original currency                │
│  4. Add reporting/base currency                              │
│  5. Store exchange rate used                                 │
│  6. Support currency exchange events                         │
│  7. Make reports/budgets/goals currency-aware                │
│  8. Preserve original values forever                         │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  CHECKPOINT 2 — MERGE MULTICURRENCY                          │
├──────────────────────────────────────────────────────────────┤
│  • Push to GitHub                                            │
│  • Merge after testing core currency flows                   │
│  • Wallets, goals, budgets, debts, income, and reports       │
│    should understand currency correctly                      │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 3 — ASSETS DOMAIN IMPROVEMENT                         │
│  Goal: make assets useful, not just stored records           │
├──────────────────────────────────────────────────────────────┤
│  • Improve asset types                                       │
│  • Link assets to purchases                                  │
│  • Link assets to loans/mortgages if needed                  │
│  • Support bank deposits as asset-like products              │
│  • Prepare for future metals/stocks/crypto                   │
│  • Keep valuation manual first                               │
│  • Feed assets into net worth / liquidity view               │
└──────────────────────────────┬───────────────────────────────┘ July 1st deadline
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 4 — REBUILD COMMAND CENTER                            │
│  Goal: make the new financial system visible and useful      │
├──────────────────────────────────────────────────────────────┤
│  1. Rebuild Dashboard                                        │
│     • Free-to-spend                                          │
│     • Budget room                                            │
│     • Protected money                                        │
│     • Upcoming obligations                                   │
│     • Goal progress                                          │
│     • Project/debt warnings                                  │
│     • Multicurrency net position                             │
│     • Assets/debts snapshot                                  │
│                                                              │
│  2. Rebuild Analytics                                        │
│     • Category spending                                      │
│     • Goal-funded vs normal spending                         │
│     • Reserve-funded spending                                │
│     • Project spending                                       │
│     • Multicurrency reporting                                │
│     • Income vs spending                                     │
│     • Obligations forecast                                   │
│     • Assets/debts/net-worth insight                         │
│                                                              │
│  3. Define Free vs Premium analytics                         │
│     • Free: current month/basic clarity                      │
│     • Premium: history, forecasts, advanced filters, AI      │
└──────────────────────────────┬───────────────────────────────┘July 7th deadline
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 5 — FULL UI/UX DESIGN SYSTEM                          │
│  Goal: make Sarflog feel premium, calm, and trustworthy      │
├──────────────────────────────────────────────────────────────┤
│  1. Responsive web polish                                    │
│     • Desktop                                                │
│     • Tablet                                                 │
│     • Mobile web                                             │
│                                                              │
│  2. App-wide design system                                   │
│     • Wallet cards                                           │
│     • Goal cards                                             │
│     • Budget cards                                           │
│     • Debt/installment cards                                 │
│     • Asset cards                                            │
│     • Empty states                                           │
│     • Review screens                                         │
│     • Confirmation flows                                     │
│                                                              │
│  3. UX simplification                                        │
│     • Ordinary expense = fast form                           │
│     • Meaning-heavy action = guided flow                     │
│     • Advanced options hidden until needed                   │
│                                                              │
│  4. Prepare mobile design language                           │
│     • Same product soul                                      │
│     • Smaller-screen patterns                                │
│     • Quick actions                                          │
│     • Bottom sheets                                          │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  CHECKPOINT 3 — WEB CORE FEELS SERIOUS                       │
├──────────────────────────────────────────────────────────────┤
│  • Push to GitHub                                            │
│  • Web version is now coherent, responsive, and premium      │
│  • Dashboard/Analytics explain Sarflog’s value clearly       │
│  • Ready to reuse design language in mobile app              │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 6 — MOBILE APP FOUNDATION                             │
│  Goal: make Sarflog usable in real life, not only desktop    │
├──────────────────────────────────────────────────────────────┤
│  1. Build Expo/React Native app                              │
│  2. Auth + API client                                        │
│  3. Mobile design system                                     │
│  4. Mobile Home dashboard                                    │
│  5. Quick add expense                                        │
│  6. Wallets                                                  │
│  7. Goals                                                    │
│  8. Budgets                                                  │
│  9. Installments/obligations                                 │
│ 10. Basic analytics cards                                    │
│                                                              │
│  Add onboarding:                                             │
│  • Explain wallets                                           │
│  • Explain free-to-spend                                     │
│  • Explain goals/protected money                             │
│  • Explain budget room                                       │
│                                                              │
│  Add expense templates:                                      │
│  • Taxi                                                      │
│  • Food                                                      │
│  • Internet                                                  │
│  • Rent                                                      │
│  • Installment payment                                       │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  CHECKPOINT 4 — MOBILE FOUNDATION READY                      │
├──────────────────────────────────────────────────────────────┤
│  • Push to GitHub                                            │
│  • App now has real daily-use surface                        │
│  • Users can quickly check and record money events           │
└──────────────────────────────┬───────────────────────────────┘August 1st deadline
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 7 — CAPTURE & INPUT INTELLIGENCE                      │
│  Goal: reduce manual friction                                │
├──────────────────────────────────────────────────────────────┤
│  1. Receipt scanning                                         │
│     • OCR draft                                              │
│     • User review                                            │
│     • Basket mode                                            │
│     • Category suggestions                                   │
│     • Terminal receipt vs item receipt distinction           │
│                                                              │
│  2. Voice input                                              │
│     • “I spent 80k on taxi from Humo”                        │
│     • Draft expense                                          │
│     • User confirms                                          │
│                                                              │
│  3. Natural language input in a telegram bot                                 │
│     • Expense                                                │
│     • Income                                                 │
│     • Installment payment                                    │
│     • Transfer                                               │
│                                                              │
│  Rule:                                                       │
│  Messy input creates drafts, not final truth.                │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  CHECKPOINT 5 — INPUT MAGIC READY                            │
├──────────────────────────────────────────────────────────────┤
│  • Push to GitHub                                            │
│  • Sarflog becomes faster and more delightful                │
│  • Manual tracking friction is reduced                       │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 8 — USEFUL AI INTEGRATION                             │
│  Goal: AI helps only where it improves money clarity         │
├──────────────────────────────────────────────────────────────┤
│  • Receipt extraction assistant                              │
│  • Smart categorization                                      │
│  • Duplicate/match detection                                 │
│  • Budget realism explanation                                │
│  • Monthly summary                                           │
│  • Goal prediction explanation                               │
│  • Financial consistency warnings                            │
│  • Analytics insight cards                                   │
│                                                              │
│  Rule:                                                       │
│  AI creates drafts/suggestions/explanations.                 │
│  User confirms financial truth.                              │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  CHECKPOINT 6 — CORE APP READY                               │
├──────────────────────────────────────────────────────────────┤
│  • Final push to GitHub                                      │
│  • Core web + mobile app is now serious                      │
│  • Main financial model is coherent                          │
│  • User-facing value is clear                                │
│  • AI enhances the app without owning truth                  │
└──────────────────────────────┬───────────────────────────────┘august 15 deadline
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  PHASE 9 — BUSINESS LAYER                                    │
│  Goal: turn Sarflog from product project into startup        │
├──────────────────────────────────────────────────────────────┤
│  1. Payment gateways in Uzbekistan                           │
│  2. Pricing strategy                                         │
│     • Free tier                                              │
│     • Premium tier — around $3/month                         │
│     • Maybe founding member plan                             │
│                                                              │
│  3. Marketing                                                │
│     • “Your bank shows balance. Sarflog shows meaning.”      │
│     • Goal cards                                             │
│     • Free-to-spend hook                                     │
│     • Local finance pain points                              │
│     • Cash/cards/e-wallets/installments/goals                │
│                                                              │
│  4. Beta users                                               │
│  5. Feedback loop                                            │
│  6. Play Store / App Store polish                            │
│  7. Revenue target                                           │
│     • First $50/month                                        │
│     • Then $100/month                                        │
│     • Then $500/month                                        │
│     • $3/month × ~167 paid users = ~$500/month 
   8. Security/auth hardening              │
└──────────────────────────────┬───────────────────────────────┘LAUNCH September 1st!
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    LONG-TERM VISION                          │
├──────────────────────────────────────────────────────────────┤
│  Sarflog becomes a personal finance operating system:        │
│                                                              │
│  • Wallet truth                                              │
│  • Protected money                                           │
│  • Budget room                                               │
│  • Goals                                                     │
│  • Projects                                                  │
│  • Debts/installments                                        │
│  • Assets                                                    │
│  • Multicurrency                                             │
│  • Dashboard/analytics command center                        │
│  • Premium responsive web UX                                 │
│  • Premium mobile UX                                         │
│  • Receipt/voice/AI input                                    │
│  • Real-world financial clarity                              │
└──────────────────────────────────────────────────────────────┘  