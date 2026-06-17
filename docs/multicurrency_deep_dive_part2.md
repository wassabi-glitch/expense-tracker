# Multicurrency Deep Dive — Part 2: Buy/Sell Rates & Currency List

## Purchase vs Sale Rates (Bid/Ask Spread) — How Currency Exchange Really Works

### The Real-World Scene

Picture this: you walk into a currency exchange bureau (обменный пункт) in Tashkent. You see a board like this:

```
┌────────────────────────────────────────────────┐
│          EXCHANGE RATES — June 8, 2026         │
├──────────┬──────────────┬──────────────────────┤
│ Currency │  PURCHASE    │     SALE             │
│          │  (Покупка)   │     (Продажа)        │
├──────────┼──────────────┼──────────────────────┤
│ 1 USD    │  12,720 UZS  │   12,850 UZS         │
│ 1 EUR    │  13,850 UZS  │   14,020 UZS         │
│ 1 GBP    │  16,100 UZS  │   16,350 UZS         │
│ 1 RUB    │    139 UZS   │     143 UZS          │
└──────────┴──────────────┴──────────────────────┘
```

### What Do "Purchase" and "Sale" Mean?

This is told **from the bureau/bank's perspective**, which is confusing at first:

> **Purchase (Покупка) = The bank BUYS foreign currency FROM you**
> **Sale (Продажа) = The bank SELLS foreign currency TO you**

So from **YOUR** perspective as the customer:

| You want to... | You use the... | Rate | You get... |
|---|---|---|---|
| **Sell** your $100 USD → get UZS | **Purchase** rate | 12,720 | 1,272,000 UZS |
| **Buy** $100 USD ← pay with UZS | **Sale** rate | 12,850 | You pay 1,285,000 UZS |

**The bank always wins.** They buy dollars from you cheap (12,720) and sell dollars to you expensive (12,850). The difference — **130 UZS per dollar** — is called the **spread**. That's the bank's profit margin.

### A Concrete Example

**Scenario A: You're selling dollars**
You did freelance work and received $500 cash. You go to the bureau to convert it to UZS.
- Bureau's Purchase rate: 12,720
- You hand over: $500
- You receive: $500 × 12,720 = **6,360,000 UZS**

**Scenario B: You're buying dollars**
You want to save $500 for a trip. You go to the bureau with UZS.
- Bureau's Sale rate: 12,850
- You receive: $500
- You pay: $500 × 12,850 = **6,425,000 UZS**

**The difference:** Buying $500 costs you 65,000 UZS more than selling $500 earns you. That's the bank's revenue.

### The Mid-Market Rate (The "True" Rate)

There's a third rate that the bureau doesn't show you: the **mid-market rate** (also called interbank rate or spot rate). This is the real exchange rate between two currencies — the rate that banks trade with each other at.

```
Purchase rate:  12,720  ◄── Bank buys from you (lower)
                  │
Mid-market rate: 12,785  ◄── The "true" rate (average)
                  │
Sale rate:      12,850  ◄── Bank sells to you (higher)
```

The mid-market rate is simply: `(Purchase + Sale) / 2 = (12,720 + 12,850) / 2 = 12,785`

Apps like **Wise (TransferWise)** built their entire business on this concept — they show you the mid-market rate and charge a transparent fee, instead of hiding profit in the spread like traditional banks.

### What Rate Do Exchange Rate APIs Give You?

This is critical for your app:

| API / Source | What Rate They Provide |
|---|---|
| **Central Bank of Uzbekistan (CBU)** | Official rate — one single rate per currency per day. Not buy/sell. |
| **exchangerate-api.com, Open Exchange Rates** | Mid-market rate |
| **Wise API** | Mid-market rate |
| **Fixer.io** | Mid-market rate |
| **Google/XE** | Mid-market rate (what you see when you Google "USD to UZS") |
| **Individual banks (Humo, Uzcard banks)** | Buy AND Sell rates (different per bank) |

