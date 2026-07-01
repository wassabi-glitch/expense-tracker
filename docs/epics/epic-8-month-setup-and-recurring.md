# Epic 8: Month Setup & Recurring Engines

**Status:** Not Started  
**Depends On:** Epic 7 completion (and implicitly Epics 2, 4, and 5)

## Goal
Now that the entire backend engine accurately understands Expected Inflows, Category Floors, Overlay Project Slices, and strict Debt Chronology, we can build the ultimate user touchpoint: The Month Setup Wizard. This epic introduces the three modes of monthly planning and enforces the "Look-Ahead Warnings" and "Overlay Parasite" rules.

## PRDs Included

1. [ ] **[G6 - New Month Planner and Recurring Floors](../prd/g6-new-month-planner-and-recurring-floors.md)**
   - *Month Setup Wizard:* Build the UI and backend seams for "Plan from Scratch", "Copy Last Month", and "Smart Auto-Fill".
   - *Strict Limit Balancing (No Permissive UX):* The wizard must intercept over-planned states. If the copied plan exceeds available Plan Backing, the user must manually reduce limits to balance the budget before proceeding.
   - *Floor Enforcement:* Ensure Smart Auto-Fill aggregates both standard recurring expenses and active Overlay Project slices as mandatory Category Floors to prevent mathematical paradoxes.

## Execution Rules
- Epic 8 is deferred to the end of the roadmap because it relies on the data structures and mathematical definitions established in almost all prior epics (Debts, Overlays, Inflows, etc.).
