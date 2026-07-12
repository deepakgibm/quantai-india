# Technical Memory: AI Orchestration & Swarm Committee

## 1. LLM Models
*   **Primary**: Google Gemini 1.5 Pro (for deep backtests analysis and swarm debates).
*   **Secondary**: Google Gemini 1.5 Flash (for quick single-stock screening and summarization).

## 2. Swarm Committee Pipeline
The Swarm Committee utilizes three separate virtual LLM personas to evaluate a stock's potential:

1.  **Bullish Analyst**: Focuses on positive indicator setups, volume expansion, and macro tailwinds.
2.  **Bearish Analyst**: Probes for structural overhead resistance, negative divergences, and risk anomalies.
3.  **Risk Officer**: Synthesizes the two arguments and enforces money-management rules.

```
Inputs (LTP, RSI, EMA, Volatility)
           │
           ▼
[Swarm Committee Debate: Bull vs Bear]
           │
           ▼
[Consensus Synthesis (Risk Officer)]
           │
           ▼
[Consensus Score & Verdict (Buy / Avoid)]
```

## 3. Score Card Fallback
If the LLM endpoints fail or throttle, the system automatically runs a deterministic scoring template comparing RSI bounds and moving average trends.
