import psycopg2
import re

def update_etl_script():
    try:
        # 1. Get completed symbols from DB
        conn = psycopg2.connect('postgresql://postgres:admin@localhost:5432/quantai')
        cur = conn.cursor()
        cur.execute("SELECT symbol FROM etl_job_status WHERE job_name = 'backfill_2022' AND status = 'COMPLETED' ORDER BY symbol")
        symbols = [r[0] for r in cur.fetchall()]
        conn.close()
        
        if not symbols:
            print("No completed symbols found in DB. Aborting.")
            return

        print(f"Found {len(symbols)} completed symbols in DB.")

        # 2. Read the script
        script_path = 'backend/etl/backfill_history_2022.py'
        with open(script_path, 'r') as f:
            content = f.read()

        # 3. Format the new symbol list
        # We'll format it with 10 symbols per line for readability
        new_list_str = "NIFTY_500_SYMBOLS = [\n"
        for i in range(0, len(symbols), 10):
            chunk = symbols[i:i+10]
            line = "    " + ", ".join(f'"{s}"' for s in chunk)
            if i + 10 < len(symbols):
                line += ","
            new_list_str += line + "\n"
        new_list_str += "]"

        # 4. Replace the old list using regex
        # Look for NIFTY_500_SYMBOLS = [ ... ]
        pattern = r"NIFTY_500_SYMBOLS = \[(?:.|\n)*?\]"
        new_content = re.sub(pattern, new_list_str, content)

        # 5. Write back
        with open(script_path, 'w') as f:
            f.write(new_content)
        
        print(f"Successfully updated {script_path} with {len(symbols)} symbols.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_etl_script()
