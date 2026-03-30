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
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend starts on `http://0.0.0.0:8000` and is reachable from other machines on the same LAN at `http://<your-machine-lan-ip>:8000`.

API client template:

- A standalone Postman collection is available at [postman_collection.json](/Users/guozhen_wu/Documents/vibe-code-test/postman_collection.json)
- When endpoints are added or changed, this collection should be updated alongside the backend routes

Environment variables:

- `MARKET_DATA_PROVIDER=yfinance`
- `MARKET_POLL_INTERVAL_SECONDS=5`

Database direction:

- Postgres is intended to become the source of truth for tracked tickers, aliases, and metadata.
- Redis is intended to hold runtime market state such as the previous completed 5-minute close.
- Initial infrastructure artifacts now exist at:
  - [docker-compose.yml](/Users/guozhen_wu/Documents/vibe-code-test/docker-compose.yml)
  - [001_market_schema.sql](/Users/guozhen_wu/Documents/vibe-code-test/infra/postgres/init/001_market_schema.sql)
  - [redis-key-design.md](/Users/guozhen_wu/Documents/vibe-code-test/docs/redis-key-design.md)

Start the databases locally:

```bash
cd /Users/guozhen_wu/Documents/vibe-code-test
docker compose up -d
```

Default local service addresses:

- Postgres: `postgresql://market_alerts:market_alerts@localhost:5432/market_alerts`
- Redis: `redis://localhost:6379/0`

Endpoints:

- `GET /api/health`
- `GET /api/markets`
- `GET /api/providers`
- `GET /api/sentiment/fear-greed`
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

The frontend starts on `http://0.0.0.0:5173` and is reachable from other machines on the same LAN at `http://<your-machine-lan-ip>:5173`.

If your API runs somewhere else, start the frontend with:

```bash
VITE_API_BASE=http://<your-api-host>:8000 npm run dev
```

By default, the frontend now calls `http://<current-browser-host>:8000`, so when you open the UI from another machine on your LAN it will target the backend on that same host automatically.

Fear & Greed gauge:

- The page now includes a CNN-style Fear & Greed gauge card.
- The frontend fetches it from `GET /api/sentiment/fear-greed`.
- The backend pulls the data from CNN's market sentiment feed and normalizes the current reading plus historical comparison points.

## Alert behavior

- Alerts are stored in browser local storage
- Browser notifications must be allowed by the user
- A rule triggers once when price crosses the threshold, then resets if price moves back across the threshold

Key frontend folders:

- `src/components/`: presentational UI pieces
- `src/composables/`: realtime stream and alert state logic
