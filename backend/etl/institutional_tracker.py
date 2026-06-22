import logging
import asyncio
import random
from datetime import datetime, date, timedelta
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from models import InstitutionalFlows
from database import get_db

logger = logging.getLogger(__name__)

# Institutional identification tokens
DII_KEYWORDS = [
    "LIFE INSURANCE CORPORATION", "HDFC MUTUAL FUND", "ICICI PRUDENTIAL", 
    "SBI MUTUAL FUND", "AXIS MUTUAL FUND", "KOTAK MUTUAL FUND", 
    "NIPPON LIFE", "UTI MUTUAL FUND", "MIRAE ASSET", "DSP MUTUAL FUND",
    "TATA MUTUAL FUND", "INFRASTRUCTURE LEASING", "EDELWEISS"
]

FII_KEYWORDS = [
    "MORGAN STANLEY", "GOLDMAN SACHS", "SOCIETE GENERALE", 
    "BANK OF AMERICA", "NOMURA", "JPMORGAN", "BNP PARIBAS", 
    "CITIGROUP", "MERRILL LYNCH", "BARRON", "VANGUARD",
    "FIDELITY", "BLACKROCK", "UBS AG", "CREDIT SUISSE"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
]

class InstitutionalFlowTracker:
    """
    Tracks and categorizes Institutional Flows (FII/DII) in the Indian Market.
    Parses Bulk and Block deal data with production-grade persistence.
    """
    
    _shared_session: Any = None # Shared session across instances to maintain cookies
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
    def _categorize_client(self, client_name: str) -> str:
        """Categorize client as FII, DII, or HNI based on keywords."""
        name_upper = client_name.upper()
        
        for kw in DII_KEYWORDS:
            if kw in name_upper:
                return "DII"
                
        for kw in FII_KEYWORDS:
            if kw in name_upper:
                return "FII"
                
        if "FUND" in name_upper or "TRUST" in name_upper:
            return "DII"
            
        return "HNI"

    async def _get_client(self):
        """Returns or creates a persistent httpx client with NSE session."""
        import httpx
        if InstitutionalFlowTracker._shared_session is None:
            InstitutionalFlowTracker._shared_session = httpx.AsyncClient(
                headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.nseindia.com/report-detail/display-bulk-and-block-deals",
                    "Source": "NSE_WEBSITE"
                },
                follow_redirects=True,
                timeout=30
            )
            # Bootstrapping session by visiting home page
            try:
                await InstitutionalFlowTracker._shared_session.get("https://www.nseindia.com/", timeout=10)
                # Small delay to mimic human behavior
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Failed to bootstrap NSE session: {e}")
                InstitutionalFlowTracker._shared_session = None
                return None
        return InstitutionalFlowTracker._shared_session

    async def fetch_deals(self, target_date: date = None, deal_type: str = "bulk") -> int:
        """
        Fetches official deals from NSE Website.
        deal_type: 'bulk' or 'block'
        """
        if target_date is None:
            target_date = date.today()
            
        logger.info(f"Fetching {deal_type} deals for {target_date}")
        client = await self._get_client()
        if not client: return 0
        
        endpoint = "live-analysis-bulk-deals" if deal_type == "bulk" else "live-analysis-block-deals"
        url = f"https://www.nseindia.com/api/{endpoint}"
        
        try:
            response = await client.get(url)
            if response.status_code != 200:
                logger.error(f"NSE {deal_type} fetch failed (Status {response.status_code}). Clearing session.")
                InstitutionalFlowTracker._shared_session = None # Reset session for retry
                return 0
            
            data = response.json()
            raw_deals = data.get("data", [])
            
            target_str = target_date.strftime("%d-%b-%Y")
            count = 0
            
            for deal in raw_deals:
                if target_date and deal.get("date") != target_str:
                    continue
                
                symbol = deal.get("symbol")
                client_name = deal.get("clientName", "UNKNOWN")
                qty = int(str(deal.get("quantityTraded", "0")).replace(",", ""))
                price = float(str(deal.get("tradePrice", "0")).replace(",", ""))
                
                if qty == 0: continue

                flow = InstitutionalFlows(
                    symbol=symbol,
                    deal_date=datetime.combine(target_date, datetime.min.time()),
                    client_name=client_name,
                    deal_type=deal.get("type", "BUY"), # BUY/SELL
                    quantity=qty,
                    price=price,
                    flow_category=self._categorize_client(client_name)
                )
                self.db.add(flow)
                count += 1
            
            await self.db.commit()
            logger.info(f"Ingested {count} {deal_type} deal(s) for {symbol if count==1 else 'multiple symbols'}")
            return count
                
        except Exception as e:
            logger.error(f"Error in NSE Ingestion ({deal_type}): {e}")
            return 0

async def run_institutional_sync():
    """Celery task entry point."""
    async for db in get_db():
        tracker = InstitutionalFlowTracker(db)
        # Fetch both bulk and block deals for yesterday and today
        yest = date.today() - timedelta(days=1)
        today = date.today()
        
        await tracker.fetch_deals(yest, "bulk")
        await tracker.fetch_deals(yest, "block")
        await tracker.fetch_deals(today, "bulk")
        await tracker.fetch_deals(today, "block")
        break
