# Experiment Lab – How-To Guide

## 1. What is Experiment Lab?

Experiment Lab is a **sandbox environment** for quickly testing and comparing trading ideas before committing to a full backtest.

Think of it as your "strategy workshop" — a place where you can:
- Test different strategy combinations rapidly
- Compare results across multiple symbols
- Tweak parameters and see immediate feedback
- Generate hypotheses to validate with proper backtesting

### Key Differences from Backtest

| Feature | Experiment Lab | Full Backtest |
|---------|----------------|---------------|
| Purpose | Quick exploration | Rigorous validation |
| Speed | Faster iteration | More thorough |
| Scope | Idea testing | Performance measurement |
| Output | Signals & patterns | Full P&L metrics |

> **Note:** Experiment Lab results are indicative. Always validate promising ideas with a proper Backtest and Walk-Forward analysis.

---

## 2. When to Use Experiment Lab

Use Experiment Lab when you want to:

| Scenario | Why Use Experiment Lab? |
|----------|-------------------------|
| Early idea validation | Quickly check if a concept has merit |
| Strategy tuning | Test parameter variations rapidly |
| Symbol screening | Find which stocks work best with a strategy |
| Hypothesis testing | "Does RSI work better on 15m or 1D?" |
| Learning | Understand how indicators behave on real data |

### When to Use Full Backtest Instead
- You need accurate P&L calculations
- You want to measure risk metrics (Sharpe, drawdown)
- You're ready to validate a refined strategy
- You need trade-by-trade analysis

---

## 3. Step-by-Step: Running an Experiment

### Step 1: Add Symbols

**Using Search:**
1. Click the symbol search field
2. Type the stock name or symbol (e.g., "RELIANCE" or "TCS")
3. Click on matching results to add them
4. Selected symbols appear as pills/tags

**Using Quick-Add:**
- Popular symbols are available for one-click addition
- Great for testing on commonly traded stocks

**Multiple Symbols:**
- Add up to 10 symbols for cross-symbol comparison
- Results will show how the strategy performs on each

### Step 2: Select a Strategy

Browse strategies by category:

| Category | Description |
|----------|-------------|
| **Single-Logic Baselines** | Simple, single-indicator strategies |
| **Dual-Indicator Trend** | Two indicators confirming each other |
| **Composite Multi-Signal** | Multiple factors combined |
| **Volatility-Adaptive** | Adjust to market volatility |
| **Pattern-Based** | Price pattern recognition |

Each strategy card shows:
- Strategy name and ID
- Brief description
- Category type

Click to select one or more strategies for comparison.

### Step 3: Modify Parameters (Optional)

Default parameters work for most cases, but you can customize:

- **Indicator periods** — Adjust lookback windows
- **Threshold values** — Change signal sensitivity
- **Filter conditions** — Add or remove confirmations

> **Tip:** Start with defaults, then adjust based on initial results.

### Step 4: Choose Timeframe

Select the candle interval for analysis:

| Timeframe | Use Case |
|-----------|----------|
| **5m** | Intraday, high-frequency signals |
| **15m** | Intraday swing, balanced frequency |
| **30m** | Intraday position, fewer signals |
| **1H** | Swing trading, end-of-day decisions |
| **1D** | Positional trading, daily signals |

> **Note:** Intraday data may have limited history compared to daily data.

### Step 5: Set Date Range

- **Start Date** — Beginning of your test period
- **End Date** — Typically today or a recent date
- **Recommended:** At least 6 months of data for meaningful results

### Step 6: Run the Experiment

Click **"Run Backtest"** to execute.

The system will:
1. Load price data for selected symbols
2. Apply strategy logic to generate signals
3. Simulate trades based on signals
4. Calculate performance metrics
5. Display results in cards

---

## 4. Reading Experiment Results

### Results Overview

Each strategy result shows:

