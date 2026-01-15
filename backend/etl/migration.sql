select distinct symbol,instrument_key  from stock_candles;

SELECT distinct m.instrument_key,m.symbol from stock_master m inner join stock_candles c on m.instrument_key=c.instrument_key
  
FROM stock_master;

select * from instrument_master

INSERT INTO instrument_master (
    symbol, series, exchange,
    company_name, sector, isin_code,
    instrument_key, is_active
)
SELECT
    symbol, series, exchange,
    company_name, sector, isin_code,
    instrument_key, is_active
FROM stock_master;


CREATE TABLE stock_candle_2026_01
PARTITION OF stock_candle
FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE INDEX idx_candle_lookup
ON stock_candle (instrument_id, timeframe, candle_ts DESC);

CREATE INDEX idx_candle_ts
ON stock_candle (candle_ts DESC);

CREATE TABLE stock_candle (
    instrument_id BIGINT NOT NULL,
    timeframe SMALLINT NOT NULL,        -- minutes: 1,5,15,60,1440
    candle_ts TIMESTAMP NOT NULL,

    open  NUMERIC(12,4),
    high  NUMERIC(12,4),
    low   NUMERIC(12,4),
    close NUMERIC(12,4),
    volume BIGINT,

    PRIMARY KEY (instrument_id, timeframe, candle_ts),
    FOREIGN KEY (instrument_id) REFERENCES instrument_master(instrument_id)
)
PARTITION BY RANGE (candle_ts);



CREATE TABLE instrument_master (
    instrument_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    symbol TEXT NOT NULL,
    series VARCHAR(10) NOT NULL,
    exchange VARCHAR(10) NOT NULL DEFAULT 'NSE',

    company_name TEXT NOT NULL,
    sector TEXT NOT NULL,
    isin_code VARCHAR(20) NOT NULL,

    instrument_key TEXT UNIQUE,
    is_active BOOLEAN DEFAULT true,

    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),

    CONSTRAINT uq_instrument UNIQUE (symbol, series, exchange)
);



INSERT INTO stock_candle_new (
    instrument_id, timeframe, candle_ts,
    open, high, low, close, volume
)
SELECT
    im.instrument_id,
    tm.timeframe_minutes,
    sc.timestamp::timestamp,
    sc.open, sc.high, sc.low, sc.close,
    sc.volume::bigint
FROM stock_candles sc
JOIN instrument_master im
    ON sc.instrument_key = im.instrument_key
JOIN timeframe_mapping tm
    ON sc.timeframe = tm.timeframe_text;


	CREATE TABLE timeframe_mapping (
    timeframe_text TEXT PRIMARY KEY,
    timeframe_minutes SMALLINT NOT NULL
);

INSERT INTO timeframe_mapping (timeframe_text, timeframe_minutes) VALUES
('1m', 1),
('3m', 3),
('5m', 5),
('10m', 10),
('15m', 15),
('30m', 30),
('1h', 60),
('2h', 120),
('4h', 240),
('1d', 1440);

SELECT DISTINCT sc.timeframe
FROM stock_candles sc
LEFT JOIN timeframe_mapping tm
    ON sc.timeframe = tm.timeframe_text
WHERE tm.timeframe_text IS NULL;


INSERT INTO stock_candle_new (
    instrument_id, timeframe, candle_ts,
    open, high, low, close, volume
)
SELECT
    im.instrument_id,
    tm.timeframe_minutes,
    sc.timestamp::timestamp,
    sc.open, sc.high, sc.low, sc.close,
    sc.volume::bigint
FROM stock_candles sc
JOIN instrument_master im
    ON sc.instrument_key = im.instrument_key
JOIN timeframe_mapping tm
    ON sc.timeframe = tm.timeframe_text;

54745889
select count(*) from stock_candle

BEGIN;
ALTER TABLE stock_candle RENAME TO stock_candle_old;
ALTER TABLE stock_candle_new RENAME TO stock_candle;
COMMIT;
