# 0021. Defer Project List Filtering, Search, and Pagination

Date: 2026-07-03

## Status

Accepted

## Context

Project lifecycle work introduced clearer states for overlay projects:

- Active projects can accept linked expenses.
- Paused projects keep reservations held but stop new linked spending.
- Completed projects are finished and release unused current/future reservations.
- Archived projects are preserved for history but should not behave like working projects.

During Issue 9 review, we considered adding backend filtering, frontend filtering, search, and pagination to the Projects list. Those capabilities are useful, especially once archived/completed projects accumulate, but they are list-management concerns rather than lifecycle correctness concerns.

## Decision

Defer project list filtering, search, and pagination to a future slice.

The future implementation should consider:

- backend filters for project status and project type
- a frontend status filter for Active, Paused, Completed, Archived, and All
- frontend text search first if project counts remain small
- backend search and pagination only when project volume, performance, or mobile UX requires it

## Consequences

- The current lifecycle slice stays focused on state rules, restore behavior, completion behavior, and deletion-resolution language.
- Archived projects may still appear in the current project list until the future filtering slice is implemented.
- Future project list work has a documented product direction without forcing API scope into this issue.
