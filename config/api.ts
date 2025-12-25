/**
 * API Configuration Constants
 * Centralized configuration for backend API URLs
 */

// Backend API base URL - change this for different environments
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// WebSocket base URL
export const WS_BASE_URL = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');

// API Endpoints
export const API_ENDPOINTS = {
    // Auth
    AUTH: {
        LOGIN: `${API_BASE_URL}/api/auth/login`,
        REGISTER: `${API_BASE_URL}/api/auth/register`,
        ME: `${API_BASE_URL}/api/auth/me`,
    },
    // Trading
    TRADING: {
        DASHBOARD: `${API_BASE_URL}/api/trading/dashboard`,
        MARKET_INDICES: `${API_BASE_URL}/api/trading/market-indices`,
        GAINERS_LOSERS: `${API_BASE_URL}/api/trading/gainers-losers`,
    },
    // AI
    AI: {
        PROMPT: `${API_BASE_URL}/api/ai/prompt`,
        SENTIMENT: `${API_BASE_URL}/api/ai/sentiment`,
        TREND_FINDER: `${API_BASE_URL}/api/ai/trend-finder`,
        BREAKOUT_DETECTOR: `${API_BASE_URL}/api/ai/breakout-detector`,
        TOP5_PICKS: `${API_BASE_URL}/api/ai/top5-picks`,
        MOMENTUM_SCANNER: `${API_BASE_URL}/api/ai/momentum-scanner`,
        MEAN_REVERSION: `${API_BASE_URL}/api/ai/mean-reversion`,
        GAP_SCANNER: `${API_BASE_URL}/api/ai/gap-scanner`,
        RELATIVE_STRENGTH: `${API_BASE_URL}/api/ai/relative-strength`,
        VWAP_SCANNER: `${API_BASE_URL}/api/ai/vwap-scanner`,
        SR_BOUNCE: `${API_BASE_URL}/api/ai/sr-bounce`,
    },
    // Scanner
    SCANNER: {
        MOMENTUM: `${API_BASE_URL}/api/scanner/momentum`,
        WEEK52_BREAKOUTS: `${API_BASE_URL}/api/scanner/week52-breakouts`,
        WS: `${WS_BASE_URL}/api/scanner/ws/scanner`,
    },
    // Quant
    QUANT: {
        SYMBOLS: `${API_BASE_URL}/api/quant/symbols`,
        STRATEGIES: `${API_BASE_URL}/api/quant/strategies`,
        BACKTEST: `${API_BASE_URL}/api/quant/backtest/run`,
        OPTIMIZE: `${API_BASE_URL}/api/quant/optimize/run`,
    },
    // Alerts
    ALERTS: {
        MONITORS: `${API_BASE_URL}/api/alerts/monitors`,
        CREATE_MONITOR: `${API_BASE_URL}/api/alerts/monitor/create`,
    },
    // ETL
    ETL: {
        STATUS: `${API_BASE_URL}/api/v1/etl/status`,
    },
};

// Helper function to build endpoint URLs with path parameters
export const buildUrl = (base: string, params: Record<string, string> = {}): string => {
    let url = base;
    Object.entries(params).forEach(([key, value]) => {
        url = url.replace(`:${key}`, encodeURIComponent(value));
    });
    return url;
};

export default API_ENDPOINTS;
