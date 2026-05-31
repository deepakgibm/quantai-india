import React, { useState, useEffect, useRef } from 'react';
import { Activity, Shield, TrendingUp, Info, AlertTriangle, TrendingDown, ArrowUpRight, ArrowDownRight, BarChart2 } from 'lucide-react';
import { useGlobalSymbol } from '../contexts/GlobalSymbolContext';
import { api } from '../services/api';
import GlobalSymbolSearch from '../components/GlobalSymbolSearch';
import DayFilter from '../components/DayFilter';
import ErrorCard from '../components/ErrorCard';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface TimeSeriesItem {
  date: string;
  price: number;
  volatility: number;
  atr: number;
}

interface InvestorSummary {
  action: string;
  confidence: number;
  risk_level: string;
  summary: string;
  reasons: string[];
}

interface VolatilityData {
  status: string;
  symbol: string;
  company_name: string;
  sector: string;
  exchange: string;
  is_fno: boolean;
  latest_price: number;
  price_change_pct: number;
  india_vix: number;
  historical_volatility: number;
  implied_volatility: number;
  iv_rank: number;
  iv_percentile: number;
  atr: number;
  regime: string;
  mean_reversion_probability: number;
  time_series: TimeSeriesItem[];
  investor_summary?: InvestorSummary;
}

