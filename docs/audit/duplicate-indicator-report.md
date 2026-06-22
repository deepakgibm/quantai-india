# QuantAI Duplicate Indicator Report

This report highlights duplicated technical indicator calculations across the backend and outlines recommendations for consolidation into a single master module.

## 1. Relative Strength Index (RSI) Duplication

### File A: `backend/core/scanner/indicator_utils.py` (Lines 21-31)
```python
def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
```

### File B: `backend/services/breakout_detector.py` (Lines 110-119)
```python
delta = df.groupby('symbol')['close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = df.groupby('symbol')['close'].transform(lambda x: x.diff().clip(lower=0).rolling(14).mean())
avg_loss = df.groupby('symbol')['close'].transform(lambda x: (-x.diff()).clip(lower=0).rolling(14).mean())
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))
```

### Differences:
* **Series vs. Multi-symbol DataFrame**: File A computes RSI on a single-symbol pandas Series using Exponential Weighted Moving Averages (EMA). File B computes RSI on a multi-symbol DataFrame using a rolling simple mean (`rolling(14).mean()`) grouped by symbol.
* **Math Divergence**: Rolling simple mean RSI (File B) produces different momentum thresholds than Wilder's standard EMA RSI (File A).

### Recommendation:
* Update `indicator_utils.py` to support both single Series and grouped Multi-index DataFrames.
* Standardize the calculations so that all modules consume the Wilder's EMA RSI formula.

---

## 2. Average True Range (ATR) Duplication

### File A: `backend/core/scanner/indicator_utils.py` (Lines 99-105)
```python
def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()
```

### File B: `backend/services/breakout_detector.py` (Lines 101-105)
```python
df['tr'] = pd.concat([h_l, h_pc, l_pc], axis=1).max(axis=1)
df['atr_20d'] = df.groupby('symbol')['tr'].transform(lambda x: x.rolling(window=20, min_periods=1).mean())
df['atr_5d'] = df.groupby('symbol')['tr'].transform(lambda x: x.rolling(window=5, min_periods=1).mean())
```

### Differences:
* File B inline calculates True Range (TR) and uses `groupby().transform()` for rolling ATR on 20-day and 5-day periods, instead of reusing the modular `atr()` function in `indicator_utils.py`.

### Recommendation:
* Refactor the `atr` utility function in `indicator_utils.py` to accept custom windows and group-aware execution, and import it into `breakout_detector.py`.

---

## 3. Duplicate Indicator Engines: DuckDB vs. Pandas

### File A: `backend/core/duckdb_indicators.py` (Lines 30-77)
Calculates RSI, ATR, and MACD inside DuckDB using window SQL functions:
```sql
100.0 - (100.0 / (1.0 + NULLIF(avg_gain / NULLIF(avg_loss, 0), 0))) AS rsi_14
```

### File B: `backend/core/scanner/indicator_utils.py`
Calculates them using pandas.

### Differences:
* DuckDB calculations use standard averages (`AVG() OVER w14`) which approximate Wilder's EMA but differ mathematically from the exact recursive pandas `.ewm()` formula, leading to minor signal differences in the backtest engine vs. active scanners.

### Target Consolidated Implementation:
Define a single source of truth for formula specifications, and add verification tests (`tests/test_indicators_consistency.py`) to confirm that DuckDB-computed indicators match the Pandas Series formulas within a 0.05% tolerance threshold.
