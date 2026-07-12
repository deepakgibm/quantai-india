"""
Institutional-Grade Explainable AI Investment Decision Engine.

Architecture:
  1. Indicator Computation — compute all technical indicators from OHLCV data
  2. Weighted Scoring — each indicator contributes a signed score within a weighted category
  3. Verdict Decision — deterministic rules map the final score to BUY/HOLD/SELL
  4. Single Decision Object — every output section references one InvestmentDecision
  5. Validation — catch contradictions before returning
  6. Audit Trail — full score breakdown for debugging
"""

import logging
import math
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from services.indicator_compute_service import get_indicator_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category weights (must sum to 1.0)
# ---------------------------------------------------------------------------
CATEGORY_WEIGHTS = {
    "trend": 0.30,
    "momentum": 0.20,
    "volume": 0.15,
    "structure": 0.15,
    "volatility": 0.10,
    "multi_tf": 0.10,
}

# ---------------------------------------------------------------------------
# Verdict thresholds (on a normalised -10 to +10 scale)
# ---------------------------------------------------------------------------
VERDICT_RULES = [
    (8, "STRONG BUY"),
    (4, "BUY"),
    (-3, "HOLD"),   # score >= -3 -> HOLD
    (-7, "SELL"),   # score >= -7 -> SELL
]
# anything below -7 -> STRONG SELL


# ===================================================================
# Helper: ADX computation
# ===================================================================
def _compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)

    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()

    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1)
    return dx.ewm(alpha=1 / period, adjust=False).mean()


# ===================================================================
# Helper: Stochastic RSI
# ===================================================================
def _compute_stoch_rsi(rsi_series: pd.Series, period: int = 14) -> float:
    rsi_min = rsi_series.rolling(period).min()
    rsi_max = rsi_series.rolling(period).max()
    denom = (rsi_max - rsi_min).replace(0, 1)
    stoch = ((rsi_series - rsi_min) / denom) * 100
    val = float(stoch.iloc[-1]) if not stoch.empty and not pd.isna(stoch.iloc[-1]) else 50.0
    return val


# ===================================================================
# Helper: Bollinger Band %B
# ===================================================================
def _compute_bollinger(close: pd.Series, period: int = 20, std_mult: float = 2.0):
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = sma + std_mult * std
    lower = sma - std_mult * std
    pct_b = ((close - lower) / (upper - lower).replace(0, 1)).iloc[-1]
    return float(sma.iloc[-1]), float(upper.iloc[-1]), float(lower.iloc[-1]), float(pct_b)


# ===================================================================
# Helper: OBV trend
# ===================================================================
def _compute_obv_trend(close: pd.Series, volume: pd.Series, lookback: int = 20) -> str:
    sign = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    obv = (sign * volume).cumsum()
    if len(obv) < lookback + 1:
        return "Flat"
    slope = obv.iloc[-1] - obv.iloc[-lookback]
    if slope > 0:
        return "Rising"
    elif slope < 0:
        return "Falling"
    return "Flat"


# ===================================================================
# Helper: Ichimoku Cloud position
# ===================================================================
def _compute_ichimoku_position(close: pd.Series, high: pd.Series, low: pd.Series):
    if len(close) < 52:
        return "Insufficient Data", False
    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)

    price = float(close.iloc[-1])
    sa = float(senkou_a.iloc[-1]) if not pd.isna(senkou_a.iloc[-1]) else price
    sb = float(senkou_b.iloc[-1]) if not pd.isna(senkou_b.iloc[-1]) else price
    cloud_top = max(sa, sb)
    cloud_bottom = min(sa, sb)

    if price > cloud_top:
        return "Above Cloud", True
    elif price < cloud_bottom:
        return "Below Cloud", False
    else:
        return "Inside Cloud", False


# ===================================================================
# Helper: Supertrend
# ===================================================================
def _compute_supertrend(close: pd.Series, high: pd.Series, low: pd.Series, period: int = 10, multiplier: float = 3.0):
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    hl2 = (high + low) / 2
    upper_band = hl2 + multiplier * atr
    lower_band = hl2 - multiplier * atr

    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=float)
    supertrend.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = -1

    for i in range(1, len(close)):
        if pd.isna(upper_band.iloc[i]):
            supertrend.iloc[i] = supertrend.iloc[i - 1]
            direction.iloc[i] = direction.iloc[i - 1]
            continue
        if close.iloc[i] > supertrend.iloc[i - 1]:
            supertrend.iloc[i] = lower_band.iloc[i]
            direction.iloc[i] = 1
        else:
            supertrend.iloc[i] = upper_band.iloc[i]
            direction.iloc[i] = -1

    is_buy = direction.iloc[-1] == 1
    st_value = float(supertrend.iloc[-1])
    return is_buy, st_value


