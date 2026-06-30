import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { 
  TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight, RefreshCw, 
  BarChart2, List, ShieldAlert, Award, Layers, AlertTriangle, 
  Gauge, Zap, Clock, Activity, Target, ShieldCheck, Flame, Info,
  Maximize2, Minimize2
} from 'lucide-react';
import { useGlobalSymbol } from '../contexts/GlobalSymbolContext';
import { api } from '../services/api';
import GlobalSymbolSearch from '../components/GlobalSymbolSearch';
import ErrorCard from '../components/ErrorCard';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, 
  Legend, ResponsiveContainer, LineChart, Line, AreaChart, Area 
} from 'recharts';
import { createChart, ColorType, ISeriesApi, UTCTimestamp, CrosshairMode } from 'lightweight-charts';
import { isFOSymbol } from '../utils/fnoUtils';


// TypeScript Definitions matching Backend response
interface StrikeData {
  strike_price: number;
  call: {
    oi: number;
    oi_change: number;
    volume: number;
    ltp: number;
    bid: number;
    ask: number;
    premium: number;
    iv: number;
    buildup: string;
    sentiment?: string;
    confidence_score?: number;
    gex: number;
    buildup_intensity: number;
  };
  put: {
    oi: number;
    oi_change: number;
    volume: number;
    ltp: number;
    bid: number;
    ask: number;
    premium: number;
    iv: number;
    buildup: string;
    sentiment?: string;
    confidence_score?: number;
    gex: number;
    buildup_intensity: number;
  };
}

interface BlockDeal {
  strike_price: number;
  type: 'CE' | 'PE';
  ltp: number;
  volume: number;
  premium: number;
  oi: number;
}

interface SmartMoneyActivity {
  strike_price: number;
  type: string;
  reason: string;
  severity: 'Low' | 'Medium' | 'High';
}

interface TradeSignal {
  signal: 'BUY' | 'SELL' | 'BREAKOUT' | 'BREAKDOWN' | 'REVERSAL' | 'NO TRADE';
  directional_bias: string;
  reason: string[];
  entry_zone: string;
  stop_loss: number;
  target_levels: number[];
  confidence: 'Low' | 'Medium' | 'High' | 'Very High';
  confidence_score: number;
  equity_contribution?: number;
  options_contribution?: number;
  bullish_evidence?: string[];
  bearish_evidence?: string[];
  key_indicators?: Record<string, string>;
}

interface MarketCorrelation {
  sector_name: string;
  sector_change_pct: number | null;
  nifty_change_pct: number | null;
  stock_change_pct: number | null;
  relative_strength: string;
  beta: number | null;
  correlation_score: number | null;
}

interface OptionFlowData {
  status: string;
  symbol: string;
  expiry: string;
  spot_price: number;
  spot_change: number;
  spot_change_pct: number;
  total_call_oi: number;
  total_put_oi: number;
  total_call_volume: number;
  total_put_volume: number;
  total_call_premium: number;
  total_put_premium: number;
  net_flow: number;
  buy_sell_ratio: number;
  pcr_oi: number;
  pcr_volume: number;
  sentiment: string;
  sentiment_score: number;
  max_pain: number;
  support_strike: number;
  resistance_strike: number;
  market_correlation: MarketCorrelation;
  smart_money_activity: SmartMoneyActivity[];
  trade_signals: TradeSignal;
  pcr_trend: Array<{ time: string; pcr: number }>;
  premium_flow_history: Array<{ time: string; net_premium: number }>;
  strikes: StrikeData[];
  block_deals: BlockDeal[];
}

interface ChartCandle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema_20: number;
  ema_50: number;
  vwap: number;
}

interface AdvancedChartData {
  symbol: string;
  interval: string;
  candles: ChartCandle[];
  support_zones: number[];
  resistance_zones: number[];
  volume_profile: Array<{ price: number; volume: number }>;
  smart_money_zones: Array<{ price_low: number; price_high: number; timestamp: string }>;
  breakout_markers: any[];
}

interface StrikeGridRowProps {
  strike: any;
  idx: number;
  isAtm: boolean;
  isHighestCallOi: boolean;
  isHighestPutOi: boolean;
}

const StrikeGridRow: React.FC<StrikeGridRowProps> = React.memo(({
  strike,
  idx,
  isAtm,
  isHighestCallOi,
  isHighestPutOi
}) => {
  const rowBg = isAtm 
    ? 'bg-[rgba(59,130,246,0.15)] border-l-4 border-l-[#3B82F6] hover:bg-[#334155]' 
    : idx % 2 === 0 ? 'bg-[#1E293B] hover:bg-[#334155]' : 'bg-[#263244] hover:bg-[#334155]';
  
  const ceBuildup = strike.call?.buildup;
  const peBuildup = strike.put?.buildup;

  const ceBuildupBadge = 
    ceBuildup === 'Long Build-Up' ? 'text-term-bullish' :
    ceBuildup === 'Short Build-Up' ? 'text-term-bearish' :
    ceBuildup === 'Long Unwinding' ? 'text-term-neutral' :
    ceBuildup === 'Short Covering' ? 'text-term-info' : 'text-slate-500';

  const peBuildupBadge = 
    peBuildup === 'Long Build-Up' ? 'text-term-bullish' :
    peBuildup === 'Short Build-Up' ? 'text-term-bearish' :
    peBuildup === 'Long Unwinding' ? 'text-term-neutral' :
    peBuildup === 'Short Covering' ? 'text-term-info' : 'text-slate-500';

  return (
    <tr className={`${rowBg} transition-colors h-[42px]`}>
      {/* CALLS */}
      <td className="px-4 py-2">
        <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${ceBuildupBadge}`}>
          {ceBuildup}
        </span>
      </td>
      <td className={`px-4 py-2 text-term-text-secondary ${isHighestCallOi ? 'bg-[rgba(16,185,129,0.15)] font-bold text-term-bullish' : ''}`}>{strike.call?.oi?.toLocaleString() ?? '0'}</td>
      <td className={`px-4 py-2 font-bold ${(strike.call?.oi_change ?? 0) >= 0 ? 'text-term-bullish' : 'text-term-bearish'}`}>
        {(strike.call?.oi_change ?? 0) >= 0 ? '+' : ''}{strike.call?.oi_change?.toLocaleString() ?? '0'}
      </td>
      <td className="px-4 py-2 text-term-text-muted">{strike.call?.volume?.toLocaleString() ?? '0'}</td>
      <td className="px-4 py-2 text-term-text-muted">{(strike.call?.iv ?? 0).toFixed(1)}%</td>
      <td className="px-4 py-2 font-semibold text-term-bullish border-r border-slate-800/60">
        ₹{(strike.call?.ltp ?? 0).toFixed(2)}
      </td>
      
      {/* STRIKE */}
      <td className={`px-4 py-2 text-center font-bold border-r border-slate-800/60 ${isAtm ? 'text-term-info bg-[rgba(59,130,246,0.1)]' : 'text-term-text-primary'}`}>
        {strike.strike_price.toFixed(1)}
      </td>
      
      {/* PUTS */}
      <td className="px-4 py-2 font-semibold text-term-bullish">
        ₹{(strike.put?.ltp ?? 0).toFixed(2)}
      </td>
      <td className="px-4 py-2 text-term-text-muted">{(strike.put?.iv ?? 0).toFixed(1)}%</td>
      <td className="px-4 py-2 text-term-text-muted">{strike.put?.volume?.toLocaleString() ?? '0'}</td>
      <td className={`px-4 py-2 font-bold ${(strike.put?.oi_change ?? 0) >= 0 ? 'text-term-bullish' : 'text-term-bearish'}`}>
        {(strike.put?.oi_change ?? 0) >= 0 ? '+' : ''}{strike.put?.oi_change?.toLocaleString() ?? '0'}
      </td>
      <td className={`px-4 py-2 text-term-text-secondary ${isHighestPutOi ? 'bg-[rgba(239,68,68,0.15)] font-bold text-term-bearish' : ''}`}>{strike.put?.oi?.toLocaleString() ?? '0'}</td>
      <td className="px-4 py-2">
        <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${peBuildupBadge}`}>
          {peBuildup}
        </span>
      </td>
    </tr>
  );
});

interface OptionFlowProps {
  isWidget?: boolean;
}

