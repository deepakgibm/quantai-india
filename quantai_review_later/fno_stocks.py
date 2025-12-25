"""
F&O Eligible Stocks List for NSE India

This module contains the master list of stocks that are eligible for
Futures & Options trading on NSE. Stocks in this list have derivatives
available (options/futures).

Updated: December 2024
Source: NSE India F&O segment
"""

# Complete list of F&O eligible stocks on NSE (200+ stocks)
FNO_STOCKS = {
    # Nifty 50 Constituents (All F&O eligible)
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC",
    "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
    "BAJFINANCE", "TITAN", "SUNPHARMA", "ULTRACEMCO", "HCLTECH", "WIPRO",
    "NTPC", "POWERGRID", "JSWSTEEL", "M&M", "TATASTEEL", "ADANIENT", "ADANIPORTS",
    "ONGC", "BPCL", "COALINDIA", "GRASIM", "TECHM", "INDUSINDBK", "HINDALCO",
    "DRREDDY", "CIPLA", "DIVISLAB", "BRITANNIA", "APOLLOHOSP", "BAJAJFINSV",
    "NESTLEIND", "EICHERMOT", "HEROMOTOCO", "TATACONSUM", "SHRIRAMFIN", "BEL",
    "SBILIFE", "HDFCLIFE", "TRENT", "BAJAJ-AUTO",
    
    # Nifty Next 50 F&O Stocks
    "ABB", "ADANIGREEN", "AMBUJACEM", "AUROPHARMA", "BANKBARODA", "BERGEPAINT",
    "BOSCHLTD", "CANBK", "CHOLAFIN", "COLPAL", "CONCOR", "CUMMINSIND", "DLF",
    "DABUR", "GAIL", "GODREJCP", "HAVELLS", "HINDPETRO", "ICICIPRULI", "ICICIGI",
    "INDHOTEL", "INDUSTOWER", "JIOFIN", "JINDALSTEL", "LICI", "LUPIN", "MARICO",
    "MOTHERSON", "NAUKRI", "NHPC", "NMDC", "OBEROIRLTY", "OFSS", "PAGEIND",
    "PERSISTENT", "PETRONET", "PFC", "PIDILITIND", "PNB", "POLYCAB", "RECLTD",
    "SBICARD", "SHREECEM", "SIEMENS", "SOLARINDS", "SRF", "TATAMOTORS", "TATAPOWER",
    "TORNTPHARM", "TVSMOTOR", "UNIONBANK", "VEDL", "ZOMATO", "ZYDUSLIFE",
    
    # Other Popular F&O Stocks
    "ACC", "ALKEM", "ASHOKLEY", "ASTRAL", "ATGL", "ATUL", "AUBANK", "AUROPHARMA",
    "BALRAMCHIN", "BANDHANBNK", "BATAINDIA", "BHEL", "BIOCON", "CANFINHOME", 
    "CESC", "CGPOWER", "CHAMBLFERT", "COFORGE", "COROMANDEL", "CROMPTON",
    "CUB", "DALBHARAT", "DEEPAKNTR", "DELTACORP", "DIXON", "ESCORTS", "EXIDEIND",
    "FEDERALBNK", "FORTIS", "GLENMARK", "GMRINFRA", "GNFC", "GODREJPROP",
    "GRANULES", "GSPL", "GUJGASLTD", "HAL", "HDFCAMC", "HONAUT", "IDFCFIRSTB",
    "IEX", "INDIANB", "INDIGO", "IRCTC", "IRFC", "IGL", "JKCEMENT", "JSWENERGY",
    "JUBLFOOD", "KALYANKJIL", "KEI", "KPITTECH", "L&TFH", "LAURUSLABS", "LICHSGFIN",
    "LTIM", "LTTS", "M&MFIN", "MANAPPURAM", "MCDOWELL-N", "MCX", "METROPOLIS",
    "MFSL", "MGL", "MINDTREE", "MPHASIS", "MUTHOOTFIN", "NAM-INDIA", "NATIONALUM",
    "NAVINFLUOR", "NBCC", "NCC", "NIACL", "NMDC", "NOCIL", "NTPCL", "OBEROIRLTY",
    "OIL", "PAYTM", "PGHH", "POLICYBZR", "POLYPLEX", "PRESTIGE", "PVRINOX", 
    "RAIN", "RAJESHEXPO", "RAMCOCEM", "RBLBANK", "RECLTD", "RELAXO", "RVNL",
    "SAIL", "SBICARD", "SJVN", "SONACOMS", "STAR", "SUNTV", "SYNGENE",
    "TATACHEM", "TATACOMM", "TATAELXSI", "TATAMTRDVR", "TIINDIA", "TORNTPOWER",
    "TRIDENT", "UBL", "UJJIVANSFB", "UPL", "VBL", "VOLTAS", "YESBANK", "ZEEL",
    
    # Recently Added F&O Stocks (Nov 2024)
    "DMART", "JIOFIN", "BSE", "ANGELONE", "PATANJALI", "PHOENIXLTD", "SUPREMEIND",
    "SWANENERGY", "TITAGARH", "KARURVYSYA", "IONEXCHANG", "KRBL", "KFINTECH",
    "LLOYDSME", "LINDEINDIA", "LXCHEM", "MAHLIFE", "MAPMYINDIA", "MASTEK",
}


def has_derivatives(symbol: str) -> bool:
    """
    Check if a stock has derivatives (F&O) available on NSE.
    
    Args:
        symbol: Stock symbol (e.g., "RELIANCE", "TCS")
        
    Returns:
        True if the stock has F&O available, False otherwise
    """
    # Normalize symbol (uppercase, remove .NS suffix if present)
    normalized = symbol.upper().replace(".NS", "").strip()
    return normalized in FNO_STOCKS


def get_fno_stock_count() -> int:
    """Get the total count of F&O eligible stocks."""
    return len(FNO_STOCKS)


def get_fno_stocks_list() -> list:
    """Get sorted list of all F&O eligible stocks."""
    return sorted(list(FNO_STOCKS))
