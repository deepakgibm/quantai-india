# Phase 10: OPTION_FLOW_REPORT.md

Verification of option chain expiries, Put-Call Ratio (PCR), and Max Pain analytics.

## 1. Option Chain & Expiries
- Option chain endpoints fetch strikes directly from the Dragonfly cache (`option_chain:{symbol}:{expiry}`).
- Non-F&O symbols (checked via `has_derivatives(symbol)`) correctly skip option calculations and return clean error structures.

## 2. Calculations Accuracy
- **PCR**: Calculated as `Total Put Open Interest / Total Call Open Interest` using `DerivativesService.calculate_pcr`.
- **Max Pain**: Calculated by computing cumulative option seller loss across all candidate strikes.
- **Implied Volatility (IV)**: Standardized by `DerivativesService.calculate_iv` to ensure uniform percentage scaling.
