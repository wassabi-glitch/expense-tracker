---
name: pre-commit-review
description: Review uncommitted local changes as a senior engineer before they are committed or pushed. Use when the user asks for a code review on their current working directory, wants to check their uncommitted changes, or asks "review my code" before making a commit.
---

# Pre-Commit Code Review

You are acting as a Senior Engineer reviewing the user's uncommitted local code changes before they are committed or pushed to the CI pipeline.

## Instructions

1. **Gather the Diff**:
   Use the `run_command` tool to run `git diff HEAD` (this will show both staged and unstaged changes compared to the last commit).
   *Note: If the diff is too large, use `git diff HEAD --stat` first to get an overview, then view specific files.*

2. **Analyze the Changes**:
   - Do these changes make sense? 
   - Are there any syntax errors, off-by-one errors, or obvious logic bugs?
   - Did the user forget to handle edge cases (e.g., null values, empty states, timezone issues)?
   - Are there security implications or performance bottlenecks?
   - Does this align with the project's existing architecture and conventions?

3. **Deliver the Review**:
   Provide a concise, highly actionable code review using the following format:

   ```text
   ### 🕵️ Senior Review Summary
   [1-2 sentences summarizing what the changes do and your overall impression]

   ### 🚨 Critical Issues (Must Fix)
   - [Bug, security flaw, or major architectural issue]
   - (If none, write "None detected.")

   ### ⚠️ Suggestions & Edge Cases
   - [Performance improvements, naming conventions, minor edge cases]
   
   ### ✅ What Looks Good
   - [Call out specific things the user did well]
   ```

4. **Offer Next Steps**:
   Ask the user if they want you to automatically apply the fixes for the issues you found, or if they prefer to fix them manually.