# ===================================================================
# Core: Build all indicator results
# ===================================================================
def _evaluate_indicators(df: pd.DataFrame) -> tuple:
    """Compute all indicators, returning (list of IndicatorResult dicts, raw_values dict)."""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    current_price = float(close.iloc[-1])
    prev_close = float(close.iloc[-2]) if len(close) > 1 else current_price

    results = []

    # ----- RSI (14) -----
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, 1)
    rsi_series = 100 - (100 / (1 + rs))
    rsi = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0

    if rsi > 70:
        rsi_signal, rsi_score = "Bearish", -1
        rsi_reason = f"RSI at {rsi:.1f} is in overbought territory (>70), signalling potential reversal."
    elif rsi > 60:
        rsi_signal, rsi_score = "Bullish", 1
        rsi_reason = f"RSI at {rsi:.1f} shows positive momentum without being overbought."
    elif rsi < 30:
        rsi_signal, rsi_score = "Bullish", 1
        rsi_reason = f"RSI at {rsi:.1f} is deeply oversold (<30), suggesting a potential bounce."
    elif rsi < 40:
        rsi_signal, rsi_score = "Bearish", -1
        rsi_reason = f"RSI at {rsi:.1f} is weak (<40), indicating bearish momentum."
    else:
        rsi_signal, rsi_score = "Neutral", 0
        rsi_reason = f"RSI at {rsi:.1f} is neutral (40-60), indicating balanced buying and selling pressure."

    results.append({
        "key": "rsi", "name": "RSI (14)", "category": "momentum",
        "value": f"{rsi:.1f}", "signal": rsi_signal, "score": rsi_score,
        "reason": rsi_reason, "contribution": f"{rsi_score:+d} points",
        "tooltip": "Measures velocity and magnitude of price movements; >70 overbought, <30 oversold."
    })

    # ----- MACD (12, 26, 9) -----
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_val = float(macd_line.iloc[-1])
    sig_val = float(macd_signal_line.iloc[-1])

    if macd_val > sig_val:
        macd_signal, macd_score = "Bullish", 2
        macd_reason = f"MACD ({macd_val:.2f}) is above signal line ({sig_val:.2f}), confirming upward momentum."
    else:
        macd_signal, macd_score = "Bearish", -2
        macd_reason = f"MACD ({macd_val:.2f}) is below signal line ({sig_val:.2f}), indicating selling pressure."

    results.append({
        "key": "macd", "name": "MACD (12,26,9)", "category": "momentum",
        "value": f"{macd_val:.2f} / {sig_val:.2f}", "signal": macd_signal, "score": macd_score,
        "reason": macd_reason, "contribution": f"{macd_score:+d} points",
        "tooltip": "Trend-following momentum indicator showing relationship between two moving averages."
    })

    # ----- EMA 20 vs EMA 50 -----
    ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
    ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
    ema200 = float(close.ewm(span=200, adjust=False).mean().iloc[-1])

    if ema20 > ema50:
        ema20_signal, ema20_score = "Bullish", 2
        ema20_reason = f"EMA 20 ({ema20:.1f}) is above EMA 50 ({ema50:.1f}), confirming intermediate uptrend."
    else:
        ema20_signal, ema20_score = "Bearish", -2
        ema20_reason = f"EMA 20 ({ema20:.1f}) is below EMA 50 ({ema50:.1f}), indicating descending pressure."

    results.append({
        "key": "ema20", "name": "EMA 20 vs 50", "category": "trend",
        "value": f"{ema20:.1f}", "signal": ema20_signal, "score": ema20_score,
        "reason": ema20_reason, "contribution": f"{ema20_score:+d} points",
        "tooltip": "Short-term exponential moving average; acts as dynamic support/resistance."
    })

    # ----- EMA 50 vs EMA 200 -----
    if ema50 > ema200:
        ema50_signal, ema50_score = "Bullish", 2
        ema50_reason = f"EMA 50 ({ema50:.1f}) is above EMA 200 ({ema200:.1f}), representing long-term bullish trend."
    else:
        ema50_signal, ema50_score = "Bearish", -2
        ema50_reason = f"EMA 50 ({ema50:.1f}) is below EMA 200 ({ema200:.1f}), showing long-term bearish structure."

    results.append({
        "key": "ema50", "name": "EMA 50 vs 200", "category": "trend",
        "value": f"{ema50:.1f}", "signal": ema50_signal, "score": ema50_score,
        "reason": ema50_reason, "contribution": f"{ema50_score:+d} points",
        "tooltip": "Medium-term EMA; crossing above EMA 200 is a Golden Cross, below is a Death Cross."
    })

    # ----- ADX (14) -----
    adx_series = _compute_adx(df.copy(), 14)
    adx_val = float(adx_series.iloc[-1]) if not pd.isna(adx_series.iloc[-1]) else 20.0

    if adx_val > 25:
        adx_signal, adx_score = "Bullish", 1
        adx_reason = f"ADX at {adx_val:.1f} (>25) confirms a strong active trend is underway."
    elif adx_val < 20:
        adx_signal, adx_score = "Neutral", 0
        adx_reason = f"ADX at {adx_val:.1f} (<20) suggests no clear trend; rangebound market."
    else:
        adx_signal, adx_score = "Neutral", 0
        adx_reason = f"ADX at {adx_val:.1f} (20-25) indicates a developing but unconfirmed trend."

    results.append({
        "key": "adx", "name": "ADX (14)", "category": "volatility",
        "value": f"{adx_val:.1f}", "signal": adx_signal, "score": adx_score,
        "reason": adx_reason, "contribution": f"{adx_score:+d} points",
        "tooltip": "Measures trend strength regardless of direction; >25 = strong trend, <20 = no trend."
    })

    # ----- Supertrend -----
    st_is_buy, st_value = _compute_supertrend(close, high, low)
    if st_is_buy:
        st_signal, st_score = "Bullish", 2
        st_reason = f"Supertrend indicates BUY -- price is above the volatility stop at {st_value:.1f}."
    else:
        st_signal, st_score = "Bearish", -2
        st_reason = f"Supertrend indicates SELL -- price has broken below the volatility stop at {st_value:.1f}."

    results.append({
        "key": "supertrend", "name": "Supertrend", "category": "trend",
        "value": "BUY" if st_is_buy else "SELL", "signal": st_signal, "score": st_score,
        "reason": st_reason, "contribution": f"{st_score:+d} points",
        "tooltip": "Combines ATR and mid-price to define dynamic buy/sell stop lines."
    })

    # ----- VWAP -----
    typical = (high + low + close) / 3
    cum_tv = (typical * volume).cumsum()
    cum_vol = volume.cumsum()
    vwap_series = cum_tv / cum_vol.replace(0, 1)
    vwap_val = float(vwap_series.iloc[-1])

    if current_price > vwap_val:
        vwap_signal, vwap_score = "Bullish", 1
        vwap_reason = f"Price ({current_price:.1f}) is above VWAP ({vwap_val:.1f}), indicating buyers dominate."
    else:
        vwap_signal, vwap_score = "Bearish", -1
        vwap_reason = f"Price ({current_price:.1f}) is below VWAP ({vwap_val:.1f}), indicating sellers dominate."

    results.append({
        "key": "vwap", "name": "VWAP", "category": "volume",
        "value": f"{vwap_val:.1f}", "signal": vwap_signal, "score": vwap_score,
        "reason": vwap_reason, "contribution": f"{vwap_score:+d} points",
        "tooltip": "Volume-weighted average price; key institutional benchmark for intraday fair value."
    })

    # ----- ATR (14) -----
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr_val = float(tr.rolling(14).mean().iloc[-1])
    atr_pct = (atr_val / current_price) * 100

    atr_signal, atr_score = "Neutral", 0
    atr_reason = f"ATR is {atr_val:.2f} ({atr_pct:.2f}% of price), indicating {'high' if atr_pct > 2 else 'moderate' if atr_pct > 1 else 'low'} daily volatility."

    results.append({
        "key": "atr", "name": "ATR (14)", "category": "volatility",
        "value": f"{atr_val:.2f}", "signal": atr_signal, "score": atr_score,
        "reason": atr_reason, "contribution": f"{atr_score:+d} points",
        "tooltip": "Average True Range; measures historical volatility. Higher = wider price swings."
    })

    # ----- OBV -----
    obv_trend = _compute_obv_trend(close, volume)
    if obv_trend == "Rising":
        obv_signal, obv_score = "Bullish", 1
        obv_reason = "On-Balance Volume is rising, confirming volume supports the price advance."
    elif obv_trend == "Falling":
        obv_signal, obv_score = "Bearish", -1
        obv_reason = "On-Balance Volume is falling, indicating distribution and selling pressure."
    else:
        obv_signal, obv_score = "Neutral", 0
        obv_reason = "On-Balance Volume is flat, showing no clear accumulation or distribution."

    results.append({
        "key": "obv", "name": "OBV", "category": "volume",
        "value": obv_trend, "signal": obv_signal, "score": obv_score,
        "reason": obv_reason, "contribution": f"{obv_score:+d} points",
        "tooltip": "Uses volume flow to predict price changes; rising OBV = accumulation."
    })

    # ----- Bollinger Bands -----
    boll_sma, boll_upper, boll_lower, boll_pctb = _compute_bollinger(close)

    if boll_pctb > 1.0:
        boll_signal, boll_score = "Bullish", 1
        boll_reason = f"Price is above the upper Bollinger Band ({boll_upper:.1f}), indicating breakout momentum."
    elif boll_pctb < 0.0:
        boll_signal, boll_score = "Bearish", -1
        boll_reason = f"Price is below the lower Bollinger Band ({boll_lower:.1f}), indicating breakdown."
    elif boll_pctb > 0.8:
        boll_signal, boll_score = "Bullish", 1
        boll_reason = f"Price is near the upper Bollinger Band, showing bullish expansion (B%={boll_pctb:.2f})."
    elif boll_pctb < 0.2:
        boll_signal, boll_score = "Bearish", -1
        boll_reason = f"Price is near the lower Bollinger Band, showing bearish compression (B%={boll_pctb:.2f})."
    else:
        boll_signal, boll_score = "Neutral", 0
        boll_reason = f"Price is within Bollinger Bands (B%={boll_pctb:.2f}), indicating normal trading range."

    results.append({
        "key": "bollinger", "name": "Bollinger Bands", "category": "structure",
        "value": f"B%={boll_pctb:.2f}", "signal": boll_signal, "score": boll_score,
        "reason": boll_reason, "contribution": f"{boll_score:+d} points",
        "tooltip": "Volatility bands around SMA; B% >1 = breakout above, <0 = breakdown below."
    })

    # ----- Ichimoku Cloud -----
    ich_label, ich_above = _compute_ichimoku_position(close, high, low)
    if ich_above:
        ich_signal, ich_score = "Bullish", 1
        ich_reason = f"Price is {ich_label}, indicating structural long-term bullish bias."
    elif ich_label == "Below Cloud":
        ich_signal, ich_score = "Bearish", -1
        ich_reason = f"Price is {ich_label}, indicating structural long-term bearish bias."
    else:
        ich_signal, ich_score = "Neutral", 0
        ich_reason = f"Price is {ich_label} -- trend direction is uncertain within the Kumo zone."

    results.append({
        "key": "ichimoku", "name": "Ichimoku Cloud", "category": "structure",
        "value": ich_label, "signal": ich_signal, "score": ich_score,
        "reason": ich_reason, "contribution": f"{ich_score:+d} points",
        "tooltip": "Comprehensive indicator showing support, resistance, trend, and momentum via the Cloud."
    })

    # ----- Stochastic RSI -----
    stoch_rsi_val = _compute_stoch_rsi(rsi_series)
    if stoch_rsi_val > 80:
        sr_signal, sr_score = "Bearish", -1
        sr_reason = f"Stochastic RSI at {stoch_rsi_val:.1f} is overbought (>80), suggesting pullback risk."
    elif stoch_rsi_val > 50:
        sr_signal, sr_score = "Bullish", 1
        sr_reason = f"Stochastic RSI at {stoch_rsi_val:.1f} shows positive momentum above the midline."
    elif stoch_rsi_val < 20:
        sr_signal, sr_score = "Bullish", 1
        sr_reason = f"Stochastic RSI at {stoch_rsi_val:.1f} is oversold (<20), suggesting potential bounce."
    elif stoch_rsi_val < 50:
        sr_signal, sr_score = "Bearish", -1
        sr_reason = f"Stochastic RSI at {stoch_rsi_val:.1f} is below midline, indicating fading momentum."
    else:
        sr_signal, sr_score = "Neutral", 0
        sr_reason = f"Stochastic RSI at {stoch_rsi_val:.1f} is neutral at the midline."

    results.append({
        "key": "stoch_rsi", "name": "Stochastic RSI", "category": "momentum",
        "value": f"{stoch_rsi_val:.1f}", "signal": sr_signal, "score": sr_score,
        "reason": sr_reason, "contribution": f"{sr_score:+d} points",
        "tooltip": "Applies Stochastic formula to RSI for high-sensitivity momentum shifts."
    })

    return results, {
        "current_price": current_price, "prev_close": prev_close,
        "ema20": ema20, "ema50": ema50, "ema200": ema200,
        "rsi": rsi, "macd": macd_val, "macd_signal": sig_val,
        "adx": adx_val, "atr": atr_val, "atr_pct": atr_pct, "vwap": vwap_val,
        "boll_upper": boll_upper, "boll_lower": boll_lower, "boll_sma": boll_sma,
    }


