"""
Index Management Service
========================
Fetches NSE index constituent CSVs, validates them against instrument_master,
and keeps index_master / index_constituent / index_refresh_log up-to-date.

Usage:
    svc = IndexManagementService()
    result = svc.refresh_index("NIFTY 50", db_session)
"""

import csv
import io
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import httpx
from sqlalchemy import text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NSE index catalogue
# ---------------------------------------------------------------------------
NSE_INDICES: List[Dict] = [
    # Broad Market
    {
        "index_name": "NIFTY 50",
        "display_name": "NIFTY 50",
        "category": "Broad Market",
        "nse_index_code": "ind_nifty50list",
        "description": "Top 50 large-cap stocks by market capitalisation",
    },
    {
        "index_name": "NIFTY NEXT 50",
        "display_name": "NIFTY Next 50",
        "category": "Broad Market",
        "nse_index_code": "ind_niftynext50list",
        "description": "Stocks ranked 51-100 by market capitalisation",
    },
    {
        "index_name": "NIFTY 100",
        "display_name": "NIFTY 100",
        "category": "Broad Market",
        "nse_index_code": "ind_nifty100list",
        "description": "Top 100 large-cap stocks",
    },
    {
        "index_name": "NIFTY 200",
        "display_name": "NIFTY 200",
        "category": "Broad Market",
        "nse_index_code": "ind_nifty200list",
        "description": "Top 200 stocks by market capitalisation",
    },
    {
        "index_name": "NIFTY 500",
        "display_name": "NIFTY 500",
        "category": "Broad Market",
        "nse_index_code": "ind_nifty500list",
        "description": "Top 500 stocks representing ~95% of total market cap",
    },
    {
        "index_name": "NIFTY TOTAL MARKET",
        "display_name": "NIFTY Total Market",
        "category": "Broad Market",
        "nse_index_code": "ind_niftytotalmarket",
        "description": "Entire NSE universe of liquid stocks",
    },
    # Sector Indices
    {
        "index_name": "NIFTY BANK",
        "display_name": "NIFTY Bank",
        "category": "Sector",
        "nse_index_code": "ind_niftybanklist",
        "description": "Most liquid and large capitalised banking stocks",
    },
    {
        "index_name": "NIFTY IT",
        "display_name": "NIFTY IT",
        "category": "Sector",
        "nse_index_code": "ind_niftyitlist",
        "description": "Companies in IT sector",
    },
    {
        "index_name": "NIFTY AUTO",
        "display_name": "NIFTY Auto",
        "category": "Sector",
        "nse_index_code": "ind_niftyautolist",
        "description": "Automobile sector companies",
    },
    {
        "index_name": "NIFTY FMCG",
        "display_name": "NIFTY FMCG",
        "category": "Sector",
        "nse_index_code": "ind_niftyfmcglist",
        "description": "Fast Moving Consumer Goods companies",
    },
    {
        "index_name": "NIFTY PHARMA",
        "display_name": "NIFTY Pharma",
        "category": "Sector",
        "nse_index_code": "ind_niftypharmalist",
        "description": "Pharmaceutical sector companies",
    },
    {
        "index_name": "NIFTY METAL",
        "display_name": "NIFTY Metal",
        "category": "Sector",
        "nse_index_code": "ind_niftymetallist",
        "description": "Metal sector companies",
    },
    {
        "index_name": "NIFTY REALTY",
        "display_name": "NIFTY Realty",
        "category": "Sector",
        "nse_index_code": "ind_niftyrealty",
        "description": "Real estate sector companies",
    },
    {
        "index_name": "NIFTY MEDIA",
        "display_name": "NIFTY Media",
        "category": "Sector",
        "nse_index_code": "ind_niftymedialist",
        "description": "Media and entertainment sector",
    },
    {
        "index_name": "NIFTY ENERGY",
        "display_name": "NIFTY Energy",
        "category": "Sector",
        "nse_index_code": "ind_niftyenergylist",
        "description": "Energy sector companies",
    },
    {
        "index_name": "NIFTY OIL AND GAS",
        "display_name": "NIFTY Oil & Gas",
        "category": "Sector",
        "nse_index_code": "ind_niftyoilgaslist",
        "description": "Oil, gas and petroleum sector",
    },
    {
        "index_name": "NIFTY PSU BANK",
        "display_name": "NIFTY PSU Bank",
        "category": "Sector",
        "nse_index_code": "ind_niftypsubanklist",
        "description": "Public sector banking companies",
    },
    {
        "index_name": "NIFTY PRIVATE BANK",
        "display_name": "NIFTY Private Bank",
        "category": "Sector",
        "nse_index_code": "ind_niftyprivatebank",
        "description": "Private sector banking companies",
    },
    {
        "index_name": "NIFTY FINANCIAL SERVICES",
        "display_name": "NIFTY Financial Services",
        "category": "Sector",
        "nse_index_code": "ind_niftyfinancelist",
        "description": "Financial services companies",
    },
    {
        "index_name": "NIFTY HEALTHCARE",
        "display_name": "NIFTY Healthcare",
        "category": "Sector",
        "nse_index_code": "ind_niftyhealthcarelist",
        "description": "Healthcare sector companies",
    },
    {
        "index_name": "NIFTY CONSUMER DURABLES",
        "display_name": "NIFTY Consumer Durables",
        "category": "Sector",
        "nse_index_code": "ind_niftyconsumerdurableslist",
        "description": "Consumer durables sector",
    },
    {
        "index_name": "NIFTY CAPITAL GOODS",
        "display_name": "NIFTY Capital Goods",
        "category": "Sector",
        "nse_index_code": "ind_niftycapitalmarket",
        "description": "Capital goods and industrial machinery",
    },
    {
        "index_name": "NIFTY CHEMICALS",
        "display_name": "NIFTY Chemicals",
        "category": "Sector",
        "nse_index_code": "ind_niftychemicals",
        "description": "Chemicals sector companies",
    },
    # Mid/Small Cap
    {
        "index_name": "NIFTY MIDCAP 50",
        "display_name": "NIFTY Midcap 50",
        "category": "Midcap",
        "nse_index_code": "ind_niftymidcap50list",
        "description": "Top 50 mid-cap stocks",
    },
    {
        "index_name": "NIFTY MIDCAP 100",
        "display_name": "NIFTY Midcap 100",
        "category": "Midcap",
        "nse_index_code": "ind_niftymidcap100list",
        "description": "Top 100 mid-cap stocks",
    },
    {
        "index_name": "NIFTY SMALLCAP 100",
        "display_name": "NIFTY Smallcap 100",
        "category": "Smallcap",
        "nse_index_code": "ind_niftysmallcap100list",
        "description": "Top 100 small-cap stocks",
    },
]

