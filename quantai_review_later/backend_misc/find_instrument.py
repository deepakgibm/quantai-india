import gzip
import json

def find_bajfinance():
    try:
        with gzip.open('instruments.json.gz', 'rb') as f:
            instruments = json.load(f)
            
        print(f"Total instruments: {len(instruments)}")
        
        with open('bajfinance_matches.txt', 'w') as out:
            for instr in instruments:
                # Search by name as well
                if 'BAJFINANCE' == instr.get('trading_symbol', '') and instr.get('segment') == 'NSE_EQ':
                    out.write(f"Found Match: {json.dumps(instr, indent=2)}\n")
        print("Done writing matches to bajfinance_matches.txt")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_bajfinance()
