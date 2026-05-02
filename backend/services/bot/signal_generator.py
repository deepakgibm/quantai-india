"""
Bot Signal Generator

Combines analysis results with market trend to produce BUY/SELL signals.
Uses correlation, price change, volatility, and PCR confirmation.
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class BotSignal:
    """A generated BUY or SELL signal."""
    symbol: str
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

    def to_dict(self) -> dict:
        return asdict(self)


class SignalGenerator:
    """
    Generates BUY/SELL signals based on market regime.

    BEARISH market → SELL signals for high-correlation stocks dropping ≥ 2%
    BULLISH market → BUY signals for high-correlation stocks rising ≥ 2%
    PCR is used as confirmation to adjust conviction level.
    """

    PRICE_CHANGE_THRESHOLD = 2.0   # Minimum % change to trigger signal
    CORRELATION_THRESHOLD = 0.7    # Minimum correlation for signal

    def generate_signals(
        self,
        market_trend: str,
        correlations: Dict[str, "CorrelationResult"],
        volatilities: Dict[str, "VolatilityResult"],
        price_changes: Dict[str, dict],   # {symbol: {current, previous, change_pct}}
        pcr_data: Dict[str, dict],         # {symbol: {pcr, source}}
    ) -> List[BotSignal]:
        """
        Generate signals based on market regime and stock analysis.

        Args:
            market_trend: "BULLISH" or "BEARISH"
            correlations: Correlation results per stock
            volatilities: Volatility results per stock
            price_changes: Price change data per stock
            pcr_data: PCR values per stock

        Returns:
            List of BotSignal objects sorted by conviction strength
        """
        signals: List[BotSignal] = []

        for symbol, corr in correlations.items():
            # Only consider highly correlated stocks
            if corr.value < self.CORRELATION_THRESHOLD:
                continue

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

            # Signal logic
            signal_type = None

            if market_trend == "BEARISH":
                if change_pct <= -self.PRICE_CHANGE_THRESHOLD:
                    signal_type = "SELL"
            elif market_trend == "BULLISH":
                if change_pct >= self.PRICE_CHANGE_THRESHOLD:
                    signal_type = "BUY"

            if signal_type is None:
                continue

            # Conviction calculation
            conviction = self._calculate_conviction(
                signal_type, corr.value, abs(change_pct), pcr_value
            )

            signals.append(BotSignal(
                symbol=symbol,
                signal_type=signal_type,
                correlation=corr.value,
                correlation_category=corr.category,
                price_change_pct=change_pct,
                current_price=current_price,
                volatility_level=vol_level,
                volatility_atr=vol_atr,
                pcr_value=round(pcr_value, 2) if pcr_value is not None else None,
                pcr_source=pcr_source,
                conviction=conviction,
            ))

        # Sort by conviction strength then by absolute price change
        conviction_order = {"STRONG": 0, "MODERATE": 1, "WEAK": 2}
        signals.sort(key=lambda s: (
            conviction_order.get(s.conviction, 3),
            -abs(s.price_change_pct),
        ))

        logger.info(
            f"Generated {len(signals)} signals "
            f"({sum(1 for s in signals if s.signal_type == 'BUY')} BUY, "
            f"{sum(1 for s in signals if s.signal_type == 'SELL')} SELL)"
        )
        return signals

    @staticmethod
    def _calculate_conviction(
        signal_type: str,
        correlation: float,
        abs_price_change: float,
        pcr_value: Optional[float],
    ) -> str:
        """
        Calculate signal conviction level.

        Factors:
        - Higher correlation → stronger conviction
        - Larger price move → stronger conviction
        - PCR confirmation → boosts conviction

        PCR confirmation:
        - For SELL: PCR < 0.7 confirms bearish bias
        - For BUY: PCR > 1.0 confirms bullish bias
        """
        score = 0

        # Correlation factor (0-3 points)
        if correlation >= 0.85:
            score += 3
        elif correlation >= 0.75:
            score += 2
        else:
            score += 1

        # Price change factor (0-3 points)
        if abs_price_change >= 5.0:
            score += 3
        elif abs_price_change >= 3.0:
            score += 2
        else:
            score += 1

        # PCR confirmation (0-2 points)
        if pcr_value is not None:
            if signal_type == "SELL" and pcr_value < 0.7:
                score += 2
            elif signal_type == "BUY" and pcr_value > 1.0:
                score += 2
            elif signal_type == "SELL" and pcr_value < 1.0:
                score += 1
            elif signal_type == "BUY" and pcr_value > 0.7:
                score += 1

        if score >= 6:
            return "STRONG"
        elif score >= 4:
            return "MODERATE"
        else:
            return "WEAK"
