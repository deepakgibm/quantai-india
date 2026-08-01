"""
Smart Money Concepts (SMC) Detection Service

Production-grade implementation with:
- Live LTP cross-check against historical candles (5% reload, 15% rejection)
- 40% price distance filter to discard stale/obsolete levels
- Live quote candle merge for real-time accuracy
- Full instrument resolution and dataset diagnostic logging
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy.future import select
from models_alpha import StockCandle, InstrumentMaster, TimeframeMapper

logger = logging.getLogger(__name__)

# Maximum % distance from live LTP before a structural level is considered irrelevant
_MAX_LEVEL_DISTANCE_PCT = 0.40


def _is_within_range(level: float, live_ltp: float, max_pct: float = _MAX_LEVEL_DISTANCE_PCT) -> bool:
    """Return True if 'level' is within max_pct of live_ltp."""
    if not live_ltp or live_ltp <= 0:
        return True  # no LTP available -- don't filter
    return abs(level - live_ltp) / live_ltp <= max_pct


def _to_naive_dt(ts) -> datetime:
    """Strip timezone info so all timestamps stay offset-naive (DB candles are naive)."""
    if ts is None:
        return datetime.now()
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
        ts = ts.replace(tzinfo=None)
    return ts


class SMCService:
    @staticmethod
    async def detect_smc_patterns(db_session, symbol: str, timeframe: str = "1D"):
        """Analyze candles for Smart Money Concepts (SMC)."""
        symbol = symbol.upper()
        timeframe = timeframe.upper() if timeframe else "1D"
        
        # Map timeframe to minutes
        tf_mins = TimeframeMapper.to_minutes(timeframe)
        
        # 1. Look up symbol instrument id
        inst_query = select(InstrumentMaster).where(InstrumentMaster.symbol == symbol)
        inst_res = await db_session.execute(inst_query)
        instrument = inst_res.scalars().first()
        
        # -- Instrument Logging -------------------------------------------------
        if instrument:
            logger.info(
                f"SMC RESOLVE: Symbol={symbol} | Exchange={instrument.exchange} | "
                f"Key={instrument.instrument_key} | Active={instrument.is_active} | "
                f"InstrumentID={instrument.instrument_id}"
            )
        else:
            logger.warning(f"SMC RESOLVE: No instrument found for symbol={symbol}")
        
        candles = []
        
        # Determine Upstox fetch interval and dates based on timeframe
        if timeframe in ("5M", "5MIN"):
            interval = "5minute"
            lookback_days = 4
        elif timeframe in ("15M", "15MIN"):
            interval = "15minute"
            lookback_days = 10
        elif timeframe in ("30M", "30MIN"):
            interval = "30minute"
            lookback_days = 20
        elif timeframe in ("1H", "60MIN", "1HOUR"):
            interval = "60minute"
            lookback_days = 40
        else:
            interval = "day"
            lookback_days = 250
            
        to_date = datetime.now()
        from_date = to_date - timedelta(days=lookback_days)
        
        if instrument:
            # Query candles from database
            candle_query = select(StockCandle).where(
                StockCandle.instrument_id == instrument.instrument_id,
                StockCandle.timeframe == tf_mins
            ).order_by(StockCandle.candle_ts.desc()).limit(150)
            
            candle_res = await db_session.execute(candle_query)
            db_candles = candle_res.scalars().all()
            
            # Convert to local format (sorted chronologically)
            for c in reversed(db_candles):
                candles.append({
                    "open": float(c.open or 0.0),
                    "high": float(c.high or 0.0),
                    "low": float(c.low or 0.0),
                    "close": float(c.close or 0.0),
                    "volume": float(c.volume or 0.0),
                    "timestamp": c.candle_ts
                })
        
        # -- 2. Fetch Live LTP ---------------------------------------------------
        live_ltp = None
        live_quote = None
        upstox = None

        if instrument and instrument.instrument_key:
            try:
                from services.upstox_client import UpstoxClient
                upstox = UpstoxClient()
                live_quote = await upstox.get_live_quote(
                    instrument_key=instrument.instrument_key,
                    symbol=symbol
                )
                if live_quote:
                    live_ltp = float(live_quote.get("last_price") or 0.0)
                    logger.info(
                        f"SMC LIVE LTP: Symbol={symbol} | LTP={live_ltp} | "
                        f"PrevClose={live_quote.get('previous_close')} | "
                        f"Change%={live_quote.get('change_percent', 0):.2f}%"
                    )
            except Exception as e:
                logger.warning(f"SMC: Could not fetch live LTP for {symbol}: {e}")

        # -- 3. Candle Dataset Validation ----------------------------------------
        if candles:
            first_close = candles[0]["close"]
            last_close = candles[-1]["close"]
            min_price = min(c["low"] for c in candles)
            max_price = max(c["high"] for c in candles)
            latest_ts_stat = candles[-1]["timestamp"]
            logger.info(
                f"SMC CANDLES STAT: Symbol={symbol} | Count={len(candles)} | "
                f"FirstClose={first_close:.2f} | LastClose={last_close:.2f} | "
                f"Min={min_price:.2f} | Max={max_price:.2f} | LatestTS={latest_ts_stat} | "
                f"LiveLTP={live_ltp}"
            )

            # Cross-check: if last candle close deviates >5% from live LTP, reload from Upstox
            if live_ltp and live_ltp > 0 and last_close > 0:
                diff_pct = abs(live_ltp - last_close) / last_close
                if diff_pct > 0.05:
                    logger.warning(
                        f"SMC STALE DATA: {symbol} last_close={last_close:.2f} vs LTP={live_ltp:.2f} "
                        f"({diff_pct:.2%} diff). Triggering Upstox reload."
                    )
                    if upstox is None:
                        try:
                            from services.upstox_client import UpstoxClient
                            upstox = UpstoxClient()
                        except Exception:
                            pass
                    if upstox and instrument and instrument.instrument_key:
                        try:
                            df = await upstox.get_historical_data(
                                symbol=symbol,
                                instrument_key=instrument.instrument_key,
                                from_date=from_date,
                                to_date=to_date,
                                interval=interval
                            )
                            if not df.empty:
                                df = df.sort_values("timestamp")
                                reloaded = []
                                for _, row in df.iterrows():
                                    reloaded.append({
                                        "open": float(row["open"] or 0.0),
                                        "high": float(row["high"] or 0.0),
                                        "low": float(row["low"] or 0.0),
                                        "close": float(row["close"] or 0.0),
                                        "volume": float(row["volume"] or 0.0),
                                        "timestamp": _to_naive_dt(
                                            row["timestamp"].to_pydatetime()
                                            if hasattr(row["timestamp"], "to_pydatetime")
                                            else row["timestamp"]
                                        )
                                    })
                                if reloaded:
                                    candles = sorted(reloaded, key=lambda x: x["timestamp"])
                                    new_last_close = candles[-1]["close"]
                                    new_diff = abs(live_ltp - new_last_close) / new_last_close
                                    logger.info(
                                        f"SMC RELOAD OK: {symbol} new_last_close={new_last_close:.2f} "
                                        f"diff={new_diff:.2%}"
                                    )
                                    if new_diff > 0.15:
                                        logger.error(
                                            f"SMC REJECT: {symbol} persistent diff={new_diff:.2%} after reload. "
                                            f"LTP={live_ltp}, Close={new_last_close}"
                                        )
                                        return {
                                            "symbol": symbol, "timeframe": timeframe,
                                            "generatedAt": datetime.utcnow().isoformat() + "Z",
                                            "lastCandleTime": None,
                                            "error": (
                                                f"Price discrepancy too large: LTP={live_ltp:.2f}, "
                                                f"close={new_last_close:.2f} ({new_diff:.1%})"
                                            ),
                                            "fairValueGaps": [], "orderBlocks": [],
                                            "bos": [], "choch": [], "liquidityZones": [],
                                            "confidenceScore": 0, "dataQualityScore": 0,
                                            "order_blocks": [], "fair_value_gaps": [],
                                            "structural_events": [], "liquidity_zones": []
                                        }
                        except Exception as ue:
                            logger.error(f"SMC: Upstox reload failed for {symbol}: {ue}")
        
        # If DB has insufficient data or stale candles, fetch from Upstox REST API
        is_stale = False
        if candles:
            latest_ts = candles[-1]["timestamp"]
            stale_threshold = timedelta(minutes=2 * tf_mins) if tf_mins < 1440 else timedelta(days=2)
            if datetime.now() - latest_ts > stale_threshold:
                is_stale = True

        if (len(candles) < 100 or is_stale) and instrument and instrument.instrument_key:
            try:
                if upstox is None:
                    from services.upstox_client import UpstoxClient
                    upstox = UpstoxClient()
                df = await upstox.get_historical_data(
                    symbol=symbol,
                    instrument_key=instrument.instrument_key,
                    from_date=from_date,
                    to_date=to_date,
                    interval=interval
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
                            "volume": float(row["volume"] or 0.0),
                            "timestamp": _to_naive_dt(
                                row["timestamp"].to_pydatetime()
                                if hasattr(row["timestamp"], "to_pydatetime")
                                else row["timestamp"]
                            )
                        })
                    logger.info(f"Loaded {len(candles)} candles from Upstox API for {symbol} ({timeframe})")
            except Exception as ue:
                logger.error(f"Failed to fetch candles from Upstox API for {symbol} ({timeframe}): {ue}")

        # -- 4. Merge Today Live Quote as Active Candle --------------------------
        if live_quote and live_ltp and live_ltp > 0:
            try:
                quote_ts = _to_naive_dt(live_quote.get("timestamp"))
                live_open = float(live_quote.get("open") or live_ltp)
                live_high = float(live_quote.get("high") or live_ltp)
                live_low_val = float(live_quote.get("low") or live_ltp)
                live_volume = float(live_quote.get("volume") or 0.0)
                if candles:
                    last_ts = candles[-1]["timestamp"]
                    same_day = (hasattr(last_ts, "date") and hasattr(quote_ts, "date")
                                and last_ts.date() == quote_ts.date())
                    if same_day:
                        candles[-1]["close"] = live_ltp
                        candles[-1]["high"] = max(candles[-1]["high"], live_high)
                        candles[-1]["low"] = min(candles[-1]["low"], live_low_val)
                        logger.info(f"SMC LIVE MERGE: Updated last candle for {symbol} | close={live_ltp}")
                    else:
                        candles.append({
                            "open": live_open, "high": live_high,
                            "low": live_low_val, "close": live_ltp,
                            "volume": live_volume, "timestamp": quote_ts
                        })
                        logger.info(f"SMC LIVE MERGE: Appended live candle for {symbol} | close={live_ltp}")
            except Exception as me:
                logger.warning(f"SMC: Live candle merge failed for {symbol}: {me}")

        # --- DATA VALIDATION ---
        # 1. Deduplicate by timestamp
        seen_timestamps = set()
        unique_candles = []
        for c in candles:
            ts = c["timestamp"]
            if ts not in seen_timestamps:
                seen_timestamps.add(ts)
                unique_candles.append(c)
        candles = unique_candles
        
        # 2. Sort chronologically
        candles = sorted(candles, key=lambda x: x["timestamp"])
        
        # 3. Filter out invalid/corrupted candles
        valid_candles = []
        for c in candles:
            if (c["open"] > 0 and c["high"] > 0 and c["low"] > 0 and c["close"] > 0 and 
                c["high"] >= c["low"] and c["high"] >= c["open"] and c["high"] >= c["close"]):
                valid_candles.append(c)
        candles = valid_candles

        if len(candles) < 20:
            logger.warning(f"SMC: Insufficient validated candles ({len(candles)}) for {symbol}. Returning empty results.")
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "generatedAt": datetime.utcnow().isoformat() + "Z",
                "lastCandleTime": candles[-1]["timestamp"].isoformat() if candles else None,
                "fairValueGaps": [],
                "orderBlocks": [],
                "bos": [],
                "choch": [],
                "liquidityZones": [],
                "confidenceScore": 0,
                "dataQualityScore": 0,
                "fair_value_gaps": [],
                "order_blocks": [],
                "structural_events": [],
                "liquidity_zones": []
            }
            
        n = len(candles)
        last_candle_time = candles[-1]["timestamp"].isoformat()
        
        # Calculate scores
        data_quality_score = min(100, int((len(candles) / 150) * 100))
        
        # --- 1. DETECT FAIR VALUE GAPS (FVG) ---
        fvgs = []
        avg_price = sum(c["close"] for c in candles) / n
        min_width = avg_price * 0.0005  # minimum 0.05% width to avoid noise
        
        for i in range(2, n):
            c1 = candles[i-2]
            c2 = candles[i-1]
            c3 = candles[i]
            
            # Bullish FVG: Low of candle 3 is above high of candle 1
            if c3["low"] > c1["high"]:
                width = c3["low"] - c1["high"]
                if width >= min_width:
                    # Check mitigation in subsequent candles
                    mitigated = False
                    fill_percent = 0.0
                    for j in range(i+1, n):
                        if candles[j]["low"] <= c1["high"]:
                            mitigated = True
                            fill_percent = 100.0
                            break
                        elif candles[j]["low"] < c3["low"]:
                            # Partial mitigation
                            current_fill = ((c3["low"] - candles[j]["low"]) / width) * 100.0
                            fill_percent = max(fill_percent, current_fill)
                            
                    if not mitigated:
                        fvg_mid = (c3["low"] + c1["high"]) / 2
                        if _is_within_range(fvg_mid, live_ltp):
                            fvgs.append({
                                "type": "BULLISH",
                                "top": c3["low"],
                                "bottom": c1["high"],
                                "width": round(width, 2),
                                "fillPercent": round(fill_percent, 1),
                                "timestamp": c2["timestamp"].strftime("%Y-%m-%d %H:%M"),
                                "mitigated": mitigated,
                                "age": n - 1 - i
                            })
                        
            # Bearish FVG: High of candle 3 is below low of candle 1
            elif c3["high"] < c1["low"]:
                width = c1["low"] - c3["high"]
                if width >= min_width:
                    # Check mitigation in subsequent candles
                    mitigated = False
                    fill_percent = 0.0
                    for j in range(i+1, n):
                        if candles[j]["high"] >= c1["low"]:
                            mitigated = True
                            fill_percent = 100.0
                            break
                        elif candles[j]["high"] > c3["high"]:
                            # Partial mitigation
                            current_fill = ((candles[j]["high"] - c3["high"]) / width) * 100.0
                            fill_percent = max(fill_percent, current_fill)
                            
                    if not mitigated:
                        fvg_mid = (c1["low"] + c3["high"]) / 2
                        if _is_within_range(fvg_mid, live_ltp):
                            fvgs.append({
                                "type": "BEARISH",
                                "top": c1["low"],
                                "bottom": c3["high"],
                                "width": round(width, 2),
                                "fillPercent": round(fill_percent, 1),
                                "timestamp": c2["timestamp"].strftime("%Y-%m-%d %H:%M"),
                                "mitigated": mitigated,
                                "age": n - 1 - i
                            })

        # --- 2. DETECT ORDER BLOCKS (OB) ---
        order_blocks = []
        # Calculate moving average of volume
        volumes = [c["volume"] for c in candles]
        
        for i in range(5, n):
            # Bullish OB: Precedes bullish displacement and structure break
            # 1.5% displacement over 3 candles
            bullish_displacement = (candles[i]["close"] - candles[i-3]["open"]) / candles[i-3]["open"] > 0.015
            
            if bullish_displacement:
                # Volatility/Volume validation: Volume must be above 1.2x of MA of previous 10 candles
                vol_ma = sum(volumes[max(0, i-10):i]) / 10 if i >= 10 else sum(volumes[:i]) / i if i > 0 else 1
                volume_valid = candles[i]["volume"] > 1.2 * vol_ma
                
                if volume_valid:
                    # Preceding bearish candle
                    for j in range(i-3, i-6, -1):
                        if j >= 0 and candles[j]["close"] < candles[j]["open"]:
                            ob_high = candles[j]["high"]
                            ob_low = candles[j]["low"]
                            
                            # Mitigation check
                            mitigated = False
                            for k in range(i+1, n):
                                if candles[k]["close"] < ob_low:  # Fully invalidated/closed below low
                                    mitigated = True
                                    break
                                    
                            if not mitigated:
                                ob_mid = (ob_high + ob_low) / 2
                                if _is_within_range(ob_mid, live_ltp):
                                    strength_val = round(((candles[i]["close"] - candles[i-3]["open"]) / candles[i-3]["open"]) * 100, 2)
                                    order_blocks.append({
                                        "type": "BULLISH",
                                        "high": ob_high,
                                        "low": ob_low,
                                        "timestamp": candles[j]["timestamp"].strftime("%Y-%m-%d %H:%M"),
                                        "mitigated": mitigated,
                                        "strength": strength_val,
                                        "freshness": True
                                    })
                            break
                            
            # Bearish OB: Precedes bearish displacement and structure break
            bearish_displacement = (candles[i-3]["open"] - candles[i]["close"]) / candles[i-3]["open"] > 0.015
            if bearish_displacement:
                vol_ma = sum(volumes[max(0, i-10):i]) / 10 if i >= 10 else sum(volumes[:i]) / i if i > 0 else 1
                volume_valid = candles[i]["volume"] > 1.2 * vol_ma
                
                if volume_valid:
                    # Preceding bullish candle
                    for j in range(i-3, i-6, -1):
                        if j >= 0 and candles[j]["close"] > candles[j]["open"]:
                            ob_high = candles[j]["high"]
                            ob_low = candles[j]["low"]
                            
                            # Mitigation check
                            mitigated = False
                            for k in range(i+1, n):
                                if candles[k]["close"] > ob_high:  # Fully invalidated/closed above high
                                    mitigated = True
                                    break
                                    
                            if not mitigated:
                                ob_mid = (ob_high + ob_low) / 2
                                if _is_within_range(ob_mid, live_ltp):
                                    strength_val = round(((candles[i-3]["open"] - candles[i]["close"]) / candles[i-3]["open"]) * 100, 2)
                                    order_blocks.append({
                                        "type": "BEARISH",
                                        "high": ob_high,
                                        "low": ob_low,
                                        "timestamp": candles[j]["timestamp"].strftime("%Y-%m-%d %H:%M"),
                                        "mitigated": mitigated,
                                        "strength": strength_val,
                                        "freshness": True
                                    })
                            break

        # --- 3. DETECT BOS / CHOCH ---
        highs = []
        lows = []
        # Find Swing Highs & Swing Lows (window size 2)
        for i in range(2, n-2):
            # Swing High
            if (candles[i]["high"] > candles[i-1]["high"] and candles[i]["high"] > candles[i-2]["high"] and
                candles[i]["high"] > candles[i+1]["high"] and candles[i]["high"] > candles[i+2]["high"]):
                highs.append({
                    "price": candles[i]["high"],
                    "index": i,
                    "timestamp": candles[i]["timestamp"]
                })
            # Swing Low
            if (candles[i]["low"] < candles[i-1]["low"] and candles[i]["low"] < candles[i-2]["low"] and
                candles[i]["low"] < candles[i+1]["low"] and candles[i]["low"] < candles[i+2]["low"]):
                lows.append({
                    "price": candles[i]["low"],
                    "index": i,
                    "timestamp": candles[i]["timestamp"]
                })

        bos_list = []
        choch_list = []
        
        # Simple trend tracker: start bullish if first close is above open
        current_trend = "BULLISH" if candles[5]["close"] > candles[0]["open"] else "BEARISH"
        
        active_highs = list(highs)
        active_lows = list(lows)
        
        for i in range(3, n):
            curr_close = candles[i]["close"]
            curr_ts = candles[i]["timestamp"].strftime("%Y-%m-%d %H:%M")
            
            # Check swing high breach (Bullish continuation or bearish reversal)
            for sh in list(active_highs):
                if sh["index"] < i and curr_close > sh["price"]:
                    if _is_within_range(sh["price"], live_ltp):
                        if current_trend == "BEARISH":
                            current_trend = "BULLISH"
                            choch_list.append({
                                "type": "BULLISH",
                                "event": "CHOCH",
                                "level": sh["price"],
                                "timestamp": curr_ts,
                                "origin_date": sh["timestamp"].strftime("%Y-%m-%d %H:%M"),
                                "strength": 2.0
                            })
                        else:
                            bos_list.append({
                                "type": "BULLISH",
                                "event": "BOS",
                                "level": sh["price"],
                                "timestamp": curr_ts,
                                "origin_date": sh["timestamp"].strftime("%Y-%m-%d %H:%M"),
                                "strength": 1.0
                            })
                    active_highs.remove(sh)
                    break
                    
            # Check swing low breach (Bearish continuation or bullish reversal)
            for sl in list(active_lows):
                if sl["index"] < i and curr_close < sl["price"]:
                    if _is_within_range(sl["price"], live_ltp):
                        if current_trend == "BULLISH":
                            current_trend = "BEARISH"
                            choch_list.append({
                                "type": "BEARISH",
                                "event": "CHOCH",
                                "level": sl["price"],
                                "timestamp": curr_ts,
                                "origin_date": sl["timestamp"].strftime("%Y-%m-%d %H:%M"),
                                "strength": 2.0
                            })
                        else:
                            bos_list.append({
                                "type": "BEARISH",
                                "event": "BOS",
                                "level": sl["price"],
                                "timestamp": curr_ts,
                                "origin_date": sl["timestamp"].strftime("%Y-%m-%d %H:%M"),
                                "strength": 1.0
                            })
                    active_lows.remove(sl)
                    break

        # --- 4. DETECT LIQUIDITY ZONES ---
        liquidity_zones = []
        # Buy Side Liquidity (BSL) - Equal Highs
        for i in range(len(highs)):
            for j in range(i+1, len(highs)):
                sh1 = highs[i]
                sh2 = highs[j]
                
                # Check if prices are within 0.25% of each other
                diff = abs(sh1["price"] - sh2["price"]) / sh1["price"]
                if diff < 0.0025:
                    lz_level = (sh1["price"] + sh2["price"]) / 2
                    if _is_within_range(lz_level, live_ltp):
                        liquidity_zones.append({
                            "type": "BSL",
                            "level": round(lz_level, 2),
                            "range_top": round(max(sh1["price"], sh2["price"]), 2),
                            "range_bottom": round(min(sh1["price"], sh2["price"]), 2),
                            "strength": 2,
                            "age": n - 1 - sh2["index"],
                            "timestamp": sh2["timestamp"].strftime("%Y-%m-%d %H:%M")
                        })
                    
        # Sell Side Liquidity (SSL) - Equal Lows
        for i in range(len(lows)):
            for j in range(i+1, len(lows)):
                sl1 = lows[i]
                sl2 = lows[j]
                
                diff = abs(sl1["price"] - sl2["price"]) / sl1["price"]
                if diff < 0.0025:
                    lz_level = (sl1["price"] + sl2["price"]) / 2
                    if _is_within_range(lz_level, live_ltp):
                        liquidity_zones.append({
                            "type": "SSL",
                            "level": round(lz_level, 2),
                            "range_top": round(max(sl1["price"], sl2["price"]), 2),
                            "range_bottom": round(min(sl1["price"], sl2["price"]), 2),
                            "strength": 2,
                            "age": n - 1 - sl2["index"],
                            "timestamp": sl2["timestamp"].strftime("%Y-%m-%d %H:%M")
                        })

        # Fallback: nearest major swing points within current price range
        if not liquidity_zones:
            nearby_highs = [h for h in highs if _is_within_range(h["price"], live_ltp)]
            nearby_lows = [l for l in lows if _is_within_range(l["price"], live_ltp)]
            if nearby_highs:
                major_high = max(nearby_highs, key=lambda x: x["price"])
                liquidity_zones.append({
                    "type": "BSL",
                    "level": round(major_high["price"], 2),
                    "range_top": round(major_high["price"] * 1.001, 2),
                    "range_bottom": round(major_high["price"] * 0.999, 2),
                    "strength": 1,
                    "age": n - 1 - major_high["index"],
                    "timestamp": major_high["timestamp"].strftime("%Y-%m-%d %H:%M")
                })
            if nearby_lows:
                major_low = min(nearby_lows, key=lambda x: x["price"])
                liquidity_zones.append({
                    "type": "SSL",
                    "level": round(major_low["price"], 2),
                    "range_top": round(major_low["price"] * 1.001, 2),
                    "range_bottom": round(major_low["price"] * 0.999, 2),
                    "strength": 1,
                    "age": n - 1 - major_low["index"],
                    "timestamp": major_low["timestamp"].strftime("%Y-%m-%d %H:%M")
                })

        # Compute confidence score
        confidence_score = min(95, 50 + len(order_blocks) * 10 + len(fvgs) * 5)
        
        # Combine structural events for legacy compatibility
        legacy_structural = bos_list[:4] + choch_list[:4]
        legacy_structural = sorted(legacy_structural, key=lambda x: x["timestamp"], reverse=True)
        
        logger.info(
            f"SMC COMPLETE: {symbol} ({timeframe}) | Candles: {n} | LiveLTP: {live_ltp} | "
            f"OBs: {len(order_blocks)} | FVGs: {len(fvgs)} | BOS: {len(bos_list)} | "
            f"CHOCH: {len(choch_list)} | Liquidity: {len(liquidity_zones)}"
        )
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "generatedAt": datetime.utcnow().isoformat() + "Z",
            "lastCandleTime": last_candle_time,
            "liveLTP": live_ltp,

            "orderBlocks": order_blocks[:6],
            "fairValueGaps": fvgs[:6],
            "bos": bos_list[:6],
            "choch": choch_list[:6],
            "liquidityZones": liquidity_zones[:5],

            "confidenceScore": confidence_score,
            "dataQualityScore": data_quality_score,

            # Legacy compatibility
            "order_blocks": order_blocks[:6],
            "fair_value_gaps": fvgs[:6],
            "structural_events": legacy_structural,
            "liquidity_zones": liquidity_zones[:5]
        }

    @staticmethod
    async def get_diagnostics(db_session, symbol: str):
        """Return SMC dataset diagnostics for a symbol without running full calculations."""
        symbol = symbol.upper()
        inst_query = select(InstrumentMaster).where(InstrumentMaster.symbol == symbol)
        inst_res = await db_session.execute(inst_query)
        instrument = inst_res.scalars().first()

        diag = {
            "symbol": symbol,
            "instrument_found": instrument is not None,
            "instrument_key": instrument.instrument_key if instrument else None,
            "exchange": instrument.exchange if instrument else None,
            "is_active": instrument.is_active if instrument else None,
            "db_candle_count_daily": 0,
            "db_first_close": None,
            "db_last_close": None,
            "db_latest_ts": None,
            "db_price_min": None,
            "db_price_max": None,
            "live_ltp": None,
            "live_prev_close": None,
            "live_change_pct": None,
            "ltp_vs_db_diff_pct": None,
            "data_aligned": None,
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }

        if instrument:
            candle_query = select(StockCandle).where(
                StockCandle.instrument_id == instrument.instrument_id,
                StockCandle.timeframe == 1440
            ).order_by(StockCandle.candle_ts.asc())
            candle_res = await db_session.execute(candle_query)
            db_candles = candle_res.scalars().all()
            diag["db_candle_count_daily"] = len(db_candles)

            if db_candles:
                closes = [float(c.close or 0) for c in db_candles if c.close]
                lows = [float(c.low or 0) for c in db_candles if c.low]
                highs = [float(c.high or 0) for c in db_candles if c.high]
                diag["db_first_close"] = closes[0] if closes else None
                diag["db_last_close"] = closes[-1] if closes else None
                diag["db_latest_ts"] = db_candles[-1].candle_ts.isoformat() if db_candles else None
                diag["db_price_min"] = min(lows) if lows else None
                diag["db_price_max"] = max(highs) if highs else None

            try:
                from services.upstox_client import UpstoxClient
                upstox = UpstoxClient()
                live_quote = await upstox.get_live_quote(
                    instrument_key=instrument.instrument_key,
                    symbol=symbol
                )
                if live_quote:
                    diag["live_ltp"] = live_quote.get("last_price")
                    diag["live_prev_close"] = live_quote.get("previous_close")
                    diag["live_change_pct"] = live_quote.get("change_percent")
                    if diag["db_last_close"] and diag["live_ltp"]:
                        diff = abs(diag["live_ltp"] - diag["db_last_close"]) / diag["db_last_close"]
                        diag["ltp_vs_db_diff_pct"] = round(diff * 100, 2)
                        diag["data_aligned"] = diff <= 0.05
            except Exception as e:
                diag["live_quote_error"] = str(e)

        return diag
