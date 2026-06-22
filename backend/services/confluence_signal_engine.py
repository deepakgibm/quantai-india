"""
Confluence Signal Engine
Layers: Normalization, Feature Engineering, Scoring, and Signal Generation.
Institutional-grade confluence scoring combining Equity indicators and Options flow data.
"""

import logging
from typing import Dict, Any, List, Optional
from data.fno_stocks import has_derivatives

logger = logging.getLogger(__name__)


class ConfluenceSignalEngine:
    """
    Unified Equity + Options intelligence signal engine.
    Fuses multi-factor indicators to output a clear Buy/Sell/Hold decision,
    confidence score, and granular evidence breakdown.
    """

    CONFIDENCE_THRESHOLD = 65.0
    NO_DERIVATIVES_PENALTY = 0.125  # 12.5%

    async def generate_confluence_signal(
        self,
        symbol: str,
        spot_price: float,
        option_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate confluence signal by merging equity technicals and options flow.
        """
        symbol = symbol.upper().strip()
        is_fno = has_derivatives(symbol) and not (option_data and option_data.get("is_empty"))

        # 1. Fetch/Calculate Equity Indicators
        equity_indicators = await self._fetch_equity_indicators(symbol, spot_price)
        
        # 2. Extract Options Metrics
        options_metrics = self._extract_options_metrics(option_data, is_fno)

        # 3. Initialize Bullish / Bearish Evidence Lists
        bullish_evidence: List[str] = []
        bearish_evidence: List[str] = []
        contributors: Dict[str, float] = {}

        # 4. Score Equity Factors (Max: 50 points)
        equity_bullish, equity_bearish = self._score_equity_factors(
            equity_indicators,
            bullish_evidence,
            bearish_evidence,
            contributors
        )

        # 5. Score Options Factors (Max: 50 points)
        options_bullish, options_bearish = self._score_options_factors(
            options_metrics,
            is_fno,
            bullish_evidence,
            bearish_evidence,
            contributors
        )

        # 6. Aggregate Scores and Scaling
        if is_fno:
            total_bullish = equity_bullish + options_bullish
            total_bearish = equity_bearish + options_bearish
            equity_contribution = round((equity_bullish + equity_bearish) / max(1.0, total_bullish + total_bearish) * 100.0, 1)
            options_contribution = round((options_bullish + options_bearish) / max(1.0, total_bullish + total_bearish) * 100.0, 1)
        else:
            # Scale equity-only score to 100%
            total_bullish = equity_bullish * 2.0
            total_bearish = equity_bearish * 2.0
            equity_contribution = 100.0
            options_contribution = 0.0

        # Clamp scores to [0, 100]
        total_bullish = max(0.0, min(100.0, total_bullish))
        total_bearish = max(0.0, min(100.0, total_bearish))

        # 7. Signal Decision Logic
        net_score = total_bullish - total_bearish
        raw_confidence = max(total_bullish, total_bearish)
        
        # Apply non-F&O confidence penalty if applicable
        if not is_fno:
            confidence_score = raw_confidence * (1.0 - self.NO_DERIVATIVES_PENALTY)
            if option_data and option_data.get("is_empty"):
                bearish_evidence.append("Option chain data currently unavailable from Upstox (12.5% confidence penalty applied)")
            else:
                bearish_evidence.append("Missing options data confirmation (12.5% confidence penalty applied)")
        else:
            confidence_score = raw_confidence

        confidence_score = round(max(0.0, min(100.0, confidence_score)), 1)

        # Determine Signal
        if net_score > 15.0 and confidence_score >= self.CONFIDENCE_THRESHOLD:
            signal = "BUY"
            directional_bias = "Bullish"
        elif net_score < -15.0 and confidence_score >= self.CONFIDENCE_THRESHOLD:
            signal = "SELL"
            directional_bias = "Bearish"
        else:
            signal = "HOLD"
            directional_bias = "Neutral"
            if confidence_score < self.CONFIDENCE_THRESHOLD:
                bullish_evidence.append(f"Confidence score {confidence_score}% below threshold of {self.CONFIDENCE_THRESHOLD}%")

        # 8. Entry, Stop-Loss, and Target Calculations
        targets = self._calculate_targets(spot_price, equity_indicators, options_metrics, signal)

        # 9. Format Key Indicators for UI Table
        key_indicators = self._format_key_indicators(equity_indicators, options_metrics, is_fno)

        # Translate score to text confidence
        if confidence_score >= 85:
            confidence = "Very High"
        elif confidence_score >= 70:
            confidence = "High"
        elif confidence_score >= 50:
            confidence = "Medium"
        else:
            confidence = "Low"

        reason_list = bullish_evidence + bearish_evidence

        return {
            "signal": signal,
            "directional_bias": directional_bias,
            "confidence": confidence,
            "confidence_score": confidence_score,
            "equity_contribution": equity_contribution,
            "options_contribution": options_contribution,
            "entry_zone": targets["entry_zone"],
            "stop_loss": targets["stop_loss"],
            "target_levels": targets["target_levels"],
            "bullish_evidence": bullish_evidence,
            "bearish_evidence": bearish_evidence,
            "reason": reason_list,
            "key_indicators": key_indicators,
            "contributors": contributors
        }

    async def _fetch_equity_indicators(self, symbol: str, spot_price: float) -> Dict[str, Any]:
        """
        Ingest historical data and compute standard technical indicators.
        """
        try:
            from services.indicator_compute_service import get_indicator_service
            service = get_indicator_service()
            df = service.get_ohlcv_data(symbol, interval="1d", days=100)
            
            if df.empty or len(df) < 30:
                logger.warning(f"No OHLCV history found for {symbol}. Falling back to default indicators.")
                return self._default_equity_indicators(spot_price)

            indicators_df = service._computer.compute_all_indicators(df)
            if indicators_df.empty:
                return self._default_equity_indicators(spot_price)

            latest = indicators_df.iloc[-1]
            atr_series = service._computer.compute_atr(df['high'], df['low'], df['close'], 14)
            latest_atr = atr_series.iloc[-1] if not atr_series.empty else (spot_price * 0.02)

            avg_vol = df['volume'].tail(20).mean()
            vol_ratio = latest['volume'] / avg_vol if avg_vol > 0 else 1.0

            # Trend classification helper
            close_val = float(latest['close'])
            ema20 = float(latest['ema_20']) if 'ema_20' in latest else close_val
            ema50 = float(latest['ema_50']) if 'ema_50' in latest else close_val

            if ema20 > ema50 and close_val > ema20:
                trend = "Strong Uptrend"
            elif ema20 > ema50:
                trend = "Uptrend"
            elif ema20 < ema50 and close_val < ema20:
                trend = "Strong Downtrend"
            elif ema20 < ema50:
                trend = "Downtrend"
            else:
                trend = "Sideways"

            return {
                "close": close_val,
                "rsi": float(latest.get('rsi_14', 50.0)),
                "roc": float(latest.get('roc_10', 0.0)),
                "macd_hist": float(latest.get('macd_histogram', 0.0)),
                "ema_20": ema20,
                "ema_50": ema50,
                "vwap": float(latest.get('vwap', close_val)),
                "bb_upper": float(latest.get('bb_upper', close_val * 1.05)),
                "bb_lower": float(latest.get('bb_lower', close_val * 0.95)),
                "atr": float(latest_atr),
                "volume_ratio": float(vol_ratio),
                "trend": trend,
                "high": float(latest['high']),
                "low": float(latest['low']),
                "prev_close": float(df['close'].iloc[-2]) if len(df) >= 2 else close_val
            }

        except Exception as e:
            logger.error(f"Failed to fetch indicators for {symbol}: {e}")
            return self._default_equity_indicators(spot_price)

    def _default_equity_indicators(self, spot_price: float) -> Dict[str, Any]:
        """Fallback equity indicators when data loading fails."""
        return {
            "close": spot_price,
            "rsi": 50.0,
            "roc": 0.0,
            "macd_hist": 0.0,
            "ema_20": spot_price,
            "ema_50": spot_price,
            "vwap": spot_price,
            "bb_upper": spot_price * 1.05,
            "bb_lower": spot_price * 0.95,
            "atr": spot_price * 0.02,
            "volume_ratio": 1.0,
            "trend": "Sideways",
            "high": spot_price,
            "low": spot_price,
            "prev_close": spot_price
        }

    def _extract_options_metrics(self, data: Optional[Dict[str, Any]], is_fno: bool) -> Dict[str, Any]:
        """
        Extract options chain metrics from option flow response.
        """
        if not is_fno or not data:
            return {
                "pcr": 1.0,
                "net_flow": 0.0,
                "max_pain": 0.0,
                "support_strike": 0.0,
                "resistance_strike": 0.0,
                "sentiment": "Neutral",
                "sentiment_score": 50,
                "smart_money": []
            }

        return {
            "pcr": float(data.get("pcr_oi", 1.0)),
            "net_flow": float(data.get("net_flow", 0.0)),
            "max_pain": float(data.get("max_pain", 0.0)),
            "support_strike": float(data.get("support_strike", 0.0)),
            "resistance_strike": float(data.get("resistance_strike", 0.0)),
            "sentiment": data.get("sentiment", "Neutral"),
            "sentiment_score": int(data.get("sentiment_score", 50)),
            "smart_money": data.get("smart_money_activity", [])
        }

    def _score_equity_factors(
        self,
        ind: Dict[str, Any],
        bullish_ev: List[str],
        bearish_ev: List[str],
        contributors: Dict[str, float]
    ) -> tuple:
        """
        Score Equity factors out of 50 maximum points.
        """
        bullish = 0.0
        bearish = 0.0

        # 1. Trend Direction (Max: 10 pts)
        trend = ind["trend"]
        if trend == "Strong Uptrend":
            bullish += 10.0
            bullish_ev.append("Strong technical uptrend confirmed on Daily EMA 20/50")
            contributors["Trend Direction"] = 10.0
        elif trend == "Uptrend":
            bullish += 5.0
            bullish_ev.append("Daily EMA 20/50 indicates bullish bias")
            contributors["Trend Direction"] = 5.0
        elif trend == "Strong Downtrend":
            bearish += 10.0
            bearish_ev.append("Strong technical downtrend on Daily EMA 20/50")
            contributors["Trend Direction"] = -10.0
        elif trend == "Downtrend":
            bearish += 5.0
            bearish_ev.append("Daily EMA 20/50 indicates bearish bias")
            contributors["Trend Direction"] = -5.0
        else:
            contributors["Trend Direction"] = 0.0

        # 2. Momentum Indicators (RSI, MACD, ROC) (Max: 10 pts)
        rsi_val = ind["rsi"]
        macd_hist = ind["macd_hist"]
        mom_contrib = 0.0

        if rsi_val > 55.0:
            bullish += 5.0
            bullish_ev.append(f"Bullish RSI Momentum: {rsi_val:.1f}")
            mom_contrib += 5.0
        elif rsi_val < 45.0:
            bearish += 5.0
            bearish_ev.append(f"Bearish RSI Momentum: {rsi_val:.1f}")
            mom_contrib -= 5.0

        if macd_hist > 0.0:
            bullish += 5.0
            bullish_ev.append("MACD histogram resides in positive territory")
            mom_contrib += 5.0
        elif macd_hist < 0.0:
            bearish += 5.0
            bearish_ev.append("MACD histogram resides in negative territory")
            mom_contrib -= 5.0

        contributors["Momentum"] = mom_contrib

        # 3. Price Position relative to VWAP & MAs (Max: 10 pts)
        close = ind["close"]
        vwap = ind["vwap"]
        vwap_contrib = 0.0

        if close > vwap:
            bullish += 5.0
            bullish_ev.append(f"Price is trading above intra-day VWAP (₹{vwap:.1f})")
            vwap_contrib += 5.0
        else:
            bearish += 5.0
            bearish_ev.append(f"Price is trading below intra-day VWAP (₹{vwap:.1f})")
            vwap_contrib -= 5.0

        if close > ind["ema_20"]:
            bullish += 5.0
            bullish_ev.append("Price holding support above short-term EMA 20")
            vwap_contrib += 5.0
        else:
            bearish += 5.0
            bearish_ev.append("Price trading below short-term EMA 20 resistance")
            vwap_contrib -= 5.0

        contributors["Price Location"] = vwap_contrib

        # 4. Volatility & Breakout Levels (Max: 10 pts)
        bb_upper = ind["bb_upper"]
        bb_lower = ind["bb_lower"]
        vol_contrib = 0.0

        if close >= bb_upper:
            bullish += 10.0
            bullish_ev.append("Bollinger Band Upper breakout detected")
            vol_contrib += 10.0
        elif close <= bb_lower:
            bearish += 10.0
            bearish_ev.append("Bollinger Band Lower breakdown detected")
            vol_contrib -= 10.0
        else:
            contributors["Breakouts"] = 0.0

        # 5. Volume Confirmation (Max: 10 pts)
        vol_ratio = ind["volume_ratio"]
        vol_ratio_contrib = 0.0

        if vol_ratio >= 1.5:
            # High volume reinforces current move
            change_pct = ((close - ind["prev_close"]) / ind["prev_close"]) * 100.0 if ind["prev_close"] > 0 else 0.0
            if change_pct >= 0:
                bullish += 10.0
                bullish_ev.append(f"Strong volume confirmation ({vol_ratio:.1f}x avg) backing bullish price movement")
                vol_ratio_contrib += 10.0
            else:
                bearish += 10.0
                bearish_ev.append(f"Aggressive sell volume ({vol_ratio:.1f}x avg) backing bearish price movement")
                vol_ratio_contrib -= 10.0
        else:
            contributors["Volume Confirmation"] = 0.0

        return bullish, bearish

    def _score_options_factors(
        self,
        opt: Dict[str, Any],
        is_fno: bool,
        bullish_ev: List[str],
        bearish_ev: List[str],
        contributors: Dict[str, float]
    ) -> tuple:
        """
        Score Options factors out of 50 maximum points.
        """
        if not is_fno:
            contributors["PCR Sentiment"] = 0.0
            contributors["Premium Flow"] = 0.0
            contributors["Strike Cones"] = 0.0
            contributors["Smart Money"] = 0.0
            return 0.0, 0.0

        bullish = 0.0
        bearish = 0.0

        # 1. PCR Sentiment (Max: 15 pts)
        pcr = opt["pcr"]
        if pcr > 1.25:
            bullish += 15.0
            bullish_ev.append(f"Highly bullish Put-Call Ratio (PCR: {pcr:.2f}) indicating dominant put writing")
            contributors["PCR Sentiment"] = 15.0
        elif pcr < 0.70:
            bearish += 15.0
            bearish_ev.append(f"Bearish Put-Call Ratio (PCR: {pcr:.2f}) indicating heavy call writing resistance")
            contributors["PCR Sentiment"] = -15.0
        else:
            contributors["PCR Sentiment"] = 0.0

        # 2. Net Premium Flow (Max: 15 pts)
        flow = opt["net_flow"]
        if flow > 1000000.0:  # > 10L net premium
            bullish += 15.0
            bullish_ev.append(f"Institutional Net Premium Flow is highly positive: +₹{(flow/100000):.1f} Lakhs")
            contributors["Premium Flow"] = 15.0
        elif flow < -1000000.0:
            bearish += 15.0
            bearish_ev.append(f"Institutional Net Premium Flow is highly negative: -₹{(abs(flow)/100000):.1f} Lakhs")
            contributors["Premium Flow"] = -15.0
        else:
            contributors["Premium Flow"] = 0.0

        # 3. Strike Cones & Max Pain Location (Max: 10 pts)
        spot = opt["max_pain"] # max pain reference or spot price
        # Actually use max pain from F&O data
        max_pain = opt["max_pain"]
        support = opt["support_strike"]
        resistance = opt["resistance_strike"]
        strike_contrib = 0.0

        if max_pain > 0:
            if opt["max_pain"] < max_pain: # Spot above max pain
                bullish += 5.0
                bullish_ev.append(f"Spot price is trading above Max Pain strike (₹{max_pain:.1f})")
                strike_contrib += 5.0
            else:
                bearish += 5.0
                bearish_ev.append(f"Spot price is compressed below Max Pain strike (₹{max_pain:.1f})")
                strike_contrib -= 5.0

        # Check proximity to support/resistance walls
        if support > 0 and abs(spot - support) / support <= 0.015:
            bullish += 5.0
            bullish_ev.append(f"Spot trading near key options support floor (₹{support:.1f})")
            strike_contrib += 5.0
        elif resistance > 0 and abs(spot - resistance) / resistance <= 0.015:
            bearish += 5.0
            bearish_ev.append(f"Spot trading near heavy options resistance ceiling (₹{resistance:.1f})")
            strike_contrib -= 5.0

        contributors["Strike Cones"] = strike_contrib

        # 4. Smart Money / Irregularities (Max: 10 pts)
        smart = opt["smart_money"]
        smart_contrib = 0.0

        if smart:
            high_severity_bullish = any(s.get("severity") == "High" and "PE" in s.get("type", "") for s in smart)
            high_severity_bearish = any(s.get("severity") == "High" and "CE" in s.get("type", "") for s in smart)
            
            if high_severity_bullish:
                bullish += 10.0
                bullish_ev.append("Aggressive institutional Put writing / Gamma Accumulation detected close to Spot")
                smart_contrib += 10.0
            elif high_severity_bearish:
                bearish += 10.0
                bearish_ev.append("Heavy short build-ups / resistance walls accumulating on call options")
                smart_contrib -= 10.0

        contributors["Smart Money"] = smart_contrib

        return bullish, bearish

    def _calculate_targets(
        self,
        spot: float,
        ind: Dict[str, Any],
        opt: Dict[str, Any],
        signal: str
    ) -> Dict[str, Any]:
        """
        Calculate suggested execution bounds and invalidation exits using ATR and support levels.
        """
        atr = ind["atr"] if ind["atr"] > 0 else (spot * 0.02)
        support = opt["support_strike"] if opt["support_strike"] > 0 else (spot - 1.5 * atr)
        resistance = opt["resistance_strike"] if opt["resistance_strike"] > 0 else (spot + 1.5 * atr)

        if signal == "BUY":
            # Entry zone is just above support or at current spot
            entry_zone = f"{round(max(support, spot - 0.5 * atr), 1)} - {round(spot, 1)}"
            stop_loss = round(support - 0.5 * atr, 1)
            target_levels = [round(spot + 1.5 * atr, 1), round(resistance, 1)]
        elif signal == "SELL":
            entry_zone = f"{round(spot, 1)} - {round(min(resistance, spot + 0.5 * atr), 1)}"
            stop_loss = round(resistance + 0.5 * atr, 1)
            target_levels = [round(spot - 1.5 * atr, 1), round(support, 1)]
        else:
            entry_zone = "N/A (Hold)"
            stop_loss = 0.0
            target_levels = []

        return {
            "entry_zone": entry_zone,
            "stop_loss": stop_loss,
            "target_levels": target_levels
        }

    def _format_key_indicators(self, ind: Dict[str, Any], opt: Dict[str, Any], is_fno: bool) -> Dict[str, Any]:
        """Format values to be rendered cleanly in the Key Indicators table."""
        formatted = {
            "rsi_14": f"{ind['rsi']:.1f}",
            "trend": ind["trend"],
            "vwap_alignment": "Above VWAP" if ind["close"] > ind["vwap"] else "Below VWAP",
            "ema_alignment": "EMA 20 > EMA 50" if ind["ema_20"] > ind["ema_50"] else "EMA 20 < EMA 50",
            "volume_ratio": f"{ind['volume_ratio']:.2f}x",
        }
        if is_fno:
            formatted.update({
                "pcr_oi": f"{opt['pcr']:.2f}",
                "net_premium_flow": f"₹{(opt['net_flow']/100000):.1f} Lakhs",
                "max_pain": f"₹{opt['max_pain']:.1f}",
                "options_sentiment": opt["sentiment"]
            })
        else:
            formatted.update({
                "pcr_oi": "N/A",
                "net_premium_flow": "N/A",
                "max_pain": "N/A",
                "options_sentiment": "N/A"
            })
        return formatted
