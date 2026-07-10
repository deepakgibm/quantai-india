// import { Order } from "../types"; // Removed unused import
import { auth } from '../lib/firebase';

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
export type ApiResult<T> = {
  success: boolean;
  data?: T;
  error?: ApiError;
};

// Helper to create success result
const ok = <T>(data: T): ApiResult<T> => ({ success: true, data });

// Helper to create error result  
const err = <T>(error: ApiError): ApiResult<T> => ({ success: false, error });

// ============= Base URL Configuration =============

const getBaseUrl = () => {
  // 1. If we're in production mode (inside Docker/Nginx), use relative paths
  // This allows the Nginx proxy to handle routing to the backend
  if (import.meta.env.PROD) {
    return "";
  }

  // 2. Check environment variable
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;

  // 3. If running on port 3000 (dev mode), default to port 8000
  if (typeof window !== 'undefined' && window.location.port === '3000') {
    return `http://${window.location.hostname}:8000`;
  }

  // 4. Fallback to relative path
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

// ============= Token Refresh & Interception =============

const originalFetch = window.fetch;
let refreshPromise: Promise<boolean> | null = null;

const getFirebaseUser = (): Promise<any> => {
  return new Promise((resolve) => {
    if (auth.currentUser) {
      resolve(auth.currentUser);
      return;
    }
    const unsubscribe = auth.onAuthStateChanged((user) => {
      unsubscribe();
      resolve(user);
    });
  });
};

export const refreshBackendToken = async (): Promise<boolean> => {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      // 1. Try to refresh via backend refresh_token first (local auth lifecycle)
      const storedRefreshToken = localStorage.getItem('refresh_token');
      if (storedRefreshToken && storedRefreshToken !== 'null' && storedRefreshToken !== 'undefined') {
        console.log("[Auth] Attempting backend token refresh via refresh_token...");
        try {
          const res = await originalFetch(`${API_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: storedRefreshToken })
          });
          if (res.ok) {
            const data = await res.json();
            if (data && data.access_token) {
              localStorage.setItem('access_token', data.access_token);
              if (data.refresh_token) {
                localStorage.setItem('refresh_token', data.refresh_token);
              }
              console.log("[Auth] Backend token successfully refreshed via refresh_token.");
              return true;
            }
          }
        } catch (e) {
          console.warn("[Auth] Direct backend refresh failed:", e);
        }
      }

      // 2. Fall back to Firebase ID token refresh
      const currentUser = await getFirebaseUser();
      if (!currentUser) {
        console.warn("[Auth] No Firebase user found for token refresh.");
        return false;
      }

      console.log("[Auth] Refreshing backend JWT using Firebase ID token...");
      const idToken = await currentUser.getIdToken(true);
      
      const res = await originalFetch(`${API_URL}/api/auth/firebase-login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id_token: idToken,
          email: currentUser.email!,
          full_name: currentUser.displayName || undefined
        })
      });

      if (!res.ok) {
        throw new Error(`Firebase login sync failed with status ${res.status}`);
      }

      const data = await res.json();
      if (data && data.access_token) {
        localStorage.setItem('access_token', data.access_token);
        if (data.refresh_token) {
          localStorage.setItem('refresh_token', data.refresh_token);
        }
        console.log("[Auth] Backend token successfully refreshed and stored.");
        return true;
      }
      return false;
    } catch (err) {
      console.error("[Auth] Failed to refresh backend token:", err);
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
};

