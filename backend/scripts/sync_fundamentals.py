import sys
import os
import asyncio
from datetime import datetime, timedelta
import urllib.parse
from sqlalchemy import text

# Add parent directory of scripts to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models_alpha import InstrumentMaster
from models import FundamentalMetrics
from services.upstox_client import get_upstox_client

# Log prefixes as requested
# [UPSTOX_COMPANY_PROFILE]
# [UPSTOX_FUNDAMENTALS]
# [UPSTOX_BALANCE_SHEET]
# [UPSTOX_COMPETITORS]
# [UPSTOX_NEWS]

async def sync_all_fundamentals(limit: int = None):
    print("[DATA_VALIDATION] Starting Upstox Fundamentals & Metadata Ingestion Engine...")
    db = SessionLocal()
    client = get_upstox_client()
    
    try:
        # Get active symbols that have daily candles
        sql = text("""
            SELECT DISTINCT im.instrument_id, im.symbol, im.isin_code, im.instrument_key
            FROM instrument_master im
            JOIN stock_candle sc ON im.instrument_id = sc.instrument_id
            WHERE im.is_active = TRUE AND sc.timeframe = 1440
            ORDER BY im.symbol
        """)
        
        result = db.execute(sql)
        instruments = [
            {"id": r.instrument_id, "symbol": r.symbol, "isin": r.isin_code, "key": r.instrument_key} 
            for r in result.fetchall()
        ]
        
        if limit:
            instruments = instruments[:limit]
            
        print(f"[DATA_VALIDATION] Found {len(instruments)} active instruments with candle data to sync.")
        
        synced = 0
        failed = 0
        
        for idx, inst in enumerate(instruments):
            symbol = inst["symbol"]
            isin = inst["isin"]
            inst_key = inst["key"]
            inst_id = inst["id"]
            
            if not isin or len(isin) != 12:
                print(f"[INSTRUMENT_MAPPING] [WARNING] Skipping {symbol} due to missing/invalid ISIN: {isin}")
                failed += 1
                continue
                
            print(f"\n[DATA_VALIDATION] [{idx+1}/{len(instruments)}] Syncing {symbol} (ISIN: {isin})...")
            
            try:
                # 0. Get Latest Close Price from DB for calculations
                price_sql = text("""
                    SELECT close FROM stock_candle 
                    WHERE instrument_id = :inst_id AND timeframe = 1440 
                    ORDER BY candle_ts DESC LIMIT 1
                """)
                price_res = db.execute(price_sql, {"inst_id": inst_id}).fetchone()
                latest_price = float(price_res[0]) if price_res else None
                
                if not latest_price or latest_price <= 0:
                    # Try to fetch live LTP from Upstox
                    quotes = await client.get_live_quotes([inst_key])
                    quote = quotes.get(inst_key) if quotes else None
                    latest_price = quote.get("last_price") if quote else None
                    
                if not latest_price or latest_price <= 0:
                    print(f"[DATA_VALIDATION] [WARNING] No close price found for {symbol}. Skipping ratios/yield calculations.")
                    latest_price = 0.0
                
                # 1. Company Profile API
                print(f"[UPSTOX_COMPANY_PROFILE] Fetching profile for {symbol}...")
                profile = await client._make_request("GET", f"/fundamentals/{isin}/profile")
                
                profile_data = profile.get("data", {}) if profile.get("status") == "success" else {}
                
                sector = profile_data.get("sector") or "Others"
                # sector_market_cap_inr contains company market cap in crore
                mcap_data = profile_data.get("sector_market_cap_inr") or {}
                mcap_crore = float(mcap_data.get("value") or 0.0)
                market_cap = mcap_crore * 10000000.0 # Convert to raw Rupees
                
                # 2. Key Ratios API
                print(f"[UPSTOX_FUNDAMENTALS] Fetching key ratios for {symbol}...")
                ratios = await client._make_request("GET", f"/fundamentals/{isin}/key-ratios")
                ratios_list = ratios.get("data", []) if ratios.get("status") == "success" else []
                
                pe_ratio = None
                pb_ratio = None
                roe = None
                roce = None
                sector_pe_benchmark = None
                sector_pb_benchmark = None
                
                for item in ratios_list:
                    name = str(item.get("name", "")).strip().upper()
                    val_str = str(item.get("company_value", "")).strip()
                    sec_str = str(item.get("sector_value", "")).strip()
                    
                    if val_str and val_str != "None" and val_str != "null":
                        try:
                            # Strip percent sign if present
                            val = float(val_str.replace("%", "").strip())
                            if name == 'P/E':
                                pe_ratio = val
                            elif name == 'P/B':
                                pb_ratio = val
                            elif name == 'ROE':
                                roe = val
                            elif name == 'ROCE':
                                roce = val
                        except ValueError:
                            pass
                            
                    if sec_str and sec_str != "None" and sec_str != "null":
                        try:
                            sec_val = float(sec_str.replace("%", "").strip())
                            if name == 'P/E':
                                sector_pe_benchmark = sec_val
                            elif name == 'P/B':
                                sector_pb_benchmark = sec_val
                        except ValueError:
                            pass
                
                # 3. Balance Sheet API
                print(f"[UPSTOX_BALANCE_SHEET] Fetching balance sheet for {symbol}...")
                bs = await client._make_request("GET", f"/fundamentals/{isin}/balance-sheet?fs=true")
                bs_data = bs.get("data", {}) if bs.get("status") == "success" else {}
                bs_history = bs_data.get("history", []) or []
                
                total_asset = 0.0
                total_liability = 0.0
                equity = 0.0
                debt = 0.0
                debt_to_equity = None
                
                if bs_history:
                    # Get latest year in history
                    latest_bs = bs_history[0]
                    total_asset = float(latest_bs.get("total_asset") or 0.0) * 10000000.0
                    total_liability = float(latest_bs.get("total_liability") or 0.0) * 10000000.0
                    equity = total_asset - total_liability
                    
                    # Try to parse Non-Current Liabilities from full_statement as Debt
                    full_stmt = bs_data.get("full_statement", []) or []
                    for item in full_stmt:
                        part = str(item.get("particular", "")).strip().lower()
                        if part == "non-current liabilities":
                            hist = item.get("history", []) or []
                            if hist:
                                try:
                                    debt = float(hist[0].get("value") or 0.0) * 10000000.0
                                except ValueError:
                                    pass
                                break
                    if not debt or debt <= 0:
                        # Fallback to total liability minus equity (standard debt approximation if not broken down)
                        debt = total_liability
                        
                    if equity > 0:
                        debt_to_equity = debt / equity
                    else:
                        debt_to_equity = 0.0
                
                # 4. Corporate Actions (Dividend Yield calculation)
                print(f"[UPSTOX_FUNDAMENTALS] Fetching corporate actions for {symbol}...")
                actions = await client._make_request("GET", f"/fundamentals/{isin}/corporate-actions")
                actions_list = actions.get("data", []) if actions.get("status") == "success" else []
                
                div_sum_1y = 0.0
                now = datetime.utcnow()
                one_year_ago = now - timedelta(days=365)
                
                if isinstance(actions_list, list):
                    for item in actions_list:
                        if item.get("name") == "Dividend":
                            exp_date_str = item.get("expiry_date")
                            amount = float(item.get("amount") or 0.0)
                            
                            if exp_date_str:
                                try:
                                    exp_date = datetime.strptime(exp_date_str, "%d %b %Y")
                                    if one_year_ago <= exp_date <= now:
                                        div_sum_1y += amount
                                except Exception as de:
                                    print(f"[UPSTOX_FUNDAMENTALS] [WARNING] Failed to parse ex-date: {exp_date_str}: {de}")
                                    
                dividend_yield = None
                if latest_price > 0:
                    dividend_yield = (div_sum_1y / latest_price) * 100.0
                else:
                    dividend_yield = 0.0
                    
                # 5. Math Calculations: EPS and Book Value
                eps = None
                if pe_ratio and pe_ratio > 0 and latest_price > 0:
                    eps = latest_price / pe_ratio
                    
                book_value = None
                if pb_ratio and pb_ratio > 0 and latest_price > 0:
                    book_value = latest_price / pb_ratio
                
                # 6. Save back to postgres
                # Update instrument_master: sector classification
                db_inst = db.query(InstrumentMaster).filter(InstrumentMaster.instrument_id == inst_id).first()
                if db_inst:
                    if sector and sector != "Others":
                        db_inst.sector = sector
                    db_inst.updated_at = datetime.utcnow()
                
                # Update fundamental_metrics
                db_metrics = db.query(FundamentalMetrics).filter(FundamentalMetrics.symbol == symbol).first()
                if not db_metrics:
                    db_metrics = FundamentalMetrics(symbol=symbol)
                    db.add(db_metrics)
                    
                db_metrics.market_cap = market_cap if market_cap > 0 else (db_metrics.market_cap or 5000000000.0)
                db_metrics.pe_ratio = pe_ratio if pe_ratio else db_metrics.pe_ratio
                db_metrics.pb_ratio = pb_ratio if pb_ratio else db_metrics.pb_ratio
                db_metrics.dividend_yield = dividend_yield if dividend_yield is not None else db_metrics.dividend_yield
                db_metrics.debt_to_equity = debt_to_equity if debt_to_equity is not None else db_metrics.debt_to_equity
                db_metrics.roe = roe if roe else db_metrics.roe
                db_metrics.roce = roce if roce else db_metrics.roce
                db_metrics.eps = eps if eps else db_metrics.eps
                db_metrics.sector_pe_benchmark = sector_pe_benchmark if sector_pe_benchmark else db_metrics.sector_pe_benchmark
                db_metrics.sector_pb_benchmark = sector_pb_benchmark if sector_pb_benchmark else db_metrics.sector_pb_benchmark
                db_metrics.updated_at = datetime.utcnow()
                
                db.commit()
                print(f"[DATA_VALIDATION] [SUCCESS] Sync complete for {symbol}. Sector: {sector} | M.Cap: Rs {market_cap/10000000:.1f} Cr | PE: {pe_ratio} | PB: {pb_ratio} | ROE: {roe}% | ROCE: {roce}% | Debt/Equity: {debt_to_equity} | DivYield: {dividend_yield:.2f}%")
                synced += 1
                
            except Exception as se:
                db.rollback()
                print(f"[DATA_VALIDATION] [ERROR] Sync failed for {symbol}: {se}")
                failed += 1
                
            # Rate limiting friendly: small sleep
            await asyncio.sleep(0.5)
            
        print(f"\n[DATA_VALIDATION] Fundamental Sync completed. Synced: {synced}, Failed: {failed}")
    except Exception as e:
        print(f"[DATA_VALIDATION] [ERROR] Ingestion process failed: {e}")
    finally:
        db.close()
        await client.aclose()

if __name__ == "__main__":
    # If run directly, sync 20 symbols for verification/demo purposes
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass
    asyncio.run(sync_all_fundamentals(limit))
