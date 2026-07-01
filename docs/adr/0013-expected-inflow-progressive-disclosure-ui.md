# 0013. Expected Inflow Progressive Disclosure UI

## Context

Following the two-layer database architecture defined in ADR-0012, the Expected Inflows frontend UI was still suffering from massive cognitive overload. The previous design resembled a "Developer UI"—dumping raw database tables, internal string IDs, and global action buttons onto a single screen. This violated Miller's Law (working memory limits) and blurred the lines between the Promise (the "What") and the Schedule (the "When").

Specific pain points included:
1. Promise rows displaying irrelevant schedule dates and global action buttons.
2. The Promise Details page being cluttered with ugly, separate tables for "Schedule History", "Activity", and "Write-offs".
3. A lack of intuitive visual hierarchy for understanding contract completion.
4. "Orphaned" UI states where users were unsure what specific chunk of money an action button would affect.

## Decision

We are adopting a strict **Progressive Disclosure** UI model for the Expected Inflows feature, driven by human psychology and the underlying two-layer database architecture.

### 1. Tabbed Presentation Structure
The UI is strictly split into two mental models:
- **Tab 1: Agreements / Promises (The "What"):** A high-level list of contracts. No dates, no month filtering.
- **Tab 2: Cashflow / Schedules (The "When"):** A time-based calendar list of specific payment chunks due in the currently selected month.

### 2. The Promise Row & The Tri-Color Progress Bar
The Promise row in Tab 1 will be heavily simplified to answer one question: *"How close is this contract to being finished?"*
- We are removing all action buttons (`Receive`, `Reschedule`) and dates from the Promise row.
- We are introducing a **Tri-Color Progress Bar** where the target (100% fill) is the `original_amount`.
  - 🟩 **Green fill:** Received amount.
  - 🟥 **Red/Gray fill:** Written off amount.
  - ⬜ **Empty space:** Outstanding amount.

### 3. The Details Drawer & Inline Actions
Clicking a Promise row opens a details drawer for mechanical accounting work.
- **Summary Cards:** Retains the 4 top-level KPI cards (Expected, Received, Written off, Outstanding).
- **Inline Actions:** Global action buttons are removed from the top header. Instead, `Receive`, `Reschedule`, and `Write off` buttons are placed **directly inside each active Schedule Card**. This ensures the user intuitively knows exactly which chunk of money they are manipulating.

### 4. The Unified Timeline
We are deleting the raw database table dumps ("Schedule history", "Activity", "Write-offs").
- These will be merged into a single **Unified Timeline**.
- The timeline will read chronologically like a human story (e.g., "[Date] 🟢 Received $5,000", "[Date] 🔄 Rescheduled remaining to Aug 1").
- Raw database IDs are hidden. Amounts are properly formatted with currency.

### 5. Schedule Tab Rows & Deep Linking
Rows on the Schedules Tab (Tab 2) are focused purely on immediate cashflow collection.
- **Row Elements:** Specific Date, Parent Promise Title (for context), Amount, Status Badge, and Action buttons.
- **Hidden Bloodline:** We will *not* show the deep rescheduling history (the "bloodline") on this tab to prevent cognitive overload.
- **No Orphaned Pages:** Schedules will not have their own dedicated details page. Clicking a Schedule row on Tab 2 will open the Parent Promise Details Drawer and visually anchor/highlight the specific Schedule Card.

## Consequences

- **Reduced Cognitive Load:** Users are no longer overwhelmed by raw data dumps. The UI feels like a premium financial tool rather than a database viewer.
- **Architectural Clarity:** The visual separation of action buttons directly reinforces the ADR-0012 backend architecture (rescheduling acts on the Schedule, not the Promise).
- **Development Effort:** Requires significant refactoring of the `ExpectedInflowDetails.jsx` and `ExpectedInflowsPanel.jsx` components, including the creation of a new Unified Timeline component and a Tri-Color Progress bar component.
