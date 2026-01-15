
import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def inspect_db():
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='admin',
            database='quantai'
        )
        cur = conn.cursor()
        
        # Check tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cur.fetchall()
        logger.info(f"Tables in DB: {[t[0] for t in tables]}")
        
        # Check stock_candles schema
        if ('stock_candles',) in tables:
            logger.info("Inspecting stock_candles schema...")
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'stock_candles'
                ORDER BY ordinal_position
            """)
            columns = cur.fetchall()
            for col in columns:
                logger.info(f"  Column: {col[0]}, Type: {col[1]}, Nullable: {col[2]}")
                
            # Check row count and timeframes
            cur.execute("SELECT timeframe, COUNT(*), MIN(timestamp), MAX(timestamp) FROM stock_candles GROUP BY timeframe")
            stats = cur.fetchall()
            logger.info("Stock Candles Stats:")
            for s in stats:
                logger.info(f"  TF: {s[0]}, Count: {s[1]}, Start: {s[2]}, End: {s[3]}")
        else:
            logger.error("stock_candles table NOT found in Postgres!")

        # Check stock_data schema for comparison
        if ('stock_data',) in tables:
            logger.info("Inspecting stock_data schema...")
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'stock_data'
                ORDER BY ordinal_position
            """)
            columns = cur.fetchall()
            for col in columns:
                logger.info(f"  Column: {col[0]}, Type: {col[1]}, Nullable: {col[2]}")
                
            cur.execute("SELECT interval, COUNT(*), MIN(timestamp), MAX(timestamp) FROM stock_data GROUP BY interval")
            stats = cur.fetchall()
            logger.info("Stock Data Stats:")
            for s in stats:
                logger.info(f"  Interval: {s[0]}, Count: {s[1]}, Start: {s[2]}, End: {s[3]}")

        conn.close()
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    inspect_db()
