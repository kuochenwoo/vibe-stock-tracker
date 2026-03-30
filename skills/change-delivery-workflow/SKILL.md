---
name: change-delivery-workflow
description: Handle post-change delivery hygiene for this project. Use when code, APIs, docs, or project files were modified and Codex must update the root CHANGELOG.md in STAR format with system datetime and update postman_collection.json when endpoints are created or changed, while leaving final verification and git operations to the user.
---

# Change Delivery Workflow

Apply this workflow after substantive changes in this repository. Treat it as the final delivery checklist for code, API, and project-structure updates.

## Workflow

1. Review what changed.
2. Update project artifacts that must stay in sync.
3. Hand off for final verification and git operations.

## Required Artifacts

### Update `CHANGELOG.md`

- Add a new entry for each new batch of changes.
- Use the system datetime in `YYYY-MM-DD hh:mm:ss` format.
- Use the existing STAR layout:
  Situation
  Task
  Action
  Result
- Include a short `Change` line and a `Reason` line.
- Keep the entry specific to the current change set. Do not rewrite older entries unless they are wrong.

### Update `postman_collection.json`

- When an HTTP endpoint is added, removed, renamed, or its request shape changes, update the root Postman collection in the same change.
- Keep `baseUrl` as a collection variable.
- Add or update request bodies, path params, and request names so the collection matches the backend routes.
- If no endpoint changed, leave the collection untouched.

## Handoff

- Stop after code and project artifacts are updated.
- Leave final verification to the user unless they explicitly ask for it.
- Leave `git add`, `git commit`, and `git push` to the user unless they explicitly ask for git operations.
- If relevant, briefly note whether `CHANGELOG.md` or `postman_collection.json` was updated as part of the change.

## Repo-Specific Notes

- The changelog file lives at the repository root: `CHANGELOG.md`.
- The Postman collection lives at the repository root: `postman_collection.json`.
- This workflow applies even for documentation-only or API-only changes when those artifacts are affected.
