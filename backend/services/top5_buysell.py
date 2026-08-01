"""
Top 5 Buy/Sell Engine Service
Identifies the best intraday/swing trading opportunities using technical analysis.
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings
from models_alpha import InstrumentMaster
from services.instrument_resolver import resolve_instrument_id


class Top5BuySellEngine:
    """
    Quantitative buy/sell signal generator.
    
    Criteria:
    - Strong trend (EMA alignment)
    - Momentum confirmation (RSI)
    - Volume support
    - Clear entry/exit levels
    
    Returns top 5 BUY and top 5 SELL candidates.
    """
    
    def __init__(self):
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        self.min_score = 60
        
    def _get_ohlcv_data(self, symbol: str, days: int = 100) -> Optional[pd.DataFrame]:
        try:
            from models_alpha import StockCandle
            session = self._Session()
            try:
                # Resolve symbol to instrument_id
                instrument_id = resolve_instrument_id(symbol)
                if not instrument_id:
                    return None
                    
                cutoff_date = datetime.now() - timedelta(days=days)
                # Filter by instrument_id and timeframe=1440 (1d)
                results = session.query(StockCandle).filter(
                    StockCandle.instrument_id == instrument_id,
                    StockCandle.timeframe == 1440,
                    StockCandle.candle_ts >= cutoff_date
                ).order_by(StockCandle.candle_ts.asc()).all()
                
                if not results or len(results) < 30:
                    return None
                
                data = [{
                    'timestamp': r.candle_ts, 'open': float(r.open),
                    'high': float(r.high), 'low': float(r.low),
                    'close': float(r.close), 'volume': int(r.volume)
                } for r in results]
                
                df = pd.DataFrame(data)
                df.set_index('timestamp', inplace=True)
                return df
            finally:
                session.close()
        except Exception:
            return None
    
    def analyze_stock(self, symbol: str) -> Optional[Dict]:
        """Generate buy/sell signal for a stock."""
        df = self._get_ohlcv_data(symbol)
        
        if df is None or len(df) < 30:
            return None
        
        close = df['close']
        volume = df['volume']
        
        current_price = close.iloc[-1]
        
        # EMAs
        ema_9 = close.ewm(span=9, adjust=False).mean()
        ema_21 = close.ewm(span=21, adjust=False).mean()
        
        current_ema9 = ema_9.iloc[-1]
        current_ema21 = ema_21.iloc[-1]
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        if pd.isna(rsi):
            rsi = 50
        
        # Volume
        avg_volume = volume.tail(20).mean()
        current_vol = volume.iloc[-1]
        vol_ratio = current_vol / avg_volume if avg_volume > 0 else 1
        
        # MACD
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        macd = ema_12 - ema_26
        signal_line = macd.ewm(span=9, adjust=False).mean()
        macd_histogram = (macd - signal_line).iloc[-1]
        
        # Determine action
        scores = {}
        
        # EMA alignment (30%)
        if current_ema9 > current_ema21 and current_price > current_ema9:
            action = "BUY"
            scores["ema_alignment"] = 90
        elif current_ema9 < current_ema21 and current_price < current_ema9:
            action = "SELL"
            scores["ema_alignment"] = 90
        elif current_ema9 > current_ema21:
            action = "BUY"
            scores["ema_alignment"] = 60
        else:
            action = "SELL"
            scores["ema_alignment"] = 60
        
        # RSI (25%)
        if action == "BUY":
            if 40 <= rsi <= 65:
                scores["rsi"] = 90
            elif rsi < 40:
                scores["rsi"] = 70  # Potentially oversold
            else:
                scores["rsi"] = 40  # Overbought
        else:
            if 35 <= rsi <= 60:
                scores["rsi"] = 90
            elif rsi > 60:
                scores["rsi"] = 70  # Potentially overbought
            else:
                scores["rsi"] = 40
        
        # Volume (20%)
        if vol_ratio >= 1.5:
            scores["volume"] = 90
        elif vol_ratio >= 1.0:
            scores["volume"] = 60
        else:
            scores["volume"] = 30
        
        # MACD (25%)
        if action == "BUY" and macd_histogram > 0:
            scores["macd"] = 90
        elif action == "SELL" and macd_histogram < 0:
            scores["macd"] = 90
        else:
            scores["macd"] = 40
        
        weights = {"ema_alignment": 0.30, "rsi": 0.25, "volume": 0.20, "macd": 0.25}
        total_score = sum(scores[k] * weights[k] for k in scores)
        
        # Calculate targets
        atr = (df['high'] - df['low']).tail(14).mean()
        
        if action == "BUY":
            entry_low = round(current_price * 0.995, 2)
            entry_high = round(current_price * 1.005, 2)
            target_1 = round(current_price + atr, 2)
            target_2 = round(current_price + atr * 2, 2)
            stop_loss = round(current_price - atr * 1.5, 2)
            expected_move = f"+{round((target_1/current_price - 1) * 100, 1)}%"
        else:
            entry_low = round(current_price * 0.995, 2)
            entry_high = round(current_price * 1.005, 2)
            target_1 = round(current_price - atr, 2)
            target_2 = round(current_price - atr * 2, 2)
            stop_loss = round(current_price + atr * 1.5, 2)
            expected_move = f"-{round((1 - target_1/current_price) * 100, 1)}%"
        
        return {
            "symbol": symbol,
            "name": self._get_stock_name(symbol),
            "action": action,
            "confidence": round(total_score),
            "current_price": round(current_price, 2),
            "entry_range": f"{entry_low}-{entry_high}",
            "target_1": target_1,
            "target_2": target_2,
            "stop_loss": stop_loss,
            "expected_move": expected_move,
            "indicators": {
                "rsi": round(rsi, 2),
                "volume_ratio": round(vol_ratio, 2),
                "macd_histogram": round(macd_histogram, 2)
            },
            "reason": self._generate_reason(action, rsi, vol_ratio, macd_histogram)
        }
    
    def _get_stock_name(self, symbol: str) -> str:
        from utils.symbol_utils import get_company_name
        return get_company_name(symbol)
    
    def _generate_reason(self, action: str, rsi: float, vol_ratio: float, macd: float) -> str:
        parts = []
        if action == "BUY":
            parts.append("Bullish EMA crossover")
        else:
            parts.append("Bearish EMA crossover")
        
        if rsi < 40:
            parts.append("oversold RSI")
        elif rsi > 60:
            parts.append("momentum RSI")
        
        if vol_ratio >= 1.5:
            parts.append(f"{vol_ratio:.1f}x volume")
        
        return ". ".join(parts[:2])
    
    def get_symbols(self) -> List[str]:
        from utils.symbol_utils import get_all_symbols
        return get_all_symbols()
    
    def _scan_all_vectorized(self, limit: int = 5) -> Dict[str, List[Dict]]:
        """
        OPTIMIZED: Vectorized scan using bulk query + pandas.
        Reduces 100+ individual queries to 1 bulk query.
        """
        import time
        t0 = time.time()
        
        try:
            from models_alpha import StockCandle
            import numpy as np
            
            session = self._Session()
            try:
                # Single bulk query for ALL symbols - last 100 days
                cutoff_date = datetime.now() - timedelta(days=100)
                query = session.query(
                    InstrumentMaster.symbol,
                    StockCandle.candle_ts.label('timestamp'),
                    StockCandle.open,
                    StockCandle.high,
                    StockCandle.low,
                    StockCandle.close,
                    StockCandle.volume
                ).join(
                    InstrumentMaster, 
                    StockCandle.instrument_id == InstrumentMaster.instrument_id
                ).filter(
                    StockCandle.timeframe == 1440,
                    StockCandle.candle_ts >= cutoff_date
                ).statement
                
                df = pd.read_sql(query, session.bind)
                
                if df.empty:
                    return {"buy": [], "sell": []}
                
                # Type conversions
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['close'] = df['close'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['volume'] = df['volume'].astype(float)
                
                # Sort
                df = df.sort_values(['symbol', 'timestamp'])
                
                # Vectorized indicator calculation per symbol
                g = df.groupby('symbol')
                
                # EMAs
                df['ema_9'] = g['close'].transform(lambda x: x.ewm(span=9, adjust=False).mean())
                df['ema_21'] = g['close'].transform(lambda x: x.ewm(span=21, adjust=False).mean())
                df['ema_12'] = g['close'].transform(lambda x: x.ewm(span=12, adjust=False).mean())
                df['ema_26'] = g['close'].transform(lambda x: x.ewm(span=26, adjust=False).mean())
                
                # MACD
                df['macd'] = df['ema_12'] - df['ema_26']
                df['macd_signal'] = df.groupby('symbol')['macd'].transform(lambda x: x.ewm(span=9, adjust=False).mean())
                df['macd_histogram'] = df['macd'] - df['macd_signal']
                
                # RSI
                def calc_rsi(x, period=14):
                    delta = x.diff()
                    gain = delta.where(delta > 0, 0).rolling(period).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
                    rs = gain / loss
                    return 100 - (100 / (1 + rs))
                
                df['rsi'] = g['close'].transform(lambda x: calc_rsi(x))
                
                # Volume ratio
                df['vol_avg_20'] = g['volume'].transform(lambda x: x.shift(1).rolling(20).mean())
                
                # Get latest row per symbol
                latest = df.groupby('symbol').tail(1).copy()
                
                # Clean NaNs
                latest['rsi'] = latest['rsi'].fillna(50)
                latest['vol_avg_20'] = latest['vol_avg_20'].replace(0, 1)
                latest['vol_ratio'] = latest['volume'] / latest['vol_avg_20']
                
                # Scoring
                # BUY: ema9 > ema21 and close > ema9
                # SELL: ema9 < ema21 and close < ema9
                buy_mask = (latest['ema_9'] > latest['ema_21']) & (latest['close'] > latest['ema_9'])
                sell_mask = (latest['ema_9'] < latest['ema_21']) & (latest['close'] < latest['ema_9'])
                
                latest['action'] = np.where(buy_mask, 'BUY', np.where(sell_mask, 'SELL', 'HOLD'))
                
                # Simple score based on RSI + volume + MACD alignment
                latest['score'] = 50  # Base
                # RSI
                latest.loc[(latest['action'] == 'BUY') & (latest['rsi'] >= 40) & (latest['rsi'] <= 65), 'score'] += 25
                latest.loc[(latest['action'] == 'SELL') & (latest['rsi'] >= 35) & (latest['rsi'] <= 60), 'score'] += 25
                # Volume
                latest.loc[latest['vol_ratio'] >= 1.5, 'score'] += 15
                latest.loc[(latest['vol_ratio'] >= 1.0) & (latest['vol_ratio'] < 1.5), 'score'] += 8
                # MACD
                latest.loc[(latest['action'] == 'BUY') & (latest['macd_histogram'] > 0), 'score'] += 15
                latest.loc[(latest['action'] == 'SELL') & (latest['macd_histogram'] < 0), 'score'] += 15
                
                # Filter by action and min score
                buys = latest[(latest['action'] == 'BUY') & (latest['score'] >= self.min_score)].nlargest(limit, 'score')
                sells = latest[(latest['action'] == 'SELL') & (latest['score'] >= self.min_score)].nlargest(limit, 'score')
                
                t1 = time.time()
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Top5BuySell: Vectorized scan of {len(df['symbol'].unique())} symbols completed in {(t1-t0)*1000:.0f}ms. Found {len(buys)} BUY, {len(sells)} SELL.")
                
                # Format output
                def format_row(row, action):
                    atr = 10  # Simplified ATR estimate
                    price = row['close']
                    if action == 'BUY':
                        target = round(price * 1.03, 2)
                        stop = round(price * 0.985, 2)
                        expected = "+3%"
                    else:
                        target = round(price * 0.97, 2)
                        stop = round(price * 1.015, 2)
                        expected = "-3%"
                    
                    # Sanitize indicators for JSON
                    def s(val):
                        import math
                        if isinstance(val, (float, int)) and (math.isnan(val) or math.isinf(val)):
                            return 0.0
                        return val

                    return {
                        "symbol": row['symbol'],
                        "name": row['symbol'],
                        "action": action,
                        "confidence": int(s(row['score'])),
                        "current_price": round(s(price), 2),
                        "entry_range": f"{round(s(price)*0.995,2)}-{round(s(price)*1.005,2)}",
                        "target_1": s(target),
                        "target_2": round(s(target) * 1.02, 2),
                        "stop_loss": s(stop),
                        "expected_move": expected,
                        "indicators": {
                            "rsi": round(s(row['rsi']), 2),
                            "volume_ratio": round(s(row['vol_ratio']), 2),
                            "macd_histogram": round(s(row['macd_histogram']), 4)
                        },
                        "reason": f"{'Bullish' if action=='BUY' else 'Bearish'} EMA crossover"
                    }
                
                buy_signals = [format_row(row, 'BUY') for _, row in buys.iterrows()]
                sell_signals = [format_row(row, 'SELL') for _, row in sells.iterrows()]
                
                elapsed = (time.time() - t0) * 1000
                total_symbols = len(latest)
                
                return {
                    "stocks": buy_signals + sell_signals,
                    "symbols_processed": total_symbols,
                    "total_symbols": total_symbols,
                    "completed_all": True,
                    "filter_stats": {
                        "filtered_by_rule": total_symbols - (len(buy_signals) + len(sell_signals))
                    },
                    "tables_used": ["stock_candle", "instrument_master"],
                    "metrics": {
                        "total_ms": int(elapsed)
                    }
                }
                
            finally:
                session.close()
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Top5BuySell: Vectorized scan error: {e}", exc_info=True)
            return {"buy": [], "sell": []}
    
    def scan_all(self, limit: int = 5) -> Dict[str, List[Dict]]:
        """
        Scan all stocks and return top 5 BUY and top 5 SELL signals.
        Uses vectorized method for performance.
        """
        # Use fast vectorized scan
        return self._scan_all_vectorized(limit)
