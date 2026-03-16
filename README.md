# Realtime Market Alerts

This app is split into:

- `backend/`: Python FastAPI service that polls quotes and pushes realtime updates over websocket
- `frontend/`: Vue 3 app that renders live prices and lets you define browser notification alarms

## Market instruments

- `CL=F`: crude oil futures front month on Yahoo Finance
- `XAUUSD=X`: gold spot priced in USD on Yahoo Finance

## Backend

```bash
cd /Users/guozhen_wu/Documents/vibe-code-test/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The backend starts on `http://127.0.0.1:8000`.

Endpoints:

- `GET /api/health`
- `GET /api/markets`
- `WS /ws/markets`

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
