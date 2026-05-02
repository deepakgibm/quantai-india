"""
Bot Analysis Engine

Pure computation module — no I/O, no API calls.
Provides: Pearson correlation, volatility (StdDev+ATR), EMA trend detection.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    symbol: str
    value: float
    category: str

    @staticmethod
    def categorize(value: float) -> str:
        abs_val = abs(value)
        if abs_val >= 0.7:
            return "HIGH"
        elif abs_val >= 0.4:
            return "MODERATE"
        else:
            return "LOW"


@dataclass
class VolatilityResult:
    symbol: str
    std_dev: float
    atr: float
    category: str

    @staticmethod
    def categorize(std_dev: float) -> str:
        annualized = std_dev * np.sqrt(252)
        if annualized > 0.40:
            return "HIGH"
        elif annualized > 0.20:
            return "MEDIUM"
        else:
            return "LOW"


@dataclass
class MarketTrend:
    trend: str
    ema_50: float
    ema_200: float
    momentum: float
    last_close: float


class AnalysisEngine:
    """Stateless analysis engine. All methods operate on DataFrames."""

    @staticmethod
    def calculate_correlations(
        stock_data: Dict[str, pd.DataFrame],
        index_df: pd.DataFrame,
        min_overlap_days: int = 20,
    ) -> Dict[str, CorrelationResult]:
        results: Dict[str, CorrelationResult] = {}
        if index_df.empty or len(index_df) < min_overlap_days:
            return results

        idx = index_df.copy()
        idx["date"] = pd.to_datetime(idx["timestamp"]).dt.date
        index_returns = idx.set_index("date")["close"].astype(float).pct_change().dropna()

        for symbol, sdf in stock_data.items():
            try:
                if len(sdf) < min_overlap_days:
                    continue
                s = sdf.copy()
                s["date"] = pd.to_datetime(s["timestamp"]).dt.date
                stock_returns = s.set_index("date")["close"].astype(float).pct_change().dropna()
                aligned = pd.DataFrame({"stock": stock_returns, "index": index_returns}).dropna()
                if len(aligned) < min_overlap_days:
                    continue
                corr_value = float(np.corrcoef(aligned["stock"].values, aligned["index"].values)[0, 1])
                if np.isnan(corr_value):
                    continue
                results[symbol] = CorrelationResult(
                    symbol=symbol, value=round(corr_value, 4),
                    category=CorrelationResult.categorize(corr_value),
                )
            except Exception as e:
                logger.debug(f"Correlation calc failed for {symbol}: {e}")
        logger.info(f"Calculated correlations for {len(results)} stocks")
        return results

    @staticmethod
    def calculate_volatility(
        stock_data: Dict[str, pd.DataFrame], atr_period: int = 14,
    ) -> Dict[str, VolatilityResult]:
        results: Dict[str, VolatilityResult] = {}
        for symbol, df in stock_data.items():
            try:
                if len(df) < atr_period + 1:
                    continue
                closes = df["close"].astype(float)
                highs = df["high"].astype(float)
                lows = df["low"].astype(float)
                daily_returns = closes.pct_change().dropna()
                std_dev = float(daily_returns.std())
                prev_close = closes.shift(1)
                tr = pd.concat([
                    highs - lows,
                    (highs - prev_close).abs(),
                    (lows - prev_close).abs(),
                ], axis=1).max(axis=1)
                atr = float(tr.rolling(window=atr_period).mean().iloc[-1])
                if np.isnan(std_dev) or np.isnan(atr):
                    continue
                results[symbol] = VolatilityResult(
                    symbol=symbol, std_dev=round(std_dev, 6),
                    atr=round(atr, 2), category=VolatilityResult.categorize(std_dev),
                )
            except Exception as e:
                logger.debug(f"Volatility calc failed for {symbol}: {e}")
        logger.info(f"Calculated volatility for {len(results)} stocks")
        return results

    @staticmethod
    def detect_market_trend(index_df: pd.DataFrame) -> Optional[MarketTrend]:
        if index_df.empty or len(index_df) < 10:
            return None
        closes = index_df["close"].astype(float)
        last_close = float(closes.iloc[-1])
        ema_50 = float(closes.ewm(span=50, adjust=False).mean().iloc[-1])
        if len(closes) >= 200:
            ema_200 = float(closes.ewm(span=200, adjust=False).mean().iloc[-1])
        else:
            ema_200 = float(closes.ewm(span=len(closes), adjust=False).mean().iloc[-1])
        momentum = 0.0
        if len(closes) >= 6:
            momentum = float(((closes.iloc[-1] - closes.iloc[-6]) / closes.iloc[-6]) * 100)
        trend = "BULLISH" if ema_50 > ema_200 else "BEARISH"
        result = MarketTrend(
            trend=trend, ema_50=round(ema_50, 2), ema_200=round(ema_200, 2),
            momentum=round(momentum, 2), last_close=round(last_close, 2),
        )
        logger.info(f"Market trend: {result.trend} | EMA50={result.ema_50} | EMA200={result.ema_200}")
        return result

    @staticmethod
    def calculate_price_change(current_price: float, previous_close: float) -> float:
        if previous_close <= 0:
            return 0.0
        return round(((current_price - previous_close) / previous_close) * 100, 2)
