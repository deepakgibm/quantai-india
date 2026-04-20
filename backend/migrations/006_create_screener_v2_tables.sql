CREATE TABLE IF NOT EXISTS fundamental_metrics (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(100) NOT NULL UNIQUE,
    market_cap DOUBLE PRECISION,
    pe_ratio DOUBLE PRECISION,
    pb_ratio DOUBLE PRECISION,
    dividend_yield DOUBLE PRECISION,
    debt_to_equity DOUBLE PRECISION,
    roce DOUBLE PRECISION,
    roe DOUBLE PRECISION,
    eps DOUBLE PRECISION,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_fundamental_metrics_symbol ON fundamental_metrics (symbol);

CREATE TABLE IF NOT EXISTS institutional_flows (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(100) NOT NULL,
    deal_date TIMESTAMP NOT NULL,
    client_name VARCHAR(255),
    deal_type VARCHAR(10),
    quantity BIGINT,
    price DOUBLE PRECISION,
    flow_category VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_institutional_flows_symbol ON institutional_flows (symbol);
CREATE INDEX IF NOT EXISTS ix_institutional_flows_deal_date ON institutional_flows (deal_date);
