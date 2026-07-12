# Technical Memory: Scanner Engine

## 1. Scanner Strategies

The platform implements three primary scanner engines:

1.  **VCP (Volatility Contraction Pattern)**: Implements Minervini's 8 Trend Template rules (e.g. price > SMA150 > SMA200, SMA200 rising, price within 25% of 52-week high, RSI > 70).
2.  **Week 52 Breakouts**: Fast DB-driven scanning utilizing `Week52BreakoutService` to isolate new highs (`52W_HIGH`) or new lows (`52W_LOW`) mapped against volume ratios.
3.  **Sector Heatmap**: Computes performance index metrics for 94 distinct sectors. Weighted by stock market capitalization to represent a real picture of market breadth.
