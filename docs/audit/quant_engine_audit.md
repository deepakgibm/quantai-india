# QuantAI Quant Engine Audit

This report analyzes technical indicator calculations, stock screening engines, and backtesting simulation loops, identifying bottlenecks and opportunities for performance improvements.

---

## 1. Loop-Based Indicator Calculations

*   **Vulnerability**: In [backend/workers/indicator_worker.py:179](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/workers/indicator_worker.py#L179) and line 192, core indicators like EMA and RSI are computed using custom Python loops.
*   **Impact**: Python loops are slow and block the thread, preventing parallel scaling. Under load, these calculations saturate the CPU cores.
*   **Vectorization Recommendation**: Standardize on **TA-Lib** (compiled C library) or vectorized **NumPy** calculations:
    ```python
    # Optimized NumPy RSI
    def numpy_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        rs = up / down
        rsi = np.zeros_like(prices)
        rsi[:period] = 100. - 100. / (1. + rs)
        # Smooth with Wilder's EMA
        # ...
        return rsi
    ```

---

## 2. Sequential Symbol Scanning Bottlenecks

*   **Vulnerability**: In `MeanReversionScanner.scan_all()`, the engine loops over all symbol dataframes in Python, running `analyze_stock(symbol, df)` sequentially.
*   **Impact**: Heavy CPU usage. Offloading this loop using `multiprocessing.Pool` helps bypass the GIL but introduces process serialization overhead.
*   **Vectorization Recommendation**: Replace Pandas and Python loops with **Polars**. Polars is built in Rust and supports multi-threaded group-by operations, allowing indicators to be computed across the entire universe in a single pass:
    ```python
    import polars as pl

    # Grouped RSI calculation in Polars
    def polars_bulk_rsi(df: pl.DataFrame, period: int = 14) -> pl.DataFrame:
        return df.with_columns([
            pl.col("close").diff().alias("diff")
        ]).with_columns([
            pl.when(pl.col("diff") > 0).then(pl.col("diff")).otherwise(0.0).alias("gain"),
            pl.when(pl.col("diff") < 0).then(-pl.col("diff")).otherwise(0.0).alias("loss")
        ]).with_columns([
            pl.col("gain").ewm_mean(com=period - 1).alias("avg_gain"),
            pl.col("loss").ewm_mean(com=period - 1).alias("avg_loss")
        ]).with_columns([
            (100 - (100 / (1 + pl.col("avg_gain") / pl.col("avg_loss")))).alias("rsi_14")
        ])
    ```

---

## 3. Backtest Engine Data Copying

*   **Vulnerability**: The backtesting loop in `core/backtest/engine.py` calls `get_history(lookback=200)` on every bar iteration to evaluate strategy rules.
*   **Impact**: Creating a dataframe copy on every bar is highly inefficient. For a 1-minute dataset with 375,000 candles, copying the dataframe 375,000 times introduces significant memory allocation overhead.
*   **Fix Recommendation**: Use **index-based slicing** on a single consolidated NumPy array or Polars DataFrame instead of copying dataframes:
    ```python
    # Instead of df.iloc[i-200:i], use array views:
    close_slice = close_array[i-200:i]
    ```
