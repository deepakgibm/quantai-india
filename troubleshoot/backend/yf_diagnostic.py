import yfinance as yf
import json

def check():
    try:
        ticker = yf.Ticker("MANAPPURAM.NS")
        info = ticker.info
        result = {
            "currentPrice": info.get("currentPrice"),
            "regularMarketPrice": info.get("regularMarketPrice"),
            "previousClose": info.get("previousClose"),
            "ask": info.get("ask"),
            "bid": info.get("bid")
        }
        print(f"YFINANCE_RESULT: {json.dumps(result)}")
    except Exception as e:
        print(f"YFINANCE_ERROR: {str(e)}")

if __name__ == "__main__":
    check()
