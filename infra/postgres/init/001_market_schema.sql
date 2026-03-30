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
            'category', 'commodities'
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
            'category', 'commodities'
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
