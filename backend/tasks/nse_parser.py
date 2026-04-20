import csv
from datetime import datetime
from database import SessionLocal
from models import InstitutionalFlows
import logging

logger = logging.getLogger(__name__)

def parse_nse_bulk_block_deals(csv_file_path: str):
    """
    Parses NSE Bulk/Block deal disclosures from a standardized CSV 
    and ingests them into the institutional_flows PostgreSQL table.
    
    Expected CSV columns:
    Date, Symbol, Security Name, Client Name, Buy/Sell, Quantity Traded, Trade Price, Remarks
    """
    db = SessionLocal()
    try:
        with open(csv_file_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                try:
                    # Clean and parse date
                    date_str = row.get("Date", "").strip()
                    deal_date = datetime.strptime(date_str, "%d-%b-%Y")
                    
                    symbol = row.get("Symbol", "").strip()
                    client_name = row.get("Client Name", "").strip().upper()
                    deal_type = row.get("Buy/Sell", "").strip().upper()
                    quantity = int(row.get("Quantity Traded", "0").replace(",", ""))
                    price = float(row.get("Trade Price", "0").replace(",", ""))
                    
                    # Logic to determine FLow Category based on names
                    flow_category = "HNI"
                    if "FUND" in client_name or "AMC" in client_name or "TRUST" in client_name:
                        flow_category = "DII"
                    elif "PTE" in client_name or "LTD" in client_name or "LIMITED" in client_name or "CAPITAL" in client_name:
                        flow_category = "FII"
                        
                    flow = InstitutionalFlows(
                        symbol=symbol,
                        deal_date=deal_date,
                        client_name=client_name,
                        deal_type=deal_type,
                        quantity=quantity,
                        price=price,
                        flow_category=flow_category
                    )
                    
                    db.add(flow)
                    count += 1
                except Exception as e:
                    logger.error(f"Error parsing row {row}: {e}")
                    
            db.commit()
            logger.info(f"Successfully ingested {count} institutional flow records.")
            
    except Exception as e:
        logger.error(f"Failed to ingest CSV {csv_file_path}: {e}")
        db.rollback()
    finally:
        db.close()
