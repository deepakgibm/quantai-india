"""Quick test to debug market indices fetching with 2d period"""
import yfinance as yf

symbols = {
    'NIFTY 50': '^NSEI',
    'BANK NIFTY': '^NSEBANK',
    'INDIA VIX': '^INDIAVIX'
}

print("Testing yfinance fetch with period='2d':\n")
for name, sym in symbols.items():
    try:
        ticker = yf.Ticker(sym)
        hist = ticker.history(period='2d')
        print(f"{name} ({sym}):")
        print(f"  Data rows: {len(hist)}")
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            curr_value = hist['Close'].iloc[-1]
            change = round(curr_value - prev_close, 2)
            percent = round((change / prev_close) * 100, 2)
            print(f"  Current: {round(curr_value, 2)}")
            print(f"  Prev Close: {round(prev_close, 2)}")
            print(f"  Change: {change}")
            print(f"  Percent: {percent}%")
        elif len(hist) == 1:
            curr = hist['Close'].iloc[-1]
            print(f"  Only 1 row - Current: {round(curr, 2)}")
            print(f"  PROBLEM: Cannot calculate change with only 1 day of data!")
        else:
            print(f"  No data returned!")
        print()
    except Exception as e:
        print(f"{name}: Error - {e}")
        print()
