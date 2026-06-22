# System Overview - QuantAI India

QuantAI India is a production-grade, AI-powered professional trading, backtesting, and analytics platform designed specifically for the Indian stock market. It enables retail traders and quantitative analysts to build, test, and run Smart Beta Multi-Factor trading models, utilize technical scanners (like VCP, Darvas Box, and volume profile), trace institutional flows (FII/DII block deals), and stream live market data with advanced performance.

## Business Domain
- **Geography**: Indian stock markets (primarily National Stock Exchange - NSE).
- **Domain**: Quantitative trading, algorithmic scanners, portfolio intelligence, backtesting simulation, and Smart Beta factor investing.

## User Personas
1. **Retail Active Trader**: Uses the web application to screen momentum stocks, track institutional block deals, review volatility indicators, and consult the AI-advisor for trading setups.
2. **Quantitative Analyst (Quant)**: Develops custom factor models, executes walk-forward optimizations, runs backtests across 20-year daily datasets, and tests machine learning strategies.
3. **SaaS Premium Subscriber**: Enrolls in the Learning Academy (courses, quizzes) and accesses premium AI-generated research newsletters and portfolio intelligence recommendations.

## Main Features
- **Real-Time Market Ingestion**: Low-latency WebSocket integration with Upstox API using binary Protobuf streaming.
- **Factor & Strategy Backtester**: Bar-by-bar historical backtesting simulator supporting multi-factor strategies and walk-forward parameter optimization.
- **Technical & Institutional Scanners**: Heavy-duty algorithms scanning Nifty 500 stocks for volatility contraction patterns (VCP), Darvas Box breakouts, volume profiles, and FII block deals.
- **AI-Powered Analytics**: Conversational prompt interface utilizing the Google Gemini API to analyze market trends, scan stocks, and generate custom trade setups.
- **SaaS Ecosystem**: Integration of Razorpay subscriptions, affiliate broker commission tracking, and a built-in educational Learning Academy.

## Core Workflows

### 1. Real-Time Market Data Flow
```
Upstox WebSocket API ──(Protobuf)──> Ingestion Worker ──> DragonflyDB Cache ──(Pub/Sub)──> FastAPI WebSocket ──> React UI
```
- Ingestion Worker decodes the incoming Protobuf ticks from Upstox and updates the real-time cache in DragonflyDB.
- FastAPI servers receive ticks via Pub/Sub subscriptions and broadcast them to connected frontend clients via WebSockets.

### 2. Signal Generation & Scanner Run
```
PostgreSQL (Daily EOD/Indicators) ──> Scanner Workers ──> Factor Signals ──> PostgreSQL / Cache ──> API ──> UI Dashboard
```
- Daily EOD cron jobs run at 3:30 PM IST (after market close) to parse NSE data, calculate technical indicators (RSI, EMA, MACD, etc.), and persist them to `precomputed_indicators`.
- Active scanners query this data, group them by VCP contractions or breakout thresholds, and cache the results to DragonflyDB for instant UI rendering.

### 3. Backtesting & ML Training Pipeline
```
Web Dashboard ──(API request)──> Celery Queue ──> Celery Worker Pool ──> Backtest Engine ──> Result Cache ──> Web UI
```
- User submits a backtest configuration or requests model training.
- The FastAPI request handler delegates the task to the Celery broker (hosted on DragonflyDB) and returns a task ID.
- Background workers process the backtesting task bar-by-bar, save results in PostgreSQL, and set a completion status in Redis.
- The UI polls for the status and renders the finished equity curves.
