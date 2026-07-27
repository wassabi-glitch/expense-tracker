# How real payment plans handle additional charges

**Research date:** 2026-07-15  
**Question:** Do banks, installment lenders, and store/BNPL providers insert later charges into the original principal-and-interest schedule, keep them separate, or capitalize them into principal?  
**Scope:** Product and architecture research, not legal or accounting advice. Contract terms and mandatory allocation rules vary by jurisdiction and product.

## Executive conclusion

The real-world pattern is not “all fees go into the schedule” or “all fees stay outside it.” Treatment depends mainly on **when the cost arises and what the contract does with it**:

| Situation | Typical treatment |
|---|---|
| Cost financed when the plan originates | Included in the opening financed principal or fixed contract price, then scheduled from day one |
| Cost paid or withheld at origination | Separate upfront/prepaid cost; it can affect APR or net proceeds without becoming future principal |
| Contractual interest | Tracked as interest, calculated under the contract from principal |
| Known recurring insurance, escrow, or service cost | Separate scheduled component, even if collected in the same monthly payment |
| Late fee, returned-payment fee, penalty, collection/legal cost | Separately assessed post-origination charge; normally does not rewrite the original principal-and-interest schedule |
| Unpaid interest or eligible arrears under a formal modification | May be explicitly capitalized into principal and followed by a replacement schedule |

Therefore, the safe Sarflog rule is:

> **An ordinary `ADD_CHARGE` action appends a separate `CHARGE`; it never silently changes principal, interest, or the existing amortization schedule. Only a separate, explicit contract-origination or contract-modification operation may turn an eligible amount into principal.**

This also confirms that Sarflog needs three independently reconstructible balances:

```text
remaining_total = remaining_principal
                + remaining_interest
                + remaining_charges
```

## The central distinction: servicing facts versus bill presentation

A provider may present one convenient number:

```text
Regular installment       1,000,000 UZS
Late fee                     50,000 UZS
──────────────────────────────────────
Total currently due       1,050,000 UZS
```

That presentation does **not** mean the late fee became principal or interest. Internally, the provider can still retain:

```text
Principal due               800,000
Interest due                200,000
Charge due                   50,000
```

