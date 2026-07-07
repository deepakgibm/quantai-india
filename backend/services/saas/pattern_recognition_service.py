"""
AI Chart Pattern Recognition Service
"""

import logging
from sqlalchemy.future import select
from models_alpha import StockCandle, InstrumentMaster
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PatternRecognitionService:
    @staticmethod
    async def detect_patterns(db_session, symbol: str):
        """Scan candles to detect technical candlestick, harmonic, and chart patterns."""
        symbol = symbol.upper()
        
        # 1. Look up symbol instrument id
        inst_query = select(InstrumentMaster).where(InstrumentMaster.symbol == symbol)
        inst_res = await db_session.execute(inst_query)
        instrument = inst_res.scalars().first()
        
        candles = []
        if instrument:
            candle_query = select(StockCandle).where(
                StockCandle.instrument_id == instrument.instrument_id,
                StockCandle.timeframe == 1440
            ).order_by(StockCandle.candle_ts.desc()).limit(60)
            candle_res = await db_session.execute(candle_query)
            db_candles = candle_res.scalars().all()
            
            for c in reversed(db_candles):
                candles.append({
                    "open": float(c.open or 0.0),
                    "high": float(c.high or 0.0),
                    "low": float(c.low or 0.0),
                    "close": float(c.close or 0.0),
                    "timestamp": c.candle_ts
                })
                
        # If DB has less than 30 candles, fetch from Upstox REST API
        if len(candles) < 30 and instrument and instrument.instrument_key:
            try:
                from services.upstox_client import UpstoxClient
                upstox = UpstoxClient()
                to_date = datetime.now()
                from_date = to_date - timedelta(days=90)
                df = await upstox.get_historical_data(
                    symbol=symbol,
                    instrument_key=instrument.instrument_key,
                    from_date=from_date,
                    to_date=to_date,
                    interval="day"
                )
                if not df.empty:
                    df = df.sort_values("timestamp")
                    candles = []
                    for _, row in df.iterrows():
                        candles.append({
                            "open": float(row["open"] or 0.0),
                            "high": float(row["high"] or 0.0),
                            "low": float(row["low"] or 0.0),
                            "close": float(row["close"] or 0.0),
                            "timestamp": row["timestamp"].to_pydatetime() if hasattr(row["timestamp"], "to_pydatetime") else row["timestamp"]
                        })
                    logger.info(f"Loaded {len(candles)} candles from Upstox API for {symbol}")
            except Exception as ue:
                logger.error(f"Failed to fetch candles from Upstox API for {symbol}: {ue}")

        if len(candles) < 30:
            logger.warning(f"Insufficient historical data ({len(candles)} candles) for symbol {symbol}. Returning empty metrics.")
            return {
                "symbol": symbol,
                "candlestick_patterns": [],
                "harmonic_patterns": [],
                "chart_patterns": []
            }
            
        n = len(candles)
        detected_candlesticks = []
        detected_harmonics = []
        detected_charts = []
        
        # 2. Candlestick Patterns detection
        for i in range(2, n):
            c1 = candles[i-1]
            c2 = candles[i]
            
            body = abs(c2["close"] - c2["open"])
            range_len = c2["high"] - c2["low"]
            if range_len == 0: continue
            
            # Doji
            if body / range_len < 0.1:
                detected_candlesticks.append({
                    "pattern": "Doji",
                    "type": "NEUTRAL",
                    "price": c2["close"],
                    "timestamp": c2["timestamp"].strftime("%Y-%m-%d"),
                    "description": "Indecision in the market; close is near open."
                })
                
            # Hammer (bullish reversal)
            lower_shadow = min(c2["open"], c2["close"]) - c2["low"]
            upper_shadow = c2["high"] - max(c2["open"], c2["close"])
            if lower_shadow > body * 2.0 and upper_shadow < body * 0.5:
                detected_candlesticks.append({
                    "pattern": "Hammer",
                    "type": "BULLISH",
                    "price": c2["close"],
                    "timestamp": c2["timestamp"].strftime("%Y-%m-%d"),
                    "description": "Bullish reversal signal. Long lower shadow indicates strong support."
                })
                
            # Engulfing Patterns
            if c1["close"] < c1["open"] and c2["close"] > c2["open"]:  # Bullish Engulfing
                if c2["open"] <= c1["close"] and c2["close"] >= c1["open"]:
                    detected_candlesticks.append({
                        "pattern": "Bullish Engulfing",
                        "type": "BULLISH",
                        "price": c2["close"],
                        "timestamp": c2["timestamp"].strftime("%Y-%m-%d"),
                        "description": "Bullish expansion engulfs previous bearish candle."
                    })
            elif c1["close"] > c1["open"] and c2["close"] < c2["open"]:  # Bearish Engulfing
                if c2["open"] >= c1["close"] and c2["close"] <= c1["open"]:
                    detected_candlesticks.append({
                        "pattern": "Bearish Engulfing",
                        "type": "BEARISH",
                        "price": c2["close"],
                        "timestamp": c2["timestamp"].strftime("%Y-%m-%d"),
                        "description": "Bearish expansion engulfs previous bullish candle."
                    })

        # 3. Harmonic Patterns detection
        # Extrema detection (swing points)
        swings = []  # list of tuples: (index, type: 'high'/'low', price, timestamp)
        for i in range(2, n - 2):
            # Check for swing high
            if (candles[i]["high"] > candles[i-1]["high"] and candles[i]["high"] > candles[i-2]["high"] and
                candles[i]["high"] > candles[i+1]["high"] and candles[i]["high"] > candles[i+2]["high"]):
                swings.append((i, "high", candles[i]["high"], candles[i]["timestamp"]))
            # Check for swing low
            elif (candles[i]["low"] < candles[i-1]["low"] and candles[i]["low"] < candles[i-2]["low"] and
                  candles[i]["low"] < candles[i+1]["low"] and candles[i]["low"] < candles[i+2]["low"]):
                swings.append((i, "low", candles[i]["low"], candles[i]["timestamp"]))

        # Find 5-point patterns (X, A, B, C, D)
        if len(swings) >= 5:
            recent_swings = swings[-5:]
            alternating = True
            for k in range(4):
                if recent_swings[k][1] == recent_swings[k+1][1]:
                    alternating = False
            if alternating:
                x_p = recent_swings[0][2]
                a_p = recent_swings[1][2]
                b_p = recent_swings[2][2]
                c_p = recent_swings[3][2]
                d_p = recent_swings[4][2]
                
                xa = abs(a_p - x_p)
                ab = abs(b_p - a_p)
                bc = abs(c_p - b_p)
                cd = abs(d_p - c_p)
                
                if xa > 0 and ab > 0 and bc > 0:
                    rt_ab = ab / xa
                    rt_bc = bc / ab
                    rt_cd = cd / bc
                    
                    if 0.5 <= rt_ab <= 0.85 and 0.3 <= rt_bc <= 0.95:
                        is_bullish = recent_swings[4][1] == "low"  # ending in a valley
                        detected_harmonics.append({
                            "pattern": "Gartley" if is_bullish else "Bearish Gartley",
                            "accuracy": float(round((1.0 - abs(rt_ab - 0.618)) * 100, 1)),
                            "target_price": float(round(d_p * (1.08 if is_bullish else 0.92), 2)),
                            "stop_loss": float(round(d_p * (0.96 if is_bullish else 1.04), 2)),
                            "timestamp": recent_swings[4][3].strftime("%Y-%m-%d"),
                            "ratio_breakdown": {
                                "XA": 1.0,
                                "AB": float(round(rt_ab, 3)),
                                "BC": float(round(rt_bc, 3)),
                                "CD": float(round(rt_cd, 3))
                            }
                        })

        # 4. Chart Patterns (Triangles, Flags, Wedges)
        # Symmetrical Triangle detection: converging highs and lows
        last_15 = candles[-15:]
        highs_15 = [c["high"] for c in last_15]
        lows_15 = [c["low"] for c in last_15]
        
        first_half_high = max(highs_15[:7])
        second_half_high = max(highs_15[7:])
        first_half_low = min(lows_15[:7])
        second_half_low = min(lows_15[7:])
        
        if second_half_high < first_half_high * 0.995 and second_half_low > first_half_low * 1.005:
            detected_charts.append({
                "pattern": "Symmetrical Triangle",
                "type": "CONSOLIDATION",
                "direction": "BREAKOUT_PENDING",
                "trigger_price": float(round(second_half_high, 2)),
                "target": float(round(second_half_high * 1.08, 2)),
                "timestamp": candles[-1]["timestamp"].strftime("%Y-%m-%d")
            })
        else:
            # Bullish Flag: check for a strong preceding uptrend followed by a consolidation channel
            if len(candles) >= 20:
                flagpole_change = (candles[-6]["close"] - candles[-16]["close"]) / candles[-16]["close"]
                flag_consolidation = all(candles[-i]["close"] <= candles[-i-1]["close"] * 1.015 for i in range(1, 5))
                if flagpole_change >= 0.05 and flag_consolidation:
                    detected_charts.append({
                        "pattern": "Bullish Flag",
                        "type": "CONTINUATION",
                        "direction": "UPWARD",
                        "trigger_price": float(round(max([c["high"] for c in candles[-5:]]), 2)),
                        "target": float(round(candles[-1]["close"] * (1.0 + flagpole_change), 2)),
                        "timestamp": candles[-1]["timestamp"].strftime("%Y-%m-%d")
                    })

        return {
            "symbol": symbol,
            "candlestick_patterns": detected_candlesticks[-5:],
            "harmonic_patterns": detected_harmonics,
            "chart_patterns": detected_charts
        }