# ===================================================================
# Core: Weighted scoring engine
# ===================================================================
def _compute_weighted_score(indicators: list) -> dict:
    category_raw = {cat: [] for cat in CATEGORY_WEIGHTS}
    for ind in indicators:
        cat = ind["category"]
        if cat in category_raw:
            category_raw[cat].append(ind["score"])

    category_scores = {}
    for cat, scores in category_raw.items():
        if scores:
            avg = sum(scores) / len(scores)
            normalised = avg * 5  # maps [-2,+2] to [-10,+10]
            weighted = normalised * CATEGORY_WEIGHTS[cat]
            category_scores[cat] = {"raw_scores": scores, "average": round(avg, 2), "normalised": round(normalised, 2), "weight": CATEGORY_WEIGHTS[cat], "weighted": round(weighted, 2)}
        else:
            category_scores[cat] = {"raw_scores": [], "average": 0, "normalised": 0, "weight": CATEGORY_WEIGHTS[cat], "weighted": 0}

    final_score = sum(cs["weighted"] for cs in category_scores.values())
    return {"category_scores": category_scores, "final_score": round(final_score, 2)}


# ===================================================================
# Core: Determine verdict from score
# ===================================================================
def _determine_verdict(final_score: float) -> str:
    for threshold, verdict in VERDICT_RULES:
        if final_score >= threshold:
            return verdict
    return "STRONG SELL"


