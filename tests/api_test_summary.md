# API Test Summary
- **Discovery Date**: 2026-01-10 13:07:59 UTC
- **Total APIs Discovered**: 122
- **APIs Tested**: 122
- **APIs Passed**: 44
- **APIs Failed**: 78
- **Average Response Time**: 208.07 ms
- **P95 Response Time**: 263.05 ms

## Slow APIs (> 200ms)
| API Name | Method | Path | Time (ms) | Status |
|----------|--------|------|-----------|--------|
| agentic_bot_process_agent_request | POST | /api/agentic-bot/process | 576 | 200 |
| ai_process_ai_prompt | POST | /api/ai/prompt | 280 | 500 |
| ai_get_trend_finder_stocks | GET | /api/ai/trend-finder | 7785 | 200 |
| ai_get_breakout_stocks | GET | /api/ai/breakout-detector | 6130 | 200 |
| ai_get_top5_picks | GET | /api/ai/top5-picks | 5080 | 200 |
| ai_get_momentum_stocks | GET | /api/ai/momentum-scanner | 2249 | 200 |
