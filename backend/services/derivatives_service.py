"""
Derivatives Data Service

Provides derivatives-related data (PCR, Open Interest, Sentiment) for stocks.
Uses real Upstox option chain API with simulated fallback.
"""

import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum

from data.fno_stocks import has_derivatives

logger = logging.getLogger(__name__)


class OIChangeType(str, Enum):
    """Open Interest Change Classification"""
    LONG_BUILDUP = "Long Buildup"
    SHORT_BUILDUP = "Short Buildup"
    SHORT_COVERING = "Short Covering"
    LONG_UNWINDING = "Long Unwinding"
    NA = "N/A"


class Sentiment(str, Enum):
    """Derivatives Sentiment"""
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"
    NA = "N/A"


@dataclass
class DerivativesData:
    """Container for derivatives-related data for a stock."""
    pcr: Optional[float]              # Put-Call Ratio (None if no derivatives)
    oi_change: OIChangeType           # OI Change classification
    sentiment: Sentiment              # Derived sentiment from PCR
    market_interpretation: str        # Human-readable explanation
    has_derivatives: bool             # Whether stock has F&O available
    data_source: str = "unavailable"  # "upstox" or "unavailable"
    
    def to_dict(self) -> dict:
        """Convert to API response format."""
        return {
            "pcr": round(self.pcr, 2) if self.pcr is not None else "N/A",
            "oi_change": self.oi_change.value,
            "sentiment": self.sentiment.value,
            "market_interpretation": self.market_interpretation,
            "has_derivatives": self.has_derivatives
        }


