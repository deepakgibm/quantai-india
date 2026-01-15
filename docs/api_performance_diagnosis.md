# API Performance Diagnosis

| API Name | Method | Time (ms) | Observations |
|---|---|---|---|
| agentic_bot_process_agent_request | POST | 576 | LLM/Agentic reasoning delay. |
| ai_process_ai_prompt | POST | 280 | High computation or blocking IO detected. |
| ai_get_trend_finder_stocks | GET | 7785 | Sequential technical analysis computation for multiple symbols in request loop. |
| ai_get_breakout_stocks | GET | 6130 | Sequential technical analysis computation for multiple symbols in request loop. |
| ai_get_top5_picks | GET | 5080 | Sequential technical analysis computation for multiple symbols in request loop. |
| ai_get_momentum_stocks | GET | 2249 | Sequential technical analysis computation for multiple symbols in request loop. |