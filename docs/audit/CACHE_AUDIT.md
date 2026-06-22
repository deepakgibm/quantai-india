# Phase 7: CACHE_AUDIT.md

Audit of Dragonfly DB caching layers, TTL, and cache hit metrics.

## 1. Key Formats & Patterns
- **Sectors**: `qai:market:sector_stocks:<SectorName>` (TTL: 600s).
- **Options**: `option_chain:{symbol}:{expiry}` (TTL: 300s).
- **Quotes**: `price:{symbol}` (TTL: None, updated via tick consumers).
- **PCR Expiries**: `option_flow_snapshot:{symbol}:nearest:all` (TTL: None, updated dynamically).

---

## 2. Stampede Protections
- Cache warming locks are implemented on startup (`warm_cache(2000)`) to populate active instrument details and prevent parallel database hits (N+1 query stampedes).
- Centralized cache TTL is managed via settings.
