# Mission: Model Payment Plans Truthfully

## Why
Rebuild Sarflog's Payment Plans around real repayment contracts so the backend remains understandable, auditable, and useful after the UI is redesigned.

## Success looks like
- Distinguish a financial product from the method used to generate its schedule.
- Classify common real-life obligations without forcing them into incorrect math.
- Recognize when Sarflog may generate a schedule and when the signed contract must be copied exactly.
- Set a clear boundary for products that need a future specialized engine.

## Constraints
- Existing development Payment Plan data may be discarded.
- Backend correctness comes before UI polish.
- Generated schedules are planning aids; the lender's contract remains authoritative.
- User-facing dates must follow the user's timezone and money math must use deterministic rounding.

## Out of scope
- Exact parity with every lender's legal interest calculation.
- Revolving credit-card and line-of-credit engines.
- Adjustable-rate, income-driven, and negative-amortization generators in the first rebuild.
- Final visual design of the creation and details experiences.
