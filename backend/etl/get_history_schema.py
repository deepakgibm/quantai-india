import psycopg2

def get_table_schema():
    try:
        conn = psycopg2.connect('postgresql://postgres:admin@localhost:5432/quantai')
        cur = conn.cursor()
        
        # 1. Get Columns
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'stock_candle_history' 
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        
        with open('backend/etl/schema_output.txt', 'w') as f:
            f.write("--- COLUMNS ---\n")
            for col in columns:
                f.write(f"Col: {col[0]}, Type: {col[1]}, Null: {col[2]}, Default: {col[3]}\n")
                
            # 2. Get Constraints (Primary Key, Unique)
            cur.execute("""
                SELECT
                    conname as constraint_name,
                    pg_get_constraintdef(c.oid) as constraint_definition
                FROM
                    pg_constraint c
                JOIN
                    pg_namespace n ON n.oid = c.connamespace
                WHERE
                    n.nspname = 'public'
                    AND contype IN ('p', 'u')
                    AND conrelid = 'stock_candle_history'::regclass
            """)
            constraints = cur.fetchall()
            f.write("\n--- CONSTRAINTS ---\n")
            for con in constraints:
                f.write(f"Name: {con[0]}, Def: {con[1]}\n")
            
        conn.close()
        print("Schema written to backend/etl/schema_output.txt")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_table_schema()
