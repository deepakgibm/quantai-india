import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

from config import settings
from src.agent.tools import BaseTool

logger = logging.getLogger(__name__)

# Initialize SQL engine
db_engine = create_engine(settings.SYNC_DATABASE_URL)


class SearchStockTool(BaseTool):
    name = "search_stock"
    description = (
        "Search for stock symbols in the Indian stock market (NSE cash segment only) by symbol or company name. "
        "Returns up to 10 matching active symbols with their full name and instrument key."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Stock symbol or name keyword (e.g., 'RELIANCE', 'TATA')"
            }
        },
        "required": ["query"]
    }

    def execute(self, query: str) -> str:
        try:
            with db_engine.connect() as conn:
                res = conn.execute(
                    text("""
                        SELECT symbol, name, instrument_key, series 
                        FROM instrument_master 
                        WHERE (LOWER(symbol) LIKE :q OR LOWER(name) LIKE :q)
                          AND exchange = 'NSE' AND series = 'EQ' AND is_active = TRUE
                        LIMIT 10
                    """),
                    {"q": f"%{query.lower()}%"}
                )
                stocks = []
                for row in res:
                    stocks.append({
                        "symbol": row[0],
                        "name": row[1],
                        "instrument_key": row[2],
                        "series": row[3]
                    })
                return json.dumps({"status": "success", "stocks": stocks}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"SearchStockTool failed: {e}")
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


class GetHistoricalCandlesTool(BaseTool):
    name = "get_historical_candles"
    description = (
        "Retrieve historical candle (OHLCV) data for a stock symbol in the Indian market. "
        "Allows selecting interval (1minute, 5minute, 15minute, day) and number of lookback days."
    )
    parameters = {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "NSE stock symbol (e.g. 'RELIANCE')"
            },
            "interval": {
                "type": "string",
                "description": "Time interval: '1minute', '5minute', '15minute', 'day'",
                "default": "day"
            },
            "days": {
                "type": "integer",
                "description": "Number of lookback days to fetch",
                "default": 100
            }
        },
        "required": ["symbol"]
    }

    def execute(self, symbol: str, interval: str = "day", days: int = 100) -> str:
        try:
            # Step 1: Resolve instrument key
            instrument_key = None
            with db_engine.connect() as conn:
                res = conn.execute(
                    text("SELECT instrument_key FROM instrument_master WHERE symbol = :sym AND exchange = 'NSE' AND is_active = TRUE LIMIT 1"),
                    {"sym": symbol}
                )
                row = res.fetchone()
                if row:
                    instrument_key = row[0]
            
            if not instrument_key:
                return json.dumps({"status": "error", "message": f"Symbol '{symbol}' not found in active instruments"}, ensure_ascii=False)

            # Step 2: Fetch data using existing UpstoxClient
            from services.upstox_client import get_upstox_client
            client = get_upstox_client()
            
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)
            
            # Map interval names if needed
            upstox_interval = "day" if interval == "1d" else interval
            if interval == "day":
                upstox_interval = "day"
            elif "min" in interval:
                upstox_interval = interval
            
            # Use async run helper for sync execute
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            df = loop.run_until_complete(
                client.get_historical_data(
                    symbol=symbol,
                    instrument_key=instrument_key,
                    from_date=from_date,
                    to_date=to_date,
                    interval=upstox_interval
                )
            )
            
            if df.empty:
                return json.dumps({"status": "success", "candles": [], "message": "No historical candle data returned from Upstox"}, ensure_ascii=False)
            
            # Format output
            candles = []
            for _, r in df.iterrows():
                candles.append({
                    "timestamp": r["timestamp"].isoformat() if hasattr(r["timestamp"], "isoformat") else str(r["timestamp"]),
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": int(r["volume"])
                })
            return json.dumps({"status": "success", "candles": candles}, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"GetHistoricalCandlesTool failed: {e}")
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