class DerivativesService:
    """
    Service for fetching and calculating derivatives data.
    
    Uses real option chain cache from Dragonfly.
    """
    
    # Confidence reduction for stocks without derivatives
    NO_DERIVATIVES_CONFIDENCE_PENALTY = 0.125  # 12.5% (midpoint of 10-15%)
    
    async def get_derivatives_data(
        self, 
        symbol: str, 
        price_change_pct: float = 0.0
    ) -> DerivativesData:
        """
        Get derivatives data for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE")
            price_change_pct: Percentage change in price (positive = up, negative = down)
            
        Returns:
            DerivativesData object with PCR, OI change, sentiment, and interpretation
        """
        # Check if stock has derivatives
        if not has_derivatives(symbol):
            return DerivativesData(
                pcr=None,
                oi_change=OIChangeType.NA,
                sentiment=Sentiment.NA,
                market_interpretation="Derivatives not available",
                has_derivatives=False
            )
        
        # Fetch raw derivatives data (real API first, no simulated fallback)
        raw_data = await self._fetch_raw_data(symbol)
        
        pcr = None
        oi_change = OIChangeType.NA
        sentiment = Sentiment.NA
        
        if raw_data.get("source") == "upstox":
            # Calculate PCR
            pcr = self.calculate_pcr(raw_data["put_oi"], raw_data["call_oi"])
            
            # Classify OI change based on price and OI movement
            price_up = price_change_pct >= 0
            oi_up = raw_data["oi_change_pct"] >= 0
            oi_change = self.classify_oi_change(price_up, oi_up)
            
            # Get sentiment from PCR
            sentiment = self.get_sentiment_from_pcr(pcr)
            
            # Generate human-readable interpretation
            interpretation = self.generate_market_interpretation(pcr, oi_change, sentiment)
        else:
            interpretation = "PCR unavailable because the connected Upstox account does not have F&O market data permission."
            
        return DerivativesData(
            pcr=pcr,
            oi_change=oi_change,
            sentiment=sentiment,
            market_interpretation=interpretation,
            has_derivatives=True,
            data_source=raw_data.get("source", "unavailable"),
        )
    
    async def _fetch_raw_data(self, symbol: str) -> dict:
        """
        Fetch raw derivatives data for a symbol.
        
        Strategy:
        1. Try real Upstox option chain cache (Dragonfly)
        2. If unavailable, return source="unavailable"
        """
        # ── Try reading from Dragonfly cache first ─────────────────
        if has_derivatives(symbol):
            try:
                from services.dragonfly_client import get_cache
                cache = get_cache()
                import json
                instrument_key = f"NSE_EQ|{symbol}"
                cache_keys = [
                    f"option_chain:{symbol}",
                    f"option_chain:{instrument_key}"
                ]
                strikes = []
                for key in cache_keys:
                    cached_val = cache.get(key)
                    if cached_val:
                        if isinstance(cached_val, str):
                            try:
                                strikes = json.loads(cached_val)
                            except Exception:
                                strikes = cached_val
                        else:
                            strikes = cached_val
                        if isinstance(strikes, dict) and "data" in strikes:
                            strikes = strikes["data"]
                        if strikes:
                            break

                if strikes:
                    total_put_oi = 0
                    total_call_oi = 0
                    for item in strikes:
                        call = item.get("call_options") or {}
                        put = item.get("put_options") or {}
                        call_market = call.get("market_data") or {}
                        put_market = put.get("market_data") or {}
                        total_call_oi += int(call_market.get("oi", 0) or 0)
                        total_put_oi += int(put_market.get("oi", 0) or 0)

                    if total_call_oi > 0 or total_put_oi > 0:
                        logger.info(f"PCR for {symbol}: {total_put_oi/max(1, total_call_oi):.4f} (Dragonfly cache, {len(strikes)} strikes)")
                        return {
                            "put_oi": total_put_oi,
                            "call_oi": total_call_oi,
                            "oi_change_pct": 0.0,
                            "futures_oi": 0,
                            "futures_oi_change_pct": 0.0,
                            "source": "upstox",
                        }
            except Exception as e:
                logger.debug(f"Dragonfly option chain failed for {symbol}: {e}")

        # No simulated fallback
        return {
            "put_oi": 0,
            "call_oi": 0,
            "oi_change_pct": 0.0,
            "futures_oi": 0,
            "futures_oi_change_pct": 0.0,
            "source": "unavailable",
        }
    
    @staticmethod
    def calculate_pcr(put_oi: int, call_oi: int) -> float:
        """
        Calculate Put-Call Ratio.
        
        PCR = Total Put Open Interest / Total Call Open Interest
        
        Args:
            put_oi: Total Put Open Interest
            call_oi: Total Call Open Interest
            
        Returns:
            PCR value (float)
        """
        if call_oi == 0:
            return 0.0
        return put_oi / call_oi
        
    @staticmethod
    def calculate_iv(iv_raw: float) -> float:
        """
        Standardize raw IV percentage representation.
        If the raw IV is a decimal fraction (e.g. 0.15), it returns 15.0.
        Otherwise, returns it unchanged.
        """
        return iv_raw * 100.0 if 0.0 < iv_raw < 1.0 else iv_raw
    
    @staticmethod
    def classify_oi_change(price_up: bool, oi_up: bool) -> OIChangeType:
        """
        Classify Open Interest change based on price and OI movement.
        
        | Price | OI  | Classification   |
        |-------|-----|------------------|
        | ↑     | ↑   | Long Buildup     |
        | ↓     | ↑   | Short Buildup    |
        | ↑     | ↓   | Short Covering   |
        | ↓     | ↓   | Long Unwinding   |
        
        Args:
            price_up: True if price increased
            oi_up: True if OI increased
            
        Returns:
            OIChangeType enum value
        """
        if price_up and oi_up:
            return OIChangeType.LONG_BUILDUP
        elif not price_up and oi_up:
            return OIChangeType.SHORT_BUILDUP
        elif price_up and not oi_up:
            return OIChangeType.SHORT_COVERING
        else:  # not price_up and not oi_up
            return OIChangeType.LONG_UNWINDING
    
    @staticmethod
    def get_sentiment_from_pcr(pcr: float) -> Sentiment:
        """
        Derive sentiment from PCR value.
        
        | PCR Range | Sentiment |
        |-----------|-----------|
        | < 0.7     | Bearish   |
        | 0.7 - 1.2 | Neutral   |
        | > 1.2     | Bullish   |
        
        Args:
            pcr: Put-Call Ratio
            
        Returns:
            Sentiment enum value
        """
        if pcr < 0.7:
            return Sentiment.BEARISH
        elif pcr > 1.2:
            return Sentiment.BULLISH
        else:
            return Sentiment.NEUTRAL
    
    @staticmethod
    def generate_market_interpretation(
        pcr: float, 
        oi_change: OIChangeType, 
        sentiment: Sentiment
    ) -> str:
        """
        Generate human-readable market interpretation.
        
        Combines PCR bias, OI behavior, and price action into a clear explanation.
        
        Args:
            pcr: Put-Call Ratio
            oi_change: OI Change classification
            sentiment: Derived sentiment
            
        Returns:
            Human-readable interpretation string
        """
        # PCR interpretation
        if pcr < 0.7:
            pcr_text = "Call writers dominating"
        elif pcr > 1.2:
            pcr_text = "Put writers active"
        else:
            pcr_text = "Balanced options activity"
        
        # OI interpretation
        oi_interpretations = {
            OIChangeType.LONG_BUILDUP: "fresh long positions being added",
            OIChangeType.SHORT_BUILDUP: "shorts increasing",
            OIChangeType.SHORT_COVERING: "shorts covering",
            OIChangeType.LONG_UNWINDING: "positions unwinding"
        }
        oi_text = oi_interpretations.get(oi_change, "unclear OI pattern")
        
        # Combine into interpretation
        if oi_change == OIChangeType.LONG_BUILDUP and sentiment == Sentiment.BULLISH:
            return f"{pcr_text} with fresh long buildup - strong bullish conviction"
        elif oi_change == OIChangeType.SHORT_BUILDUP and sentiment == Sentiment.BEARISH:
            return f"{pcr_text}, shorts increasing - bearish pressure"
        elif oi_change == OIChangeType.SHORT_COVERING:
            return f"{pcr_text}, {oi_text} - potential reversal"
        elif oi_change == OIChangeType.LONG_UNWINDING:
            return f"{pcr_text}, {oi_text} - weak conviction"
        else:
            return f"{pcr_text}, {oi_text}"
    
    def get_confidence_penalty(self, symbol: str) -> float:
        """
        Get confidence penalty for stocks without derivatives.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Confidence penalty (0.0 for F&O stocks, 0.125 for non-F&O stocks)
        """
        if has_derivatives(symbol):
            return 0.0
        return self.NO_DERIVATIVES_CONFIDENCE_PENALTY