export const OptionFlow: React.FC<OptionFlowProps> = React.memo(({ isWidget = false }) => {
  const { selectedSymbol } = useGlobalSymbol();
  const [data, setData] = useState<OptionFlowData | null>(null);
  const [expiries, setExpiries] = useState<string[]>([]);
  const [selectedExpiry, setSelectedExpiry] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isNonFno, setIsNonFno] = useState(false);
  const [chartError, setChartError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'chain' | 'heatmap' | 'blocks' | 'summary'>('chain');
  const [brokerConnected, setBrokerConnected] = useState<boolean | null>(null);
  const [dataSource, setDataSource] = useState<string>('upstox');
  const [chartTimeframe, setChartTimeframe] = useState<'1d' | '5m' | '15m' | '30m'>('1d');
  
  // Advanced Chart State
  const [chartData, setChartData] = useState<AdvancedChartData | null>(null);
  const [chartLoading, setChartLoading] = useState(false);
  const chartContainerRef = useRef<HTMLDivElement | null>(null);
  const chartCardRef = useRef<HTMLDivElement | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const lightweightChartRef = useRef<any>(null);
  const candlestickSeriesRef = useRef<any>(null);
  const ema20SeriesRef = useRef<any>(null);
  const ema50SeriesRef = useRef<any>(null);
  const vwapSeriesRef = useRef<any>(null);
  const volumeSeriesRef = useRef<any>(null);
  const chartMarkersRef = useRef<any[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const chartCacheRef = useRef<Record<string, AdvancedChartData>>({});
  const lastChartTimeRef = useRef<any>(null);
  const chartPollFailuresRef = useRef<number>(0);
  const maxRetries = 2;

  // Fetch Broker Connection Status
  const checkBrokerStatus = async () => {
    try {
      const response = await api.getUpstoxStatus();
      if (response && response.status === 'success' && response.upstox) {
        setBrokerConnected(response.upstox.connected);
      } else {
        setBrokerConnected(false);
      }
    } catch (err) {
      console.warn('[OptionFlow] Failed to fetch broker status:', err);
      setBrokerConnected(false);
    }
  };

  // Fetch Expiries
  const fetchExpiries = async (symbol: string, bypassCache = false) => {
    const clean = symbol.toUpperCase().replace("NSE:", "").trim();
    if (!isFOSymbol(clean)) {
      setIsNonFno(true);
      setLoading(false);
      return;
    }

    setIsNonFno(false);
    setError(null);
    try {
      const response = await api.getOptionFlowExpiries(symbol, bypassCache);
      if (response && response.success && response.data && Array.isArray(response.data.expiries)) {
        setExpiries(response.data.expiries);
        setError(null);
        if (response.data.expiries.length > 0) {
          if (!response.data.expiries.includes(selectedExpiry)) {
            setSelectedExpiry(response.data.expiries[0]);
          }
        } else {
          setSelectedExpiry('');
          setLoading(false);
        }
      } else if (response && response.error) {
        setError(response.error.message || 'Failed to retrieve option chain expiries.');
        setLoading(false);
      } else {
        setError(response?.message || 'Failed to retrieve option chain expiries.');
        setLoading(false);
      }
    } catch (err: any) {
      console.warn('[OptionFlow] Fetch expiries error:', err);
      if (err.status === 400 || err.message?.includes('F&O')) {
        setIsNonFno(true);
      } else {
        setError(err.message || 'Failed to connect to Option Flow Expiries API.');
        setLoading(false);
      }
    }
  };

  // Fetch Option Flow Details
  const fetchOptionFlow = async (symbol: string, expiry: string, forceSilent = false, bypassCache = false, attempt = 0) => {
    const clean = symbol.toUpperCase().replace("NSE:", "").trim();
    if (isNonFno || !isFOSymbol(clean)) {
      setLoading(false);
      return;
    }

    if (!forceSilent && attempt === 0) {
      setLoading(true);
    }
    if (attempt === 0) {
      setError(null);
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      const response = await api.getOptionFlow(symbol, expiry, '', bypassCache);
      
      if (response && response.success && response.data) {
        setData(response.data);
        console.log("Relative Strength API Response", JSON.stringify(response.data.market_correlation, null, 2));
        // console.log("Heatmap Classification", response.data.strikes); // REMOVED to avoid confusion
        setError(null);
        setDataSource(response.status === 'stale' || response.source === 'stale_cache' ? 'stale_cache' : response.source || 'upstox');
        setLastUpdated(new Date().toLocaleTimeString());
        
        if ((response.status === 'stale' || response.source === 'stale_cache') && response._diagnostics) {
          console.warn('[OptionFlow] Serving STALE CACHE data:', response._diagnostics);
        }
      } else if (response && response.error) {
        if (attempt < maxRetries && !forceSilent) {
          const backoffMs = Math.min(500 * Math.pow(2, attempt), 4000);
          if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
          retryTimeoutRef.current = setTimeout(() => {
            fetchOptionFlow(symbol, expiry, forceSilent, true, attempt + 1);
          }, backoffMs);
          return;
        }
        if (!forceSilent || !data) {
          setError(response.error.message || 'Option flow data currently unavailable.');
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        if (attempt < maxRetries && !forceSilent) {
          const backoffMs = Math.min(500 * Math.pow(2, attempt), 4000);
          if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
          retryTimeoutRef.current = setTimeout(() => {
            fetchOptionFlow(symbol, expiry, forceSilent, true, attempt + 1);
          }, backoffMs);
          return;
        } else if (!forceSilent || !data) {
          setError(err.message || 'Failed to connect to Option Flow API.');
        }
      }
    } finally {
      if (!forceSilent) {
        setLoading(false);
      }
    }
  };

  // Fetch Advanced Chart Overlay Data
  const fetchChartData = async (symbol: string, timeframe: '1d' | '5m' | '15m' | '30m') => {
    const clean = symbol.toUpperCase().replace("NSE:", "").trim();
    if (!isFOSymbol(clean)) {
      setChartLoading(false);
      return;
    }
    
    // Resolve dynamic historical data availability depending on selected timeframe
    let lookbackDays = 90;
    if (timeframe === '1d') {
      lookbackDays = 730; // Load 2 Years of daily candles
    } else if (timeframe === '30m') {
      lookbackDays = 365; // Load 1 Year of 30m candles
    } else if (timeframe === '15m') {
      lookbackDays = 180; // Load 6 Months of 15m candles
    } else if (timeframe === '5m') {
      lookbackDays = 90;  // Load 90 Days of 5m candles
    }
    
    const cacheKey = `${symbol}:${timeframe}:${lookbackDays}`;
    if (chartCacheRef.current[cacheKey]) {
      setChartError(null);
      setChartData(chartCacheRef.current[cacheKey]);
      return;
    }
    
    setChartLoading(true);
    setChartError(null);
    try {
      const response = await api.getOptionFlowChart(clean, timeframe, lookbackDays);
      // Handle double-nested data payload structure if API returns {success: true, data: {...}}
      const chartPayload = response?.data && response?.success ? response.data : response;
      
      if (chartPayload) {
        chartCacheRef.current[cacheKey] = chartPayload;
        setChartData(chartPayload);
      }
    } catch (err: any) {
      console.warn('[OptionFlow] Failed to fetch advanced chart overlays:', err);
      setChartError(err?.message || 'Failed to connect to Option Flow Chart API.');
    } finally {
      setChartLoading(false);
    }
  };

  // Run on Symbol change to reset states and load expiries
  useEffect(() => {
    const init = async () => {
      setData(null);
      setChartData(null);
      setExpiries([]);
      setSelectedExpiry('');
      setError(null);
      setChartError(null);
      
      const clean = selectedSymbol.toUpperCase().replace("NSE:", "").trim();
      const fnoValid = isFOSymbol(clean);
      
      if (!fnoValid) {
        setIsNonFno(true);
        setLoading(false);
      } else {
        setIsNonFno(false);
        setLoading(true);
        try {
          await Promise.all([
            fetchExpiries(selectedSymbol),
            checkBrokerStatus()
          ]);
        } catch (e) {
          console.warn('[OptionFlow] Initialization failed:', e);
        } finally {
          setLoading(false);
        }
      }
    };
    init();
  }, [selectedSymbol]);

  // Run on Symbol or Timeframe change - ALWAYS load the price chart!
  useEffect(() => {
    fetchChartData(selectedSymbol, chartTimeframe);
  }, [selectedSymbol, chartTimeframe]);

  // Run on Expiry change - load F&O option metrics when expiry is selected
  useEffect(() => {
    if (selectedExpiry && !isNonFno) {
      fetchOptionFlow(selectedSymbol, selectedExpiry);
    }
  }, [selectedSymbol, selectedExpiry, isNonFno]);

  // Hook for incremental updates polling
  useEffect(() => {
    const clean = selectedSymbol.toUpperCase().replace("NSE:", "").trim();

    const fetchIncrementalChartData = async () => {
      if (!lightweightChartRef.current || !candlestickSeriesRef.current) return;
      
      const timeToComparable = (time: any): number => {
        if (time === null || time === undefined) return 0;
        
        // Lightweight Charts business day object: { year, month, day }
        if (typeof time === 'object' && time.year && time.month && time.day) {
          return time.year * 10000 + time.month * 100 + time.day;
        }
        
        // String date: e.g. "2026-06-30" or ISO string
        if (typeof time === 'string') {
          if (time.includes('T')) {
            return Math.floor(new Date(time).getTime() / 1000);
          }
          const parts = time.split('-');
          if (parts.length === 3) {
            const y = parseInt(parts[0], 10);
            const m = parseInt(parts[1], 10);
            const d = parseInt(parts[2], 10);
            if (!isNaN(y) && !isNaN(m) && !isNaN(d)) {
              return y * 10000 + m * 100 + d;
            }
          }
          return Math.floor(new Date(time).getTime() / 1000);
        }
        
        // Number: Unix timestamp
        if (typeof time === 'number') {
          if (time > 10000000000) {
            return Math.floor(time / 1000);
          }
          return time;
        }
        
        return 0;
      };

      try {
        const response = await api.getOptionFlowChart(clean, chartTimeframe, 2);
        chartPollFailuresRef.current = 0; // Reset failures on success!
        const chartPayload = response?.data && response?.success ? response.data : response;

        if (chartPayload && chartPayload.candles && chartPayload.candles.length > 0) {
          // 1. Update Existing Candlestick Series Instantly
          chartPayload.candles.forEach((c: any) => {
            let t = c.time;
            if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
            else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
            
            const lastTime = lastChartTimeRef.current;
            const newComp = timeToComparable(t);
            const lastComp = timeToComparable(lastTime);
            
            if (lastTime && newComp < lastComp) {
              console.warn(
                `[OptionFlow] Update rejected: Incoming timestamp is older than last candle.`,
                `Previous time:`, lastTime,
                `Incoming time:`, t,
                `Reason: Out of order timestamp (Incoming: ${newComp} < Last: ${lastComp})`
              );
              return; // Skip this outdated candle update
            }

            if (candlestickSeriesRef.current) {
              candlestickSeriesRef.current.update({
                time: t as UTCTimestamp,
                open: Number(c.open),
                high: Number(c.high),
                low: Number(c.low),
                close: Number(c.close)
              });
            }
            if (ema20SeriesRef.current && c.ema_20 !== undefined && !isNaN(c.ema_20)) {
              ema20SeriesRef.current.update({ time: t as UTCTimestamp, value: Number(c.ema_20) });
            }
            if (ema50SeriesRef.current && c.ema_50 !== undefined && !isNaN(c.ema_50)) {
              ema50SeriesRef.current.update({ time: t as UTCTimestamp, value: Number(c.ema_50) });
            }
            if (vwapSeriesRef.current && c.vwap !== undefined && !isNaN(c.vwap)) {
              vwapSeriesRef.current.update({ time: t as UTCTimestamp, value: Number(c.vwap) });
            }
            if (volumeSeriesRef.current && c.volume !== undefined && !isNaN(c.volume)) {
              volumeSeriesRef.current.update({
                time: t as UTCTimestamp,
                value: Number(c.volume),
                color: Number(c.close) >= Number(c.open) ? '#10b98155' : '#ef444455'
              });
            }
            
            // Set lastChartTimeRef to the newest processed timestamp
            if (newComp >= lastComp) {
              lastChartTimeRef.current = t;
            }
          });

          // 2. Accumulate/Merge Smart Money Zones
          if (chartPayload.smart_money_zones && chartPayload.smart_money_zones.length > 0) {
            // Keep at most 5 recent smart money zones
            const mergedZones = [...chartPayload.smart_money_zones];
            // Render zones (not shown here)
          }

          // 3. Accumulate/Merge Breakout Markers
          if (chartPayload.breakout_markers && chartPayload.breakout_markers.length > 0 && candlestickSeriesRef.current) {
            const existingMarkersMap = new Map(chartMarkersRef.current.map(m => [m.time, m]));
            chartPayload.breakout_markers.forEach((m: any) => {
              let t = m.time;
              if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
              else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
              existingMarkersMap.set(t, { ...m, time: t });
            });
            const mergedMarkers = Array.from(existingMarkersMap.values()).sort((a: any, b: any) => {
              const tA = typeof a.time === 'number' ? a.time : new Date(a.time).getTime();
              const tB = typeof b.time === 'number' ? b.time : new Date(b.time).getTime();
              return tA - tB;
            });
            candlestickSeriesRef.current.setMarkers(mergedMarkers);
            chartMarkersRef.current = mergedMarkers;
          }
        }
      } catch (err) {
        chartPollFailuresRef.current += 1;
        console.warn(`[OptionFlow] Failed to fetch incremental chart updates (consecutive failures: ${chartPollFailuresRef.current}):`, err);
      }
    };

    const interval = setInterval(() => {
      if (selectedExpiry && !isNonFno) {
        fetchOptionFlow(selectedSymbol, selectedExpiry, true);
        checkBrokerStatus();
        
        // Polling back-off logic for incremental updates
        if (chartPollFailuresRef.current < 3) {
          fetchIncrementalChartData();
        } else if (chartPollFailuresRef.current % 10 === 0) {
          console.log('[OptionFlow] Retrying incremental chart poll after cool-down...');
          fetchIncrementalChartData();
        }
      }
    }, 15000);

    return () => {
      clearInterval(interval);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, [selectedSymbol, selectedExpiry, isNonFno, chartTimeframe]);

  // Fullscreen Toggler
  const toggleFullscreen = useCallback(() => {
    if (!chartCardRef.current) return;
    
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(err => {
        console.error('[Fullscreen] Exit failed:', err);
      });
    } else {
      chartCardRef.current.requestFullscreen().catch(err => {
        console.error('[Fullscreen] Request failed:', err);
      });
    }
  }, []);

  // Listen for browser fullscreen change events (handles ESC key natively)
  useEffect(() => {
    const handleFullscreenChange = () => {
      const active = document.fullscreenElement === chartCardRef.current;
      console.log('[Fullscreen] Native event triggered. Active status:', active);
      setIsFullscreen(active);
      
      // Trigger a resize manually on state switch to ensure chart fills element instantly
      setTimeout(() => {
        const chart = lightweightChartRef.current;
        const container = chartContainerRef.current;
        if (chart && container) {
          console.log(`[Fullscreen Resize] Resizing chart to container width: ${container.clientWidth}, height: ${container.clientHeight}`);
          chart.resize(container.clientWidth, container.clientHeight);
        }
      }, 50);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  // =========================================================================
  // TradingView Lightweight Chart Setup & Lifecycle
  // =========================================================================
  
  // 1. Initialize Chart Instance (Created once on symbol or timeframe change)
  useEffect(() => {
    if (!chartContainerRef.current) return;
    
    // Destroy previous chart if it exists
    if (lightweightChartRef.current) {
      try {
        lightweightChartRef.current.remove();
      } catch (e) {
        console.warn('Error removing chart:', e);
      }
      lightweightChartRef.current = null;
      candlestickSeriesRef.current = null;
      volumeSeriesRef.current = null;
      ema20SeriesRef.current = null;
      ema50SeriesRef.current = null;
      vwapSeriesRef.current = null;
      chartMarkersRef.current = [];
    }
    
    lastChartTimeRef.current = null;
    setChartError(null);

    const container = chartContainerRef.current;
    console.log(`[Chart Init] Creating chart. Container clientWidth: ${container.clientWidth}, height: 700`);
    
    try {
      const chart = createChart(container, {
        width: container.clientWidth || 800,
        height: 700,
        layout: {
          background: { type: ColorType.Solid, color: '#090d16' },
          textColor: '#64748b',
        },
        grid: {
          vertLines: { color: '#1e293b' },
          horzLines: { color: '#1e293b' },
        },
        crosshair: {
          mode: CrosshairMode.Normal,
        },
        rightPriceScale: {
          visible: true,
          borderColor: '#1e293b',
        },
        timeScale: {
          borderColor: '#1e293b',
          timeVisible: true,
          secondsVisible: false,
        },
      });

      lightweightChartRef.current = chart;

      // Create candlestick series
      const candlestickSeries = chart.addCandlestickSeries({
        upColor: '#10b981',
        downColor: '#ef4444',
        borderVisible: false,
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444',
      });
      candlestickSeriesRef.current = candlestickSeries;

      // Create volume series
      const volumeSeries = chart.addHistogramSeries({
        color: '#26a69a',
        priceFormat: { type: 'volume' },
        priceScaleId: '',
      });
      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });
      volumeSeriesRef.current = volumeSeries;

      // Create EMA20 series
      const ema20Series = chart.addLineSeries({
        color: '#F59E0B',
        lineWidth: 1,
        title: 'EMA 20'
      });
      ema20SeriesRef.current = ema20Series;

      // Create EMA50 series
      const ema50Series = chart.addLineSeries({
        color: '#3b82f6',
        lineWidth: 1,
        title: 'EMA 50'
      });
      ema50SeriesRef.current = ema50Series;

      // Create VWAP series
      const vwapSeries = chart.addLineSeries({
        color: '#8B5CF6',
        lineWidth: 1,
        title: 'VWAP'
      });
      vwapSeriesRef.current = vwapSeries;

      // Double click to toggle fullscreen and reset zoom
      const handleDoubleClick = () => {
        chart.timeScale().fitContent();
        toggleFullscreen();
      };
      container.addEventListener('dblclick', handleDoubleClick);
      (container as any)._dblClickHandler = handleDoubleClick;

      // Handle Resize using ResizeObserver
      const resizeObserver = new ResizeObserver(entries => {
        if (!entries || entries.length === 0) return;
        const { width, height } = entries[0].contentRect;
        if (lightweightChartRef.current && width > 0 && height > 0) {
          console.log(`[Chart Resize] Resizing chart to clientWidth: ${width}, height: ${height}`);
          lightweightChartRef.current.resize(width, height);
        }
      });
      resizeObserver.observe(container);
      (container as any)._resizeObserver = resizeObserver;

    } catch (e: any) {
      console.error('[Chart Init] Fatal error during chart creation:', e);
      setChartError(e.message || e.toString());
    }

    return () => {
      // Cleanup chart on unmount or symbol/timeframe changes
      if (lightweightChartRef.current) {
        try { lightweightChartRef.current.remove(); } catch (ex) {}
        lightweightChartRef.current = null;
        candlestickSeriesRef.current = null;
        volumeSeriesRef.current = null;
        ema20SeriesRef.current = null;
        ema50SeriesRef.current = null;
        vwapSeriesRef.current = null;
        chartMarkersRef.current = [];
      }
      if (chartContainerRef.current) {
        const c = chartContainerRef.current;
        if ((c as any)._resizeObserver) (c as any)._resizeObserver.disconnect();
        if ((c as any)._dblClickHandler) c.removeEventListener('dblclick', (c as any)._dblClickHandler);
      }
    };
  }, [selectedSymbol, chartTimeframe, toggleFullscreen]);

  // 2. Draw/Update Chart Data (Runs when chartData is fetched or refreshed)
  useEffect(() => {
    const chart = lightweightChartRef.current;
    const candlestickSeries = candlestickSeriesRef.current;
    const volumeSeries = volumeSeriesRef.current;
    const ema20Series = ema20SeriesRef.current;
    const ema50Series = ema50SeriesRef.current;
    const vwapSeries = vwapSeriesRef.current;

    if (!chart || !candlestickSeries || !volumeSeries || !ema20Series || !ema50Series || !vwapSeries || !chartData || !chartData.candles || chartData.candles.length === 0) {
      return;
    }

    // Populate candle data
    const candlesData = (chartData.candles || [])
      .filter((c: any) => c && c.time && c.open != null && c.high != null && c.low != null && c.close != null && !isNaN(c.close))
      .map((c: any) => {
        let t = c.time;
        if (typeof t === 'string' && t.includes('T')) {
          t = Math.floor(new Date(t).getTime() / 1000);
        } else if (typeof t === 'number' && t > 10000000000) {
          t = Math.floor(t / 1000);
        }
        return {
          time: t,
          open: Number(c.open),
          high: Number(c.high),
          low: Number(c.low),
          close: Number(c.close)
        };
      });

    try {
      candlestickSeries.setData(candlesData);
      if (candlesData.length > 0) {
        lastChartTimeRef.current = candlesData[candlesData.length - 1].time;
        console.log(`[Chart Data] Set candlestick data. Count: ${candlesData.length}, lastTime:`, lastChartTimeRef.current);
      }
    } catch (e) {
      console.error('[Chart Data] Error setting candlestick data:', e);
    }

    // Populate volume data
    const volumeData = (chartData.candles || [])
      .filter((c: any) => c && c.time && c.volume != null && !isNaN(c.volume))
      .map((c: any) => {
        let t = c.time;
        if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
        else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
        return {
          time: t,
          value: Number(c.volume),
          color: Number(c.close) >= Number(c.open) ? '#10b98155' : '#ef444455'
        };
      });
    try {
      volumeSeries.setData(volumeData);
    } catch (e) {
      console.error('[Chart Data] Error setting volume data:', e);
    }

    // Populate EMA20 data
    const ema20Data = (chartData.candles || [])
      .filter((c: any) => c && c.time && c.ema_20 != null && !isNaN(c.ema_20))
      .map((c: any) => {
        let t = c.time;
        if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
        else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
        return { time: t, value: Number(c.ema_20) };
      });
    try {
      ema20Series.setData(ema20Data);
    } catch (e) {
      console.error('[Chart Data] Error setting EMA20 data:', e);
    }

    // Populate EMA50 data
    const ema50Data = (chartData.candles || [])
      .filter((c: any) => c && c.time && c.ema_50 != null && !isNaN(c.ema_50))
      .map((c: any) => {
        let t = c.time;
        if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
        else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
        return { time: t, value: Number(c.ema_50) };
      });
    try {
      ema50Series.setData(ema50Data);
    } catch (e) {
      console.error('[Chart Data] Error setting EMA50 data:', e);
    }

    // Populate VWAP data
    const vwapData = (chartData.candles || [])
      .filter((c: any) => c && c.time && c.vwap != null && !isNaN(c.vwap))
      .map((c: any) => {
        let t = c.time;
        if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
        else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
        return { time: t, value: Number(c.vwap) };
      });
    try {
      vwapSeries.setData(vwapData);
    } catch (e) {
      console.error('[Chart Data] Error setting VWAP data:', e);
    }

    // Clear previous price lines if they exist
    if ((candlestickSeries as any)._priceLines) {
      (candlestickSeries as any)._priceLines.forEach((l: any) => {
        try { candlestickSeries.removePriceLine(l); } catch (ex) {}
      });
    }
    (candlestickSeries as any)._priceLines = [];

    // Support Zones
    if (chartData.support_zones && chartData.support_zones.length > 0) {
      chartData.support_zones.forEach(price => {
        const line = candlestickSeries.createPriceLine({
          price: price,
          color: '#10B981',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: 'Support',
        });
        (candlestickSeries as any)._priceLines.push(line);
      });
    }

    // Resistance Zones
    if (chartData.resistance_zones && chartData.resistance_zones.length > 0) {
      chartData.resistance_zones.forEach(price => {
        const line = candlestickSeries.createPriceLine({
          price: price,
          color: '#EF4444',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: 'Resistance',
        });
        (candlestickSeries as any)._priceLines.push(line);
      });
    }

    // Set markers for breakouts/breakdowns
    if (chartData.breakout_markers && chartData.breakout_markers.length > 0) {
      try {
        const validMarkers = chartData.breakout_markers.map((m: any) => {
          let t = m.time;
          if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
          else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
          return { ...m, time: t };
        });
        
        console.log(`[Chart Data] Setting ${validMarkers.length} markers`);
        candlestickSeries.setMarkers(validMarkers);
        chartMarkersRef.current = validMarkers;
      } catch (e) {
        console.error('[Chart Data] Error setting markers:', e);
      }
    } else {
      candlestickSeries.setMarkers([]);
      chartMarkersRef.current = [];
    }

    // Auto-fit contents
    try {
      chart.timeScale().fitContent();
    } catch (e) {}

    // Task 6 - Validate Candle Counts Log
    if (candlesData.length > 0) {
      const getFormattedDate = (timeVal: any) => {
        if (typeof timeVal === 'number') {
          return new Date(timeVal * 1000).toISOString().split('T')[0];
        } else {
          return String(timeVal).split('T')[0];
        }
      };
      const oldestTs = getFormattedDate(candlesData[0].time);
      const latestTs = getFormattedDate(candlesData[candlesData.length - 1].time);
      console.log(`[Chart History Validation]\nTimeframe: ${chartTimeframe}\nHistory Range: ${chartTitleRange}\nNumber of Candles: ${candlesData.length}\nOldest Timestamp: ${oldestTs}\nLatest Timestamp: ${latestTs}`);
    }

    // Tooltip rendering logic
    const lastCandle = candlesData[candlesData.length - 1];
    const updateTooltipText = (candle: any, volumeVal?: number, ema20Val?: number, ema50Val?: number, vwapVal?: number) => {
      const timeEl = document.getElementById('chart-tooltip-time');
      const ohlcEl = document.getElementById('chart-tooltip-ohlc');
      const volEl = document.getElementById('chart-tooltip-volume');
      const indEl = document.getElementById('chart-tooltip-indicators');

      if (timeEl && ohlcEl && volEl && indEl) {
        if (candle) {
          const dateStr = typeof candle.time === 'number'
            ? new Date(candle.time * 1000).toLocaleString()
            : String(candle.time);
          timeEl.textContent = dateStr;
          ohlcEl.innerHTML = `O: <span class="text-white">${Number(candle.open).toFixed(2)}</span> H: <span class="text-emerald-400">${Number(candle.high).toFixed(2)}</span> L: <span class="text-red-400">${Number(candle.low).toFixed(2)}</span> C: <span class="text-white">${Number(candle.close).toFixed(2)}</span>`;
        } else {
          timeEl.textContent = '';
          ohlcEl.innerHTML = '';
        }

        if (volumeVal != null) {
          volEl.textContent = `Vol: ${volumeVal.toLocaleString()}`;
        } else {
          volEl.textContent = '';
        }

        let indStr = '';
        if (ema20Val != null && !isNaN(ema20Val)) indStr += `EMA20: ${ema20Val.toFixed(2)} `;
        if (ema50Val != null && !isNaN(ema50Val)) indStr += `EMA50: ${ema50Val.toFixed(2)} `;
        if (vwapVal != null && !isNaN(vwapVal)) indStr += `VWAP: ${vwapVal.toFixed(2)} `;
        indEl.textContent = indStr.trim();
      }
    };

    if (lastCandle) {
      const lastIdx = (chartData.candles || []).length - 1;
      const lastRaw = (chartData.candles || [])[lastIdx];
      updateTooltipText(
        lastCandle, 
        lastRaw?.volume, 
        lastRaw?.ema_20, 
        lastRaw?.ema_50, 
        lastRaw?.vwap
      );
    }

    const crosshairHandler = (param: any) => {
      const timeEl = document.getElementById('chart-tooltip-time');
      const ohlcEl = document.getElementById('chart-tooltip-ohlc');
      const volEl = document.getElementById('chart-tooltip-volume');
      const indEl = document.getElementById('chart-tooltip-indicators');

      if (!timeEl || !ohlcEl || !volEl || !indEl) return;

      if (
        !param.time ||
        param.point === undefined ||
        param.point.x < 0 ||
        param.point.y < 0
      ) {
        if (lastCandle) {
          const lastIdx = (chartData.candles || []).length - 1;
          const lastRaw = (chartData.candles || [])[lastIdx];
          updateTooltipText(
            lastCandle, 
            lastRaw?.volume, 
            lastRaw?.ema_20, 
            lastRaw?.ema_50, 
            lastRaw?.vwap
          );
        }
        return;
      }

      const dateStr = typeof param.time === 'number'
        ? new Date(param.time * 1000).toLocaleString()
        : String(param.time);
      
      timeEl.textContent = dateStr;

      const candle = param.seriesData.get(candlestickSeries);
      if (candle) {
        const c = candle as any;
        ohlcEl.innerHTML = `O: <span class="text-white">${c.open.toFixed(2)}</span> H: <span class="text-emerald-400">${c.high.toFixed(2)}</span> L: <span class="text-red-400">${c.low.toFixed(2)}</span> C: <span class="text-white">${c.close.toFixed(2)}</span>`;
      } else {
        ohlcEl.innerHTML = '';
      }

      const vol = param.seriesData.get(volumeSeries);
      if (vol) {
        const v = vol as any;
        volEl.textContent = `Vol: ${v.value.toLocaleString()}`;
      } else {
        volEl.textContent = '';
      }

      const ema20 = param.seriesData.get(ema20Series);
      const ema50 = param.seriesData.get(ema50Series);
      const vwap = param.seriesData.get(vwapSeries);
      
      let indStr = '';
      if (ema20) indStr += `EMA20: ${(ema20 as any).value.toFixed(2)} `;
      if (ema50) indStr += `EMA50: ${(ema50 as any).value.toFixed(2)} `;
      if (vwap) indStr += `VWAP: ${(vwap as any).value.toFixed(2)} `;
      indEl.textContent = indStr.trim();
    };
    chart.subscribeCrosshairMove(crosshairHandler);

    return () => {
      chart.unsubscribeCrosshairMove(crosshairHandler);
    };
  }, [chartData]); // Note: No cleanup function returned here to prevent destruction on data updates. Cleanup is in useEffect #1.

  // 3. Global cleanup on unmount
  useEffect(() => {
    return () => {
      if (chartContainerRef.current) {
        const container = chartContainerRef.current;
        if ((container as any)._resizeObserver) {
          (container as any)._resizeObserver.disconnect();
        }
        if ((container as any)._dblClickHandler) {
          container.removeEventListener('dblclick', (container as any)._dblClickHandler);
        }
      }
      if (lightweightChartRef.current) {
        try { lightweightChartRef.current.remove(); } catch (e) {}
      }
    };
  }, []);

  const handleRetry = () => {
    setLoading(true);
    fetchExpiries(selectedSymbol, true);
    fetchChartData(selectedSymbol, chartTimeframe);
    checkBrokerStatus();
  };

  // Find ATM strike for highlighting
  const atmStrike = useMemo(() => {
    if (!data || !data.strikes || data.strikes.length === 0) return null;
    return data.max_pain || data.spot_price;
  }, [data]);

  // Recharts OI distribution dataset
  const strikesChartData = useMemo(() => {
    if (!data || !data.strikes) return [];
    
    // Select closest 10 strikes around ATM
    let closestIndex = data.strikes.findIndex(s => s.strike_price >= (data.spot_price || data.max_pain));
    if (closestIndex === -1) closestIndex = Math.floor(data.strikes.length / 2);
    
    const sliceStart = Math.max(0, closestIndex - 5);
    const sliceEnd = Math.min(data.strikes.length, closestIndex + 6);
    
    return data.strikes.slice(sliceStart, sliceEnd).map(s => ({
      strike: s.strike_price.toString(),
      'Call OI': s.call.oi,
      'Put OI': s.put.oi,
      'Call Premium (L)': Math.round(s.call.premium / 100000),
      'Put Premium (L)': Math.round(s.put.premium / 100000),
      'Call GEX (Cr)': Math.round(s.call.gex / 10000000),
      'Put GEX (Cr)': Math.round(s.put.gex / 10000000)
    }));
  }, [data]);

  const chartTitleRange = useMemo(() => {
    if (!chartData || !chartData.candles || chartData.candles.length === 0) {
      return '';
    }
    const candles = chartData.candles;
    const firstCandle = candles[0];
    const lastCandle = candles[candles.length - 1];
    
    let firstTime = firstCandle.time;
    let lastTime = lastCandle.time;
    
    // Convert to Date objects
    let firstDate: Date;
    let lastDate: Date;
    
    if (typeof firstTime === 'number') {
      firstDate = new Date(firstTime * 1000);
    } else {
      firstDate = new Date(firstTime);
    }
    
    if (typeof lastTime === 'number') {
      lastDate = new Date(lastTime * 1000);
    } else {
      lastDate = new Date(lastTime);
    }
    
    const diffTime = Math.abs(lastDate.getTime() - firstDate.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (chartTimeframe === '5m' || chartTimeframe === '15m') {
      return `${diffDays} Days`;
    }
    
    if (diffDays >= 360) {
      const yrs = Math.round(diffDays / 365);
      return `${yrs} Year${yrs > 1 ? 's' : ''}`;
    } else if (diffDays >= 30) {
      const mos = Math.round(diffDays / 30);
      return `${mos} Month${mos > 1 ? 's' : ''}`;
    } else {
      return `${diffDays} Day${diffDays > 1 ? 's' : ''}`;
    }
  }, [chartData, chartTimeframe]);

  const getChartTitle = () => {
    const rangeStr = chartTitleRange ? ` (${chartTitleRange})` : '';
    switch (chartTimeframe) {
      case '5m': return `5 Minute Chart${rangeStr}`;
      case '15m': return `15 Minute Chart${rangeStr}`;
      case '30m': return `30 Minute Chart${rangeStr}`;
      case '1d': return `Daily Chart${rangeStr}`;
      default: return `Stock Chart${rangeStr}`;
    }
  };



  // Render Skeletons
  const renderSkeletons = () => (
    <div className="space-y-6 animate-pulse">
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
            <div className="h-3 w-16 bg-slate-800 rounded"></div>
            <div className="h-8 w-24 bg-slate-800 rounded"></div>
          </div>
        ))}
      </div>
      <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl space-y-4">
        <div className="h-4 w-48 bg-slate-800 rounded"></div>
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-8 bg-slate-800 rounded"></div>
          ))}
        </div>
      </div>
    </div>
  );

  if (loading && !data && !isNonFno) {
    return (
      <div className="space-y-6">
        {!isWidget && (
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-white font-display">Option Flow Terminal</h2>
              <p className="text-sm text-slate-500 font-medium font-mono">Connecting to broker option chain...</p>
            </div>
          </div>
        )}
        {renderSkeletons()}
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        {!isWidget && (
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-white font-display">Option Flow Terminal</h2>
              <p className="text-sm text-slate-500 font-medium">Error loading data</p>
            </div>
            <div className="flex items-center gap-3">
              <GlobalSymbolSearch />
            </div>
          </div>
        )}
        <ErrorCard message={error || ''} onRetry={handleRetry} title="Option Flow Analytics Error" />
      </div>
    );
  }

  const isDataEmpty = !data || !data.strikes || data.strikes.length === 0;

  if (isDataEmpty && !loading && !isNonFno) {
    let emptyTitle = "No Option Chain Data Available";
    let emptyMessage = (
      <>
        The Upstox API returned no option chain strikes for <span className="text-white font-bold">{selectedSymbol}</span>.
      </>
    );

    if (!selectedExpiry && expiries.length === 0) {
      emptyTitle = "No Expiry Found";
      emptyMessage = <>No active expiry available for <span className="text-white font-bold">{selectedSymbol}</span>.</>;
    } else if (data?.status === 'error') {
      emptyTitle = "API Error";
      emptyMessage = <>Failed to retrieve option chain from Upstox API for <span className="text-white font-bold">{selectedSymbol}</span>.</>;
    } else if (data?.strikes?.length === 0) {
      emptyTitle = "Empty Data";
      emptyMessage = <>No strikes returned by exchange for <span className="text-white font-bold">{selectedSymbol}</span> at expiry {selectedExpiry}.</>;
    }

    return (
      <div className="space-y-6">
        {!isWidget && (
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-white font-display">Option Flow Terminal</h2>
              <p className="text-sm text-slate-500 font-medium">No Option Chain Data</p>
            </div>
            <div className="flex items-center gap-3">
              <GlobalSymbolSearch />
            </div>
          </div>
        )}
        <div className="flex flex-col items-center justify-center p-8 min-h-[300px] rounded-2xl border border-amber-500/20 bg-slate-900/60 dark:bg-slate-950/40 backdrop-blur-md text-slate-100 shadow-2xl">
          <div className="w-12 h-12 rounded-full bg-amber-950/30 border border-amber-500/30 flex items-center justify-center mb-4 text-amber-400">
            <Layers size={24} />
          </div>
          <h3 className="font-display font-bold text-base text-slate-200 mb-2">
            {emptyTitle}
          </h3>
          <p className="text-xs text-slate-400 max-w-md text-center mb-2 font-medium leading-relaxed font-sans">
            {emptyMessage}
          </p>
          <button
            onClick={handleRetry}
            className="flex items-center gap-2 px-5 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 active:bg-emerald-700 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all cursor-pointer border-0"
          >
            Retry Request
          </button>
        </div>
      </div>
    );
  }

  // Formatting helper
  const formatPremium = (val: number | null | undefined) => {
    if (val === null || val === undefined || isNaN(val)) {
      return '₹0.00';
    }
    if (Math.abs(val) >= 10000000) {
      return `₹${(val / 10000000).toFixed(2)} Cr`;
    }
    if (Math.abs(val) >= 100000) {
      return `₹${(val / 100000).toFixed(2)} L`;
    }
    return `₹${val.toLocaleString('en-IN')}`;
  };

  const isStaleData = data ? (dataSource === 'stale_cache' || dataSource === 'cache') : false;

  // F&O analytics helper variables with safe fallbacks
  const pcr = data?.pcr_oi ?? 0;
  const sentiment = data?.sentiment ?? 'Neutral';
  const sentimentScore = data?.sentiment_score ?? 50;
  const totalVolume = data?.total_call_volume ?? 0;

  // Extract latest candle to calculate fallback price and changes
  const latestCandle = chartData?.candles?.[chartData.candles.length - 1];
  const spotPrice = data?.spot_price ?? latestCandle?.close ?? 0;
  const spotChange = data?.spot_change_pct ?? (latestCandle && chartData?.candles && chartData.candles.length > 1 ? ((latestCandle.close - chartData.candles[0].close) / chartData.candles[0].close) * 100 : 0);
  
  let signal = 'NO TRADE';
  let bias = 'Neutral';
  let confidence = 'Medium';
  let signalReason = 'No signals generated currently.';
  
  if (data?.trade_signals) {
    signal = data.trade_signals.signal || 'NO TRADE';
    bias = data.trade_signals.directional_bias || 'Neutral';
    confidence = data.trade_signals.confidence || 'Medium';
    signalReason = data.trade_signals.reason?.[0] || 'No signals generated currently.';
  } else if (latestCandle) {
    const ema20 = latestCandle.ema_20;
    const ema50 = latestCandle.ema_50;
    if (ema20 && ema50) {
      if (ema20 > ema50) {
        signal = 'TECHNICAL BUY';
        bias = 'Bullish';
        confidence = 'Medium';
        signalReason = 'EMA 20 is above EMA 50 indicating upward trend.';
      } else {
        signal = 'TECHNICAL SELL';
        bias = 'Bearish';
        confidence = 'Medium';
        signalReason = 'EMA 20 is below EMA 50 indicating downward trend.';
      }
    }
  }

  const isDev = (typeof process !== 'undefined' && process.env && process.env.NODE_ENV === 'development') || 
                (typeof window !== 'undefined' && window.location && window.location.hostname === 'localhost');

  return (
    <div className="p-6 lg:p-8 max-w-[1600px] mx-auto space-y-6 text-slate-100 font-sans selection:bg-emerald-500/30">
      {/* Diagnostic Panel */}
      {isDev && (
        <div className="flex flex-wrap items-center gap-4 px-4 py-3 bg-indigo-950/30 border border-indigo-500/30 rounded-xl text-[11px] font-mono text-slate-300 backdrop-blur-md">
          <div className="flex items-center gap-2 border-r border-slate-700/50 pr-4">
            <span className="text-indigo-400 font-bold">DIAGNOSTIC</span>
          </div>
          <div className="flex items-center gap-1.5 border-r border-slate-700/50 pr-4">
            <span className="text-slate-500">Symbol:</span>
            <span className="text-white font-bold">{selectedSymbol}</span>
          </div>
          <div className="flex items-center gap-1.5 border-r border-slate-700/50 pr-4">
            <span className="text-slate-500">Expiry:</span>
            <span className="text-white font-bold">{selectedExpiry}</span>
          </div>
          <div className="flex items-center gap-1.5 border-r border-slate-700/50 pr-4">
            <span className="text-slate-500">Instrument Key:</span>
            <span className="text-white font-bold">{data?._diagnostics?.instrument_key || 'N/A'}</span>
          </div>
          <div className="flex items-center gap-1.5 border-r border-slate-700/50 pr-4">
            <span className="text-slate-500">API Status:</span>
            <span className="text-emerald-400 font-bold">{data?._diagnostics?.api_status || data?.status || 'N/A'}</span>
          </div>
          <div className="flex items-center gap-1.5 border-r border-slate-700/50 pr-4">
            <span className="text-slate-500">Cache Status:</span>
            <span className="text-white font-bold">{data?._diagnostics?.cache_status || dataSource || 'N/A'}</span>
          </div>
          <div className="flex items-center gap-1.5 border-r border-slate-700/50 pr-4">
            <span className="text-slate-500">Strike Count:</span>
            <span className="text-white font-bold">{data?.strikes?.length || 0}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">Last Refresh:</span>
            <span className="text-white font-bold">{data?._diagnostics?.last_refresh || lastUpdated || 'N/A'}</span>
          </div>
        </div>
      )}

      {/* Stale Cache Banner */}
      {isStaleData && (
        <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl border border-amber-500/30 bg-amber-950/20 text-amber-300 backdrop-blur-md">
          <AlertTriangle size={16} className="shrink-0 animate-pulse" />
          <span className="text-xs font-semibold">
            Showing cached data from a previous session. Live data from Upstox is temporarily offline outside market hours.
          </span>
        </div>
      )}

      {/* Institutional Metrics summary bar */}
      <div className="flex flex-wrap items-center gap-6 px-4 py-3 bg-slate-900/40 border border-slate-800/80 rounded-xl text-[11px] font-mono font-bold text-slate-400 backdrop-blur-md">
        <div className="flex items-center gap-1.5 border-r border-slate-800/80 pr-4">
          <span className="text-slate-500">Call Turnover</span>
          <span className="text-slate-100 font-extrabold">{formatPremium(data?.total_call_premium)}</span>
        </div>
        <div className="flex items-center gap-1.5 border-r border-slate-800/80 pr-4">
          <span className="text-slate-500">Put Turnover</span>
          <span className="text-slate-100 font-extrabold">{formatPremium(data?.total_put_premium)}</span>
        </div>
        <div className="flex items-center gap-1.5 border-r border-slate-800/80 pr-4">
          <span className="text-slate-500">Net Premium Flow</span>
          <span className={`font-extrabold ${(data?.net_flow ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {(data?.net_flow ?? 0) >= 0 ? "+" : ""}{formatPremium(data?.net_flow ?? 0)}
          </span>
        </div>
        <div className="flex items-center gap-1.5 border-r border-slate-800/80 pr-4">
          <span className="text-slate-500">Put-Call Ratio (PCR)</span>
          <span className="text-slate-100 font-extrabold">{pcr.toFixed(2)}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500">Institutional Bias</span>
          <span className={`font-extrabold ${sentiment.includes('Bullish') ? "text-emerald-400" : sentiment.includes('Bearish') ? "text-red-400" : "text-slate-400"}`}>
            {sentiment}
          </span>
        </div>
      </div>

      {/* =========================================================================
          TOP INSTITUTIONAL HUD ROW
         ========================================================================= */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Quote Panel */}
        <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md flex flex-col justify-between hover:border-slate-700/60 transition-all">
          <div className="flex justify-between items-center">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Asset Quote</span>
            <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded ${spotChange >= 0 ? 'bg-emerald-950/40 text-emerald-400' : 'bg-red-950/40 text-red-400'}`}>
              {spotChange >= 0 ? '+' : ''}{spotChange.toFixed(2)}%
            </span>
          </div>
          <div className="my-3">
            <div className="text-xs text-slate-400 font-semibold">{data?.symbol || selectedSymbol}</div>
            <div className="text-2xl font-bold font-mono mt-1 text-slate-100">
              ₹{spotPrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
          </div>
          <div className="flex justify-between items-center text-[10px] text-slate-500 font-semibold">
            <span>Vol: {totalVolume.toLocaleString()} contracts</span>
            <span className="flex items-center gap-1">
              <Clock size={10} /> Auto-Refreshed
            </span>
          </div>
        </div>

        {/* Sentiment Meter Panel */}
        <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md flex flex-col justify-between hover:border-slate-700/60 transition-all">
          <div className="flex justify-between items-center">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Option Sentiment</span>
            <Activity size={12} className="text-purple-400 animate-pulse" />
          </div>
          <div className="my-3 text-center">
            <div className={`text-xl font-bold uppercase ${sentiment.includes('Bullish') ? 'text-emerald-400' : sentiment.includes('Bearish') ? 'text-red-400' : 'text-slate-400'}`}>
              {sentiment}
            </div>
            {/* Slider track visualization */}
            <div className="w-full bg-slate-800/80 h-1.5 rounded-full mt-3 overflow-hidden relative border border-slate-700/40">
              <div 
                className={`h-full rounded-full transition-all duration-500 ${sentimentScore >= 60 ? 'bg-emerald-500' : sentimentScore <= 40 ? 'bg-red-500' : 'bg-slate-500'}`}
                style={{ width: `${sentimentScore}%` }}
              ></div>
            </div>
          </div>
          <div className="flex justify-between text-[10px] text-slate-500 font-semibold font-mono">
            <span>PCR: {pcr.toFixed(2)}</span>
            <span>Index: {sentimentScore}/100</span>
          </div>
        </div>

        {/* Signal Panel */}
        <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md flex flex-col justify-between hover:border-slate-700/60 transition-all">
          <div className="flex justify-between items-center">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Signal Engine</span>
            <Zap size={12} className="text-yellow-400" />
          </div>
          <div className="my-2 flex items-center justify-between">
            <div>
              <span className={`text-2xl font-bold px-3 py-0.5 rounded font-display ${
                signal.includes('BUY') || signal.includes('BREAKOUT') || signal.includes('BULLISH') ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-500/20' :
                signal.includes('SELL') || signal.includes('BREAKDOWN') || signal.includes('BEARISH') ? 'bg-red-950/40 text-red-400 border border-red-500/20' : 'bg-slate-800 text-slate-400'
              }`}>
                {signal}
              </span>
            </div>
            <div className="text-right">
              <div className="text-[9px] text-slate-500 font-bold">CONFIDENCE</div>
              <div className="text-xs font-semibold text-slate-200">{confidence} ({data?.trade_signals?.confidence_score ?? 50}%)</div>
            </div>
          </div>
          <div className="text-[9px] text-slate-400 font-semibold truncate">
            {signalReason}
          </div>
          {data?.trade_signals?.equity_contribution !== undefined && data?.trade_signals?.options_contribution !== undefined && (
            <div className="mt-2.5 pt-2 border-t border-slate-800/40">
              <div className="flex justify-between text-[8px] font-mono font-bold text-slate-500 mb-1">
                <span>EQUITY: {data.trade_signals.equity_contribution}%</span>
                <span>OPTIONS: {data.trade_signals.options_contribution}%</span>
              </div>
              <div className="w-full bg-slate-850 h-1.5 rounded-full overflow-hidden flex border border-slate-800/60">
                <div className="bg-blue-500 h-full transition-all duration-500" style={{ width: `${data.trade_signals.equity_contribution}%` }}></div>
                <div className="bg-purple-500 h-full transition-all duration-500" style={{ width: `${data.trade_signals.options_contribution}%` }}></div>
              </div>
            </div>
          )}
        </div>

        {/* Market Relative Strength HUD */}
        {(() => {
          const stockChange = data?.market_correlation?.stock_change_pct;
          const sectorChange = data?.market_correlation?.sector_change_pct;
          const niftyChange = data?.market_correlation?.nifty_change_pct;
          
          const isAvailable = stockChange !== null && stockChange !== undefined;
          
          const stockChangeStr = isAvailable ? `${stockChange!.toFixed(1)}%` : 'N/A';
          const sectorChangeStr = sectorChange !== null && sectorChange !== undefined ? `${sectorChange!.toFixed(1)}%` : 'N/A';
          const niftyChangeStr = niftyChange !== null && niftyChange !== undefined ? `${niftyChange!.toFixed(1)}%` : 'N/A';
          
          const stockColor = isAvailable ? (stockChange! >= 0 ? 'text-emerald-400' : 'text-red-400') : 'text-slate-500';
          const sectorColor = sectorChange !== null && sectorChange !== undefined ? (sectorChange! >= 0 ? 'text-emerald-400' : 'text-red-400') : 'text-slate-500';
          const niftyColor = niftyChange !== null && niftyChange !== undefined ? (niftyChange! >= 0 ? 'text-emerald-400' : 'text-red-400') : 'text-slate-500';
          
          const betaVal = data?.market_correlation?.beta;
          const corrVal = data?.market_correlation?.correlation_score;
          
          const betaStr = betaVal !== null && betaVal !== undefined ? betaVal.toFixed(2) : 'N/A';
          const corrStr = corrVal !== null && corrVal !== undefined ? corrVal.toFixed(2) : 'N/A';
          
          return (
            <div 
              className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md flex flex-col justify-between hover:border-slate-700/60 transition-all"
              title={isAvailable ? undefined : "Relative strength data unavailable"}
            >
              <div className="flex justify-between items-center">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Relative Strength</span>
                <span className="text-[10px] font-mono font-bold text-slate-400">{data?.market_correlation?.sector_name ?? 'N/A'}</span>
              </div>
              <div className="my-2">
                <div className="text-[11px] font-bold text-purple-400 truncate">
                  {data?.market_correlation?.relative_strength ?? 'N/A'}
                </div>
                <div className="grid grid-cols-3 gap-2 mt-2.5 text-center text-[10px] font-mono font-bold">
                  <div className="bg-slate-950/60 p-1 rounded">
                    <div className="text-slate-500 scale-90">STOCK</div>
                    <div className={stockColor}>{stockChangeStr}</div>
                  </div>
                  <div className="bg-slate-950/60 p-1 rounded">
                    <div className="text-slate-500 scale-90">SECTOR</div>
                    <div className={sectorColor}>{sectorChangeStr}</div>
                  </div>
                  <div className="bg-slate-950/60 p-1 rounded">
                    <div className="text-slate-500 scale-90">NIFTY</div>
                    <div className={niftyColor}>{niftyChangeStr}</div>
                  </div>
                </div>
              </div>
              <div className="flex justify-between text-[10px] text-slate-500 font-semibold font-mono">
                <span>Beta: {betaStr}</span>
                <span>Corr: {corrStr}</span>
              </div>
            </div>
          );
        })()}
      </div>

      {/* =========================================================================
          MAIN WORKSPACE LAYOUT GRID
         ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-10 gap-6">
        
        {/* LEFT & CENTER COLUMN: Advanced Charting & Intraday PCR/Flow Trends - 70% */}
        <div className="lg:col-span-7 space-y-6">
          {/* Lightweight Chart Panel */}
          <div 
            ref={chartCardRef} 
            className={`p-6 border rounded-2xl backdrop-blur-md transition-all ${
              isFullscreen 
                ? 'w-full h-full flex flex-col justify-between bg-slate-950 border-0 rounded-none' 
                : 'bg-slate-900/60 border-slate-800/80'
            }`}
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
              <div>
                <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider flex items-center gap-1.5">
                  <BarChart2 size={14} className="text-purple-400" /> {getChartTitle()}
                  {chartData && (
                    <span className="group relative inline-block cursor-pointer ml-1.5 align-middle">
                      <Info size={12} className="text-slate-500 hover:text-slate-300" />
                      <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block bg-slate-950/95 border border-slate-800 text-slate-350 text-[10px] p-2.5 rounded-lg shadow-xl font-mono whitespace-nowrap z-50 pointer-events-none transition-all">
                        <span className="block text-purple-400 font-bold border-b border-slate-800/80 pb-1 mb-1">
                          History Loaded:
                        </span>
                        <span className="block text-slate-100 font-bold mb-2">
                          {chartData.available_history_days || 90} Days
                        </span>
                        <span className="block text-purple-400 font-bold border-b border-slate-800/80 pb-1 mb-1">
                          Candles:
                        </span>
                        <span className="block text-slate-100 font-bold">
                          {chartData.candle_count || 0}
                        </span>
                      </span>
                    </span>
                  )}
                </h3>
                <p className="text-[10px] text-slate-500 font-semibold mt-0.5">VWAP, EMA 20/50, Support/Resistance & Accumulation Zones</p>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1 bg-slate-950/40 p-1 rounded-lg border border-slate-800/80">
                  {(['5m', '15m', '30m', '1d'] as const).map((tf) => (
                    <button
                      key={tf}
                      onClick={() => setChartTimeframe(tf)}
                      className={`px-2.5 py-1 rounded-md text-[10px] font-bold transition-all cursor-pointer border-0 ${
                        chartTimeframe === tf
                          ? 'bg-purple-600 text-white shadow-md shadow-purple-500/20'
                          : 'bg-transparent text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {tf === '1d' ? '1D' : tf}
                    </button>
                  ))}
                </div>
                <button
                  onClick={toggleFullscreen}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-bold bg-slate-950/40 border border-slate-800/80 hover:bg-slate-850 hover:border-slate-700 text-slate-300 hover:text-slate-100 transition-all cursor-pointer"
                  title={isFullscreen ? "Exit Full Screen" : "Enter Full Screen"}
                >
                  {isFullscreen ? (
                    <>
                      <Minimize2 size={12} className="text-purple-400" />
                      <span>Exit Full Screen</span>
                    </>
                  ) : (
                    <>
                      <Maximize2 size={12} className="text-purple-400" />
                      <span>Full Screen</span>
                    </>
                  )}
                </button>
              </div>
            </div>
            
            <div className={`relative ${isFullscreen ? 'flex-grow h-[calc(100vh-140px)]' : 'h-[700px] min-h-[700px]'} bg-slate-950/40 rounded-xl overflow-hidden border border-slate-850`}>
              {/* Dynamic Interactive Tooltip Overlay */}
              <div 
                id="chart-tooltip" 
                className="absolute top-2.5 left-2.5 z-10 p-2.5 bg-slate-950/90 border border-slate-850 rounded-lg text-[10px] font-mono text-slate-300 pointer-events-none select-none flex flex-wrap gap-x-3.5 gap-y-1 max-w-[95%] shadow-lg shadow-black/80"
              >
                <span id="chart-tooltip-time" className="text-purple-400 font-bold"></span>
                <span id="chart-tooltip-ohlc"></span>
                <span id="chart-tooltip-volume" className="text-teal-400"></span>
                <span id="chart-tooltip-indicators" className="text-yellow-400"></span>
              </div>

              {chartLoading && (
                <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center z-10 text-xs text-purple-400 font-bold gap-2">
                  <RefreshCw className="animate-spin" size={14} /> Loading Advanced Overlays...
                </div>
              )}
              {chartError && (
                <div className="absolute inset-0 bg-red-950/80 backdrop-blur-sm flex flex-col items-center justify-center z-20 p-6 text-center border border-red-500/50 rounded-xl">
                  <span className="text-red-400 font-bold mb-2">Chart Render Error</span>
                  <p className="text-xs text-red-200/80 whitespace-pre-wrap break-all">{chartError}</p>
                </div>
              )}
              <div ref={chartContainerRef} className={`w-full h-full ${isFullscreen ? '' : 'min-h-[700px]'}`}></div>
            </div>

            <div className="flex flex-wrap items-center gap-4 mt-3 text-[10px] font-semibold text-slate-500">
              <div className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-yellow-500"></span> EMA 20</div>
              <div className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-blue-500"></span> EMA 50</div>
              <div className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-purple-500"></span> VWAP</div>
              <div className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-emerald-500/30"></span> Support Zones</div>
              <div className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-red-500/30"></span> Resistance Zones</div>
            </div>
          </div>

          {/* Intraday PCR & Premium Accumulation Curves */}
          {!isNonFno && data && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* PCR Intraday Momentum */}
            <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-md">
              <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mb-4 flex items-center gap-1.5">
                <Activity size={14} className="text-purple-400" /> Intraday PCR Momentum
              </h3>
              <div className="h-[180px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.pcr_trend || []}>
                    <defs>
                      <linearGradient id="pcrGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#1e293b" vertical={false} />
                    <XAxis dataKey="time" stroke="#475569" fontSize={9} />
                    <YAxis stroke="#475569" fontSize={9} domain={['auto', 'auto']} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }} />
                    <Area type="monotone" dataKey="pcr" stroke="#8b5cf6" strokeWidth={2} fillOpacity={1} fill="url(#pcrGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Premium Accumulation Curve */}
            <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-md">
              <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mb-4 flex items-center gap-1.5">
                <TrendingUp size={14} className="text-emerald-400" /> Premium Accumulation Curve
              </h3>
              <div className="h-[180px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.premium_flow_history || []}>
                    <defs>
                      <linearGradient id="flowGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#1e293b" vertical={false} />
                    <XAxis dataKey="time" stroke="#475569" fontSize={9} />
                    <YAxis stroke="#475569" fontSize={9} tickFormatter={(val) => `${(val / 100000).toFixed(0)}L`} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }} />
                    <Area type="monotone" dataKey="net_premium" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#flowGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
          )}
        </div>

        {/* RIGHT COLUMN: Open Interest Profile & Smart Money Panel - 30% */}
        {isNonFno ? (
          <div className="lg:col-span-3 p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-md flex flex-col justify-center items-center text-center space-y-4">
            <ShieldAlert size={36} className="text-purple-400 mb-2" />
            <div>
              <h4 className="text-slate-200 font-bold font-display text-sm">Option Analytics Unavailable</h4>
              <p className="text-slate-400 font-semibold text-xs leading-relaxed max-w-xs mt-2">
                The stock <span className="text-white font-bold">{selectedSymbol}</span> does not trade in the F&O segment. Intraday PCR trend, option chains, and smart money blocks are only supported for F&O-active contracts.
              </p>
            </div>
            <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-850 w-full text-left font-mono text-[10px] text-slate-400 space-y-1.5 shadow-inner">
              <div className="text-slate-500 font-bold border-b border-slate-800 pb-1 mb-1">FEATURE CAPABILITIES DETECTED</div>
              <div>• Historical Price Chart: <span className="text-emerald-400 font-bold">✓ AVAILABLE</span></div>
              <div>• EMA 20/50 Indicators: <span className="text-emerald-400 font-bold">✓ AVAILABLE</span></div>
              <div>• VWAP Overlays: <span className="text-emerald-400 font-bold">✓ AVAILABLE</span></div>
              <div>• Volume & Buy/Sell Signals: <span className="text-emerald-400 font-bold">✓ AVAILABLE</span></div>
              <div>• Relative Strength (RS): <span className="text-emerald-400 font-bold">✓ AVAILABLE</span></div>
              <div>• Options Chain / PCR: <span className="text-red-400 font-bold">✗ UNAVAILABLE</span></div>
              <div>• Smart Money blocks: <span className="text-red-400 font-bold">✗ UNAVAILABLE</span></div>
            </div>
          </div>
        ) : (
          <div className="lg:col-span-3 space-y-6">
            {/* Open Interest Horizontal Histogram Profile */}
            <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-md">
              <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mb-4 flex items-center gap-1.5">
                <Layers size={14} className="text-purple-400" /> Open Interest Profile (ATM strikes)
              </h3>
              <div className="h-[250px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={strikesChartData || []} layout="vertical">
                    <CartesianGrid stroke="#1e293b" horizontal={false} />
                    <XAxis type="number" stroke="#475569" fontSize={9} />
                    <YAxis dataKey="strike" type="category" stroke="#475569" fontSize={9} width={45} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }} />
                    <Legend fontSize={9} />
                    <Bar dataKey="Call OI" fill="#10b981" radius={[0, 2, 2, 0]} />
                    <Bar dataKey="Put OI" fill="#ef4444" radius={[0, 2, 2, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-[10px] font-mono grid grid-cols-3 text-center">
                <div>
                  <div className="text-slate-500 scale-95 uppercase font-bold">Max Pain</div>
                  <div className="text-purple-400 font-bold text-xs mt-0.5">{data?.max_pain}</div>
                </div>
                <div className="border-x border-slate-800">
                  <div className="text-slate-500 scale-95 uppercase font-bold">S Support</div>
                  <div className="text-emerald-400 font-bold text-xs mt-0.5">{data?.support_strike}</div>
                </div>
                <div>
                  <div className="text-slate-500 scale-95 uppercase font-bold">R Resistance</div>
                  <div className="text-red-400 font-bold text-xs mt-0.5">{data?.resistance_strike}</div>
                </div>
              </div>
            </div>

            {/* Smart Money & Anomalies activity tracker */}
            <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-md">
              <h3 className="font-bold text-xs uppercase tracking-wider mb-4 flex items-center gap-1.5" style={{ color: '#FFFFFF' }}>
                <Award size={14} style={{ color: '#FFFFFF' }} /> SMART MONEY ACTIVITY
              </h3>
              <div className="space-y-3 max-h-[290px] overflow-y-auto pr-1">
                {data?.smart_money_activity && data.smart_money_activity.length > 0 ? (
                  data.smart_money_activity.map((act, idx) => (
                    <div 
                      key={idx} 
                      className={`p-3 rounded-xl border flex flex-col justify-between text-[11px] font-semibold transition-all hover:bg-slate-850/40 ${
                        act.severity === 'High' ? 'bg-red-950/15 border-red-500/20' :
                        act.severity === 'Medium' ? 'bg-amber-950/15 border-amber-500/20' :
                        'bg-slate-950/40 border-slate-800'
                      }`}
                    >
                      <div className="flex justify-between items-center border-b border-slate-800/60 pb-1.5 mb-1.5 font-bold uppercase tracking-wider text-[10px]" style={{ color: '#FFFFFF' }}>
                        <span className="flex items-center gap-1" style={{ color: '#FFFFFF' }}>
                          <Flame size={12} className={act.severity === 'High' ? 'animate-pulse' : ''} style={{ color: '#FFFFFF' }} />
                          {act.type}
                        </span>
                        <span style={{ color: '#FFFFFF' }}>Strike {act.strike_price}</span>
                      </div>
                      <p className="text-[10px] leading-relaxed font-mono" style={{ color: '#FFFFFF' }}>
                        {act.reason}
                      </p>
                    </div>
                  ))
                ) : (
                  <div style={{ padding: '3rem 0', textAlign: 'center' }}>
                    <p style={{ color: '#FFFFFF', fontSize: '14px', fontWeight: 'bold', margin: 0, opacity: 1 }} className="text-white">
                      No unusual smart money patterns detected currently.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* =========================================================================
          TABS AREA: OPTION CHAIN, HEATMAP, BLOCK TRADES, TRADE SUMMARY
         ========================================================================= */}
      {!isNonFno && data && (
        <div className="space-y-4">
        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-800/80 gap-2 overflow-x-auto">
          <button
            onClick={() => setActiveTab('chain')}
            className={`px-4 py-2 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all cursor-pointer border-t-0 border-x-0 ${
              activeTab === 'chain'
                ? 'border-emerald-500 text-emerald-400 bg-emerald-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <List size={14} /> Option Chain
          </button>
          <button
            onClick={() => setActiveTab('heatmap')}
            className={`px-4 py-2 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all cursor-pointer border-t-0 border-x-0 ${
              activeTab === 'heatmap'
                ? 'border-emerald-500 text-emerald-400 bg-emerald-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <BarChart2 size={14} /> Option Flow Heatmap
          </button>
          <button
            onClick={() => setActiveTab('blocks')}
            className={`px-4 py-2 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all cursor-pointer border-t-0 border-x-0 ${
              activeTab === 'blocks'
                ? 'border-emerald-500 text-emerald-400 bg-emerald-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Award size={14} /> Large Block Tape ({data.block_deals?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('summary')}
            className={`px-4 py-2 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all cursor-pointer border-t-0 border-x-0 ${
              activeTab === 'summary'
                ? 'border-emerald-500 text-emerald-400 bg-emerald-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck size={14} /> Institutional Trade Setup
          </button>
        </div>

        {/* Tab Contents */}
        <div className="min-h-[400px]">
          
          {/* TAB 1: OPTION CHAIN */}
          {activeTab === 'chain' && (
            <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-900/30 backdrop-blur-md">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/80 text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                    <th className="px-4 py-3 text-center border-r border-slate-800/60" colSpan={6}>Calls (CE)</th>
                    <th className="px-4 py-3 text-center border-r border-slate-800/60">Strike</th>
                    <th className="px-4 py-3 text-center" colSpan={6}>Puts (PE)</th>
                  </tr>
                  <tr className="border-b border-slate-800 text-[10px] text-slate-500 font-bold uppercase tracking-wider bg-slate-900/40">
                    <th className="px-4 py-2.5">Buildup</th>
                    <th className="px-4 py-2.5">OI</th>
                    <th className="px-4 py-2.5">OI Chg</th>
                    <th className="px-4 py-2.5">Vol</th>
                    <th className="px-4 py-2.5">IV</th>
                    <th className="px-4 py-2.5 border-r border-slate-800/60">LTP</th>
                    <th className="px-4 py-2.5 text-center border-r border-slate-800/60">Strike Price</th>
                    <th className="px-4 py-2.5">LTP</th>
                    <th className="px-4 py-2.5">IV</th>
                    <th className="px-4 py-2.5">Vol</th>
                    <th className="px-4 py-2.5">OI Chg</th>
                    <th className="px-4 py-2.5">OI</th>
                    <th className="px-4 py-2.5">Buildup</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-850/50 font-mono text-[14px]">
                  {(() => {
                    const maxCallOi = Math.max(...data.strikes.map(s => s.call?.oi ?? 0), 0);
                    const maxPutOi = Math.max(...data.strikes.map(s => s.put?.oi ?? 0), 0);
                    return data.strikes.map((s, idx) => {
                      const isAtm = s.strike_price === atmStrike;
                      const isHighestCallOi = (s.call?.oi ?? 0) === maxCallOi && maxCallOi > 0;
                      const isHighestPutOi = (s.put?.oi ?? 0) === maxPutOi && maxPutOi > 0;
                      
                      return (
                        <StrikeGridRow
                          key={s.strike_price}
                          strike={s}
                          idx={idx}
                          isAtm={isAtm}
                          isHighestCallOi={isHighestCallOi}
                          isHighestPutOi={isHighestPutOi}
                        />
                      );
                    });
                  })()}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB 2: OPTION FLOW HEATMAP */}
          {activeTab === 'heatmap' && (
            <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md">
              <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mb-4 flex items-center gap-1.5">
                <BarChart2 size={14} className="text-purple-400" /> Option Flow Heatmap (Buildup Concentration & Volume)
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {data.strikes.map((s) => {
                  const callIntensity = Math.min(100, Math.abs(s.call.buildup_intensity));
                  const putIntensity = Math.min(100, Math.abs(s.put.buildup_intensity));
                  
                  const isAtm = s.strike_price === atmStrike;

                  return (
                    <div 
                      key={s.strike_price} 
                      className={`p-4 rounded-xl border flex flex-col justify-between font-semibold font-mono text-[11px] ${
                        isAtm ? 'border-purple-500/40 bg-purple-950/15' : 'border-slate-800 bg-slate-950/40'
                      }`}
                    >
                      <div className="flex justify-between items-center border-b border-slate-800/80 pb-2 mb-2">
                        <span className="text-slate-400 uppercase text-[10px] font-bold">Strike Price</span>
                        <span className={`font-bold text-xs ${isAtm ? 'text-purple-400' : 'text-slate-100'}`}>
                          {s.strike_price} {isAtm && '(ATM)'}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        {/* Calls Column */}
                        <div className="space-y-1">
                          <div className="text-[9px] text-slate-500 font-bold uppercase">Calls (CE)</div>
                          <div className={`px-2 py-0.5 rounded text-[10px] font-bold text-center inline-block ${
                            s.call.sentiment === 'Strong Bullish' ? 'bg-emerald-950/70 text-emerald-400 border border-emerald-500/40' :
                            s.call.sentiment === 'Bullish' ? 'bg-emerald-900/30 text-emerald-500/90 border border-emerald-500/10' :
                            s.call.sentiment === 'Bearish' ? 'bg-orange-950/40 text-orange-400 border border-orange-500/20' :
                            s.call.sentiment === 'Strong Bearish' ? 'bg-red-950/70 text-red-400 border border-red-500/40' :
                            'bg-slate-800 text-slate-400 border border-slate-700/30'
                          }`}>
                            {s.call.sentiment ?? 'Neutral'}
                          </div>
                          <div className="text-[9px] text-slate-500 font-semibold mt-0.5">
                            Conf: {s.call.confidence_score ?? 50}%
                          </div>
                          <div className="text-[10px] text-slate-400 mt-1">OI: {s.call?.oi?.toLocaleString() ?? '0'}</div>
                          <div className="text-[10px] text-slate-400">GEX: ₹{((s.call?.gex ?? 0) / 10000000).toFixed(1)} Cr</div>
                        </div>

                        {/* Puts Column */}
                        <div className="space-y-1 text-right">
                          <div className="text-[9px] text-slate-500 font-bold uppercase">Puts (PE)</div>
                          <div className={`px-2 py-0.5 rounded text-[10px] font-bold text-center inline-block ${
                            s.put.sentiment === 'Strong Bullish' ? 'bg-emerald-950/70 text-emerald-400 border border-emerald-500/40' :
                            s.put.sentiment === 'Bullish' ? 'bg-emerald-900/30 text-emerald-500/90 border border-emerald-500/10' :
                            s.put.sentiment === 'Bearish' ? 'bg-orange-950/40 text-orange-400 border border-orange-500/20' :
                            s.put.sentiment === 'Strong Bearish' ? 'bg-red-950/70 text-red-400 border border-red-500/40' :
                            'bg-slate-800 text-slate-400 border border-slate-700/30'
                          }`}>
                            {s.put.sentiment ?? 'Neutral'}
                          </div>
                          <div className="text-[9px] text-slate-500 font-semibold mt-0.5">
                            Conf: {s.put.confidence_score ?? 50}%
                          </div>
                          <div className="text-[10px] text-slate-400 mt-1">OI: {s.put?.oi?.toLocaleString() ?? '0'}</div>
                          <div className="text-[10px] text-slate-400">GEX: ₹{((s.put?.gex ?? 0) / 10000000).toFixed(1)} Cr</div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 3: LARGE BLOCK TAPE */}
          {activeTab === 'blocks' && (
            <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md">
              <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
                <div>
                  <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider flex items-center gap-1.5">
                    <Award size={14} className="text-emerald-400 animate-pulse" /> Large Block Deals Tape
                  </h3>
                  <p className="text-[10px] text-slate-500 font-semibold mt-0.5">Real-time options trades exceeding ₹10 Lakhs in premium value.</p>
                </div>
                <span className="text-[10px] text-slate-500 uppercase font-mono font-bold">
                  Threshold: &gt; ₹10L Premium
                </span>
              </div>

              {(data.block_deals?.length || 0) > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-[11px] border-collapse font-mono">
                    <thead>
                      <tr className="border-b border-slate-800 text-[10px] text-slate-500 font-bold uppercase">
                        <th className="py-2.5">Strike</th>
                        <th className="py-2.5">Option Type</th>
                        <th className="py-2.5 text-right">LTP</th>
                        <th className="py-2.5 text-right">Volume</th>
                        <th className="py-2.5 text-right">Premium Value</th>
                        <th className="py-2.5 text-right">Open Interest</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/40">
                      {(data.block_deals || []).map((block, idx) => {
                        const isCe = block.type === 'CE';
                        return (
                          <tr key={idx} className="hover:bg-slate-800/20">
                            <td className="py-2.5 text-slate-100 font-bold">{block.strike_price.toFixed(1)}</td>
                            <td className="py-2.5">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                isCe ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'
                              }`}>
                                {block.type}
                              </span>
                            </td>
                            <td className="py-2.5 text-right text-slate-200">₹{block.ltp.toFixed(2)}</td>
                            <td className="py-2.5 text-right text-slate-400">{block.volume?.toLocaleString() ?? '0'}</td>
                            <td className="py-2.5 text-right text-emerald-400 font-bold">{formatPremium(block.premium)}</td>
                            <td className="py-2.5 text-right text-slate-300">{block.oi?.toLocaleString() ?? '0'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-12 text-center text-slate-500 font-medium">
                  No large block deals detected for this contract expiry.
                </div>
              )}
            </div>
          )}

          {/* TAB 4: INSTITUTIONAL TRADE SETUP SUMMARY */}
          {activeTab === 'summary' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Trade parameters setup */}
              <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md lg:col-span-1">
                <h4 className="text-slate-200 font-bold text-xs uppercase tracking-wider mb-4 flex items-center gap-1.5 border-b border-slate-800 pb-3">
                  <Target size={14} className="text-emerald-400" /> Optimal Execution Parameters
                </h4>
                
                <div className="space-y-4">
                  <div className="flex justify-between items-center py-2 border-b border-slate-800/60 text-[11px] font-semibold">
                    <span className="text-slate-500">Directional Bias</span>
                    <span className={`font-bold px-2 py-0.5 rounded uppercase ${
                      bias === 'Bullish' ? 'bg-emerald-950/40 text-emerald-400' :
                      bias === 'Bearish' ? 'bg-red-950/40 text-red-400' : 'bg-slate-800 text-slate-400'
                    }`}>
                      {bias}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-slate-800/60 text-[11px] font-semibold">
                    <span className="text-slate-500">Suggested Entry Zone</span>
                    <span className="font-mono font-bold text-slate-200">{data.trade_signals?.entry_zone}</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-slate-800/60 text-[11px] font-semibold">
                    <span className="text-slate-500">Stop Loss / Invalidation</span>
                    <span className="font-mono font-bold text-red-400">₹{data.trade_signals?.stop_loss}</span>
                  </div>
                  <div className="flex justify-between items-start py-2 border-b border-slate-800/60 text-[11px] font-semibold">
                    <span className="text-slate-500 mt-0.5">Target Levels (T1/T2)</span>
                    <div className="flex flex-col text-right font-mono font-bold text-emerald-400 gap-1">
                      {data.trade_signals?.target_levels && data.trade_signals.target_levels.length > 0 ? (
                        data.trade_signals.target_levels.map((t, idx) => (
                          <span key={idx}>T{idx+1}: ₹{t}</span>
                        ))
                      ) : (
                        <span>N/A</span>
                      )}
                    </div>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-slate-800/60 text-[11px] font-semibold">
                    <span className="text-slate-500">Confidence Score</span>
                    <span className="text-purple-400 font-bold">{confidence} ({data.trade_signals?.confidence_score}%)</span>
                  </div>
                  {data.trade_signals?.equity_contribution !== undefined && (
                    <div className="flex justify-between items-center py-2 border-b border-slate-800/60 text-[11px] font-semibold">
                      <span className="text-slate-500">Equity Contribution</span>
                      <span className="text-blue-400 font-bold">{data.trade_signals.equity_contribution}%</span>
                    </div>
                  )}
                  {data.trade_signals?.options_contribution !== undefined && (
                    <div className="flex justify-between items-center py-1 text-[11px] font-semibold">
                      <span className="text-slate-500">Options Contribution</span>
                      <span className="text-purple-400 font-bold">{data.trade_signals.options_contribution}%</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Dynamic Option Commentary & Analysis */}
              <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md lg:col-span-2 space-y-6">
                <h4 className="text-slate-200 font-bold text-xs uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-800 pb-3">
                  <Activity size={14} className="text-purple-400" /> Options Positioning & Market Structure Commentary
                </h4>
                
                <div className="space-y-4 text-xs font-medium text-slate-300 leading-relaxed font-sans">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <h5 className="text-[10px] text-slate-500 uppercase font-bold mb-1">Market Structure</h5>
                      <p>
                        The current sentiment score is <span className="text-slate-100 font-bold">{data.sentiment_score}/100</span> (classified as <span className="text-slate-100 font-bold">{data.sentiment}</span>). 
                        The derivative pricing suggests {bias === 'Bullish' ? 'bullish continuation as option writers are actively backing lower strikes.' : bias === 'Bearish' ? 'directional weakness under intense short build-ups.' : 'a range-bound consolidated consolidation cycle.'}
                      </p>
                    </div>
                    
                    <div>
                      <h5 className="text-[10px] text-slate-500 uppercase font-bold mb-1">Options Positioning</h5>
                      <p>
                        Open Interest profile shows a dominant Call concentration at <span className="text-slate-100 font-bold">{data.resistance_strike}</span> (representing a strong ceiling wall) and Put support floor at <span className="text-slate-100 font-bold">{data.support_strike}</span>. 
                        Max Pain is currently set at <span className="text-slate-100 font-bold">{data.max_pain}</span>. Options pain points indicate that option sellers are incentivized to target this zone on expiry day.
                      </p>
                    </div>
                  </div>

                  {/* Bullish vs Bearish Evidence Columns */}
                  <div className="border-t border-slate-800/80 pt-4">
                    <h5 className="text-[10px] text-slate-500 uppercase font-bold mb-2">Confluence Evidence Breakdown</h5>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Bullish List */}
                      <div className="p-3 bg-emerald-950/10 border border-emerald-950/40 rounded-xl space-y-1.5">
                        <div className="text-[9px] text-emerald-400 font-bold uppercase tracking-wider flex items-center gap-1 mb-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Bullish Support Evidence
                        </div>
                        {data.trade_signals?.bullish_evidence && data.trade_signals.bullish_evidence.length > 0 ? (
                          <ul className="space-y-1 pl-1 text-[10px] text-slate-350 list-none">
                            {data.trade_signals.bullish_evidence.map((item, idx) => (
                              <li key={idx} className="flex items-start gap-1">
                                <span className="text-emerald-400">✓</span> <span>{item}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <div className="text-[10px] text-slate-500 italic">No significant bullish indicators detected.</div>
                        )}
                      </div>

                      {/* Bearish List */}
                      <div className="p-3 bg-red-950/10 border border-red-950/40 rounded-xl space-y-1.5">
                        <div className="text-[9px] text-red-400 font-bold uppercase tracking-wider flex items-center gap-1 mb-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-red-400"></span> Bearish Risk Evidence
                        </div>
                        {data.trade_signals?.bearish_evidence && data.trade_signals.bearish_evidence.length > 0 ? (
                          <ul className="space-y-1 pl-1 text-[10px] text-slate-350 list-none">
                            {data.trade_signals.bearish_evidence.map((item, idx) => (
                              <li key={idx} className="flex items-start gap-1">
                                <span className="text-red-400">✗</span> <span>{item}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <div className="text-[10px] text-slate-500 italic">No major bearish risks detected.</div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Key Indicators Confluence Table */}
                  {data.trade_signals?.key_indicators && (
                    <div className="border-t border-slate-800/80 pt-4">
                      <h5 className="text-[10px] text-slate-500 uppercase font-bold mb-2">Key Indicators Dashboard</h5>
                      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                        {Object.entries(data.trade_signals.key_indicators).map(([key, value]) => (
                          <div key={key} className="p-2 bg-slate-950/50 border border-slate-800/60 rounded-lg text-center">
                            <div className="text-[8px] text-slate-500 uppercase font-bold tracking-wider mb-0.5">
                              {key.replace(/_/g, ' ')}
                            </div>
                            <div className="text-[10px] font-bold text-slate-200 truncate">
                              {value}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                </div>
              </div>
            </div>
          )}

        </div>
      </div>
      )}

    </div>
  );
});

export default OptionFlow;
