CREATE TABLE IF NOT EXISTS market_data_quarantine (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    timeframe VARCHAR(10),
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_market_data_quarantine_id ON market_data_quarantine (id);
CREATE INDEX IF NOT EXISTS ix_market_data_quarantine_symbol ON market_data_quarantine (symbol);
