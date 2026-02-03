import asyncio
from sqlalchemy import text
from database import engine

async def get_db_size():
    try:
        async with engine.connect() as conn:
            # Get Database Size
            db_size_query = text("SELECT pg_size_pretty(pg_database_size('quantai'));")
            result = await conn.execute(db_size_query)
            db_size = result.scalar()
            print(f"Database 'quantai' size: {db_size}")
            
            # Get Top 10 Tables by Size
            table_size_query = text("""
                SELECT 
                    relname AS "Table",
                    pg_size_pretty(pg_total_relation_size(C.oid)) AS "Size"
                FROM pg_class C
                LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
                WHERE nspname NOT IN ('pg_catalog', 'information_schema')
                  AND C.relkind <> 'i'
                  AND nspname !~ '^pg_toast'
                ORDER BY pg_total_relation_size(C.oid) DESC
                LIMIT 10;
            """)
            print("\nTop 10 Tables by Size:")
            print("-" * 30)
            result = await conn.execute(table_size_query)
            for row in result:
                print(f"{row[0]:<20} | {row[1]}")
                
    except Exception as e:
        print(f"Error checking database size: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(get_db_size())
