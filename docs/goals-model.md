# Goals Model

This file captures my current understanding of the Goals architecture from the backend code as of May 19, 2026.

If any part is wrong, correct the rule directly and I will use that corrected version as the frontend contract.

## 1. Core philosophy

Goals are not just simple "target + saved amount" cards anymore.

They now sit between:

- `Savings`
- `Goals`
- `Projects`

So the model has three different money states:

1. `Free savings`
   - money already in savings
   - not yet locked into a goal

2. `Funded inside goal`
   - money contributed into a goal
   - no longer free savings

3. `Released to project`
   - money that had been funded in the goal
   - then released into a linked project

That means the backend tracks more than just "saved so far".

It tracks:

- `funded_amount`
- `released_amount`
- `unreleased_amount`
- `linked_project_id`

## 2. Goal lifecycle status

Primary lifecycle status is still goal-level:

- `ACTIVE`
- `COMPLETED`
- `ARCHIVED`

Important nuance:

- goal completion is driven by `funded_amount` reaching `target_amount`
- not by release-to-project

So a goal can be:

- `COMPLETED`
- while still having `released_amount = 0`

Example:

- Goal: `Wedding`
- Target: `25M`
- Funded: `25M`
- Released to project: `0`

This is valid.

Meaning:

- savings mission is complete
- execution/spending mission may not have started yet

## 3. Contribution and return model

### Contribute
Route:

- `POST /goals/{goal_id}/contribute`

Meaning:

- move money from `free_savings_balance`
- into goal funding

Constraint:

- contribution cannot exceed free savings balance

### Return
Route:

- `POST /goals/{goal_id}/return`

Meaning:

- move money back from the goal into free savings

Important nuance:

- you can only return the `unreleased_amount`
- not the full `funded_amount`

So if:

- funded = `10M`
- released = `7M`
- unreleased = `3M`

then max return = `3M`

You cannot return the released part because that funding has already been committed to the linked project.

## 4. Goal -> Project bridge

This is the major new architecture.

### One goal can create one project

Backend enforces one linked project per goal using:

- `Project.origin_goal_id`
- unique constraint on that field

Meaning:

- one goal -> at most one project

### Graduation
Route:

- `POST /goals/{goal_id}/graduate`

Meaning:

- create a project from the goal
- link that project back to the goal
- optionally release an initial amount immediately

Payload supports:

- `project_title`
- `description`
- `start_date`
- `target_end_date`
- `total_limit`
- `is_isolated`
- `initial_release_amount`

Defaults/behavior:

- if `project_title` is omitted, it uses goal title
- if `total_limit` is omitted, it uses `goal.target_amount`
- if `target_end_date` is omitted, it uses `goal.target_date`
- if `initial_release_amount` is present, it creates the first goal-to-project release ledger row

Example:

- Goal: `Car Repair`
- Target: `10M`
- Funded already: `7M`

User graduates:

- Project title: `Car Repair`
- Total limit: `10M`
- Initial release: `7M`

Result:

- linked project created
- released amount becomes `7M`
- unreleased amount becomes `0`

## 5. Release-to-project model

Route:

- `POST /goals/{goal_id}/release-to-project`

Meaning:

- linked project already exists
- now release more funded goal money into that existing project

Payload:

- `amount`
- `released_at`
- `note`

Constraints:

- goal cannot be archived
- linked project must exist
- linked project must be active
- release amount cannot exceed `unreleased_amount`
- total released cannot exceed project total limit
- release date cannot be before project start date
- release date cannot be after project completion date

Example:

- Goal target: `10M`
- Funded: `9M`
- Released so far: `7M`
- Unreleased: `2M`

Valid release:

- release `2M`

Invalid release:

- release `3M`

because only `2M` remains unreleased

## 6. What goal summary means now

The frontend `GoalWithProgressOut` now means:

- `funded_amount`
  - total net amount currently locked in the goal after contributions and returns

- `released_amount`
  - amount already released from goal into linked project

- `unreleased_amount`
  - `funded_amount - released_amount`

- `remaining_amount`
  - `target_amount - funded_amount`

- `linked_project_id`
  - project created from this goal, if any

### Example

Goal:

- target `15M`
- funded `10M`
- released `4M`

then:

- unreleased = `6M`
- remaining = `5M`

Meaning:

- `6M` is still returnable to free savings
- `4M` is already committed to the linked project

## 7. Archive behavior

Route:

- `POST /goals/{goal_id}/archive`

Important backend behavior:

- archiving auto-returns the `unreleased_amount` out of the goal
- but keeps `released_amount` unchanged

So archive is not "just status flip".

It also reconciles loose goal money back into free savings.

Example:

- funded `10M`
- released `6M`
- unreleased `4M`

Archive:

- auto-return `4M`
- funded becomes effectively `6M`
- released stays `6M`

Meaning:

- nothing unreleased remains trapped in an archived goal

## 8. Delete behavior

Route:

- `DELETE /goals/{goal_id}`

Constraints:

- goal must already be archived
- funded amount must be zero
- released amount must be zero

So a goal cannot be permanently deleted while it still holds money or still has released funding history tied into a project.

## 9. Real-world examples

### Example A. Fully funded but not graduated

- Goal: `Laptop`
- Target: `12M`
- Funded: `12M`
- Released: `0`
- Status: `COMPLETED`

Meaning:

- user finished saving
- no linked project release has happened yet

### Example B. Partially funded and graduated

- Goal: `Car Repair`
- Target: `10M`
- Funded: `7M`
- Released: `7M`
- Unreleased: `0`
- Linked project exists
- Status: still `ACTIVE`

Meaning:

- project execution started early
- goal can still receive more contributions later

### Example C. Continued funding after project already exists

- Goal target: `10M`
- Funded: `9M`
- Released: `7M`
- Unreleased: `2M`

Later:

- release another `2M`

Now:

- Funded: `9M`
- Released: `9M`
- Unreleased: `0`

Later:

- contribute final `1M`

Now:

- Funded: `10M`
- Released: `9M`
- Unreleased: `1M`
- Status: `COMPLETED`

Meaning:

- contribution completion is independent from release completion

## 10. Frontend implications

A correct Goals frontend should now expose:

- create goal
- edit goal
- contribute
- return
- archive
- restore
- delete
- graduate to project
- release to project

And each goal card/detail should clearly show:

- funded
- released
- unreleased
- remaining to target
- linked project state

Important UX rules:

- `Return` should use `unreleased_amount` as the available balance
- not `funded_amount`

- `Graduate` should be shown only when no linked project exists

- `Release to project` should be shown only when a linked project already exists

- archived goals are read-only for money actions

## 11. Blunt summary

Goals are no longer only:

- "save money toward target"

They are now:

- a funding reservoir
- that can create a linked project
- and release funded tranches into that project over time

That is the current backend architecture as I understand it.
