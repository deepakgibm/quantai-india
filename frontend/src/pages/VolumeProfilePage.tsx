import React, { useState, useEffect, useMemo } from 'react';
import { 
  TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight, RefreshCw, 
  ShieldAlert, Activity, Target, ShieldCheck, Flame, Cpu, 
  HelpCircle, AlertTriangle, Scale, Percent, Zap, ChevronRight
} from 'lucide-react';
import { useGlobalSymbol } from '../contexts/GlobalSymbolContext';
import { api } from '../services/api';
import GlobalSymbolSearch from '../components/GlobalSymbolSearch';
import ErrorCard from '../components/ErrorCard';
import { 
  ResponsiveContainer, LineChart, Line, BarChart, Bar, 
  XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, Cell
} from 'recharts';

interface PricePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface HistogramBin {
  price_min: number;
  price_max: number;
  volume: number;
}

interface TimeframeData {
  shape: string;
  verdict: string;
}

interface RiskManagement {
  entry_zone: string;
  stop_loss: number;
  target_1: number;
  target_2: number;
  risk_reward_ratio: number;
}

interface SectorIntegration {
  sector_name: string;
  sector_score: number;
  sector_rank: number;
  relative_strength_rank: number;
}

interface VolumeProfileData {
  status: string;
  symbol: string;
  company_name: string;
  sector: string;
  price: number;
  poc: number;
  vah: number;
  val: number;
  hvn: number[];
  lvn: number[];
  shape: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  verdict: string;
  confidence: number;
  risk_score: number;
  institutional_bias: string;
  summary: string;
  factors: string[];
  histogram: HistogramBin[];
  price_history: PricePoint[];
  timeframes: {
    daily: TimeframeData;
    weekly: TimeframeData;
    monthly: TimeframeData;
  };
  risk_management: RiskManagement;
  sector_integration: SectorIntegration;
}

interface VolumeProfilePageProps {
  onNavigate?: (page: any) => void;
}

