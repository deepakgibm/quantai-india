"""
Momentum Scanner Service
Finds stocks with strong price momentum using ROC and MFI indicators.
Optimized: Uses precomputed indicators when available.
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import settings
import logging

logger = logging.getLogger(__name__)


class MomentumScanner:
    """
    Momentum-based stock scanner.
    
    Indicators:
    - ROC (Rate of Change) - Price momentum
    - MFI (Money Flow Index) - Volume-weighted momentum
    - RSI acceleration - Momentum of momentum
    
    Optimization: Uses precomputed_indicators table when available.
    """
    
    def __init__(self):
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        self.min_score = 60
        self._use_precomputed = self._check_precomputed_available()
    
    def _check_precomputed_available(self) -> bool:
        """Check if precomputed indicators table exists and has data."""
        try:
            session = self._Session()
            try:
                result = session.execute(text(
                    "SELECT COUNT(*) FROM precomputed_indicators LIMIT 1"
                ))
                count = result.scalar()
                if count and count > 0:
                    logger.info("Precomputed indicators available - using fast path")
                    return True
            except Exception:
                pass
            finally:
                session.close()
        except Exception:
            pass
        return False
    
    def scan_from_precomputed(self, limit: int = 10) -> List[Dict]:
        """
        Fast scan using precomputed indicators.
        Returns top momentum stocks directly from indicator table.
        """
        session = self._Session()
        try:
            # Get latest indicators per symbol with high momentum score
            query = text("""
                WITH latest_indicators AS (
                    SELECT DISTINCT ON (symbol) 
                        symbol, timestamp, close, 
                        rsi_14, roc_10, roc_20, mfi_14, momentum_score
                    FROM precomputed_indicators
                    WHERE momentum_score IS NOT NULL
                    ORDER BY symbol, timestamp DESC
                )
                SELECT * FROM latest_indicators
                WHERE momentum_score >= :min_score
                ORDER BY momentum_score DESC
                LIMIT :limit
            """)
            
            result = session.execute(query, {"min_score": self.min_score, "limit": limit})
            rows = result.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "symbol": row.symbol,
                    "name": row.symbol,
                    "momentum_type": "STRONG" if row.roc_10 and row.roc_10 > 3 else "MODERATE",
                    "strength": round(row.momentum_score) if row.momentum_score else 0,
                    "current_price": round(float(row.close), 2) if row.close else 0,
                    "roc_10d": round(float(row.roc_10), 2) if row.roc_10 else 0,
                    "roc_20d": round(float(row.roc_20), 2) if row.roc_20 else 0,
                    "mfi": round(float(row.mfi_14), 2) if row.mfi_14 else 0,
                    "target_price": round(float(row.close) * 1.05, 2) if row.close else 0,
                    "stop_loss": round(float(row.close) * 0.97, 2) if row.close else 0,
                    "reason": f"ROC {row.roc_10:.1f}%. MFI {row.mfi_14:.0f}" if row.roc_10 and row.mfi_14 else "Precomputed"
                })
            
            logger.info(f"Fast scan: returned {len(results)} results from precomputed indicators")
            return results
            
        except Exception as e:
            logger.warning(f"Precomputed scan failed, falling back: {e}")
            return []
        finally:
            session.close()
        
    def _get_ohlcv_data(self, symbol: str, days: int = 60) -> Optional[pd.DataFrame]:
        try:
            from models_ml import Nifty100Daily
            from sqlalchemy import desc
            session = self._Session()
            try:
                # Get latest N records (no date filter - use whatever data is available)
                results = session.query(Nifty100Daily).filter(
                    Nifty100Daily.symbol == symbol
                ).order_by(desc(Nifty100Daily.timestamp)).limit(days).all()
                
                if not results or len(results) < 20:
                    return None
                
                # Reverse to chronological order
                results = results[::-1]
                
                data = [{'timestamp': r.timestamp, 'open': float(r.open), 'high': float(r.high),
                         'low': float(r.low), 'close': float(r.close), 'volume': int(r.volume)} for r in results]
                df = pd.DataFrame(data)
                df.set_index('timestamp', inplace=True)
                return df
            finally:
                session.close()
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None
    
    def calculate_mfi(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Money Flow Index."""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']
        
        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(period).sum()
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(period).sum()
        
        mfi = 100 - (100 / (1 + positive_flow / negative_flow))
        return mfi.iloc[-1] if not pd.isna(mfi.iloc[-1]) else 50
    
    def analyze_stock(self, symbol: str) -> Optional[Dict]:
        df = self._get_ohlcv_data(symbol)
        if df is None:
            return None
        
        close = df['close']
        current_price = close.iloc[-1]
        
        # ROC (10-period)
        roc_10 = ((close.iloc[-1] - close.iloc[-10]) / close.iloc[-10]) * 100 if len(close) >= 10 else 0
        roc_20 = ((close.iloc[-1] - close.iloc[-20]) / close.iloc[-20]) * 100 if len(close) >= 20 else 0
        
        # MFI
        mfi = self.calculate_mfi(df)
        
        # Score calculation
        scores = {}
        
        # ROC score (40%)
        if roc_10 > 5:
            scores["roc"] = 100
        elif roc_10 > 2:
            scores["roc"] = 80
        elif roc_10 > 0:
            scores["roc"] = 60
        else:
            scores["roc"] = 30
        
        # MFI score (30%)
        if 50 < mfi < 80:
            scores["mfi"] = 90
        elif mfi >= 80:
            scores["mfi"] = 50  # Overbought
        else:
            scores["mfi"] = 40
        
        # Trend consistency (30%)
        if roc_10 > 0 and roc_20 > 0:
            scores["trend"] = 90
        elif roc_10 > 0:
            scores["trend"] = 60
        else:
            scores["trend"] = 30
        
        total = scores["roc"] * 0.4 + scores["mfi"] * 0.3 + scores["trend"] * 0.3
        
        return {
            "symbol": symbol,
            "name": symbol,
            "momentum_type": "STRONG" if roc_10 > 3 else "MODERATE",
            "strength": round(total),
            "current_price": round(current_price, 2),
            "roc_10d": round(roc_10, 2),
            "roc_20d": round(roc_20, 2),
            "mfi": round(mfi, 2),
            "target_price": round(current_price * 1.05, 2),
            "stop_loss": round(current_price * 0.97, 2),
            "reason": f"ROC {roc_10:.1f}%. MFI {mfi:.0f}"
        }
    
    def get_symbols(self) -> List[str]:
        try:
            from models_ml import Nifty100Daily
            session = self._Session()
            try:
                return [s[0] for s in session.query(Nifty100Daily.symbol).distinct().all()]
            finally:
                session.close()
        except:
            return ["RELIANCE", "TCS", "HDFCBANK", "INFY"]
    
    def scan_all(self, limit: int = 10) -> List[Dict]:
        """
        Scan all symbols for momentum signals.
        Optimized: 
        1. Tries precomputed indicators first (fastest)
        2. Falls back to on-demand computation with symbol limits
        """
        # Try fast path using precomputed indicators
        if self._use_precomputed:
            precomputed_results = self.scan_from_precomputed(limit)
            if precomputed_results:
                return precomputed_results
        
        # Fallback: compute on-demand
        logger.info("Using on-demand indicator computation")
        symbols = self.get_symbols()[:200]  # Limit to 200 symbols max
        results = []
        
        for symbol in symbols:
            try:
                analysis = self.analyze_stock(symbol)
                if analysis and analysis["strength"] >= self.min_score:
                    results.append(analysis)
                    # Early termination: once we have 3x the limit, sort and return
                    if len(results) >= limit * 3:
                        break
            except:
                continue
        
        results.sort(key=lambda x: x["strength"], reverse=True)
        return results[:limit]
