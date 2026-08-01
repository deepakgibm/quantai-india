"""Create optimized indexes

Revision ID: 001_create_optimized_indexes
Revises: None
Create Date: 2026-06-23 18:00:00

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '001_create_optimized_indexes'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. precomputed_indicators indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_indicators_lookup ON precomputed_indicators (symbol, interval, timestamp DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_indicators_momentum ON precomputed_indicators (momentum_score)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_indicators_volatility ON precomputed_indicators (volatility_score)")
    
    # 2. stock_candle indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_candles_lookup_fast ON stock_candle (instrument_id, timeframe, candle_ts DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_candle_timeframe_instrument_ts ON stock_candle (timeframe, instrument_id, candle_ts DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_candle_tf_ts ON stock_candle (timeframe, candle_ts DESC)")

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_candle_tf_ts")
    op.execute("DROP INDEX IF EXISTS idx_candle_timeframe_instrument_ts")
    op.execute("DROP INDEX IF EXISTS idx_candles_lookup_fast")
    op.execute("DROP INDEX IF EXISTS idx_indicators_volatility")
    op.execute("DROP INDEX IF EXISTS idx_indicators_momentum")
    op.execute("DROP INDEX IF EXISTS idx_indicators_lookup")
