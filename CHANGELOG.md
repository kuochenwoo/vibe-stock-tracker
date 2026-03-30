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

## 2026-03-30 08:56:14

### Change
Refactored the app into a modular project structure, introduced a provider factory for market data, and replaced the failing raw Yahoo endpoint integration.

### STAR

#### Situation
The backend was calling a raw Yahoo Finance quote endpoint that was returning `401 Unauthorized`, the codebase was too concentrated in a few files, and the project needed a real extension point for future providers such as TradingView.

#### Task
Rework the project into a maintainable backend and frontend structure, isolate market data access behind a factory-based provider layer, and keep the realtime UI and alarms working.

#### Action
- Split the backend into `core`, `models`, `providers`, `services`, and `api` modules.
- Added a `MarketDataProviderFactory` to create provider implementations from configuration.
- Replaced the raw Yahoo quote call with a `yfinance` provider and verified live fetching for crude oil.
- Added an explicit fallback path for the XAUUSD instrument when the provider cannot serve `XAUUSD=X` directly.
- Split the Vue frontend into focused components and composables for streaming, cards, alerts, and error display.
- Updated the README with provider architecture, runtime configuration, and the current fallback behavior.
- Added ignore rules for generated local cache files.

#### Result
The backend is now structured like a real project, live data retrieval no longer depends on the failing endpoint, the frontend still builds successfully, and the provider layer is ready for a future TradingView or other market data implementation.

### Reason
These changes were made to fix the live market fetch failure, reduce coupling, and make the project extensible enough to support additional market data providers later.

## 2026-03-30 09:04:19

### Change
Replaced hard-coded ticker settings with a persisted tracked-ticker registry and added backend/frontend support for managing tickers dynamically.

### STAR

#### Situation
The app still relied on fixed symbol placeholders in backend settings, and the frontend alerting and market cards were tied to a static list. That made it awkward to add more instruments and conflicted with the goal of treating this as a real project.

#### Task
Move ticker definitions out of config placeholders, default gold to `GC=F`, add backend endpoints for managing tracked tickers, and make the frontend consume that dynamic list for both market display and alarms.

#### Action
- Removed hard-coded ticker symbols from backend settings.
- Added a persisted ticker registry in [tracked_tickers.json](/Users/guozhen_wu/Documents/vibe-code-test/backend/data/tracked_tickers.json) with default entries for `CL=F` and `GC=F`.
- Introduced repository and service layers for ticker management.
- Added `GET /api/tickers`, `POST /api/tickers`, and `DELETE /api/tickers/{code}` endpoints.
- Updated the market provider contract so providers fetch whatever symbols are currently tracked.
- Refactored the Vue frontend so market cards and alert options come from the live tracked ticker list instead of fixed constants.
- Added a frontend ticker management panel for adding and removing symbols.

#### Result
The app now treats tickers as project data rather than code constants. Live snapshots include the tracked ticker registry, `GC=F` is the default gold instrument, and new symbols can be added from the UI or backend API without editing source files.

### Reason
These changes were made to remove hard-coded ticker assumptions, make the project extensible, and support adding future instruments directly from the frontend.

## 2026-03-30 09:06:14

### Change
Normalized the default gold ticker so its tracked code is `GC=F` instead of `XAUUSD`.

### STAR

#### Situation
The default tracked ticker list still used `XAUUSD` as the internal code while mapping it to the provider symbol `GC=F`, which left an unnecessary mismatch in the seeded project data.

#### Task
Align the default gold instrument so the tracked ticker code and provider symbol both use the actual ticker `GC=F`.

#### Action
- Updated the seeded backend ticker repository entry to use `TrackedTicker(code="GC=F", symbol="GC=F", name="Gold Futures")`.
- Updated the persisted default ticker data file to match.
- Updated the main frontend heading and ticker creation placeholder to reflect `GC=F`.

#### Result
The default gold instrument is now represented consistently across backend seed data and frontend copy using the actual ticker `GC=F`.

### Reason
These changes were made to remove the remaining mismatch between the internal tracked ticker code and the actual provider symbol for gold futures.

## 2026-03-30 09:09:59

### Change
Added a standalone Postman collection template for the current backend API surface.

### STAR

#### Situation
The project had backend routes for health, markets, provider info, and ticker management, but there was no standalone Postman template to keep API testing in sync as endpoints evolve.

#### Task
Add a project-level Postman collection covering the current endpoints and make it clear that future endpoint changes must update that file too.

#### Action
- Created [postman_collection.json](/Users/guozhen_wu/Documents/vibe-code-test/postman_collection.json) at the project root.
- Included requests for `GET /api/health`, `GET /api/markets`, `GET /api/providers`, `GET /api/tickers`, `POST /api/tickers`, and `DELETE /api/tickers/{code}`.
- Added collection variables for `baseUrl` and `tickerCode`.
- Updated the README to point to the Postman collection and document the maintenance rule.

#### Result
The project now has a standalone Postman template that matches the current API and can be updated alongside future backend endpoint changes.

### Reason
These changes were made to keep API testing artifacts aligned with backend route changes instead of letting the API contract drift.