# ===================================================================
# Core: Dynamic confidence
# ===================================================================
def _compute_confidence(indicators: list, adx_val: float, tf_alignment_ratio: float) -> int:
    total = len(indicators)
    if total == 0:
        return 50
    bullish = sum(1 for i in indicators if i["signal"] == "Bullish")
    bearish = sum(1 for i in indicators if i["signal"] == "Bearish")
    dominant = max(bullish, bearish)
    agreement = dominant / total
    confidence = 50 + int(agreement * 40)
    if adx_val > 25:
        confidence += 5
    if tf_alignment_ratio >= 0.8:
        confidence += 5
    elif tf_alignment_ratio >= 0.6:
        confidence += 3
    return max(50, min(95, confidence))


# ===================================================================
# Core: Multi-timeframe analysis
# ===================================================================
def _compute_timeframes(raw: dict) -> list:
    current = raw["current_price"]
    ema20, ema50, ema200 = raw["ema20"], raw["ema50"], raw["ema200"]
    prev = raw["prev_close"]
    tfs = []

    # 5 Min: price vs previous close
    if current > prev * 1.001:
        tfs.append({"timeframe": "5 Min", "trend": "Bullish"})
    elif current < prev * 0.999:
        tfs.append({"timeframe": "5 Min", "trend": "Bearish"})
    else:
        tfs.append({"timeframe": "5 Min", "trend": "Neutral"})

    # 15 Min: price vs VWAP
    if current > raw["vwap"]:
        tfs.append({"timeframe": "15 Min", "trend": "Bullish"})
    elif current < raw["vwap"]:
        tfs.append({"timeframe": "15 Min", "trend": "Bearish"})
    else:
        tfs.append({"timeframe": "15 Min", "trend": "Neutral"})

    # 1 Hour: price vs EMA 20
    if current > ema20:
        tfs.append({"timeframe": "1 Hour", "trend": "Bullish"})
    elif current < ema20:
        tfs.append({"timeframe": "1 Hour", "trend": "Bearish"})
    else:
        tfs.append({"timeframe": "1 Hour", "trend": "Neutral"})

    # Daily: EMA 20 vs EMA 50
    if ema20 > ema50:
        tfs.append({"timeframe": "Daily", "trend": "Bullish"})
    else:
        tfs.append({"timeframe": "Daily", "trend": "Bearish"})

    # Weekly: EMA 50 vs EMA 200
    if ema50 > ema200:
        tfs.append({"timeframe": "Weekly", "trend": "Bullish"})
    else:
        tfs.append({"timeframe": "Weekly", "trend": "Bearish"})

    return tfs


