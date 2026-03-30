# Redis Key Design

This document defines the initial Redis key layout for short-lived market state.

## Goals

- Keep Postgres as the source of truth for tracked tickers and metadata
- Use Redis for fast runtime state shared by polling, APIs, and websocket broadcasting
- Store the previous completed 5-minute reference value per tracked ticker

## Naming Rules

- Prefix keys by domain: `market:`
- Use the internal ticker `code`, not the provider symbol, in Redis keys
- Keep values structured as JSON where multiple fields are stored together

## Core Keys

### Latest Quote

Key:

```text
market:last:{code}
```

Example:

```text
market:last:CL
market:last:GC
```

Suggested value:

```json
{
  "code": "CL",
  "provider": "yfinance",
  "provider_symbol": "CL=F",
  "price": 101.41,
  "previous_close": 100.98,
  "change": 0.43,
  "change_percent": 0.43,
  "market_state": "REGULAR",
  "timestamp": "2026-03-30T13:55:45Z"
}
```

TTL:

- Optional
- Usually no TTL if this is the current shared quote cache

### Previous Completed 5-Minute Close

Key:

```text
market:ref:5m:prev_close:{code}
```

Example:

```text
market:ref:5m:prev_close:CL
market:ref:5m:prev_close:GC
```

Suggested value:

```json
{
  "code": "CL",
  "price": 101.08,
  "bar_closed_at": "2026-03-30T13:50:00Z",
  "source_timestamp": "2026-03-30T13:55:00Z"
}
```

Meaning:

- This is the close of the previous completed 5-minute bar
- It is not just “the price from five minutes ago”

TTL:

- No TTL required
- Overwrite on each new completed 5-minute bar

## Optional Supporting Keys

### Current 5-Minute Bar Snapshot

Key:

```text
market:bar:5m:current:{code}
```

Use when the app later needs live 5-minute bar construction.

### Pub/Sub Channel

Channel:

```text
market:updates
```

Use when multiple backend instances need shared quote fanout.

Message shape:

```json
{
  "code": "GC",
  "event": "quote_updated",
  "timestamp": "2026-03-30T13:55:45Z"
}
```

## Why This Split

- Postgres stores durable instrument data:
  - tracked ticker definitions
  - aliases
  - display metadata
  - provider mappings
- Redis stores fast-changing runtime state:
  - latest quote
  - previous completed 5-minute close
  - later pub/sub and short rolling caches

## Recommended Access Pattern

1. Read active tracked tickers from Postgres
2. Poll provider data using `provider_symbol`
3. Write latest quote to `market:last:{code}`
4. When a 5-minute bar closes, write the completed bar close to `market:ref:5m:prev_close:{code}`
5. Build websocket payloads from Redis runtime state plus Postgres ticker metadata when needed
