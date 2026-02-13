import psycopg2

def check_schema():
    try:
        conn = psycopg2.connect('postgresql://postgres:admin@localhost:5432/quantai')
        cur = conn.cursor()
        
        # Check columns
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'parquet_load_audit'")
        cols = [r[0] for r in cur.fetchall()]
        print(f"Columns: {cols}")
        
        # Check constraints
        cur.execute("SELECT constraint_name FROM information_schema.table_constraints WHERE table_name = 'parquet_load_audit' AND constraint_type = 'UNIQUE'")
        constraints = [r[0] for r in cur.fetchall()]
        print(f"Unique Constraints: {constraints}")
        
        # If uq_batch is missing, add it
        if 'uq_batch' not in constraints:
            print("Adding unique constraint 'uq_batch' (symbol, timeframe, year, month)...")
            try:
                cur.execute("ALTER TABLE parquet_load_audit ADD CONSTRAINT uq_batch UNIQUE (symbol, timeframe, year, month)")
                conn.commit()
                print("Constraint added successfully.")
            except Exception as e:
                print(f"Failed to add constraint: {e}")
                conn.rollback()

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
