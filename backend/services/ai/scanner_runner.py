import logging
import asyncio
import time
from typing import Dict, Any
from services.dragonfly_client import get_cache
from utils.json_utils import sanitize_for_json
from services.live_price_enricher import enrich_scanner_results
from config import settings

logger = logging.getLogger(__name__)

class ScannerRunner:
    async def run_scanner(self, scanner_class, scanner_name: str, cache_key: str, limit: int = 10, timeout: float = 5.0) -> Dict[str, Any]:
        """Generic runner for AI technical scanners with caching and enrichment."""
        start_time = time.time()
        enriched_cache_key = f"{cache_key}:enriched"
        
        # 1. Check Cache
        cache = get_cache()
        if cache.is_available():
            try:
                cached_enriched = cache.get(enriched_cache_key)
                if cached_enriched:
                    logger.info(f"ScannerRunner: {scanner_name} enriched cache hit")
                    return cached_enriched
                
                cached_raw = cache.get(cache_key)
                if cached_raw:
                    logger.info(f"ScannerRunner: {scanner_name} raw cache hit, enriching...")
                    if isinstance(cached_raw, dict) and "stocks" in cached_raw:
                        cached_raw["stocks"] = await enrich_scanner_results(cached_raw["stocks"])
                        cache.set(enriched_cache_key, cached_raw, ttl=60)
                        return cached_raw
            except Exception as e:
                logger.error(f"ScannerRunner: {scanner_name} cache/enrichment error: {e}")

        # 2. Run Scan
        try:
            logger.info(f"ScannerRunner: Starting {scanner_name} scan with {timeout}s budget...")
            detector = scanner_class()
            
            # Check if scan_all is a coroutine function
            import inspect
            if inspect.iscoroutinefunction(detector.scan_all):
                scan_result = await asyncio.wait_for(detector.scan_all(limit=limit, timeout=timeout), timeout=timeout + 2.0)
            else:
                loop = asyncio.get_event_loop()
                scan_result = await asyncio.wait_for(
                    loop.run_in_executor(None, detector.scan_all, limit),
                    timeout=timeout + 2.0
                )
            
            # Handle return format (dict with progress vs legacy list)
            if isinstance(scan_result, dict):
                # Check for explicit error codes from scanner
                if scan_result.get("error_code") == "INCOMPLETE_SCAN":
                    return sanitize_for_json({
                        "status": "error",
                        "error_code": "INCOMPLETE_SCAN",
                        "message": scan_result.get("message", "Incomplete scan universe detected."),
                        "stocks": [],
                        "count": 0,
                        "buy_signals": [],
                        "sell_signals": [],
                        "scan_type": f"{cache_key.lower()}_technical",
                        "description": f"{scanner_name} scan failed",
                        "debug": {
                            "symbols_expected": scan_result.get("symbols_expected", 503),
                            "symbols_scanned": scan_result.get("symbols_processed", 0),
                            "symbols_failed": scan_result.get("symbols_failed", 0),
                            "symbols_missing": scan_result.get("symbols_missing", 503),
                            "tables_used": scan_result.get("tables_used", []),
                            "execution_time_ms": int((time.time() - start_time) * 1000)
                        }
                    })
                
                stocks = scan_result.get("stocks", [])
                symbols_processed = scan_result.get("symbols_processed", 0)
                symbols_expected = scan_result.get("symbols_expected", 503)
                symbols_missing = scan_result.get("symbols_missing", symbols_expected - symbols_processed)
                symbols_failed = scan_result.get("symbols_failed", 0)
                completed_all = scan_result.get("completed_all", True)
                scan_metrics = scan_result.get("metrics", {})
                tables_used = scan_result.get("tables_used", [])
                filter_stats = scan_result.get("filter_stats", {})
                status = scan_result.get("status", "success")
                indicators_timeframe = scan_result.get("indicators_timeframe", "15m")
            else:
                stocks = scan_result
                symbols_processed = len(stocks) if stocks else 0
                symbols_expected = 503
                symbols_missing = symbols_expected - symbols_processed
                symbols_failed = 0
                completed_all = True
                scan_metrics = {}
                tables_used = []
                filter_stats = {}
                status = "success"
                indicators_timeframe = "15m"

            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Refine Status
            if status == "success" and not stocks:
                status = "no_signal"
            
            # Calculate Buy/Sell signal lists
            buy_signals = [s for s in stocks if s.get("signal") == "BUY" or s.get("action") == "BUY" or s.get("trend") == "BULLISH"]
            sell_signals = [s for s in stocks if s.get("signal") == "SELL" or s.get("action") == "SELL" or s.get("trend") == "BEARISH"]

            # 4. Enrich and Build Response
            enriched_stocks = await enrich_scanner_results(stocks)
            enriched_buy = await enrich_scanner_results(buy_signals)
            enriched_sell = await enrich_scanner_results(sell_signals)
            
            # Map filter stats to a reason summary if no signals
            message = None
            if status == "no_signal":
                reasons = []
                if filter_stats.get("no_data", 0) > 0: reasons.append(f"{filter_stats['no_data']} no data")
                if filter_stats.get("insufficient_history", 0) > 0: reasons.append(f"{filter_stats['insufficient_history']} insufficient history")
                if filter_stats.get("filtered_by_rule", 0) > 0: reasons.append(f"{filter_stats['filtered_by_rule']} filtered by rule")
                reason_str = ", ".join(reasons) if reasons else "no matches"
                message = f"Market conditions monitored for {symbols_processed} stocks. Filter summary: {reason_str}."

            response = {
                "status": status,
                "count": len(enriched_stocks),
                "stocks": enriched_stocks,
                "buy_signals": enriched_buy,
                "sell_signals": enriched_sell,
                "scan_type": f"{scanner_name.lower().replace(' ', '_')}_technical",
                "description": f"{scanner_name} with LIVE prices",
                "message": message or f"{scanner_name} scan {status}",
                "debug": {
                    "symbols_expected": symbols_expected,
                    "symbols_scanned": symbols_processed,
                    "symbols_failed": symbols_failed,
                    "symbols_missing": symbols_missing,
                    "buy_signals": len(buy_signals),
                    "sell_signals": len(sell_signals),
                    "tables_used": tables_used,
                    "price_source": "websocket/cache",
                    "indicator_timeframe": indicators_timeframe,
                    "execution_time_ms": execution_time_ms,
                    "completed": completed_all,
                    "filter_stats": filter_stats,
                    "scan_metrics": scan_metrics
                }
            }
            
            # Final Sanitization for JSON safety
            sanitized_response = sanitize_for_json(response)
            
            # Cache full or partial successes
            if cache.is_available():
                cache.set(cache_key, sanitized_response, ttl=600)
                cache.set(enriched_cache_key, sanitized_response, ttl=60)
            
            return sanitized_response
            
        except asyncio.TimeoutError:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"ScannerRunner: {scanner_name} hard timeout after {timeout}s")
            return sanitize_for_json({
                "status": "scan_timed_out", 
                "count": 0, 
                "stocks": [], 
                "buy_signals": [],
                "sell_signals": [],
                "scan_type": f"{cache_key.lower()}_technical",
                "description": "Total execution budget exceeded.",
                "message": f"The {scanner_name} scan took too long to respond.",
                "error_code": "TIMEOUT",
                "debug": {
                    "symbols_expected": 503,
                    "symbols_scanned": 0,
                    "symbols_failed": 0,
                    "symbols_missing": 503,
                    "execution_time_ms": execution_time_ms,
                    "completed": False
                }
            })
        except Exception as e:
            logger.error(f"ScannerRunner: {scanner_name} CRITICAL error: {e}", exc_info=True)
            return sanitize_for_json({
                "status": "error", 
                "count": 0, 
                "stocks": [], 
                "buy_signals": [],
                "sell_signals": [],
                "scan_type": f"{cache_key.lower()}_technical",
                "description": f"{scanner_name} failed",
                "message": f"An internal error occurred: {str(e)}",
                "error_code": "EXECUTION_ERROR",
                "debug": {
                    "symbols_expected": 503,
                    "symbols_scanned": 0,
                    "symbols_failed": 0,
                    "symbols_missing": 503,
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                    "completed": False
                }
            })

_runner = None
def get_scanner_runner() -> ScannerRunner:
    global _runner
    if _runner is None:
        _runner = ScannerRunner()
    return _runner