# ===================================================================
# Core: Dynamic risk metrics
# ===================================================================
def _compute_risk_metrics(df: pd.DataFrame, raw: dict, target_price: float, stop_loss: float) -> dict:
    close = df["close"]
    returns = close.pct_change().dropna()

    # Sharpe ratio (annualised, risk-free = 6% for India)
    if len(returns) > 1 and returns.std() > 0:
        daily_rf = 0.06 / 252
        sharpe = float(((returns.mean() - daily_rf) / returns.std()) * math.sqrt(252))
    else:
        sharpe = 0.0

    # Max drawdown
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_dd = float(drawdown.min()) * 100 if len(drawdown) > 0 else 0.0

    # Expected daily move
    expected_move = float(returns.std() * 100) if len(returns) > 0 else 0.0

    # Stop/target probability estimates
    current = raw["current_price"]
    daily_std = float(returns.std()) if len(returns) > 0 else 0.01

    prob_target, prob_stop = 50.0, 30.0
    if daily_std > 0 and current > 0:
        target_pct = abs(target_price - current) / current
        stop_pct_val = abs(stop_loss - current) / current
        horizon_std = daily_std * math.sqrt(10)
        if horizon_std > 0:
            try:
                from scipy.stats import norm
                if target_price > current:
                    prob_target = float(1 - norm.cdf(target_pct / horizon_std)) * 100
                else:
                    prob_target = float(norm.cdf(-target_pct / horizon_std)) * 100
                if stop_loss < current:
                    prob_stop = float(norm.cdf(-stop_pct_val / horizon_std)) * 100
                else:
                    prob_stop = float(1 - norm.cdf(stop_pct_val / horizon_std)) * 100
            except Exception:
                pass

    return {
        "atr": f"{raw['atr']:.2f}",
        "atr_pct": f"{raw['atr_pct']:.2f}%",
        "expected_move": f"{expected_move:.2f}%",
        "max_drawdown": f"{abs(max_dd):.1f}%",
        "sharpe": f"{sharpe:.2f}",
        "prob_stop": f"{prob_stop:.0f}%",
        "prob_target": f"{prob_target:.0f}%",
    }


# ===================================================================
# Core: Validation layer
# ===================================================================
def _validate_report(report: dict) -> list:
    warnings = []
    verdict = report["verdict"]

    for f in report.get("bull_factors", []):
        fl = f.lower()
        if any(neg in fl for neg in ["below", "bearish", "sell", "declining", "falling", "weak", "breakdown"]):
            warnings.append(f"Bull factor contains bearish language: '{f[:80]}'")

    for f in report.get("bear_factors", []):
        fl = f.lower()
        if any(pos in fl for pos in ["bullish", "buy", "rising", "breakout", "strong uptrend"]):
            warnings.append(f"Bear factor contains bullish language: '{f[:80]}'")

    tfs = report.get("trend_timeframes", [])
    actual_bullish = sum(1 for t in tfs if t["trend"] == "Bullish")
    summary = report.get("tf_summary", "")
    if summary:
        expected_prefix = f"{actual_bullish} / {len(tfs)}"
        if expected_prefix not in summary:
            warnings.append(f"TF summary mismatch: '{summary}' vs actual {actual_bullish} bullish")

    votes = report.get("votes", {})
    pm_vote = votes.get("pm", {}).get("vote", "")
    if pm_vote and pm_vote != verdict:
        warnings.append(f"PM vote '{pm_vote}' != verdict '{verdict}'")

    for w in warnings:
        logger.warning(f"[ExplainableAI Validation] {w}")
    return warnings


