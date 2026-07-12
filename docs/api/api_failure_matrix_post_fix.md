# Post-Fix API Failure Matrix

| API Name | Status | Category | Error Evidence |
|---|---|---|---|
| agentic_bot_run_agent_analysis | 422 | Unhandled exception | `Unknown Error` |
| agentic_bot_process_agent_request | 422 | Unhandled exception | `Unknown Error` |
| ai_process_ai_prompt | 422 | Unhandled exception | `Unknown Error` |
| ai_get_market_analysis | 503 | Unhandled exception | `Market analysis temporarily unavailable. AI service error.` |
| ai_process_command | 422 | Unhandled exception | `Unknown Error` |
| ai_get_ai_sentiment | 422 | Unhandled exception | `Unknown Error` |
| algorithms_create_algorithm | 422 | Unhandled exception | `Unknown Error` |
| algorithms_get_algorithm | 422 | Unhandled exception | `Unknown Error` |
| algorithms_update_algorithm | 422 | Unhandled exception | `Unknown Error` |
| algorithms_delete_algorithm | 422 | Unhandled exception | `Unknown Error` |
| analytics_get_volatility_analysis | 404 | Incorrect path / Router not mounted | `No data found for {symbol}` |
| analytics_get_correlation_matrix | 422 | Unhandled exception | `Unknown Error` |
| analytics_execute_custom_query | 422 | Unhandled exception | `Unknown Error` |
| analytics_archive_month | 422 | Unhandled exception | `Unknown Error` |
| analytics_restore_from_archive | 422 | Unhandled exception | `Unknown Error` |
| analytics_get_latest_indicators | 404 | Incorrect path / Router not mounted | `No indicators found for {symbol} (1d)` |
| auth_signup | 422 | Unhandled exception | `Unknown Error` |
| auth_login | 422 | Unhandled exception | `Unknown Error` |
| auth_firebase_login | 422 | Unhandled exception | `Unknown Error` |
| heatmap_seed_data | 403 | Unhandled exception | `Only admins can seed data` |
| hp_scanner_api_get_symbol_snapshot | 404 | Incorrect path / Router not mounted | `Symbol {symbol} not found in cache` |
| orders_create_order | 422 | Unhandled exception | `Unknown Error` |
| orders_get_order | 422 | Unhandled exception | `Unknown Error` |
| quant_bot_run_backtest | 422 | Unhandled exception | `Unknown Error` |
| quant_bot_run_walkforward | 422 | Unhandled exception | `Unknown Error` |
| scanner_run_scan | 422 | Unhandled exception | `Unknown Error` |
| scanner_save_preset | 422 | Unhandled exception | `Unknown Error` |
| scanner_delete_preset | 422 | Unhandled exception | `Unknown Error` |
| upstox_upstox_callback | 422 | Unhandled exception | `Unknown Error` |
| upstox_get_portfolio | 400 | Unhandled exception | `Upstox not connected. Please login to Upstox.` |
| upstox_get_positions | 400 | Unhandled exception | `Upstox not connected` |
| upstox_get_market_quote | 400 | Unhandled exception | `Upstox not connected` |
| backtest_strategies_search_strategies | 422 | Unhandled exception | `Unknown Error` |
| backtest_strategies_get_strategy_details | 404 | Incorrect path / Router not mounted | `Strategy '{strategy_name}' not found. Use /api/v1/backtest/strategies/list to see available strategi` |
| experiment_lab_get_strategy | 422 | Unhandled exception | `Unknown Error` |
| experiment_lab_run_backtest | 422 | Unhandled exception | `Unknown Error` |
| experiment_lab_compare_strategies | 422 | Unhandled exception | `Unknown Error` |
| ml_forecast_predict_price | 422 | Unhandled exception | `Unknown Error` |
| walk_forward_backtest_get_available_symbols | 500 | Unhandled exception | `Unknown Error` |