CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE IF NOT EXISTS tracked_tickers (
    id BIGSERIAL PRIMARY KEY,
    code CITEXT NOT NULL UNIQUE,
    provider VARCHAR(64) NOT NULL,
    provider_symbol VARCHAR(128) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    asset_type VARCHAR(64),
    exchange VARCHAR(128),
    currency VARCHAR(32),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT tracked_tickers_provider_symbol_unique UNIQUE (provider, provider_symbol)
);

CREATE INDEX IF NOT EXISTS idx_tracked_tickers_is_active
    ON tracked_tickers (is_active);

CREATE INDEX IF NOT EXISTS idx_tracked_tickers_metadata
    ON tracked_tickers
    USING GIN (metadata);

CREATE TABLE IF NOT EXISTS ticker_aliases (
    id BIGSERIAL PRIMARY KEY,
    ticker_id BIGINT NOT NULL REFERENCES tracked_tickers(id) ON DELETE CASCADE,
    alias CITEXT NOT NULL,
    alias_type VARCHAR(64) NOT NULL DEFAULT 'general',
    source VARCHAR(64),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ticker_aliases_unique_per_type UNIQUE (ticker_id, alias, alias_type),
    CONSTRAINT ticker_aliases_alias_type_not_blank CHECK (char_length(trim(alias_type)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_ticker_aliases_alias
    ON ticker_aliases (alias);

CREATE INDEX IF NOT EXISTS idx_ticker_aliases_ticker_id
    ON ticker_aliases (ticker_id);

CREATE TABLE IF NOT EXISTS app_preferences (
    preference_key TEXT PRIMARY KEY,
    value JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_rules (
    id UUID PRIMARY KEY,
    ticker_code CITEXT NOT NULL REFERENCES tracked_tickers(code) ON DELETE CASCADE,
    direction VARCHAR(16) NOT NULL,
    threshold NUMERIC(18, 6) NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT alert_rules_direction_check CHECK (direction IN ('above', 'below'))
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_ticker_code
    ON alert_rules (ticker_code);

CREATE TABLE IF NOT EXISTS ticker_daily_bars (
    id BIGSERIAL PRIMARY KEY,
    ticker_code CITEXT NOT NULL REFERENCES tracked_tickers(code) ON DELETE CASCADE,
    trading_date DATE NOT NULL,
    open NUMERIC(18, 6) NOT NULL,
    high NUMERIC(18, 6) NOT NULL,
    low NUMERIC(18, 6) NOT NULL,
    close NUMERIC(18, 6) NOT NULL,
    volume NUMERIC(20, 2),
    source VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ticker_daily_bars_unique UNIQUE (ticker_code, trading_date)
);

CREATE INDEX IF NOT EXISTS idx_ticker_daily_bars_ticker_code_date
    ON ticker_daily_bars (ticker_code, trading_date DESC);

CREATE TABLE IF NOT EXISTS truth_social_posts (
    id TEXT PRIMARY KEY,
    author_handle TEXT NOT NULL,
    author_display_name TEXT,
    source_url TEXT,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_truth_social_posts_author_published
    ON truth_social_posts (author_handle, published_at DESC);

INSERT INTO tracked_tickers (
    code,
    provider,
    provider_symbol,
    display_name,
    asset_type,
    exchange,
    currency,
    metadata
)
VALUES
    (
        'CL',
        'yfinance',
        'CL=F',
        'Crude Oil Futures',
        'futures',
        'NYMEX',
        'USD',
        jsonb_build_object(
            'sector', 'energy',
            'category', 'commodities',
            'asset_type', 'futures',
            'session_timezone', 'America/New_York',
            'session_start', '18:00'
        )
    ),
    (
        'GC',
        'yfinance',
        'GC=F',
        'Gold Futures',
        'futures',
        'COMEX',
        'USD',
        jsonb_build_object(
            'sector', 'metals',
            'category', 'commodities',
            'asset_type', 'futures',
            'session_timezone', 'America/New_York',
            'session_start', '18:00'
        )
    )
ON CONFLICT (code) DO NOTHING;

INSERT INTO ticker_aliases (ticker_id, alias, alias_type, source)
SELECT id, 'CL=F', 'provider_symbol', 'seed'
FROM tracked_tickers
WHERE code = 'CL'
ON CONFLICT (ticker_id, alias, alias_type) DO NOTHING;

INSERT INTO ticker_aliases (ticker_id, alias, alias_type, source)
SELECT id, 'GC=F', 'provider_symbol', 'seed'
FROM tracked_tickers
WHERE code = 'GC'
ON CONFLICT (ticker_id, alias, alias_type) DO NOTHING;