### Should Sarflog Model Purchase/Sale Rates?

Here's my strong recommendation:

> **No. Sarflog should use the mid-market rate for all internal calculations.**

Here's why:

1. **Sarflog is not a currency exchange platform.** You're a financial tracking app. You need to convert amounts for reporting, not to execute actual trades.

2. **Buy/sell rates vary by bank, by branch, by day, by amount.** Modeling them would require knowing *which specific bureau* the user went to — that's impractical.

3. **The mid-market rate is the fairest, most neutral rate.** It's what XE, Google, Wise, and every financial reporting tool uses. It's the industry standard.

4. **When a user does an actual currency exchange**, they enter the *real amounts* — "I gave 1,000,000 UZS and got $78." The actual rate they got is computed from those amounts (12,820.51 UZS/USD). This captures the real spread they paid, without you needing to model buy/sell separately.

**The philosophy:**
```
┌─────────────────────────────────────────────────────────────┐
│  For TRACKING past transactions:                            │
│  → Use the ACTUAL rate the user experienced                 │
│    (computed from real amounts they enter)                   │
│                                                             │
│  For DISPLAYING current values / dashboard / conversions:   │
│  → Use the MID-MARKET rate from an API                      │
│    (this is the global standard for "what is $1 worth?")    │
│                                                             │
│  For CONVERTING an expense from a foreign wallet to base:   │
│  → Use the mid-market rate at the time of the transaction   │
│    (user can override if they know the exact rate)          │
└─────────────────────────────────────────────────────────────┘
```

### Where Buy/Sell Rates *Could* Be Useful (Future Feature)

If you ever add a "Currency Exchange Finder" feature (comparing rates across Tashkent bureaus), *then* you'd show buy/sell rates. But that's a completely different feature from your core financial tracking engine. Think of it as a "nice to have" comparison tool, not a core accounting concept.

---

## How Many Currencies Should Sarflog Support?

### The Answer: Support ALL of Them (Through the API), Display a Curated List

Here's the smart approach: exchange rate APIs like Open Exchange Rates or exchangerate-api.com already support **160+ currencies**. You don't need to manually define exchange rates for each one. You store a simple list of supported currencies with their metadata, and the API handles the rates.

What you *do* need to curate is the **user-facing list** — the currencies that appear in dropdowns, onboarding, and wallet creation. Nobody wants to scroll through 160 currencies to find UZS.

### Recommended Currency List for Sarflog (Uzbekistan-First)

#### Tier 1 — Uzbekistan Essential (Always at the Top)

| Code | Currency | Symbol | Decimals | Why |
|---|---|---|---|---|
| UZS | Uzbekistani So'm | сўм / so'm | 0 | Home currency. Default for everything. |
| USD | US Dollar | $ | 2 | The de facto second currency of Uzbekistan. Everyone tracks USD savings. |

These two should be **front and center** in every dropdown, always on top.

#### Tier 2 — Very Common in Uzbekistan

| Code | Currency | Symbol | Decimals | Why |
|---|---|---|---|---|
| EUR | Euro | € | 2 | International purchases, some business dealings |
| RUB | Russian Ruble | ₽ | 2 | Huge trade partner, many remittances, Russia connection |
| CNY | Chinese Yuan | ¥ | 2 | Major trade partner, growing presence |

#### Tier 3 — Central Asian Neighbors

| Code | Currency | Symbol | Decimals | Why |
|---|---|---|---|---|
| KZT | Kazakhstani Tenge | ₸ | 2 | Closest neighbor, lots of cross-border activity |
| KGS | Kyrgyzstani Som | С | 2 | Close neighbor, shared history |
| TJS | Tajikistani Somoni | SM | 2 | Close neighbor, remittance corridor |
| TMT | Turkmenistani Manat | m | 2 | Neighbor (though forex is restricted there) |

#### Tier 4 — Major Global Currencies