NSE_CSV_BASE_URL = "https://nsearchives.nseindia.com/content/indices/{code}.csv"

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.nseindia.com/",
    "DNT": "1",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ConstituentRecord:
    symbol: str
    company_name: str
    industry: str
    series: str
    isin: str
    weight: Optional[float] = None


@dataclass
class ValidationReport:
    index_name: str
    total_nse: int = 0
    matched: List[Dict] = field(default_factory=list)
    missing: List[Dict] = field(default_factory=list)
    auto_resolved: List[Dict] = field(default_factory=list)

    @property
    def coverage_pct(self) -> float:
        if self.total_nse == 0:
            return 0.0
        return round((len(self.matched) + len(self.auto_resolved)) / self.total_nse * 100, 2)


@dataclass
class RefreshResult:
    index_name: str
    status: str
    added_count: int = 0
    removed_count: int = 0
    matched_count: int = 0
    missing_count: int = 0
    coverage_pct: float = 0.0
    missing_symbols: List[str] = field(default_factory=list)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class IndexManagementService:

    def __init__(self):
        self._http = httpx.Client(timeout=30, follow_redirects=True, headers=NSE_HEADERS)

    # ------------------------------------------------------------------
    # NSE Fetch
    # ------------------------------------------------------------------

    def fetch_nse_constituents(self, nse_index_code: str) -> List[ConstituentRecord]:
        """
        Download and parse NSE constituent CSV for a given index code.
        Returns list of ConstituentRecord objects.
        """
        url = NSE_CSV_BASE_URL.format(code=nse_index_code)
        logger.info(f"Fetching NSE constituents from: {url}")

        try:
            resp = self._http.get(url)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch NSE CSV for {nse_index_code}: {e}")
            raise RuntimeError(f"NSE CSV fetch failed for {nse_index_code}: {e}")

        content = resp.text
        records: List[ConstituentRecord] = []

        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            # NSE CSV columns: Company Name, Industry, Symbol, Series, ISIN Code
            # Some CSVs also have Index Weight
            symbol = (row.get("Symbol", "") or row.get("symbol", "")).strip().upper()
            if not symbol:
                continue
            records.append(ConstituentRecord(
                symbol=symbol,
                company_name=(row.get("Company Name", "") or "").strip(),
                industry=(row.get("Industry", "") or "").strip(),
                series=(row.get("Series", "EQ") or "EQ").strip(),
                isin=(row.get("ISIN Code", "") or "").strip(),
                weight=self._parse_weight(row.get("Index Weight") or row.get("Weight")),
            ))

        logger.info(f"Parsed {len(records)} constituents for {nse_index_code}")
        return records

    @staticmethod
    def _parse_weight(val) -> Optional[float]:
        try:
            return float(str(val).replace("%", "").strip()) if val else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_constituents(
        self,
        index_name: str,
        nse_records: List[ConstituentRecord],
        conn,
    ) -> ValidationReport:
        """
        Validate NSE constituents against instrument_master.
        Tries exact match, then case-insensitive, then common alias resolution.
        """
        report = ValidationReport(index_name=index_name, total_nse=len(nse_records))

        # Load instrument_master into a lookup dict
        rows = conn.execute(text(
            "SELECT symbol, instrument_key, instrument_id, is_active FROM instrument_master"
        )).fetchall()

        exact_map: Dict[str, Dict] = {}
        upper_map: Dict[str, Dict] = {}
        for r in rows:
            sym = r[0] or ""
            entry = {"symbol": sym, "instrument_key": r[1], "instrument_id": r[2], "is_active": r[3]}
            exact_map[sym] = entry
            upper_map[sym.upper()] = entry

        for rec in nse_records:
            sym = rec.symbol

            # 1. Exact match
            if sym in exact_map and exact_map[sym]["is_active"]:
                report.matched.append({
                    "nse_symbol": sym,
                    "db_symbol": sym,
                    "instrument_id": exact_map[sym]["instrument_id"],
                    "instrument_key": exact_map[sym]["instrument_key"],
                    "industry": rec.industry,
                    "weight": rec.weight,
                    "resolution": "exact",
                })
                continue

            # 2. Case-insensitive match
            if sym.upper() in upper_map and upper_map[sym.upper()]["is_active"]:
                resolved = upper_map[sym.upper()]
                report.auto_resolved.append({
                    "nse_symbol": sym,
                    "db_symbol": resolved["symbol"],
                    "instrument_id": resolved["instrument_id"],
                    "instrument_key": resolved["instrument_key"],
                    "industry": rec.industry,
                    "weight": rec.weight,
                    "resolution": "case_insensitive",
                })
                continue

            # 3. Try with -EQ suffix removed / added
            for variant in [sym.replace("-EQ", ""), sym + "-EQ", sym.replace("&", "AND")]:
                if variant in exact_map and exact_map[variant]["is_active"]:
                    report.auto_resolved.append({
                        "nse_symbol": sym,
                        "db_symbol": variant,
                        "instrument_id": exact_map[variant]["instrument_id"],
                        "instrument_key": exact_map[variant]["instrument_key"],
                        "industry": rec.industry,
                        "weight": rec.weight,
                        "resolution": f"alias:{variant}",
                    })
                    break
            else:
                # Not found
                report.missing.append({
                    "nse_symbol": sym,
                    "company_name": rec.company_name,
                    "isin": rec.isin,
                    "reason": "not_in_db" if sym not in exact_map else "inactive",
                })

        return report

    # ------------------------------------------------------------------
    # Refresh — the main operation
    # ------------------------------------------------------------------

    def refresh_index(self, index_name: str, conn) -> RefreshResult:
        """
        Full refresh cycle for one index:
          1. Find index definition in NSE_INDICES catalogue
          2. Fetch NSE CSV
          3. Validate against instrument_master
          4. Upsert index_master row
          5. Soft-delete removed constituents, insert new ones
          6. Log to index_refresh_log
        """
        # Find catalogue entry
        catalogue_entry = next(
            (i for i in NSE_INDICES if i["index_name"].upper() == index_name.upper()), None
        )
        if catalogue_entry is None:
            return RefreshResult(index_name=index_name, status="failed",
                                 error=f"Index '{index_name}' not in NSE catalogue")

        nse_code = catalogue_entry["nse_index_code"]

        # Fetch NSE CSV
        try:
            nse_records = self.fetch_nse_constituents(nse_code)
        except Exception as e:
            self._log_refresh(conn, None, index_name, RefreshResult(
                index_name=index_name, status="failed", error=str(e)
            ))
            return RefreshResult(index_name=index_name, status="failed", error=str(e))

        # Validate
        report = self.validate_constituents(index_name, nse_records, conn)
        all_matched = report.matched + report.auto_resolved

        # Upsert index_master
        index_id = self._upsert_index_master(conn, catalogue_entry, len(all_matched))

        # Sync constituents
        added, removed = self._sync_constituents(conn, index_id, all_matched)

        # Invalidate utils/index_config.py cache
        try:
            from utils.index_config import clear_cache
            clear_cache()
        except Exception:
            pass

        result = RefreshResult(
            index_name=index_name,
            status="success" if not report.missing else "partial",
            added_count=added,
            removed_count=removed,
            matched_count=len(all_matched),
            missing_count=len(report.missing),
            coverage_pct=report.coverage_pct,
            missing_symbols=[m["nse_symbol"] for m in report.missing],
        )

        self._log_refresh(conn, index_id, index_name, result,
                          total_nse=report.total_nse,
                          missing_symbols=report.missing)
        return result

    def refresh_all(self, conn) -> List[RefreshResult]:
        """Refresh every index in the NSE catalogue sequentially."""
        results = []
        for entry in NSE_INDICES:
            logger.info(f"Refreshing index: {entry['index_name']}")
            try:
                result = self.refresh_index(entry["index_name"], conn)
                results.append(result)
                logger.info(
                    f"  {entry['index_name']}: matched={result.matched_count} "
                    f"missing={result.missing_count} coverage={result.coverage_pct}%"
                )
            except Exception as e:
                logger.error(f"  FAILED {entry['index_name']}: {e}")
                results.append(RefreshResult(index_name=entry["index_name"], status="failed", error=str(e)))
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _upsert_index_master(self, conn, entry: Dict, count: int) -> int:
        """Insert or update the index_master row. Returns index_id."""
        now = datetime.utcnow()
        csv_url = NSE_CSV_BASE_URL.format(code=entry["nse_index_code"])

        existing = conn.execute(
            text("SELECT index_id FROM index_master WHERE index_name = :name"),
            {"name": entry["index_name"]}
        ).fetchone()

        if existing:
            conn.execute(text("""
                UPDATE index_master SET
                    display_name = :dn,
                    description = :desc,
                    category = :cat,
                    nse_index_code = :code,
                    csv_url = :url,
                    last_refreshed = :ts,
                    constituent_count = :cnt,
                    updated_at = :ts,
                    is_active = TRUE
                WHERE index_name = :name
            """), {
                "dn": entry.get("display_name", entry["index_name"]),
                "desc": entry.get("description", ""),
                "cat": entry.get("category", "Broad Market"),
                "code": entry["nse_index_code"],
                "url": csv_url,
                "ts": now,
                "cnt": count,
                "name": entry["index_name"],
            })
            return existing[0]
        else:
            row = conn.execute(text("""
                INSERT INTO index_master
                    (index_name, display_name, description, category, nse_index_code,
                     csv_url, last_refreshed, constituent_count, is_active, created_at, updated_at)
                VALUES
                    (:name, :dn, :desc, :cat, :code,
                     :url, :ts, :cnt, TRUE, :ts, :ts)
                RETURNING index_id
            """), {
                "name": entry["index_name"],
                "dn": entry.get("display_name", entry["index_name"]),
                "desc": entry.get("description", ""),
                "cat": entry.get("category", "Broad Market"),
                "code": entry["nse_index_code"],
                "url": csv_url,
                "ts": now,
                "cnt": count,
            }).fetchone()
            return row[0]

    def _sync_constituents(self, conn, index_id: int, matched: List[Dict]) -> Tuple[int, int]:
        """
        Sync index_constituent rows for this index:
        - Soft-delete constituents that are no longer in the matched list.
        - Insert new constituents with ON CONFLICT DO UPDATE.
        Returns (added_count, removed_count).
        """
        new_instrument_ids = {m["instrument_id"] for m in matched}

        # Fetch current active constituents
        current_rows = conn.execute(text(
            "SELECT instrument_id FROM index_constituent "
            "WHERE index_id = :iid AND removed_at IS NULL"
        ), {"iid": index_id}).fetchall()
        current_ids = {r[0] for r in current_rows}

        removed_ids = current_ids - new_instrument_ids
        added_ids = new_instrument_ids - current_ids

        # Soft-delete removed
        if removed_ids:
            conn.execute(text(
                "UPDATE index_constituent SET removed_at = NOW() "
                "WHERE index_id = :iid AND instrument_id = ANY(:ids)"
            ), {"iid": index_id, "ids": list(removed_ids)})

        # Insert / re-activate new constituents
        for m in matched:
            iid = m["instrument_id"]
            if iid not in added_ids:
                # Still active — update weight/sector
                conn.execute(text("""
                    UPDATE index_constituent
                    SET weight = :w, sector = :sec, industry = :ind, removed_at = NULL
                    WHERE index_id = :idx AND instrument_id = :iid
                """), {"w": m.get("weight"), "sec": m.get("industry"), "ind": m.get("industry"),
                        "idx": index_id, "iid": iid})
            else:
                # Insert new (or re-activate if exists with removed_at set)
                conn.execute(text("""
                    INSERT INTO index_constituent (index_id, instrument_id, weight, sector, industry, added_at)
                    VALUES (:idx, :iid, :w, :sec, :ind, NOW())
                    ON CONFLICT (index_id, instrument_id) DO UPDATE SET
                        weight = EXCLUDED.weight,
                        sector = EXCLUDED.sector,
                        industry = EXCLUDED.industry,
                        removed_at = NULL
                """), {"idx": index_id, "iid": iid,
                        "w": m.get("weight"), "sec": m.get("industry"), "ind": m.get("industry")})

        return len(added_ids), len(removed_ids)

    def _log_refresh(self, conn, index_id, index_name: str, result: RefreshResult,
                     total_nse: int = 0, missing_symbols: List = None):
        """Write a row to index_refresh_log."""
        try:
            conn.execute(text("""
                INSERT INTO index_refresh_log
                    (index_id, index_name, added_count, removed_count,
                     matched_count, missing_count, total_nse_count,
                     coverage_pct, status, error_message, missing_symbols)
                VALUES
                    (:iid, :name, :add, :rem,
                     :match, :miss, :total,
                     :cov, :status, :err, :msym)
            """), {
                "iid": index_id,
                "name": index_name,
                "add": result.added_count,
                "rem": result.removed_count,
                "match": result.matched_count,
                "miss": result.missing_count,
                "total": total_nse or 0,
                "cov": result.coverage_pct,
                "status": result.status,
                "err": result.error,
                "msym": json.dumps([m.get("nse_symbol") for m in (missing_symbols or [])]),
            })
        except Exception as e:
            logger.warning(f"Failed to write refresh log: {e}")

    def get_index_info(self, index_name: str) -> Optional[Dict]:
        """Return catalogue entry for a given index_name (case-insensitive)."""
        return next(
            (i for i in NSE_INDICES if i["index_name"].upper() == index_name.upper()),
            None
        )

    def list_all_catalogue(self) -> List[Dict]:
        """Return the full NSE index catalogue."""
        return NSE_INDICES
