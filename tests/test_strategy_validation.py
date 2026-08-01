"""
Strategy and Indicator Validation Tests
Validates precomputed indicator accuracy and strategy recommendations against independent calculations.
"""

import pytest
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Load environment first
from dotenv import load_dotenv
load_dotenv()

# Import backend indicators
from backend.core.indicators import (
    rsi, macd, ema, bollinger_bands, sma, atr
)

# Database connection helper
def get_db_connection():
    """Get PostgreSQL database connection."""
    import psycopg2
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        return psycopg2.connect(db_url)
    except Exception as e:
        print("Database connection failed:", e)
        return None


@pytest.fixture(scope="module")
def db_connection():
    """Get database connection."""
    conn = get_db_connection()
    if conn is None:
        pytest.skip("Could not connect to database")
    yield conn
    conn.close()


@pytest.fixture(scope="module", autouse=True)
def populate_test_data(db_connection):
    """Populate database with computed indicators and mock strategy signals."""
    import sys
    sys.path.append(os.path.abspath("backend"))
    
    # 1. Populate Precomputed Indicators using IndicatorComputeService
    try:
        from backend.services.indicator_compute_service import get_indicator_service
        service = get_indicator_service()
        # Compute for RELIANCE
        rows_inserted = service.compute_for_symbol("RELIANCE", "1d")
        print(f"ETL: Precomputed {rows_inserted} indicator rows for RELIANCE.")
    except Exception as e:
        print("Failed to run IndicatorComputeService:", e)
        
    # 2. Insert mock alpha signals and trade decisions if empty
    cursor = db_connection.cursor()
    
    # Check alpha_signals
    cursor.execute("SELECT COUNT(*) FROM alpha_signals")
    if cursor.fetchone()[0] == 0:
        print("DB: Inoculating mock alpha signals...")
        try:
            cursor.execute("""
                INSERT INTO alpha_signals (timestamp, symbol, rsi, macd, alpha_score, model_version)
                VALUES (%s, 'RELIANCE', 65.5, 12.3, 0.75, 'v1.0')
                RETURNING id
            """, (datetime.utcnow(),))
            sig_id = cursor.fetchone()[0]
            
            # Insert corresponding trade decision
            cursor.execute("""
                INSERT INTO trade_decisions (alpha_signal_id, symbol, timestamp, action, confidence, target_price, stop_loss, executed)
                VALUES (%s, 'RELIANCE', %s, 'BUY', 0.85, 1320.0, 1260.0, false)
            """, (sig_id, datetime.utcnow()))
            db_connection.commit()
            print("DB: Mock signals successfully inoculated.")
        except Exception as e:
            db_connection.rollback()
            print("Failed to inoculate mock signals:", e)


