from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Any

class SectorAnalysisRepository:
    @staticmethod
    async def get_raw_sector_data(db: AsyncSession) -> List[Any]:
        """
        Fetches daily candle close, volume, candle_ts, and fundamental metrics
        for all active instruments, limiting to the latest 300 candles per instrument.
        """
        sql = text("""
            WITH ranked_candles AS (
                SELECT 
                    instrument_id,
                    candle_ts,
                    close,
                    volume,
                    ROW_NUMBER() OVER (PARTITION BY instrument_id ORDER BY candle_ts DESC) as rn
                FROM stock_candle
                WHERE timeframe = 1440
            )
            SELECT 
                im.symbol,
                im.company_name,
                im.sector,
                rc.close,
                rc.volume,
                rc.candle_ts,
                fm.pe_ratio,
                fm.pb_ratio,
                fm.dividend_yield,
                fm.market_cap,
                fm.roe,
                fm.roce,
                fm.debt_to_equity,
                fm.sector_pe_benchmark,
                fm.sector_pb_benchmark,
                fm.updated_at as fundamentals_updated_at
            FROM instrument_master im
            JOIN ranked_candles rc ON im.instrument_id = rc.instrument_id
            LEFT JOIN fundamental_metrics fm ON im.symbol = fm.symbol
            WHERE im.is_active = TRUE AND rc.rn <= 300
            ORDER BY im.symbol, rc.candle_ts ASC
        """)
        result = await db.execute(sql)
        return result.fetchall()
