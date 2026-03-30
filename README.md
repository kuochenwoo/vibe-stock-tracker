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
- `POSTGRES_DSN=postgresql://market_alerts:market_alerts@localhost:5432/market_alerts`
- `POSTGRES_SCHEMA_PATH=../infra/postgres/init/001_market_schema.sql`
- `REDIS_URL=redis://localhost:6379/0`

Database layout:

- Postgres is now the backend source of truth for tracked tickers, aliases, and metadata.
- Redis now stores runtime market cache values, including the latest quote snapshot and the previous completed 5-minute close.
- Supporting artifacts:
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
- `GET /api/markets/{code}/history`
- `GET /api/providers`
- `GET /api/sentiment/fear-greed`
- `GET /api/tickers`
- `POST /api/tickers`
- `DELETE /api/tickers/{code}`
- `GET /api/preferences/panel-order`
- `PUT /api/preferences/panel-order`
- `GET /api/alerts`
- `POST /api/alerts`
- `DELETE /api/alerts/{alert_id}`
- `WS /ws/markets`

Provider architecture:

- `yfinance`: default provider, used to avoid the failing raw Yahoo quote endpoint
- `mock`: useful for UI development when live data is unavailable
- `tradingview`: reserved provider slot for a future implementation

Ticker management:

- Tracked instruments are stored in Postgres table `tracked_tickers`
- Aliases are stored in Postgres table `ticker_aliases`
- The schema seeds `CL` -> `CL=F` and `GC` -> `GC=F` as the initial tracked tickers
- New tickers can be added from the frontend or by calling the ticker endpoints directly

Current provider note:

- The `yfinance` provider fetches whatever symbols exist in the tracked ticker registry
- The default gold instrument now uses `GC=F`
- The backend writes latest quotes to Redis key `market:last:{code}`
- The backend writes the previous completed 5-minute close to Redis key `market:ref:5m:prev_close:{code}`
- The backend also seeds `1d / 5m` chart history to Redis key `market:history:1d:5m:{code}`
- Session-aware chart seeding defaults are:
  - futures: `18:00` `America/New_York`
  - crypto: `00:00` `UTC`
  - stocks: `04:00` `America/New_York` to include pre-market, regular session, post-market, and overnight context
- These session defaults can be overridden later through ticker metadata

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

- Alerts are stored in Postgres and survive page refreshes
- Browser notifications must be allowed by the user
- A rule triggers once when price crosses the threshold, then resets if price moves back across the threshold
- The frontend still evaluates live trigger state in the browser against the websocket market stream

## Chart seeding

- Price panels now seed their `1D` line from `GET /api/markets/{code}/history`
- The backend fetches raw `5d / 5m` intraday data from `yfinance`, applies an asset-aware session start, and returns the active session window
- The frontend then merges websocket prices into the latest 5-minute bucket so the chart stays live after the initial seed

Key frontend folders:

- `src/components/`: presentational UI pieces
- `src/composables/`: realtime stream and alert state logic
