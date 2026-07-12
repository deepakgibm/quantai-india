# Technical Memory: Business Rules

## 1. Market Hours & Swaps
*   **Active Session**: Monday to Friday, 9:15 AM to 3:30 PM IST. Live ticks are streamed directly via WebSockets.
*   **Off-Hours Switch**: Outside of active sessions, the system defaults to the last verified trading day's EOD data in PostgreSQL.

## 2. Subscription Plans
*   **Standard**: Limited to basic watchlist checks and index heatmaps.
*   **Premium**: Complete access to AI Swarm debates, custom backtester simulations, and Minervini scanners.
