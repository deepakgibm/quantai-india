# Frontend Architecture

The QuantAI India frontend is a Single Page Application (SPA) built using React, TypeScript, and Vite, styled with Tailwind CSS, and optimized for real-time financial dashboards.

## Routing & Layout Structure
The entry point of the app is [App.tsx](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/frontend/src/App.tsx) which wraps the application in `QueryClientProvider` (TanStack Query) and `GlobalSymbolProvider`. 

Routing is handled via `react-router-dom` with a `ProtectedRoute` component wrapping authenticated pages.
- **Mobile Menu**: Mobile devices use a toggleable hamburger button triggering a slide-out drawer sidebar.
- **Sidebar Layout**: Contains navigation icons, user profile info, subscription tier display, and dark/light mode toggle.
- **Full-Bleed Layouts**: Pages like the `QuantWorkspace` or `ExperimentLab` use a full-width/height flex canvas to accommodate dense charts and backtesting logs.

---

## Page Inventory & Routes

| Route | Page Component | Key Functionality | API Endpoints Called |
| :--- | :--- | :--- | :--- |
| `/` | `LandingPage` | Public marketing, core features list, call to action | None |
| `/login` / `/signup`| `Login` / `Signup` | User authentication forms | `/api/auth/firebase-login`, `/api/auth/signup` |
| `/dashboard` | `Dashboard` | Real-time P&L, capital usage stats, indices, top gainers | `/api/trading/stats`, `/api/trading/market-indices`, `/api/trading/top-gainers` |
| `/ai-prompt` | `AIPrompt` | Chat canvas for conversational Gemini queries | `/api/ai/prompt` |
| `/scanner` | `Scanner` | Real-time scanners (Momentum, Mean Reversion, Gap, etc.) | `/api/scanner/active` |
| `/sector-heatmap`| `SectorHeatmapPage` | Treemap sector performance relative-strength weights | `/api/heatmap?mode={mode}&timeframe={tf}` |
| `/sector-analysis`| `SectorAnalysisPage` | Sector trends, relative strength tables | `/api/sector-analysis` |
| `/volume-profile` | `VolumeProfilePage` | POC, Value Area High/Low histogram overlays | `/api/volume-profile?symbol={s}` |
| `/volatility` | `VolatilityDashboard`| Option VIX spreads, IV rank charts | `/api/volatility/stats` |
| `/option-flow` | `OptionFlow` | Options sweeps, block trades filter table | `/api/option-flow/sweeps` |
| `/quant-workspace`| `QuantWorkspace` | Code editor workspace, backtesting & bot runner tab | `/api/workspace/files`, `/api/backtest/run` |
| `/watchlist` | `Watchlist` | User custom symbols list with live P&L | `/api/watchlist` |
| `/institutional` | `InstitutionalScanner`| NSE Bulk/Block deal FII footprint scan | `/api/institutional/flows` |
| `/diagnostics` | `PriceDiagnosticPanel`| Cache status check and data staleness checks | `/api/system/health`, `/api/upstox/status` |

---

## State Management Architecture

```
┌────────────────────────────────────────────────────────┐
│                      Global Providers                  │
│  ┌───────────────────────┐   ┌──────────────────────┐  │
│  │      AuthContext      │   │ GlobalSymbolProvider │  │
│  └───────────────────────┘   └──────────────────────┘  │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│                    TanStack Query Cache                │
│  - GET requests cached for 3 seconds                   │
│  - In-flight request deduplication                     │
│  - Automatic stale-while-revalidate                    │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│                   Component Local State                │
│  - useState, useRef (e.g. AbortController references)  │
└────────────────────────────────────────────────────────┘
```

1. **Global Contexts**:
   - **`AuthContext`**: Manages current user state, Firebase credentials token sync, and token refresh loops.
   - **`GlobalSymbolProvider`**: Broadcasts the currently active stock symbol (e.g., RELIANCE) across pages so clicking a symbol in the Watchlist updates the charts on the Volume Profile page.
2. **Server State Caching**:
   - Handled via **TanStack Query**. Requests are cached, preventing repetitive API hits when navigating tabs.
   - Secondary cache inside [api.ts](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/frontend/src/services/api.ts) caches fetch promises for 3000ms.
3. **In-Flight Cancellation**:
   - Custom React pages implement `abortControllerRef = useRef<AbortController | null>(null)`. 
   - Before firing a new data fetch, any previous in-flight request is explicitly aborted using `abortControllerRef.current.abort()` to prevent race conditions and network hogging.

---

## API Consumption Client ([api.ts](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/frontend/src/services/api.ts))
- **Base URL**: Dynamically resolved. Resolves to `http://localhost:8000` in local dev or empty string `""` in production (delegating routing to the Nginx reverse proxy).
- **Interceptors**: 
  - Automatically fetches the active Firebase JWT token (`auth.currentUser?.getIdToken()`) and appends it as `Bearer <Token>` in headers.
  - Intercepts `401 Unauthorized` responses, attempts to call `refreshBackendToken()`, and silently retries the original request upon success.
- **Timeout**: Enforces a strict 30-second timeout on requests using `AbortController` timeout hooks.
