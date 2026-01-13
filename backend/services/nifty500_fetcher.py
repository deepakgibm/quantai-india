"""
Nifty 500 Symbol Fetcher
Fetches Nifty 500 stock list from NSE India website.
"""

import requests
import pandas as pd
from typing import List, Tuple
from datetime import datetime
from sqlalchemy import Column, String, DateTime, create_engine
from sqlalchemy.orm import sessionmaker
from database import Base


class Nifty500Symbol(Base):
    """Database model for Nifty 500 symbols."""
    __tablename__ = "nifty500_symbols"
    
    symbol = Column(String(50), primary_key=True)
    company_name = Column(String(200))
    industry = Column(String(100))
    isin = Column(String(20))
    instrument_key = Column(String(50))  # Upstox instrument key
    last_updated = Column(DateTime, default=datetime.now)


class Nifty500Fetcher:
    """
    Fetches Nifty 500 stock list from NSE India.
    """
    
    NSE_NIFTY500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    
    # Headers to mimic browser request
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }
    
    def __init__(self):
        from config import settings
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
    
    def fetch_from_nse(self) -> pd.DataFrame:
        """
        Fetch Nifty 500 list from NSE website.
        
        Returns:
            DataFrame with columns: Symbol, Company Name, Industry, ISIN
        """
        print("📥 Fetching Nifty 500 list from NSE...")
        
        try:
            response = requests.get(self.NSE_NIFTY500_URL, headers=self.HEADERS, timeout=30)
            response.raise_for_status()
            
            # Parse CSV
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            print(f"✅ Retrieved {len(df)} stocks from NSE")
            return df
            
        except Exception as e:
            print(f"❌ Error fetching from NSE: {e}")
            # Fallback to alternative source
            return self._fetch_fallback()
    
    def _fetch_fallback(self) -> pd.DataFrame:
        """Fallback: Try alternative NSE endpoint."""
        try:
            alt_url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500"
            session = requests.Session()
            
            # First hit main page to get cookies
            session.get("https://www.nseindia.com", headers=self.HEADERS, timeout=10)
            
            # Then get data
            response = session.get(alt_url, headers=self.HEADERS, timeout=30)
            data = response.json()
            
            stocks = data.get("data", [])
            df = pd.DataFrame([{
                "Symbol": s["symbol"],
                "Company Name": s.get("meta", {}).get("companyName", s["symbol"]),
                "Industry": s.get("meta", {}).get("industry", ""),
                "ISIN Code": s.get("meta", {}).get("isin", "")
            } for s in stocks if s["symbol"] != "NIFTY 500"])
            
            print(f"✅ Retrieved {len(df)} stocks from NSE API (fallback)")
            return df
            
        except Exception as e:
            print(f"❌ Fallback also failed: {e}")
            return pd.DataFrame()
    
    def get_instrument_key(self, symbol: str, isin: str) -> str:
        """
        Generate Upstox instrument key from ISIN.
        Format: NSE_EQ|<ISIN>
        """
        if isin:
            return f"NSE_EQ|{isin}"
        return f"NSE_EQ|{symbol}"
    
    def save_to_database(self, df: pd.DataFrame) -> int:
        """
        Save Nifty 500 symbols to database.
        
        Returns:
            Number of symbols saved
        """
        print("💾 Saving to database...")
        
        # Ensure table exists
        Base.metadata.create_all(self._engine)
        
        session = self._Session()
        try:
            saved = 0
            for _, row in df.iterrows():
                symbol = row.get("Symbol", "").strip()
                if not symbol:
                    continue
                
                company_name = row.get("Company Name", symbol)
                industry = row.get("Industry", "")
                isin = row.get("ISIN Code", "") or row.get("ISIN", "")
                
                # Upsert
                existing = session.query(Nifty500Symbol).filter_by(symbol=symbol).first()
                if existing:
                    existing.company_name = company_name
                    existing.industry = industry
                    existing.isin = isin
                    existing.instrument_key = self.get_instrument_key(symbol, isin)
                    existing.last_updated = datetime.now()
                else:
                    new_symbol = Nifty500Symbol(
                        symbol=symbol,
                        company_name=company_name,
                        industry=industry,
                        isin=isin,
                        instrument_key=self.get_instrument_key(symbol, isin),
                        last_updated=datetime.now()
                    )
                    session.add(new_symbol)
                saved += 1
            
            session.commit()
            print(f"✅ Saved {saved} symbols to database")
            return saved
            
        except Exception as e:
            print(f"❌ Error saving to database: {e}")
            session.rollback()
            return 0
        finally:
            session.close()
    
    def get_all_symbols(self) -> List[Tuple[str, str]]:
        """
        Get all Nifty 500 symbols from database.
        
        Returns:
            List of (symbol, instrument_key) tuples
        """
        session = self._Session()
        try:
            symbols = session.query(Nifty500Symbol).all()
            return [(s.symbol, s.instrument_key) for s in symbols]
        finally:
            session.close()

    def fetch_nifty_500(self) -> List[Nifty500Symbol]:
        """
        Get all Nifty 500 symbol objects from database.
        """
        session = self._Session()
        try:
            return session.query(Nifty500Symbol).all()
        finally:
            session.close()
    
    def refresh(self) -> int:
        """
        Fetch from NSE and save to database.
        
        Returns:
            Number of symbols saved
        """
        df = self.fetch_from_nse()
        if df.empty:
            print("⚠️ No data fetched")
            return 0
        return self.save_to_database(df)


# CLI interface
if __name__ == "__main__":
    import sys
    
    fetcher = Nifty500Fetcher()
    
    if len(sys.argv) > 1 and sys.argv[1] == "refresh":
        count = fetcher.refresh()
        print(f"\n📊 Total symbols: {count}")
    else:
        # Just fetch and display
        df = fetcher.fetch_from_nse()
        if not df.empty:
            print("\n📋 Sample symbols:")
            print(df.head(10).to_string())
            print(f"\n📊 Total: {len(df)} stocks")
