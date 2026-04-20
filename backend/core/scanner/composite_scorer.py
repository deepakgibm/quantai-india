import pandas as pd
from typing import Dict, Any, List
import logging
from sqlalchemy import text
from database import SessionLocal
from core.duckdb_engine import engine as duckdb_engine
from services.dragonfly_client import get_cache

logger = logging.getLogger(__name__)

class CompositeScoringEngine:
    """
    Evaluates stocks using a weighted composite model:
    - 40% Technicals (DuckDB generated RSI/MACD/ATR)
    - 30% Institutional Flows (from PostgreSQL)
    - 30% Fundamentals (from PostgreSQL)
    """
    def __init__(self):
        # Weight configurations
        self.TECHNICAL_WEIGHT = 0.4
        self.INSTITUTIONAL_WEIGHT = 0.3
        self.FUNDAMENTAL_WEIGHT = 0.3

    def score_symbol(self, symbol: str) -> Dict[str, Any]:
        """Runs the composite scoring algorithm on a specific symbol."""
        db = SessionLocal()
        technical_score = 0.0
        institutional_score = 0.0
        fundamental_score = 0.0
        
        try:
            # 1. Technical Score (from DuckDB)
            # Evaluate using daily candles
            df = duckdb_engine.query_candles(symbol, "1d")
            if not df.empty and len(df) > 14:
                # Basic mock logic for technical rating out of 100
                latest_close = df.iloc[-1]['close']
                sma_14 = df.iloc[-14:]['close'].mean()
                if latest_close > sma_14:
                    technical_score = 70.0 + min(((latest_close - sma_14) / sma_14) * 1000, 30.0)
                else:
                    technical_score = 40.0
                    
            # 2. Institutional Score (from PostgreSQL)
            # Find net buy vs sell quantities in recent deals
            query_inst = text("""
                SELECT deal_type, SUM(quantity) as total_qty
                FROM institutional_flows
                WHERE symbol = :symbol AND flow_category IN ('FII', 'DII')
                GROUP BY deal_type
            """)
            inst_results = db.execute(query_inst, {"symbol": symbol}).fetchall()
            buy_qty = 0
            sell_qty = 0
            for row in inst_results:
                if row.deal_type == 'BUY':
                    buy_qty = row.total_qty
                elif row.deal_type == 'SELL':
                    sell_qty = row.total_qty
                    
            if buy_qty > sell_qty:
                ratio = buy_qty / (sell_qty + 1)
                institutional_score = min(50.0 + (ratio * 10), 100.0)
            elif sell_qty > buy_qty:
                institutional_score = 20.0
            else:
                institutional_score = 50.0

            # 3. Fundamental Score (from PostgreSQL)
            query_fund = text("""
                SELECT roe, debt_to_equity, pe_ratio FROM fundamental_metrics
                WHERE symbol = :symbol
            """)
            fund_result = db.execute(query_fund, {"symbol": symbol}).fetchone()
            if fund_result:
                roe, d_to_e, pe = fund_result
                f_score = 50.0
                if roe is not None and roe > 15: f_score += 20
                if d_to_e is not None and d_to_e < 1: f_score += 20
                if pe is not None and pe < 25: f_score += 10
                fundamental_score = min(f_score, 100.0)
            else:
                fundamental_score = 50.0 # Neutral

            # Format final composite config
            final_score = (
                (technical_score * self.TECHNICAL_WEIGHT) +
                (institutional_score * self.INSTITUTIONAL_WEIGHT) +
                (fundamental_score * self.FUNDAMENTAL_WEIGHT)
            )
            
            result = {
                "symbol": symbol,
                "composite_score": round(final_score, 2),
                "breakdown": {
                    "technical": round(technical_score, 2),
                    "institutional": round(institutional_score, 2),
                    "fundamental": round(fundamental_score, 2)
                }
            }
            
            # Cache the result to Redis to prevent re-querying inside screener APIs
            cache = get_cache()
            if cache.is_available():
                cache.set(f"screener:composite:{symbol}", result, ttl=3600)
                
            return result
            
        except Exception as e:
            logger.error(f"Failed composite scoring for {symbol}: {e}")
            return {"symbol": symbol, "composite_score": 0.0}
        finally:
            db.close()

scoring_engine = CompositeScoringEngine()