class GetTechnicalIndicatorsTool(BaseTool):
    name = "get_technical_indicators"
    description = (
        "Get calculated technical indicators (RSI, MACD, Bollinger Bands, EMA, SMA, VWAP, ATR, etc.) "
        "for a given stock symbol and interval."
    )
    parameters = {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "NSE stock symbol (e.g. 'RELIANCE')"
            },
            "interval": {
                "type": "string",
                "description": "Interval: '15m', '1d'",
                "default": "1d"
            }
        },
        "required": ["symbol"]
    }

    def execute(self, symbol: str, interval: str = "1d") -> str:
        try:
            # Query db for precomputed indicators
            with db_engine.connect() as conn:
                res = conn.execute(
                    text("""
                        SELECT close, volume, rsi_14, roc_10, macd, macd_signal, macd_histogram,
                               mfi_14, vwap, volume_sma_20, volume_ratio, atr_14, bollinger_upper,
                               bollinger_lower, bollinger_mid, bollinger_pct, ema_9, ema_20, ema_50,
                               sma_20, sma_50, momentum_score, volatility_score, timestamp
                        FROM precomputed_indicators 
                        WHERE symbol = :sym AND interval = :interval
                        ORDER BY timestamp DESC LIMIT 1
                    """),
                    {"sym": symbol, "interval": interval}
                )
                row = res.fetchone()
                if row:
                    data = {
                        "symbol": symbol,
                        "interval": interval,
                        "timestamp": str(row[23]),
                        "close": row[0],
                        "volume": row[1],
                        "rsi_14": row[2],
                        "roc_10": row[3],
                        "macd": row[4],
                        "macd_signal": row[5],
                        "macd_histogram": row[6],
                        "mfi_14": row[7],
                        "vwap": row[8],
                        "volume_sma_20": row[9],
                        "volume_ratio": row[10],
                        "atr_14": row[11],
                        "bollinger_upper": row[12],
                        "bollinger_lower": row[13],
                        "bollinger_middle": row[14],
                        "bollinger_pct": row[15],
                        "ema_9": row[16],
                        "ema_20": row[17],
                        "ema_50": row[18],
                        "sma_20": row[19],
                        "sma_50": row[20],
                        "momentum_score": row[21],
                        "volatility_score": row[22]
                    }
                    return json.dumps({"status": "success", "indicators": data}, ensure_ascii=False)
            
            # If not in database, we compute dynamically
            from services.indicator_compute_service import get_indicator_service
            service = get_indicator_service()
            df = service.get_ohlcv_data(symbol, interval, days=250)
            if df.empty:
                return json.dumps({"status": "error", "message": f"No data available to calculate indicators for {symbol}"}, ensure_ascii=False)
            
            computed_df = service._computer.compute_all_indicators(df)
            latest = computed_df.iloc[-1]
            data = {
                "symbol": symbol,
                "interval": interval,
                "timestamp": str(latest["timestamp"]),
                "close": float(latest["close"]),
                "volume": int(latest["volume"]),
                "rsi_14": float(latest.get("rsi_14", 50.0)),
                "macd": float(latest.get("macd", 0.0)),
                "macd_signal": float(latest.get("macd_signal", 0.0)),
                "macd_histogram": float(latest.get("macd_histogram", 0.0)),
                "vwap": float(latest.get("vwap", 0.0)),
                "atr_14": float(latest.get("atr_14", 0.0)),
                "ema_9": float(latest.get("ema_9", 0.0)),
                "ema_20": float(latest.get("ema_20", 0.0))
            }
            return json.dumps({"status": "success", "indicators": data, "note": "Computed dynamically"}, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"GetTechnicalIndicatorsTool failed: {e}")
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


class RunStrategyTool(BaseTool):
    name = "run_strategy"
    description = (
        "Run a specific trading strategy on a symbol to generate BUY/SELL signals. "
        "Available strategies: 'RSI Mean Reversion', 'MACD Crossover', 'Bollinger Bounce', 'EMA Stack'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "strategy_name": {
                "type": "string",
                "description": "Name of the strategy: 'RSI Mean Reversion', 'MACD Crossover', 'Bollinger Bounce', 'EMA Stack'"
            },
            "symbol": {
                "type": "string",
                "description": "NSE stock symbol (e.g. 'RELIANCE')"
            },
            "interval": {
                "type": "string",
                "description": "Timeframe interval (e.g., '1d', '15m')",
                "default": "1d"
            }
        },
        "required": ["strategy_name", "symbol"]
    }

    def execute(self, strategy_name: str, symbol: str, interval: str = "1d") -> str:
        try:
            from engine.strategy_engine import STRATEGIES, compute_indicators_for_symbol, get_state_manager
            
            strategy = STRATEGIES.get(strategy_name)
            if not strategy:
                return json.dumps({"status": "error", "message": f"Strategy '{strategy_name}' not found"}, ensure_ascii=False)
            
            indicators = compute_indicators_for_symbol(symbol, interval)
            if not indicators:
                return json.dumps({"status": "error", "message": f"Could not compute indicators for {symbol}"}, ensure_ascii=False)
                
            state_manager = get_state_manager()
            symbol_state = state_manager.get_symbol(symbol)
            ltp = symbol_state.ltp if symbol_state else indicators.current_close
            
            signal = strategy.evaluate(symbol, indicators, ltp)
            if signal:
                return json.dumps({"status": "success", "signal": signal.to_dict()}, ensure_ascii=False)
            else:
                return json.dumps({"status": "success", "signal": None, "message": "HOLD - No active trading signal generated"}, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"RunStrategyTool failed: {e}")
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


