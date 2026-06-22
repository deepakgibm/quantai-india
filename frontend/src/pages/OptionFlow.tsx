import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { 
  TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight, RefreshCw, 
  BarChart2, List, ShieldAlert, Award, Layers, AlertTriangle, 
  Gauge, Zap, Clock, Activity, Target, ShieldCheck, Flame, Info
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
  const lightweightChartRef = useRef<any>(null);
  const candlestickSeriesRef = useRef<any>(null);
  const ema20SeriesRef = useRef<any>(null);
  const ema50SeriesRef = useRef<any>(null);
  const vwapSeriesRef = useRef<any>(null);
  const chartMarkersRef = useRef<any[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const chartCacheRef = useRef<Record<string, AdvancedChartData>>({});
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
    
    const cacheKey = `${symbol}:${timeframe}:90`;
    if (chartCacheRef.current[cacheKey]) {
      setChartError(null);
      setChartData(chartCacheRef.current[cacheKey]);
      return;
    }
    
    setChartLoading(true);
    setChartError(null);
    try {
      const response = await api.getOptionFlowChart(clean, timeframe, 90);
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

  // Run on Symbol change
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
        return;
      }
      
      setIsNonFno(false);
      setLoading(true);
      
      await Promise.all([
        fetchExpiries(selectedSymbol),
        checkBrokerStatus()
      ]);
    };
    init();
  }, [selectedSymbol]);

  // Run on Expiry or Timeframe change
  useEffect(() => {
    const clean = selectedSymbol.toUpperCase().replace("NSE:", "").trim();
    if (!isFOSymbol(clean)) {
      setIsNonFno(true);
      setLoading(false);
      return;
    }

    if (selectedExpiry) {
      fetchOptionFlow(selectedSymbol, selectedExpiry);
      fetchChartData(selectedSymbol, chartTimeframe);
    }

    const fetchIncrementalChartData = async () => {
      if (!lightweightChartRef.current || !candlestickSeriesRef.current) return;
      try {
        const response = await api.getOptionFlowChart(clean, chartTimeframe, 2);
        const chartPayload = response?.data && response?.success ? response.data : response;

        if (chartPayload && chartPayload.candles && chartPayload.candles.length > 0) {
          // 1. Update Existing Candlestick Series Instantly
          chartPayload.candles.forEach((c: any) => {
            if (candlestickSeriesRef.current) {
              let t = c.time;
              if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
              else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
              
              candlestickSeriesRef.current.update({
                time: t as UTCTimestamp,
                open: c.open,
                high: c.high,
                low: c.low,
                close: c.close
              });
            }
            if (ema20SeriesRef.current && c.ema_20 !== undefined) {
              let t = c.time;
              if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
              else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
              ema20SeriesRef.current.update({ time: t as UTCTimestamp, value: c.ema_20 });
            }
            if (ema50SeriesRef.current && c.ema_50 !== undefined) {
              let t = c.time;
              if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
              else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
              ema50SeriesRef.current.update({ time: t as UTCTimestamp, value: c.ema_50 });
            }
            if (vwapSeriesRef.current && c.vwap !== undefined) {
              let t = c.time;
              if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
              else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
              vwapSeriesRef.current.update({ time: t as UTCTimestamp, value: c.vwap });
            }
          });

          // 2. Update Breakout Markers
          if (chartPayload.breakout_markers && chartPayload.breakout_markers.length > 0 && candlestickSeriesRef.current) {
            const existingMarkersMap = new Map(chartMarkersRef.current.map(m => [m.time, m]));
            chartPayload.breakout_markers.forEach((m: any) => {
              let t = m.time;
              if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
              else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
              existingMarkersMap.set(t, { ...m, time: t });
            });
            const mergedMarkers = Array.from(existingMarkersMap.values()).sort((a, b) => {
              const tA = typeof a.time === 'number' ? a.time : new Date(a.time).getTime();
              const tB = typeof b.time === 'number' ? b.time : new Date(b.time).getTime();
              return tA - tB;
            });
            candlestickSeriesRef.current.setMarkers(mergedMarkers);
            chartMarkersRef.current = mergedMarkers;
          }

          setChartData(prev => {
            if (!prev) return null;
            const existingCandlesMap = new Map((prev.candles || []).map(c => [c.time, c]));
            chartPayload.candles.forEach((c: any) => {
              let t = c.time;
              if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
              else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
              existingCandlesMap.set(t, { ...c, time: t });
            });
            const mergedCandles = Array.from(existingCandlesMap.values()).sort((a, b) => {
              const tA = typeof a.time === 'number' ? a.time : new Date(a.time).getTime();
              const tB = typeof b.time === 'number' ? b.time : new Date(b.time).getTime();
              return tA - tB;
            });
            return {
              ...prev,
              candle_count: mergedCandles.length,
              candles: mergedCandles
            };
          });
        }
      } catch (err) {
        console.warn('[OptionFlow] Failed to fetch incremental chart updates:', err);
      }
    };

    const interval = setInterval(() => {
      if (selectedExpiry && !isNonFno) {
        fetchOptionFlow(selectedSymbol, selectedExpiry, true);
        checkBrokerStatus();
        fetchIncrementalChartData();
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

  // =========================================================================
  // TradingView Lightweight Chart Setup & Lifecycle
  // =========================================================================
  
  // 1. Reset/Destroy Chart on Symbol or Timeframe change
  useEffect(() => {
    if (lightweightChartRef.current) {
      try {
        lightweightChartRef.current.remove();
      } catch (e) {
        console.warn('Error removing chart:', e);
      }
      lightweightChartRef.current = null;
      candlestickSeriesRef.current = null;
      ema20SeriesRef.current = null;
      ema50SeriesRef.current = null;
      vwapSeriesRef.current = null;
      chartMarkersRef.current = [];
    }
    setChartData(null);
    setChartError(null);
  }, [selectedSymbol, chartTimeframe]);

  // 2. Initialize and draw chart when chartData arrives
  useEffect(() => {
    if (!chartContainerRef.current || !chartData || !chartData.candles || chartData.candles.length === 0) {
      return;
    }

    // If chart already initialized, skip full recreation (incremental updates handle live data)
    if (lightweightChartRef.current) {
      return;
    }

    const container = chartContainerRef.current;
    console.log(`[Chart Init] Creating chart. Container clientWidth: ${container.clientWidth}, height: 320`);
    
    // Create Chart Instance
    try {
      const chart = createChart(container, {
      width: container.clientWidth || 800,
      height: 320,
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

    // Main Candlestick Series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });
    candlestickSeriesRef.current = candlestickSeries;

    // Populate candle data
    const candlesData = (chartData.candles || [])
      .filter((c: any) => c && c.time && c.open != null && c.high != null && c.low != null && c.close != null && !isNaN(c.close))
      .map((c: any) => {
        let t = c.time;
        // Strict timestamp conversion logic as requested
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
    
    console.log(`[Chart Init] Adding ${candlesData.length} candles to series. First candle:`, candlesData[0]);
    
    try {
      candlestickSeries.setData(candlesData);
      console.log('[Chart Init] Successfully set candlestick data');
    } catch (e) {
      console.error('[Chart Init] Error setting candlestick data:', e);
    }

    // Volume Series
    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: { type: 'volume' },
      priceScaleId: '',
      scaleMargins: { top: 0.8, bottom: 0 },
    });
    volumeSeries.setData((chartData.candles || [])
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
      }));

    // EMA 20 Overlays (Yellow)
    const ema20Series = chart.addLineSeries({
      color: '#F59E0B',
      lineWidth: 1,
      title: 'EMA 20'
    });
    ema20SeriesRef.current = ema20Series;
    ema20Series.setData((chartData.candles || [])
      .filter((c: any) => c && c.time && c.ema_20 != null && !isNaN(c.ema_20))
      .map((c: any) => {
        let t = c.time;
        if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
        else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
        return { time: t, value: Number(c.ema_20) };
      }));

    // EMA 50 Overlays (Blue)
    const ema50Series = chart.addLineSeries({
      color: '#3b82f6',
      lineWidth: 1,
      title: 'EMA 50'
    });
    ema50SeriesRef.current = ema50Series;
    ema50Series.setData((chartData.candles || [])
      .filter((c: any) => c && c.time && c.ema_50 != null && !isNaN(c.ema_50))
      .map((c: any) => {
        let t = c.time;
        if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
        else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
        return { time: t, value: Number(c.ema_50) };
      }));

    // VWAP Overlay (Purple)
    const vwapSeries = chart.addLineSeries({
      color: '#8B5CF6',
      lineWidth: 1,
      title: 'VWAP'
    });
    vwapSeriesRef.current = vwapSeries;
    vwapSeries.setData((chartData.candles || [])
      .filter((c: any) => c && c.time && c.vwap != null && !isNaN(c.vwap))
      .map((c: any) => {
        let t = c.time;
        if (typeof t === 'string' && t.includes('T')) t = Math.floor(new Date(t).getTime() / 1000);
        else if (typeof t === 'number' && t > 10000000000) t = Math.floor(t / 1000);
        return { time: t, value: Number(c.vwap) };
      }));

    // Support & Resistance Zones
    if (chartData.support_zones && chartData.support_zones.length > 0) {
      chartData.support_zones.forEach(price => {
        candlestickSeries.createPriceLine({
          price: price,
          color: '#10B981',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: 'Support',
        });
      });
    }

    if (chartData.resistance_zones && chartData.resistance_zones.length > 0) {
      chartData.resistance_zones.forEach(price => {
        candlestickSeries.createPriceLine({
          price: price,
          color: '#EF4444',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: 'Resistance',
        });
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
        
        console.log(`[Chart Init] Setting ${validMarkers.length} markers`);
        candlestickSeries.setMarkers(validMarkers);
        chartMarkersRef.current = validMarkers;
      } catch (e) {
        console.error('[Chart Init] Error setting markers:', e);
      }
    }

    // Auto-fit contents
    try {
      chart.timeScale().fitContent();
      console.log('[Chart Init] Successfully fitted content');
    } catch (e) {
      console.error('[Chart Init] Error fitting content:', e);
    }

    // Handle Resize
    const handleResize = () => {
      if (lightweightChartRef.current && container.clientWidth > 0) {
        lightweightChartRef.current.applyOptions({ width: container.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    // Store resize listener in ref so we can remove it on unmount
    (container as any)._resizeHandler = handleResize;

    } catch (e: any) {
      console.error('[Chart Init] Fatal error during chart creation:', e);
      setChartError(e.message || e.toString());
    }
  }, [chartData]); // Note: No cleanup function returned here to prevent destruction on data updates. Cleanup is in useEffect #1.

  // 3. Global cleanup on unmount
  useEffect(() => {
    return () => {
      if (chartContainerRef.current && (chartContainerRef.current as any)._resizeHandler) {
        window.removeEventListener('resize', (chartContainerRef.current as any)._resizeHandler);
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

  if (isNonFno) {
    if (isWidget) {
      return (
        <div className="flex flex-col items-center justify-center p-6 min-h-[200px] text-center">
          <div className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-2.5 text-slate-400">
            <ShieldAlert size={16} className="text-slate-400 dark:text-slate-500" />
          </div>
          <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">
            Options data unavailable for this stock.
          </p>
        </div>
      );
    }
    return (
      <div className="space-y-6">
        {!isWidget && (
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-white font-display">Option Flow Terminal</h2>
              <p className="text-sm text-slate-500 font-medium">Derivative turnover & institutional block tracker</p>
            </div>
            <div className="flex items-center gap-3">
              <GlobalSymbolSearch />
            </div>
          </div>
        )}

        <div className="flex flex-col items-center justify-center p-8 min-h-[250px] rounded-xl border border-purple-500/20 bg-slate-900/60 dark:bg-slate-950/40 backdrop-blur-md text-slate-100 shadow-xl">
          <div className="w-10 h-10 rounded-full bg-purple-950/30 border border-purple-500/30 flex items-center justify-center mb-3.5 text-purple-400">
            <ShieldAlert size={20} />
          </div>
          <h3 className="font-display font-semibold text-sm text-purple-400 mb-1.5">F&O Segment Required</h3>
          <p className="text-xs text-slate-400 max-w-md text-center mb-4 font-medium leading-relaxed">
            The symbol <span className="text-white font-bold">{selectedSymbol}</span> does not trade in the Futures & Options segment on the NSE. Option chain and flow metrics are only available for F&O-active stocks.
          </p>
          <div className="text-[10px] text-slate-500">
            Please search for an F&O stock (e.g., RELIANCE, NIFTY, TCS, SBIN).
          </div>
        </div>
      </div>
    );
  }

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

  if (loading && !data) {
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

  if (isDataEmpty && !loading) {
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

  const isStaleData = dataSource === 'stale_cache' || dataSource === 'cache';
  const signal = data.trade_signals?.signal || 'NO TRADE';
  const bias = data.trade_signals?.directional_bias || 'Neutral';
  const confidence = data.trade_signals?.confidence || 'Medium';

  const isDev = (typeof process !== 'undefined' && process.env && process.env.NODE_ENV === 'development') || 
                (typeof window !== 'undefined' && window.location && window.location.hostname === 'localhost');

  return (
    <div className="space-y-6 text-slate-100 font-sans selection:bg-emerald-500/30">
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
            <span className="text-white font-bold">{data.strikes?.length || 0}</span>
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
          <span className="text-slate-100 font-extrabold">{formatPremium(data.total_call_premium)}</span>
        </div>
        <div className="flex items-center gap-1.5 border-r border-slate-800/80 pr-4">
          <span className="text-slate-500">Put Turnover</span>
          <span className="text-slate-100 font-extrabold">{formatPremium(data.total_put_premium)}</span>
        </div>
        <div className="flex items-center gap-1.5 border-r border-slate-800/80 pr-4">
          <span className="text-slate-500">Net Premium Flow</span>
          <span className={`font-extrabold ${data.net_flow >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {data.net_flow >= 0 ? "+" : ""}{formatPremium(data.net_flow)}
          </span>
        </div>
        <div className="flex items-center gap-1.5 border-r border-slate-800/80 pr-4">
          <span className="text-slate-500">Put-Call Ratio (PCR)</span>
          <span className="text-slate-100 font-extrabold">{(data.pcr_oi ?? 0).toFixed(2)}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500">Institutional Bias</span>
          <span className={`font-extrabold ${(data.sentiment ?? 'Neutral').includes('Bullish') ? "text-emerald-400" : (data.sentiment ?? 'Neutral').includes('Bearish') ? "text-red-400" : "text-slate-400"}`}>
            {data.sentiment}
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
            <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded ${(data.spot_change_pct ?? 0) >= 0 ? 'bg-emerald-950/40 text-emerald-400' : 'bg-red-950/40 text-red-400'}`}>
              {(data.spot_change_pct ?? 0) >= 0 ? '+' : ''}{(data.spot_change_pct ?? 0).toFixed(2)}%
            </span>
          </div>
          <div className="my-3">
            <div className="text-xs text-slate-400 font-semibold">{data.symbol}</div>
            <div className="text-2xl font-bold font-mono mt-1 text-slate-100">
              ₹{(data.spot_price ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
          </div>
          <div className="flex justify-between items-center text-[10px] text-slate-500 font-semibold">
            <span>Vol: {(data.total_call_volume ?? 0).toLocaleString()} contracts</span>
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
            <div className={`text-xl font-bold uppercase ${(data.sentiment ?? 'Neutral').includes('Bullish') ? 'text-emerald-400' : (data.sentiment ?? 'Neutral').includes('Bearish') ? 'text-red-400' : 'text-slate-400'}`}>
              {data.sentiment ?? 'Neutral'}
            </div>
            {/* Slider track visualization */}
            <div className="w-full bg-slate-800/80 h-1.5 rounded-full mt-3 overflow-hidden relative border border-slate-700/40">
              <div 
                className={`h-full rounded-full transition-all duration-500 ${(data.sentiment_score ?? 50) >= 60 ? 'bg-emerald-500' : (data.sentiment_score ?? 50) <= 40 ? 'bg-red-500' : 'bg-slate-500'}`}
                style={{ width: `${data.sentiment_score ?? 50}%` }}
              ></div>
            </div>
          </div>
          <div className="flex justify-between text-[10px] text-slate-500 font-semibold font-mono">
            <span>PCR: {(data.pcr_oi ?? 0).toFixed(2)}</span>
            <span>Index: {data.sentiment_score ?? 50}/100</span>
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
                signal.includes('BUY') || signal.includes('BREAKOUT') ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-500/20' :
                signal.includes('SELL') || signal.includes('BREAKDOWN') ? 'bg-red-950/40 text-red-400 border border-red-500/20' : 'bg-slate-800 text-slate-400'
              }`}>
                {signal}
              </span>
            </div>
            <div className="text-right">
              <div className="text-[9px] text-slate-500 font-bold">CONFIDENCE</div>
              <div className="text-xs font-semibold text-slate-200">{confidence} ({data.trade_signals?.confidence_score ?? 50}%)</div>
            </div>
          </div>
          <div className="text-[9px] text-slate-400 font-semibold truncate">
            {data.trade_signals?.reason?.[0] || 'No signals generated currently.'}
          </div>
          {data.trade_signals?.equity_contribution !== undefined && data.trade_signals?.options_contribution !== undefined && (
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
          const stockChange = data.market_correlation?.stock_change_pct;
          const sectorChange = data.market_correlation?.sector_change_pct;
          const niftyChange = data.market_correlation?.nifty_change_pct;
          
          const isAvailable = stockChange !== null && stockChange !== undefined;
          
          const stockChangeStr = isAvailable ? `${stockChange!.toFixed(1)}%` : 'N/A';
          const sectorChangeStr = sectorChange !== null && sectorChange !== undefined ? `${sectorChange!.toFixed(1)}%` : 'N/A';
          const niftyChangeStr = niftyChange !== null && niftyChange !== undefined ? `${niftyChange!.toFixed(1)}%` : 'N/A';
          
          const stockColor = isAvailable ? (stockChange! >= 0 ? 'text-emerald-400' : 'text-red-400') : 'text-slate-500';
          const sectorColor = sectorChange !== null && sectorChange !== undefined ? (sectorChange! >= 0 ? 'text-emerald-400' : 'text-red-400') : 'text-slate-500';
          const niftyColor = niftyChange !== null && niftyChange !== undefined ? (niftyChange! >= 0 ? 'text-emerald-400' : 'text-red-400') : 'text-slate-500';
          
          const betaVal = data.market_correlation?.beta;
          const corrVal = data.market_correlation?.correlation_score;
          
          const betaStr = betaVal !== null && betaVal !== undefined ? betaVal.toFixed(2) : 'N/A';
          const corrStr = corrVal !== null && corrVal !== undefined ? corrVal.toFixed(2) : 'N/A';
          
          return (
            <div 
              className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md flex flex-col justify-between hover:border-slate-700/60 transition-all"
              title={isAvailable ? undefined : "Relative strength data unavailable"}
            >
              <div className="flex justify-between items-center">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Relative Strength</span>
                <span className="text-[10px] font-mono font-bold text-slate-400">{data.market_correlation?.sector_name ?? 'N/A'}</span>
              </div>
              <div className="my-2">
                <div className="text-[11px] font-bold text-purple-400 truncate">
                  {data.market_correlation?.relative_strength ?? 'N/A'}
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
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT & CENTER COLUMN: Advanced Charting & Intraday PCR/Flow Trends */}
        <div className="lg:col-span-2 space-y-6">
          {/* Lightweight Chart Panel */}
          <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-md">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
              <div>
                <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider flex items-center gap-1.5">
                  <BarChart2 size={14} className="text-purple-400" /> {
                    chartTimeframe === '5m' ? '5 Minute Chart (3 Months)' :
                    chartTimeframe === '15m' ? '15 Minute Chart (3 Months)' :
                    chartTimeframe === '30m' ? '30 Minute Chart (3 Months)' :
                    'Daily Chart (3 Months)'
                  }
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
            </div>
            
            <div className="relative h-[320px] min-h-[320px] bg-slate-950/40 rounded-xl overflow-hidden border border-slate-850">
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
              <div ref={chartContainerRef} className="w-full h-full min-h-[320px]"></div>
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
        </div>

        {/* RIGHT COLUMN: Open Interest Profile & Smart Money Panel */}
        <div className="space-y-6">
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
                <div className="text-purple-400 font-bold text-xs mt-0.5">{data.max_pain}</div>
              </div>
              <div className="border-x border-slate-800">
                <div className="text-slate-500 scale-95 uppercase font-bold">S Support</div>
                <div className="text-emerald-400 font-bold text-xs mt-0.5">{data.support_strike}</div>
              </div>
              <div>
                <div className="text-slate-500 scale-95 uppercase font-bold">R Resistance</div>
                <div className="text-red-400 font-bold text-xs mt-0.5">{data.resistance_strike}</div>
              </div>
            </div>
          </div>

          {/* Smart Money & Anomalies activity tracker */}
          <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-md">
            <h3 className="font-bold text-xs uppercase tracking-wider mb-4 flex items-center gap-1.5" style={{ color: '#FFFFFF' }}>
              <Award size={14} style={{ color: '#FFFFFF' }} /> SMART MONEY ACTIVITY
            </h3>
            <div className="space-y-3 max-h-[290px] overflow-y-auto pr-1">
              {data.smart_money_activity && data.smart_money_activity.length > 0 ? (
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
      </div>

      {/* =========================================================================
          TABS AREA: OPTION CHAIN, HEATMAP, BLOCK TRADES, TRADE SUMMARY
         ========================================================================= */}
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

    </div>
  );
});

export default OptionFlow;
