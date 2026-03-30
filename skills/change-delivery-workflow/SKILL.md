---
name: change-delivery-workflow
description: Handle post-change delivery hygiene for this project. Use when code, APIs, docs, or project files were modified and Codex must keep the changelog index and daily changelog files plus postman_collection.json in sync, while batching minor tweaks into larger changelog entries when appropriate and leaving final verification and git operations to the user.
---

# Change Delivery Workflow

Apply this workflow after substantive changes in this repository. Treat it as the final delivery checklist for code, API, and project-structure updates.

## Workflow

1. Review what changed.
2. Update project artifacts that must stay in sync.
3. Hand off for final verification and git operations.

## Required Artifacts

### Update The Changelog

- Add a new entry for each substantive batch of changes.
- Use the system datetime in `YYYY-MM-DD hh:mm:ss` format.
- Use the existing STAR layout:
  Situation
  Task
  Action
  Result
- Include a short `Change` line and a `Reason` line.
- Keep the entry specific to the current change set. Do not rewrite older entries unless they are wrong.
- Do not add a new entry for every minor polish tweak or tiny wording adjustment.
- Batch small related changes into one larger changelog entry when they belong to the same workstream.
- Add or update the changelog when one of these is true:
  - a feature, workflow, or behavior changed in a meaningful way
  - an API, data contract, or project structure changed
  - a bug fix materially changed user-visible behavior
  - a set of minor related tweaks is large enough to summarize as one coherent batch
- For very small follow-up tweaks, defer the changelog update until there is a meaningful batch to summarize.
- When batching, summarize the set of related tweaks in one STAR entry instead of creating multiple tiny entries.
- Keep the root `CHANGELOG.md` as an index only.
- Store actual entries in daily files under `changelogs/YYYY-MM/YYYY-MM-DD.md`.
- Keep exactly one changelog file per calendar day.
- If the current day's file already exists, append the new substantive entry to that file instead of creating another file.
- If the month folder does not exist yet, create it before writing the daily file.

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

- The changelog index lives at the repository root: `CHANGELOG.md`.
- Daily changelog files live under `changelogs/YYYY-MM/YYYY-MM-DD.md`.
- The Postman collection lives at the repository root: `postman_collection.json`.
- This workflow applies even for documentation-only or API-only changes when those artifacts are affected.
- Prefer fewer, higher-signal changelog entries over a long stream of tiny low-signal entries.