| Metric | What It Means |
|--------|---------------|
| **Total Return %** | Overall profit/loss |
| **Sharpe Ratio** | Risk-adjusted return |
| **Max Drawdown %** | Worst decline from peak |
| **Win Rate %** | Profitable trade percentage |
| **Trade Count** | Number of trades executed |
| **Profit Factor** | Gross profit / gross loss |

### Performance Rating

Strategies are grouped by performance tier:
- 🟢 **Top Performers** — Highest returns and Sharpe
- 🟡 **Moderate** — Decent results, worth investigating
- 🔴 **Underperformers** — May need adjustment or exclusion

### Category Comparison

The category filter shows aggregate performance:
- See which strategy types work best for your symbols
- Identify consistent patterns vs. one-time outliers

### Equity Curve

Expand results to view:
- **Visual growth trajectory** — How capital grows over time
- **Drawdown periods** — When losses occurred
- **Recovery patterns** — How quickly losses were recovered

---

## 5. Experiment Lab vs. Backtest Output

| Aspect | Experiment Lab | Backtest |
|--------|----------------|----------|
| **Signal frequency** | How often signals trigger | Trade-by-trade detail |
| **Directional bias** | Long vs. short tendency | Entry/exit prices |
| **Consistency** | Across symbols/timeframes | Per-trade P&L |
| **Use case** | Quick screening | Final validation |

### What Experiment Lab Shows Well
- Relative strategy comparison
- Symbol suitability screening
- Parameter sensitivity
- Signal frequency patterns

### What Requires Full Backtest
- Accurate P&L calculation
- Precise drawdown analysis
- Trade-level statistics
- Execution timing

---

## 6. How Experiment Lab Fits in Your Workflow

### The Recommended Progression

```
1. Experiment Lab
   ↓
   Quickly test ideas, filter out weak strategies
   ↓
2. Backtest
   ↓
   Validate top candidates with accurate metrics
   ↓
3. Walk-Forward Backtest
   ↓
   Test on unseen data to prevent overfitting
   ↓
4. Paper Trading / Live Monitor
   ↓
   Real-time validation with small capital
   ↓
5. Full Deployment
   ↓
   Scale up with confidence
```

### Don't Skip Steps

| If you skip... | Risk |
|----------------|------|
| Experiment Lab | Waste time backtesting bad ideas |
| Backtest | No accurate P&L or risk metrics |
| Walk-Forward | Overfit to historical data |
| Paper Trading | Unexpected live trading issues |

---

## 7. Tips for Effective Experimentation

### ✅ Do
- Test on multiple symbols to check robustness
- Compare similar strategies (e.g., all trend-following)
- Use consistent date ranges for fair comparison
- Note promising ideas for deeper backtest analysis

### ❌ Avoid
- Over-optimizing parameters on one symbol
- Drawing conclusions from very few trades
- Ignoring max drawdown (return means nothing if you can't survive the dip)
- Testing only on recent data (include older periods)

---

## 8. Common Questions

### "Why are my experiment results different from backtest?"
Experiment Lab and Backtest may use slightly different execution assumptions. Backtest is more rigorous. Use Experiment Lab for screening, Backtest for final validation.

### "How many strategies should I test?"
Start broad (10-20 strategies), then narrow to 3-5 top performers for deeper analysis.

### "What's a good number of trades?"
At least 20-30 trades for statistically meaningful results. Fewer trades = less reliable conclusions.

### "Should I test on one symbol or many?"
Test on multiple symbols. A strategy that only works on one stock may be overfit to that stock's specific behavior.

---

## 9. Next Steps

After finding promising strategies in Experiment Lab:

1. **Run a Full Backtest** — Get accurate metrics
2. **Try Walk-Forward Analysis** — Validate on unseen data
3. **Compare Against Benchmark** — Does it beat Nifty 50?
4. **Document Your Findings** — Track what works and what doesn't

---

*⚠️ This is for educational and simulation purposes only. All results are hypothetical and do not guarantee future performance.*
