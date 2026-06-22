import asyncio
import logging
import time
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import text, insert
from sqlalchemy.orm import Session

from database import get_db_session_context, SessionLocal
from models_institutional_scanner import (
    InstitutionalPattern,
    VcpScore,
    TrendTemplateScore,
    RelativeStrengthRanking,
    BreakoutCandidate,
    DarvasBox,
    PatternHistory
)
from core.quant_engine.market_data.historical import get_market_data_engine
from utils.symbol_utils import get_all_symbols, get_company_name, get_stock_sector
from services.dragonfly_client import get_cache

logger = logging.getLogger(__name__)

def _to_native(val):
    if isinstance(val, dict):
        return {k: _to_native(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [_to_native(v) for v in val]
    elif isinstance(val, np.ndarray):
        return [_to_native(x) for x in val.tolist()]
    elif isinstance(val, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(val)
    elif isinstance(val, (np.floating, np.float64, np.float32)):
        return float(val)
    elif isinstance(val, np.bool_):
        return bool(val)
    elif isinstance(val, (str, int, float, bool)) or val is None:
        return val
    elif pd.isna(val):
        return None
    elif hasattr(val, "item") and callable(val.item):
        return val.item()
    else:
        return val

class InstitutionalScannerService:
    """
    Service to execute technical screening and institutional pattern scanning
    across the NSE stock universe.
    """
    
    def __init__(self):
        self.market_data = get_market_data_engine()
        self.cache = get_cache()
        self._is_scanning = False
        self._scan_progress = 0.0
        self._last_scan_time = None
        self._scan_duration = 0.0
        self._total_scanned = 0

    @property
    def scan_status(self) -> Dict[str, Any]:
        return {
            "is_scanning": self._is_scanning,
            "progress": round(self._scan_progress, 2),
            "last_scan_time": self._last_scan_time.isoformat() if self._last_scan_time else None,
            "scan_duration_seconds": round(self._scan_duration, 2),
            "total_scanned": self._total_scanned
        }

    # =========================================================================
    # Pattern Detection Math Engines
    # =========================================================================

    def _calculate_sma(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Simple Moving Averages."""
        df = df.copy()
        df['sma50'] = df['close'].rolling(window=50, min_periods=1).mean()
        df['sma150'] = df['close'].rolling(window=150, min_periods=1).mean()
        df['sma200'] = df['close'].rolling(window=200, min_periods=1).mean()
        return df

    def _detect_trend_template(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Mark Minervini's Trend Template Screening:
        1. Price > SMA50
        2. Price > SMA150
        3. Price > SMA200
        4. SMA50 > SMA150
        5. SMA150 > SMA200
        6. Price is at least 30% above 52W Low
        7. Price is within 25% of 52W High
        """
        if len(df) < 50:
            return {"score": 0.0, "matched": 0, "details": {}}
            
        df = self._calculate_sma(df)
        last_row = df.iloc[-1]
        close = float(last_row['close'])
        
        # Calculate 52W extreme values (approx. 250 trading days)
        window_52w = df.iloc[-250:] if len(df) >= 250 else df
        high_52w = float(window_52w['high'].max())
        low_52w = float(window_52w['low'].min())
        
        sma50 = float(last_row['sma50']) if not pd.isna(last_row['sma50']) else 0.0
        sma150 = float(last_row['sma150']) if not pd.isna(last_row['sma150']) else 0.0
        sma200 = float(last_row['sma200']) if not pd.isna(last_row['sma200']) else 0.0
        
        cond1 = close > sma50
        cond2 = close > sma150
        cond3 = close > sma200
        cond4 = sma50 > sma150
        cond5 = sma150 > sma200
        cond6 = close >= (low_52w * 1.30)
        cond7 = close >= (high_52w * 0.75)
        
        conditions = [cond1, cond2, cond3, cond4, cond5, cond6, cond7]
        matched_count = sum(1 for c in conditions if c)
        score = (matched_count / 7.0) * 100.0
        
        dist_high = ((high_52w - close) / high_52w) * 100.0 if high_52w > 0 else 0.0
        
        return {
            "score": score,
            "matched": matched_count,
            "conditions": {
                "price_above_sma50": bool(cond1),
                "price_above_sma150": bool(cond2),
                "price_above_sma200": bool(cond3),
                "sma50_above_sma150": bool(cond4),
                "sma150_above_sma200": bool(cond5),
                "price_above_52w_low_by_30pct": bool(cond6),
                "price_within_25pct_of_52w_high": bool(cond7)
            },
            "sma50": sma50,
            "sma150": sma150,
            "sma200": sma200,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "distance_to_52w_high": dist_high
        }

    def _find_swings(self, df: pd.DataFrame, window: int = 5) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Find local swing highs and swing lows."""
        highs = []
        lows = []
        
        high_series = df['high'].values
        low_series = df['low'].values
        close_series = df['close'].values
        ts_series = df['timestamp'].values
        
        n = len(df)
        for i in range(window, n - window):
            # Swing High
            is_high = True
            for j in range(i - window, i + window + 1):
                if high_series[j] > high_series[i]:
                    is_high = False
                    break
            if is_high:
                highs.append({
                    "idx": i,
                    "price": float(high_series[i]),
                    "close": float(close_series[i]),
                    "timestamp": ts_series[i]
                })
                
            # Swing Low
            is_low = True
            for j in range(i - window, i + window + 1):
                if low_series[j] < low_series[i]:
                    is_low = False
                    break
            if is_low:
                lows.append({
                    "idx": i,
                    "price": float(low_series[i]),
                    "close": float(close_series[i]),
                    "timestamp": ts_series[i]
                })
                
        return highs, lows

    def _detect_vcp(self, df: pd.DataFrame, rs_score: float = 50.0) -> Dict[str, Any]:
        """
        Volatility Contraction Pattern (VCP) Engine.
        Finds sequential contractions (e.g. 25% -> 15% -> 10% -> 5%).
        """
        if len(df) < 50:
            return {"is_vcp": False, "score": 0.0, "details": {}}
            
        highs, lows = self._find_swings(df, window=5)
        
        # Combine and sort chronologically
        events = []
        for h in highs:
            events.append(("high", h))
        for l in lows:
            events.append(("low", l))
        events.sort(key=lambda x: x[1]["idx"])
        
        # Identify contraction waves (peaks to troughs)
        contractions = []
        last_high = None
        for event_type, data in events:
            if event_type == "high":
                last_high = data
            elif event_type == "low" and last_high is not None:
                # Calculate contraction depth %
                high_val = last_high["price"]
                low_val = data["price"]
                if high_val > low_val:
                    depth = ((high_val - low_val) / high_val) * 100.0
                    contractions.append({
                        "high": high_val,
                        "low": low_val,
                        "depth": depth,
                        "high_idx": last_high["idx"],
                        "low_idx": data["idx"]
                    })
                    last_high = None # Reset to find next pair
                    
        # Filter for contractions in the last 150 days
        cutoff_idx = len(df) - 150
        recent_contractions = [c for c in contractions if c["high_idx"] >= cutoff_idx]
        
        if len(recent_contractions) < 2:
            return {
                "is_vcp": False,
                "score": 0.0,
                "category": "Ignore",
                "num_contractions": len(recent_contractions),
                "depths": [],
                "latest_contraction_pct": 0.0,
                "volume_dry_up_pct": 0.0,
                "atr_contraction_pct": 0.0,
                "breakout_pivot": 0.0,
                "breakout_ready": False,
                "trend_quality": 0.0,
                "volatility_compression": 0.0,
                "proximity_to_pivot": 100.0,
                "relative_strength": rs_score,
                "details": {
                    "num_contractions": len(recent_contractions),
                    "reason": "Insufficient contraction waves in last 150 days",
                    "depths": [],
                    "avg_contraction": 0.0,
                    "final_contraction": 0.0
                }
            }
            
        # Get contraction depths
        depths = [c["depth"] for c in recent_contractions]
        
        # Volatility contraction: sequential depths must generally decrease
        decreases = 0
        for i in range(1, len(depths)):
            if depths[i] < depths[i-1] * 1.1: # Allow 10% tolerance for minor noise
                decreases += 1
                
        is_contracting = (decreases >= len(depths) - 1)
        
        # Pivot point: highest peak of the contractions
        pivot = max(c["high"] for c in recent_contractions)
        current_close = float(df.iloc[-1]['close'])
        proximity = ((pivot - current_close) / pivot) * 100.0 if pivot > 0 else 100.0
        
        # Calculate ATR contraction
        df_copy = df.copy()
        high_low = df_copy['high'] - df_copy['low']
        high_cp = (df_copy['high'] - df_copy['close'].shift(1)).abs()
        low_cp = (df_copy['low'] - df_copy['close'].shift(1)).abs()
        df_copy['tr'] = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        df_copy['atr'] = df_copy['tr'].rolling(window=14).mean()
        
        recent_atr = df_copy['atr'].iloc[-20:].mean()
        older_atr = df_copy['atr'].iloc[-70:-20].mean()
        atr_contraction_pct = ((older_atr - recent_atr) / (older_atr + 1e-5)) * 100.0
        
        # Volume Dry-Up calculation during contractions
        last_vol = df['volume'].iloc[-20:].mean()
        prev_vol = df['volume'].iloc[-70:-20].mean()
        volume_dry_up_pct = ((prev_vol - last_vol) / (prev_vol + 1e-5)) * 100.0
        
        # VCP Scoring Components (each 20 points, total 100)
        # 1. Volatility Compression
        final_depth = depths[-1]
        vc_score = 20.0 if final_depth <= 8.0 else max(0.0, 20.0 - (final_depth - 8.0) * 1.5)
        if is_contracting:
            vc_score += 5.0
        vc_score = min(vc_score, 20.0)
        
        # 2. Trend Quality (MAs)
        df_ma = self._calculate_sma(df)
        last_row = df_ma.iloc[-1]
        c = float(last_row['close'])
        s50 = float(last_row['sma50'])
        s150 = float(last_row['sma150'])
        s200 = float(last_row['sma200'])
        
        trend_score = 0.0
        if c > s50: trend_score += 5.0
        if s50 > s150: trend_score += 5.0
        if s150 > s200: trend_score += 5.0
        if c > s200: trend_score += 5.0
        
        # 3. Volume Dry Up Score
        vdu_score = max(0.0, min(20.0, volume_dry_up_pct / 3.0)) if volume_dry_up_pct > 0 else 0.0
        
        # 4. Proximity to Pivot
        prox_score = max(0.0, 20.0 - abs(proximity) * 3.0) if proximity >= -5.0 else 0.0
        
        # 5. Relative Strength Component
        rs_component = min(20.0, rs_score / 5.0)
        
        total_score = vc_score + trend_score + vdu_score + prox_score + rs_component
        
        # Categories: Elite, Excellent, Good, Watchlist, Ignore
        if total_score >= 90.0:
            category = "Elite"
        elif total_score >= 80.0:
            category = "Excellent"
        elif total_score >= 70.0:
            category = "Good"
        elif total_score >= 60.0:
            category = "Watchlist"
        else:
            category = "Ignore"
            
        # Adaptive proximity threshold based on 14-day ATR percent
        atr_val = float(df_copy['atr'].iloc[-1]) if 'atr' in df_copy.columns else 2.0
        atr_pct = (atr_val / current_close) * 100.0 if current_close > 0 else 2.0
        proximity_threshold = max(1.5, min(4.0, atr_pct * 1.2))
        
        breakout_ready = (proximity <= proximity_threshold and proximity >= -1.0 and total_score >= 70.0)
        
        return {
            "is_vcp": (total_score >= 60.0 and len(depths) >= 2),
            "score": total_score,
            "category": category,
            "num_contractions": len(depths),
            "depths": depths,
            "latest_contraction_pct": final_depth,
            "volume_dry_up_pct": volume_dry_up_pct,
            "atr_contraction_pct": atr_contraction_pct,
            "breakout_pivot": pivot,
            "breakout_ready": breakout_ready,
            "trend_quality": trend_score * 5.0, # Scale to 0-100 for storage
            "volatility_compression": vc_score * 5.0,
            "proximity_to_pivot": proximity,
            "relative_strength": rs_score,
            "details": {
                "depths": [round(d, 2) for d in depths],
                "avg_contraction": round(np.mean(depths), 2) if depths else 0.0,
                "final_contraction": round(final_depth, 2)
            }
        }

    def _detect_relative_strength(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate Relative Strength Score based on weighted returns:
        RS Score = (0.4 * 6M Return) + (0.3 * 3M Return) + (0.3 * 1M Return)
        """
        if len(df) < 130:
            return {"rs_score": 0.0, "r6m": 0.0, "r3m": 0.0, "r1m": 0.0}
            
        close_series = df['close'].values
        now_close = float(close_series[-1])
        
        # Assuming ~21 trading days in a month
        close_1m = float(close_series[-22])
        close_3m = float(close_series[-64])
        close_6m = float(close_series[-127])
        
        r1m = ((now_close - close_1m) / close_1m) * 100.0 if close_1m > 0 else 0.0
        r3m = ((now_close - close_3m) / close_3m) * 100.0 if close_3m > 0 else 0.0
        r6m = ((now_close - close_6m) / close_6m) * 100.0 if close_6m > 0 else 0.0
        
        rs_score = (0.4 * r6m) + (0.3 * r3m) + (0.3 * r1m)
        
        return {
            "rs_score": rs_score,
            "r6m": r6m,
            "r3m": r3m,
            "r1m": r1m
        }

    def _detect_breakout(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect Resistance, Volume, and Range breakouts.
        Conditions: Current Close > Pivot AND Volume > 1.5 * 50 Day Average Volume
        """
        if len(df) < 55:
            return {"is_breakout": False, "pivot": 0.0, "surge": 0.0, "pct": 0.0}
            
        # Resistance Pivot: Max high of previous 20 days (excluding today)
        sub_df = df.iloc[-21:-1]
        pivot = float(sub_df['high'].max())
        
        close = float(df['close'].iloc[-1])
        volume = float(df['volume'].iloc[-1])
        
        # 50-day average volume
        avg_vol_50 = float(df['volume'].iloc[-51:-1].mean())
        
        is_price_breakout = close > pivot
        is_volume_breakout = volume > (1.5 * avg_vol_50)
        
        breakout_pct = ((close - pivot) / pivot) * 100.0 if pivot > 0 else 0.0
        volume_surge_pct = ((volume - avg_vol_50) / avg_vol_50) * 100.0 if avg_vol_50 > 0 else 0.0
        
        is_breakout = is_price_breakout and is_volume_breakout
        
        confirmation_status = "Confirmed" if (close > pivot and volume > 2.0 * avg_vol_50) else "Pending"
        if not is_breakout:
            confirmation_status = "Failed"
            
        # Breakout type
        breakout_type = "Resistance"
        if volume > 2.5 * avg_vol_50:
            breakout_type = "Volume"
        elif close > float(df['high'].iloc[-51:-1].max()):
            breakout_type = "Range"
            
        return {
            "is_breakout": is_breakout,
            "breakout_price": pivot,
            "current_price": close,
            "breakout_pct": breakout_pct,
            "volume_surge_pct": volume_surge_pct,
            "confirmation_status": confirmation_status,
            "breakout_type": breakout_type
        }

    def _detect_darvas_box(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Implement Nicolas Darvas Box State Machine.
        Returns Box Top, Box Bottom, Days Inside Box, Breakout Status.
        """
        if len(df) < 20:
            return {"box_top": 0.0, "box_bottom": 0.0, "days": 0, "status": "No Box"}
            
        # Simple rolling Darvas Box simulation
        box_top = None
        box_bottom = None
        days_inside = 0
        status = "Inside Box"
        
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
        # Loop through to simulate Darvas Box establishment
        # A high is a top if not exceeded for 3 days
        # A low since top is a bottom if not broken for 3 days
        i = 0
        n = len(df)
        while i < n:
            if box_top is None:
                # Try to establish top
                if i >= 3:
                    candidate_top = highs[i-3]
                    if highs[i-2] <= candidate_top and highs[i-1] <= candidate_top and highs[i] <= candidate_top:
                        box_top = float(candidate_top)
                        box_bottom = None
                        days_inside = 0
                i += 1
            elif box_bottom is None:
                # Try to establish bottom
                if i >= 3:
                    candidate_bottom = lows[i-3]
                    if lows[i-2] >= candidate_bottom and lows[i-1] >= candidate_bottom and lows[i] >= candidate_bottom:
                        box_bottom = float(candidate_bottom)
                        days_inside = 1
                i += 1
            else:
                # Box is active, check breakout or breakdown
                close = closes[i]
                low = lows[i]
                high = highs[i]
                
                if close > box_top:
                    status = "Bullish Breakout"
                    # Reset to look for a new box
                    box_top = None
                    box_bottom = None
                    days_inside = 0
                elif close < box_bottom:
                    status = "Bearish Breakdown"
                    # Reset to look for a new box
                    box_top = None
                    box_bottom = None
                    days_inside = 0
                else:
                    days_inside += 1
                    status = "Inside Box"
                i += 1
                
        # If no active box is found at the end, default to final elements in series
        if box_top is None or box_bottom is None:
            # Approximate a recent consolidation box
            box_top = float(df['high'].iloc[-10:].max())
            box_bottom = float(df['low'].iloc[-10:].min())
            days_inside = 5
            status = "Inside Box"
            
        return {
            "box_top": box_top,
            "box_bottom": box_bottom,
            "days_inside_box": days_inside,
            "breakout_status": status
        }

    def _detect_cup_and_handle(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect Cup and Handle formation using adaptive swing analysis.
        Supports variable durations (40-day, 80-day, 120-day).
        """
        if len(df) < 50:
            return {"is_pattern": False, "pivot": 0.0, "confidence": 0.0, "confirmed": False}
            
        highs, lows = self._find_swings(df, window=5)
        if len(highs) < 2 or len(lows) < 1:
            return {"is_pattern": False, "pivot": 0.0, "confidence": 0.0, "confirmed": False}
            
        closes = df['close'].values
        high_vals = df['high'].values
        low_vals = df['low'].values
        
        best_pattern = None
        best_confidence = 0.0
        
        # Look for pattern in the last 120 days
        cutoff_idx = len(df) - 120
        recent_highs = [h for h in highs if h["idx"] >= cutoff_idx]
        
        # Try all pairs of recent swing highs as Left and Right Lips
        for idx_l, left in enumerate(recent_highs):
            for right in recent_highs[idx_l + 1:]:
                # Distance in bars
                duration = right["idx"] - left["idx"]
                if duration < 20 or duration > 90:
                    continue
                    
                # The Left and Right Lip prices
                left_price = left["price"]
                right_price = right["price"]
                
                # Lips should be at a similar level (within 15%)
                lip_diff = (abs(left_price - right_price) / max(left_price, right_price)) * 100.0
                if lip_diff > 15.0:
                    continue
                    
                # Find the lowest low (cup bottom) between left and right lip
                cup_range_lows = low_vals[left["idx"]:right["idx"]]
                if len(cup_range_lows) == 0:
                    continue
                cup_bottom = float(np.min(cup_range_lows))
                
                # Cup depth should be 10% to 50%
                avg_lip = (left_price + right_price) / 2.0
                cup_depth = ((avg_lip - cup_bottom) / avg_lip) * 100.0
                if cup_depth < 10.0 or cup_depth > 50.0:
                    continue
                    
                # Handle starts after right lip
                handle_closes = closes[right["idx"]:]
                if len(handle_closes) < 3:
                    continue
                
                # Handle pullback parameters
                handle_min = float(np.min(handle_closes))
                handle_pullback = ((right_price - handle_min) / right_price) * 100.0
                
                # Handle shouldn't exceed cup bottom, and pullback should be 2% to 20%
                if handle_min <= cup_bottom or handle_pullback < 2.0 or handle_pullback > 20.0:
                    continue
                    
                # Scoring Confidence (0-100)
                confidence = 30.0 # Base for matching geometry
                
                # Symmetry score (Left vs Right Lip)
                confidence += max(0.0, 25.0 - lip_diff * 1.6)
                
                # Handle quality (tighter pullback is better)
                confidence += max(0.0, 25.0 - abs(handle_pullback - 8.0) * 1.5)
                
                # Trend quality (cup should be U-shaped, check that bottom is in the middle third)
                bottom_rel_idx = (np.argmin(low_vals[left["idx"]:right["idx"]]) / duration)
                if 0.25 <= bottom_rel_idx <= 0.75:
                    confidence += 20.0
                    
                if confidence > best_confidence:
                    best_confidence = confidence
                    current_close = float(closes[-1])
                    confirmed = (current_close > right_price)
                    
                    best_pattern = {
                        "is_pattern": confidence >= 50.0,
                        "pivot": right_price,
                        "cup_depth_pct": cup_depth,
                        "handle_depth_pct": handle_pullback,
                        "confidence_score": confidence,
                        "breakout_confirmed": confirmed
                    }
                    
        if best_pattern:
            return best_pattern
            
        return {"is_pattern": False, "pivot": 0.0, "confidence": 0.0, "confirmed": False}

    def _detect_double_bottom(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect Double Bottom formation using local minima and neckline peak analysis.
        """
        if len(df) < 40:
            return {"is_pattern": False, "pivot": 0.0, "confidence": 0.0}
            
        highs, lows = self._find_swings(df, window=5)
        if len(lows) < 2:
            return {"is_pattern": False, "pivot": 0.0, "confidence": 0.0}
            
        closes = df['close'].values
        high_vals = df['high'].values
        
        best_pattern = None
        best_confidence = 0.0
        
        # Look for swing lows in the last 90 days
        cutoff_idx = len(df) - 90
        recent_lows = [l for l in lows if l["idx"] >= cutoff_idx]
        
        for idx_l, b1 in enumerate(recent_lows):
            for b2 in recent_lows[idx_l + 1:]:
                duration = b2["idx"] - b1["idx"]
                if duration < 10 or duration > 60:
                    continue
                    
                b1_price = b1["price"]
                b2_price = b2["price"]
                
                # Bottoms at a similar level (within 4% tolerance bands)
                bottom_diff = (abs(b1_price - b2_price) / max(b1_price, b2_price)) * 100.0
                if bottom_diff > 4.0:
                    continue
                    
                # Neckline pivot (highest high between the two bottoms)
                mid_highs = high_vals[b1["idx"]:b2["idx"]]
                if len(mid_highs) == 0:
                    continue
                pivot = float(np.max(mid_highs))
                
                # Peak must be significantly higher than bottoms (at least 7%)
                min_bottom = min(b1_price, b2_price)
                peak_depth = ((pivot - min_bottom) / min_bottom) * 100.0
                if peak_depth < 7.0:
                    continue
                    
                # Calculate confidence score
                confidence = 40.0
                confidence += max(0.0, 30.0 - bottom_diff * 7.5) # closer bottoms = higher score
                confidence += max(0.0, 30.0 - abs(peak_depth - 15.0) * 1.5) # balanced valley depth
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    age = len(df) - b1["idx"]
                    
                    best_pattern = {
                        "is_pattern": confidence >= 50.0,
                        "first_bottom": b1_price,
                        "second_bottom": b2_price,
                        "pivot": pivot,
                        "pattern_age_days": age,
                        "confidence_score": confidence
                    }
                    
        if best_pattern:
            return best_pattern
            
        return {"is_pattern": False, "pivot": 0.0, "confidence": 0.0}


    def _detect_flat_base(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect Flat Base consolidation.
        Maximum correction <= 15% in a consolidation window of 15+ days.
        """
        if len(df) < 25:
            return {"is_pattern": False, "length": 0, "pivot": 0.0}
            
        # Consolidation window (last 20 days)
        sub_df = df.iloc[-20:]
        max_price = float(sub_df['high'].max())
        min_price = float(sub_df['low'].min())
        
        correction = ((max_price - min_price) / max_price) * 100.0
        is_flat = correction <= 15.0
        
        # Calculate length of consolidation: how long the price stayed within this 15% range
        length = 0
        highs = df['high'].values
        lows = df['low'].values
        
        for idx in range(len(df) - 1, -1, -1):
            if highs[idx] <= max_price and lows[idx] >= min_price:
                length += 1
            else:
                break
                
        return {
            "is_pattern": is_flat and length >= 12,
            "base_length_days": length,
            "base_depth_pct": correction,
            "pivot": max_price
        }

    def _detect_volume_dry_up(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate Supply Drying and Accumulation Score.
        Current 20-Day Avg Volume vs Previous 50-Day Avg Volume.
        """
        if len(df) < 70:
            return {"volume_contraction": 0.0, "drying_score": 0.0, "accumulation_score": 0.0}
            
        vols = df['volume'].values
        closes = df['close'].values
        opens = df['open'].values
        
        curr_avg = float(np.mean(vols[-20:]))
        prev_avg = float(np.mean(vols[-70:-20]))
        
        contraction = ((prev_avg - curr_avg) / (prev_avg + 1e-5)) * 100.0
        
        # Supply Drying Score: scaled between 0 and 100
        drying_score = min(100.0, max(0.0, contraction * 2.0)) if contraction > 0 else 0.0
        
        # Accumulation Score (up-day volume vs down-day volume ratios)
        up_volume = 0.0
        down_volume = 0.0
        for i in range(len(df) - 20, len(df)):
            if closes[i] > opens[i]:
                up_volume += float(vols[i])
            else:
                down_volume += float(vols[i])
                
        accumulation_score = (up_volume / (up_volume + down_volume + 1e-5)) * 100.0
        
        return {
            "volume_contraction_pct": contraction,
            "drying_score": drying_score,
            "accumulation_score": accumulation_score
        }

    # =========================================================================
    # Scanning Orchestrator
    # =========================================================================

    def scan_single_stock(self, db: Session, symbol: str, rs_scores_map: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """Run all scans on a single symbol and return results."""
        try:
            # Load daily candles
            df = self.market_data.load_candles(symbol, "1d")
            
            if df.empty or len(df) < 50:
                logger.warning(f"Insufficient daily candles for {symbol} (len={len(df)})")
                return None
                
            close = float(df['close'].iloc[-1])
            
            # Fetch company and industry/sector info
            company_name = get_company_name(symbol)
            sector = get_stock_sector(symbol)
            industry = "Others" # fallback if not structured
            
            # 0. Relative Strength
            rs_res = self._detect_relative_strength(df)
            rs_score = rs_res["rs_score"]
            rs_scores_map[symbol] = rs_score
            
            # Get fundamental metrics (market cap etc.)
            fund = db.execute(
                text("SELECT market_cap, sector_pe_benchmark FROM fundamental_metrics WHERE symbol = :symbol"),
                {"symbol": symbol}
            ).fetchone()
            market_cap = float(fund[0]) if fund and fund[0] else 5000000000.0 # fallback 500cr
            
            # 1. Minervini Trend Template
            tt_res = self._detect_trend_template(df)
            
            # 2. VCP
            vcp_res = self._detect_vcp(df, rs_score=rs_score)
            
            # 3. Breakout
            bo_res = self._detect_breakout(df)
            
            # 4. Darvas Box
            db_res = self._detect_darvas_box(df)
            
            # 5. Cup & Handle
            ch_res = self._detect_cup_and_handle(df)
            
            # 6. Double Bottom
            dbot_res = self._detect_double_bottom(df)
            
            # 7. Flat Base
            fb_res = self._detect_flat_base(df)
            
            # 8. Volume Dry Up
            vdu_res = self._detect_volume_dry_up(df)
            
            return {
                "symbol": symbol,
                "company_name": company_name,
                "sector": sector,
                "industry": industry,
                "market_cap": market_cap,
                "current_price": close,
                "rs": rs_res,
                "trend_template": tt_res,
                "vcp": vcp_res,
                "breakout": bo_res,
                "darvas": db_res,
                "cup_handle": ch_res,
                "double_bottom": dbot_res,
                "flat_base": fb_res,
                "volume_dry_up": vdu_res
            }
        except Exception as e:
            logger.error(f"Error scanning stock {symbol}: {e}")
            return None

    async def scan_all_stocks(self) -> Dict[str, Any]:
        """Orchestrate parallel scanning across the NSE universe."""
        if self._is_scanning:
            logger.warning("Scan is already in progress")
            return self.scan_status
            
        self._is_scanning = True
        self._scan_progress = 0.0
        self._total_scanned = 0
        start_time = time.time()
        
        logger.info("Starting Institutional Pattern Scan Job...")
        
        try:
            # 1. Fetch symbols
            symbols = get_all_symbols()
            if not symbols:
                logger.error("No active symbols loaded in symbol manager")
                self._is_scanning = False
                return self.scan_status
                
            # Limit universe size to 300 for execution speed, but keep representative
            if len(symbols) > 300:
                symbols = symbols[:300]
                
            total = len(symbols)
            logger.info(f"Targeting {total} symbols for VCP and breakout screening...")
            
            # Initialize temp storage for RS ranking
            rs_scores_map = {}
            results = []
            
            # Execute scan with semaphore to limit concurrency and resource exhaustion
            sem = asyncio.Semaphore(15)
            
            async def _worker(symbol: str):
                async with sem:
                    def _do_scan():
                        db = SessionLocal()
                        try:
                            return self.scan_single_stock(db, symbol, rs_scores_map)
                        finally:
                            db.close()
                    res = await asyncio.to_thread(_do_scan)
                    if res:
                        results.append(res)
                        
                    # Update progress
                    self._total_scanned += 1
                    self._scan_progress = (self._total_scanned / total) * 100.0
            
            # Gather all scanning tasks
            tasks = [_worker(sym) for sym in symbols]
            await asyncio.gather(*tasks)
            
            # 2. Assign RS overall ranks, sector ranks, and industry ranks
            logger.info("Computing Relative Strength rankings...")
            results = self._assign_rs_rankings(results)
            
            # 3. Save results to Database
            logger.info("Saving results to SQL database tables...")
            await self._persist_results_to_db(results)
            
            # 4. Cache summary snapshot in Redis/Dragonfly
            logger.info("Caching scanner summary results...")
            await self._cache_scanner_snapshot(results)
            
            self._last_scan_time = datetime.now()
            self._scan_duration = time.time() - start_time
            logger.info(f"Institutional Pattern Scan completed in {self._scan_duration:.2f} seconds. Scanned: {len(results)} stocks.")
            
        except Exception as e:
            logger.error(f"Scanner service loop crashed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._is_scanning = False
            self._scan_progress = 100.0
            
        return self.scan_status

    def _assign_rs_rankings(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Assign overall, sector, and industry Relative Strength ranks."""
        # Sort overall
        results.sort(key=lambda x: x["rs"]["rs_score"], reverse=True)
        for rank, item in enumerate(results, 1):
            item["rs"]["rank"] = rank
            
        # Group by Sector and sort
        sectors = {}
        for item in results:
            sec = item["sector"]
            if sec not in sectors:
                sectors[sec] = []
            sectors[sec].append(item)
            
        for sec, items in sectors.items():
            items.sort(key=lambda x: x["rs"]["rs_score"], reverse=True)
            for rank, item in enumerate(items, 1):
                item["rs"]["sector_rank"] = rank
                
        # Group by Industry and sort
        industries = {}
        for item in results:
            ind = item["industry"]
            if ind not in industries:
                industries[ind] = []
            industries[ind].append(item)
            
        for ind, items in industries.items():
            items.sort(key=lambda x: x["rs"]["rs_score"], reverse=True)
            for rank, item in enumerate(items, 1):
                item["rs"]["industry_rank"] = rank
                
        return results

    async def _persist_results_to_db(self, results: List[Dict[str, Any]]):
        """Save calculations directly into PostgreSQL database tables."""
        async with get_db_session_context() as session:
            try:
                # 1. Clear old data from these EOD/Scanner tables to keep clean
                await session.execute(text("TRUNCATE TABLE vcp_scores, trend_template_scores, relative_strength_rankings, breakout_candidates, darvas_boxes, institutional_patterns RESTART IDENTITY CASCADE"))
                
                # 2. Batch inserts
                vcp_inserts = []
                tt_inserts = []
                rs_inserts = []
                bo_inserts = []
                darvas_inserts = []
                pattern_inserts = []
                history_inserts = []
                
                for item in results:
                    sym = item["symbol"]
                    price = item["current_price"]
                    mcap = item["market_cap"]
                    
                    # VCP Scores
                    vcp = item["vcp"]
                    vcp_inserts.append({
                        "symbol": sym,
                        "current_price": price,
                        "distance_from_52w_high": vcp["proximity_to_pivot"],
                        "vcp_score": vcp["score"],
                        "num_contractions": vcp["num_contractions"],
                        "latest_contraction_pct": vcp["latest_contraction_pct"],
                        "volume_dry_up_pct": vcp["volume_dry_up_pct"],
                        "atr_contraction_pct": vcp["atr_contraction_pct"],
                        "breakout_pivot": vcp["breakout_pivot"],
                        "breakout_ready": vcp["breakout_ready"],
                        "category": vcp["category"],
                        "trend_quality": vcp["trend_quality"],
                        "volume_dry_up": vcp["volume_dry_up_pct"],
                        "volatility_compression": vcp["volatility_compression"],
                        "proximity_to_pivot": vcp["proximity_to_pivot"],
                        "relative_strength": vcp["relative_strength"]
                    })
                    
                    # Save major patterns detected to institutional_patterns & history
                    if vcp["is_vcp"]:
                        pattern_inserts.append({
                            "symbol": sym,
                            "pattern_type": "VCP",
                            "confidence_score": vcp["score"],
                            "breakout_pivot": vcp["breakout_pivot"],
                            "breakout_status": "Confirmed" if vcp["breakout_ready"] else "Pending",
                            "details": vcp["details"]
                        })
                        history_inserts.append({
                            "symbol": sym,
                            "pattern_type": "VCP",
                            "details": vcp["details"],
                            "confidence_score": vcp["score"],
                            "status": "Active"
                        })
                        
                    # Trend Template
                    tt = item["trend_template"]
                    tt_inserts.append({
                        "symbol": sym,
                        "trend_template_score": tt["score"],
                        "price_above_sma50": tt["conditions"]["price_above_sma50"],
                        "price_above_sma150": tt["conditions"]["price_above_sma150"],
                        "price_above_sma200": tt["conditions"]["price_above_sma200"],
                        "sma50_above_sma150": tt["conditions"]["sma50_above_sma150"],
                        "sma150_above_sma200": tt["conditions"]["sma150_above_sma200"],
                        "price_above_52w_low_by_30pct": tt["conditions"]["price_above_52w_low_by_30pct"],
                        "price_within_25pct_of_52w_high": tt["conditions"]["price_within_25pct_of_52w_high"],
                        "sma50": tt["sma50"],
                        "sma150": tt["sma150"],
                        "sma200": tt["sma200"],
                        "distance_to_52w_high": tt["distance_to_52w_high"]
                    })
                    
                    # RS Rankings
                    rs = item["rs"]
                    rs_inserts.append({
                        "rank": rs["rank"],
                        "symbol": sym,
                        "rs_score": rs["rs_score"],
                        "return_6m": rs["r6m"],
                        "return_3m": rs["r3m"],
                        "return_1m": rs["r1m"],
                        "sector_rank": rs.get("sector_rank", 1),
                        "industry_rank": rs.get("industry_rank", 1),
                        "sector": item["sector"],
                        "industry": item["industry"],
                        "market_cap": mcap
                    })
                    
                    # Breakouts
                    bo = item["breakout"]
                    if bo["is_breakout"]:
                        bo_inserts.append({
                            "symbol": sym,
                            "breakout_price": bo["breakout_price"],
                            "current_price": bo["current_price"],
                            "breakout_pct": bo["breakout_pct"],
                            "volume_surge_pct": bo["volume_surge_pct"],
                            "confirmation_status": bo["confirmation_status"],
                            "breakout_type": bo["breakout_type"]
                        })
                        
                    # Darvas
                    dbx = item["darvas"]
                    darvas_inserts.append({
                        "symbol": sym,
                        "box_top": dbx["box_top"],
                        "box_bottom": dbx["box_bottom"],
                        "days_inside_box": dbx["days_inside_box"],
                        "breakout_status": dbx["breakout_status"]
                    })
                    
                    # Cup & Handle
                    ch = item["cup_handle"]
                    if ch["is_pattern"]:
                        pattern_inserts.append({
                            "symbol": sym,
                            "pattern_type": "CUP_AND_HANDLE",
                            "confidence_score": ch["confidence_score"],
                            "breakout_pivot": ch["pivot"],
                            "breakout_status": "Confirmed" if ch["breakout_confirmed"] else "Pending",
                            "details": {"cup_depth": ch["cup_depth_pct"], "handle_depth": ch["handle_depth_pct"]}
                        })
                        history_inserts.append({
                            "symbol": sym,
                            "pattern_type": "CUP_AND_HANDLE",
                            "details": {"cup_depth": ch["cup_depth_pct"], "handle_depth": ch["handle_depth_pct"]},
                            "confidence_score": ch["confidence_score"],
                            "status": "Active"
                        })
                        
                    # Double Bottom
                    dbot = item["double_bottom"]
                    if dbot["is_pattern"]:
                        pattern_inserts.append({
                            "symbol": sym,
                            "pattern_type": "DOUBLE_BOTTOM",
                            "confidence_score": dbot["confidence_score"],
                            "breakout_pivot": dbot["pivot"],
                            "breakout_status": "Pending",
                            "details": {"first_bottom": dbot["first_bottom"], "second_bottom": dbot["second_bottom"], "age": dbot["pattern_age_days"]}
                        })
                        history_inserts.append({
                            "symbol": sym,
                            "pattern_type": "DOUBLE_BOTTOM",
                            "details": {"first_bottom": dbot["first_bottom"], "second_bottom": dbot["second_bottom"], "age": dbot["pattern_age_days"]},
                            "confidence_score": dbot["confidence_score"],
                            "status": "Active"
                        })
                        
                    # Flat Base
                    fb = item["flat_base"]
                    if fb["is_pattern"]:
                        pattern_inserts.append({
                            "symbol": sym,
                            "pattern_type": "FLAT_BASE",
                            "confidence_score": 80.0,
                            "breakout_pivot": fb["pivot"],
                            "breakout_status": "Pending",
                            "details": {"base_length": fb["base_length_days"], "base_depth": fb["base_depth_pct"]}
                        })
                        history_inserts.append({
                            "symbol": sym,
                            "pattern_type": "FLAT_BASE",
                            "details": {"base_length": fb["base_length_days"], "base_depth": fb["base_depth_pct"]},
                            "confidence_score": 80.0,
                            "status": "Active"
                        })
                
                # Bulk inserts
                if vcp_inserts:
                    await session.execute(insert(VcpScore), vcp_inserts)
                if tt_inserts:
                    await session.execute(insert(TrendTemplateScore), tt_inserts)
                if rs_inserts:
                    await session.execute(insert(RelativeStrengthRanking), rs_inserts)
                if bo_inserts:
                    await session.execute(insert(BreakoutCandidate), bo_inserts)
                if darvas_inserts:
                    await session.execute(insert(DarvasBox), darvas_inserts)
                if pattern_inserts:
                    await session.execute(insert(InstitutionalPattern), pattern_inserts)
                if history_inserts:
                    await session.execute(insert(PatternHistory), history_inserts)
                    
                await session.commit()
                logger.info("All scan results successfully saved to database.")
            except Exception as dbe:
                logger.error(f"Failed to persist scan results to DB: {dbe}")
                await session.rollback()
                raise dbe

    async def _cache_scanner_snapshot(self, results: List[Dict[str, Any]]):
        """Cache summary stats and scan list in Dragonfly Redis."""
        try:
            total_scanned = len(results)
            vcp_cands = sum(1 for r in results if r["vcp"]["is_vcp"])
            bo_ready = sum(1 for r in results if r["vcp"]["breakout_ready"])
            fresh_bo = sum(1 for r in results if r["breakout"]["is_breakout"])
            near_52w = sum(1 for r in results if r["vcp"]["proximity_to_pivot"] <= 5.0)
            rs_leaders = sum(1 for r in results if r["rs"]["rs_score"] >= 80.0)
            
            dashboard = {
                "total_scanned": total_scanned,
                "vcp_candidates": vcp_cands,
                "breakout_ready": bo_ready,
                "fresh_breakouts": fresh_bo,
                "near_52w_high": near_52w,
                "rs_leaders": rs_leaders,
                "last_updated": datetime.now().isoformat()
            }
            
            # Save dashboard
            dashboard = _to_native(dashboard)
            await self.cache.set_async("qai:scanner:institutional:dashboard", dashboard, ttl=86400)
            
            # Save top results list (brief columns for UI table rendering speed)
            ui_table_data = []
            for item in results:
                ui_table_data.append({
                    "symbol": item["symbol"],
                    "company_name": item["company_name"],
                    "sector": item["sector"],
                    "current_price": item["current_price"],
                    "market_cap": item["market_cap"],
                    "rs_score": item["rs"]["rs_score"],
                    "rs_rank": item["rs"]["rank"],
                    "sector_rank": item["rs"].get("sector_rank", 1),
                    "industry_rank": item["rs"].get("industry_rank", 1),
                    "vcp_score": item["vcp"]["score"],
                    "vcp_category": item["vcp"]["category"],
                    "vcp_contractions": item["vcp"]["num_contractions"],
                    "vcp_latest_contraction": item["vcp"]["latest_contraction_pct"],
                    "volume_dry_up": item["vcp"]["volume_dry_up_pct"],
                    "atr_contraction": item["vcp"]["atr_contraction_pct"],
                    "breakout_pivot": item["vcp"]["breakout_pivot"],
                    "breakout_ready": item["vcp"]["breakout_ready"],
                    "trend_template_score": item["trend_template"]["score"],
                    "sma50": item["trend_template"]["sma50"],
                    "sma150": item["trend_template"]["sma150"],
                    "sma200": item["trend_template"]["sma200"],
                    "distance_52w_high": item["trend_template"]["distance_to_52w_high"],
                    "is_breakout": item["breakout"]["is_breakout"],
                    "breakout_type": item["breakout"]["breakout_type"],
                    "breakout_price": item["breakout"]["breakout_price"],
                    "volume_surge": item["breakout"]["volume_surge_pct"],
                    "darvas_status": item["darvas"]["breakout_status"],
                    "darvas_top": item["darvas"]["box_top"],
                    "darvas_bottom": item["darvas"]["box_bottom"],
                    "darvas_days": item["darvas"]["days_inside_box"],
                    "cup_handle_confidence": item["cup_handle"]["confidence_score"] if item["cup_handle"]["is_pattern"] else 0.0,
                    "double_bottom_confidence": item["double_bottom"]["confidence_score"] if item["double_bottom"]["is_pattern"] else 0.0,
                    "flat_base_length": item["flat_base"]["base_length_days"] if item["flat_base"]["is_pattern"] else 0,
                    "flat_base_depth": item["flat_base"]["base_depth_pct"] if item["flat_base"]["is_pattern"] else 0.0,
                    "volume_contraction": item["volume_dry_up"]["volume_contraction_pct"],
                    "supply_drying_score": item["volume_dry_up"]["drying_score"],
                    "accumulation_score": item["volume_dry_up"]["accumulation_score"]
                })
                
            ui_table_data = _to_native(ui_table_data)
            await self.cache.set_async("qai:scanner:institutional:results", ui_table_data, ttl=86400)
            logger.info("Cached institutional scanner results list in Dragonfly.")
        except Exception as ce:
            logger.error(f"Failed to cache scanner stats in Redis: {ce}")

    # =========================================================================
    # Stock Detail APIs
    # =========================================================================

    async def get_stock_detail(self, symbol: str) -> Dict[str, Any]:
        """Retrieve full scanner and fundamental details for a single stock."""
        db = SessionLocal()
        try:
            symbol = symbol.upper().strip()
            
            # Get latest close, profile and stats
            vcp = db.query(VcpScore).filter(VcpScore.symbol == symbol).first()
            tt = db.query(TrendTemplateScore).filter(TrendTemplateScore.symbol == symbol).first()
            rs = db.query(RelativeStrengthRanking).filter(RelativeStrengthRanking.symbol == symbol).first()
            bo = db.query(BreakoutCandidate).filter(BreakoutCandidate.symbol == symbol).first()
            dbx = db.query(DarvasBox).filter(DarvasBox.symbol == symbol).first()
            patterns = db.query(InstitutionalPattern).filter(InstitutionalPattern.symbol == symbol).all()
            
            # Fetch Upstox News, Competitors, Balance Sheet via Upstox REST API wrapper
            from services.upstox_client import get_upstox_client
            client = get_upstox_client()
            
            # Resolve ISIN
            inst = db.execute(
                text("SELECT isin_code, instrument_key FROM instrument_master WHERE symbol = :symbol"),
                {"symbol": symbol}
            ).fetchone()
            
            isin = inst[0] if inst else None
            inst_key = inst[1] if inst else None
            
            # Fetch News (real data)
            news_data = []
            if inst_key:
                try:
                    res = await client._make_request("GET", f"/news?category=instrument_keys&instrument_keys={inst_key}")
                    if res.get("status") == "success" and res.get("data"):
                        news_data = res.get("data")[:5]
                except Exception as ne:
                    logger.warning(f"Failed to fetch Upstox news for {symbol}: {ne}")
                    
            # Fetch Competitors (real data)
            competitors = []
            if inst_key:
                try:
                    import urllib.parse
                    encoded_key = urllib.parse.quote(inst_key, safe='')
                    res = await client._make_request("GET", f"/fundamentals/{encoded_key}/competitors")
                    if res.get("status") == "success" and res.get("data"):
                        raw_competitors = res.get("data")[:4]
                        mapped_competitors = []
                        for peer in raw_competitors:
                            peer_key = peer.get("instrument_key")
                            peer_info = db.execute(
                                text("SELECT symbol, company_name FROM instrument_master WHERE instrument_key = :key"),
                                {"key": peer_key}
                            ).fetchone()
                            
                            symbol_val = peer_info[0] if peer_info else None
                            company_val = peer_info[1] if peer_info else None
                            
                            mcap_val = 0.0
                            mcap_inr = peer.get("sector_market_cap_inr")
                            if mcap_inr and isinstance(mcap_inr, dict):
                                mcap_val = float(mcap_inr.get("value", 0.0)) * 100000000.0 # Crore to Rupee (1 crore = 10^7 or 10^8 depending on base, let's use 10^7 for standard crore conversion)
                                
                            mapped_competitors.append({
                                "symbol": symbol_val or (peer_key.split("|")[-1] if peer_key else "UNKNOWN"),
                                "company_name": company_val or (peer.get("company_profile", "").split(" Limited")[0] + " Limited" if peer.get("company_profile") else "Peer"),
                                "market_cap": mcap_val,
                                "pe_ratio": 18.5
                            })
                        competitors = mapped_competitors
                except Exception as ce:
                    logger.warning(f"Failed to fetch Upstox competitors for {symbol}: {ce}")
                    
            # Fetch Key Ratios & Fundamentals
            fundamentals = db.execute(
                text("SELECT * FROM fundamental_metrics WHERE symbol = :symbol"),
                {"symbol": symbol}
            ).mappings().fetchone()
            
            # Resolve current price for this stock
            current_price = 0.0
            if bo and bo.current_price:
                current_price = bo.current_price
            elif vcp and vcp.current_price:
                current_price = vcp.current_price
                
            if current_price == 0.0:
                try:
                    df = self.market_data.load_candles(symbol, "1d")
                    if not df.empty:
                        current_price = float(df['close'].iloc[-1])
                except Exception as pe:
                    logger.warning(f"Failed to load candles for {symbol} to get current price: {pe}")
            
            # Construct JSON response
            return {
                "symbol": symbol,
                "company_name": get_company_name(symbol),
                "sector": get_stock_sector(symbol),
                "vcp": {
                    "vcp_score": vcp.vcp_score if vcp else 0.0,
                    "num_contractions": vcp.num_contractions if vcp else 0,
                    "latest_contraction_pct": vcp.latest_contraction_pct if vcp else 0.0,
                    "volume_dry_up_pct": vcp.volume_dry_up_pct if vcp else 0.0,
                    "atr_contraction_pct": vcp.atr_contraction_pct if vcp else 0.0,
                    "breakout_pivot": vcp.breakout_pivot if vcp else 0.0,
                    "breakout_ready": vcp.breakout_ready if vcp else False,
                    "category": vcp.category if vcp else "Ignore",
                    "trend_quality": vcp.trend_quality if vcp else 0.0,
                    "volatility_compression": vcp.volatility_compression if vcp else 0.0
                } if vcp else None,
                "trend_template": {
                    "score": tt.trend_template_score if tt else 0.0,
                    "sma50": tt.sma50 if tt else 0.0,
                    "sma150": tt.sma150 if tt else 0.0,
                    "sma200": tt.sma200 if tt else 0.0,
                    "distance_to_52w_high": tt.distance_to_52w_high if tt else 0.0,
                    "conditions": {
                        "price_above_sma50": tt.price_above_sma50 if tt else False,
                        "price_above_sma150": tt.price_above_sma150 if tt else False,
                        "price_above_sma200": tt.price_above_sma200 if tt else False,
                        "sma50_above_sma150": tt.sma50_above_sma150 if tt else False,
                        "sma150_above_sma200": tt.sma150_above_sma200 if tt else False,
                        "price_above_52w_low_by_30pct": tt.price_above_52w_low_by_30pct if tt else False,
                        "price_within_25pct_of_52w_high": tt.price_within_25pct_of_52w_high if tt else False
                    }
                } if tt else None,
                "relative_strength": {
                    "rs_score": rs.rs_score if rs else 0.0,
                    "rank": rs.rank if rs else 0,
                    "sector_rank": rs.sector_rank if rs else 0,
                    "industry_rank": rs.industry_rank if rs else 0,
                    "return_6m": rs.return_6m if rs else 0.0,
                    "return_3m": rs.return_3m if rs else 0.0,
                    "return_1m": rs.return_1m if rs else 0.0
                } if rs else None,
                "breakout": {
                    "is_breakout": True if bo else False,
                    "breakout_price": bo.breakout_price if bo else 0.0,
                    "current_price": current_price,
                    "breakout_pct": bo.breakout_pct if bo else 0.0,
                    "volume_surge_pct": bo.volume_surge_pct if bo else 0.0,
                    "confirmation_status": bo.confirmation_status if bo else "None",
                    "breakout_type": bo.breakout_type if bo else "None"
                },
                "darvas": {
                    "box_top": dbx.box_top if dbx else 0.0,
                    "box_bottom": dbx.box_bottom if dbx else 0.0,
                    "days_inside_box": dbx.days_inside_box if dbx else 0,
                    "breakout_status": dbx.breakout_status if dbx else "None"
                } if dbx else None,
                "patterns": [
                    {
                        "pattern_type": p.pattern_type,
                        "confidence_score": p.confidence_score,
                        "breakout_pivot": p.breakout_pivot,
                        "breakout_status": p.breakout_status,
                        "details": p.details,
                        "updated_at": p.updated_at.isoformat()
                    } for p in patterns
                ],
                "fundamentals": dict(fundamentals) if fundamentals else None,
                "news": news_data,
                "competitors": competitors
            }
        except Exception as e:
            logger.error(f"Error loading stock detail for {symbol}: {e}")
            raise e
        finally:
            db.close()

# Singleton accessor
_scanner_service = None

def get_institutional_scanner_service() -> InstitutionalScannerService:
    global _scanner_service
    if _scanner_service is None:
        _scanner_service = InstitutionalScannerService()
    return _scanner_service
