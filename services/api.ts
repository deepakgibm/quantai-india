// import { Order } from "../types"; // Removed unused import

// ============= API Error Handling =============

/**
 * Structured API error for consistent error handling
 */
export class ApiError extends Error {
  public code: string;
  public status: number;
  public details?: any;

  constructor(code: string, message: string, status: number = 500, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }

  static fromResponse(response: Response, body?: any): ApiError {
    const message = body?.detail || body?.error?.message || response.statusText || 'Request failed';
    const code = body?.error?.code || `HTTP_${response.status}`;
    return new ApiError(code, message, response.status, body);
  }

  static networkError(error: Error): ApiError {
    if (error.message.includes('timed out')) {
      return new ApiError('TIMEOUT', 'Request timed out. Please try again.', 408);
    }
    return new ApiError('NETWORK_ERROR', 'Network error. Please check your connection.', 0);
  }
}

/**
 * Result type for API calls - either success with data or error
 */
export type ApiResult<T> =
  | { success: true; data: T }
  | { success: false; error: ApiError };

// Helper to create success result
const ok = <T>(data: T): ApiResult<T> => ({ success: true, data });

// Helper to create error result  
const err = <T>(error: ApiError): ApiResult<T> => ({ success: false, error });

// ============= Base URL Configuration =============

const getBaseUrl = () => {
  // 1. Check environment variable
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;

  // 2. If running on port 3000 (frontend dev/prod), default to port 8000
  if (typeof window !== 'undefined' && window.location.port === '3000') {
    return `http://${window.location.hostname}:8000`;
  }

  // 3. Fallback to same host/port (for Docker/Nginx scenarios)
  return "";
};

export const API_URL = getBaseUrl();
const REQUEST_TIMEOUT = 30000; // 30 second timeout (reduced from 60s)

// PRODUCTION MODE: Mock data is disabled
const USE_MOCK = false;

// PRODUCTION MODE: No mock data fallbacks
// If real data is unavailable, UI must show "Data unavailable" - never fake numbers



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

// Helper to get auth headers
export const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json'
  };

  // Robust token detection
  const isValidToken = token &&
    token !== 'null' &&
    token !== 'undefined' &&
    token.trim().length > 10; // Basic length check for JWT

  if (isValidToken) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return headers;
};

/**
 * Standardized API request wrapper with proper error handling.
 * Use this for new API calls to get consistent error handling.
 */
export async function apiRequest<T>(
  url: string,
  options: RequestInit = {},
  timeout = REQUEST_TIMEOUT
): Promise<ApiResult<T>> {
  try {
    const response = await fetchWithTimeout(url, options, timeout);

    // Try to parse JSON body
    let body: any;
    try {
      body = await response.json();
    } catch {
      body = null;
    }

    if (!response.ok) {
      return err(ApiError.fromResponse(response, body));
    }

    return ok(body as T);
  } catch (error: any) {
    return err(ApiError.networkError(error));
  }
}

/**
 * Helper for GET requests with auth
 */
export async function apiGet<T>(endpoint: string, timeout?: number): Promise<ApiResult<T>> {
  return apiRequest<T>(`${API_URL}${endpoint}`, { headers: getAuthHeaders() }, timeout);
}

/**
 * Helper for POST requests with auth
 */
