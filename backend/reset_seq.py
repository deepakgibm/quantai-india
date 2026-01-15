
import psycopg2
try:
    conn = psycopg2.connect("postgresql://postgres:admin@localhost:5432/quantai")
    cur = conn.cursor()
    # Find the sequence name
    cur.execute("SELECT pg_get_serial_sequence('nifty100_daily', 'id')")
    seq_name = cur.fetchone()[0]
    print(f"Sequence name: {seq_name}")
    
    # Reset it
    cur.execute(f"SELECT setval('{seq_name}', (SELECT MAX(id) FROM nifty100_daily)+1)")
    new_val = cur.fetchone()[0]
    conn.commit()
    print(f"Sequence reset to: {new_val}")
except Exception as e:
    print(f"Error: {e}")