| Code | Currency | Symbol | Decimals | Why |
|---|---|---|---|---|
| GBP | British Pound | £ | 2 | Major global currency |
| CHF | Swiss Franc | CHF | 2 | Safe haven currency, you mentioned it |
| JPY | Japanese Yen | ¥ | 0 | Major world currency |
| SAR | Saudi Riyal | ﷼ | 2 | Religious travel (Hajj/Umrah), worker remittances |
| AED | UAE Dirham | د.إ | 2 | Dubai is a huge hub for Uzbek travelers/workers |
| TRY | Turkish Lira | ₺ | 2 | Turkey is a major destination for Uzbek workers/students |
| KRW | South Korean Won | ₩ | 0 | Growing Uzbek diaspora in South Korea |

#### Tier 5 — Useful Additional Currencies

| Code | Currency | Symbol | Decimals | Why |
|---|---|---|---|---|
| CAD | Canadian Dollar | C$ | 2 | Global standard |
| AUD | Australian Dollar | A$ | 2 | Global standard |
| INR | Indian Rupee | ₹ | 2 | Regional importance |
| PLN | Polish Zloty | zł | 2 | Uzbek workers in Poland |
| GEL | Georgian Lari | ₾ | 2 | Popular destination for Uzbeks |
| ILS | Israeli Shekel | ₪ | 2 | Some diaspora connection |
| SGD | Singapore Dollar | S$ | 2 | Finance hub |
| HKD | Hong Kong Dollar | HK$ | 2 | Finance hub |
| THB | Thai Baht | ฿ | 2 | Popular travel destination |
| MYR | Malaysian Ringgit | RM | 2 | Some student/worker presence |
| BRL | Brazilian Real | R$ | 2 | Large economy |
| MXN | Mexican Peso | $ | 2 | Large economy |
| ZAR | South African Rand | R | 2 | BRICS connection |
| SEK | Swedish Krona | kr | 2 | European standard |
| NOK | Norwegian Krone | kr | 2 | European standard |
| DKK | Danish Krone | kr | 2 | European standard |
| CZK | Czech Koruna | Kč | 2 | European standard |
| HUF | Hungarian Forint | Ft | 2 | European standard |
| RON | Romanian Leu | lei | 2 | European standard |
| BGN | Bulgarian Lev | лв | 2 | European standard |
| UAH | Ukrainian Hryvnia | ₴ | 2 | Regional connection |
| BYN | Belarusian Ruble | Br | 2 | CIS connection |
| AZN | Azerbaijani Manat | ₼ | 2 | CIS/neighbor connection |
| AMD | Armenian Dram | ֏ | 2 | CIS connection |
| MDL | Moldovan Leu | L | 2 | CIS connection |
| EGP | Egyptian Pound | £ | 2 | Muslim world connection |
| PKR | Pakistani Rupee | ₨ | 2 | Muslim world connection |
| BDT | Bangladeshi Taka | ৳ | 2 | Regional |
| VND | Vietnamese Dong | ₫ | 0 | Growing trade |
| IDR | Indonesian Rupiah | Rp | 2 | Large Muslim-majority economy |
| PHP | Philippine Peso | ₱ | 2 | Large economy |
| NGN | Nigerian Naira | ₦ | 2 | Large economy |
| KES | Kenyan Shilling | KSh | 2 | East African hub |
| GHS | Ghanaian Cedi | GH₵ | 2 | West African economy |
| COP | Colombian Peso | $ | 2 | Latin American economy |
| CLP | Chilean Peso | $ | 0 | Latin American economy |
| PEN | Peruvian Sol | S/ | 2 | Latin American economy |
| ARS | Argentine Peso | $ | 2 | Notable for high inflation parallels |
| NZD | New Zealand Dollar | NZ$ | 2 | Global standard |
| QAR | Qatari Riyal | ﷼ | 2 | Gulf state |
| KWD | Kuwaiti Dinar | د.ك | 3 | Gulf state (note: 3 decimal places!) |
| BHD | Bahraini Dinar | .د.ب | 3 | Gulf state (3 decimals) |
| OMR | Omani Rial | ﷼ | 3 | Gulf state (3 decimals) |
| JOD | Jordanian Dinar | د.ا | 3 | Middle East (3 decimals) |
| TWD | Taiwan Dollar | NT$ | 2 | Tech economy |

