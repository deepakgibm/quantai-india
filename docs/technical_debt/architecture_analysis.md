# Strategy + ML Training Architecture Analysis

**Role**: Principal Quant Architect + ML Systems Designer
**Date**: 2026-02-05
**Scope**: Design & Decision Analysis Only

---

## Hardware Profile (Local Development Machine)

| Component | Specification |
|:---|:---|
| **GPU** | NVIDIA GeForce RTX 5050 Laptop (8GB VRAM, Compute 12.0) |
| **CPU** | 13th Gen Intel Core i7 |
| **RAM** | 16 GB |
| **Driver** | 573.13 |

---

## 1. Executive Summary

**Current State**: A PostgreSQL-centric system holding ~50GB of OHLCV data for 500 stocks (2022-2026). Suitable for dashboards but suboptimal for ML training and backtesting.

**Core Problem**: Using a transactional database for analytical workloads creates I/O bottlenecks, storage bloat, and compute waste. Real-time inference adds latency constraints.

**Recommended Architecture**: A **three-tier hybrid model**:

| Tier | Technology | Purpose |
|:---|:---|:---|
| **Live** | DragonflyDB + WebSocket | Real-time ticks, inference state |
| **Hot** | PostgreSQL | Recent 30 days, user data, orders |
| **Warm/Cold** | Parquet on SSD | Historical data, pre-computed features |

**Key Shifts**:
1.  **Compute-Once, Read-Many**: Pre-calculate indicators into static Parquet files.
2.  **Sector-Level Models**: Train 10-12 models instead of 500.
3.  **Event-Driven Inference**: Trigger ML prediction only on price change events, not polling.
4.  **GPU-Accelerated Deep Learning (Optional)**: With RTX 5050, small LSTM/Transformer models are feasible for experimentation.

**Cost Impact**: Estimated 60-80% reduction in storage costs, 90%+ reduction in ML training compute via feature reuse, sub-50ms real-time inference latency.

---

## 2. Current System Pain Points

| Category | Observed/Implied Issue | Cost/Performance Impact |
|:---|:---|:---|
| **Storage** | Single PostgreSQL for all data (50GB) | High SSD cost for transactional storage; inefficient for bulk analytical reads. |
| **Compute** | Indicators recomputed per query/backtest | CPU/electricity waste; slow iteration cycles. |
| **I/O** | Row-based reads for column-centric analysis | Reads entire rows when only `Close` column needed; wasted bandwidth. |
| **Contention** | ML training shares DB with dashboard | Heavy queries block real-time UI responsiveness. |
| **Real-Time** | No clear inference pipeline | Unclear how live WebSocket data feeds into ML models for live scoring. |
| **Governance** | No model versioning/registry | Risk of "zombie models" running in production without oversight. |

---

## 3. Recommended High-Level Architecture

### Conceptual Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          OPERATIONAL PLANE                              │
│  [Upstox WebSocket] ──► [Tick Processor] ──► [DragonflyDB Ring Buffer]  │
│                                │                      │                 │
│                                ▼                      ▼                 │
│                      [PostgreSQL (Hot 30d)]   [Inference Engine]        │
│                                                       │                 │
│                                                       ▼                 │
│                                              [Signal Confidence API]    │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                        ┌─────────────┴─────────────┐
                        ▼                           ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│       RESEARCH PLANE            │   │       TRAINING PLANE            │
