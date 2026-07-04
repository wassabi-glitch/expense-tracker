# PRD: G37 - Isolated Project Top-Ups and Unassigned Allocation

Labels: `ready-for-agent`

## Problem Statement

Isolated Projects protect major life events by locking real wallet money into a dedicated project stash. The first design for mid-project repairs made a top-up immediately cascade into a parent category or micro-subcategory. That mixed two different user decisions: adding more real money to the project, and deciding where inside the project that money belongs.

In real life, users often know that a project needs more funding before they know the exact category split. A renovation may need another 500,000, but the user may still be deciding whether that money belongs to materials, labor, transport, or contingency. The system needs to support that moment without loosening the isolated project vault.

## Solution

Split project repair into three simple actions:

- Top up an active isolated project from one or more eligible wallets.
- Keep newly topped-up money as unassigned project funding until the user allocates it.
- Let the user allocate or rebalance project funding into parent categories and micro-subcategories before spending.

Unassigned project funding increases the total isolated project stash, but it cannot be spent directly. Isolated project expenses still require a parent category, and optional micro-subcategory, with enough allocated funding available at that level.

## User Stories

1. As a project user, I want to top up an isolated project from one or more wallets, so that I can add real money when a project becomes more expensive.
2. As a project user, I want topped-up money to land in unassigned project funding first, so that I can decide the internal category split separately.
3. As a project user, I want to see total stash, assigned funding, unassigned funding, spent, and remaining funding, so that I understand the project at a glance.
4. As a project user, I want to allocate unassigned project money into parent categories, so that future project expenses have clear spending permission.
5. As a project user, I want to allocate category funding into micro-subcategories, so that detailed project spending remains organized.
6. As a project user, I want unassigned money to be blocked from direct spending, so that the project does not become a loose pile of cash.
7. As a project user, I want a clear error when I try to spend from a category that has no available allocation even though the project has unassigned money, so that I know to assign funding first.
8. As a project user, I want to rebalance already-assigned funding between categories or micro-subcategories, so that I can adapt when real prices change.
9. As a project user, I want rebalancing to respect actual spending, so that I cannot reduce a source bucket below money already spent there.
10. As a project user, I want top-ups to require eligible wallet money, so that project funding stays tied to real available cash.
11. As a project user, I want top-ups to fail when wallet free-to-allocate money or global Free Money Now is insufficient, so that I do not accidentally double-spend.
12. As a project user, I want completed and archived projects to reject top-ups, allocation changes, and rebalances, so that closed project history stays stable.
13. As a project user, I want expense overrun resolution to guide me to either top up the project or assign/rebalance funding, so that I can fix the blocker without guessing.
14. As a project user, I want before/after previews for top-up, allocation, and rebalance actions, so that I can trust the effect before saving.
15. As a budget user, I want isolated project top-ups and allocations to remain separate from monthly budget permission, so that normal budget categories are not distorted.

## Implementation Decisions

- Top-up means wallet funding into the isolated project stash only. It does not directly target a parent category or micro-subcategory.
- Top-ups may accept one or more funding wallets in a single action, provided every wallet is owned by the user, active, eligible, and has enough free-to-allocate money.
- New top-up funding increases isolated project wallet-allocation truth and therefore increases the derived total project stash.
- The system exposes unassigned isolated project funding as derived math: total project stash minus active assigned parent-category funding.
- Unassigned funding is project-level capacity, not expense permission.
- Parent category allocation and micro-subcategory allocation are explicit internal assignment actions separate from top-up.
- A parent category allocation can consume unassigned project funding but cannot cause total assigned parent-category funding to exceed the derived total stash.
- A micro-subcategory allocation consumes available parent-category room and cannot cause micro-subcategory funding to exceed the parent category allocation.
- Rebalancing moves already-assigned funding between categories or micro-subcategories without changing wallet allocations or total project stash.
- Rebalancing cannot reduce any source parent category or micro-subcategory below actual non-voided spending already posted against it.
- Isolated project expense posting continues to require a parent category and may require or allow a micro-subcategory according to the existing project setup.
- Expense posting cannot spend directly from unassigned project funding. If unassigned funding exists but the selected category lacks allocation, the user must assign or rebalance first.
- Top-up, allocation, and rebalance actions are blocked for completed and archived isolated projects.
- The project detail response should expose enough summary fields for the UI to render total stash, assigned, unassigned, spent, remaining, category availability, and micro-subcategory availability without guessing from nullable overlay fields.
- The overrun resolution UX should distinguish between "add more money to project" and "assign or rebalance existing project money."

## Testing Decisions

- Backend tests should verify behavior through public project and expense endpoints rather than private helper functions.
- Good top-up tests cover wallet ownership, multi-wallet top-up, insufficient wallet free-to-allocate money, insufficient global Free Money Now, transaction rollback, completed/archived blocking, and derived unassigned funding.
- Good allocation tests cover assigning unassigned funding into parent categories, allocating parent-category room into micro-subcategories, over-assignment rejection, and completed/archived blocking.
- Good rebalance tests cover moving category and micro-subcategory funding, preserving wallet allocation totals, preventing source buckets from going below actual spending, and transaction rollback.
- Good expense tests prove that unassigned project funding cannot be spent directly and that category or micro-subcategory allocation is required before expense posting succeeds.
- Frontend tests should cover top-up forms, allocation forms, rebalance forms, before/after previews, over-allocation errors, unassigned-money guidance, overrun resolution handoff, cache invalidation, mobile layout, and localized errors.
- Docker verification should pass for focused backend tests and frontend build.

## Out of Scope

- Direct top-up into a parent category or micro-subcategory.
- Automatic allocation of topped-up money.
- Spending directly from unassigned project funding.
- Changing historical expense ledger rows.
- Reopening completed or archived isolated projects.
- External bank integration.
- Native recurring expected inflows inside an isolated project.

## Further Notes

This PRD supersedes the older "cascading top-up" idea. The preserved cascade is conceptual rather than automatic: wallet money enters the project stash first, then the user deliberately assigns it into categories or micro-subcategories before spending.

