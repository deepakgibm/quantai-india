import React, { useState, useEffect, useRef, useMemo } from 'react';
import { TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight, RefreshCw, BarChart2, List, ShieldAlert, Award, Layers } from 'lucide-react';
import { useGlobalSymbol } from '../contexts/GlobalSymbolContext';
import { api } from '../services/api';
import GlobalSymbolSearch from '../components/GlobalSymbolSearch';
import ErrorCard from '../components/ErrorCard';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

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

interface OptionFlowData {
  status: string;
  symbol: string;
  expiry: string;
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
  strikes: StrikeData[];
  block_deals: BlockDeal[];
}

interface OptionFlowProps {
  isWidget?: boolean;
}

export const OptionFlow: React.FC<OptionFlowProps> = ({ isWidget = false }) => {
  const { selectedSymbol } = useGlobalSymbol();
  const [data, setData] = useState<OptionFlowData | null>(null);
  const [expiries, setExpiries] = useState<string[]>([]);
  const [selectedExpiry, setSelectedExpiry] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isNonFno, setIsNonFno] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'chain' | 'charts' | 'blocks'>('chain');
  const [brokerConnected, setBrokerConnected] = useState<boolean | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

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

  // Fetch Expiries first
  const fetchExpiries = async (symbol: string, bypassCache = false) => {
    setIsNonFno(false);
    setError(null);
    try {
      const response = await api.getOptionFlowExpiries(symbol, bypassCache);
      if (response && response.success && response.data && Array.isArray(response.data.expiries)) {
        setExpiries(response.data.expiries);
        setError(null); // Clear error on success
        if (response.data.expiries.length > 0) {
          // If previous expiry is not in new list, pick first one
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
  const fetchOptionFlow = async (symbol: string, expiry: string, forceSilent = false, bypassCache = false) => {
    if (isNonFno) {
      setLoading(false);
      return;
    }

    if (!forceSilent) {
      setLoading(true);
    }
    setError(null);

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      const response = await api.getOptionFlow(symbol, expiry, '', bypassCache);
      if (response && response.success && response.data) {
        setData(response.data);
        setError(null); // Clear error on success
        setLastUpdated(new Date().toLocaleTimeString());
      } else if (response && response.error) {
        if (!forceSilent || !data) {
          setError(response.error.message || 'Option flow data currently unavailable.');
        }
      } else {
        setError('Unexpected API response format.');
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error('[OptionFlow] Fetch details error:', err);
        if (err.status === 400 || err.message?.includes('F&O')) {
          setIsNonFno(true);
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

  // Run on Symbol change
  useEffect(() => {
    const init = async () => {
      // Clear old state immediately on symbol changes to prevent stale data display
      setData(null);
      setExpiries([]);
      setSelectedExpiry('');
      setIsNonFno(false);
      setError(null);
      setLoading(true);
      
      await Promise.all([
        fetchExpiries(selectedSymbol),
        checkBrokerStatus()
      ]);
    };
    init();
  }, [selectedSymbol]);

  // Run on Expiry change or after expiries are loaded
  useEffect(() => {
    if (selectedExpiry || isNonFno) {
      fetchOptionFlow(selectedSymbol, selectedExpiry);
    }

    // Auto-refresh every 15 seconds
    const interval = setInterval(() => {
      if (selectedExpiry && !isNonFno) {
        fetchOptionFlow(selectedSymbol, selectedExpiry, true);
        checkBrokerStatus();
      }
    }, 15000);

    return () => {
      clearInterval(interval);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [selectedSymbol, selectedExpiry, isNonFno]);

  const handleRetry = () => {
    setLoading(true);
    fetchExpiries(selectedSymbol, true); // Force bypass cache on manual retry
    checkBrokerStatus();
  };

  // Find ATM strike for highlighting
  const atmStrike = useMemo(() => {
    if (!data || !data.strikes || data.strikes.length === 0) return null;
    // We estimate ATM by finding where CE LTP is closest to PE LTP (approx spot)
    // or where they cross. Since we don't have Spot directly in response,
    // let's compute the strike with the minimum absolute difference between call ltp and put ltp.
    let minDiff = Infinity;
    let closestStrike = data.strikes[0].strike_price;
    data.strikes.forEach(s => {
      if (s.call.ltp > 0 && s.put.ltp > 0) {
        const diff = Math.abs(s.call.ltp - s.put.ltp);
        if (diff < minDiff) {
          minDiff = diff;
          closestStrike = s.strike_price;
        }
      }
    });
    return closestStrike;
  }, [data]);

  // Chart Data preparation (Recharts)
  const chartData = useMemo(() => {
    if (!data || !data.strikes) return [];
    // We filter strikes close to ATM (e.g. ±10 strikes) so the chart isn't too cluttered
    const atmIndex = data.strikes.findIndex(s => s.strike_price === atmStrike);
    const sliceStart = Math.max(0, atmIndex - 8);
    const sliceEnd = Math.min(data.strikes.length, atmIndex + 9);
    
    return data.strikes.slice(sliceStart, sliceEnd).map(s => ({
      strike: s.strike_price.toString(),
      'Call OI': s.call.oi,
      'Put OI': s.put.oi,
      'Call Premium (L)': Math.round(s.call.premium / 100000),
      'Put Premium (L)': Math.round(s.put.premium / 100000)
    }));
  }, [data, atmStrike]);

  if (isNonFno) {
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

  if (!marketOpen) {
    return (
      <div className="space-y-6">
        {!isWidget && (
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-white font-display">Option Flow Terminal</h2>
              <p className="text-sm text-slate-500 font-medium">NSE Market Closed</p>
            </div>
            <div className="flex items-center gap-3">
              <GlobalSymbolSearch />
              {expiries.length > 0 && (
                <select
                  value={selectedExpiry}
                  onChange={e => setSelectedExpiry(e.target.value)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 text-xs font-semibold focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 dark:focus:ring-emerald-500/50 dark:focus:border-emerald-500 transition-all outline-none cursor-pointer"
                >
                  {expiries.map(exp => (
                    <option key={exp} value={exp}>
                      Expiry: {exp}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>
        )}
        <div className="flex flex-col items-center justify-center p-8 min-h-[300px] rounded-2xl border border-slate-850 bg-slate-900/60 dark:bg-slate-950/40 backdrop-blur-md text-slate-100 shadow-2xl">
          <div className="w-12 h-12 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center mb-4 text-slate-400">
            <Layers size={24} />
          </div>
          <h3 className="font-display font-bold text-base text-slate-200 mb-2">
            Option Chain Unavailable
          </h3>
          <p className="text-xs text-slate-400 max-w-md text-center mb-4 font-medium leading-relaxed font-sans">
            Option chain data is temporarily unavailable. NSE market may be closed or Upstox API is not returning data.
          </p>
          <div className="text-xs text-slate-500 font-mono font-medium">
            Market Hours: Mon–Fri | 9:15 AM – 3:30 PM IST
          </div>
        </div>
      </div>
    );
  }

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
        <ErrorCard message={error} onRetry={handleRetry} title="Option Flow Analytics Error" />
      </div>
    );
  }

  const isDataEmpty = !data || !data.strikes || data.strikes.length === 0;

  if (isDataEmpty) {
    return (
      <div className="space-y-6">
        {!isWidget && (
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-white font-display">Option Flow Terminal</h2>
              <p className="text-sm text-slate-500 font-medium">Option Chain Unavailable</p>
            </div>
            <div className="flex items-center gap-3">
              <GlobalSymbolSearch />
            </div>
          </div>
        )}
        <div className="flex flex-col items-center justify-center p-8 min-h-[300px] rounded-2xl border border-slate-850 bg-slate-900/60 dark:bg-slate-950/40 backdrop-blur-md text-slate-100 shadow-2xl">
          <div className="w-12 h-12 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center mb-4 text-slate-400">
            <Layers size={24} />
          </div>
          <h3 className="font-display font-bold text-base text-slate-200 mb-2">
            Option Chain Unavailable
          </h3>
          <p className="text-xs text-slate-400 max-w-md text-center mb-4 font-medium leading-relaxed font-sans">
            Option chain data is temporarily unavailable. NSE market may be closed or Upstox API is not returning data.
          </p>
          <div className="text-xs text-slate-500 font-mono font-medium mb-6">
            Market Hours: Mon–Fri | 9:15 AM – 3:30 PM IST
          </div>
          <button
            onClick={handleRetry}
            className="flex items-center gap-2 px-5 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 active:bg-emerald-700 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all cursor-pointer border-0"
          >
            {loading && <RefreshCw size={12} className="animate-spin" />}
            Retry Request
          </button>
        </div>
      </div>
    );
  }

  // Sentiment classes
  const isBullish = data.sentiment.toLowerCase() === 'bullish';
  const isBearish = data.sentiment.toLowerCase() === 'bearish';
  const sentimentColor = isBullish ? 'text-emerald-500' : isBearish ? 'text-red-500' : 'text-slate-400';
  const sentimentBg = isBullish ? 'bg-emerald-500/10' : isBearish ? 'bg-red-500/10' : 'bg-slate-800';

  // Format premium figures
  const formatPremium = (val: number) => {
    if (val >= 10000000) {
      return `₹${(val / 10000000).toFixed(2)} Cr`;
    }
    if (val >= 100000) {
      return `₹${(val / 100000).toFixed(2)} L`;
    }
    return `₹${val.toLocaleString('en-IN')}`;
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      {!isWidget ? (
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-bold tracking-tight text-white font-display">
                {data.symbol} Option Flow
              </h2>
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                {data.expiry}
              </span>
            </div>
            <div className="flex items-center gap-4 mt-1">
              <p className="text-xs text-slate-500 font-semibold">
                Real-time derivative sentiment and order tracking.
              </p>
              <div className="flex items-center gap-1.5 text-[10px] font-semibold font-mono">
                <span className={`w-2 h-2 rounded-full ${brokerConnected === true ? 'bg-emerald-500 animate-pulse' : brokerConnected === false ? 'bg-red-500 animate-pulse' : 'bg-yellow-500'}`}></span>
                <span className={brokerConnected === true ? 'text-emerald-400' : brokerConnected === false ? 'text-red-400' : 'text-yellow-400'}>
                  {brokerConnected === true ? 'Broker Connected' : brokerConnected === false ? 'Broker Disconnected' : 'Checking Broker...'}
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <GlobalSymbolSearch />
            
            {/* Expiry Selector */}
            {expiries.length > 0 && (
              <select
                value={selectedExpiry}
                onChange={e => setSelectedExpiry(e.target.value)}
                className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 text-xs font-semibold focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 dark:focus:ring-emerald-500/50 dark:focus:border-emerald-500 transition-all outline-none cursor-pointer"
              >
                {expiries.map(exp => (
                  <option key={exp} value={exp}>
                    Expiry: {exp}
                  </option>
                ))}
              </select>
            )}

            <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono mt-1 w-full lg:w-auto text-left lg:text-right">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
              </span>
              <span>Auto-Refreshed: {lastUpdated || 'Never'}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-white font-display flex items-center gap-2">
              <TrendingUp size={15} className="text-emerald-500" /> Option Flow Analytics
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
              {data.expiry}
            </span>
            <div className="flex items-center gap-1.5 text-[9px] font-semibold font-mono">
              <span className={`w-1.5 h-1.5 rounded-full ${brokerConnected === true ? 'bg-emerald-500 animate-pulse' : brokerConnected === false ? 'bg-red-500 animate-pulse' : 'bg-yellow-500'}`}></span>
              <span className={brokerConnected === true ? 'text-emerald-400' : brokerConnected === false ? 'text-red-400' : 'text-yellow-400'}>
                {brokerConnected === true ? 'Live' : brokerConnected === false ? 'Offline' : 'Checking'}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {expiries.length > 0 && (
              <select
                value={selectedExpiry}
                onChange={e => setSelectedExpiry(e.target.value)}
                className="px-2 py-1 rounded border border-slate-800 bg-slate-950 text-slate-200 text-[10px] font-medium focus:ring-1 focus:ring-emerald-500 transition-all outline-none cursor-pointer"
              >
                {expiries.map(exp => (
                  <option key={exp} value={exp}>
                    Expiry: {exp}
                  </option>
                ))}
              </select>
            )}
            <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
              </span>
              <span>Updated: {lastUpdated || 'Never'}</span>
            </div>
          </div>
        </div>
      )}

      {/* Metric Cards Row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Call Premium */}
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl flex flex-col justify-between">
          <span className="text-xs text-slate-500 font-semibold flex items-center gap-1">
            Call Turnover
          </span>
          <div className="mt-2">
            <span className="text-lg font-bold text-slate-100 font-mono">
              {formatPremium(data.total_call_premium)}
            </span>
          </div>
          <span className="text-[10px] text-slate-500 mt-2 font-mono">
            {data.total_call_volume.toLocaleString()} contracts
          </span>
        </div>

        {/* Put Premium */}
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl flex flex-col justify-between">
          <span className="text-xs text-slate-500 font-semibold flex items-center gap-1">
            Put Turnover
          </span>
          <div className="mt-2">
            <span className="text-lg font-bold text-slate-100 font-mono">
              {formatPremium(data.total_put_premium)}
            </span>
          </div>
          <span className="text-[10px] text-slate-500 mt-2 font-mono">
            {data.total_put_volume.toLocaleString()} contracts
          </span>
        </div>

        {/* Net Flow */}
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl flex flex-col justify-between">
          <span className="text-xs text-slate-500 font-semibold flex items-center gap-1">
            Net Premium Flow
          </span>
          <div className="mt-2">
            <span className={`text-lg font-bold font-mono ${data.net_flow >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
              {data.net_flow >= 0 ? '+' : ''}{formatPremium(data.net_flow)}
            </span>
          </div>
          <span className="text-[10px] text-slate-500 mt-2 font-semibold">
            {data.net_flow >= 0 ? 'Call dominated buying' : 'Put dominated buying'}
          </span>
        </div>

        {/* PCR */}
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl flex flex-col justify-between">
          <span className="text-xs text-slate-500 font-semibold flex items-center gap-1">
            Put-Call Ratio (PCR)
          </span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-lg font-bold text-slate-100 font-mono">
              {data.pcr_oi.toFixed(2)}
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              (Vol: {data.pcr_volume.toFixed(2)})
            </span>
          </div>
          <span className="text-[10px] text-slate-500 mt-2 font-medium">PCR &gt; 1.0 is historically bullish</span>
        </div>

        {/* Sentiment */}
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl flex flex-col justify-between">
          <span className="text-xs text-slate-500 font-semibold flex items-center gap-1">
            Option Sentiment
          </span>
          <div className="mt-2">
            <span className={`text-lg font-bold font-display px-2 py-0.5 rounded ${sentimentBg} ${sentimentColor}`}>
              {data.sentiment}
            </span>
          </div>
          <span className="text-[10px] text-slate-500 mt-2 font-medium">Derived from PCR & OI shifts</span>
        </div>
      </div>

      {/* Tabs Menu */}
      <div className="flex border-b border-slate-800 gap-2">
        <button
          onClick={() => setActiveTab('chain')}
          className={`px-4 py-2 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'chain'
              ? 'border-emerald-500 text-emerald-400 bg-emerald-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers size={14} /> Option Chain
        </button>
        <button
          onClick={() => setActiveTab('charts')}
          className={`px-4 py-2 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'charts'
              ? 'border-emerald-500 text-emerald-400 bg-emerald-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <BarChart2 size={14} /> Strike Distribution
        </button>
        <button
          onClick={() => setActiveTab('blocks')}
          className={`px-4 py-2 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'blocks'
              ? 'border-emerald-500 text-emerald-400 bg-emerald-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Award size={14} /> Block Trades ({data.block_deals.length})
        </button>
      </div>

      {/* Tabs Content */}
      <div className="min-h-[400px]">
        {activeTab === 'chain' && (
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/40">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/80 text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                  <th className="px-4 py-3 text-center border-r border-slate-800/60" colSpan={5}>Calls (CE)</th>
                  <th className="px-4 py-3 text-center border-r border-slate-800/60">Strike</th>
                  <th className="px-4 py-3 text-center" colSpan={5}>Puts (PE)</th>
                </tr>
                <tr className="border-b border-slate-800 text-[10px] text-slate-500 font-bold uppercase tracking-wider">
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
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50 font-mono text-[11px]">
                {data.strikes.map((s) => {
                  const isAtm = s.strike_price === atmStrike;
                  const rowBg = isAtm 
                    ? 'bg-purple-900/10 hover:bg-purple-900/15 border-y border-purple-500/20' 
                    : 'hover:bg-slate-800/25';
                  
                  // Heat intensifier calculations
                  const ceOiChg = s.call.oi_change;
                  const peOiChg = s.put.oi_change;
                  
                  const ceChgColor = ceOiChg > 0 ? 'text-emerald-400' : ceOiChg < 0 ? 'text-red-400' : 'text-slate-400';
                  const peChgColor = peOiChg > 0 ? 'text-emerald-400' : peOiChg < 0 ? 'text-red-400' : 'text-slate-400';

                  const ceChgBg = ceOiChg > 10000 ? 'bg-emerald-950/20' : ceOiChg < -10000 ? 'bg-red-950/20' : '';
                  const peChgBg = peOiChg > 10000 ? 'bg-emerald-950/20' : peOiChg < -10000 ? 'bg-red-950/20' : '';

                  return (
                    <tr key={s.strike_price} className={`${rowBg} transition-colors`}>
                      {/* CALLS */}
                      <td className="px-4 py-2 text-slate-300">{s.call.oi.toLocaleString()}</td>
                      <td className={`px-4 py-2 font-bold ${ceChgColor} ${ceChgBg}`}>
                        {ceOiChg > 0 ? '+' : ''}{ceOiChg.toLocaleString()}
                      </td>
                      <td className="px-4 py-2 text-slate-400">{s.call.volume.toLocaleString()}</td>
                      <td className="px-4 py-2 text-slate-400">{s.call.iv.toFixed(1)}%</td>
                      <td className="px-4 py-2 font-semibold text-emerald-400 border-r border-slate-800/60">
                        ₹{s.call.ltp.toFixed(2)}
                      </td>
                      
                      {/* STRIKE */}
                      <td className={`px-4 py-2 text-center font-bold border-r border-slate-800/60 text-slate-100 ${isAtm ? 'text-purple-400' : ''}`}>
                        {s.strike_price.toFixed(1)}
                      </td>
                      
                      {/* PUTS */}
                      <td className="px-4 py-2 font-semibold text-emerald-400">
                        ₹{s.put.ltp.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-slate-400">{s.put.iv.toFixed(1)}%</td>
                      <td className="px-4 py-2 text-slate-400">{s.put.volume.toLocaleString()}</td>
                      <td className={`px-4 py-2 font-bold ${peChgColor} ${peChgBg}`}>
                        {peOiChg > 0 ? '+' : ''}{peOiChg.toLocaleString()}
                      </td>
                      <td className="px-4 py-2 text-slate-300">{s.put.oi.toLocaleString()}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'charts' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* OI Distribution Chart */}
            <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/60">
              <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mb-6 flex items-center gap-1.5">
                <BarChart2 size={14} className="text-emerald-400" /> Open Interest (Contracts)
              </h3>
              <div className="w-full h-[320px]">
                {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                      <CartesianGrid stroke="#1e293b" vertical={false} />
                      <XAxis dataKey="strike" stroke="#475569" fontSize={9} />
                      <YAxis stroke="#475569" fontSize={9} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
                        labelStyle={{ color: '#64748b' }}
                      />
                      <Legend fontSize={10} />
                      <Bar dataKey="Call OI" fill="#10b981" radius={[2, 2, 0, 0]} />
                      <Bar dataKey="Put OI" fill="#ef4444" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-slate-500 font-medium">
                    No strike data available.
                  </div>
                )}
              </div>
            </div>

            {/* Premium Turnover Chart */}
            <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/60">
              <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider mb-6 flex items-center gap-1.5">
                <BarChart2 size={14} className="text-emerald-400" /> Premium Turnover (₹ Lakhs)
              </h3>
              <div className="w-full h-[320px]">
                {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                      <CartesianGrid stroke="#1e293b" vertical={false} />
                      <XAxis dataKey="strike" stroke="#475569" fontSize={9} />
                      <YAxis stroke="#475569" fontSize={9} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
                        labelStyle={{ color: '#64748b' }}
                      />
                      <Legend />
                      <Bar dataKey="Call Premium (L)" fill="#10b981" radius={[2, 2, 0, 0]} />
                      <Bar dataKey="Put Premium (L)" fill="#ef4444" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-slate-500 font-medium">
                    No premium data available.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'blocks' && (
          <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/60">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-slate-200 font-bold text-xs uppercase tracking-wider flex items-center gap-1.5">
                <Award size={14} className="text-emerald-400 animate-pulse" /> Large Block Deals Tape
              </h3>
              <span className="text-[10px] text-slate-500 uppercase font-mono">
                Threshold: &gt; ₹10 Lakhs Premium
              </span>
            </div>

            {data.block_deals.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[11px] border-collapse font-mono">
                  <thead>
                    <tr className="border-b border-slate-800 text-[10px] text-slate-500 font-bold uppercase">
                      <th className="py-2">Strike</th>
                      <th className="py-2">Option Type</th>
                      <th className="py-2 text-right">LTP</th>
                      <th className="py-2 text-right">Volume</th>
                      <th className="py-2 text-right">Premium Value</th>
                      <th className="py-2 text-right">Open Interest</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40">
                    {data.block_deals.map((block, idx) => {
                      const isCe = block.type === 'CE';
                      return (
                        <tr key={idx} className="hover:bg-slate-800/20">
                          <td className="py-2 text-slate-100 font-bold">{block.strike_price.toFixed(1)}</td>
                          <td className="py-2">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              isCe ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'
                            }`}>
                              {block.type}
                            </span>
                          </td>
                          <td className="py-2 text-right text-slate-200">₹{block.ltp.toFixed(2)}</td>
                          <td className="py-2 text-right text-slate-400">{block.volume.toLocaleString()}</td>
                          <td className="py-2 text-right text-emerald-400 font-bold">{formatPremium(block.premium)}</td>
                          <td className="py-2 text-right text-slate-300">{block.oi.toLocaleString()}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-12 text-center text-slate-500 font-medium">
                No block trades exceeding ₹10L premium detected for this expiry.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default OptionFlow;