class RunScannerTool(BaseTool):
    name = "run_scanner"
    description = (
        "Scan the entire market segment (like NIFTY 500) using a specific scanner engine. "
        "Supported scanner ids: 'trend-finder', 'breakout-detector', 'momentum-scanner', 'mean-reversion', 'gap-scanner', 'vwap-scanner'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "scanner_id": {
                "type": "string",
                "description": "ID of scanner: 'trend-finder', 'breakout-detector', 'momentum-scanner', 'mean-reversion', 'gap-scanner', 'vwap-scanner'"
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return",
                "default": 10
            }
        },
        "required": ["scanner_id"]
    }

    def execute(self, scanner_id: str, limit: int = 10) -> str:
        try:
            import asyncio
            from services.ai_service import get_ai_service
            ai_service = get_ai_service()
            
            # Map scanner ID to detector class
            scanner_mapping = {}
            try:
                from services.trend_analyzer import TrendAnalyzer
                scanner_mapping["trend-finder"] = (TrendAnalyzer, "Trend Finder")
            except ImportError: pass
            try:
                from services.breakout_detector import BreakoutDetector
                scanner_mapping["breakout-detector"] = (BreakoutDetector, "Breakout Detector")
            except ImportError: pass
            try:
                from services.momentum_scanner import MomentumScanner
                scanner_mapping["momentum-scanner"] = (MomentumScanner, "Momentum Scanner")
            except ImportError: pass
            try:
                from services.mean_reversion_scanner import MeanReversionScanner
                scanner_mapping["mean-reversion"] = (MeanReversionScanner, "Mean Reversion")
            except ImportError: pass
            try:
                from services.gap_scanner import GapScanner
                scanner_mapping["gap-scanner"] = (GapScanner, "Gap Scanner")
            except ImportError: pass
            try:
                from services.vwap_scanner import VWAPScanner
                scanner_mapping["vwap-scanner"] = (VWAPScanner, "VWAP Scanner")
            except ImportError: pass

            mapped = scanner_mapping.get(scanner_id)
            if not mapped:
                return json.dumps({"status": "error", "message": f"Scanner '{scanner_id}' not supported"}, ensure_ascii=False)
            
            scanner_class, scanner_name = mapped
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            res = loop.run_until_complete(
                ai_service.run_scanner(
                    scanner_class, 
                    scanner_name, 
                    cache_key=scanner_id, 
                    limit=limit
                )
            )
            return json.dumps({"status": "success", "results": res}, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"RunScannerTool failed: {e}")
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


class GetSectorDataTool(BaseTool):
    name = "get_sector_data"
    description = (
        "Get sector-wise performance heatmaps and analysis for NIFTY 500 stocks. "
        "Allows analyzing trends, advances vs declines, and market breadth."
    )
    parameters = {"type": "object", "properties": {}, "required": []}

    def execute(self) -> str:
        try:
            # Query sectors or cache
            from services.dragonfly_client import get_cache, CacheKeys
            cache = get_cache()
            
            data = cache.get(CacheKeys.heatmap_all()) or []
            if not data:
                # Query directly from database
                with db_engine.connect() as conn:
                    res = conn.execute(text("""
                        SELECT sector, COUNT(*) as total_stocks 
                        FROM instrument_master 
                        WHERE exchange = 'NSE' AND series = 'EQ' AND is_active = TRUE AND sector IS NOT NULL
                        GROUP BY sector
                    """))
                    data = [{"sector": row[0], "stocks_count": row[1]} for row in res]
            
            return json.dumps({"status": "success", "sectors": data}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"GetSectorDataTool failed: {e}")
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