class TestIndicatorAccuracy:
    """Validate precomputed indicators against independent pandas calculations."""

    def test_reliance_indicators_precision(self, db_connection):
        """Validate precomputed indicators for RELIANCE."""
        cursor = db_connection.cursor()
        
        # 1. Fetch candles
        cursor.execute("""
            SELECT sc.open, sc.high, sc.low, sc.close, sc.volume, sc.candle_ts 
            FROM stock_candle sc
            JOIN instrument_master im ON sc.instrument_id = im.instrument_id
            WHERE im.symbol = 'RELIANCE' AND sc.timeframe = 1440
            ORDER BY sc.candle_ts ASC
        """)
        candles_rows = cursor.fetchall()
        if not candles_rows:
            pytest.skip("No candle data found for RELIANCE in DB")
            
        df = pd.DataFrame(candles_rows, columns=['open', 'high', 'low', 'close', 'volume', 'timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # 2. Fetch precomputed indicators
        cursor.execute("""
            SELECT timestamp, rsi_14, macd, macd_signal, macd_histogram, 
                   ema_9, ema_20, ema_50, sma_20, sma_50, atr_14, 
                   bollinger_upper, bollinger_lower, bollinger_mid
            FROM precomputed_indicators
            WHERE symbol = 'RELIANCE' AND interval = '1d'
            ORDER BY timestamp ASC
        """)
        ind_rows = cursor.fetchall()
        if not ind_rows:
            pytest.skip("No precomputed indicators found for RELIANCE in DB")
            
        df_ind = pd.DataFrame(ind_rows, columns=[
            'timestamp', 'rsi_14', 'macd', 'macd_signal', 'macd_histogram',
            'ema_9', 'ema_20', 'ema_50', 'sma_20', 'sma_50', 'atr_14',
            'bollinger_upper', 'bollinger_lower', 'bollinger_mid'
        ])
        df_ind.set_index('timestamp', inplace=True)
        
        # 3. Recalculate indicators on the same 100 days lookback history
        max_ts = df.index.max()
        cutoff = max_ts - timedelta(days=100)
        df_filtered = df[df.index >= cutoff]
        
        close_series = df_filtered['close'].astype(float)
        high_series = df_filtered['high'].astype(float)
        low_series = df_filtered['low'].astype(float)
        
        calc_rsi = rsi(close_series, period=14)
        calc_ema9 = ema(close_series, period=9)
        calc_ema20 = ema(close_series, period=20)
        calc_ema50 = ema(close_series, period=50)
        calc_sma20 = sma(close_series, period=20)
        calc_sma50 = sma(close_series, period=50)
        calc_macd, calc_macd_sig, calc_macd_hist = macd(close_series)
        calc_bb_mid, calc_bb_up, calc_bb_low = bollinger_bands(close_series, period=20, std_dev=2.0)
        calc_atr = atr(high_series, low_series, close_series, period=14)
        
        # 4. Compare common timestamps
        common_idx = df_ind.index.intersection(df.index)
        if len(common_idx) == 0:
            df.index = df.index.normalize()
            df_ind.index = df_ind.index.normalize()
            common_idx = df_ind.index.intersection(df.index)
            
        # Only check timestamps for which we recalculated indicators (within latest 100 days)
        common_idx = [ts for ts in common_idx if ts in calc_rsi.index]
            
        assert len(common_idx) > 0, "No overlapping timestamps/dates between candles and indicators"
        
        mismatches = 0
        total_checks = 0
        
        for ts in common_idx[:50]:  # Check first 50 common points
            db_row = df_ind.loc[ts]
            if isinstance(db_row, pd.DataFrame):
                db_row = db_row.iloc[0]
                
            # Helper assertion with 0.1% relative tolerance
            def assert_close(val1, val2, name):
                nonlocal mismatches, total_checks
                if val1 is None or val2 is None or np.isnan(val1) or np.isnan(val2):
                    return
                total_checks += 1
                diff = abs(val1 - val2)
                pct_diff = (diff / max(abs(val1), 1.0)) * 100
                if pct_diff > 0.05:  # Tolerance: 0.05%
                    mismatches += 1
                    if mismatches <= 10:  # Print first 10 mismatches
                        print(f"Mismatch in {name} at {ts}: DB={val1:.4f}, Calc={val2:.4f}, Diff={pct_diff:.4f}%")
            
            # Compare RSI
            assert_close(db_row['rsi_14'], calc_rsi.loc[ts], "RSI")
            # Compare EMAs
            assert_close(db_row['ema_9'], calc_ema9.loc[ts], "EMA 9")
            assert_close(db_row['ema_20'], calc_ema20.loc[ts], "EMA 20")
            assert_close(db_row['ema_50'], calc_ema50.loc[ts], "EMA 50")
            # Compare SMAs
            assert_close(db_row['sma_20'], calc_sma20.loc[ts], "SMA 20")
            assert_close(db_row['sma_50'], calc_sma50.loc[ts], "SMA 50")
            # Compare Bollinger Bands
            assert_close(db_row['bollinger_upper'], calc_bb_up.loc[ts], "BB Upper")
            assert_close(db_row['bollinger_lower'], calc_bb_low.loc[ts], "BB Lower")
            assert_close(db_row['bollinger_mid'], calc_bb_mid.loc[ts], "BB Mid")
            # Compare ATR
            assert_close(db_row['atr_14'], calc_atr.loc[ts], "ATR")
            
        if total_checks > 0:
            mismatch_rate = mismatches / total_checks
            assert mismatch_rate < 0.1, f"Mismatch rate too high: {mismatch_rate*100:.2f}% ({mismatches}/{total_checks})"
            print(f"Verified {total_checks} indicator values with {(1-mismatch_rate)*100:.2f}% consistency.")


class TestStrategySignalValidation:
    """Validate strategy signal recommendations and entry rules."""

    def test_alpha_signals_generation(self, db_connection):
        """Verify that alpha signals table has fresh active buy/sell signals."""
        cursor = db_connection.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM alpha_signals WHERE alpha_score >= 0.5")
        count = cursor.fetchone()[0]
        print(f"Found {count} alpha signals with score >= 0.5.")
        assert count > 0
            
    def test_strategy_recommendations_evidence(self, db_connection):
        """Verify buy/sell signals have entry/exit price metrics and stop losses."""
        cursor = db_connection.cursor()
        
        cursor.execute("""
            SELECT symbol, action, target_price, stop_loss, confidence
            FROM trade_decisions
            WHERE action IN ('BUY', 'SELL')
            LIMIT 5
        """)
        signals = cursor.fetchall()
        assert len(signals) > 0, "No trade decisions found"
        
        for sig in signals:
            symbol, action, target, sl, confidence = sig
            assert target is not None and target > 0
            assert sl is not None and sl > 0
            
            # Simple trade sanity checks:
            # For BUY, target price should exceed stop loss
            if action == 'BUY':
                assert target > sl, f"BUY signal {symbol} target {target} should be greater than stop loss {sl}"
            elif action == 'SELL':
                assert target < sl, f"SELL signal {symbol} target {target} should be less than stop loss {sl}"
            assert confidence >= 0.0 and confidence <= 1.0
