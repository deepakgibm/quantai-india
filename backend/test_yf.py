import sys
sys.path.append("/app")

from screener.data.financial_data_fetcher import FinancialDataFetcher
import logging

logging.basicConfig(level=logging.INFO)

def test():
    fetcher = FinancialDataFetcher()
    symbol = "RELIANCE"
    print(f"Fetching data for {symbol}...")
    data = fetcher.fetch_financials(symbol)
    print(f"Data Available: {data.get('data_available')}")
    print(f"Error: {data.get('error')}")
    if data.get('data_available'):
        print(f"CMP: {data.get('cmp')}")
        print(f"MCap: {data.get('market_cap_cr')}")
        print(f"Promoter: {data.get('promoter_holding')}")

if __name__ == "__main__":
    test()
