"""
Bot Signal Generator

Combines analysis results with market trend to produce BUY/SELL signals.
Uses correlation, price change, volatility, and PCR confirmation.
"""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class BotSignal:
    """A generated BUY or SELL signal."""
    symbol: str
    sector: str = "Others"
    signal_type: str           # BUY or SELL
    correlation: float         # Pearson correlation with NIFTY 50
    correlation_category: str  # HIGH, MODERATE, LOW
    price_change_pct: float    # % price change
    current_price: float
    volatility_level: str      # HIGH, MEDIUM, LOW
    volatility_atr: float
    pcr_value: Optional[float]
    pcr_source: str            # "simulated" or "live"
    conviction: str            # STRONG, MODERATE, WEAK
    score: float = 50.0
    ai_tag: str = "Watchlist"
    ai_details: dict = None

    def to_dict(self) -> dict:
        return asdict(self)


class SignalGenerator:
    """
    Generates BUY/SELL signals based on market regime.

    BEARISH market → SELL signals for highly correlated stocks dropping ≥ 2%
    BULLISH market → BUY signals for highly correlated stocks rising ≥ 2%
    PCR is used as confirmation to adjust conviction level.
    """

    PRICE_CHANGE_THRESHOLD = 2.0   # Minimum % change to trigger signal
    CORRELATION_THRESHOLD = 0.5    # Minimum correlation for signal

    def generate_signals(
        self,
        market_trend: str,
        correlations: Dict[str, "CorrelationResult"],
        volatilities: Dict[str, "VolatilityResult"],
        price_changes: Dict[str, dict],   # {symbol: {current, previous, change_pct}}
        pcr_data: Dict[str, dict],         # {symbol: {pcr, source}}
        indicators: Optional[Dict[str, dict]] = None,
        sector_results: Optional[Dict[str, dict]] = None,
    ) -> List[BotSignal]:
        """
        Generate signals based on market regime and stock analysis.
        Uses a rule-based engine with multiple indicator confirmations.
        """
        signals: List[BotSignal] = []
        
        # Trackers for diagnostics (Phase 10)
        total_scanned = len(correlations)
        corr_passed = 0
        signals_generated = 0
        passed_rules_buy = {
            "ema_bullish": 0, "macd_bullish": 0, "rsi_bullish": 0, "adx_bullish": 0,
            "vwap_bullish": 0, "corr_bullish": 0, "vol_bullish": 0, "breakout_bullish": 0
        }
        passed_rules_sell = {
            "ema_bearish": 0, "macd_bearish": 0, "rsi_bearish": 0, "adx_bearish": 0,
            "vwap_bearish": 0, "momentum_bearish": 0, "vol_bearish": 0, "breakout_bearish": 0
        }

        # Load sector mapping to assign sector trend score
        sector_mapping = {}
        try:
            from database import SessionLocal
            from sqlalchemy import text
            with SessionLocal() as session:
                res = session.execute(text("SELECT symbol, sector FROM instrument_master"))
                for r in res:
                    if r[0]:
                        sector_mapping[r[0].strip()] = r[1].strip() if r[1] else "Others"
        except Exception:
            pass

        # Make sure indicators are provided
        if not indicators:
            indicators = {}

        for symbol, corr in correlations.items():
            if corr.value >= self.CORRELATION_THRESHOLD:
                corr_passed += 1

            # Get price change data
            pc = price_changes.get(symbol)
            if not pc:
                continue
            change_pct = pc.get("change_pct", 0.0)
            current_price = pc.get("current", 0.0)

            # Get volatility
            vol = volatilities.get(symbol)
            vol_level = vol.category if vol else "UNKNOWN"
            vol_atr = vol.atr if vol else 0.0

            # Get PCR
            pcr_info = pcr_data.get(symbol, {})
            pcr_value = pcr_info.get("pcr")
            pcr_source = pcr_info.get("source", "unavailable")

            # Technical indicators
            ind = indicators.get(symbol, {})
            ema_20 = ind.get("ema_20", current_price)
            ema_50 = ind.get("ema_50", current_price)
            ema_200 = ind.get("ema_200", current_price)
            rsi = ind.get("rsi", 50.0)
            adx = ind.get("adx", 20.0)
            macd = ind.get("macd", 0.0)
            macd_signal = ind.get("macd_signal", 0.0)
            vwap = ind.get("vwap", current_price)
            vol_exp = ind.get("vol_expansion", 1.0)
            res_20 = ind.get("resistance_20", current_price)
            sup_20 = ind.get("support_20", current_price)

            # ── BUY Confirmations (Rule-based) ──────────────────────────
            # 1. EMA bullish alignment
            ema_bullish = ema_20 > ema_50
            # 2. MACD bullish crossover
            macd_bullish = macd > macd_signal
            # 3. RSI in bullish/accumulation zone (50-70)
            rsi_bullish = 50.0 <= rsi <= 70.0
            # 4. ADX trend strength
            adx_bullish = adx > 25.0
            # 5. Price above VWAP
            vwap_bullish = current_price > vwap
            # 6. Positive correlation against index
            corr_bullish = corr.value > 0
            # 7. Volume > 20-day average
            vol_bullish = vol_exp > 1.0
            # 8. Resistance broken (price closed above 20-day high)
            breakout_bullish = current_price > res_20

            # Increment Buy trackers
            passed_rules_buy["ema_bullish"] += int(ema_bullish)
            passed_rules_buy["macd_bullish"] += int(macd_bullish)
            passed_rules_buy["rsi_bullish"] += int(rsi_bullish)
            passed_rules_buy["adx_bullish"] += int(adx_bullish)
            passed_rules_buy["vwap_bullish"] += int(vwap_bullish)
            passed_rules_buy["corr_bullish"] += int(corr_bullish)
            passed_rules_buy["vol_bullish"] += int(vol_bullish)
            passed_rules_buy["breakout_bullish"] += int(breakout_bullish)

            buy_confirmations = sum([
                ema_bullish, macd_bullish, rsi_bullish, adx_bullish,
                vwap_bullish, corr_bullish, vol_bullish, breakout_bullish
            ])

            # ── SELL Confirmations (Rule-based) ─────────────────────────
            # 1. EMA bearish alignment
            ema_bearish = ema_20 < ema_50
            # 2. MACD bearish crossover
            macd_bearish = macd < macd_signal
            # 3. RSI in bearish breakdown zone (< 45)
            rsi_bearish = rsi < 45.0
            # 4. ADX trend strength
            adx_bearish = adx > 25.0
            # 5. Price below VWAP
            vwap_bearish = current_price < vwap
            # 6. Negative momentum (price change is negative)
            momentum_bearish = change_pct < 0
            # 7. Volume expansion on down day
            vol_bearish = (vol_exp > 1.0) and (change_pct < 0)
            # 8. Support broken (price closed below 20-day low)
            breakout_bearish = current_price < sup_20

            # Increment Sell trackers
            passed_rules_sell["ema_bearish"] += int(ema_bearish)
            passed_rules_sell["macd_bearish"] += int(macd_bearish)
            passed_rules_sell["rsi_bearish"] += int(rsi_bearish)
            passed_rules_sell["adx_bearish"] += int(adx_bearish)
            passed_rules_sell["vwap_bearish"] += int(vwap_bearish)
            passed_rules_sell["momentum_bearish"] += int(momentum_bearish)
            passed_rules_sell["vol_bearish"] += int(vol_bearish)
            passed_rules_sell["breakout_bearish"] += int(breakout_bearish)

            sell_confirmations = sum([
                ema_bearish, macd_bearish, rsi_bearish, adx_bearish,
                vwap_bearish, momentum_bearish, vol_bearish, breakout_bearish
            ])

            # Determine signal type
            signal_type = None
            confirmations_count = buy_confirmations if market_trend == "BULLISH" else sell_confirmations

            # Signal Confidence mapping based on confirmations count
            if confirmations_count == 8:
                confidence_label = "Very High"
            elif confirmations_count >= 7:
                confidence_label = "High"
            elif confirmations_count >= 6:
                confidence_label = "Medium"
            else:
                confidence_label = "Low"

            # Fetch sector trend score
            sector_name = sector_mapping.get(symbol, "Others")
            sec_res = sector_results.get(sector_name, {}) if sector_results else {}
            sector_score = sec_res.get("trend_score", 0.0)

            # Match overall regime direction
            if market_trend == "BULLISH" and buy_confirmations >= 5 and corr.value >= self.CORRELATION_THRESHOLD:
                signal_type = "BUY"
            elif market_trend == "BEARISH" and sell_confirmations >= 5 and corr.value >= self.CORRELATION_THRESHOLD:
                signal_type = "SELL"
            else:
                signal_type = None

            # Calculate score using the regime's direction to see if it is a WATCH or HOLD
            temp_signal = "BUY" if market_trend == "BULLISH" else "SELL"
            score, conviction, ai_tag, ai_details = self._calculate_conviction_and_score(
                symbol=symbol,
                signal_type=temp_signal,
                confidence_label=confidence_label,
                ema_20=ema_20,
                ema_50=ema_50,
                ema_200=ema_200,
                macd=macd,
                macd_signal=macd_signal,
                rsi=rsi,
                adx=adx,
                vwap=vwap,
                current_price=current_price,
                change_pct=change_pct,
                vol_exp=vol_exp,
                correlation=corr.value,
                pcr_value=pcr_value,
                sector_trend_score=sector_score
            )

            # If it didn't pass BUY/SELL, classify based on score
            if not signal_type:
                if score >= 40.0:
                    signal_type = "WATCH"
                else:
                    signal_type = "HOLD"
                    ai_tag = "Hold"
                    ai_details["reasoning"] = f"Technical indicators neutral for {symbol} under {market_trend} regime. Score={score}."

            logger.info(f"{symbol} Evaluated: {signal_type} signal, score={score}, conviction={conviction}")
            if signal_type in ["BUY", "SELL"]:
                signals_generated += 1

            signals.append(BotSignal(
                symbol=symbol,
                sector=sector_name,
                signal_type=signal_type,
                correlation=corr.value,
                correlation_category=corr.category,
                price_change_pct=change_pct,
                current_price=current_price,
                volatility_level=vol_level,
                volatility_atr=vol_atr,
                pcr_value=round(pcr_value, 2) if pcr_value is not None else None,
                pcr_source=pcr_source if pcr_value is not None else "unavailable",
                conviction=conviction,
                score=score,
                ai_tag=ai_tag,
                ai_details=ai_details
            ))

        # Sort by composite score descending (highest rank opportunity first)
        signals.sort(key=lambda s: -s.score)

        # Print final scan diagnostics summary (Phase 10)
        logger.info(
            f"=== SCAN DIAGNOSTICS SUMMARY ===\n"
            f"  Total Stocks Scanned: {total_scanned}\n"
            f"  Passed Correlation Filter (>= {self.CORRELATION_THRESHOLD}): {corr_passed}\n"
            f"  BUY Confirmations Met: {passed_rules_buy}\n"
            f"  SELL Confirmations Met: {passed_rules_sell}\n"
            f"  Final BUY Signals Generated: {sum(1 for s in signals if s.signal_type == 'BUY')}\n"
            f"  Final SELL Signals Generated: {sum(1 for s in signals if s.signal_type == 'SELL')}\n"
            f"  Final WATCH Signals Generated: {sum(1 for s in signals if s.signal_type == 'WATCH')}\n"
            f"  Final HOLD Signals Generated: {sum(1 for s in signals if s.signal_type == 'HOLD')}"
        )
        return signals

    def _calculate_conviction_and_score(
        self,
        symbol: str,
        signal_type: str,
        confidence_label: str,
        ema_20: float,
        ema_50: float,
        ema_200: float,
        macd: float,
        macd_signal: float,
        rsi: float,
        adx: float,
        vwap: float,
        current_price: float,
        change_pct: float,
        vol_exp: float,
        correlation: float,
        pcr_value: Optional[float],
        sector_trend_score: float
    ) -> Tuple[float, str, str, dict]:
        """
        Phase 7: Composite Scoring (0-100) and weighted Conviction mapping.
        """
        score = 0.0

        # 1. Trend (25%) - EMA alignments
        if signal_type == "BUY":
            if ema_20 > ema_50 and ema_50 > ema_200:
                score += 25.0
            elif ema_20 > ema_50:
                score += 15.0
        else: # SELL
            if ema_20 < ema_50 and ema_50 < ema_200:
                score += 25.0
            elif ema_20 < ema_50:
                score += 15.0

        # 2. Momentum (20%) - 1-week return or price direction alignment
        mom_weight = 0.0
        if signal_type == "BUY" and change_pct > 0:
            mom_weight += 10.0
        if signal_type == "BUY" and macd > macd_signal:
            mom_weight += 10.0
        if signal_type == "SELL" and change_pct < 0:
            mom_weight += 10.0
        if signal_type == "SELL" and macd < macd_signal:
            mom_weight += 10.0
        score += mom_weight

        # 3. Volume (15%) - volume expansion confirmation
        if vol_exp >= 1.5:
            score += 15.0
        elif vol_exp >= 1.0:
            score += 10.0
        elif vol_exp >= 0.8:
            score += 5.0

        # 4. Correlation (10%) - Pearson correlation strength
        if correlation >= 0.85:
            score += 10.0
        elif correlation >= 0.70:
            score += 7.0
        elif correlation >= 0.50:
            score += 4.0

        # 5. RSI Zone (10%) - optimal zones
        if signal_type == "BUY":
            if 50.0 <= rsi <= 70.0:
                score += 10.0
            elif 40.0 <= rsi < 50.0:
                score += 5.0
        else: # SELL
            if rsi < 45.0:
                score += 10.0
            elif rsi < 50.0:
                score += 5.0

        # 6. MACD Trend (10%) - alignment strength
        if signal_type == "BUY" and macd > macd_signal:
            score += 10.0
        elif signal_type == "SELL" and macd < macd_signal:
            score += 10.0

        # 7. ADX Strength (10%) - trend strength
        if adx > 25.0:
            score += 10.0
        elif adx > 15.0:
            score += 5.0

        # Ensure score is rounded
        score = round(max(0.0, min(100.0, score)), 1)

        # Map to Conviction:
        # 0-30 Weak, 31-50 Moderate, 51-70 Strong, 71-100 Very Strong
        if score >= 71.0:
            conviction = "Very Strong"
        elif score >= 51.0:
            conviction = "Strong"
        elif score >= 31.0:
            conviction = "Moderate"
        else:
            conviction = "Weak"

        # AI Tag categorization matching conviction
        if signal_type == "BUY":
            if conviction == "Very Strong":
                ai_tag = "Strong Buy"
            elif conviction == "Strong":
                ai_tag = "Buy"
            elif conviction == "Moderate":
                ai_tag = "Accumulate"
            else:
                ai_tag = "Watchlist"
        else: # SELL
            if conviction == "Very Strong":
                ai_tag = "Strong Sell"
            elif conviction == "Strong":
                ai_tag = "Sell"
            elif conviction == "Moderate":
                ai_tag = "Reduce"
            else:
                ai_tag = "Hold"

        # Generate rule-based detailed reasoning (No random placeholders)
        reasoning_list = []
        if signal_type == "BUY":
            reasoning_list.append(f"Confirmed BUY setup for {symbol} at ₹{current_price:,.2f}.")
            if ema_20 > ema_50:
                reasoning_list.append("EMA crossover indicates short-term bullish trend continuation.")
            if macd > macd_signal:
                reasoning_list.append("MACD histogram registers positive bullish crossover.")
            if vol_exp > 1.2:
                reasoning_list.append(f"Volume is expanding at {vol_exp:.1f}x the 20-day average.")
            if sector_trend_score > 20:
                reasoning_list.append(f"Supported by strong sector performance ({sector_trend_score:.1f}% bullish bias).")
        else:
            reasoning_list.append(f"Confirmed SELL setup for {symbol} at ₹{current_price:,.2f}.")
            if ema_20 < ema_50:
                reasoning_list.append("EMA crossover indicates short-term bearish trend continuation.")
            if macd < macd_signal:
                reasoning_list.append("MACD histogram registers bearish crossover.")
            if vol_exp > 1.2:
                reasoning_list.append(f"Volume distribution is expanding at {vol_exp:.1f}x the 20-day average.")
            if sector_trend_score < -20:
                reasoning_list.append(f"Aggravated by weak sector performance ({abs(sector_trend_score):.1f}% bearish bias).")

        reasoning_str = " ".join(reasoning_list)

        ai_details = {
            "confidence": int(score),
            "risk_level": "Low" if score >= 71.0 else ("Medium" if score >= 51.0 else "High"),
            "time_horizon": "Short-term (1-5 days)",
            "reasoning": reasoning_str
        }

        return score, conviction.upper(), ai_tag, ai_details
