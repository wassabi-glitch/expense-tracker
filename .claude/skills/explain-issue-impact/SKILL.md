---
name: explain-issue-impact
description: Explain a completed issue, feature, bug fix, or implementation in simple practical terms. Use when the user asks what an issue was about, what problem was solved, why the work mattered, what practical mission was accomplished, or asks for real-life examples after code or product work is completed.
---

# Explain Issue Impact

Explain completed work so the user understands the practical mission, not just the technical diff.

## Workflow

1. Identify the user-facing problem the work solved.
2. State the mission in one plain sentence.
3. Explain the before-and-after behavior.
4. Use simple real-life examples from the product domain.
5. Separate behavior that changed from behavior that intentionally stayed the same.
6. Avoid implementation jargon unless it directly helps understanding.

## Answer Shape

Use this structure by default:

```text
This issue was about <plain problem>.

The practical mission was: <one sentence>.

Before:
- <what was confusing, risky, duplicated, blocked, or missing>

Now:
- <what the user/system can do>
- <what is prevented or protected>

Example:
<concrete real-life scenario>

What stayed the same:
- <important unchanged behavior, if relevant>
```

## Style Rules

- Keep it simple, warm, and concrete.
- Prefer everyday examples over architecture language.
- Translate technical terms into product concepts.
- Use money, budgeting, workflow, or user-action examples when the project domain supports them.
- If the user asks about an issue number, explain the issue's intent first, then mention implementation details only briefly.
- If there were tests or verification, mention them only after the practical explanation.
