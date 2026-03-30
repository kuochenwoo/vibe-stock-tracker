# Realtime Market Alerts

This app is split into:

- `backend/`: Python FastAPI service with provider factory, polling service, websocket streaming, and API routes
- `frontend/`: Vue 3 app with components and composables for market streaming and alarm management

## Market instruments

- `CL=F`: crude oil futures front month
- `GC=F`: gold futures

## Backend

```bash
cd /Users/guozhen_wu/Documents/vibe-code-test/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The backend starts on `http://127.0.0.1:8000`.

API client template:

- A standalone Postman collection is available at [postman_collection.json](/Users/guozhen_wu/Documents/vibe-code-test/postman_collection.json)
- When endpoints are added or changed, this collection should be updated alongside the backend routes

Environment variables:

- `MARKET_DATA_PROVIDER=yfinance`
- `MARKET_POLL_INTERVAL_SECONDS=5`

Endpoints:

- `GET /api/health`
- `GET /api/markets`
- `GET /api/providers`
- `GET /api/tickers`
- `POST /api/tickers`
- `DELETE /api/tickers/{code}`
- `WS /ws/markets`

Provider architecture:

- `yfinance`: default provider, used to avoid the failing raw Yahoo quote endpoint
- `mock`: useful for UI development when live data is unavailable
- `tradingview`: reserved provider slot for a future implementation

Ticker management:

- Tracked instruments are stored in [tracked_tickers.json](/Users/guozhen_wu/Documents/vibe-code-test/backend/data/tracked_tickers.json)
- The backend seeds `CL=F` and `GC=F` as the initial tracked tickers
- New tickers can be added from the frontend or by calling the ticker endpoints directly

Current provider note:

- The `yfinance` provider fetches whatever symbols exist in the tracked ticker registry
- The default gold instrument now uses `GC=F`

Key backend folders:

- `app/core/`: settings and shared configuration
- `app/models/`: response models
- `app/providers/`: market data providers and factory
- `app/services/`: polling, state, and orchestration
- `app/api/`: route definitions and shared dependencies

## Frontend

```bash
cd /Users/guozhen_wu/Documents/vibe-code-test/frontend
npm install
npm run dev
```

The frontend starts on `http://127.0.0.1:5173`.

If your API runs somewhere else, start the frontend with:

```bash
VITE_API_BASE=http://127.0.0.1:8000 npm run dev
```

## Alert behavior

- Alerts are stored in browser local storage
- Browser notifications must be allowed by the user
- A rule triggers once when price crosses the threshold, then resets if price moves back across the threshold

Key frontend folders:

- `src/components/`: presentational UI pieces
- `src/composables/`: realtime stream and alert state logic
