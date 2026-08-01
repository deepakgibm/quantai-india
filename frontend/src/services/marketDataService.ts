import { api, API_URL } from './api';

export interface MarketQuote {
  symbol: string;
  ltp: number;
  prev_close: number;
  change_pct: number;
  volume: number;
  timestamp: number; // local milliseconds timestamp
  isLive: boolean;
}

type PriceCallback = (quote: MarketQuote) => void;

class MarketDataServiceClass {
  private cache = new Map<string, MarketQuote>();
  private ws: WebSocket | null = null;
  private wsUrl: string;
  private isConnected = false;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private retryCount = 0;
  private maxRetries = 10;
  private baseDelay = 1000;
  
  // symbol -> set of callbacks
  private listeners = new Map<string, Set<PriceCallback>>();
  
  // general callbacks for reconnecting status
  private statusListeners = new Set<(connected: boolean, isReconnecting: boolean) => void>();

  private getWsUrl = () => {
    const baseUrl = API_URL || window.location.origin;
    const proto = baseUrl.startsWith('https') ? 'wss' : 'ws';
    const host = baseUrl.replace(/^https?:\/\//, '');
    const token = localStorage.getItem('access_token');
    const query = token && token !== 'null' && token !== 'undefined' ? `?token=${encodeURIComponent(token)}` : '';
    return `${proto}://${host}/api/ws/live${query}`;
  };

  constructor() {
    this.wsUrl = this.getWsUrl();
    this.connectWS();
  }

  private connectWS() {
    if (this.ws) {
      this.cleanupWS();
    }

    this.wsUrl = this.getWsUrl();
    console.log('MarketDataService: Connecting to WS:', this.wsUrl);
    try {
      const socket = new WebSocket(this.wsUrl);
      this.ws = socket;

      socket.onopen = () => {
        console.log('MarketDataService: WS Connected');
        this.isConnected = true;
        this.retryCount = 0;
        this.notifyStatusListeners();
        
        // Re-subscribe to all active symbols
        const activeSymbols = Array.from(this.listeners.keys());
        if (activeSymbols.length > 0) {
          this.sendWSMessage({
            action: 'subscribe',
            symbols: activeSymbols
          });
        }
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          if (message.type === 'ping') {
            this.sendWSMessage({
              action: 'pong',
              id: message.id
            });
            return;
          }
          
          if (message.event === 'market_tick' && message.data) {
            console.log("WebSocket Tick:", message);
            const symbol = message.symbol;
            const tick = message.data;
            
            // Extract attributes to satisfy WS ticks verification
            const ltp = Number(tick.ltp || tick.last_price || 0);
            const volume = Number(tick.volume || 0);
            const change_pct = Number(tick.change_percent || tick.change_pct || tick.percentage_change || 0);
            let prev_close = Number(tick.prev_close || tick.previous_close || tick.close_price || 0);
            
            if (prev_close <= 0 && ltp > 0 && change_pct !== 0) {
              prev_close = ltp / (1 + change_pct / 100);
            }
            
            const timestamp = tick.timestamp ? new Date(tick.timestamp).getTime() : Date.now();
            
            const quote: MarketQuote = {
              symbol,
              ltp,
              prev_close,
              change_pct,
              volume,
              timestamp,
              isLive: true
            };
            
            this.cache.set(symbol, quote);
            
            // Notify listeners
            const callbacks = this.listeners.get(symbol);
            if (callbacks) {
              callbacks.forEach(cb => cb(quote));
            }
          }
        } catch (e) {
          console.warn('MarketDataService: WS Message parse error:', e);
        }
      };

      socket.onerror = (err) => {
        console.warn('MarketDataService: WS Error:', err);
        socket.close();
      };

      socket.onclose = () => {
        console.log('MarketDataService: WS Closed');
        this.isConnected = false;
        this.ws = null;
        this.notifyStatusListeners();
        this.scheduleReconnect();
      };
    } catch (e) {
      console.error('MarketDataService: WS initialization failed:', e);
      this.scheduleReconnect();
    }
  }

