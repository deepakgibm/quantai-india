import { Order } from "../types";

const API_URL = "http://localhost:8000";
const USE_MOCK = false; // Toggle this to FALSE when backend is running locally
const REQUEST_TIMEOUT = 60000; // 60 second timeout

// Helper for fetch with timeout
const fetchWithTimeout = async (url: string, options: RequestInit = {}, timeout = REQUEST_TIMEOUT): Promise<Response> => {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(id);
    return response;
  } catch (error: any) {
    clearTimeout(id);
    if (error.name === 'AbortError') {
      throw new Error('Request timed out. Please check your connection and try again.');
    }
    throw error;
  }
};

// --- MOCK DATA (Fallback) ---
const MOCK_POSITIONS = [
  { id: '1', symbol: 'RELIANCE', quantity: 50, entryPrice: 2440.0, ltp: 2456.0, pnl: 800 },
  { id: '2', symbol: 'HDFCBANK', quantity: 25, entryPrice: 1455.0, ltp: 1450.0, pnl: -125 },
  { id: '3', symbol: 'INFY', quantity: 100, entryPrice: 1580.0, ltp: 1585.0, pnl: 500 },
];

const MOCK_ORDERS: Order[] = [
  { id: 'ORD-001', timestamp: '10:23:45', stock: 'RELIANCE', type: 'BUY', quantity: 50, entryPrice: 2450.5, exitPrice: 0, status: 'OPEN', algo: 'Trend Finder', pnl: 1250 },
  { id: 'ORD-002', timestamp: '11:15:10', stock: 'TATASTEEL', type: 'SELL', quantity: 200, entryPrice: 110.2, exitPrice: 108.5, status: 'CLOSED', algo: 'Breakout Detector', pnl: 340 },
  { id: 'ORD-003', timestamp: '12:45:00', stock: 'HDFCBANK', type: 'BUY', quantity: 100, entryPrice: 1450.0, exitPrice: 0, status: 'OPEN', algo: 'Top 3 Buy', pnl: -450 },
];

// Helper to get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token');
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
};