│  [Parquet Feature Store]        │   │  [Parquet Feature Store]        │
│  [Backtest Engine (Vectorized)] │   │  [ML Training Jobs (Batch)]     │
│  [Experiment Tracker (SQLite)]  │   │  [Model Registry (Files/DB)]    │
│                                 │   │  [GPU Training: LSTM/Transformer]│
└─────────────────────────────────┘   └─────────────────────────────────┘
```

### Data Format Recommendations

| Use Case | Format | Rationale |
|:---|:---|:---|
| **Real-Time Ticks** | In-Memory (DragonflyDB) | Sub-ms access; volatile is acceptable. |
| **Recent Candles (30d)** | PostgreSQL | Transactional integrity for UI; indexed queries. |
| **Historical OHLCV** | Parquet (Snappy) | 5-10x compression; columnar for fast scans. |
| **Pre-Computed Features** | Parquet (per-symbol files) | Eliminates re-calculation; direct load into Polars/Pandas. |
| **ML Training Input** | Arrow/Parquet | Zero-copy memory mapping; GPU-friendly. |

---

## 4. Walk-Forward Backtest Design (Conceptual)

**Objective**: Realistic simulation without look-ahead bias, at high speed.

### Architecture Pattern: "The Sliding Window Generator"

**Phase 1: Data Preparation (One-Time, Offline)**
*   Export all history to Parquet, partitioned by symbol.
*   Pre-compute base features (SMA, EMA, RSI, MACD, ATR) for all symbols.
*   **Cost Justification**: Polars processes 500 stocks x 4 years in ~30 seconds.

**Phase 2: Window Iteration (Runtime)**
*   Load pre-computed feature Parquet into memory (Arrow memory-mapping if RAM is tight).
*   Generator yields `(train_start_idx, train_end_idx, test_end_idx)` tuples.
*   Strategy logic receives a slice view, not a data copy.

**What NOT to Do**: Query PostgreSQL inside the backtest loop.

---

## 5. Strategy Experiment Lab Design (Conceptual)

**Objective**: Fast iteration, reproducibility, and cost control.

### Core Components
1.  **Experiment Configuration Store**: `experiment_id` = SHA256 hash of (strategy_name, param_dict, data_version).
2.  **Artifact Store**: `/experiments/{experiment_id}/metrics.json`, `equity_curve.parquet`.
3.  **Deduplication Logic**: Check if experiment already exists before running.

### Integration with ML Signal Confidence
*   Strategies consume ML model output as a feature column in the Parquet file.
*   Keeps the Lab decoupled from the training pipeline.

---

## 6. Price Forecasting & Real-Time Signal Confidence (Decision Matrix)

### Model Approach Comparison (Updated for RTX 5050)

| Approach | Training Cost | Inference Speed | Suitability | RTX 5050 Viability | Recommendation |
|:---|:---|:---|:---|:---|:---|
| **XGBoost/LightGBM** | Low (CPU) | <1ms | High | N/A (CPU) | ✅ **Primary choice** |
| **Small LSTM** (2-layer, 128 hidden) | Medium (GPU) | 10-30ms | Medium | ✅ **Feasible** | ✅ Experimental |
| **Small Transformer** (4-layer, 256 dim) | Medium-High (GPU) | 20-50ms | Medium | ⚠️ Tight (3-5GB) | ⚠️ Experimental |
| **Large Transformer** (12+ layers) | Very High | 50-100ms | Low | ❌ OOM Risk | ❌ Avoid |
| **Linear (Ridge/Lasso)** | Very Low | Instant | Medium | N/A | ✅ Baseline |

### GPU Deep Learning Guidelines (RTX 5050, 8GB VRAM)

| Parameter | Recommended Value | Rationale |
|:---|:---|:---|
| **Model Type** | 2-layer LSTM or 4-layer Transformer | Fits in 8GB VRAM. |
| **Sequence Length** | 20-60 time steps | >100 explodes memory. |
| **Batch Size** | 32-64 | Reduce if OOM. |
| **Hidden Dim** | 128-256 | >512 is risky. |
| **Training Time** | 10-30 mins/model | Acceptable for research. |
| **Scope** | **Sector-Level** (10-12 models) | Avoids per-symbol overfitting. |

### Model Scope Strategy

| Strategy | # Models | Training Cost | Generalization | Recommendation |
|:---|:---|:---|:---|:---|
| **Per-Symbol Model** | 500 | Very High | Low (overfits) | ❌ Avoid. |
| **Global Model (Stock Embedding)** | 1 | Low | **High** | ✅ Best for cost. |
| **Sector-Level Model** | 10-12 | Low-Medium | High | ✅ **Recommended for LSTM.** |

### Prediction Target Analysis

| Target | Recommendation |
|:---|:---|
| `Close Price` | ❌ Never model directly. |
| `Log Returns` | ⚠️ Acceptable, but noisy. |
| `Direction (1/0)` | ✅ Good. Classification is easier. |
| `Probability(Return > X%)` | ✅ **Best.** Outputs confidence directly. |

### Real-Time Inference Pipeline

1.  **WebSocket Tick Arrives**.
2.  **State Lookup (DragonflyDB)**: Fetch last N prices from ring buffer.
3.  **On-Demand Feature Calc**: Compute features for latest row only.
4.  **Inference**: XGBoost (<1ms) or LSTM (10-30ms).
5.  **Publish**: `{"symbol": "RELIANCE", "signal": "BUY", "confidence": 72}`.

**Latency Budget**: < 50ms total (XGBoost preferred for lowest latency).

---

## 7. AI Training Control Strategy

### Separation of Environments

| Environment | Purpose | Output |
|:---|:---|:---|
| **Research/Sandbox** | Experimentation | Metrics, Notebooks |
| **Production Training** | Certified model builds | Model Artifacts to Registry |
| **Production Inference** | Live scoring via WebSocket | Real-time Signal API |

### Retraining Governance

| Trigger Type | Condition | Action |
|:---|:---|:---|
| **Scheduled** | Weekly (Sunday night) | Full retrain. |
| **Drift-Based** | Realized RMSE > Expected RMSE + 2 std | Champion/Challenger evaluation. |
| **Manual** | After major market event | Ad-hoc retrain. |

### Cost-Aware Controls
*   **Feature Freeze**: Pre-compute features daily.
*   **Early Stopping**: Stop after 5 epochs without improvement.
*   **GPU for LSTM, CPU for XGBoost**: Right-size compute.

---

## 8. Cost Optimization Summary

| Decision | Cost Reduction | Trade-Off / Risk |
|:---|:---|:---|
| **Move History to Parquet** | **High** | Requires daily ETL sync. |
| **Pre-Compute Features Offline** | **High** | Features stale until next ETL. |
| **Global/Sector ML Models** | **Very High** | May miss niche alpha. |
| **Event-Driven Inference** | **Medium** | Requires robust state management. |
| **Sector-Level LSTMs (GPU)** | **Medium** | 10-12 models vs 500. Trades off per-stock specificity. |
| **Use XGBoost for Real-Time** | **High** | <1ms latency. LSTM adds 10-30ms. |

---

## 9. What NOT to Build (Anti-Patterns)

| Anti-Pattern | Why It Fails | What to Do Instead |
|:---|:---|:---|
| **Real-time retraining** | Extremely expensive. | Retrain weekly or on drift. |
| **Per-symbol LSTM models** | 500 models, each overfitting. | Global/Sector model. |
| **Large Transformer (12+ layers)** | Exceeds 8GB VRAM, OOM. | Small 4-layer Transformer max. |
| **Feature computation in SQL** | Slow, hard to debug. | Python/Polars, save to Parquet. |
| **Predicting raw Close price** | Non-stationary target. | Predict directional probability. |
| **Always-on inference polling** | Wasteful. | Event-driven: infer on tick. |

---

**Final Verdict**: The architecture uses PostgreSQL for operational data, Parquet for analytics, and DragonflyDB for real-time state. With RTX 5050, sector-level LSTMs are feasible as an experimental enhancement to the primary XGBoost pipeline.