  private cleanupWS() {
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.onmessage = null;
      this.ws.onopen = null;
      try {
        this.ws.close();
      } catch (e) {}
      this.ws = null;
    }
    this.isConnected = false;
    this.notifyStatusListeners();
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    if (this.retryCount < this.maxRetries) {
      const delay = Math.min(30000, this.baseDelay * Math.pow(2, this.retryCount));
      console.log(`MarketDataService: Scheduling WS reconnect in ${delay}ms (attempt ${this.retryCount + 1}/${this.maxRetries})`);
      this.reconnectTimeout = setTimeout(() => {
        this.retryCount++;
        this.connectWS();
      }, delay);
    }
  }

  private sendWSMessage(payload: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  // General Status Listener (connected, isReconnecting)
  public addStatusListener(callback: (connected: boolean, isReconnecting: boolean) => void) {
    this.statusListeners.add(callback);
    callback(this.isConnected, this.retryCount > 0 && !this.isConnected);
    return () => {
      this.statusListeners.delete(callback);
    };
  }

  private notifyStatusListeners() {
    const isReconnecting = this.retryCount > 0 && !this.isConnected;
    this.statusListeners.forEach(cb => cb(this.isConnected, isReconnecting));
  }

  // --- Stale Price Detection ---
  public isPriceStale(timestamp: number): boolean {
    return Date.now() - timestamp > 60000; // 60 seconds stale policy
  }

  // --- Authors & Authoritative Single Sourcing ---

  /**
   * Get the Last Traded Price (LTP) for a symbol with caching and stale fallback
   */
  public async getLTP(symbol: string): Promise<number> {
    const quote = await this.getQuote(symbol);
    return quote.ltp;
  }

  /**
   * Get the full quote (LTP, Volume, Prev Close) with auto-refresh if stale
   */
  public async getQuote(symbol: string): Promise<MarketQuote> {
    const upperSymbol = symbol.toUpperCase().trim ? symbol.toUpperCase().trim() : symbol.toUpperCase();
    const cached = this.cache.get(upperSymbol);
    
    // If cache exists and is fresh, return it
    if (cached && !this.isPriceStale(cached.timestamp)) {
      console.log("Cached Price:", cached.ltp);
      console.log("Cache Timestamp:", new Date(cached.timestamp).toISOString());
      return cached;
    }

    // Otherwise force refresh via REST fallback
    try {
      console.log(`MarketDataService: Fetching live price for ${upperSymbol} via REST`);
      const res = await api.getQuote(upperSymbol);
      if (res && res.status === 'success' && res.data) {
        let quoteData = null;
        const keys = Object.keys(res.data);
        if (keys.length > 0) {
          const matchKey = keys.find(k => k.endsWith(`:${upperSymbol}`) || k === upperSymbol) || keys[0];
          quoteData = res.data[matchKey];
        }

        if (quoteData) {
          const ltp = Number(quoteData.last_price || quoteData.ltp || 0);
          const change_pct = Number(quoteData.change_percent || quoteData.change_pct || quoteData.percentage_change || 0);
          let prev_close = Number(quoteData.close_price || quoteData.previous_close || quoteData.prev_close || 0);
          
          if (prev_close <= 0 && ltp > 0 && change_pct !== 0) {
            prev_close = ltp / (1 + change_pct / 100);
          }
          
          const quote: MarketQuote = {
            symbol: upperSymbol,
            ltp,
            prev_close,
            change_pct,
            volume: Number(quoteData.volume || 0),
            timestamp: Date.now(),
            isLive: true
          };
          this.cache.set(upperSymbol, quote);
          return quote;
        }
      }
    } catch (e) {
      console.error(`MarketDataService: REST price refresh failed for ${upperSymbol}:`, e);
    }

    // Hard fallback to cache if available even if stale, or empty default
    return cached || {
      symbol: upperSymbol,
      ltp: 0,
      prev_close: 0,
      change_pct: 0,
      volume: 0,
      timestamp: Date.now(),
      isLive: false
    };
  }

  /**
   * Alias for getLTP
   */
  public async getLivePrice(symbol: string): Promise<number> {
    return this.getLTP(symbol);
  }

  /**
   * Subscribe to real-time tick updates for a symbol
   */
  public subscribe(symbol: string, callback: PriceCallback): () => void {
    const upperSymbol = symbol.toUpperCase().trim ? symbol.toUpperCase().trim() : symbol.toUpperCase();
    
    let symListeners = this.listeners.get(upperSymbol);
    if (!symListeners) {
      symListeners = new Set();
      this.listeners.set(upperSymbol, symListeners);
      
      // Send WS subscribe message
      if (this.isConnected) {
        this.sendWSMessage({
          action: 'subscribe',
          symbols: [upperSymbol]
        });
      }
    }

    symListeners.add(callback);

    // If we already have a cached price, notify immediately
    const cached = this.cache.get(upperSymbol);
    if (cached) {
      callback(cached);
    } else {
      // Proactively fetch initial quote
      this.getQuote(upperSymbol).then(q => {
        if (q.ltp > 0) callback(q);
      });
    }

    // Return unsubscribe function
    return () => {
      const symList = this.listeners.get(upperSymbol);
      if (symList) {
        symList.delete(callback);
        if (symList.size === 0) {
          this.listeners.delete(upperSymbol);
          if (this.isConnected) {
            this.sendWSMessage({
              action: 'unsubscribe',
              symbols: [upperSymbol]
            });
          }
        }
      }
    };
  }
}

export const MarketDataService = new MarketDataServiceClass();
