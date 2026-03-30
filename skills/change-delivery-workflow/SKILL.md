---
name: change-delivery-workflow
description: Handle post-change delivery hygiene for this project. Use when code, APIs, docs, or project files were modified and Codex must keep the changelog index and daily changelog files plus postman_collection.json in sync, while batching minor tweaks into larger changelog entries when appropriate, keeping the todo list updated for idea-only discussions, and leaving final verification and git operations to the user.
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
- Use the existing STAR layout for feature entries:
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
- Formalize entry types:
  - For new features or meaningful feature expansions, group related work into one main feature entry and label it as `<span style="color:#1b8f59;font-weight:700;">FEAT</span>`.
  - Feature entries should use STAR and represent the main feature batch rather than many small sub-entries.
  - For bug fixes, label entries as `<span style="color:#d14343;font-weight:700;">FIX</span>`.
  - Bug-fix entries do not need a full STAR breakdown if the fixes are straightforward; a concise grouped summary is enough.
  - When multiple related bugs are fixed in the same batch, list them together under one `FIX` entry instead of creating one entry per bug.
  - Avoid mixing unrelated feature and fix work in the same entry unless the change set is inseparable.

### Update `postman_collection.json`

- When an HTTP endpoint is added, removed, renamed, or its request shape changes, update the root Postman collection in the same change.
- Keep `baseUrl` as a collection variable.
- Add or update request bodies, path params, and request names so the collection matches the backend routes.
- If no endpoint changed, leave the collection untouched.

### Update `TODO-LIST.md`

- When either the user or Codex proposes a new idea, enhancement, future feature, or architecture direction without implementing it in the current turn, add it to `TODO-LIST.md`.
- Treat idea capture as required project hygiene, not an optional note.
- Record each idea with an explicit status:
  - `Not Yet Implemented`
  - `Implemented`
- Use `Not Yet Implemented` for roadmap items, design ideas, deferred work, and future integrations that were discussed but not built yet.
- Change an item's status to `Implemented` when the work is actually completed in the repository.
- Update existing todo items instead of duplicating them when the same idea comes up again.
- Keep wording concise and implementation-oriented so the todo list stays useful as a working roadmap.
- If an idea is superseded or narrowed, revise the existing item rather than appending a conflicting duplicate.

## Handoff

- Stop after code and project artifacts are updated.
- Leave final verification to the user unless they explicitly ask for it.
- Leave `git add`, `git commit`, and `git push` to the user unless they explicitly ask for git operations.
- If relevant, briefly note whether the changelog, `postman_collection.json`, or `TODO-LIST.md` was updated as part of the change.

## Repo-Specific Notes

- The changelog index lives at the repository root: `CHANGELOG.md`.
- Daily changelog files live under `changelogs/YYYY-MM/YYYY-MM-DD.md`.
- The Postman collection lives at the repository root: `postman_collection.json`.
- The roadmap file lives at the repository root: `TODO-LIST.md`.
- This workflow applies even for documentation-only or API-only changes when those artifacts are affected.
- Prefer fewer, higher-signal changelog entries over a long stream of tiny low-signal entries.
