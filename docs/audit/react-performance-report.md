# QuantAI React Performance Audit

This report reviews the performance characteristics of the frontend React application, identifying render hotspots, missing memoization, and component re-render cascades.

## 1. OptionFlow Terminal Hotspots (`OptionFlow.tsx`)
* **Issues**:
  * Renders a large grid of option strike prices, calls, and puts.
  * Every incoming tick message via WebSocket triggers a state update on the parent component, causing the *entire* strike grid to re-render.
  * Lack of `useMemo` on the grid rows and `useCallback` on event handlers.
* **Render Count Estimates**: ~120 renders per minute during active market hours.
* **Potential FPS Issues**: Drops to 15-20 FPS on tick updates.
* **Optimization Plan**:
  * Extract the strike grid row into a standalone component wrapped in `React.memo`.
  * Memoize calculated column values (e.g. PCR, Implied Volatility spreads) using `useMemo`.

## 2. Watchlist Component Re-renders (`Watchlist.tsx`)
* **Issues**:
  * The symbol table re-renders all rows when any single stock's price updates.
* **Optimization Plan**:
  * Wrap table rows in `React.memo` with a custom comparison function checking only the symbol and current price.
  * Implement `VirtualizedTable` for watchlists with more than 50 stocks.

## 3. Context Re-render Cascades (`QuantContext.tsx`)
* **Issues**:
  * `QuantContext` stores global states including active symbols, active strategy, scan results, and connection status.
  * Any update to the connection status causes all consumer components (including the heavy charts) to re-render.
* **Optimization Plan**:
  * Split `QuantContext` into smaller, focused contexts: `ConnectionContext`, `SymbolSelectionContext`, and `StrategyContext`.
