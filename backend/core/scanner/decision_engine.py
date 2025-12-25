"""
Decision Engine for Scanner

Generates final Buy/Sell/Hold signals by fusing technical analysis
with derivatives sentiment (PCR, OI Change).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any

from strategies.base import ScanResult, SignalType
from services.derivatives_service import DerivativesData, OIChangeType, Sentiment


class FinalSignal(str, Enum):
    """Final trading signal"""
    BUY = "Buy"
    SELL = "Sell"
    HOLD = "Hold"


class SignalStrength(str, Enum):
    """Signal alignment strength"""
    STRONG = "Strong"
    MODERATE = "Moderate"
    WEAK = "Weak"


@dataclass
class DecisionResult:
    """Result from the decision engine."""
    final_signal: FinalSignal
    signal_strength: SignalStrength
    adjusted_confidence: float
    derivatives_data: DerivativesData
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        deriv_dict = self.derivatives_data.to_dict()
        return {
            "final_signal": self.final_signal.value,
            "signal_strength": self.signal_strength.value,
            "adjusted_confidence": round(self.adjusted_confidence, 2),
            **deriv_dict
        }


class DecisionEngine:
    """
    Decision Engine for generating Buy/Sell/Hold signals.
    
    Fuses technical analysis signals with derivatives sentiment to
    produce final actionable signals with confidence levels.
    """
    
    # Minimum confidence threshold for actionable signals
    CONFIDENCE_THRESHOLD = 0.70
    
    # Confidence penalty for stocks without derivatives
    NO_DERIVATIVES_PENALTY = 0.125  # 12.5%
    
    def generate_decision(
        self, 
        scan_result: ScanResult, 
        derivatives_data: DerivativesData
    ) -> DecisionResult:
        """
        Generate final decision from technical scan result and derivatives data.
        
        Args:
            scan_result: Technical analysis scan result
            derivatives_data: Derivatives data (PCR, OI, Sentiment)
            
        Returns:
            DecisionResult with final signal, strength, and adjusted confidence
        """
        # Adjust confidence for non-F&O stocks
        adjusted_confidence = self._calculate_adjusted_confidence(
            scan_result.confidence_score,
            derivatives_data.has_derivatives
        )
        
        # Generate final signal
        final_signal = self._determine_signal(
            scan_result.signal,
            adjusted_confidence,
            derivatives_data.sentiment,
            derivatives_data.oi_change,
            scan_result.trend
        )
        
        # Calculate signal strength
        signal_strength = self._calculate_signal_strength(
            scan_result.signal,
            derivatives_data.sentiment,
            derivatives_data.oi_change,
            derivatives_data.has_derivatives
        )
        
        return DecisionResult(
            final_signal=final_signal,
            signal_strength=signal_strength,
            adjusted_confidence=adjusted_confidence,
            derivatives_data=derivatives_data
        )
    
    def _calculate_adjusted_confidence(
        self, 
        original_confidence: float, 
        has_derivatives: bool
    ) -> float:
        """
        Calculate adjusted confidence score.
        
        Non-F&O stocks receive a 12.5% penalty due to missing derivatives confirmation.
        
        Args:
            original_confidence: Original confidence from technical scan
            has_derivatives: Whether stock has F&O available
            
        Returns:
            Adjusted confidence score
        """
        if has_derivatives:
            return original_confidence
        
        # Apply penalty
        adjusted = original_confidence * (1 - self.NO_DERIVATIVES_PENALTY)
        return max(0.0, min(1.0, adjusted))  # Clamp to [0, 1]
    
    def _determine_signal(
        self,
        technical_signal: SignalType,
        confidence: float,
        sentiment: Sentiment,
        oi_change: OIChangeType,
        trend: str
    ) -> FinalSignal:
        """
        Determine final Buy/Sell/Hold signal.
        
        BUY Conditions (ALL must be met):
        - Technical Signal = Bullish
        - Confidence >= 70%
        - Sentiment = Bullish
        - OI Change = Long Buildup OR Short Covering
        - Trend != Strong Downtrend
        
        SELL Conditions (ALL must be met):
        - Technical Signal = Bearish
        - Confidence >= 70%
        - Sentiment = Bearish
        - OI Change = Short Buildup OR Long Unwinding
        - Trend != Strong Uptrend
        
        HOLD when:
        - Technical and derivatives signals conflict
        - Sentiment = Neutral
        - Confidence < 70%
        - OR derivatives data is missing/unclear
        """
        # Check if derivatives data is available
        if sentiment == Sentiment.NA:
            # No derivatives - use technical signal only with reduced confidence
            if confidence >= self.CONFIDENCE_THRESHOLD:
                if technical_signal == SignalType.BULLISH:
                    return FinalSignal.BUY
                elif technical_signal == SignalType.BEARISH:
                    return FinalSignal.SELL
            return FinalSignal.HOLD
        
        # Check confidence threshold
        if confidence < self.CONFIDENCE_THRESHOLD:
            return FinalSignal.HOLD
        
        # Check for BUY signal
        if self._check_buy_conditions(technical_signal, sentiment, oi_change, trend):
            return FinalSignal.BUY
        
        # Check for SELL signal
        if self._check_sell_conditions(technical_signal, sentiment, oi_change, trend):
            return FinalSignal.SELL
        
        # Default to HOLD (conflicting signals or neutral sentiment)
        return FinalSignal.HOLD
    
    def _check_buy_conditions(
        self,
        technical_signal: SignalType,
        sentiment: Sentiment,
        oi_change: OIChangeType,
        trend: str
    ) -> bool:
        """Check if all BUY conditions are met."""
        # Technical must be bullish
        if technical_signal != SignalType.BULLISH:
            return False
        
        # Sentiment must be bullish
        if sentiment != Sentiment.BULLISH:
            return False
        
        # OI must show long buildup or short covering
        bullish_oi = oi_change in [OIChangeType.LONG_BUILDUP, OIChangeType.SHORT_COVERING]
        if not bullish_oi:
            return False
        
        # Trend must not be strong downtrend
        if self._is_strong_downtrend(trend):
            return False
        
        return True
    
    def _check_sell_conditions(
        self,
        technical_signal: SignalType,
        sentiment: Sentiment,
        oi_change: OIChangeType,
        trend: str
    ) -> bool:
        """Check if all SELL conditions are met."""
        # Technical must be bearish
        if technical_signal != SignalType.BEARISH:
            return False
        
        # Sentiment must be bearish
        if sentiment != Sentiment.BEARISH:
            return False
        
        # OI must show short buildup or long unwinding
        bearish_oi = oi_change in [OIChangeType.SHORT_BUILDUP, OIChangeType.LONG_UNWINDING]
        if not bearish_oi:
            return False
        
        # Trend must not be strong uptrend
        if self._is_strong_uptrend(trend):
            return False
        
        return True
    
    def _is_strong_downtrend(self, trend: str) -> bool:
        """Check if trend indicates strong downtrend."""
        trend_lower = trend.lower()
        return "strong" in trend_lower and "down" in trend_lower
    
    def _is_strong_uptrend(self, trend: str) -> bool:
        """Check if trend indicates strong uptrend."""
        trend_lower = trend.lower()
        return "strong" in trend_lower and "up" in trend_lower
    
    def _calculate_signal_strength(
        self,
        technical_signal: SignalType,
        sentiment: Sentiment,
        oi_change: OIChangeType,
        has_derivatives: bool
    ) -> SignalStrength:
        """
        Calculate signal strength based on alignment.
        
        STRONG: Tech + OI + PCR all aligned
        MODERATE: Partial alignment (2 of 3)
        WEAK: Conflict between signals
        """
        if not has_derivatives:
            # Without derivatives, max strength is Moderate
            return SignalStrength.MODERATE
        
        # Count aligned signals
        alignment_score = 0
        
        # Technical signal direction
        is_bullish_tech = technical_signal == SignalType.BULLISH
        is_bearish_tech = technical_signal == SignalType.BEARISH
        
        # Sentiment alignment
        if sentiment == Sentiment.BULLISH and is_bullish_tech:
            alignment_score += 1
        elif sentiment == Sentiment.BEARISH and is_bearish_tech:
            alignment_score += 1
        elif sentiment == Sentiment.NEUTRAL:
            # Neutral sentiment - partial alignment
            pass
        else:
            # Conflicting sentiment
            alignment_score -= 1
        
        # OI alignment
        bullish_oi = oi_change in [OIChangeType.LONG_BUILDUP, OIChangeType.SHORT_COVERING]
        bearish_oi = oi_change in [OIChangeType.SHORT_BUILDUP, OIChangeType.LONG_UNWINDING]
        
        if is_bullish_tech and bullish_oi:
            alignment_score += 1
        elif is_bearish_tech and bearish_oi:
            alignment_score += 1
        elif (is_bullish_tech and bearish_oi) or (is_bearish_tech and bullish_oi):
            alignment_score -= 1
        
        # Determine strength
        if alignment_score >= 2:
            return SignalStrength.STRONG
        elif alignment_score >= 0:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
