import yfinance as yf

def main():
    print("Fetching active option expiries from Yahoo Finance...")
    try:
        # RELIANCE
        reliance = yf.Ticker("RELIANCE.NS")
        print("\nRELIANCE.NS option expiries:")
        print(reliance.options)
        
        # NIFTY 50
        nifty = yf.Ticker("^NSEI")
        print("\n^NSEI (Nifty 50) option expiries:")
        print(nifty.options)
        
        # BANKNIFTY
        banknifty = yf.Ticker("^NSEBANK")
        print("\n^NSEBANK (Bank Nifty) option expiries:")
        print(banknifty.options)
        
    except Exception as e:
        print(f"Error fetching option expiries: {e}")

if __name__ == "__main__":
    main()