export async function apiPost<T>(endpoint: string, body: any, timeout?: number): Promise<ApiResult<T>> {
  return apiRequest<T>(`${API_URL}${endpoint}`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(body)
  }, timeout);
}

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

  verifyToken: async () => {
    try {
      const res = await fetchWithTimeout(`${API_URL}/api/auth/me`, {
        headers: getAuthHeaders()
      }, 5000);
      return res.ok;
    } catch (e) {
      return false;
    }
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
        const errorData = await res.json().catch(() => ({}));
        const message = errorData.detail || `Firebase login sync failed with status ${res.status}`;
        throw new Error(message);
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
    try {
      const res = await fetch(`${API_URL}/api/upstox/positions`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
      console.warn(`Positions API returned ${res.status}: ${res.statusText}`);
    } catch (e) {
      console.warn("Failed to fetch Upstox positions:", e);
    }
    // PRODUCTION: Return empty array, not mock data
    return [];
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
        headers: getAuthHeaders(),
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
    // Return empty array if API fails - no fake data
    console.log("Market indices API failed, returning empty array");
    return [];
  },

  getEnginePerformance: async () => {
    try {
      const res = await fetch(`${API_URL}/api/engines/performance`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to fetch engine performance");
    }
    return null;
  },


  getGainersLosers: async () => {
    try {
      const res = await fetch(`${API_URL}/api/market/top-movers`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to fetch gainers/losers");
    }
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
      const res = await fetch(`${API_URL}/api/market/sector/${encodeURIComponent(sector)}`, {
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
    try {
      const res = await fetch(`${API_URL}/api/orders/`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
      console.warn(`Orders API returned ${res.status}: ${res.statusText}`);
    } catch (e) {
      console.warn("API Orders fetch failed:", e);
    }
    // PRODUCTION: Return empty array, not mock data
    return [];
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


  // --- SCANNER ---
  getStrategies: async () => {
    try {
      // Use short 10s timeout for strategies
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);

      const res = await fetch(`${API_URL}/api/scanner/strategies`, {
        signal: controller.signal,
        headers: getAuthHeaders()
      });
      clearTimeout(timeoutId);

      if (res.ok) return await res.json();
      console.warn("Strategies fetch returned:", res.status, res.statusText);
    } catch (e: any) {
      console.warn("Failed to fetch strategies:", e.message);
    }
    // PRODUCTION: Return null, not mock data. UI should show "Strategies unavailable"
    return null;
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
  },

  // Generic scanner runner for AI endpoints
  runScanner: async (endpoint: string) => {
    try {
      // Ensure endpoint starts with /
      const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
      const res = await fetch(`${API_URL}${path}`, {
        headers: getAuthHeaders()
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error: ${res.status}`);
      }
      return await res.json();
    } catch (e) {
      console.error(`Scanner failed for ${endpoint}:`, e);
      throw e;
    }
  },

  // --- ML FORECAST ---
  getPriceForecast: async (symbol: string, timeframe: string = '5m', horizon: number = 10) => {
    try {
      const params = new URLSearchParams({
        symbol: symbol.toUpperCase(),
        timeframe,
        horizon: horizon.toString()
      });
      const res = await fetch(`${API_URL}/api/forecast/predict?${params}`);
      if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: { message: 'Prediction failed' } }));
        throw new Error(error.detail?.message || 'Prediction failed');
      }
      return await res.json();
    } catch (e) {
      console.error('ML Forecast failed:', e);
      throw e;
    }
  },

  // --- ADMIN & MONITORING ---
  getAdminIndices: async () => {
    const res = await apiGet<any[]>('/api/admin/indices/');
    if (res.success) return res.data;
    throw res.error;
  },

  createAdminIndex: async (name: string, description: string = "", baseIndexId?: number) => {
    const res = await apiPost<any>('/api/admin/indices/', { name, description, base_index_id: baseIndexId });
    if (res.success) return res.data;
    throw res.error;
  },

  addIndexConstituent: async (indexId: number, symbol: string) => {
    const res = await apiPost<any>(`/api/admin/indices/${indexId}/constituents/${symbol}`, {});
    if (res.success) return res.data;
    throw res.error;
  },

  removeIndexConstituent: async (indexId: number, symbol: string) => {
    // using apiRequest because delete isn't in helpers yet
    const res = await apiRequest<any>(`${API_URL}/api/admin/indices/${indexId}/constituents/${symbol}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    if (res.success) return res.data;
    throw res.error;
  },

  deleteAdminIndex: async (indexId: number) => {
    const res = await apiRequest<any>(`${API_URL}/api/admin/indices/${indexId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    if (res.success) return res.data;
    throw res.error;
  },

  getSystemHealth: async () => {
    const res = await apiGet<any>('/api/health/');
    if (res.success) return res.data;
    throw res.error;
  },

  getEtlLogs: async () => {
    // Using existing endpoint
    const res = await apiGet<any>('/api/etl/status');
    if (res.success) return res.data;
    throw res.error;
  },

  getSymbols: async () => {
    try {
      const res = await fetch(`${API_URL}/api/metrics/symbols`, {
        headers: getAuthHeaders()
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Failed to fetch symbols");
    }
    return { symbols: [] };
  }
};

