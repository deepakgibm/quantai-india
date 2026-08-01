import asyncio
import sys
import unittest
from pathlib import Path
import httpx

# Add paths
sys.path.insert(0, r"c:\Users\Deepak Kumar\Downloads\quantai-india")
sys.path.insert(0, r"c:\Users\Deepak Kumar\Downloads\quantai-india\backend")

from backend.main import app
from utils.auth import get_current_user
from utils.index_config import get_index_constituents

# Mock current user for authentication bypass in testing
async def mock_current_user():
    from models import User
    return User(id=1, email="demo@example.com", username="demo", full_name="Demo User")

app.dependency_overrides[get_current_user] = mock_current_user

# Mock normalizeSector function to test frontend sector mapping rules
def mock_normalize_sector(sec: str) -> str:
    if not sec:
        return 'Miscellaneous'
    lower = sec.lower().strip()

    if 'financial' in lower or 'bank' in lower or 'insurance' in lower or 'credit' in lower or 'nbfc' in lower or 'finance' in lower or 'investment' in lower:
        return 'Financial Services'
    if 'it - software' in lower or 'it' in lower or 'software' in lower or 'computer' in lower or 'technology' in lower:
        return 'Information Technology'
    if 'healthcare' in lower or 'hospital' in lower or 'medical' in lower or 'clinical' in lower:
        return 'Healthcare'
    if 'pharma' in lower or 'biotech' in lower or 'drugs' in lower or 'medicine' in lower or 'pharmaceuticals' in lower:
        return 'Pharma'
    if 'automobile' in lower or 'automotive' in lower or 'motorcycle' in lower or 'scooter' in lower or 'car' in lower or 'vehicle' in lower or 'others' in lower:
        return 'Automobile'
    if 'refineries' in lower or 'oil' in lower or 'gas' in lower or 'petro' in lower or 'refinery' in lower:
        return 'Oil & Gas'
    if 'power' in lower or 'electricity' in lower or 'utilities' in lower:
        return 'Power'
    if 'metal' in lower or 'steel' in lower or 'mining' in lower or 'iron' in lower or 'aluminium' in lower or 'minerals' in lower or 'coal' in lower:
        return 'Metals'
    if 'fmcg' in lower or 'food' in lower or 'beverage' in lower or 'household' in lower or 'tobacco' in lower or 'tea' in lower or 'coffee' in lower or 'consumer product' in lower:
        return 'FMCG'
    if 'jewellery' in lower or 'paints' in lower or 'durables' in lower or 'appliances' in lower:
        return 'Consumer Durables'
    if 'cement' in lower or 'construction materials' in lower:
        return 'Cement'
    if 'construction' in lower or 'infra' in lower or 'real estate' in lower or 'building' in lower or 'engineering' in lower:
        return 'Construction'
    if 'telecom' in lower or 'communication' in lower:
        return 'Telecom'
    if 'trading' in lower or 'retail' in lower or 'ecommerce' in lower or 'e-commerce' in lower or 'port' in lower or 'airlines' in lower or 'logistics' in lower or 'transport' in lower or 'shipping' in lower or 'diversified' in lower:
        return 'Services'

    return 'Miscellaneous'

class TestHeatmapReadiness(unittest.IsolatedAsyncioTestCase):
    
    async def asyncSetUp(self):
        self.transport = httpx.ASGITransport(app=app)
        self.client = httpx.AsyncClient(transport=self.transport, base_url="http://test")
        
    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_nifty50_constituents_loaded(self):
        """Test: Load NIFTY 50 constituents and assert exactly 50 unique elements."""
        nifty50 = get_index_constituents("NIFTY 50")
        print(f"\n[TEST] NIFTY Constituents Loaded: {len(nifty50)}")
        self.assertEqual(len(nifty50), 50, "NIFTY 50 must have exactly 50 constituents.")
        self.assertEqual(len(set(nifty50)), 50, "NIFTY 50 constituents must contain no duplicate symbols.")

    async def test_heatmap_api_response_complete(self):
        """Test: Heatmap API returns all 50 stocks across multiple sectors and timeframes."""
        modes = ["performance", "volatility", "momentum", "delivery", "relative_strength"]
        timeframes = ["1D", "1W", "1M"]
        
        # Test default mode and timeframe
        res = await self.client.get("/api/heatmap?mode=performance&timeframe=1D")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("index"), "NIFTY50")
        self.assertEqual(data.get("stockCount"), 50, "Heatmap response must contain exactly 50 stocks.")
        self.assertGreater(data.get("sectorCount"), 10, "Heatmap response must contain multiple distinct sectors.")
        
        # Verify sectors are aggregated and stocks are non-empty
        sectors = data.get("sectors", [])
        total_stocks = 0
        for s in sectors:
            self.assertIsNotNone(s.get("name"))
            self.assertGreater(len(s.get("stocks", [])), 0)
            total_stocks += len(s.get("stocks", []))
            
            # Verify stock properties
            for st in s["stocks"]:
                self.assertIsNotNone(st.get("symbol"))
                self.assertIsNotNone(st.get("price"))
                self.assertIsNotNone(st.get("market_cap"))
                self.assertIsNotNone(st.get("change_pct"))
                self.assertIsNotNone(st.get("value"))
                
        self.assertEqual(total_stocks, 50, "Sectors aggregate count must sum to exactly 50 stocks.")
        print(f"[TEST] Heatmap API returns 50/50 stocks across {len(sectors)} raw sectors.")

    async def test_sector_classification_normalization(self):
        """Test: Every stock is mapped correctly to a valid sector and no stocks land in 'Unknown'."""
        res = await self.client.get("/api/heatmap?mode=performance&timeframe=1D")
        self.assertEqual(res.status_code, 200)
        sectors = res.json().get("sectors", [])
        
        normalized_sectors = {}
        for s in sectors:
            raw_name = s.get("name")
            norm_name = mock_normalize_sector(raw_name)
            
            if norm_name not in normalized_sectors:
                normalized_sectors[norm_name] = []
            
            for st in s["stocks"]:
                normalized_sectors[norm_name].append(st["symbol"])
                
        # Assert none of the stocks default to bad names
        self.assertNotIn("Unknown", normalized_sectors)
        self.assertNotIn("Miscellaneous", normalized_sectors)  # Both Coal India & TMPV are now mapped to Metals & Automobile
        
        # Verify specific expected Nifty 50 mappings
        self.assertIn("HDFCBANK", normalized_sectors.get("Financial Services", []))
        self.assertIn("ICICIBANK", normalized_sectors.get("Financial Services", []))
        self.assertIn("TCS", normalized_sectors.get("Information Technology", []))
        self.assertIn("INFY", normalized_sectors.get("Information Technology", []))
        self.assertIn("RELIANCE", normalized_sectors.get("Oil & Gas", []))
        self.assertIn("MARUTI", normalized_sectors.get("Automobile", []))
        self.assertIn("APOLLOHOSP", normalized_sectors.get("Healthcare", []))
        self.assertIn("MAXHEALTH", normalized_sectors.get("Healthcare", []))
        self.assertIn("SUNPHARMA", normalized_sectors.get("Pharma", []))
        
        # Sum of normalized sector stocks must equal 50
        sum_normalized = sum(len(stocks) for stocks in normalized_sectors.values())
        self.assertEqual(sum_normalized, 50)
        print(f"[TEST] Sector normalization mapping successful. Verified 50/50 sector placements.")

if __name__ == "__main__":
    unittest.main()
