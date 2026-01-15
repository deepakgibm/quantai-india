CREATE TABLE stock_master (
    id BIGSERIAL PRIMARY KEY,

    company_name TEXT NOT NULL,
    sector TEXT NOT NULL,                 -- Renamed from industry → sector
    symbol TEXT NOT NULL,
    series VARCHAR(10) NOT NULL,          -- EQ, BE, etc.
    isin_code VARCHAR(12) NOT NULL,

    exchange VARCHAR(10) DEFAULT 'NSE',
    instrument_key TEXT,                  -- Upstox instrument_key

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT uq_stock_isin UNIQUE (isin_code),
    CONSTRAINT uq_stock_symbol_series UNIQUE (symbol, series)
);

CREATE INDEX idx_stock_master_sector
ON stock_master (sector);

CREATE INDEX idx_stock_master_symbol
ON stock_master (symbol);

CREATE INDEX idx_stock_master_instrument_key
ON stock_master (instrument_key);


commit;