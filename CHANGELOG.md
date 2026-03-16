# Change Log

## 2026-03-16 15:14:44

### Change
Created the initial full-stack realtime market tracking app with a Python backend and Vue frontend.

### STAR

#### Situation
The workspace started as a static prototype and did not satisfy the requirement for a Python backend, a Vue frontend, realtime updates, or configurable frontend alarms.

#### Task
Rebuild the project into a maintainable full-stack app that streams live market data for crude oil futures and XAUUSD, then expose alert creation on the frontend.

#### Action
- Replaced the static one-page prototype with a FastAPI backend in `backend/`.
- Added polling against Yahoo Finance symbols `CL=F` and `XAUUSD=X`.
- Added a websocket endpoint for pushing live updates to clients.
- Built a Vue 3 frontend in `frontend/` with live market cards and alert rule management.
- Added browser notification support and local storage persistence for alarm rules.
- Documented local setup and runtime flow in `README.md`.

#### Result
The project now has a backend/frontend architecture that can deliver live quote updates to the UI and trigger user-defined browser alerts when price thresholds are crossed.

### Reason
These changes were made to satisfy the explicit requirement for a Python backend, a Vue frontend, realtime page updates, and configurable alarm notifications.
