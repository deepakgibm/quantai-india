# Backtest Page – How-To Guide

## 1. What is Backtesting?

Backtesting is a way to test your trading strategy using **past market data** before risking real money.

Think of it like a "practice run" — you simulate how your strategy would have performed during a specific historical period. The system executes all the buy and sell signals your strategy would have generated and calculates the resulting profit or loss.

### Key Points
- **No real money** is involved — it's purely a simulation
- Uses **actual historical price data** from the market
- Helps you **validate your strategy logic** before going live
- Shows you how the strategy behaves under different market conditions

> **Note:** A successful backtest does not guarantee future profits. Markets change, and past performance is not indicative of future results.

---

## 2. When Should You Use Backtesting?

Use the Backtest page when:

| Scenario | Why Backtest? |
|----------|---------------|
| Before live trading | Validate that your strategy has an edge |
| After modifying parameters | See if changes improve or hurt performance |
| Comparing strategies | Objectively measure which performs better |
| Testing on new symbols | Check if your strategy works across different stocks |
| Understanding risk | See maximum drawdown and worst-case scenarios |

### When NOT to Rely on Backtesting Alone
- Strategies with very few trades (statistically unreliable)
- After excessive parameter optimization (overfitting risk)
- Without testing across different market conditions

---

## 3. Step-by-Step: How to Run a Backtest

### Step 1: Select Your Universe
Choose the index universe that contains your target stocks:
- **Nifty 50** — Large-cap blue chips
- **Nifty 100** — Extended large-cap coverage
- **Nifty 200** — Mid + large caps
- **Nifty 500** — Broad market coverage

### Step 2: Select Symbols
Use the symbol search to find and add stocks:
- Type to search by name or symbol
- Click to add to your selection
- Use quick-add buttons for commonly traded stocks
- You can test on a single stock or multiple stocks

### Step 3: Choose Your Strategy
Select a trading strategy from the available options. Strategies are organized by category:
- **Trend Following** — Capture sustained price moves
- **Mean Reversion** — Trade pullbacks and bounces
- **Breakout** — Trade price/volume breakouts
- **Momentum** — Follow strong directional moves

Each strategy has default parameters that you can customize.

### Step 4: Select Timeframe
Choose the candle timeframe for your analysis:

| Timeframe | Best For | Typical Holding Period |
|-----------|----------|------------------------|
| 5m | Intraday scalping | Minutes to hours |
| 15m | Intraday swing | Hours |
| 30m | Intraday position | Hours |
| 1H | Swing trading | Hours to days |
| 1D | Positional trading | Days to weeks |

### Step 5: Set Capital and Risk Parameters
- **Initial Capital** — Starting amount (e.g., ₹10,00,000)
- **Risk Per Trade** — Maximum % to risk per trade
- **Position Sizing** — How trade size is calculated

### Step 6: Click "Run Backtest"
The system will:
1. Load historical data for your selected period
2. Apply your strategy rules
3. Simulate all trades
4. Calculate performance metrics
5. Display results (typically 5-15 seconds)

---

## 4. Understanding Backtest Results

### Total Return (%)
**What it shows:** Your overall profit or loss as a percentage of starting capital.

| Value | Assessment |
|-------|------------|
| > 20% (annual) | Strong performance |
| 10-20% | Good |
| 0-10% | Modest |
| < 0% | Losing strategy |

> **Technical Note:** Calculated as `(Final Capital - Initial Capital) / Initial Capital × 100`

---

### Win Rate (%)
**What it shows:** The percentage of trades that were profitable.

| Value | Assessment |
|-------|------------|
| > 60% | High accuracy |
| 50-60% | Solid |
| 40-50% | Can still be profitable with good R:R |
| < 40% | Needs high reward-to-risk ratio |

> **Important:** Win rate alone doesn't determine profitability. A 30% win rate can be profitable if winners are much larger than losers.

---

### Maximum Drawdown (%)
**What it shows:** The largest peak-to-trough decline your portfolio experienced.

| Value | Risk Level |
|-------|------------|
| < 10% | Low risk |
| 10-20% | Moderate risk |
| 20-30% | High risk |
| > 30% | Very high risk |

> **Ask yourself:** Can you emotionally and financially handle this level of temporary loss?

---

### Sharpe Ratio
**What it shows:** Risk-adjusted return — how much return you get per unit of risk.

| Value | Assessment |
|-------|------------|
| > 2.0 | Excellent |
| 1.0-2.0 | Good |
| 0.5-1.0 | Acceptable |
| < 0.5 | Poor risk/reward |

> **Technical Note:** Higher Sharpe = Better risk-adjusted returns. Compares excess return (above risk-free rate) to volatility.

---

### Number of Trades
**What it shows:** How many trades the strategy executed during the test period.

| Trades | Consideration |
|--------|---------------|
| < 10 | Results may not be statistically significant |
| 10-50 | Reasonable sample size |
| 50-200 | Good statistical reliability |
| > 200 | Watch for over-trading costs |

---

### Equity Curve
**What it shows:** A visual chart of how your portfolio value changed over time.

**How to read it:**
- **Upward slope** — Strategy is making money
- **Smooth curve** — Consistent, low-volatility returns
- **Jagged curve** — High volatility, larger swings
- **Flat periods** — Strategy not generating signals
- **Sharp drops** — Drawdown periods

---

## 5. What Backtesting Does NOT Tell You

### ❌ No Guarantee of Future Profits
Markets are dynamic. A strategy that worked in 2023 may not work in 2024. Always validate with out-of-sample testing.

### ❌ Execution May Differ in Live Trading
- **Slippage** — You may not get the exact price shown
- **Liquidity** — Large orders may move the market
- **Gaps** — Price may jump overnight or after news

### ❌ Costs Are Simplified
- Brokerage fees may reduce actual returns
- STT, stamp duty, GST add up
- Spread costs in less liquid stocks

### ❌ Overfitting Risk
If you keep adjusting parameters until the backtest looks perfect, you may have "curve-fitted" to historical data. The strategy may fail on new data.

---

## 6. Best Practices

1. **Test across multiple time periods** — Include bull, bear, and sideways markets
2. **Don't over-optimize** — Simple rules often work better than complex ones
3. **Check trade count** — More trades = more statistical confidence
4. **Compare to benchmarks** — Beat the Nifty 50 buy-and-hold?
5. **Use Walk-Forward testing** — Validates on unseen data
6. **Start small** — When going live, begin with small capital

---

## 7. Next Steps After Backtesting

```
✓ Backtest shows promise?
    ↓
→ Run Walk-Forward Backtest (validates on unseen data)
    ↓
→ Paper trade or small live test
    ↓
→ Scale up if results hold
```

---

*⚠️ This is for educational and simulation purposes only. Past performance does not guarantee future results.*
