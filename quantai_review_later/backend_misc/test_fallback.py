import yfinance as yf

def test_yfinance():
    symbols = ["BAJFINANCE.NS", "BAJFINANCE.BO", "RELIANCE.NS"]
    for ticker in symbols:
        try:
            stock = yf.Ticker(ticker)
            price = stock.history(period="1d")['Close'].iloc[-1]
            print(f"{ticker}: {price}")
        except Exception as e:
            print(f"{ticker}: Error {e}")

if __name__ == "__main__":
    test_yfinance()
