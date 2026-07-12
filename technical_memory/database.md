# Technical Memory: Database Schema & Caching

## 1. Schema Layout (PostgreSQL)

```text
  ┌──────────────┐          ┌───────────────────────┐
  │    users     │          │ precomputed_indicators │
  └──────┬───────┘          └───────────┬───────────┘
         │                              │
         ▼ 1:N                          ▼ N:1
  ┌──────────────┐          ┌───────────────────────┐
  │ watchlists   ├─────────>│      instruments      │
  └──────────────┘          └───────────┬───────────┘
                                        │
                                        ▼ 1:N
                            ┌───────────────────────┐
                            │     stock_candle      │
                            └───────────────────────┘
```

*   `users`: Subscription plan state and credentials.
*   `instruments`: Active symbol master mapped to exchange token IDs.
*   `stock_candle`: Daily OHLCV price series.
*   `precomputed_indicators`: Array of MACD, RSI, and Bollinger values indexed by symbol and date.

## 2. In-Memory Caching (DragonflyDB)
*   **Keys**: Quotes are cached using `price:<symbol>` (TTL: 1-5s).
*   **Pub/Sub**: Ticks decode to channel `ticks:live` to broadcast live pricing.
