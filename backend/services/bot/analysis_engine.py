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
    value: float              # Correlation Score (90-day Pearson correlation)
    category: str             # Correlation Strength (HIGH, MODERATE, LOW)
    trend: str                # Trend direction of correlation (BULLISH, BEARISH, NEUTRAL)
    confidence: float         # Confidence index (0.0 to 1.0)
    corr_30: float
    corr_60: float
    corr_90: float
    corr_180: float

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
    true_range: float
    annualized_volatility: float
    historical_volatility: float
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
    advances: int = 0
    declines: int = 0
    above_ema50_count: int = 0
    above_ema200_count: int = 0
    pct_above_ema50: float = 0.0
    pct_above_ema200: float = 0.0
    momentum_5d: float = 0.0
    momentum_1m: float = 0.0
    pct_outperforming: float = 0.0


class AnalysisEngine:
    """Stateless analysis engine. All methods operate on DataFrames."""

    @staticmethod
    def synthesize_index_df(stock_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Synthesize an equal-weighted returns-compounded index DataFrame.
        """
        if not stock_data:
            return pd.DataFrame()
        
        # 1. Collect all daily returns series
        all_returns = []
        for symbol, df in stock_data.items():
            if df.empty:
                continue
            s = df.copy()
            s["date"] = pd.to_datetime(s["timestamp"]).dt.date
            ret = s.set_index("date")["close"].astype(float).pct_change()
            all_returns.append(ret)
            
        if not all_returns:
            return pd.DataFrame()
            
        # Align and take the mean return for each day
        aligned_returns = pd.concat(all_returns, axis=1)
        mean_returns = aligned_returns.mean(axis=1).fillna(0.0).sort_index()
        
        # Compound price starting at 1000.0
        index_prices = 1000.0 * (1.0 + mean_returns).cumprod()
        
        index_df = pd.DataFrame({
            "timestamp": [dt.strftime("%Y-%m-%d") for dt in index_prices.index],
            "close": index_prices.values
        })
        
        # 2. Synthesize high/low using average highs/lows percentage ratio
        all_high_ratios = []
        all_low_ratios = []
        for symbol, df in stock_data.items():
            if df.empty:
                continue
            s = df.copy()
            s["date"] = pd.to_datetime(s["timestamp"]).dt.date
            closes = s.set_index("date")["close"].astype(float)
            highs = s.set_index("date")["high"].astype(float)
            lows = s.set_index("date")["low"].astype(float)
            all_high_ratios.append(highs / (closes + 1e-9))
            all_low_ratios.append(lows / (closes + 1e-9))
            
        mean_high_ratio = pd.concat(all_high_ratios, axis=1).mean(axis=1).fillna(1.002).sort_index()
        mean_low_ratio = pd.concat(all_low_ratios, axis=1).mean(axis=1).fillna(0.998).sort_index()
        
        index_df["high"] = index_df["close"] * mean_high_ratio.values
        index_df["low"] = index_df["close"] * mean_low_ratio.values
        
        return index_df

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

                # Compute rolling Pearson correlations
                total_len = len(aligned)
                
                # 30-day
                c30_df = aligned.tail(min(30, total_len))
                corr_30 = float(np.corrcoef(c30_df["stock"].values, c30_df["index"].values)[0, 1]) if len(c30_df) >= 15 else 0.0
                
                # 60-day
                c60_df = aligned.tail(min(60, total_len))
                corr_60 = float(np.corrcoef(c60_df["stock"].values, c60_df["index"].values)[0, 1]) if len(c60_df) >= 30 else 0.0
                
                # 90-day
                c90_df = aligned.tail(min(90, total_len))
                corr_90 = float(np.corrcoef(c90_df["stock"].values, c90_df["index"].values)[0, 1]) if len(c90_df) >= 45 else 0.0
                
                # 180-day
                c180_df = aligned.tail(min(180, total_len))
                corr_180 = float(np.corrcoef(c180_df["stock"].values, c180_df["index"].values)[0, 1]) if len(c180_df) >= 90 else 0.0

                corr_value = corr_90  # Default to 90 days
                if np.isnan(corr_value):
                    corr_value = 0.0

                # Determine Trend (crossover)
                trend = "NEUTRAL"
                if not np.isnan(corr_30) and not np.isnan(corr_90):
                    if corr_30 > corr_90 + 0.05:
                        trend = "BULLISH"
                    elif corr_30 < corr_90 - 0.05:
                        trend = "BEARISH"

                # Categorize strength
                category = CorrelationResult.categorize(corr_value)

                # Confidence calculation (data density + category)
                base_conf = min(1.0, total_len / 180.0)
                multiplier = 0.9 if category == "HIGH" else (0.6 if category == "MODERATE" else 0.3)
                confidence = round(base_conf * multiplier, 2)

                results[symbol] = CorrelationResult(
                    symbol=symbol,
                    value=round(corr_value, 4),
                    category=category,
                    trend=trend,
                    confidence=confidence,
                    corr_30=round(0.0 if np.isnan(corr_30) else corr_30, 4),
                    corr_60=round(0.0 if np.isnan(corr_60) else corr_60, 4),
                    corr_90=round(0.0 if np.isnan(corr_90) else corr_90, 4),
                    corr_180=round(0.0 if np.isnan(corr_180) else corr_180, 4),
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
                if np.isnan(std_dev):
                    std_dev = 0.0

                prev_close = closes.shift(1)
                tr = pd.concat([
                    highs - lows,
                    (highs - prev_close).abs(),
                    (lows - prev_close).abs(),
                ], axis=1).max(axis=1)
                
                atr = float(tr.rolling(window=atr_period).mean().iloc[-1])
                true_range = float(tr.iloc[-1])
                
                if np.isnan(atr) or np.isnan(true_range):
                    continue

                ann_vol = std_dev * np.sqrt(252) * 100.0
                hist_vol = std_dev * np.sqrt(252) * 100.0

                results[symbol] = VolatilityResult(
                    symbol=symbol,
                    std_dev=round(std_dev, 6),
                    atr=round(atr, 2),
                    true_range=round(true_range, 2),
                    annualized_volatility=round(ann_vol, 2),
                    historical_volatility=round(hist_vol, 2),
                    category=VolatilityResult.categorize(std_dev),
                )
            except Exception as e:
                logger.debug(f"Volatility calc failed for {symbol}: {e}")
        logger.info(f"Calculated volatility for {len(results)} stocks")
        return results

    @staticmethod
    def detect_market_trend(index_df: pd.DataFrame, stock_data: Dict[str, pd.DataFrame] = None) -> Optional[MarketTrend]:
        if index_df.empty or len(index_df) < 10:
            return None
        closes = index_df["close"].astype(float)
        last_close = float(closes.iloc[-1])
        
        # Calculate index EMAs
        ema_50 = float(closes.ewm(span=50, adjust=False).mean().iloc[-1])
        ema_200 = float(closes.ewm(span=200, adjust=False).mean().iloc[-1]) if len(closes) >= 200 else float(closes.ewm(span=len(closes), adjust=False).mean().iloc[-1])
        
        # Default fallback values
        advances = 0
        declines = 0
        above_ema50 = 0
        above_ema200 = 0
        pct_above_ema50 = 0.0
        pct_above_ema200 = 0.0
        avg_mom_5d = 0.0
        avg_mom_1m = 0.0
        pct_outperforming = 0.0
        
        if stock_data:
            total_stocks = len(stock_data)
            all_mom_5d = []
            all_mom_1m = []
            outperformers = 0
            index_change = ((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) * 100 if len(closes) >= 2 else 0.0
            
            for symbol, df in stock_data.items():
                if len(df) >= 2:
                    s_closes = df["close"].astype(float)
                    last = s_closes.iloc[-1]
                    prev = s_closes.iloc[-2]
                    
                    # Advances/Declines
                    if last > prev:
                        advances += 1
                    elif last < prev:
                        declines += 1
                        
                    # Outperformance (Relative Strength)
                    s_change = ((last - prev) / prev) * 100
                    if s_change > index_change:
                        outperformers += 1
                        
                    # EMAs
                    s_ema50 = s_closes.ewm(span=50, adjust=False).mean().iloc[-1]
                    s_ema200 = s_closes.ewm(span=200, adjust=False).mean().iloc[-1] if len(df) >= 200 else s_closes.ewm(span=len(df), adjust=False).mean().iloc[-1]
                    if last > s_ema50:
                        above_ema50 += 1
                    if last > s_ema200:
                        above_ema200 += 1
                        
                    # Momentum
                    if len(df) >= 6:
                        all_mom_5d.append(((last - s_closes.iloc[-6]) / s_closes.iloc[-6]) * 100)
                    if len(df) >= 21:
                        all_mom_1m.append(((last - s_closes.iloc[-21]) / s_closes.iloc[-21]) * 100)
            
            if total_stocks > 0:
                pct_above_ema50 = (above_ema50 / total_stocks) * 100
                pct_above_ema200 = (above_ema200 / total_stocks) * 100
                pct_outperforming = (outperformers / total_stocks) * 100
                
            avg_mom_5d = float(np.mean(all_mom_5d)) if all_mom_5d else 0.0
            avg_mom_1m = float(np.mean(all_mom_1m)) if all_mom_1m else 0.0
            
        # Determine Market Trend based on Nifty 500 Breadth Rules
        # Bullish if at least 3 of 5 conditions are met:
        cond_ema50_pct = pct_above_ema50 > 60.0
        cond_ema_alignment = ema_50 > ema_200
        cond_breadth = advances > declines
        cond_ad_ratio = (advances / max(1, declines)) > 1.0
        cond_momentum = avg_mom_5d > 0.0
        
        bullish_conditions = sum([
            cond_ema50_pct, cond_ema_alignment, cond_breadth, cond_ad_ratio, cond_momentum
        ])
        
        trend = "BULLISH" if bullish_conditions >= 3 else "BEARISH"
        
        result = MarketTrend(
            trend=trend,
            ema_50=round(ema_50, 2),
            ema_200=round(ema_200, 2),
            momentum=round(avg_mom_5d, 2),
            last_close=round(last_close, 2),
            advances=advances,
            declines=declines,
            above_ema50_count=above_ema50,
            above_ema200_count=above_ema200,
            pct_above_ema50=round(pct_above_ema50, 2),
            pct_above_ema200=round(pct_above_ema200, 2),
            momentum_5d=round(avg_mom_5d, 2),
            momentum_1m=round(avg_mom_1m, 2),
            pct_outperforming=round(pct_outperforming, 2)
        )
        logger.info(
            f"NIFTY 500 Market Trend: {result.trend} | "
            f"Bullish Conditions: {bullish_conditions}/5 | "
            f"Above EMA50: {pct_above_ema50:.1f}% | "
            f"Adv/Dec: {advances}/{declines}"
        )
        return result

    @staticmethod
    def calculate_price_change(current_price: float, previous_close: float) -> float:
        if previous_close <= 0:
            return 0.0
        return round(((current_price - previous_close) / previous_close) * 100, 2)

    @staticmethod
    def calculate_market_breadth(stock_data: Dict[str, pd.DataFrame]) -> dict:
        """
        Phase 5: Market Breadth metrics calculation for the active universe.
        """
        total = len(stock_data)
        if total == 0:
            return {}
            
        advancing = 0
        declining = 0
        above_20_ema = 0
        above_50_ema = 0
        above_200_ema = 0
        rsi_gt_60 = 0
        rsi_lt_40 = 0
        new_highs = 0
        new_lows = 0
        breakouts = 0
        breakdowns = 0
        
        rs_leaders = [] # List of (symbol, rs_score)
        
        for symbol, df in stock_data.items():
            if len(df) < 20:
                continue
                
            closes = df['close'].astype(float)
            highs = df['high'].astype(float)
            lows = df['low'].astype(float)
            
            last_close = float(closes.iloc[-1])
            prev_close = float(closes.iloc[-2]) if len(closes) >= 2 else last_close
            
            # Advancing / Declining
            if last_close > prev_close:
                advancing += 1
            elif last_close < prev_close:
                declining += 1
                
            # EMAs
            ema_20 = float(closes.ewm(span=20, adjust=False).mean().iloc[-1])
            ema_50 = float(closes.ewm(span=50, adjust=False).mean().iloc[-1])
            ema_200 = float(closes.ewm(span=200, adjust=False).mean().iloc[-1]) if len(closes) >= 200 else float(closes.ewm(span=len(closes), adjust=False).mean().iloc[-1])
            
            if last_close > ema_20:
                above_20_ema += 1
            if last_close > ema_50:
                above_50_ema += 1
            if last_close > ema_200:
                above_200_ema += 1
                
            # RSI
            rsi_series = calc_rsi(closes)
            last_rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0
            if last_rsi > 60:
                rsi_gt_60 += 1
            elif last_rsi < 40:
                rsi_lt_40 += 1
                
            # New Highs / Lows (52-week or max lookback)
            lookback = min(252, len(df))
            max_high = float(highs.iloc[-lookback:].max())
            min_low = float(lows.iloc[-lookback:].min())
            if last_close >= max_high * 0.99:
                new_highs += 1
            if last_close <= min_low * 1.01:
                new_lows += 1
                
            # Breakout / Breakdown (20-day high/low)
            if len(closes) >= 21:
                high_20 = float(highs.iloc[-21:-1].max())
                low_20 = float(lows.iloc[-21:-1].min())
                if last_close > high_20:
                    breakouts += 1
                elif last_close < low_20:
                    breakdowns += 1
                    
            # Relative Strength (1-month change)
            ret_1m = ((last_close - closes.iloc[-21]) / closes.iloc[-21]) if len(closes) >= 21 else 0.0
            rs_leaders.append((symbol, ret_1m))
            
        # Top 10 relative strength leaders
        rs_leaders.sort(key=lambda x: x[1], reverse=True)
        rs_leaders_top = [sym for sym, _ in rs_leaders[:10]]
        
        return {
            "advancing": advancing,
            "declining": declining,
            "above_20_ema": above_20_ema,
            "above_50_ema": above_50_ema,
            "above_200_ema": above_200_ema,
            "rsi_greater_60": rsi_gt_60,
            "rsi_less_40": rsi_lt_40,
            "new_highs": new_highs,
            "new_lows": new_lows,
            "breakouts": breakouts,
            "breakdowns": breakdowns,
            "relative_strength_leaders": rs_leaders_top
        }

    @staticmethod
    def calculate_indicators(stock_data: Dict[str, pd.DataFrame]) -> Dict[str, dict]:
        """
        Calculate strict technical indicators (EMA, MACD, RSI, ADX, VWAP) for all stocks in the universe.
        Calculations are derived solely from real historical candles.
        """
        results = {}
        for symbol, df in stock_data.items():
            if len(df) < 20:
                continue
            try:
                closes = df["close"].astype(float)
                highs = df["high"].astype(float)
                lows = df["low"].astype(float)
                volumes = df["volume"].astype(float)
                
                # EMAs
                ema_20 = float(closes.ewm(span=20, adjust=False).mean().iloc[-1])
                ema_50 = float(closes.ewm(span=50, adjust=False).mean().iloc[-1])
                ema_200 = float(closes.ewm(span=200, adjust=False).mean().iloc[-1]) if len(closes) >= 200 else float(closes.ewm(span=len(closes), adjust=False).mean().iloc[-1])
                
                # RSI
                rsi_series = calc_rsi(closes)
                last_rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0
                
                # ADX
                adx_series = calc_adx(highs, lows, closes)
                last_adx = float(adx_series.iloc[-1]) if not adx_series.empty else 20.0
                
                # MACD
                ema_12 = closes.ewm(span=12, adjust=False).mean()
                ema_26 = closes.ewm(span=26, adjust=False).mean()
                macd_line = ema_12 - ema_26
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                last_macd = float(macd_line.iloc[-1])
                last_signal = float(signal_line.iloc[-1])
                
                # VWAP (20-day Typical Price volume-weighted)
                tp = (highs + lows + closes) / 3.0
                tp_vol = tp * volumes
                vwap_20 = float(tp_vol.rolling(20).sum().iloc[-1] / (volumes.rolling(20).sum().iloc[-1] + 1e-9))
                
                # Volume average & expansion
                vol_avg = float(volumes.rolling(20).mean().iloc[-1])
                last_volume = float(volumes.iloc[-1])
                vol_exp = last_volume / (vol_avg + 1e-9)
                
                # 20-day High / Low for breakouts/breakdowns
                res_20 = float(highs.rolling(20).max().iloc[-2]) if len(df) >= 21 else float(highs.max())
                sup_20 = float(lows.rolling(20).min().iloc[-2]) if len(df) >= 21 else float(lows.min())
                
                results[symbol] = {
                    "ema_20": round(ema_20, 2),
                    "ema_50": round(ema_50, 2),
                    "ema_200": round(ema_200, 2),
                    "rsi": round(last_rsi, 2),
                    "adx": round(last_adx, 2),
                    "macd": round(last_macd, 4),
                    "macd_signal": round(last_signal, 4),
                    "vwap": round(vwap_20, 2),
                    "vol_avg": round(vol_avg, 1),
                    "vol_expansion": round(vol_exp, 2),
                    "resistance_20": round(res_20, 2),
                    "support_20": round(sup_20, 2)
                }
            except Exception as e:
                logger.debug(f"Indicator calculation failed for {symbol}: {e}")
        return results

    @staticmethod
    def calculate_sector_analysis(stock_data: Dict[str, pd.DataFrame]) -> Dict[str, dict]:
        """
        Phase 6: Sector-Level Analysis.
        Aggregates stock-level analysis into sector metrics.
        """
        # Load sector mapping from database
        sector_mapping = {}
        try:
            from database import SessionLocal
            from sqlalchemy import text
            with SessionLocal() as session:
                res = session.execute(text("""
                    SELECT im.symbol, im.sector, ns.industry
                    FROM instrument_master im
                    LEFT JOIN nifty500_symbols ns ON im.symbol = ns.symbol
                """))
                for r in res:
                    if r[0]:
                        sector_mapping[r[0]] = (r[1] or "Others", r[2] or "Others")
        except Exception as e:
            logger.error(f"Failed to load sector mapping: {e}")
            
        sectors_data = {}
        
        for symbol, df in stock_data.items():
            if len(df) < 20:
                continue
                
            sector, _ = sector_mapping.get(symbol, ("Others", "Others"))
            if sector not in sectors_data:
                sectors_data[sector] = []
                
            # Calculate stock technicals
            closes = df['close'].astype(float)
            highs = df['high'].astype(float)
            lows = df['low'].astype(float)
            volumes = df['volume'].astype(float)
            
            last_close = float(closes.iloc[-1])
            prev_close = float(closes.iloc[-2]) if len(closes) >= 2 else last_close
            change_pct = ((last_close - prev_close) / prev_close) * 100.0 if prev_close > 0 else 0.0
            
            # RSI
            rsi_series = calc_rsi(closes)
            last_rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0
            
            # ADX
            adx_series = calc_adx(highs, lows, closes)
            last_adx = float(adx_series.iloc[-1]) if not adx_series.empty else 20.0
            
            # Momentum (1-week return)
            mom_pct = ((last_close - closes.iloc[-6]) / closes.iloc[-6]) * 100.0 if len(closes) >= 6 else 0.0
            
            # Volume Expansion (current volume vs 20-day average)
            vol_avg = float(volumes.iloc[-20:].mean()) if len(volumes) >= 20 else 1.0
            vol_exp = float(volumes.iloc[-1] / (vol_avg + 1e-9))
            
            # Trend determination
            ema_50 = float(closes.ewm(span=50, adjust=False).mean().iloc[-1])
            trend = "NEUTRAL"
            if last_close > ema_50:
                trend = "BULLISH"
            elif last_close < ema_50:
                trend = "BEARISH"
                
            sectors_data[sector].append({
                "symbol": symbol,
                "change_pct": change_pct,
                "rsi": last_rsi,
                "adx": last_adx,
                "momentum": mom_pct,
                "volume_expansion": vol_exp,
                "trend": trend
            })
            
        sector_results = {}
        for sector, stocks in sectors_data.items():
            cnt = len(stocks)
            if cnt == 0:
                continue
                
            bullish_pct = sum(1 for s in stocks if s["trend"] == "BULLISH") / cnt * 100
            bearish_pct = sum(1 for s in stocks if s["trend"] == "BEARISH") / cnt * 100
            neutral_pct = sum(1 for s in stocks if s["trend"] == "NEUTRAL") / cnt * 100
            
            avg_rsi = float(np.mean([s["rsi"] for s in stocks]))
            avg_adx = float(np.mean([s["adx"] for s in stocks]))
            avg_mom = float(np.mean([s["momentum"] for s in stocks]))
            avg_vol_exp = float(np.mean([s["volume_expansion"] for s in stocks]))
            avg_ret = float(np.mean([s["change_pct"] for s in stocks]))
            
            # Trend Score: bullish% minus bearish%
            trend_score = bullish_pct - bearish_pct
            
            sector_results[sector] = {
                "sector": sector,
                "stock_count": cnt,
                "bullish_pct": round(bullish_pct, 2),
                "bearish_pct": round(bearish_pct, 2),
                "neutral_pct": round(neutral_pct, 2),
                "avg_rsi": round(avg_rsi, 2),
                "avg_adx": round(avg_adx, 2),
                "avg_relative_strength": round(avg_ret, 2),
                "avg_momentum": round(avg_mom, 2),
                "volume_expansion": round(avg_vol_exp, 2),
                "trend_score": round(trend_score, 2)
            }
            
        return sector_results


def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.clip(lower=0)).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))


def calc_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    # DM filters
    plus_dm.loc[plus_dm < minus_dm] = 0
    minus_dm.loc[minus_dm < plus_dm] = 0
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / (atr + 1e-9))
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / (atr + 1e-9))
    
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9))
    adx = dx.rolling(window=period).mean()
    return adx
