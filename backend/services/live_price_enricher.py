"""
Live Price Enrichment Service
Fetches real-time prices from Upstox and enriches scanner results.
Falls back to Yahoo Finance for unmapped symbols.
"""

import requests
from typing import List, Dict, Optional
from urllib.parse import quote
from config import settings

# Import comprehensive Nifty 500 mapping
from data.nifty500_instruments import NIFTY_500_MAPPING

# Use the comprehensive mapping (300+ Nifty 500 stocks)
INSTRUMENT_MAPPING = NIFTY_500_MAPPING


def get_yfinance_price(symbol: str) -> Optional[float]:
    """Fallback to Yahoo Finance for symbols not in Upstox mapping."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.info
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        if price and price > 0:
            return float(price)
    except Exception as e:
        print(f"⚠️ yFinance fallback failed for {symbol}: {e}")
    return None


def get_instrument_key(symbol: str) -> Optional[str]:
    """Get Upstox instrument key for a symbol, returns None if not found."""
    return INSTRUMENT_MAPPING.get(symbol.upper())


def fetch_live_ltp(symbols: List[str], access_token: str = None) -> Dict[str, float]:
    """
    Fetch live LTP (Last Traded Price) for multiple symbols from Upstox.
    
    Args:
        symbols: List of stock symbols
        access_token: Upstox access token
        
    Returns:
        Dict mapping symbol -> live price
    """
    if not access_token:
        access_token = settings.UPSTOX_ACCESS_TOKEN
    
    if not access_token:
        print("⚠️ No Upstox access token available for live prices")
        return {}
    
    prices = {}
    
    # Fetch in batches of 10 (Upstox API limit)
    batch_size = 10
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        batch_prices = _fetch_batch_ltp(batch, access_token)
        prices.update(batch_prices)
    
    return prices


def _fetch_batch_ltp(symbols: List[str], access_token: str) -> Dict[str, float]:
    """Fetch LTP for a batch of symbols. Falls back to yFinance for unmapped symbols."""
    prices = {}
    
    for symbol in symbols:
        try:
            inst_key = get_instrument_key(symbol)
            
            # If symbol not in mapping, try yFinance fallback
            if inst_key is None:
                print(f"⚠️ {symbol} not in mapping, trying yFinance...")
                yf_price = get_yfinance_price(symbol)
                if yf_price and yf_price > 0:
                    prices[symbol] = yf_price
                    print(f"📈 {symbol}: ₹{yf_price:,.2f} (yFinance)")
                continue
            
            # Try Upstox API
            encoded_key = quote(inst_key, safe='')
            url = f"https://api.upstox.com/v2/market-quote/ltp?instrument_key={encoded_key}"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and data.get("data"):
                    for key, quote_data in data["data"].items():
                        ltp = quote_data.get("last_price")
                        if ltp and ltp > 0:
                            prices[symbol] = ltp
                            print(f"📈 {symbol}: ₹{ltp:,.2f}")
            else:
                # Upstox failed, try yFinance
                yf_price = get_yfinance_price(symbol)
                if yf_price and yf_price > 0:
                    prices[symbol] = yf_price
                    print(f"📈 {symbol}: ₹{yf_price:,.2f} (yFinance fallback)")
                    
        except Exception as e:
            print(f"⚠️ Error fetching {symbol}: {e}")
            # Try yFinance as last resort
            try:
                yf_price = get_yfinance_price(symbol)
                if yf_price and yf_price > 0:
                    prices[symbol] = yf_price
                    print(f"📈 {symbol}: ₹{yf_price:,.2f} (yFinance fallback)")
            except:
                pass
    
    return prices


def enrich_scanner_results(results: List[Dict], access_token: str = None) -> List[Dict]:
    """
    Enrich scanner results with live prices from Upstox.
    
    Updates current_price, entry_price, target_price, and stop_loss
    based on real-time LTP instead of database close prices.
    
    Args:
        results: List of scanner result dictionaries
        access_token: Upstox access token
        
    Returns:
        Enriched results with live prices
    """
    if not results:
        return results
    
    # Get unique symbols
    symbols = list(set(r.get("symbol") for r in results if r.get("symbol")))
    
    print(f"🔄 Fetching live prices for {len(symbols)} symbols...")
    live_prices = fetch_live_ltp(symbols, access_token)
    
    if not live_prices:
        print("⚠️ No live prices available, using database prices")
        return results
    
    print(f"✅ Got live prices for {len(live_prices)} symbols")
    
    # Enrich each result
    enriched = []
    for result in results:
        symbol = result.get("symbol")
        live_price = live_prices.get(symbol)
        
        if live_price and live_price > 0:
            # Create a copy with updated prices
            enriched_result = result.copy()
            old_price = enriched_result.get("current_price", 0)
            enriched_result["current_price"] = round(live_price, 2)
            
            # Log significant price changes
            if old_price > 0:
                change_pct = ((live_price - old_price) / old_price) * 100
                if abs(change_pct) > 1:
                    print(f"📊 {symbol}: DB ₹{old_price:,.2f} → Live ₹{live_price:,.2f} ({change_pct:+.2f}%)")
            
            # Recalculate trade levels based on live price
            trend = enriched_result.get("trend", "BULLISH")
            action = enriched_result.get("action", "BUY")
            
            if trend == "BULLISH" or action == "BUY":
                enriched_result["entry_price"] = round(live_price * 0.995, 2)  # 0.5% below
                enriched_result["target_price"] = round(live_price * 1.05, 2)  # 5% target
                enriched_result["stop_loss"] = round(live_price * 0.97, 2)  # 3% stop
            else:
                enriched_result["entry_price"] = round(live_price * 1.005, 2)
                enriched_result["target_price"] = round(live_price * 0.95, 2)
                enriched_result["stop_loss"] = round(live_price * 1.03, 2)
            
            enriched.append(enriched_result)
        else:
            # Keep original if no live price
            enriched.append(result)
    
    return enriched


def get_single_live_price(symbol: str, access_token: str = None) -> Optional[float]:
    """Get live price for a single symbol."""
    prices = fetch_live_ltp([symbol], access_token)
    return prices.get(symbol)
