import yfinance as yf
try:
    ticker = yf.Ticker("MANAPPURAM.NS")
    info = ticker.info
    print(f"YF_CURRENT: {info.get('currentPrice')}")
    print(f"YF_REGULAR: {info.get('regularMarketPrice')}")
    print(f"YF_PREV_CLOSE: {info.get('previousClose')}")
except Exception as e:
    print(f"YF_ERROR: {e}")