const authenticatedFetch = async (
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> => {
  const urlString = typeof input === 'string' ? input : (input as any).url || String(input);
  
  const isBackendRequest = urlString.startsWith('/api/') || 
                           urlString.startsWith('api/') ||
                           (API_URL && urlString.startsWith(API_URL));

  if (!isBackendRequest) {
    return originalFetch(input, init);
  }

  const isAuthRequest = urlString.includes('/api/auth/firebase-login') || 
                        urlString.includes('/api/auth/login') || 
                        urlString.includes('/api/auth/signup');

  if (isAuthRequest) {
    return originalFetch(input, init);
  }

  const authHeaders = getAuthHeaders();
  const requestHeaders: Record<string, string> = {};

  if (init && init.headers) {
    Object.entries(init.headers).forEach(([k, v]) => {
      requestHeaders[k] = String(v);
    });
  }

  if (!requestHeaders['Content-Type'] && init && init.body && typeof init.body === 'string') {
    requestHeaders['Content-Type'] = 'application/json';
  }

  if (authHeaders['Authorization']) {
    requestHeaders['Authorization'] = authHeaders['Authorization'];
  } else {
    delete requestHeaders['Authorization'];
  }

  const requestOptions = {
    ...init,
    headers: requestHeaders
  };

  let response = await originalFetch(input, requestOptions);

  if (response.status === 401) {
    console.warn(`[Auth] Received 401 from ${urlString}. Attempting token refresh...`);
    const refreshed = await refreshBackendToken();
    if (refreshed) {
      console.log(`[Auth] Token refreshed successfully. Retrying request to ${urlString}...`);
      
      const newAuthHeaders = getAuthHeaders();
      const retryHeaders = { ...requestHeaders };
      
      if (newAuthHeaders['Authorization']) {
        retryHeaders['Authorization'] = newAuthHeaders['Authorization'];
      } else {
        delete retryHeaders['Authorization'];
      }

      const retryOptions = {
        ...init,
        headers: retryHeaders
      };
      
      response = await originalFetch(input, retryOptions);
    } else {
      console.error(`[Auth] Token refresh failed. Propagating 401 for ${urlString}.`);
    }
  }

  return response;
};

// Override window.fetch globally to intercept 401s and automatically refresh tokens
window.fetch = authenticatedFetch;
const fetch = authenticatedFetch;

const inFlightRequests = new Map<string, Promise<any>>();
const apiCache = new Map<string, { data: any; expiry: number }>();

/**
 * Standardized API request wrapper with proper error handling.
 * Use this for new API calls to get consistent error handling.
 */
export async function apiRequest<T>(
  url: string,
  options: RequestInit = {},
  timeout = REQUEST_TIMEOUT
): Promise<ApiResult<T>> {
  const method = options.method || 'GET';

  if (method === 'GET') {
    const cacheKey = url;

    // Check Cache
    const cached = apiCache.get(cacheKey);
    if (cached && cached.expiry > Date.now()) {
      return cached.data;
    }

    // Check In-flight
    let inFlight = inFlightRequests.get(cacheKey);
    if (!inFlight) {
      inFlight = (async () => {
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

          const result = ok(body as T);

          // Cache for 3 seconds
          apiCache.set(cacheKey, {
            data: result,
            expiry: Date.now() + 3000
          });

          return result;
        } catch (error: any) {
          return err(ApiError.networkError(error));
        } finally {
          inFlightRequests.delete(cacheKey);
        }
      })();
      inFlightRequests.set(cacheKey, inFlight);
    }
    return inFlight;
  }

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
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token);
      }
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
    // Check if there is already a global in-flight promise for this exact function
    const existingPromise = (window as any).__firebaseLoginPromise;
    if (existingPromise) {
      console.log("[Auth] Reusing in-flight firebaseLogin promise...");
      return existingPromise;
    }

    const promise = (async () => {
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
      } finally {
        delete (window as any).__firebaseLoginPromise;
      }
    })();

    (window as any).__firebaseLoginPromise = promise;
    return promise;
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


  getGainersLosers: async (refresh?: boolean) => {
    const url = refresh ? '/api/market/top-movers?refresh=true' : '/api/market/top-movers';
    const res = await apiGet<any>(url);
    if (res.success) return res.data;
    console.warn("Failed to fetch gainers/losers:", res.error.message);
    return null;
  },

  getSectorHeatmap: async () => {
    const res = await apiGet<any>('/api/market/heatmap');
    if (res.success) return res.data;
    console.warn("Failed to fetch sector heatmap:", res.error.message);
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
    const res = await apiGet<any[]>('/api/orders/');
    if (res.success) return res.data;
    console.warn("API Orders fetch failed:", res.error.message);
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
        const errData = await res.json().catch(() => ({}));
        // Standardize error message extraction from QuantAI envelope or FastAPI detail
        const errorMessage = errData.error?.message || errData.message || errData.detail || `API error: ${res.status}`;
        throw new ApiError('SCAN_ERROR', errorMessage, res.status);
      }
      return await res.json();
    } catch (e) {
      console.error(`Scanner failed for ${endpoint}:`, e);
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



  // --- INSTITUTIONAL SCREENER ---
  getScreenerRankings: async (params: any = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        query.append(key, String(value));
      }
    });
    const res = await apiGet<any>(`/api/screener/rankings?${query.toString()}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getConvictionList: async (listType: "BUY" | "AVOID" = "BUY", scoreDate?: string) => {
    const query = new URLSearchParams({ list_type: listType });
    if (scoreDate) query.append("score_date", scoreDate);
    const res = await apiGet<any>(`/api/screener/conviction-list?${query.toString()}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getAvoidList: async (scoreDate?: string) => {
    const query = new URLSearchParams();
    if (scoreDate) query.append("score_date", scoreDate);
    const res = await apiGet<any>(`/api/screener/avoid-list?${query.toString()}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getScreenerSectorRotation: async (scoreDate?: string) => {
    const query = new URLSearchParams();
    if (scoreDate) query.append("score_date", scoreDate);
    const res = await apiGet<any>(`/api/screener/sector-rotation?${query.toString()}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getScreenerPortfolios: async (scoreDate?: string) => {
    const query = new URLSearchParams();
    if (scoreDate) query.append("score_date", scoreDate);
    const res = await apiGet<any>(`/api/screener/portfolios?${query.toString()}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getScreenerStatus: async () => {
    const res = await apiGet<any>('/api/screener/status');
    if (res.success) return res.data;
    throw res.error;
  },

  runScreener: async (skipFinancials: boolean = false, topN?: number) => {
    const query = new URLSearchParams({ skip_financials: String(skipFinancials) });
    if (topN) query.append("top_n", String(topN));
    const res = await apiPost<any>(`/api/screener/run?${query.toString()}`, {});
    if (res.success) return res.data;
    throw res.error;
  },

  // --- SIGNAL BOT ---
  startBot: async (universe?: string) => {
    const res = await apiPost<any>('/api/bot/run', universe ? { universe } : {});
    if (res.success) return res.data;
    throw res.error;
  },

  getBotStatus: async (runId: string) => {
    const res = await apiGet<any>(`/api/bot/status/${runId}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getBotResults: async (runId: string) => {
    const res = await apiGet<any>(`/api/bot/results/${runId}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getLastBotRun: async () => {
    const res = await apiGet<any>('/api/bot/last-run');
    if (res.success) return res.data;
    throw res.error;
  },

  getBotHistory: async (limit: number = 10) => {
    const res = await apiGet<any>(`/api/bot/history?limit=${limit}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getBotSchedulerStatus: async () => {
    const res = await apiGet<any>('/api/bot/scheduler-status');
    if (res.success) return res.data;
    throw res.error;
  },

  // --- NEW MODULES ---
  searchStocks: async (query: string) => {
    const res = await apiGet<any>(`/api/search/stocks?q=${encodeURIComponent(query)}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getVolatility: async (symbol: string, days: number) => {
    const res = await apiGet<any>(`/api/volatility/${symbol}?lookback_days=${days}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getOptionFlow: async (symbol: string, expiry: string = '', strike_range: string = '', bypassCache: boolean = false) => {
    let url = `/api/option-flow/${symbol}`;
    const params = [];
    if (expiry) params.push(`expiry=${encodeURIComponent(expiry)}`);
    if (strike_range) params.push(`strike_range=${encodeURIComponent(strike_range)}`);
    if (bypassCache) params.push(`bypass_cache=true`);
    if (params.length > 0) {
      url += `?${params.join('&')}`;
    }
    const res = await apiGet<any>(url);
    if (res.success) return res.data;
    throw res.error;
  },

  getOptionFlowChart: async (symbol: string, interval: string, lookbackDays: number = 90) => {
    const res = await apiGet<any>(`/api/option-flow/${symbol}/chart?interval=${interval}&lookback_days=${lookbackDays}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getOptionFlowExpiries: async (symbol: string, bypassCache: boolean = false) => {
    let url = `/api/option-flow/${symbol}/expiries`;
    if (bypassCache) {
      url += `?bypass_cache=true`;
    }
    const res = await apiGet<any>(url);
    if (res.success) return res.data;
    throw res.error;
  },

  getUpstoxStatus: async () => {
    const res = await apiGet<any>('/api/upstox/status');
    if (res.success) return res.data;
    throw res.error;
  },

  getHeatmapData: async (mode: string, timeframe: string = "1D") => {
    const res = await apiGet<any>(`/api/heatmap?mode=${mode}&timeframe=${timeframe}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getSectorAnalysisData: async (timeframe: string = "1D") => {
    const res = await apiGet<any>(`/api/sector-analysis?timeframe=${timeframe}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getVolumeProfileData: async (symbol: string, lookback: number) => {
    const res = await apiGet<any>(`/api/volume-profile?symbol=${encodeURIComponent(symbol)}&lookback=${lookback}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getVolumeProfileSummary: async (symbol: string) => {
    const res = await apiGet<any>(`/api/volume-profile/summary?symbol=${encodeURIComponent(symbol)}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getVolumeProfileVerdict: async (symbol: string) => {
    const res = await apiGet<any>(`/api/volume-profile/ai-verdict?symbol=${encodeURIComponent(symbol)}`);
    if (res.success) return res.data;
    throw res.error;
  },

  // --- SAAS ENTERPRISE MODULES ---
  getSubscriptionDashboard: async () => {
    const res = await apiGet<any>('/api/saas/subscription');
    if (res.success) return res.data;
    throw res.error;
  },

  createSubscriptionCheckout: async (planName: string, couponCode?: string) => {
    let url = `/api/saas/subscription/checkout?plan_name=${planName}`;
    if (couponCode) url += `&coupon_code=${encodeURIComponent(couponCode)}`;
    const res = await apiPost<any>(url, {});
    if (res.success) return res.data;
    throw res.error;
  },

  verifySubscriptionPayment: async (subscriptionId: number, razorpayPaymentId: string, razorpaySignature: string = 'mock_sig') => {
    const res = await apiPost<any>(`/api/saas/subscription/verify?subscription_id=${subscriptionId}&razorpay_payment_id=${razorpayPaymentId}&razorpay_signature=${razorpaySignature}`, {});
    if (res.success) return res.data;
    throw res.error;
  },

  getSMCAnalysis: async (symbol: string) => {
    const res = await apiGet<any>(`/api/saas/smc?symbol=${encodeURIComponent(symbol)}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getPatternRecognition: async (symbol: string) => {
    const res = await apiGet<any>(`/api/saas/patterns?symbol=${encodeURIComponent(symbol)}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getAcademyCourses: async () => {
    const res = await apiGet<any>('/api/saas/academy');
    if (res.success) return res.data;
    throw res.error;
  },

  getAcademyCourseDetails: async (courseId: number) => {
    const res = await apiGet<any>(`/api/saas/academy/course/${courseId}`);
    if (res.success) return res.data;
    throw res.error;
  },

  completeAcademyLesson: async (courseId: number, lessonIdx: number) => {
    const res = await apiPost<any>(`/api/saas/academy/course/${courseId}/complete-lesson?lesson_idx=${lessonIdx}`, {});
    if (res.success) return res.data;
    throw res.error;
  },

  submitAcademyQuiz: async (courseId: number, answers: number[]) => {
    const res = await apiPost<any>(`/api/saas/academy/course/${courseId}/submit-quiz`, answers);
    if (res.success) return res.data;
    throw res.error;
  },

  getAffiliateDashboard: async () => {
    const res = await apiGet<any>('/api/saas/affiliate');
    if (res.success) return res.data;
    throw res.error;
  },

  explainTradingSignal: async (symbol: string, signalType: string, price: number, conviction: string) => {
    const res = await apiGet<any>(`/api/ai/explain-signal?symbol=${encodeURIComponent(symbol)}&signal_type=${encodeURIComponent(signalType)}&price=${price}&conviction=${encodeURIComponent(conviction)}`);
    if (res.success) return res.data;
    throw res.error;
  },

  getAIMarketSummary: async () => {
    const res = await apiGet<any>('/api/ai/market-summary');
    if (res.success) return res.data;
    throw res.error;
  },
};

