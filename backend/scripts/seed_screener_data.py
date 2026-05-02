import sys
import os
from datetime import datetime, date

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from screener.models import ScreenerFinancials, ScreenerHoldingsHistory
from sqlalchemy import text

def seed():
    session = SessionLocal()
    try:
        # 1. Clear existing financials for these stocks
        symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "BHEL"]
        session.execute(text("DELETE FROM screener_financials WHERE symbol IN :s"), {"s": tuple(symbols)})
        
        print("Seeding financials...")
        
        # RELIANCE
        rel = ScreenerFinancials(
            symbol="RELIANCE",
            period_type="quarterly",
            period_end=date(2023, 12, 31),
            updated_at=datetime.now(),
            market_cap=1800000.0,
            pe_ratio=25.4,
            revenue_growth_yoy=12.5,
            profit_growth_yoy=15.2,
            ebitda_margin=18.5,
            roe=14.0,
            roce=13.0,
            debt_to_equity=0.4,
            interest_coverage=8.5,
            sales_cagr_3y=14.0,
            profit_cagr_3y=12.0
        )
        session.add(rel)
        
        # BHEL
        bhel = ScreenerFinancials(
            symbol="BHEL",
            period_type="quarterly",
            period_end=date(2023, 12, 31),
            updated_at=datetime.now(),
            market_cap=80000.0,
            pe_ratio=45.0,
            revenue_growth_yoy=22.0,
            profit_growth_yoy=35.0,
            ebitda_margin=12.0,
            roe=8.0,
            roce=10.0,
            debt_to_equity=0.2,
            interest_coverage=5.0,
            sales_cagr_3y=18.0,
            profit_cagr_3y=25.0
        )
        session.add(bhel)
        
        # TCS
        tcs = ScreenerFinancials(
            symbol="TCS",
            period_type="quarterly",
            period_end=date(2023, 12, 31),
            updated_at=datetime.now(),
            market_cap=1400000.0,
            pe_ratio=30.0,
            revenue_growth_yoy=10.0,
            profit_growth_yoy=12.0,
            ebitda_margin=26.0,
            roe=45.0,
            roce=50.0,
            debt_to_equity=0.0,
            interest_coverage=50.0,
            sales_cagr_3y=12.0,
            profit_cagr_3y=11.0
        )
        session.add(tcs)
        
        print("Seeding holdings history...")
        session.execute(text("DELETE FROM screener_holdings_history WHERE symbol IN :s"), {"s": tuple(symbols)})
        
        # Simple holdings history for RELIANCE
        dates = [date(2023, 12, 31), date(2023, 9, 30), date(2023, 6, 30), date(2023, 3, 31)]
        for d in dates:
            h = ScreenerHoldingsHistory(
                symbol="RELIANCE",
                quarter_end=d,
                promoter_pct=50.3,
                fii_pct=23.4,
                dii_pct=15.2,
                promoter_pledge_pct=0.0
            )
            session.add(h)
            
        # For BHEL (ensure it has high promoter holding)
        h_bhel = ScreenerHoldingsHistory(
            symbol="BHEL",
            quarter_end=date(2023, 12, 31),
            promoter_pct=63.17,
            fii_pct=8.5,
            dii_pct=18.2,
            promoter_pledge_pct=0.0
        )
        session.add(h_bhel)

        # For TCS
        h_tcs = ScreenerHoldingsHistory(
            symbol="TCS",
            quarter_end=date(2023, 12, 31),
            promoter_pct=72.3,
            fii_pct=12.5,
            dii_pct=9.8,
            promoter_pledge_pct=0.0
        )
        session.add(h_tcs)
            
        session.commit()
        print("Seeding complete!")
        
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    seed()
