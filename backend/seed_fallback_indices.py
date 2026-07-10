"""
Fallback seed for 4 NSE indices where CSV is not publicly accessible.
Uses the instrument_master's sector data to identify likely constituents.
These will be overridden when NSE publishes updated CSVs.
"""
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
from sqlalchemy import create_engine, text
from config import settings

engine = create_engine(settings.SYNC_DATABASE_URL)

# Known constituents for these indices (from NSE published factsheets)
FALLBACK_INDICES = {
    "NIFTY REALTY": {
        "display_name": "NIFTY Realty",
        "category": "Sector",
        "nse_index_code": "ind_niftyrealty",
        "description": "Real estate sector companies",
        "symbols": [
            "DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "PHOENIXLTD",
            "SOBHA", "BRIGADE", "MAHLIFE", "SUNTECK", "LODHA",
        ],
    },
    "NIFTY PRIVATE BANK": {
        "display_name": "NIFTY Private Bank",
        "category": "Sector",
        "nse_index_code": "ind_niftyprivatebank",
        "description": "Private sector banking companies",
        "symbols": [
            "HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "INDUSINDBK",
            "BANDHANBNK", "FEDERALBNK", "IDFCFIRSTB", "CUB", "AUBANK",
        ],
    },
    "NIFTY CAPITAL GOODS": {
        "display_name": "NIFTY Capital Goods",
        "category": "Sector",
        "nse_index_code": "ind_niftycapitalgoods",
        "description": "Capital goods and industrial machinery",
        "symbols": [
            "LT", "SIEMENS", "ABB", "HAVELLS", "BHEL", "CGPOWER",
            "BEL", "HAL", "POLYCAB", "THERMAX", "CUMMINSIND", "AIAENG",
            "GRINDWELL", "ELGIEQUIP", "TIINDIA",
        ],
    },
    "NIFTY CHEMICALS": {
        "display_name": "NIFTY Chemicals",
        "category": "Sector",
        "nse_index_code": "ind_niftychemicals",
        "description": "Chemicals sector companies",
        "symbols": [
            "PIDILITIND", "SRF", "DEEPAKNTR", "AARTIIND", "NAVINFLUOR",
            "FINOLEXIND", "BALRAMCHIN", "GNFC", "TATACHEM", "CHAMBLFERT",
            "COROMANDEL", "PIIND", "ATUL", "FINEORG", "ALKYLAMINE",
        ],
    },
}

with engine.begin() as conn:
    for index_name, info in FALLBACK_INDICES.items():
        print(f"\n  → Seeding {index_name} with {len(info['symbols'])} symbols...")
        
        # Upsert index_master
        existing = conn.execute(text(
            "SELECT index_id FROM index_master WHERE index_name = :name"
        ), {"name": index_name}).fetchone()
        
        if existing:
            index_id = existing[0]
            conn.execute(text("""
                UPDATE index_master SET display_name=:dn, category=:cat, description=:desc,
                       nse_index_code=:code, is_active=TRUE, updated_at=NOW()
                WHERE index_name=:name
            """), {"dn": info["display_name"], "cat": info["category"],
                   "desc": info["description"], "code": info["nse_index_code"],
                   "name": index_name})
        else:
            row = conn.execute(text("""
                INSERT INTO index_master (index_name, display_name, category, description, nse_index_code, is_active, created_at, updated_at)
                VALUES (:name, :dn, :cat, :desc, :code, TRUE, NOW(), NOW())
                RETURNING index_id
            """), {"name": index_name, "dn": info["display_name"], "cat": info["category"],
                   "desc": info["description"], "code": info["nse_index_code"]}).fetchone()
            index_id = row[0]
        
        # Resolve symbols to instrument_ids
        matched = 0
        for sym in info["symbols"]:
            row = conn.execute(text(
                "SELECT instrument_id FROM instrument_master WHERE symbol=:s AND is_active=TRUE"
            ), {"s": sym}).fetchone()
            if row:
                conn.execute(text("""
                    INSERT INTO index_constituent (index_id, instrument_id, added_at)
                    VALUES (:idx, :iid, NOW())
                    ON CONFLICT (index_id, instrument_id) DO UPDATE SET removed_at=NULL
                """), {"idx": index_id, "iid": row[0]})
                matched += 1
            else:
                print(f"    WARN: {sym} not found in instrument_master")
        
        # Update constituent count
        conn.execute(text(
            "UPDATE index_master SET constituent_count=:cnt WHERE index_id=:iid"
        ), {"cnt": matched, "iid": index_id})
        
        print(f"  ✓ {index_name}: seeded {matched}/{len(info['symbols'])} symbols")

print("\nFallback seed complete.")