export const api = {
  // --- AUTHENTICATION ---
  login: async (email: string, password: string) => {
    if (USE_MOCK) {
      await new Promise(r => setTimeout(r, 800));
      if (email === 'demo@example.com' && password === 'testpass123') {
        localStorage.setItem('access_token', 'mock_token_123');
        return { access_token: 'mock_token_123', token_type: 'bearer' };
      }
      throw new Error("Invalid Credentials");
    }

    try {
      // Use 8s timeout for login - if backend is slow, fallback to demo mode
      const res = await fetchWithTimeout(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      }, 8000);

      if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: 'Login failed' }));
        throw new Error(error.detail || 'Invalid credentials');
      }

      const data = await res.json();
      localStorage.setItem('access_token', data.access_token);
      return data;
    } catch (err: any) {
      console.error("Login error:", err);

      // Fallback for demo credentials when backend is slow/unreachable
      if (email === 'demo@example.com' && password === 'demo123') {
        if (err.message.includes('timed out') || err.message.includes('fetch') || err.message.includes('NetworkError')) {
          console.warn("Backend slow/unreachable - using offline demo mode");
          localStorage.setItem('access_token', 'offline_demo_token');
          return { access_token: 'offline_demo_token', token_type: 'bearer' };
        }
      }

      throw err; // Re-throw for invalid credentials
    }
  },

  getCurrentUser: async () => {
    try {
      const res = await fetchWithTimeout(`${API_URL}/api/auth/me`, {
        headers: getAuthHeaders()
      }, 5000); // Shorter timeout for auth check
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to fetch current user");
    }
    return null;
  },

  signup: async (email: string, password: string, username: string, full_name: string) => {
    if (USE_MOCK) {
      await new Promise(r => setTimeout(r, 1000));
      localStorage.setItem('access_token', 'mock_token_new_user');
      return { access_token: 'mock_token_new_user', token_type: 'bearer' };
    }

    try {
      // Use longer timeout (60s) for signup as database operations can be slow
      const res = await fetchWithTimeout(`${API_URL}/api/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, username, full_name })
      }, REQUEST_TIMEOUT);

      if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: 'Signup failed' }));
        throw new Error(error.detail || 'Signup failed');
      }

      const user = await res.json();
      console.log('Signup successful, attempting login...');

      // After signup, login (also with longer timeout)
      return await api.login(email, password);
    } catch (err: any) {
      console.error("Signup failed:", err);
      throw err;
    }
  },

  firebaseLogin: async (idToken: string, email: string, fullName?: string) => {
    try {
      const res = await fetchWithTimeout(`${API_URL}/api/auth/firebase-login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id_token: idToken,
          email: email,
          full_name: fullName
        })
      });

      if (!res.ok) {
        throw new Error('Firebase login sync failed');
      }

      const data = await res.json();
      localStorage.setItem('access_token', data.access_token);
      return data;
    } catch (err: any) {
      console.error("Firebase login sync error:", err);
      throw err;
    }
  },

  // --- UPSTOX INTEGRATION ---
  getUpstoxAuthUrl: async () => {
    try {
      const res = await fetch(`${API_URL}/api/upstox/auth-url`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to get Upstox auth URL");
    }
    return null;
  },

  upstoxCallback: async (code: string) => {
    try {
      const res = await fetch(`${API_URL}/api/upstox/callback`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ code })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Upstox callback failed");
    }
    return null;
  },

  getUpstoxPortfolio: async () => {
    try {
      const res = await fetch(`${API_URL}/api/upstox/portfolio`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to fetch Upstox portfolio");
    }
    return null;
  },

  getUpstoxPositions: async () => {
    if (USE_MOCK) return MOCK_POSITIONS;

    try {
      const res = await fetch(`${API_URL}/api/upstox/positions`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to fetch Upstox positions");
    }
    return MOCK_POSITIONS;
  },

  // --- TRADING ---
  getDashboardStats: async () => {
    try {
      const res = await fetch(`${API_URL}/api/trading/dashboard`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to fetch dashboard stats");
    }
    return null;
  },

  getMarketIndices: async () => {
    try {
      // Use 15s timeout for market indices (Upstox API can be slow)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000);

      const res = await fetch(`${API_URL}/api/trading/market-indices`, {
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        console.log("Market indices fetched successfully:", data);
        return data;
      } else {
        console.warn(`Market indices API returned ${res.status}: ${res.statusText}`);
      }
    } catch (e: any) {
      console.warn("Failed to fetch market indices:", e.message);
    }
    // Return realistic fallback data (updated Dec 2024)
    console.log("Using fallback market data");
    return [
      { name: "NIFTY 50", value: 23850.15, change: 125.4, percent: 0.53, source: "fallback" },
      { name: "BANK NIFTY", value: 51200.80, change: -89.3, percent: -0.17, source: "fallback" },
      { name: "INDIA VIX", value: 13.25, change: -0.35, percent: -2.58, source: "fallback" }
    ];
  },

  getGainersLosers: async () => {
    return null;
  },

  getSectorHeatmap: async () => {
    try {
      const res = await fetch(`${API_URL}/api/market/heatmap`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to fetch sector heatmap");
    }
    return null;
  },

  getSectorStocks: async (sector: string) => {
    try {
      const res = await fetch(`${API_URL}/api/market/sector-stocks/${sector}`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to fetch sector stocks");
    }
    return null;
  },

  // --- ORDERS ---
  placeOrder: async (symbol: string, order_type: string, quantity: number, price?: number) => {
    try {
      const res = await fetch(`${API_URL}/api/orders/`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ symbol, order_type, quantity, price })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to place order");
    }
    return null;
  },

  getOrders: async () => {
    if (USE_MOCK) return MOCK_ORDERS;

    try {
      const res = await fetch(`${API_URL}/api/orders/`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("API Orders fetch failed");
    }
    return MOCK_ORDERS;
  },

  // --- AI ---
  processAIPrompt: async (prompt: string) => {
    try {
      const res = await fetch(`${API_URL}/api/ai/prompt`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ prompt })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("AI prompt processing failed");
    }
    return null;
  },

  getMarketAnalysis: async () => {
    try {
      const res = await fetch(`${API_URL}/api/ai/market-analysis`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to fetch market analysis");
    }
    return null;
  },

  // --- ALGORITHMS ---
  getAlgorithms: async () => {
    try {
      const res = await fetch(`${API_URL}/api/algorithms/`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to fetch algorithms");
    }
    return [];
  },

  createAlgorithm: async (name: string, description: string, config: any) => {
    try {
      const res = await fetch(`${API_URL}/api/algorithms/`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ name, description, config })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to create algorithm");
    }
    return null;
  },

  updateAlgorithm: async (id: number, updates: any) => {
    try {
      const res = await fetch(`${API_URL}/api/algorithms/${id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(updates)
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to update algorithm");
    }
    return null;
  },

  // --- RISK MANAGEMENT ---
  getRiskSettings: async () => {
    try {
      const res = await fetch(`${API_URL}/api/risk/`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to fetch risk settings");
    }
    return null;
  },

  updateRiskSettings: async (max_capital?: number, max_risk_per_trade?: number) => {
    try {
      const params = new URLSearchParams();
      if (max_capital !== undefined) params.append('max_capital', max_capital.toString());
      if (max_risk_per_trade !== undefined) params.append('max_risk_per_trade', max_risk_per_trade.toString());

      const res = await fetch(`${API_URL}/api/risk/?${params.toString()}`, {
        method: 'PUT',
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to update risk settings");
    }
    return null;
  },

  // --- SETTINGS ---
  getUserSettings: async () => {
    try {
      const res = await fetch(`${API_URL}/api/settings/`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to fetch user settings");
    }
    return null;
  },

  updateUserSettings: async (settings: any) => {
    try {
      const params = new URLSearchParams(settings);
      const res = await fetch(`${API_URL}/api/settings/?${params.toString()}`, {
        method: 'PUT',
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to update settings");
    }
    return null;
  },

  // Legacy support
  getQuote: async (symbol: string) => {
    if (USE_MOCK) return null;

    try {
      const res = await fetch(`${API_URL}/api/upstox/market-quote/${symbol}`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("API Quote fetch failed");
    }
    return null;
  },

  getPositions: async () => {
    return await api.getUpstoxPositions();
  },

  // --- ALPHAPRIME ---
  alphaPrime: {
    // Train the ML model
    train: async (lookback_days: number = 30, n_estimators: number = 100, max_depth: number = 10) => {
      try {
        const res = await fetch(`${API_URL}/api/v1/alpha-prime/train`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ lookback_days, n_estimators, max_depth })
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("AlphaPrime training failed:", e);
      }
      return null;
    },

    // Run backtest
    backtest: async (start_date: string, end_date: string, initial_capital: number = 1000000) => {
      try {
        const res = await fetch(`${API_URL}/api/v1/alpha-prime/backtest`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ start_date, end_date, initial_capital })
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("AlphaPrime backtest failed:", e);
      }
      return null;
    },

    // Get latest signals
    getSignals: async (limit: number = 20, min_confidence: number = 0.7) => {
      try {
        const params = new URLSearchParams({
          limit: limit.toString(),
          min_confidence: min_confidence.toString()
        });
        const res = await fetch(`${API_URL}/api/v1/alpha-prime/signals?${params}`, {
          headers: getAuthHeaders()
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("AlphaPrime signals fetch failed:", e);
      }
      return [];
    },

    // Get configuration
    getConfig: async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/alpha-prime/config`, {
          headers: getAuthHeaders()
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("AlphaPrime config fetch failed:", e);
      }
      return null;
    }
  },

  // --- SCANNER ---
  getStrategies: async () => {
    // Mock strategies for fallback when backend is slow
    const MOCK_STRATEGIES = {
      "Tier 1 - Highest Win Rate": [
        { name: "RSI Mean Reversion", description: "Identifies oversold/overbought conditions using RSI", tier: "Tier 1 - Highest Win Rate", min_bars: 30 },
        { name: "Bollinger Breakout", description: "Detects price breakouts from Bollinger Bands", tier: "Tier 1 - Highest Win Rate", min_bars: 20 },
        { name: "Williams %R", description: "Momentum indicator for overbought/oversold", tier: "Tier 1 - Highest Win Rate", min_bars: 14 }
      ],
      "Tier 2 - Solid Strategies": [
        { name: "MACD Crossover", description: "Classic MACD signal line crossover", tier: "Tier 2 - Solid Strategies", min_bars: 26 },
        { name: "ADX Trend", description: "Trend strength indicator", tier: "Tier 2 - Solid Strategies", min_bars: 14 },
        { name: "Stochastic Oscillator", description: "Momentum comparison indicator", tier: "Tier 2 - Solid Strategies", min_bars: 14 }
      ],
      "Tier 3 - Advanced Strategies": [
        { name: "Ichimoku Cloud", description: "Multi-component trend indicator", tier: "Tier 3 - Advanced Strategies", min_bars: 52 },
        { name: "Fibonacci Bounce", description: "Price reactions at Fibonacci levels", tier: "Tier 3 - Advanced Strategies", min_bars: 50 }
      ]
    };

    try {
      // Use short 5s timeout for strategies
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const res = await fetch(`${API_URL}/api/scanner/strategies`, {
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (res.ok) return await res.json();
      console.warn("Strategies fetch returned:", res.status, res.statusText);
    } catch (e: any) {
      console.warn("Failed to fetch strategies (using mock data):", e.message);
      // Return mock data when backend is slow/unavailable
      return { status: "success", strategies: MOCK_STRATEGIES, total_count: 8, source: "mock" };
    }
    return { status: "success", strategies: MOCK_STRATEGIES, total_count: 8, source: "mock" };
  },

  runScan: async (indices: string[], timeframe: string, strategies: string[]) => {
    try {
      const res = await fetch(`${API_URL}/api/scanner/run`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ indices, timeframe, strategies })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Scan failed:", e);
    }
    return null;
  }
};