**Total: ~55 currencies**

### How to Implement This Smartly

Don't hardcode 55 exchange rate values. Instead:

```
┌──────────────────────────────────────────────────────────┐
│  CURRENCY REGISTRY (in your app — static data)           │
├──────────────────────────────────────────────────────────┤
│  • code: "USD"                                           │
│  • name: "US Dollar"                                     │
│  • symbol: "$"                                           │
│  • decimal_places: 2                                     │
│  • flag_emoji: "🇺🇸"                                      │
│  • tier: 1  (for sort order in dropdowns)                │
│  • is_active: true                                       │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  EXCHANGE RATE CACHE (fetched from API periodically)     │
├──────────────────────────────────────────────────────────┤
│  • base: "USD"  (APIs typically use USD as base)         │
│  • rates: { "UZS": 12785, "EUR": 0.92, "RUB": 89.5 }   │
│  • fetched_at: "2026-06-08T10:00:00Z"                   │
│  • source: "exchangerate-api.com"                        │
└──────────────────────────────────────────────────────────┘
```

The currency registry is **static** — it changes only when you add a new currency to the app. The exchange rates are **dynamic** — fetched from an API every few hours.

### Important: Decimal Places Matter!

Notice that most currencies have 2 decimal places ($19.99), but some are special:

| Decimals | Currencies | Storage Implication |
|---|---|---|
| **0** | UZS, JPY, KRW, VND, CLP | Store as whole units (1 UZS = 1 minor unit) |
| **2** | USD, EUR, most others | Store as cents (1 USD = 100 cents → store 1999 for $19.99) |
| **3** | KWD, BHD, OMR, JOD | Store as 1/1000ths (1 KWD = 1000 fils → store 1500 for 1.500 KWD) |

You currently store amounts as `BigInteger`. The question is: **are you storing in major units (dollars) or minor units (cents)?**

Looking at your code, you store UZS as whole numbers (85000 for eighty-five thousand som). For multicurrency to work correctly, you should decide on a consistent strategy:

- **Option A: Store in minor units always** → $19.99 stored as 1999, 85000 UZS stored as 85000 (since UZS has 0 decimals, major = minor)
- **Option B: Store in major units always** → $19.99 stored as 1999 (cents) doesn't work cleanly...

**Option A is the industry standard.** Every fintech (Stripe, Wise, every bank) stores money in the smallest unit of the currency. This avoids floating-point issues entirely.

For your app this means:
- UZS: 85,000 som → store `85000` (0 decimal places, major unit = minor unit)
- USD: $19.99 → store `1999` (in cents)
- KWD: 1.500 KD → store `1500` (in fils)

Your existing UZS data naturally works since UZS has 0 decimal places. You just need to be aware of this when adding other currencies.

---

## Summary of Decisions So Far

Based on your feedback, here's where we stand:

| Decision | Your Choice |
|---|---|
| Exchange rate source | Auto-fetch from API (production quality) |
| Buy/Sell vs Mid-market | Mid-market rate for all internal calculations |
| Target market | Uzbekistan first, then expand |
| Budget currency | Base currency (UZS for Uzbek users) — we'll design carefully for edge cases |
| Manual vs auto rates | Auto-fetch, with user override option for actual transaction rates |
| Currency count | ~55 currencies, tiered for UX |
| Quality bar | Production-grade, not MVP |

Let me know your thoughts on:
1. The buy/sell rate explanation — does it make sense now?
2. The currency list — any currencies missing that you think are important?
3. The minor-unit storage strategy — does that feel right for your existing data?
