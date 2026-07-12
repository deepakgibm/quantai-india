# API Risk Register
Explicitly flagged APIs based on measured performance and security observations.

| Risk Area | API Name | Method | Time (ms) | Observations |
|-----------|----------|--------|-----------|--------------|
| Latency | agentic_bot_process_agent_request | POST | 576 | Response time exceeds 200ms SLA. Potentially high DB load or blocking IO. |
| Latency | ai_process_ai_prompt | POST | 280 | Response time exceeds 200ms SLA. Potentially high DB load or blocking IO. |
| Latency | ai_get_trend_finder_stocks | GET | 7785 | Response time exceeds 200ms SLA. Potentially high DB load or blocking IO. |
| Latency | ai_get_breakout_stocks | GET | 6130 | Response time exceeds 200ms SLA. Potentially high DB load or blocking IO. |
| Latency | ai_get_top5_picks | GET | 5080 | Response time exceeds 200ms SLA. Potentially high DB load or blocking IO. |
| Latency | ai_get_momentum_stocks | GET | 2249 | Response time exceeds 200ms SLA. Potentially high DB load or blocking IO. |
| Stability | ai_process_ai_prompt | POST | 280 | API returned 500 Internal Server Error. |
| Stability | ai_process_command | POST | 135 | API returned 500 Internal Server Error. |
| Stability | market_get_nifty100_top_movers | GET | 33 | API returned 500 Internal Server Error. |
| Stability | market_get_nifty100_ranking_status | GET | 30 | API returned 500 Internal Server Error. |
| Stability | market_get_top_movers_alias | GET | 29 | API returned 500 Internal Server Error. |
| Stability | trading_get_top_gainers | GET | 23 | API returned 500 Internal Server Error. |
| Stability | trading_get_gainers_losers | GET | 20 | API returned 500 Internal Server Error. |