export const VolatilityDashboard: React.FC = () => {
  const { selectedSymbol, selectedDays } = useGlobalSymbol();
  const [data, setData] = useState<VolatilityData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>('');
  const [isWhyOpen, setIsWhyOpen] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchVolatility = async (symbol: string, days: number, forceSilent = false) => {
    if (!forceSilent) {
      setLoading(true);
    }
    setError(null);

    // Abort previous request if in flight
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      const response = await api.getVolatility(symbol, days);
      if (response && response.status === 'success') {
        setData(response);
        setLastUpdated(new Date().toLocaleTimeString());
      } else if (response && response.status === 'error') {
        setError(response.message || 'Error loading volatility analysis.');
      } else {
        setError('Unexpected API response.');
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error('[VolatilityDashboard] Fetch error:', err);
        setError(err.message || 'Failed to fetch volatility analytics from server.');
      }
    } finally {
      if (!forceSilent) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    fetchVolatility(selectedSymbol, selectedDays);

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      fetchVolatility(selectedSymbol, selectedDays, true);
    }, 30000);

    return () => {
      clearInterval(interval);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [selectedSymbol, selectedDays]);

  const handleRetry = () => {
    fetchVolatility(selectedSymbol, selectedDays);
  };

  // Render Skeleton Loader
  const renderSkeletons = () => (
    <div className="space-y-6">
      {/* Metric Cards Skeleton */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-3 animate-pulse">
            <div className="h-3 w-16 bg-slate-800 rounded"></div>
            <div className="h-8 w-24 bg-slate-800 rounded"></div>
            <div className="h-3 w-20 bg-slate-800 rounded"></div>
          </div>
        ))}
      </div>

      {/* Main Panels Skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl space-y-4 animate-pulse">
          <div className="h-4 w-32 bg-slate-800 rounded"></div>
          <div className="h-20 bg-slate-800 rounded"></div>
          <div className="h-4 w-40 bg-slate-800 rounded"></div>
          <div className="h-16 bg-slate-800 rounded"></div>
        </div>
        <div className="lg:col-span-2 p-6 bg-slate-900 border border-slate-800 rounded-xl space-y-4 animate-pulse">
          <div className="flex justify-between items-center">
            <div className="h-4 w-48 bg-slate-800 rounded"></div>
            <div className="h-4 w-24 bg-slate-800 rounded"></div>
          </div>
          <div className="h-[300px] bg-slate-800 rounded"></div>
        </div>
      </div>
    </div>
  );

  if (loading && !data) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white font-display">Volatility Index Dashboard</h2>
            <p className="text-sm text-slate-500 font-medium">Analyzing historical and implied regime metrics...</p>
          </div>
        </div>
        {renderSkeletons()}
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white font-display">Volatility Index Dashboard</h2>
            <p className="text-sm text-slate-500 font-medium">Error loading details</p>
          </div>
          <div className="flex items-center gap-3">
            <GlobalSymbolSearch />
            <DayFilter />
          </div>
        </div>
        <ErrorCard message={error || ''} onRetry={handleRetry} title="Volatility Analytics Error" />
      </div>
    );
  }

  if (!data) return null;

  const priceChangeColor = data.price_change_pct >= 0 ? 'text-emerald-500' : 'text-red-500';
  const priceChangeBg = data.price_change_pct >= 0 ? 'bg-emerald-500/10' : 'bg-red-500/10';

  // Determine Regime color themes
  const isHighVol = data.regime.toLowerCase().includes('high');
  const isLowVol = data.regime.toLowerCase().includes('low');
  const regimeColor = isHighVol ? 'text-orange-500' : isLowVol ? 'text-cyan-500' : 'text-emerald-500';
  const regimeBorder = isHighVol ? 'border-orange-500/30' : isLowVol ? 'border-cyan-500/30' : 'border-emerald-500/30';
  const regimeBg = isHighVol ? 'bg-orange-500/5' : isLowVol ? 'bg-cyan-500/5' : 'bg-emerald-500/5';

  return (
    <div className="space-y-6">
      {/* Dashboard Top Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold tracking-tight text-white font-display">
              {data.symbol} Volatility Analysis
            </h2>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-400">
              {data.exchange}
            </span>
            {data.is_fno && (
              <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded bg-purple-900/30 text-purple-400 border border-purple-800/30">
                Derivatives Active
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">
            {data.company_name} &bull; Sector: {data.sector || 'N/A'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <GlobalSymbolSearch />
          <DayFilter />
          <div className="text-[10px] text-slate-500 font-mono mt-1 w-full lg:w-auto text-left lg:text-right">
            Updated: {lastUpdated || 'Never'}
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        {/* Spot Price */}
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl flex flex-col justify-between">
          <span className="text-xs text-slate-500 font-semibold flex items-center gap-1.5">
            LTP (Spot)
          </span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold text-slate-100 font-mono">
              ₹{data.latest_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <div className={`mt-2 inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold w-fit ${priceChangeBg} ${priceChangeColor}`}>
            {data.price_change_pct >= 0 ? <ArrowUpRight size={10} /> : <ArrowDownRight size={10} />}
            {data.price_change_pct >= 0 ? '+' : ''}{data.price_change_pct.toFixed(2)}%
          </div>
        </div>

        {/* India VIX */}
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl flex flex-col justify-between">
          <span className="text-xs text-slate-500 font-semibold flex items-center gap-1.5">
            India VIX
          </span>
          <div className="mt-2">
            <span className="text-xl font-bold text-slate-100 font-mono">
              {data.india_vix.toFixed(2)}%
            </span>
          </div>
          <span className="text-[10px] text-slate-500 mt-2 font-medium">Market fear index</span>
        </div>

        {/* Implied Volatility (IV) */}
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl flex flex-col justify-between">
          <span className="text-xs text-slate-500 font-semibold flex items-center gap-1.5">
            Implied Vol (IV)
          </span>
          <div className="mt-2">
            <span className="text-xl font-bold text-slate-100 font-mono">
              {data.implied_volatility.toFixed(2)}%
            </span>
          </div>
          <span className="text-[10px] text-slate-500 mt-2 font-medium">
            {data.is_fno ? 'ATM option chain IV' : 'HV proxy (Non-F&O)'}
          </span>
        </div>

        {/* Historical Volatility (HV) */}
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl flex flex-col justify-between">
          <span className="text-xs text-slate-500 font-semibold flex items-center gap-1.5">
            Hist Vol (HV)
          </span>
          <div className="mt-2">
            <span className="text-xl font-bold text-slate-100 font-mono">
              {data.historical_volatility.toFixed(2)}%
            </span>
          </div>
          <span className="text-[10px] text-slate-500 mt-2 font-medium">{selectedDays}-day standard lookback</span>
        </div>

        {/* IV Rank */}
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl flex flex-col justify-between">
          <span className="text-xs text-slate-500 font-semibold flex items-center gap-1.5">
            IV Rank
          </span>
          <div className="mt-2">
            <span className="text-xl font-bold text-slate-100 font-mono">
              {data.iv_rank.toFixed(1)}
            </span>
          </div>
          <div className="w-full bg-slate-800 h-1 rounded-full mt-3 overflow-hidden">
            <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${Math.min(data.iv_rank, 100)}%` }}></div>
          </div>
        </div>

        {/* IV Percentile */}
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl flex flex-col justify-between">
          <span className="text-xs text-slate-500 font-semibold flex items-center gap-1.5">
            IV Percentile
          </span>
          <div className="mt-2">
            <span className="text-xl font-bold text-slate-100 font-mono">
              {data.iv_percentile.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-slate-800 h-1 rounded-full mt-3 overflow-hidden">
            <div className="bg-purple-500 h-full rounded-full" style={{ width: `${Math.min(data.iv_percentile, 100)}%` }}></div>
          </div>
        </div>
      </div>

      {/* Main Charts & Regime Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Hand: Volatility Regime & Mean Reversion Signals */}
        <div className="space-y-6 flex flex-col">
          {/* Regime Card */}
          <div className={`p-6 rounded-xl border bg-slate-900/60 backdrop-blur-md flex flex-col justify-between flex-1 ${regimeBorder} ${regimeBg}`}>
            <div>
              <h3 className="text-slate-400 font-bold text-xs uppercase tracking-wider flex items-center gap-2 mb-4">
                <Activity size={14} className={regimeColor} /> Volatility Regime
              </h3>
              <div className="flex flex-col gap-2">
                <span className={`text-2xl font-bold font-display ${regimeColor}`}>
                  {data.regime}
                </span>
                <p className="text-sm text-slate-400 font-medium leading-relaxed mt-2">
                  {isHighVol 
                    ? 'Current option implied volatility is significantly elevated compared to its historical mean, indicating wide price swings. Favorable for Option Sellers (Premium Decay).'
                    : isLowVol
                    ? 'Volatility is trading at depressed levels, suggesting a consolidation period. Options are cheap, pointing to potential expansion setups. Favorable for Option Buyers.'
                    : 'Volatility levels are trading inside their historical standard deviations. Trend is likely to continue at its current moderate momentum.'
                  }
                </p>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-800/80 flex justify-between items-center text-xs">
              <span className="text-slate-500 font-semibold">14-Day ATR:</span>
              <span className="font-mono font-bold text-slate-200">
                ₹{data.atr.toFixed(2)} ({(data.atr / data.latest_price * 100).toFixed(2)}%)
              </span>
            </div>
          </div>

          {/* Simple Investor Summary Card */}
          {data.investor_summary && (() => {
            const summary = data.investor_summary;
            const action = summary.action;
            
            // Define Action Color Schemes
            let actionColor = 'text-yellow-400 bg-yellow-950/40 border-yellow-500/20';
            let actionDotColor = 'bg-yellow-400';
            let cardBorderColor = 'border-slate-800 bg-slate-900/70';
            
            if (action === 'STRONG BUY') {
              actionColor = 'text-emerald-400 bg-emerald-950/70 border-emerald-500/30';
              actionDotColor = 'bg-emerald-400';
              cardBorderColor = 'border-emerald-500/30 bg-emerald-950/5';
            } else if (action === 'BUY') {
              actionColor = 'text-emerald-500/90 bg-emerald-900/30 border-emerald-500/10';
              actionDotColor = 'bg-emerald-500';
              cardBorderColor = 'border-emerald-500/10 bg-emerald-500/5';
            } else if (action === 'SELL') {
              actionColor = 'text-orange-400 bg-orange-950/40 border-orange-500/20';
              actionDotColor = 'bg-orange-400';
              cardBorderColor = 'border-orange-500/30 bg-orange-950/5';
            } else if (action === 'WAIT FOR BETTER ENTRY') {
              actionColor = 'text-red-400 bg-red-950/70 border-red-500/40';
              actionDotColor = 'bg-red-400';
              cardBorderColor = 'border-red-500/30 bg-red-950/5';
            }

            return (
              <div className={`p-6 rounded-xl border backdrop-blur-md flex flex-col justify-between ${cardBorderColor}`}>
                <div>
                  <h3 className="text-slate-400 font-bold text-xs uppercase tracking-wider flex items-center gap-2 mb-4">
                    <span className={`w-2.5 h-2.5 rounded-full ${actionDotColor}`}></span> Simple Investor Summary
                  </h3>
                  
                  <div className="flex flex-col gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-500">Action:</span>
                      <span className={`text-xs font-bold font-mono px-2.5 py-0.5 rounded border uppercase ${actionColor}`}>
                        {action}
                      </span>
                    </div>

                    <p className="text-sm text-slate-200 font-medium leading-relaxed">
                      {summary.summary}
                    </p>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-slate-800/80 flex flex-wrap gap-4 text-xs justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-500 font-semibold">Risk Level:</span>
                    <span className="font-bold text-slate-300 font-mono">{summary.risk_level}</span>
                  </div>

                  <div 
                    className="flex items-center gap-1.5 cursor-help"
                    title="Higher confidence means more indicators agree with the recommendation."
                  >
                    <span className="text-slate-500 font-semibold">Confidence:</span>
                    <span className="font-bold text-slate-300 font-mono">{summary.confidence}%</span>
                    <Info size={12} className="text-slate-500" />
                  </div>
                </div>

                {/* Expandable Explanation Section */}
                <div className="mt-4 pt-3 border-t border-slate-800/40">
                  <button
                    onClick={() => setIsWhyOpen(!isWhyOpen)}
                    className="text-xs font-bold text-purple-400 hover:text-purple-300 flex items-center gap-1.5 focus:outline-none transition-all cursor-pointer border-0 bg-transparent p-0"
                  >
                    <span>{isWhyOpen ? 'Hide Description' : 'Why am I seeing this recommendation?'}</span>
                    <svg
                      className={`w-3 h-3 transition-transform duration-200 ${isWhyOpen ? 'rotate-180' : ''}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                    </svg>
                  </button>

                  {isWhyOpen && (
                    <div className="mt-2.5 p-3 rounded-lg bg-slate-950/40 border border-slate-800/50 space-y-1.5 text-xs text-slate-400 animate-fadeIn">
                      <div className="font-semibold text-slate-500 text-[10px] uppercase tracking-wider mb-1">Recommendation Reasons:</div>
                      {summary.reasons.map((reason, idx) => (
                        <div key={idx} className="flex items-start gap-1.5 leading-relaxed">
                          <span className="text-purple-400/80 mt-0.5">•</span>
                          <span>{reason}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })()}

          {/* Mean Reversion Probability */}
          <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/70 backdrop-blur-md flex flex-col justify-between">
            <h3 className="text-slate-400 font-bold text-xs uppercase tracking-wider flex items-center gap-2 mb-4">
              <Shield size={14} className="text-purple-400" /> Statistical Signals
            </h3>

            <div className="flex items-center gap-6 my-2">
              <div className="relative w-20 h-20 flex items-center justify-center">
                {/* SVG Progress Circle */}
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="40"
                    cy="40"
                    r="34"
                    stroke="#1e293b"
                    strokeWidth="6"
                    fill="transparent"
                  />
                  <circle
                    cx="40"
                    cy="40"
                    r="34"
                    stroke={data.mean_reversion_probability > 70 ? '#eab308' : data.mean_reversion_probability > 40 ? '#10b981' : '#3b82f6'}
                    strokeWidth="6"
                    strokeDasharray={2 * Math.PI * 34}
                    strokeDashoffset={2 * Math.PI * 34 * (1 - data.mean_reversion_probability / 100)}
                    strokeLinecap="round"
                    fill="transparent"
                  />
                </svg>
                <div className="absolute text-center">
                  <span className="text-lg font-bold font-mono text-slate-100">
                    {data.mean_reversion_probability.toFixed(0)}%
                  </span>
                </div>
              </div>

              <div className="flex-1">
                <span className="text-xs text-slate-400 font-bold block mb-1">
                  Mean Reversion Z-Score
                </span>
                <p className="text-xs text-slate-500 font-medium leading-relaxed">
                  Probability that the stock's volatility returns to the historical mean. High values indicate peak expansion/contraction ready to reverse.
                </p>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-slate-800/80 flex justify-between items-center text-xs">
              <span className="text-slate-500 font-semibold">Instrument Regime:</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                Mean Reverting
              </span>
            </div>
          </div>
        </div>

        {/* Right Hand: Interactive Volatility Chart */}
        <div className="lg:col-span-2 p-6 rounded-xl border border-slate-800 bg-slate-900/70 backdrop-blur-md flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-slate-200 font-bold text-sm flex items-center gap-2">
              <BarChart2 size={16} className="text-emerald-400" /> Historical Volatility Time Series
            </h3>
            <span className="text-xs text-slate-500 font-medium">
              Lookback: {selectedDays} Days
            </span>
          </div>

          <div className="flex-1 w-full min-h-[300px]">
            {data.time_series && data.time_series.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                <AreaChart
                  data={data.time_series}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="volatilityGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="date"
                    stroke="#475569"
                    fontSize={10}
                    tickLine={false}
                    axisLine={false}
                    dy={10}
                  />
                  <YAxis
                    stroke="#475569"
                    fontSize={10}
                    tickLine={false}
                    axisLine={false}
                    domain={['auto', 'auto']}
                    dx={-5}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#1e293b',
                      borderRadius: '8px',
                      color: '#f1f5f9',
                      fontSize: '11px',
                    }}
                    labelStyle={{ color: '#64748b', fontWeight: 'bold' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="volatility"
                    name="HV (%)"
                    stroke="#10b981"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#volatilityGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-slate-500 font-medium">
                No time-series data available for chart.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VolatilityDashboard;