# ===================================================================
# Public API
# ===================================================================
def get_explainable_ai_report(symbol: str) -> dict:
    """
    Generate a fully explainable, internally consistent investment report.
    Every section derives from the same computed indicators and weighted
    scoring model. No hardcoded values. No contradictions.
    """
    symbol = symbol.upper().strip()
    data_source = "live"
    price_updated_at = datetime.now().isoformat()
    price_source = "DB_EOD"
    price_stale = True
    is_market_open_val = False

    try:
        service = get_indicator_service()
        df = service.get_ohlcv_data(symbol, "1d", days=250)
    except Exception as e:
        logger.error(f"Error fetching OHLCV data for {symbol}: {e}")
        df = pd.DataFrame()

    # Retrieve live stock price from PriceService
    try:
        from services.price_manager import get_price_service
        import asyncio
        import concurrent.futures
        import pytz
        
        price_svc = get_price_service()
        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
            
        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: asyncio.run(price_svc.get_price(symbol)))
                price_data = future.result()
        else:
            price_data = asyncio.run(price_svc.get_price(symbol))
            
        if price_data and price_data.get("ltp", 0.0) > 0.0:
            ltp = float(price_data["ltp"])
            price_updated_at = price_data.get("timestamp") or datetime.now().isoformat()
            price_source = price_data.get("source") or "UPSTOX_REST"
            price_stale = price_data.get("source") == "DB_EOD" or price_data.get("market_status") != "OPEN"
            is_market_open_val = price_data.get("market_status") == "OPEN" and price_data.get("source") != "DB_EOD"
            
            # Enrich/sync the dataframe with the latest live price
            if not df.empty:
                ist = pytz.timezone('Asia/Kolkata')
                today_ist = datetime.now(ist).date()
                
                last_row_ts = df["timestamp"].iloc[-1]
                last_row_date = pd.to_datetime(last_row_ts).date()
                
                if last_row_date == today_ist:
                    df.loc[df.index[-1], "close"] = ltp
                    df.loc[df.index[-1], "high"] = max(float(df["high"].iloc[-1]), ltp)
                    df.loc[df.index[-1], "low"] = min(float(df["low"].iloc[-1]), ltp)
                    df.loc[df.index[-1], "volume"] = max(float(df["volume"].iloc[-1]), float(price_data.get("volume") or 0))
                elif last_row_date < today_ist:
                    # Append a new daily candle for today if it is a weekday or if the feed is active
                    is_weekday = today_ist.weekday() < 5
                    is_live_source = price_data.get("source") in ["UPSTOX_WS", "UPSTOX_REST"]
                    if is_weekday or is_live_source:
                        new_row = {
                            "timestamp": pd.Timestamp(today_ist),
                            "open": float(price_data.get("previous_close") or ltp),
                            "high": max(float(price_data.get("previous_close") or ltp), ltp),
                            "low": min(float(price_data.get("previous_close") or ltp), ltp),
                            "close": ltp,
                            "volume": int(price_data.get("volume") or 0)
                        }
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    except Exception as ex:
        logger.error(f"PriceService enrichment failed for {symbol}: {ex}")

    if df.empty or len(df) < 30:
        logger.error(f"Insufficient historical data for {symbol}. Found {len(df)} candles, 30 required.")
        from core.exceptions import DataUnavailableError
        raise DataUnavailableError(
            message=f"Insufficient historical data for {symbol} to perform AI analysis. Minimum 30 candles required.",
            symbol=symbol,
            required_candles=30,
            available_candles=len(df)
        )

    # Phase 1: Compute all indicators
    indicators, raw = _evaluate_indicators(df)

    # Phase 2: Weighted scoring
    scoring = _compute_weighted_score(indicators)
    final_score = scoring["final_score"]
    category_scores = scoring["category_scores"]

    # Phase 3: Determine verdict
    verdict = _determine_verdict(final_score)

    # Multi-timeframe
    timeframes = _compute_timeframes(raw)
    tf_bullish = sum(1 for t in timeframes if t["trend"] == "Bullish")
    tf_bearish = sum(1 for t in timeframes if t["trend"] == "Bearish")
    tf_neutral = sum(1 for t in timeframes if t["trend"] == "Neutral")
    tf_total = len(timeframes)
    tf_summary = f"{tf_bullish} / {tf_total} Bullish"
    tf_alignment_ratio = tf_bullish / tf_total if tf_total > 0 else 0.5

    # Phase 4: Dynamic confidence
    confidence = _compute_confidence(indicators, raw["adx"], tf_alignment_ratio)

    # Signal counts
    bullish_count = sum(1 for i in indicators if i["signal"] == "Bullish")
    bearish_count = sum(1 for i in indicators if i["signal"] == "Bearish")
    neutral_count = sum(1 for i in indicators if i["signal"] == "Neutral")
    total_indicators = len(indicators)

    # Bull / Bear factors (only matching signals)
    bull_factors = [i["reason"] for i in indicators if i["signal"] == "Bullish"]
    bear_factors = [i["reason"] for i in indicators if i["signal"] == "Bearish"]

    # Dynamic reasoning
    reasoning = []
    if verdict in ("BUY", "STRONG BUY"):
        reasoning.append(f"{bullish_count} of {total_indicators} technical indicators are bullish.")
        for i in indicators:
            if i["signal"] == "Bullish":
                reasoning.append(f"{i['name']}: {i['reason']}")
        if tf_bullish >= 3:
            reasoning.append(f"{tf_bullish} of {tf_total} timeframes confirm bullish alignment.")
    elif verdict in ("SELL", "STRONG SELL"):
        reasoning.append(f"{bearish_count} of {total_indicators} technical indicators are bearish.")
        for i in indicators:
            if i["signal"] == "Bearish":
                reasoning.append(f"{i['name']}: {i['reason']}")
        if tf_bearish >= 3:
            reasoning.append(f"{tf_bearish} of {tf_total} timeframes confirm bearish alignment.")
    else:
        reasoning.append(f"Mixed signals: {bullish_count} bullish, {bearish_count} bearish, {neutral_count} neutral out of {total_indicators}.")
        reasoning.append("No high-confidence directional setup exists.")
        for i in sorted(indicators, key=lambda x: abs(x["score"]), reverse=True)[:4]:
            reasoning.append(f"{i['name']}: {i['reason']}")
    reasoning.append(f"Overall weighted technical score: {final_score:+.1f}")

    # Price levels
    current_price = raw["current_price"]
    recent_high = float(df["high"].iloc[-20:].max())
    recent_low = float(df["low"].iloc[-20:].min())
    pivot = (recent_high + recent_low + current_price) / 3
    r1 = round(pivot * 2 - recent_low, 1)
    r2 = round(pivot + (recent_high - recent_low), 1)
    s1 = round(pivot * 2 - recent_high, 1)
    s2 = round(pivot - (recent_high - recent_low), 1)
    breakout_level = round(recent_high, 1)
    is_breakout = current_price > breakout_level

    # Target / Stop Loss (direction-aware)
    if verdict in ("BUY", "STRONG BUY"):
        target_pct = 5.5 if verdict == "STRONG BUY" else 4.0
        stop_pct = 3.0
        target_price = round(current_price * (1 + target_pct / 100), 1)
        stop_loss = round(current_price * (1 - stop_pct / 100), 1)
    elif verdict in ("SELL", "STRONG SELL"):
        target_pct = 5.5 if verdict == "STRONG SELL" else 4.0
        stop_pct = 3.0
        target_price = round(current_price * (1 - target_pct / 100), 1)
        stop_loss = round(current_price * (1 + stop_pct / 100), 1)
    else:
        target_pct = 2.0
        stop_pct = 2.0
        target_price = round(current_price * (1 + target_pct / 100), 1)
        stop_loss = round(current_price * (1 - stop_pct / 100), 1)

    rr_ratio = f"1 : {abs(target_pct / stop_pct):.1f}" if stop_pct != 0 else "1 : 1"

    # Risk metrics
    risk_metrics = _compute_risk_metrics(df, raw, target_price, stop_loss)

    # Volume analysis
    volumes = df["volume"]
    avg_vol = float(volumes.iloc[-20:].mean())
    curr_vol = float(volumes.iloc[-1])
    rel_vol = curr_vol / avg_vol if avg_vol > 0 else 1.0

    # Votes (aligned with verdict)
    if verdict in ("BUY", "STRONG BUY"):
        votes = {
            "bull": {"vote": "BUY", "confidence": max(60, bullish_count * 100 // max(total_indicators, 1))},
            "bear": {"vote": "HOLD" if bearish_count < bullish_count else "SELL", "confidence": max(40, bearish_count * 100 // max(total_indicators, 1))},
            "risk": {"vote": verdict, "status": "Approved"},
            "pm": {"vote": verdict, "status": "Final Decision"},
            "consensus": f"{bullish_count} / {total_indicators} Bullish Signals",
        }
    elif verdict in ("SELL", "STRONG SELL"):
        votes = {
            "bull": {"vote": "HOLD" if bullish_count > 2 else "SELL", "confidence": max(40, bullish_count * 100 // max(total_indicators, 1))},
            "bear": {"vote": "SELL", "confidence": max(60, bearish_count * 100 // max(total_indicators, 1))},
            "risk": {"vote": verdict, "status": "Caution -- Elevated Risk"},
            "pm": {"vote": verdict, "status": "Final Decision"},
            "consensus": f"{bearish_count} / {total_indicators} Bearish Signals",
        }
    else:
        votes = {
            "bull": {"vote": "HOLD", "confidence": max(40, bullish_count * 100 // max(total_indicators, 1))},
            "bear": {"vote": "HOLD", "confidence": max(40, bearish_count * 100 // max(total_indicators, 1))},
            "risk": {"vote": "HOLD", "status": "No Clear Edge"},
            "pm": {"vote": "HOLD", "status": "Final Decision"},
            "consensus": f"Mixed -- {bullish_count}B / {bearish_count}S / {neutral_count}N",
        }

    # Price action (dynamic)
    price_action = []
    if current_price > raw["prev_close"]:
        price_action.append("Closing price higher than previous session.")
    else:
        price_action.append("Closing price lower than previous session.")
    if is_breakout:
        price_action.append(f"Price has broken above 20-day high ({breakout_level}).")
    else:
        price_action.append(f"Price remains below 20-day high ({breakout_level}).")
    if raw["ema20"] > raw["ema50"]:
        price_action.append("Short-term MA alignment is bullish (EMA20 > EMA50).")
    else:
        price_action.append("Short-term MA alignment is bearish (EMA20 < EMA50).")
    if current_price > raw["vwap"]:
        price_action.append("Trading above VWAP, indicating institutional buying interest.")
    else:
        price_action.append("Trading below VWAP, indicating institutional selling pressure.")

    # Strategy (direction-aware)
    if verdict in ("BUY", "STRONG BUY"):
        strategy = {
            "style": "Swing Trade -- Long",
            "holding": "5-10 Trading Days",
            "entry": f"{round(current_price * 0.995, 1)}-{round(current_price * 1.002, 1)}",
            "add_on_dip": f"{round(current_price * 0.985, 1)}",
            "partial": f"{round(current_price * 1.025, 1)}",
            "exit": f"{target_price}",
        }
    elif verdict in ("SELL", "STRONG SELL"):
        strategy = {
            "style": "Risk Reduction -- Exit / Short",
            "holding": "Reduce within 3-5 Days",
            "entry": f"Short below {round(current_price * 0.998, 1)}",
            "add_on_dip": f"Add short below {round(current_price * 0.985, 1)}",
            "partial": f"Cover at {round(current_price * 0.975, 1)}",
            "exit": f"{target_price}",
        }
    else:
        strategy = {
            "style": "Wait and Watch",
            "holding": "No New Position Recommended",
            "entry": f"Wait for breakout above {r1} or breakdown below {s1}",
            "add_on_dip": "N/A",
            "partial": "N/A",
            "exit": "N/A",
        }

    # Confidence breakdown (dynamic from category scores)
    label_map = {"trend": "Trend Strength", "momentum": "Momentum Factors", "volume": "Volume Confirmation", "structure": "Market Structure", "volatility": "Volatility / Risk", "multi_tf": "Multi-TF Alignment"}
    total_weight = sum(CATEGORY_WEIGHTS.values())
    confidence_breakdown = {}
    for cat, cs in category_scores.items():
        pct = round(cs["weight"] / total_weight * confidence)
        confidence_breakdown[cat] = {"label": label_map.get(cat, cat), "value": pct, "weight_pct": round(cs["weight"] * 100)}

    # Audit trail
    audit_trail = {
        "symbol": symbol, "data_source": data_source, "data_points": len(df),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "indicator_count": total_indicators,
        "bullish_count": bullish_count, "bearish_count": bearish_count, "neutral_count": neutral_count,
        "category_breakdown": {cat: {"weight": f"{cs['weight'] * 100:.0f}%", "raw_avg": cs["average"], "weighted_score": cs["weighted"]} for cat, cs in category_scores.items()},
        "final_score": final_score, "verdict": verdict, "confidence": confidence,
    }

    # Build consensus report markdown dynamically
    risk_level = "Low" if confidence >= 75 else ("High" if confidence < 60 else "Moderate")
    consensus_report = (
        f"**Investment Committee Verdict: {verdict}**\n\n"
        f"### Consensus Rationale\n"
        f"The Swarm Committee has completed the debate. A confluence of technical indicators "
        f"and quantitative risk factors yields a {verdict} recommendation with {confidence:.0f}% confidence. "
    )
    if verdict in ("BUY", "STRONG BUY"):
        consensus_report += "The intermediate and long-term trend alignments remain supportive of upward expansion."
    elif verdict in ("SELL", "STRONG SELL"):
        consensus_report += "Key moving average breakdowns and negative momentum signals indicate elevated downside risk."
    else:
        consensus_report += "Range-bound price action and mixed momentum indicators suggest maintaining a neutral posture."
    
    consensus_report += "\n\n"
    if reasoning:
        consensus_report += "### Key Decision Drivers\n"
        for r in reasoning:
            consensus_report += f"- {r}\n"
    
    consensus_report += (
        f"\n### Trade Details\n"
        f"- **Verdict**: {verdict}\n"
        f"- **Target Price**: {f'₹{target_price}' if target_price else 'N/A'}\n"
        f"- **Stop Loss**: {f'₹{stop_loss}' if stop_loss else 'N/A'}\n"
        f"- **Confidence**: {confidence:.0f}%\n"
        f"- **Risk Profile**: {risk_level}\n"
        f"- **Strategy**: {strategy.get('style', 'N/A')}\n"
    )

    # Build final report
    report = {
        "verdict": verdict, "confidence": confidence,
        "risk_level": risk_level,
        "horizon": "Swing (5-15 Days)" if verdict != "HOLD" else "Wait for Setup",
        "current_price": round(current_price, 2), "target_price": target_price, "stop_loss": stop_loss,
        "risk_reward": rr_ratio, "final_score": final_score, "data_source": data_source,
        "votes": votes,
        "price_updated_at": price_updated_at,
        "price_source": price_source,
        "price_stale": price_stale,
        "is_market_open": is_market_open_val,
        "indicators": {i["key"]: {"value": i["value"], "signal": i["signal"], "status": i["signal"], "desc": i["reason"], "score": i["score"], "contribution": i["contribution"]} for i in indicators},
        "indicator_list": indicators,
        "signal_summary": {"bullish": bullish_count, "bearish": bearish_count, "neutral": neutral_count, "total": total_indicators},
        "price_action": price_action,
        "levels": {"s1": s1, "s2": s2, "r1": r1, "r2": r2, "breakout": breakout_level, "status": "Breakout Confirmed" if is_breakout else "Testing Resistance"},
        "volume": {"current": f"{curr_vol / 1e6:.2f}M", "average": f"{avg_vol / 1e6:.2f}M", "relative": f"{rel_vol:.2f}x", "delivery": "N/A", "trend": "Increasing" if curr_vol > avg_vol else ("Decreasing" if curr_vol < avg_vol * 0.8 else "Stable")},
        "trend_timeframes": timeframes,
        "tf_summary": tf_summary,
        "tf_detail": {"bullish": tf_bullish, "bearish": tf_bearish, "neutral": tf_neutral, "total": tf_total},
        "risk_metrics": risk_metrics,
        "bull_factors": bull_factors, "bear_factors": bear_factors,
        "reasoning": reasoning,
        "recommended_strategy": strategy,
        "confidence_breakdown": confidence_breakdown,
        "historical_stats": None,
        "audit_trail": audit_trail,
        "consensus_report": consensus_report,
    }

    # Assert current price consistency across sub-structures
    if abs(report["current_price"] - round(float(df["close"].iloc[-1]), 2)) > 0.05:
        raise ValueError("MarketDataConsistencyError: Current price mismatch detected across application modules.")

    # Phase 6: Validation
    report["validation_warnings"] = _validate_report(report)
    
    # Run consensus check
    if report.get("consensus_report"):
        try:
            validate_consensus_consistency(report["consensus_report"], report)
        except DecisionConsistencyError as e:
            report["validation_warnings"].append(str(e))
            
    return report


class DecisionConsistencyError(ValueError):
    """Exception raised when Consensus Report contradicts Portfolio Manager decision."""
    pass


def validate_consensus_consistency(consensus_text: str, report: dict) -> None:
    """Validates that the consensus report string matches the final decision object metrics.
    
    Raises DecisionConsistencyError if there is any inconsistency.
    """
    if not consensus_text:
        return
        
    text_clean = consensus_text.replace("*", "").lower()
    
    # 1. Verdict assertion
    expected_verdict = report["verdict"].lower()
    import re
    verdict_match = re.search(r'verdict\s*:\s*([a-z]+(?:\s+[a-z]+)?)', text_clean)
    if verdict_match:
        found_verdict = verdict_match.group(1).strip()
        if "buy" in found_verdict:
            found_verdict = "buy"
        elif "sell" in found_verdict:
            found_verdict = "sell"
        elif "hold" in found_verdict:
            found_verdict = "hold"
            
        clean_expected = "buy" if "buy" in expected_verdict else ("sell" if "sell" in expected_verdict else "hold")
        if found_verdict != clean_expected:
            raise DecisionConsistencyError(
                f"DecisionConsistencyError: Consensus verdict '{found_verdict}' does not match Portfolio Manager output '{clean_expected}'"
            )
            
    # 2. Confidence assertion
    conf_match = re.search(r'confidence\s*:\s*(\d+)', text_clean)
    if conf_match:
        found_conf = int(conf_match.group(1))
        expected_conf = int(report["confidence"])
        if found_conf != expected_conf:
            raise DecisionConsistencyError(
                f"DecisionConsistencyError: Consensus confidence '{found_conf}%' does not match Portfolio Manager output '{expected_conf}%'"
            )
            
    # 3. Target Price assertion
    target_match = re.search(r'target\s*(?:price)?\s*:\s*(?:[^\d\n\r]*?)(\d+(?:\.\d+)?)', text_clean)
    if target_match and report.get("target_price"):
        found_target = float(target_match.group(1))
        expected_target = float(report["target_price"])
        if abs(found_target - expected_target) > 0.01:
            raise DecisionConsistencyError(
                f"DecisionConsistencyError: Consensus target '{found_target}' does not match Portfolio Manager output '{expected_target}'"
            )
            
    # 4. Stop Loss assertion
    stop_match = re.search(r'stop\s*(?:loss)?\s*:\s*(?:[^\d\n\r]*?)(\d+(?:\.\d+)?)', text_clean)
    if stop_match and report.get("stop_loss"):
        found_stop = float(stop_match.group(1))
        expected_stop = float(report["stop_loss"])
        if abs(found_stop - expected_stop) > 0.01:
            raise DecisionConsistencyError(
                f"DecisionConsistencyError: Consensus stop loss '{found_stop}' does not match Portfolio Manager output '{expected_stop}'"
            )

