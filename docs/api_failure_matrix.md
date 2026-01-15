# API Failure Matrix

| API Name | Failure Category | Error Evidence | Reproducibility |
|---|---|---|---|
| agentic_bot_run_agent_analysis | Missing or invalid request validation | `[{'type': 'missing', 'loc': ['body', 'prompt'], 'msg': 'Field required', 'input': {'symbol': 'RELIAN` | Yes |
| ai_process_ai_prompt | Unhandled exception | `AI processing failed: 403 Your API key was reported as leaked. Please use another API key.` | Yes |
| ai_get_market_analysis | Unhandled exception | `Market analysis temporarily unavailable. AI service error.` | Yes |
| ai_process_command | Unhandled exception | `Command processing failed: 403 Your API key was reported as leaked. Please use another API key.` | Yes |
| ai_get_ai_sentiment | Missing or invalid request validation | `[{'type': 'missing', 'loc': ['query', 'symbol'], 'msg': 'Field required', 'input': None, 'url': 'htt` | Yes |
| algorithms_create_algorithm | Missing or invalid request validation | `[{'type': 'missing', 'loc': ['body', 'name'], 'msg': 'Field required', 'input': {'test': 'data'}, 'u` | Yes |
| algorithms_get_algorithm | Unhandled exception | `Algorithm not found` | Yes |
| algorithms_update_algorithm | Unhandled exception | `Algorithm not found` | Yes |
| algorithms_delete_algorithm | Unhandled exception | `Algorithm not found` | Yes |
| analytics_get_analytics_overview | Unhandled exception | `Not Found` | Yes |
| analytics_get_top_momentum | Unhandled exception | `Not Found` | Yes |
| analytics_get_volatility_analysis | Unhandled exception | `Not Found` | Yes |
| analytics_get_correlation_matrix | Unhandled exception | `Not Found` | Yes |
| analytics_get_support_resistance | Unhandled exception | `Not Found` | Yes |
| analytics_execute_custom_query | Unhandled exception | `Not Found` | Yes |
| analytics_list_archives | Unhandled exception | `Not Found` | Yes |
| analytics_get_archive_stats | Unhandled exception | `Not Found` | Yes |
| analytics_archive_month | Unhandled exception | `Not Found` | Yes |
| analytics_archive_old_data | Unhandled exception | `Not Found` | Yes |
| analytics_restore_from_archive | Unhandled exception | `Not Found` | Yes |
| analytics_trigger_indicator_computation | Unhandled exception | `Not Found` | Yes |
| analytics_get_latest_indicators | Unhandled exception | `Not Found` | Yes |
| auth_signup | Unhandled exception | `Username already taken` | Yes |
| auth_login | Missing or invalid request validation | `[{'type': 'missing', 'loc': ['body', 'email'], 'msg': 'Field required', 'input': {'test': 'data'}, '` | Yes |
| auth_firebase_login | Authentication / authorization issue | `[{'type': 'missing', 'loc': ['body', 'id_token'], 'msg': 'Field required', 'input': {'test': 'data'}` | Yes |
| heatmap_seed_data | Unhandled exception | `Only admins can seed data` | Yes |
| hp_scanner_api_get_momentum | Unhandled exception | `Not Found` | Yes |
| hp_scanner_api_get_breakout | Unhandled exception | `Not Found` | Yes |
| hp_scanner_api_get_reversal | Unhandled exception | `Not Found` | Yes |
| hp_scanner_api_get_active_signals | Unhandled exception | `Not Found` | Yes |
| hp_scanner_api_get_all_snapshots | Unhandled exception | `Not Found` | Yes |
| hp_scanner_api_get_symbol_snapshot | Unhandled exception | `Not Found` | Yes |
| hp_scanner_api_get_status | Unhandled exception | `Not Found` | Yes |
| hp_scanner_api_get_metrics | Unhandled exception | `Not Found` | Yes |
| hp_scanner_api_trigger_warm | Unhandled exception | `Not Found` | Yes |
| market_get_nifty100_top_movers | External dependency failure | `cannot import name 'get_nifty_symbols' from 'utils.symbol_utils' (/app/utils/symbol_utils.py)` | Yes |
| market_get_nifty100_ranking_status | External dependency failure | `cannot import name 'get_nifty_symbols' from 'utils.symbol_utils' (/app/utils/symbol_utils.py)` | Yes |
| market_get_top_movers_alias | External dependency failure | `cannot import name 'get_nifty_symbols' from 'utils.symbol_utils' (/app/utils/symbol_utils.py)` | Yes |
| orders_create_order | Missing or invalid request validation | `[{'type': 'missing', 'loc': ['body', 'symbol'], 'msg': 'Field required', 'input': {'test': 'data'}, ` | Yes |
| orders_get_order | Unhandled exception | `Order not found` | Yes |
| quant_bot_run_backtest | Missing or invalid request validation | `[{'type': 'missing', 'loc': ['body', 'symbol'], 'msg': 'Field required', 'input': {'test': 'data'}, ` | Yes |
| quant_bot_run_walkforward | Missing or invalid request validation | `[{'type': 'missing', 'loc': ['body', 'symbol'], 'msg': 'Field required', 'input': {'test': 'data'}, ` | Yes |
| scanner_get_strategies | Unhandled exception | `Not Found` | Yes |
| scanner_get_indices | Unhandled exception | `Not Found` | Yes |
| scanner_get_timeframes | Unhandled exception | `Not Found` | Yes |
| scanner_run_scan | Unhandled exception | `Not Found` | Yes |
| scanner_get_scan_progress | Unhandled exception | `Not Found` | Yes |
| scanner_get_presets | Unhandled exception | `Not Found` | Yes |
| scanner_save_preset | Unhandled exception | `Not Found` | Yes |
| scanner_delete_preset | Unhandled exception | `Not Found` | Yes |
| scanner_get_momentum_data | Unhandled exception | `Not Found` | Yes |
| scanner_get_breakout_data | Unhandled exception | `Not Found` | Yes |
| scanner_get_reversal_data | Unhandled exception | `Not Found` | Yes |
| scanner_get_trendfinder_data | Unhandled exception | `Not Found` | Yes |
| scanner_get_week52_breakouts | Unhandled exception | `Not Found` | Yes |
| scanner_get_momentum_status | Unhandled exception | `Not Found` | Yes |
| trading_get_top_gainers | External dependency failure | `cannot import name 'get_nifty_symbols' from 'utils.symbol_utils' (/app/utils/symbol_utils.py)` | Yes |
| trading_get_gainers_losers | External dependency failure | `cannot import name 'get_nifty_symbols' from 'utils.symbol_utils' (/app/utils/symbol_utils.py)` | Yes |
| upstox_upstox_callback | Unhandled exception | `Upstox auth failed: {"status":"error","errors":[{"errorCode":"UDAPI100057","message":"Invalid Auth c` | Yes |
| upstox_get_portfolio | Unhandled exception | `Upstox not connected. Please login to Upstox.` | Yes |
| upstox_get_positions | Unhandled exception | `Upstox not connected` | Yes |
| upstox_get_market_quote | Unhandled exception | `Upstox not connected` | Yes |
| backtest_strategies_search_strategies | Missing or invalid request validation | `[{'type': 'missing', 'loc': ['query', 'query'], 'msg': 'Field required', 'input': None, 'url': 'http` | Yes |
| backtest_strategies_get_strategy_details | Unhandled exception | `Strategy '{strategy_name}' not found. Use /api/v1/backtest/strategies/list to see available strategi` | Yes |
| etl_status_get_etl_status | Unhandled exception | `Not Found` | Yes |
| experiment_lab_get_lab_info | Unhandled exception | `Not Found` | Yes |
| experiment_lab_list_strategies | Unhandled exception | `Not Found` | Yes |
| experiment_lab_get_strategy | Unhandled exception | `Not Found` | Yes |
| experiment_lab_list_categories | Unhandled exception | `Not Found` | Yes |
| experiment_lab_run_backtest | Unhandled exception | `Not Found` | Yes |
| experiment_lab_compare_strategies | Unhandled exception | `Not Found` | Yes |
| experiment_lab_get_available_symbols | Unhandled exception | `Not Found` | Yes |
| experiment_lab_get_available_timeframes | Unhandled exception | `Not Found` | Yes |
| experiment_lab_clear_cache | Unhandled exception | `Not Found` | Yes |
| ml_forecast_predict_price | Missing or invalid request validation | `[{'type': 'missing', 'loc': ['query', 'symbol'], 'msg': 'Field required', 'input': None, 'url': 'htt` | Yes |
| walk_forward_backtest_get_available_strategies | Unhandled exception | `Not Found` | Yes |
| walk_forward_backtest_get_walk_forward_presets | Unhandled exception | `Not Found` | Yes |
| walk_forward_backtest_get_available_symbols | Unhandled exception | `Not Found` | Yes |