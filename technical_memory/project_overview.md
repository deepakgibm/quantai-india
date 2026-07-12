# Technical Memory: Project Overview

## 1. Purpose & Vision
QuantAI India is a production-grade, high-performance quantitative trading, backtesting, and analytics platform designed specifically for the Indian stock market. It aims to empower retail traders and analysts with institutional-grade technical scanning (VCP, breakout channels, volume profiles) and machine-learning driven consensus research.

## 2. Business Domain & Focus
*   **Primary Exchange**: National Stock Exchange of India (NSE).
*   **Core Concepts**: Smart Beta multi-factor strategies, swing-trading breakout detection, real-time index weightings, volatility contraction cycles, FII/DII institutional deal flow monitoring.

## 3. System Workflows
1.  **Ingestion & Live Feed**: WebSocket connections pull Protobuf ticks from Upstox, updates in-memory cache inside DragonflyDB, and pushes changes via Redis Pub/Sub channels to FastAPI WebSockets.
2.  **Indicators & EOD Processing**: celerebeat schedulers query Postgres historical tables at market close to compute RSI, MACD, and EMA arrays, storing them in `precomputed_indicators`.
3.  **Algorithmic Scanning**: Active query executors process stock candle statistics to identify Minervini trend contractions and 52-week breakout events.
