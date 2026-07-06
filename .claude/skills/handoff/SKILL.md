---
name: handoff
description: Create concise next-session handoff prompts for Codex when context is getting long, a work slice is finished, the user wants to restart in a fresh session, or the user asks for a checkpoint, continuation prompt, resume prompt, context reset, or session handoff.
---

# Handoff

Create a compact prompt that lets a fresh Codex session continue the work with high signal and low stale context.

## Workflow

1. Identify the active objective from the latest user request and current work.
2. Prefer durable project artifacts over chat memory: read the plan file, docs, ADRs, tests, and relevant code that the next session must know.
3. Check the current worktree if code was changed or implementation is in progress.
4. Produce one copy-ready handoff prompt. Do not include broad transcript summaries.
5. Include exact files to read and the first concrete next step.

## Handoff Prompt Shape

Use this structure unless the user asks for a different format:

```text
Objective:
- <one concrete outcome for the next session>

Read first:
- <file or doc>
- <file or test>

Current state:
- <what is done, not done, blocked, or in progress>

Decisions to preserve:
- <stable product/domain/technical decisions>

Constraints:
- <what not to touch, dirty worktree notes, scope limits>

Next steps:
1. <first action>
2. <second action>
3. <third action>

Verification:
- <test/build command or manual check>

Stop when:
- <clear stopping condition>
```

## Rules

- Keep the handoff short enough to paste into a new session.
- Use absolute dates when dates matter.
- Name repo files explicitly.
- Mention uncommitted changes and user-owned worktree risk when relevant.
- Include tests already run and tests still needed.
- Include blockers only when the next session cannot proceed without a decision.
- Do not invent decisions; if uncertain, mark the item as an open question.
- Do not preserve stale failed approaches unless they prevent repeated mistakes.
- Do not create or edit repo files unless the user explicitly asks to save the handoff.

## Good Defaults For ExpenseTracker

- If the work relates to execution planning, read `docs/EC_IMPLEMENTATION_PLAN.md` first.
- If the work relates to edge cases, read only the relevant EC range from `docs/EDGE_CASES_AND_BUGS.md`.
- If the work relates to settled product decisions, read `docs/DECISIONS.md`.
- If the work relates to architecture language, read `CONTEXT.md` if it exists and any relevant ADRs.
- If the work relates to backend behavior, include the narrowest relevant pytest command.
- If the work relates to frontend behavior, include `npm.cmd run build` or the narrowest available frontend check.
