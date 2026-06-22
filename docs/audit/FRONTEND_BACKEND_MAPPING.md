# Phase 2: FRONTEND_BACKEND_MAPPING.md

This document maps all frontend components, routes, and their respective backend API endpoints, queries, and current status.

| Page | Component | API Endpoint | Backend Service | Status |
|------|-----------|--------------|-----------------|--------|
| Dashboard | `Dashboard.tsx` | `/api/health/` | `verify_database_health` | ✅ Healthy |
| Option Flow | `OptionFlow.tsx` | `/api/option-flow/{symbol}` | `DerivativesService` | ✅ Healthy |
| Watchlist | `Watchlist.tsx` | `/api/watchlist/` | `watchlist_service` | ✅ Healthy |
| Scanner | `Scanner.tsx` | `/api/scanner/ws` | `scanner_websocket` | ✅ Healthy |
| Volatility | `OptionFlow.tsx` | `/api/volatility/{symbol}` | `upstox_price_resolver` | ✅ Healthy |
| Volume Profile | `OptionFlow.tsx` | `/api/volume-profile/{symbol}` | `volume_profile` | ✅ Healthy |

---

## Component-to-Query Mapping Evidence

### Page: Option Flow
- **Component**: `OptionFlow.tsx`
- **API Endpoint**: `/api/option-flow/RELIANCE`
- **Backend Service**: `DerivativesService`
- **Database Query**: `SELECT instrument_id, instrument_key FROM instrument_master WHERE symbol = :symbol`
- **Status**: ✅ Active. No database JOINs; utilizes cache-first `resolve_instrument_info`.
- **Issue**: None detected. PCR and IV calculations moved to derivatives service.

### Page: Volatility
- **Component**: `OptionFlow.tsx` (Advanced Tab)
- **API Endpoint**: `/api/volatility/{symbol}`
- **Backend Service**: `upstox_price_resolver`
- **Database Query**: `SELECT close FROM stock_candle WHERE instrument_id = :iid AND timeframe = 1440`
- **Status**: ✅ Active.