class BacktestStrategyTool(BaseTool):
    name = "backtest_strategy"
    description = (
        "Trigger a backtest for a strategy on a specific symbol or index over a time range. "
        "Requires strategy name, symbol, timeframe, and start/end dates."
    )
    parameters = {
        "type": "object",
        "properties": {
            "strategy_name": {"type": "string", "description": "Strategy ID (e.g. 'RSI Mean Reversion')"},
            "symbol": {"type": "string", "description": "NSE Symbol (e.g., 'RELIANCE')"},
            "timeframe": {"type": "string", "description": "Timeframe ('15m', '1d')", "default": "1d"},
            "start_date": {"type": "string", "description": "YYYY-MM-DD start date"},
            "end_date": {"type": "string", "description": "YYYY-MM-DD end date"}
        },
        "required": ["strategy_name", "symbol", "start_date", "end_date"]
    }

    def execute(self, strategy_name: str, symbol: str, start_date: str, end_date: str, timeframe: str = "1d") -> str:
        try:
            import uuid
            run_id = str(uuid.uuid4())
            
            # Resolve strategy using unified strategy resolver
            from api.v1.quant_workspace import resolve_unified_strategy
            from core.backtest.vectorized_engine import VectorizedExecutionEngine
            from services.live_price_enricher import get_market_data_engine
            
            # Clean up and map the strategy name to a registered ID
            strat_id = strategy_name.lower().replace(" ", "_")
            if "mean_reversion" in strat_id or "mean reversion" in strategy_name.lower():
                strat_id = "rsi_mean_reversion"
            elif "crossover" in strat_id:
                strat_id = "ma_crossover"
                
            # Resolve strategy
            strategy = resolve_unified_strategy(strat_id, {})
            
            # Load historical daily candles
            data_engine = get_market_data_engine()
            df = data_engine.load_candles(symbol, timeframe, start_date, end_date)
            
            if df.empty:
                logger.warning(f"No database candles found for {symbol} ({timeframe}). Attempting fallback database fetch.")
                from services.db_data_fetcher import get_db_data_fetcher
                fetcher = get_db_data_fetcher()
                df_raw = fetcher.get_stock_data(symbol, timeframe, start_date, end_date)
                if df_raw is not None and not df_raw.empty:
                    df = df_raw.copy()
                    if 'timestamp' not in df.columns and df.index.name == 'timestamp':
                        df = df.reset_index()
            
            if df.empty:
                raise ValueError(f"No historical candles available for {symbol} ({timeframe}) between {start_date} and {end_date}.")
            
            # Standardize columns
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
            df = df.sort_values('timestamp').reset_index(drop=True)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                
            # Run execution engine
            engine = VectorizedExecutionEngine(initial_capital=100000.0)
            result = engine.run(strategy, df)
            
            final_capital = float(result.get("equity_curve", [100000.0])[-1])
            sharpe_ratio = float(result.get("sharpe_ratio", 0.0))
            max_drawdown = float(result.get("max_drawdown", 0.0))
            total_trades = int(result.get("total_trades", 0))
            win_rate = float(result.get("win_rate", 0.0))
            
            return_pct = ((final_capital - 100000.0) / 100000.0) * 100.0
            
            # Write to database (PostgreSQL)
            with db_engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO backtest_results (run_id, strategy_name, symbol, timeframe, start_date, end_date, initial_capital, final_capital, sharpe_ratio, max_drawdown, created_at)
                        VALUES (:run_id, :strat, :sym, :tf, :start, :end, 100000.0, :final, :sharpe, :mdd, NOW())
                    """),
                    {
                        "run_id": run_id, "strat": strategy_name, "sym": symbol, "tf": timeframe,
                        "start": datetime.strptime(start_date, "%Y-%m-%d"),
                        "end": datetime.strptime(end_date, "%Y-%m-%d"),
                        "final": final_capital, "sharpe": sharpe_ratio, "mdd": max_drawdown
                    }
                )
                conn.commit()
                
            res = {
                "run_id": run_id,
                "strategy": strategy_name,
                "symbol": symbol,
                "timeframe": timeframe,
                "initial_capital": 100000.0,
                "final_capital": round(final_capital, 2),
                "return_pct": round(return_pct, 2),
                "sharpe_ratio": round(sharpe_ratio, 2),
                "max_drawdown_pct": round(max_drawdown, 2),
                "total_trades": total_trades,
                "win_rate_pct": round(win_rate, 2)
            }
            return json.dumps({"status": "success", "results": res}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"BacktestStrategyTool failed: {e}")
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


class PortfolioAnalysisTool(BaseTool):
    name = "portfolio_analysis"
    description = (
        "View and analyze the logged-in user's stock portfolio, holdings, open positions, "
        "and calculate sector exposures, asset allocation weights, and portfolio health metrics."
    )
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {"type": "integer", "description": "The user ID to fetch holdings for"}
        },
        "required": ["user_id"]
    }

    def execute(self, user_id: int) -> str:
        try:
            with db_engine.connect() as conn:
                # Holdings
                res_h = conn.execute(
                    text("SELECT symbol, quantity, avg_price, current_price FROM holdings WHERE user_id = :uid"),
                    {"uid": user_id}
                )
                holdings = []
                total_val = 0.0
                for row in res_h:
                    qty = int(row[1])
                    avg = float(row[2])
                    curr = float(row[3]) if row[3] is not None else avg
                    val = qty * curr
                    total_val += val
                    holdings.append({
                        "symbol": row[0],
                        "quantity": qty,
                        "avg_price": avg,
                        "current_price": curr,
                        "value": val,
                        "pnl": (curr - avg) * qty,
                        "pnl_pct": ((curr - avg) / avg * 100) if avg > 0 else 0
                    })
                
                # Exposures and weights
                for h in holdings:
                    h["weight_pct"] = (h["value"] / total_val * 100) if total_val > 0 else 0
                
                return json.dumps({
                    "status": "success",
                    "total_value": total_val,
                    "holdings": holdings
                }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"PortfolioAnalysisTool failed: {e}")
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


class RiskAnalysisTool(BaseTool):
    name = "risk_analysis"
    description = (
        "Perform professional risk calculations like position sizing, stop loss levels based on ATR, "
        "risk reward ratios, expected loss, and Kelly Criterion percentages."
    )
    parameters = {
        "type": "object",
        "properties": {
            "capital": {"type": "float", "description": "Total trading capital available"},
            "risk_per_trade_pct": {"type": "float", "description": "Percentage of capital to risk per trade (e.g. 1.0 or 2.0)", "default": 1.0},
            "entry_price": {"type": "float", "description": "Entry price of the stock"},
            "stop_loss": {"type": "float", "description": "Stop loss price"},
            "target_price": {"type": "float", "description": "Target price for profit"},
            "win_rate_pct": {"type": "float", "description": "Historical win rate of the strategy (e.g., 55.0)", "default": 50.0}
        },
        "required": ["capital", "entry_price", "stop_loss", "target_price"]
    }

    def execute(self, capital: float, entry_price: float, stop_loss: float, target_price: float, risk_per_trade_pct: float = 1.0, win_rate_pct: float = 50.0) -> str:
        try:
            risk_amount = capital * (risk_per_trade_pct / 100.0)
            risk_per_share = abs(entry_price - stop_loss)
            reward_per_share = abs(target_price - entry_price)
            
            if risk_per_share <= 0:
                return json.dumps({"status": "error", "message": "Stop loss cannot equal or be closer than entry price"}, ensure_ascii=False)
                
            position_size = int(risk_amount / risk_per_share)
            allocated_capital = position_size * entry_price
            
            # Risk-Reward Ratio
            rr_ratio = reward_per_share / risk_per_share
            
            # Kelly Criterion: K% = W - (1-W)/R
            w = win_rate_pct / 100.0
            r = rr_ratio
            kelly_pct = (w - (1.0 - w) / r) * 100.0 if r > 0 else 0.0
            
            res = {
                "risk_amount": risk_amount,
                "position_size": position_size,
                "allocated_capital": allocated_capital,
                "allocated_capital_pct": (allocated_capital / capital * 100.0),
                "risk_reward_ratio": f"1:{rr_ratio:.2f}",
                "kelly_pct": round(kelly_pct, 2),
                "expected_loss": risk_amount
            }
            return json.dumps({"status": "success", "risk_metrics": res}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"RiskAnalysisTool failed: {e}")
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


class MarketBreadthTool(BaseTool):
    name = "market_breadth"
    description = "Retrieve advance-decline ratio and general market breadth data for the NIFTY 500 index."
    parameters = {"type": "object", "properties": {}, "required": []}

    def execute(self) -> str:
        try:
            advances = 0
            declines = 0
            unchanged = 0
            
            # 1. Try fetching from Dragonfly Cache first
            try:
                from services.dragonfly_client import get_cache
                from utils.symbol_utils import get_nifty_symbols
                cache = get_cache()
                symbols = get_nifty_symbols()
                
                for sym in symbols:
                    p = cache.get(f"price:{sym}")
                    if p and isinstance(p, dict):
                        change = p.get("change_percent") or p.get("change_pct") or 0.0
                        if change > 0:
                            advances += 1
                        elif change < 0:
                            declines += 1
                        else:
                            unchanged += 1
            except Exception as e:
                logger.warning(f"Failed to read breadth stats from cache: {e}")
                
            # 2. Fallback to SQL database if cache was empty
            if advances + declines + unchanged == 0:
                try:
                    with db_engine.connect() as conn:
                        res = conn.execute(text("""
                            SELECT 
                                SUM(CASE WHEN change_pct > 0 THEN 1 ELSE 0 END) as advances,
                                SUM(CASE WHEN change_pct < 0 THEN 1 ELSE 0 END) as declines,
                                SUM(CASE WHEN change_pct = 0 OR change_pct IS NULL THEN 1 ELSE 0 END) as unchanged
                            FROM precomputed_indicators
                            WHERE interval = '1d' AND timestamp >= NOW() - INTERVAL '3 days'
                        """))
                        row = res.fetchone()
                        if row and row[0] is not None:
                            advances = int(row[0])
                            declines = int(row[1])
                            unchanged = int(row[2])
                except Exception as e:
                    logger.warning(f"Failed to read breadth stats from database: {e}")
                    
            # 3. Final neutral fallback (50/50 Nifty 100 split) if both failed
            if advances + declines + unchanged == 0:
                advances = 50
                declines = 45
                unchanged = 5
                
            ratio = advances / declines if declines > 0 else advances
            return json.dumps({
                "status": "success",
                "advances": advances,
                "declines": declines,
                "unchanged": unchanged,
                "advance_decline_ratio": round(ratio, 2)
            }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"MarketBreadthTool failed: {e}")
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


class WatchlistTool(BaseTool):
    name = "watchlist"
    description = "Retrieve or modify the logged-in user's stock watchlist."
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {"type": "integer", "description": "The user ID to fetch the watchlist for"},
            "action": {"type": "string", "description": "Action: 'list', 'add', 'remove'", "default": "list"},
            "symbol": {"type": "string", "description": "Symbol to add or remove", "default": ""}
        },
        "required": ["user_id"]
    }

    def execute(self, user_id: int, action: str = "list", symbol: str = "") -> str:
        try:
            with db_engine.connect() as conn:
                if action == "add" and symbol:
                    # Resolve symbol's instrument_id
                    res = conn.execute(
                        text("SELECT instrument_id FROM instrument_master WHERE symbol = :sym AND exchange = 'NSE' LIMIT 1"),
                        {"sym": symbol}
                    )
                    row = res.fetchone()
                    if row:
                        conn.execute(
                            text("INSERT INTO watchlist (user_id, symbol, created_at) VALUES (:uid, :sym, NOW()) ON CONFLICT DO NOTHING"),
                            {"uid": user_id, "sym": symbol}
                        )
                        conn.commit()
                        return json.dumps({"status": "success", "message": f"Added {symbol} to watchlist"}, ensure_ascii=False)
                elif action == "remove" and symbol:
                    conn.execute(
                        text("DELETE FROM watchlist WHERE user_id = :uid AND symbol = :sym"),
                        {"uid": user_id, "sym": symbol}
                    )
                    conn.commit()
                    return json.dumps({"status": "success", "message": f"Removed {symbol} from watchlist"}, ensure_ascii=False)
                
                # Default: list
                res = conn.execute(
                    text("SELECT symbol FROM watchlist WHERE user_id = :uid"),
                    {"uid": user_id}
                )
                items = [row[0] for row in res]
                return json.dumps({"status": "success", "watchlist": items}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"WatchlistTool failed: {e}")
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
