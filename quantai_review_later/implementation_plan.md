# Nifty 100 Daily Data Pipeline

## Goal Description
Create a robust data pipeline to maintain a 20-year history of daily OHLCV data for Nifty 100 stocks. The initial 20-year history will be backfilled using Yahoo Finance (`yfinance`), and subsequent daily updates will be fetched via the Upstox API to ensure consistency with the trading platform. This data will serve as the foundation for machine learning models.

## User Review Required
> [!IMPORTANT]
> **Data Source Switch**: The system will use `yfinance` for the initial 20-year backfill but will switch to `Upstox` for all future updates. This ensures we have a long history without exhausting Upstox rate limits, while keeping recent data aligned with the execution broker.

## Proposed Changes

### Database Models
#### [NEW] [models_ml.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/models_ml.py)
- Create `Nifty100Daily` model:
    - `symbol` (String, Indexed)
    - `timestamp` (DateTime, Indexed)
    - `open`, `high`, `low`, `close`, `volume` (Float/Integer)
    - `source` (String) - to track 'yfinance' vs 'upstox'
    - Composite index on `(symbol, timestamp)`

#### [MODIFY] [models.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/models.py)
- Import `Nifty100Daily` to ensure it's registered with SQLAlchemy `Base`.

### ETL Scripts
#### [NEW] [nifty100_initial_loader.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/etl/nifty100_initial_loader.py)
- Script to:
    1. Fetch Nifty 100 symbol list (hardcoded or scraped).
    2. Download 20 years of daily data for each symbol using `yfinance`.
    3. Bulk insert into `nifty100_daily` table.
    4. Log progress to `ETLLog`.

#### [NEW] [daily_update_loader.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/etl/daily_update_loader.py)
- Script to:
    1. Identify the last available date for each symbol in `nifty100_daily`.
    2. Fetch missing daily candles from Upstox API.
    3. Append new data to the table.

### Configuration
#### [MODIFY] [config.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/config.py)
- Add `NIFTY_100_SYMBOLS` list (or path to CSV).

## Verification Plan

### Automated Tests
- **Import Test**: Verify `yfinance` can fetch data.
- **Database Test**: Verify data can be inserted and queried from `nifty100_daily`.
- **Switchover Test**: Verify `daily_update_loader.py` correctly identifies the gap after the `yfinance` load and fetches only the missing days from Upstox.

### Manual Verification
- Run `nifty100_initial_loader.py` and check the System Status UI (ETL logs).
- Inspect the database to confirm 20 years of data exists for a sample stock (e.g., RELIANCE).
