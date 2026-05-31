import requests
import gzip
import io
import pandas as pd

def main():
    url = "https://files.upstox.com/complete.csv.gz"
    print(f"Downloading instrument master from: {url}")
    try:
        response = requests.get(url, stream=True, timeout=15)
        print(f"Response status: {response.status_code}")
        if response.status_code != 200:
            print("Failed to download file")
            return
            
        content = response.raw.read()
        print(f"Downloaded {len(content)} bytes of gzip data")
        
        # Decompress gzip data
        with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
            df = pd.read_csv(f)
            
        print(f"Loaded dataframe of shape: {df.shape}")
        print("Columns:", list(df.columns))
        
        # Check distinct instrument_type or segment or exchange
        print("\nDistinct segment types:")
        print(df['segment'].value_counts() if 'segment' in df.columns else "segment column missing")
        
        # Filter for NIFTY options and print a sample
        print("\nNIFTY Option samples:")
        nifty_opts = df[(df['name'] == 'NIFTY') & (df['instrument_type'] == 'OPTIDX')] if 'instrument_type' in df.columns else df[df['tradingsymbol'].str.contains('NIFTY', na=False) & df['tradingsymbol'].str.endswith(('CE', 'PE'), na=False)]
        print(nifty_opts[['tradingsymbol', 'expiry', 'strike', 'instrument_key']].head(10))
        
        # Print unique expiries for NIFTY options
        print("\nUnique expiries for NIFTY Options:")
        print(sorted(nifty_opts['expiry'].dropna().unique())[:10])
        
        # Filter for RELIANCE options and print a sample
        print("\nRELIANCE Option samples:")
        rel_opts = df[(df['name'] == 'RELIANCE') & (df['instrument_type'] == 'OPTSTK')] if 'instrument_type' in df.columns else df[df['tradingsymbol'].str.contains('RELIANCE', na=False) & df['tradingsymbol'].str.endswith(('CE', 'PE'), na=False)]
        print(rel_opts[['tradingsymbol', 'expiry', 'strike', 'instrument_key']].head(10))
        
        # Print unique expiries for RELIANCE options
        print("\nUnique expiries for RELIANCE Options:")
        print(sorted(rel_opts['expiry'].dropna().unique())[:10])
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
