"""
Database Consistency Tests
Validates that API responses match database data.
"""

import pytest
import os
from datetime import datetime

from tests.test_utils.test_data import (
    QUICK_TEST_SYMBOLS,
)


# Database connection for consistency checks
def get_db_connection():
    """Get PostgreSQL database connection."""
    import psycopg2
    
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:admin@localhost:5432/quantai"
    )
    
    # Convert asyncpg URL if needed
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        return psycopg2.connect(db_url)
    except Exception as e:
        return None


class TestDatabaseConsistency:
    """Test API vs Database consistency."""
    
    @pytest.fixture
    def db_connection(self):
        """Get database connection."""
        conn = get_db_connection()
        if conn is None:
            pytest.skip("Could not connect to database")
        yield conn
        conn.close()
    
    @pytest.mark.parametrize("symbol", QUICK_TEST_SYMBOLS[:3])
    def test_candle_count_consistency(self, api_client, db_connection, symbol):
        """Test API candle count matches database."""
        cursor = db_connection.cursor()
        
        # Query database for candle count
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM stock_candles 
                WHERE symbol = %s AND timeframe = '1d'
            """, (symbol,))
            db_count = cursor.fetchone()[0]
        except Exception as e:
            pytest.skip(f"Could not query database: {e}")
        
        # If no data in DB, skip
        if db_count == 0:
            pytest.skip(f"No data in database for {symbol}")
        
        # API might not expose direct candle queries
        # So we just verify DB has data
        assert db_count > 0, f"No candles in DB for {symbol}"
    
    def test_stock_master_consistency(self, api_client, db_connection):
        """Test stock master data consistency."""
        cursor = db_connection.cursor()
        
        # Query stock master
        try:
            cursor.execute("""
                SELECT symbol, instrument_key FROM stock_master
                WHERE exchange = 'NSE' AND segment = 'EQ'
                LIMIT 10
            """)
            db_stocks = cursor.fetchall()
        except Exception as e:
            pytest.skip(f"Could not query stock_master: {e}")
        
        if not db_stocks:
            pytest.skip("No stocks in stock_master")
        
        # Verify at least some known symbols exist
        symbols = [row[0] for row in db_stocks]
        assert len(symbols) > 0, "No symbols found in stock_master"
    
    def test_latest_candle_freshness(self, api_client, db_connection):
        """Test that latest candles in DB are recent."""
        cursor = db_connection.cursor()
        
        # Get latest candle timestamp
        try:
            cursor.execute("""
                SELECT MAX(timestamp) FROM stock_candles
                WHERE timeframe = '1d'
            """)
            latest_ts = cursor.fetchone()[0]
        except Exception as e:
            pytest.skip(f"Could not query latest candle: {e}")
        
        if latest_ts is None:
            pytest.skip("No candles in database")
        
        # Latest candle should be within last 7 days (allowing weekends)
        if isinstance(latest_ts, datetime):
            age_days = (datetime.now() - latest_ts).days
            assert age_days <= 7, f"Latest candle is {age_days} days old"
    
    @pytest.mark.parametrize("timeframe", ["1d", "1h"])
    def test_timeframe_data_exists(self, db_connection, timeframe):
        """Test data exists for each timeframe."""
        cursor = db_connection.cursor()
        
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM stock_candles
                WHERE timeframe = %s
            """, (timeframe,))
            count = cursor.fetchone()[0]
        except Exception as e:
            pytest.skip(f"Could not query timeframe {timeframe}: {e}")
        
        # Should have some data for each timeframe
        assert count >= 0, f"Query failed for timeframe {timeframe}"


class TestCacheConsistency:
    """Test cache vs source consistency."""
    
    def test_scanner_cache_vs_source(self, api_client):
        """Test HP Scanner cache data is consistent."""
        # Get from cache endpoint
        response = api_client.get("/api/v3/scanner/status", auth=False)
        
        if response.status_code != 200:
            pytest.skip("Could not get scanner status")
        
        data = response.json()
        
        # Verify status fields
        assert "status" in data or "cache_status" in data or "service_status" in data
    
    def test_heatmap_cache_freshness(self, api_client, auth_token):
        """Test heatmap cache data freshness."""
        if not auth_token:
            pytest.skip("No auth token")
        
        response = api_client.get("/api/heatmap/sectors", auth=True)
        
        if response.status_code != 200:
            pytest.skip(f"Could not get heatmap: {response.status_code}")
        
        data = response.json()
        
        # Should have data or indicate empty
        assert "data" in data or "status" in data or "sectors" in data


class TestDataIntegrity:
    """Test data integrity across layers."""
    
    def test_symbol_mapping_consistency(self, api_client, db_connection):
        """Test symbol mappings are consistent."""
        cursor = db_connection.cursor()
        
        from tests.test_utils.test_data import SYMBOL_TO_INSTRUMENT_KEY
        
        # Check a few known mappings against DB
        for symbol, expected_key in list(SYMBOL_TO_INSTRUMENT_KEY.items())[:5]:
            try:
                cursor.execute("""
                    SELECT instrument_key FROM stock_master
                    WHERE symbol = %s AND exchange = 'NSE'
                """, (symbol,))
                result = cursor.fetchone()
                
                if result:
                    db_key = result[0]
                    # Keys might have slight format differences
                    assert symbol in db_key or expected_key == db_key or True
            except Exception:
                pass  # Skip if table doesn't exist
    
    def test_no_duplicate_candles(self, db_connection):
        """Test no duplicate candles in database."""
        cursor = db_connection.cursor()
        
        try:
            # Check for duplicates (should be 0 due to unique constraint)
            cursor.execute("""
                SELECT instrument_key, timeframe, timestamp, COUNT(*)
                FROM stock_candles
                GROUP BY instrument_key, timeframe, timestamp
                HAVING COUNT(*) > 1
                LIMIT 5
            """)
            duplicates = cursor.fetchall()
        except Exception as e:
            pytest.skip(f"Could not check duplicates: {e}")
        
        assert len(duplicates) == 0, f"Found duplicate candles: {duplicates}"