This separation is explicit in U.S. mortgage servicing rules. A qualifying periodic mortgage payment covers principal, interest, and escrow even when it does not include late fees or other fees. Mortgage statements separately break payment application into principal, interest, escrow, fees, and charges, while also showing transaction activity. ([CFPB Regulation Z § 1026.36(c)](https://www.consumerfinance.gov/rules-policy/regulations/1026/36/), [CFPB Regulation Z § 1026.41](https://www.consumerfinance.gov/rules-policy/regulations/1026/41/))

The same idea appears in Uzbekistan. Uzum Nasiya defines a total debt or overdue debt that may aggregate principal, accrued interest, and other compensation/fees/fines, but it names those as distinct components. ([Uzum Nasiya public offer, pp. 6–8](https://uzumnasiya.uz/doc/publicOffer.pdf))

**Modeling consequence:** API and UI responses may return a combined `total_due`, but that total must be accompanied by a component breakdown. A combined card or bill is a view, not the source-of-truth representation.

## 1. Origination fees and other prepaid finance costs

Origination costs have more than one legitimate treatment.

### Financed at origination

Some costs are included in the legal loan amount or financed contract price. They are then repaid through the original schedule because they were part of the opening obligation—not because a later charge was inserted into an existing schedule.

CFPB Regulation Z examples explicitly distinguish a fee financed by the creditor from a fee paid in cash at closing. A financed fee can affect the principal/amount financed, while a cash-paid fee does not become financed principal. ([CFPB Regulation Z § 1026.18 and official interpretation](https://www.consumerfinance.gov/rules-policy/regulations/1026/18/))

The Federal Direct Loan program provides a useful second structure: its origination fee is deducted from the disbursement, so the borrower receives less cash but remains responsible for the full face amount borrowed. ([Federal Student Aid financial-aid dictionary](https://studentaid.gov/articles/financial-aid-dictionary/))

Uzum Nasiya supplies a local store/finance example. Its current public offer says that, for specified products, legal principal can include operator remuneration and the cost of the goods; a trade installment amount can include both the goods price and trade markup. ([Uzum Nasiya public offer, pp. 7–8](https://uzumnasiya.uz/doc/publicOffer.pdf))

### Paid or withheld upfront

A prepaid finance charge can be paid at closing or withheld from proceeds instead of being amortized through future installments. The consumer may receive less than the note’s face amount without the withheld fee becoming a newly assessed later charge. The CFPB describes origination fees as loan-making costs disclosed at origination, and Regulation Z requires them to be reflected in the appropriate credit-cost disclosures. ([CFPB origination-fee explanation](https://www.consumerfinance.gov/ask-cfpb/what-are-mortgage-origination-services-what-is-an-origination-fee-en-155/), [CFPB Regulation Z § 1026.4](https://www.consumerfinance.gov/rules-policy/regulations/1026/4/))

### Sarflog rule

- Preserve the lender’s **legal opening principal**, not a principal inferred from cash received.
- Optionally store `net_proceeds` and the opening cost breakdown for explanation.
- If the contract legally embeds a fee/markup in principal or fixed price, reflect that contract; do not manufacture a later `CHARGE_ADDED` event.
- If an upfront fee is itemized separately, represent it as an opening contractual `CHARGE`, with its real settlement method (paid in cash, withheld from proceeds, or still due).
- Never infer whether an opening fee is principal merely from the fee’s name. Follow the agreement.

## 2. Recurring contractual fees, insurance, taxes, and escrow

Institutions often collect these amounts in the same payment while accounting for them separately from principal and interest.

U.S. mortgage disclosures separate periodic principal-and-interest from estimated taxes, insurance, mortgage insurance, and other escrow items. ([CFPB Regulation Z § 1026.18(s)](https://www.consumerfinance.gov/rules-policy/regulations/1026/18/)) Fannie Mae’s servicing order likewise lists interest, principal, escrow deposits, and late charges as distinct destinations for the same incoming payment. ([Fannie Mae, Processing Mortgage Loan Payments and Payoffs](https://servicing-guide.fanniemae.com/svc/f-1-09/processing-mortgage-loan-payments-and-payoffs))

Regulation Z also illustrates that a statement can label periodic interest as an interest charge while showing credit-insurance cost as a fee. ([CFPB Regulation Z § 1026.7](https://www.consumerfinance.gov/rules-policy/regulations/1026/7/))

### Sarflog rule

- If a recurring cost is fixed and known at contract creation, create scheduled `CHARGE` components grouped with the corresponding installment.
- If it varies or is assessed later, append the charge when the institution assesses it.
- `STANDARD_AMORTIZATION` should generate principal and interest only. Insurance, tax, and service costs remain separate components even when the UI shows one monthly total.
- `EXACT_CONTRACT` should copy the institution’s scheduled components without reclassifying them.

## 3. Late fees and penalties

Late fees are generally event-triggered obligations rather than a rewrite of the original schedule.

U.S. Regulation Z excludes charges caused by an actual unanticipated late payment or similar default occurrence from the ordinary finance-charge definition. It also identifies a returned unpaid check as a similar separately triggered charge. ([CFPB Regulation Z § 1026.4(c)(2)](https://www.consumerfinance.gov/rules-policy/regulations/1026/4/)) For mortgages, the scheduled payment can be credited without the late fee, confirming that the late fee is outside the regular principal-interest-escrow installment. ([CFPB Regulation Z § 1026.36(c)](https://www.consumerfinance.gov/rules-policy/regulations/1026/36/))

BNPL contracts show several product choices:

- Klarna’s U.S. Pay in 4 may add a failed installment to the next payment together with a separately identified late fee. This changes the displayed next amount due but does not turn the fee into principal or interest. ([Klarna Pay in 4](https://www.klarna.com/us/pay-in-4/))
- Afterpay’s U.S. installment agreement keeps a final payment schedule and conditionally imposes a late fee after an installment remains unpaid for the stated period. ([Afterpay U.S. Installment Agreement](https://www.afterpay.com/en-US/installment-agreement))
- PayPal U.S. Pay in 4 and Affirm are counterexamples that currently charge no provider late fee; a failed PayPal funding payment can still cause the consumer’s bank to assess its own NSF fee. ([PayPal Pay in 4](https://www.paypal.com/us/cshelp/article/what-is-pay-in-4-help463), [Affirm terms](https://www.affirm.com/terms/))

Uzbekistan’s Central Bank separately discusses increased overdue interest, daily penalties, and additional one-time fines, and says default consequences must be transparent, proportionate, and established in advance. ([Central Bank of Uzbekistan review of credit sanctions, 2026-01-21](https://cbu.uz/uz/press_center/news/3326077/)) Its regulatory explanation also distinguishes principal from interest, commissions, penalties, and other liability measures when limiting total non-principal payments. ([Central Bank of Uzbekistan, debt-load regulation update](https://cbu.uz/ru/documents/3316/853181/))

### Sarflog rule

An assessed late fee should produce:

```text
CHARGE_ADDED action
└── CHARGE schedule row
    ├── charge_kind = LATE_FEE
    ├── amount
    ├── assessed_on
    ├── due_date
    ├── related_installment_id (optional)
    ├── contractual_basis or note (optional)
    └── immutable ledger entry
```

It should **not** mutate the related principal or interest rows. The UI may attach it visually to the missed installment or next bill.

## 4. Returned-payment and NSF fees

Returned-payment fees are also event-based costs. Regulation Z treats a returned unpaid payment as a default-like charge, separate from ordinary scheduled finance cost. ([CFPB Regulation Z § 1026.4(c)(2)](https://www.consumerfinance.gov/rules-policy/regulations/1026/4/))

There are two different real-life creditors to distinguish:

1. The plan provider may assess a returned-payment fee under its contract.
2. The user’s bank may assess an NSF fee independently, even when the plan provider does not.

PayPal’s official Pay in 4 explanation makes this distinction expressly: PayPal charges neither a Pay in 4 late fee nor NSF fee, but the funding institution may charge one. ([PayPal Pay in 4](https://www.paypal.com/us/cshelp/article/what-is-pay-in-4-help463))

### Sarflog rule

- A provider-assessed returned-payment fee is a Payment Plan `CHARGE` with `charge_kind = RETURNED_PAYMENT_FEE`.
- A bank-account NSF fee that is not owed to the payment-plan provider belongs to the bank/expense domain, not inside the Payment Plan’s obligation.
- The failed payment itself needs a reversed/failed money event; it must not remain counted as a successful Payment Plan payment.

## 5. Collection, legal, and recovery costs

Collection and legal costs increase the total amount owed only when the agreement and applicable law authorize them. They remain identifiable costs rather than becoming interest merely because they contribute to a payoff total.

The U.S. Federal Direct PLUS Loan promissory note says default may cause collection, court, and attorney costs in addition to the loan amount. Its payment instructions separately name late charges and collection costs when defining allocation order. ([Federal Student Aid Direct PLUS Master Promissory Note, pp. 10–11](https://studentaid.gov/sites/default/files/MasterPromissoryNoteMPNDirectPLUSLoans-en-us.pdf)) U.S. debt-collection rules likewise require balance itemization that distinguishes interest, fees, payments, and credits. ([CFPB Regulation F § 1006.34](https://www.consumerfinance.gov/rules-policy/regulations/1006/34/))

Uzbekistan Civil Code Article 248 puts other creditor collection expenses after principal/interest and penalty in the statutory order for insufficient payments on covered individual/business credits and microloans. This order itself demonstrates that those expenses are distinct obligations. ([LexUZ, Law ZRU-914 amending Civil Code Article 248](https://www.lex.uz/Pages/GetPdf.aspx?file=LexUz_6837534.pdf))

### Sarflog rule

- Add collection/legal costs only when actually assessed, not as speculative future amounts.
- Use separate charge kinds such as `COLLECTION_COST`, `LEGAL_FEE`, and `RECOVERY_COST`.
- Preserve the contract or source note that explains the charge.
- Do not relabel these costs as interest or principal unless a later formal capitalization event changes the legal obligation.

## 6. Payment allocation order is contractual and jurisdictional—not universal mathematics

There is no single global “charges first” waterfall.

Examples from primary sources:

- Fannie Mae’s normal modern mortgage order is interest, principal, escrow items, then late charges. ([Fannie Mae payment processing](https://servicing-guide.fanniemae.com/svc/f-1-09/processing-mortgage-loan-payments-and-payoffs))
- The U.S. Direct PLUS note uses late charges/collection costs, then interest, then principal for some repayment plans, but interest, then costs, then principal for other income-driven plans. ([Federal Student Aid Direct PLUS Master Promissory Note, p. 10](https://studentaid.gov/sites/default/files/MasterPromissoryNoteMPNDirectPLUSLoans-en-us.pdf))
- ANORBANK’s published microloan terms send insufficient payments through overdue interest/commissions, overdue principal, other overdue contractual amounts, and then penalties; its records also place principal and accrued interest in separate accounts. ([ANORBANK published microloan terms](https://anorbank.uz/upload/medialibrary/ab1/ab176939771af01405d74a0c04e76b92.pdf))
- Uzbekistan Civil Code Article 248 prescribes, for covered credit/microloan payments: overdue principal and overdue interest proportionally, then current interest and principal, then penalty, then other collection expenses. ([LexUZ, Law ZRU-914](https://www.lex.uz/Pages/GetPdf.aspx?file=LexUz_6837534.pdf))
- Afterpay publishes its own ordering for custom payments involving due-today, overdue, late-fee, and future installments. ([Afterpay payment management](https://www.afterpay.com/en-US/help/21014684254873-Managing-Your-Payments-Early-Multiple-Custom-and-More))

### Sarflog rule

- Do not encode one global allocation waterfall as “financial truth.”
- Store the plan’s `allocation_policy` and the actual allocations produced for each payment.
- Provide product/jurisdiction defaults, but allow the exact contract to override them.
- For Uzbekistan bank credit/microloan behavior, do not use a generic charges-first default that conflicts with Civil Code Article 248.
- Reversal must reverse the original recorded allocations rather than run today’s waterfall again.

## 7. Capitalization and re-amortization are explicit exceptional events

Capitalization means converting an amount that was previously interest or another eligible arrearage into principal. After that conversion, future interest may accrue on the larger principal and a new payment schedule may be necessary.

Federal student-loan materials define capitalization as adding unpaid accrued interest to principal; the borrower then pays interest on the higher principal. ([Federal Student Aid financial-aid dictionary](https://studentaid.gov/articles/financial-aid-dictionary/))

Fannie Mae’s Flex Modification shows how controlled this is in practice. A formal modification may capitalize specified accrued interest, escrow advances, and eligible servicing advances, but its rules explicitly prohibit capitalizing late charges and require them to be waived when modification conditions are met. The modification then establishes new loan terms. ([Fannie Mae Flex Modification](https://servicing-guide.fanniemae.com/svc/f-1-27/processing-fannie-mae-flex-modification))

The Central Bank of Uzbekistan’s consumer guidance says changes to credit agreements are made through an additional agreement, supporting an explicit contract change rather than a silent ledger mutation. ([Central Bank of Uzbekistan consumer reminder](https://cbu.uz/uz/consumer-protection/reminder-of-consumer-banking-services/?mobile=Y))

### Sarflog rule

Capitalization must be represented by its own business action, for example:

```text
CONTRACT_MODIFIED / BALANCE_CAPITALIZED
├── references the source INTEREST and/or CHARGE amounts
├── appends component-transfer ledger entries
│   ├── interest_delta or charge_delta = -X
│   ├── principal_delta = +X
│   └── total_delta = 0
├── preserves the original assessments and allocations
├── creates a new contract/schedule revision
└── regenerates future P&I only under the new agreed terms
```

This is not `ADD_CHARGE`. It cannot happen merely because a charge remains unpaid.

## Recommended Sarflog contract

### Component semantics

```text
PRINCIPAL
  The legal financed or contractual base amount currently classified as principal.

INTEREST
  The contractual cost of borrowing calculated as interest under the agreement.

CHARGE
  A non-interest fee, insurance amount, penalty, or other separately classified cost.
```

Regulatory terms such as **finance charge** or **total cost of credit** can include both interest and fees. Those disclosure categories must not collapse Sarflog’s operational `INTEREST` and `CHARGE` components.

### Original schedule versus later activity

```text
PAYMENT PLAN
│
├── ORIGINAL CONTRACT SCHEDULE
│   ├── PRINCIPAL rows
│   ├── INTEREST rows
│   └── known contractual CHARGE rows (if any)
│
└── APPEND-ONLY ACTIVITY
    ├── PAYMENT_RECORDED
    ├── CHARGE_ADDED
    ├── WRITE_OFF_RECORDED
    ├── CONTRACT_MODIFIED / BALANCE_CAPITALIZED
    └── REVERSAL
```

### Minimum charge fields

```text
payment_plan_charges
├── id
├── plan_id
├── action_id                 unique
├── schedule_row_id           unique
├── charge_kind
├── amount
├── assessed_on
├── due_date
├── related_installment_id    nullable
├── contractual_basis         nullable
├── external_reference        nullable
└── created_at
```

Recommended initial `charge_kind` values:

```text
ORIGINATION_FEE
SERVICE_FEE
INSURANCE
ADMINISTRATIVE_FEE
LATE_FEE
RETURNED_PAYMENT_FEE
PENALTY
COLLECTION_COST
LEGAL_FEE
OTHER
```

### Required invariants

1. Adding a charge never mutates an existing principal or interest row.
2. Every post-origination charge has a separate action, schedule row, and ledger entry.
3. A charge may be grouped with an installment for display without becoming part of that installment’s principal or interest.
4. Capitalization requires an explicit contract-modification action and schedule revision.
5. Capitalization preserves the source charge/interest history and records a component transfer; it does not delete or relabel history.
6. Payment allocations retain principal, interest, and charge destinations separately.
7. Reversal negates the original allocations exactly; it does not recompute them with the current waterfall.
8. A failed payment is not counted as paid and any provider fee resulting from failure is a separate charge.
9. `remaining_total` must reconcile with the three component balances and the immutable ledger.
10. Combined UI totals never replace component-level source data.

## Recommended UI/API presentation

The compact card can remain simple:

```text
Next installment       1,000,000 UZS
Additional charges        50,000 UZS
Total due              1,050,000 UZS
```

The Details view should show:

```text
Remaining principal    8,000,000 UZS
Remaining interest       900,000 UZS
Remaining charges         50,000 UZS
─────────────────────────────────────
Remaining total        8,950,000 UZS
```

The Activity view should retain separate events:

```text
Jul 01  Scheduled installment due
Jul 12  Late fee assessed               +50,000
Jul 15  Payment recorded              -500,000
        ├── interest                    200,000
        ├── principal                   250,000
        └── late fee                     50,000
```

Suggested API fields:

```text
next_contractual_installment
additional_charges_due
total_due
remaining_principal
remaining_interest
remaining_charges
remaining_total
allocation_policy
available_actions
```

## Decision for the rebuild

The real-world evidence supports the proposed Payment Plan architecture with this precise policy:

```text
DEFAULT
  Later fee/penalty/insurance assessment
      → append CHARGE
      → preserve original P&I schedule

AT ORIGINATION
  Financed fee or markup
      → follow the legal contract classification
      → may be included in opening principal/fixed price

EXCEPTION
  Formal capitalization/restructure
      → explicit modification action
      → preserve old history
      → transfer eligible balance into principal
      → create a revised schedule
```

So the correct answer is: **banks and stores frequently collect charges alongside installments, but they generally keep post-origination charges as separate assessed balances. They insert costs into principal or regenerate the schedule only when the original contract finances those costs or a later formal modification explicitly capitalizes them.**
