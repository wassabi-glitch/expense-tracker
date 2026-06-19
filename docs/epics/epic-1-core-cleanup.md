# Epic 1: Core Cleanup (Deadwood Removal)

**Status:** Not Started

## Goal
Before we can safely introduce advanced budget intelligence, we must "clear the blast radius" by removing highly complex, deprecated mechanisms from the core ledger. By deleting code related to Budget Rollovers and Budget Sweeping, we drastically simplify the database schema, reduce edge cases, and ensure a clean slate for Epic 2.

## PRDs Included

- [ ] **[G12 - Eradicate Budget Rollovers](../prd/g12-eradicate-budget-rollovers.md)**
  - Remove all rollover logic, UI toggles, and rollover DB columns.
- [ ] **[G13 - Eradicate Budget Sweeping](../prd/g13-eradicate-budget-sweeping.md)**
  - Remove the sweeping background tasks and UI sweep buttons.

## Execution Rules
- Execute vertically (Backend -> UI -> Tests).
- Ensure all tests pass after removing the deadwood before moving to the next PRD.
