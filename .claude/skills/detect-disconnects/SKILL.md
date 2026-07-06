---
name: detect-disconnects
description: Analyze PRD documents against the codebase to identify frontend-backend disconnects. Use when the user wants to audit PRD features to see if the frontend is fully wired to the backend, or if parts of a feature are only partially implemented (e.g. UI exists but no API, or API exists but no UI).
---

<what-to-do>

Your goal is to systematically process product requirement documents (PRDs) and check the codebase for frontend-backend integration disconnects.

A "disconnect" means:
- The frontend UI exists, but it's not wired to any existing backend logic/API.
- The backend logic/API exists, but there is no frontend UI to interact with it. For example, endpoints and API client functions might exist, but React hooks, buttons, and menus are entirely missing from the UI (a UI disconnect).
- A feature mentioned in the PRD is partially implemented on one side but entirely missing on the other.

Follow this process:
1. **Locate PRDs**: First, locate the PRD files in `docs/prd/` (or wherever the user specifies).
2. **Iterate File by File**: Process one PRD file at a time. Do not try to do all of them at once.
3. **Extract Ideas**: Read the PRD file and extract the core features, UI requirements, and backend requirements.
4. **Codebase Audit**: 
   - Use `grep_search`, `list_dir`, and `view_file` to find related frontend code (e.g., React components, HTML/JS files, API client calls).
   - Use the same tools to find related backend code (e.g., API endpoints, services, database models).
5. **Detect Disconnects**: Compare what you found in the frontend vs. the backend. Identify any disconnects where the wiring is incomplete.
6. **Report Findings**: Present your findings for the current PRD file to the user. Use clear formatting to show:
   - The Idea/Feature
   - Frontend status
   - Backend status
   - Identified Disconnects
7. **Wait for Feedback**: After presenting the findings for one file, ask the user if they want to move on to the next file or dig deeper into the current one.

</what-to-do>

<supporting-info>

## Best Practices
- **Be Systematic**: Keep track of which PRDs you have already processed.
- **Provide Context**: When reporting a disconnect, mention the file paths where you looked and what you expected to find.
- **Don't Guess**: If you can't find something, state that it appears missing, rather than assuming it's implemented somewhere obscure.
- **Use Artifacts for Large Summaries**: If the list of disconnects is large, consider creating a Markdown artifact to store the results.

</supporting-info>