const VolumeProfilePage: React.FC<VolumeProfilePageProps> = () => {
  const { selectedSymbol } = useGlobalSymbol();
  const [data, setData] = useState<VolumeProfileData | null>(null);
  const [lookback, setLookback] = useState<number>(90);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  useEffect(() => {
    const fetchVolumeProfile = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.getVolumeProfileData(selectedSymbol, lookback);
        if (response && response.status === 'success') {
          setData(response);
        } else {
          setError('Failed to fetch volume profile analysis data.');
        }
      } catch (err: any) {
        console.error('Error fetching volume profile:', err);
        setError(err.message || 'Failed to connect to Volume Profile API.');
      } finally {
        setLoading(false);
      }
    };

    fetchVolumeProfile();
  }, [selectedSymbol, lookback, refreshTrigger]);

  const handleRefresh = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  // Compute common Y-axis domain to align charts perfectly
  const chartConfigs = useMemo(() => {
    if (!data || !data.price_history || data.price_history.length === 0) {
      return { yDomain: [0, 100], histogramWithMids: [] };
    }

    const prices = data.price_history.map(p => p.close);
    const lows = data.price_history.map(p => p.low);
    const highs = data.price_history.map(p => p.high);

    // Get absolute price limits
    let minPrice = Math.min(...lows, data.val);
    let maxPrice = Math.max(...highs, data.vah);

    const padding = (maxPrice - minPrice) * 0.08;
    const yDomain = [Math.max(0, minPrice - padding), maxPrice + padding];

    // Compute midpoints for histogram bins to plot on vertical scale
    const histogramWithMids = data.histogram.map(bin => ({
      ...bin,
      price_mid: (bin.price_min + bin.price_max) / 2
    }));

    return { yDomain, histogramWithMids };
  }, [data]);

  // Loading skeleton layout
  const renderSkeletons = () => (
    <div className="space-y-6 animate-pulse">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl space-y-3">
            <div className="h-3 w-16 bg-slate-800 rounded"></div>
            <div className="h-8 w-24 bg-slate-800 rounded"></div>
            <div className="h-3 w-28 bg-slate-800 rounded"></div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 h-[450px] bg-slate-900/60 border border-slate-800/80 rounded-xl p-6">
          <div className="h-6 w-48 bg-slate-800 rounded mb-4"></div>
          <div className="h-80 w-full bg-slate-800/50 rounded"></div>
        </div>
        <div className="h-[450px] bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 space-y-6">
          <div className="h-6 w-32 bg-slate-800 rounded"></div>
          <div className="h-24 bg-slate-800/50 rounded"></div>
          <div className="h-24 bg-slate-800/50 rounded"></div>
        </div>
      </div>
    </div>
  );

  if (loading && !data) {
    return (
      <div className="space-y-6 text-slate-100">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white font-display flex items-center gap-2">
              <Cpu className="text-brand-500 animate-spin" size={24} /> Volume Profile Terminal
            </h2>
            <p className="text-sm text-slate-500 font-medium">Running proportional volume allocation algorithm...</p>
          </div>
        </div>
        {renderSkeletons()}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white font-display">Volume Profile Analysis</h2>
            <p className="text-sm text-slate-500 font-medium">Error loading details</p>
          </div>
          <div className="flex items-center gap-3">
            <GlobalSymbolSearch />
          </div>
        </div>
        <ErrorCard message={error || 'No analysis data found.'} onRetry={handleRefresh} title="Volume Profile Engine Error" />
      </div>
    );
  }

  // Visual highlights and styles based on action and shape
  const getActionColor = (action: string) => {
    switch (action) {
      case 'BUY': return 'text-emerald-400 border-emerald-500/20 bg-emerald-950/40';
      case 'SELL': return 'text-red-400 border-red-500/20 bg-red-950/40';
      default: return 'text-slate-400 border-slate-800 bg-slate-800/50';
    }
  };

  const getShapeColor = (shape: string) => {
    switch (shape) {
      case 'P Shape': return 'text-emerald-400 bg-emerald-950/40 border border-emerald-500/20';
      case 'B Shape': return 'text-red-400 bg-red-950/40 border border-red-500/20';
      case 'Double Distribution': return 'text-indigo-400 bg-indigo-950/40 border border-indigo-500/20';
      case 'Trend Day': return 'text-cyan-400 bg-cyan-950/40 border border-cyan-500/20';
      default: return 'text-slate-300 bg-slate-800/80 border border-slate-700/50';
    }
  };

  const formattedPrice = (val: number) => `₹${val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  return (
    <div className="space-y-6 text-slate-100 font-sans selection:bg-brand-500/30">
      
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold tracking-tight text-white font-display">Volume Profile Analysis</h2>
            <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20">INSTITUTIONAL</span>
          </div>
          <p className="text-sm text-slate-400 font-medium mt-0.5">
            {data.company_name} ({data.symbol}) • <span className="text-slate-500">{data.sector}</span>
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {/* Lookback selection pills */}
          <div className="flex items-center bg-slate-950/80 border border-slate-800 rounded-lg p-1">
            {[30, 60, 90, 180].map((days) => (
              <button
                key={days}
                onClick={() => setLookback(days)}
                className={`px-3 py-1 text-xs font-mono font-bold rounded-md transition-all ${
                  lookback === days 
                    ? 'bg-brand-600 text-white shadow' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
                }`}
              >
                {days}D
              </button>
            ))}
          </div>

          <GlobalSymbolSearch />

          <button
            onClick={handleRefresh}
            className="p-2 rounded-lg bg-slate-950/80 border border-slate-800 hover:bg-slate-900 text-slate-400 hover:text-white transition-colors"
            title="Recalculate Volume Profile"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin text-brand-400' : ''} />
          </button>
        </div>
      </div>

      {/* TOP SUMMARY STATS ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Spot Price Card */}
        <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md hover:border-slate-700/60 transition-all flex flex-col justify-between">
          <div className="flex justify-between items-center text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            <span>Market Price</span>
            <Activity size={12} className="text-brand-500 animate-pulse" />
          </div>
          <div className="my-2">
            <div className="text-2xl font-bold font-mono text-slate-100">{formattedPrice(data.price)}</div>
          </div>
          <div className="text-[10px] text-slate-400 font-semibold flex items-center gap-1">
            <span>POC Deviation:</span>
            <span className={`font-bold font-mono ${data.price >= data.poc ? 'text-emerald-400' : 'text-red-400'}`}>
              {(((data.price - data.poc) / data.poc) * 100).toFixed(2)}%
            </span>
          </div>
        </div>

        {/* POC Price Card */}
        <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md hover:border-slate-700/60 transition-all flex flex-col justify-between">
          <div className="flex justify-between items-center text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            <span>Point of Control (POC)</span>
            <span className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
          </div>
          <div className="my-2">
            <div className="text-2xl font-bold font-mono text-yellow-400">{formattedPrice(data.poc)}</div>
          </div>
          <div className="text-[10px] text-slate-400 font-semibold">
            Highest traded price by distributed volume.
          </div>
        </div>

        {/* Value Area Card */}
        <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md hover:border-slate-700/60 transition-all flex flex-col justify-between">
          <div className="flex justify-between items-center text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            <span>70% Value Area (VA)</span>
            <Scale size={12} className="text-indigo-400" />
          </div>
          <div className="my-2">
            <div className="text-sm font-bold font-mono text-indigo-300">
              VAH: <span className="text-slate-100 font-extrabold">{formattedPrice(data.vah)}</span>
            </div>
            <div className="text-sm font-bold font-mono text-indigo-300 mt-0.5">
              VAL: <span className="text-slate-100 font-extrabold">{formattedPrice(data.val)}</span>
            </div>
          </div>
          <div className="text-[10px] text-slate-450 font-semibold flex justify-between">
            <span>Width: {(((data.vah - data.val) / data.val) * 100).toFixed(1)}%</span>
            <span className="text-slate-550 font-mono">Acceptance zone</span>
          </div>
        </div>

        {/* Shape / Structure Card */}
        <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md hover:border-slate-700/60 transition-all flex flex-col justify-between">
          <div className="flex justify-between items-center text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            <span>Profile Structure</span>
            <Percent size={12} className="text-cyan-400" />
          </div>
          <div className="my-2 flex items-center justify-between">
            <span className={`text-sm font-bold px-2 py-0.5 rounded font-mono ${getShapeColor(data.shape)}`}>
              {data.shape}
            </span>
          </div>
          <div className="text-[10px] text-slate-400 font-semibold">
            Bias: <span className="text-slate-200 font-bold">{data.institutional_bias}</span>
          </div>
        </div>
      </div>

      {/* CORE ANALYSIS: CHARTS & AI PANEL */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT COLUMN: DUAL-ALIGNED CHARTS */}
        <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 backdrop-blur-md flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-display font-semibold text-sm text-slate-200">Volume Profile Histogram & POC Overlays</h3>
              <p className="text-xs text-slate-500 font-medium">Daily Close Price vs Horizontal Volume Distribution</p>
            </div>
            <div className="flex items-center gap-3 text-[10px] font-mono font-bold">
              <span className="flex items-center gap-1 text-yellow-400">
                <span className="w-2 h-0.5 bg-yellow-400 inline-block" /> POC ({formattedPrice(data.poc)})
              </span>
              <span className="flex items-center gap-1 text-emerald-400">
                <span className="w-2 h-0.5 border-t border-dashed border-emerald-400 inline-block" /> VAH ({formattedPrice(data.vah)})
              </span>
              <span className="flex items-center gap-1 text-red-400">
                <span className="w-2 h-0.5 border-t border-dashed border-red-400 inline-block" /> VAL ({formattedPrice(data.val)})
              </span>
            </div>
          </div>

          {/* Synchronized Side-by-side Grid */}
          <div className="grid grid-cols-12 h-[340px] gap-2 select-none">
            {/* Price line chart (Takes 9/12 cols) */}
            <div className="col-span-9 h-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={data.price_history}
                  margin={{ top: 10, right: 10, left: 10, bottom: 10 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.5} />
                  <XAxis 
                    dataKey="date" 
                    stroke="#475569" 
                    tick={{ fill: '#64748b', fontSize: 9, fontFamily: 'monospace' }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis 
                    domain={chartConfigs.yDomain} 
                    stroke="#475569"
                    tick={{ fill: '#64748b', fontSize: 9, fontFamily: 'monospace' }}
                    orientation="left"
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(val) => `₹${Math.round(val)}`}
                  />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#090d16', border: '1px solid #1e293b', borderRadius: '8px' }}
                    labelStyle={{ color: '#94a3b8', fontFamily: 'monospace', fontSize: 10 }}
                    itemStyle={{ color: '#f8fafc', fontSize: 11 }}
                    formatter={(val: any) => [formattedPrice(val), 'Close']}
                  />
                  {/* Reference Lines representing VAH, VAL, POC */}
                  <ReferenceLine y={data.poc} stroke="#eab308" strokeWidth={1.5} strokeDasharray="3 3" label={{ value: 'POC', fill: '#eab308', fontSize: 9, position: 'right' }} />
                  <ReferenceLine y={data.vah} stroke="#10b981" strokeWidth={1} strokeDasharray="4 4" label={{ value: 'VAH', fill: '#10b981', fontSize: 9, position: 'right' }} />
                  <ReferenceLine y={data.val} stroke="#ef4444" strokeWidth={1} strokeDasharray="4 4" label={{ value: 'VAL', fill: '#ef4444', fontSize: 9, position: 'right' }} />

                  {/* HVN markers */}
                  {data.hvn.map((hvn_price, index) => (
                    <ReferenceLine key={`hvn-${index}`} y={hvn_price} stroke="#6366f1" strokeWidth={0.5} strokeDasharray="2 4" label={{ value: `HVN ${index+1}`, fill: '#818cf8', fontSize: 8, position: 'insideLeft' }} />
                  ))}

                  {/* LVN markers */}
                  {data.lvn.map((lvn_price, index) => (
                    <ReferenceLine key={`lvn-${index}`} y={lvn_price} stroke="#f43f5e" strokeWidth={0.5} strokeDasharray="2 4" label={{ value: `LVN ${index+1}`, fill: '#fda4af', fontSize: 8, position: 'insideLeft' }} />
                  ))}

                  <Line 
                    type="monotone" 
                    dataKey="close" 
                    stroke="#38bdf8" 
                    strokeWidth={2} 
                    dot={false}
                    activeDot={{ r: 4, stroke: '#38bdf8', strokeWidth: 1 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Horizontal Bar Chart (Takes 3/12 cols) */}
            <div className="col-span-3 h-full border-l border-slate-800/80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={chartConfigs.histogramWithMids}
                  margin={{ top: 10, right: 5, left: 5, bottom: 10 }}
                >
                  <XAxis type="number" hide />
                  {/* Share same scale domain */}
                  <YAxis 
                    type="number" 
                    domain={chartConfigs.yDomain} 
                    hide 
                    dataKey="price_mid" 
                  />
                  <Bar dataKey="volume" radius={[0, 2, 2, 0]}>
                    {
                      chartConfigs.histogramWithMids.map((bin, index) => {
                        // Color bins: POC gets bright yellow, Value Area (between VAL & VAH) gets Indigo, rest gets dark slate.
                        const isPOCBin = bin.price_min <= data.poc && bin.price_max >= data.poc;
                        const insideValueArea = bin.price_min >= data.val && bin.price_max <= data.vah;
                        
                        let fill = '#334155'; // outside VA default
                        if (isPOCBin) fill = '#eab308'; // POC
                        else if (insideValueArea) fill = '#4f46e5'; // Inside value area
                        
                        return <Cell key={`cell-${index}`} fill={fill} />;
                      })
                    }
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Sector Strength Score and Ranks panel footer */}
          <div className="mt-4 pt-3 border-t border-slate-800/85 grid grid-cols-3 gap-2 text-center text-xs">
            <div>
              <span className="text-[10px] text-slate-550 block font-bold uppercase tracking-wider">Sector Score</span>
              <span className="font-extrabold text-sm text-slate-200 mt-0.5 inline-block">{data.sector_integration.sector_score}/100</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-550 block font-bold uppercase tracking-wider">Sector Rank</span>
              <span className="font-extrabold text-sm text-slate-200 mt-0.5 inline-block">#{data.sector_integration.sector_rank}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-550 block font-bold uppercase tracking-wider">Relative Strength</span>
              <span className={`font-extrabold text-sm mt-0.5 inline-block ${data.sector_integration.relative_strength_rank >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {data.sector_integration.relative_strength_rank >= 0 ? '+' : ''}{data.sector_integration.relative_strength_rank} RS
              </span>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: AI VERDICT, RISK DETAILS & MULTI TIMEFRAME */}
        <div className="space-y-6">
          
          {/* AI SCORING & FINAL RECOMMENDATION */}
          <div className="p-5 bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800/90 rounded-xl backdrop-blur-md relative overflow-hidden">
            <div className="absolute top-0 right-0 p-3 text-[10px] font-bold font-mono text-slate-500">AI AGENT</div>
            
            <h3 className="font-display font-semibold text-xs text-slate-400 uppercase tracking-widest mb-3.5">
              QuantAI Market Verdict
            </h3>

            {/* Recommendation badge & Verdict */}
            <div className="flex items-center gap-3 mb-4">
              <span className={`text-xl font-black px-4 py-1.5 rounded-lg border tracking-wide font-display shadow-md ${getActionColor(data.action)}`}>
                {data.verdict}
              </span>
              <div className="flex-1">
                <div className="text-[10px] font-bold text-slate-500 uppercase">Confidence Rating</div>
                <div className="flex items-center gap-2 mt-0.5">
                  <div className="flex-1 bg-slate-800/80 h-2 rounded-full overflow-hidden border border-slate-700/20">
                    <div 
                      className={`h-full rounded-full transition-all duration-700 bg-brand-500`}
                      style={{ width: `${data.confidence}%` }}
                    />
                  </div>
                  <span className="text-xs font-black font-mono text-brand-400 shrink-0">{data.confidence}%</span>
                </div>
              </div>
            </div>

            {/* Top 5 factors */}
            <div className="space-y-2.5">
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Supporting Factors</div>
              {data.factors.map((factor, index) => {
                const isBullish = factor.toLowerCase().includes('bullish') || factor.toLowerCase().includes('above') || factor.toLowerCase().includes('support') || factor.toLowerCase().includes('buyers');
                const isBearish = factor.toLowerCase().includes('bearish') || factor.toLowerCase().includes('below') || factor.toLowerCase().includes('resistance') || factor.toLowerCase().includes('sellers');
                
                return (
                  <div key={index} className="flex gap-2 items-start text-xs font-medium text-slate-200">
                    {isBullish ? (
                      <ArrowUpRight size={14} className="text-emerald-400 shrink-0 mt-0.5" />
                    ) : isBearish ? (
                      <ArrowDownRight size={14} className="text-red-400 shrink-0 mt-0.5" />
                    ) : (
                      <ChevronRight size={14} className="text-slate-500 shrink-0 mt-0.5" />
                    )}
                    <span className="leading-snug">{factor}</span>
                  </div>
                );
              })}
            </div>

            {/* AI Summary Interpretation paragraph */}
            <div className="mt-4 pt-3.5 border-t border-slate-800/50 text-xs text-slate-400 leading-relaxed font-sans font-medium italic">
              " {data.summary} "
            </div>
          </div>

          {/* RISK MANAGEMENT PARAMETERS */}
          <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md">
            <h3 className="font-display font-semibold text-xs text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-1.5">
              <Target size={14} className="text-brand-500" /> Risk Management
            </h3>

            <div className="space-y-3 font-mono">
              <div className="flex justify-between items-center text-xs py-1 border-b border-slate-800/50">
                <span className="text-slate-500 font-bold">Entry Zone</span>
                <span className="text-slate-100 font-extrabold">{data.risk_management.entry_zone}</span>
              </div>
              <div className="flex justify-between items-center text-xs py-1 border-b border-slate-800/50">
                <span className="text-slate-500 font-bold">Stop Loss</span>
                <span className="text-red-400 font-extrabold">{formattedPrice(data.risk_management.stop_loss)}</span>
              </div>
              <div className="flex justify-between items-center text-xs py-1 border-b border-slate-800/50">
                <span className="text-slate-500 font-bold">Target 1</span>
                <span className="text-emerald-400 font-extrabold">{formattedPrice(data.risk_management.target_1)}</span>
              </div>
              <div className="flex justify-between items-center text-xs py-1 border-b border-slate-800/50">
                <span className="text-slate-500 font-bold">Target 2</span>
                <span className="text-emerald-400 font-extrabold">{formattedPrice(data.risk_management.target_2)}</span>
              </div>
              <div className="flex justify-between items-center text-xs py-1">
                <span className="text-slate-500 font-bold">Risk Reward Ratio</span>
                <span className="text-brand-400 font-black px-2 py-0.5 rounded bg-brand-500/10 border border-brand-500/20">
                  1 : {data.risk_management.risk_reward_ratio}
                </span>
              </div>
            </div>
          </div>

        </div>

      </div>

      {/* MULTI-TIMEFRAME ANALYSIS & FLOW PANEL BOTTOM ROW */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* MULTI TIMEFRAME ANALYSIS MATRIX */}
        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md">
          <h3 className="font-display font-semibold text-xs text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-1.5">
            <Activity size={14} className="text-brand-500" /> Multi-Timeframe Matrix
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500 font-bold">
                  <th className="py-2.5">Timeframe</th>
                  <th className="py-2.5">Profile Structure</th>
                  <th className="py-2.5 text-right">Verdict</th>
                </tr>
              </thead>
              <tbody className="font-semibold text-slate-200">
                <tr className="border-b border-slate-800/40">
                  <td className="py-3 font-bold">Daily</td>
                  <td className="py-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${getShapeColor(data.timeframes.daily.shape)}`}>
                      {data.timeframes.daily.shape}
                    </span>
                  </td>
                  <td className="py-3 text-right">
                    <span className={`font-mono font-bold text-xs ${
                      data.timeframes.daily.verdict === 'Buy' ? 'text-emerald-400' :
                      data.timeframes.daily.verdict === 'Sell' ? 'text-red-400' : 'text-slate-400'
                    }`}>
                      {data.timeframes.daily.verdict}
                    </span>
                  </td>
                </tr>
                <tr className="border-b border-slate-800/40">
                  <td className="py-3 font-bold">Weekly</td>
                  <td className="py-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${getShapeColor(data.timeframes.weekly.shape)}`}>
                      {data.timeframes.weekly.shape}
                    </span>
                  </td>
                  <td className="py-3 text-right">
                    <span className={`font-mono font-bold text-xs ${
                      data.timeframes.weekly.verdict === 'Buy' ? 'text-emerald-400' :
                      data.timeframes.weekly.verdict === 'Sell' ? 'text-red-400' : 'text-slate-400'
                    }`}>
                      {data.timeframes.weekly.verdict}
                    </span>
                  </td>
                </tr>
                <tr>
                  <td className="py-3 font-bold">Monthly</td>
                  <td className="py-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${getShapeColor(data.timeframes.monthly.shape)}`}>
                      {data.timeframes.monthly.shape}
                    </span>
                  </td>
                  <td className="py-3 text-right">
                    <span className={`font-mono font-bold text-xs ${
                      data.timeframes.monthly.verdict === 'Buy' ? 'text-emerald-400' :
                      data.timeframes.monthly.verdict === 'Sell' ? 'text-red-400' : 'text-slate-400'
                    }`}>
                      {data.timeframes.monthly.verdict}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* INSTITUTIONAL FLOW PANEL */}
        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md">
          <h3 className="font-display font-semibold text-xs text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-1.5">
            <Flame size={14} className="text-brand-500 animate-pulse" /> Institutional Flow triggers
          </h3>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-3">
              <div>
                <span className="text-[10px] text-slate-500 font-bold block">PRICE VS POC</span>
                <span className={`text-xs font-extrabold ${data.price >= data.poc ? 'text-emerald-400' : 'text-red-400'} mt-0.5 inline-block`}>
                  {data.price >= data.poc ? 'Trading ABOVE POC' : 'Trading BELOW POC'}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 font-bold block">PRICE VS VALUE AREA</span>
                <span className={`text-xs font-extrabold ${
                  data.price > data.vah ? 'text-emerald-400' : 
                  data.price < data.val ? 'text-red-400' : 'text-slate-300'
                } mt-0.5 inline-block`}>
                  {data.price > data.vah ? 'Value Acceptance High' : 
                   data.price < data.val ? 'Value Rejection Low' : 'Consolidating Inside Value Area'}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 font-bold block">HVN SUPPORT LEVELS</span>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {data.hvn.map((price, i) => (
                    <span key={i} className="text-[10px] font-mono font-bold bg-indigo-950/40 text-indigo-400 border border-indigo-500/20 px-1.5 py-0.5 rounded">
                      ₹{price}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <span className="text-[10px] text-slate-500 font-bold block">RISK BIAS INDEX</span>
                <span className={`text-xs font-extrabold ${data.risk_score <= 40 ? 'text-emerald-400' : data.risk_score >= 60 ? 'text-red-400' : 'text-slate-300'} mt-0.5 inline-block`}>
                  {data.risk_score} / 100 ({data.risk_score <= 40 ? 'Low Risk' : data.risk_score >= 60 ? 'High Risk' : 'Medium Risk'})
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 font-bold block">VALUATION BIAS</span>
                <span className="text-xs font-extrabold text-slate-300 mt-0.5 inline-block">
                  {data.institutional_bias}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-550 font-bold block">LVN BREAKOUT LEVELS</span>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {data.lvn.map((price, i) => (
                    <span key={i} className="text-[10px] font-mono font-bold bg-rose-950/40 text-rose-450 border border-rose-500/20 px-1.5 py-0.5 rounded">
                      ₹{price}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
};

export default VolumeProfilePage;
