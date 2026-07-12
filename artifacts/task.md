# Task Checklist: Codebase Audit & Feature Consolidation

- [ ] 1. Backend Service Cleanups & Deletion
  - [ ] Delete `backend/services/top_movers_service.py`
  - [ ] Delete `backend/services/yearly_breakout_engine.py`
- [ ] 2. Backend Scanner API Refactoring
  - [ ] Refactor `backend/api/scanners.py` to use `Week52BreakoutService`
- [ ] 3. Backend Heatmap & Sector APIs Price Manager Alignment
  - [ ] Refactor `backend/api/heatmap.py` to use `PriceService`
  - [ ] Refactor `backend/api/sector_analysis.py` to use `PriceService`
- [ ] 4. Frontend Routing & Sidebar Consolidation
  - [ ] Modify `frontend/src/App.tsx` routes (route trade-screener to Scanner, sector-analysis to SectorHeatmapPage)
  - [ ] Modify `frontend/src/components/Sidebar.tsx` navigation (merge sector pages, remove TradeScreener)
- [ ] 5. Frontend Pages Consolidation & Porting
  - [ ] Delete `frontend/src/pages/TradeScreener.tsx`
  - [ ] Delete `frontend/src/pages/SectorAnalysisPage.tsx`
  - [ ] Port comparative metrics & Recharts BarCharts into `frontend/src/pages/SectorHeatmapPage.tsx` with a togglable view mode
- [ ] 6. Verification and Integration Tests
  - [ ] Run test suite to verify code compilation and API integrity
  - [ ] Generate final `walkthrough.md`
