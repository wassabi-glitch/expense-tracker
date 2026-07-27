# Payment Plan Modeling Resources

## Knowledge

- [Sarflog ADR 0028: Payment Plan Schedule Models and Contract Review](docs/adr/0028-payment-plan-schedule-models-and-contract-review.md)
  The project's current decision separating product language from schedule math. Use for: Sarflog terminology, supported generators, and product boundaries.
- [CFPB: What is amortization and how could it affect my auto loan?](https://www.consumerfinance.gov/ask-cfpb/what-is-amortization-and-how-could-it-affect-my-auto-loan-en-771/)
  A regulator's plain-language explanation of fixed payments whose interest and principal portions change. Use for: amortized-loan behavior.
- [CFPB: Buy Now, Pay Later market trends and consumer impacts](https://www.consumerfinance.gov/data-research/research-reports/buy-now-pay-later-market-trends-and-consumer-impacts/)
  Documents the common pay-in-four, equal-installment structure. Use for: fixed-total installment examples and their limits.
- [CFPB: How does paying down a mortgage work?](https://www.consumerfinance.gov/ask-cfpb/how-does-paying-down-a-mortgage-work-en-1943/)
  Explains why fixed-rate mortgage payments shift from interest-heavy to principal-heavy over time. Use for: principal/charge decomposition.
- [CFPB: What is a Qualified Mortgage?](https://www.consumerfinance.gov/ask-cfpb/what-is-a-qualified-mortgage-en-1789/)
  Identifies real variants such as interest-only periods, negative amortization, and balloon payments. Use for: stress-testing the boundary of the standard amortized generator.
- [CFPB: Simple interest versus precomputed interest](https://www.consumerfinance.gov/ask-cfpb/whats-the-difference-between-a-simple-interest-rate-and-precomputed-interest-on-an-auto-loan-en-841/)
  Explains interest calculated from the outstanding principal on a daily or monthly basis. Use for: declining-balance and daily-simple-interest examples.
- [CFPB: What is a daily periodic rate?](https://www.consumerfinance.gov/ask-cfpb/what-is-a-daily-periodic-rate-on-a-credit-card-en-46/)
  Explains how adding daily interest to the next day's balance creates daily compounding. Use for: identifying when interest itself starts earning interest.
- [CFPB: Tips for student-loan borrowers](https://www.consumerfinance.gov/paying-for-college/repay-student-debt/student-loan-debt-tips/)
  Gives a numerical example of daily interest and capitalization increasing principal. Use for: separating accrued interest from capitalized interest.
- [CFPB: How does interest accrue while I am in school?](https://www.consumerfinance.gov/ask-cfpb/how-does-interest-accrue-while-i-am-in-school-en-593/)
  Defines capitalization as accrued interest being added to principal and shows the resulting higher interest-bearing balance. Use for: capitalization actions and before/after schedule examples.
- [CFPB: What is negative amortization?](https://www.consumerfinance.gov/ask-cfpb/what-is-negative-amortization-en-103/)
  Explains how insufficient payments can leave unpaid interest that increases principal. Use for: capitalization triggers and explicit v1 boundaries.
- [CFPB: Negotiating a settlement with a debt collector](https://www.consumerfinance.gov/ask-cfpb/how-do-i-negotiate-a-settlement-with-a-debt-collector-en-1447/)
  Confirms that negotiated repayment and settlement agreements can be bespoke and should be recorded in writing. Use for: exact/manual contract schedules.
- [RFC 9110: HTTP Semantics, Section 9.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2)
  Defines idempotency as multiple identical requests having the same intended effect as one request. Use for: retry semantics and HTTP method behavior.
- [IETF HTTPAPI: Idempotency-Key Header Field (work in progress)](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-idempotency-key-header-07)
  Specifies a client-supplied key for making POST/PATCH requests fault-tolerant, including key reuse and concurrent-request behavior. Use for: API idempotency-key design; treat as a draft, not a final standard.
- [Stripe API: Idempotent requests](https://docs.stripe.com/api/idempotent_requests)
  Documents a production API pattern that stores the first result for a key and rejects reuse with different parameters. Use for: a concrete implementation model, not as an HTTP standard.

## Gaps

- Uzbekistan-specific lender calculation and disclosure rules should be researched before claiming legal parity with local bank contracts.
- No single industry term exactly matches Sarflog's `FLAT_TOTAL`; it is an internal schedule-generation name, not a universal financial-product label.
