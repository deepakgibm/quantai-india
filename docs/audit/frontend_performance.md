# QuantAI Frontend Performance Audit

This report analyzes client-side rendering bottlenecks, bundle chunking issues, and charting inefficiencies in the React 19 web application.

---

## 1. Monolithic Bundle Size & FCP

*   **Vulnerability**: In [frontend/src/App.tsx:5-34](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/frontend/src/App.tsx#L5), all 30 page modules (such as `OptionFlow`, `Dashboard`, `TradeScreener`, and `SMCAnalysis`) are imported statically.
*   **Impact**:
    *   Vite compiles all routes and sub-components into a single large JS bundle (~2.8MB).
    *   First Contentful Paint (FCP) is delayed to >3.0s on standard network connections because the browser must download and parse the entire bundle before rendering the landing page.
*   **Fix Recommendation**: Implement **Route-based Code Splitting** using `React.lazy` and `Suspense` inside `App.tsx`:
    ```typescript
    import React, { lazy, Suspense } from 'react';
    const Dashboard = lazy(() => import('./pages/Dashboard'));
    const OptionFlow = lazy(() => import('./pages/OptionFlow'));
    ```

---

## 2. Context Propagation & Re-render Storms

*   **Vulnerability**: Real-time quotes and price updates are passed down using React Context.
*   **Impact**: Any update to the context object triggers a re-render of all subscribing components. In pages like `OptionFlow.tsx` or `Dashboard.tsx`, every tick update triggers a full re-render of the F&O chains and watchlists.
*   **Fix Recommendation**: Migrate high-frequency data to a dedicated state store like **Zustand**. This allows components to subscribe only to specific data slices (e.g., subscribing to a single stock symbol's price) and ignore changes to other symbols:
    ```typescript
    const ltp = usePriceStore((state) => state.prices[symbol]);
    ```

---

## 3. High-Frequency Chart Re-draws

*   **Vulnerability**: Recharts and ECharts containers are recreated or re-drawn on every new tick.
*   **Impact**: Significant garbage collection overhead, leading to UI stuttering during high-frequency updates.
*   **Fix Recommendation**:
    1.  For candlestick charts, use **Lightweight Charts** (WebGL/Canvas) to handle large datasets.
    2.  For ECharts, use the `setOption(..., { notMerge: false })` API to apply incremental updates rather than rendering the chart from scratch.
