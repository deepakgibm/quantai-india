"""
F&O Stocks Data Module
List of NSE stocks that have derivatives (Futures & Options) available.
"""

# All stocks available in NSE F&O segment (as of Dec 2024)
FNO_STOCKS = {
    # Nifty 50 - All have derivatives
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC",
    "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
    "BAJFINANCE", "TITAN", "SUNPHARMA", "ULTRACEMCO", "HCLTECH", "WIPRO",
    "NTPC", "POWERGRID", "JSWSTEEL", "M&M", "TATASTEEL", "ADANIENT", "ADANIPORTS",
    "ONGC", "BPCL", "COALINDIA", "GRASIM", "TECHM", "INDUSINDBK", "HINDALCO",
    "DRREDDY", "CIPLA", "DIVISLAB", "BRITANNIA", "APOLLOHOSP", "BAJAJFINSV",
    "NESTLEIND", "EICHERMOT", "HEROMOTOCO", "TATACONSUM", "SHRIRAMFIN", "BEL",
    "SBILIFE", "HDFCLIFE", "TRENT", "BAJAJ-AUTO",
    
    # Nifty Next 50 - F&O available
    "ABB", "ADANIGREEN", "AMBUJACEM", "AUROPHARMA", "BANKBARODA", "BERGEPAINT",
    "BOSCHLTD", "CANBK", "CHOLAFIN", "COLPAL", "DLF", "DABUR", "GAIL", "GODREJCP",
    "HAVELLS", "ICICIPRULI", "ICICIGI", "INDHOTEL", "INDUSTOWER", "JIOFIN",
    "JINDALSTEL", "LICI", "LUPIN", "MARICO", "MOTHERSON", "NAUKRI", "NHPC",
    "NMDC", "OBEROIRLTY", "OFSS", "PAGEIND", "PERSISTENT", "PETRONET", "PFC",
    "PIDILITIND", "PNB", "POLYCAB", "RECLTD", "SBICARD", "SHREECEM", "SIEMENS",
    "SRF", "TATAMOTORS", "TATAPOWER", "TORNTPHARM", "TVSMOTOR", "VEDL", "ZOMATO",
    
    # Other F&O stocks
    "ACC", "ALKEM", "ASHOKLEY", "ASTRAL", "AUBANK", "BANDHANBNK", "BATAINDIA",
    "BHEL", "BIOCON", "CANFINHOME", "COFORGE", "COROMANDEL", "CROMPTON",
    "CUB", "DALBHARAT", "DEEPAKNTR", "DIXON", "ESCORTS", "EXIDEIND",
    "FEDERALBNK", "FORTIS", "GLENMARK", "GMRINFRA", "GNFC", "GODREJPROP",
    "GRANULES", "GUJGASLTD", "HAL", "HDFCAMC", "HONAUT", "IDFCFIRSTB", "IEX",
    "INDIANB", "INDIGO", "IRCTC", "IRFC", "IGL", "JKCEMENT", "JSWENERGY",
    "JUBLFOOD", "KEI", "KPITTECH", "LAURUSLABS", "LICHSGFIN", "LTIM", "LTTS",
    "M&MFIN", "MANAPPURAM", "MCDOWELL-N", "MCX", "METROPOLIS", "MFSL", "MGL",
    "MPHASIS", "MUTHOOTFIN", "NAM-INDIA", "NATIONALUM", "NAVINFLUOR", "NBCC",
    "NCC", "OIL", "PAYTM", "PIIND", "POLYPLEX", "PRESTIGE", "PVRINOX",
    "RAIN", "RAMCOCEM", "RBLBANK", "RELAXO", "RVNL", "SAIL", "SJVN",
    "SONACOMS", "STAR", "SUNTV", "SYNGENE", "TATACHEM", "TATACOMM", "TATAELXSI",
    "TIINDIA", "TORNTPOWER", "TRIDENT", "UBL", "UJJIVANSFB", "UPL", "VBL",
    "VOLTAS", "YESBANK", "ZEEL", "ZYDUSLIFE",
    
    # Index derivatives
    "NIFTY", "BANKNIFTY", "FINNIFTY", "NIFTYNXT50",
}


def has_derivatives(symbol: str) -> bool:
    """
    Check if a stock symbol has F&O (Futures & Options) available.
    
    Args:
        symbol: NSE stock symbol (e.g., "RELIANCE", "TCS")
        
    Returns:
        True if the stock has derivatives available, False otherwise
    """
    # Clean symbol - remove any exchange prefix
    clean_symbol = symbol.upper().replace("NSE:", "").strip()
    return clean_symbol in FNO_STOCKS


def get_fno_stocks() -> list:
    """Get list of all F&O stocks."""
    return sorted(list(FNO_STOCKS))


def is_index(symbol: str) -> bool:
    """Check if symbol is an index."""
    indices = {"NIFTY", "BANKNIFTY", "FINNIFTY", "NIFTYNXT50", "NIFTY 50", "BANK NIFTY"}
    return symbol.upper().replace("_", " ") in indices
