import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../services/api';
import { calculatePriceChange } from '../utils/marketPrice';
import {
  Bot, Play, Loader2, CheckCircle2, XCircle, Clock, TrendingUp,
  TrendingDown, ArrowUpCircle, ArrowDownCircle, Activity, BarChart3,
  Zap, RefreshCw, AlertTriangle, History, Filter, Search, SlidersHorizontal,
  ChevronDown, ChevronUp
} from 'lucide-react';

// ── Types ────────────────────────────────────────────────────────────────────

interface BotSignal {
  symbol: string;
  sector?: string;
  signal_type: 'BUY' | 'SELL' | 'HOLD' | 'WATCH';
  correlation: number;
  correlation_category: string;
  price_change_pct: number;
  current_price: number;
  volatility_level: string;
  volatility_atr: number;
  pcr_value: number | null;
  pcr_source: string;
  conviction: string;
  score?: number;
  ai_tag?: string;
  ai_details?: { confidence: number; risk_level: string; time_horizon: string; reasoning: string };
}

interface MarketTrend {
  trend: string;
  ema_50: number;
  ema_200: number;
  momentum: number;
  last_close: number;
}

interface BotSummary {
  universe?: string;
  total_universe_count?: number;
  valid_stocks_count?: number;
  total_stocks_analyzed: number;
  total_correlations: number;
  high_correlation_count: number;
  total_signals: number;
  buy_count: number;
  sell_count: number;
  execution_time_seconds: number;
  data_sources: { historical: string; live_quotes: number; pcr: string };
}

interface MarketBreadth {
  advancing: number;
  declining: number;
  above_20_ema: number;
  above_50_ema: number;
  above_200_ema: number;
  rsi_greater_60: number;
  rsi_less_40: number;
  new_highs: number;
  new_lows: number;
  breakouts: number;
  breakdowns: number;
  relative_strength_leaders: string[];
}

interface SectorResult {
  sector: string;
  stock_count: number;
  bullish_pct: number;
  bearish_pct: number;
  avg_rsi: number;
  avg_adx: number;
  avg_relative_strength: number;
  trend_score: number;
}

interface BotResult {
  run_id: string;
  market_trend: MarketTrend | null;
  buy_signals: BotSignal[];
  sell_signals: BotSignal[];
  hold_signals: BotSignal[];
  watch_signals: BotSignal[];
  summary: BotSummary;
  completed_at: string | null;
  market_breadth?: MarketBreadth;
  sector_results?: Record<string, SectorResult>;
}

type BotStatus = 'IDLE' | 'LOADING_UNIVERSE' | 'COLLECTING_DATA' | 'VALIDATING_DATA' |
  'ANALYZING_BREADTH' | 'ANALYZING_SECTORS' | 'ANALYZING_CORRELATION' |
  'ANALYZING_VOLATILITY' | 'DETECTING_TREND' | 'GENERATING_SIGNALS' |
  'RANKING_SIGNALS' | 'AI_CLASSIFICATION' | 'COMPLETED' | 'ERROR';

// ── Step Config ──────────────────────────────────────────────────────────────

const STEPS: { key: BotStatus; label: string; icon: React.ReactNode }[] = [
  { key: 'LOADING_UNIVERSE', label: 'Universe', icon: <BarChart3 size={16} /> },
  { key: 'COLLECTING_DATA', label: 'Data', icon: <BarChart3 size={16} /> },
  { key: 'VALIDATING_DATA', label: 'Validate', icon: <CheckCircle2 size={16} /> },
  { key: 'ANALYZING_BREADTH', label: 'Breadth', icon: <Activity size={16} /> },
  { key: 'ANALYZING_SECTORS', label: 'Sectors', icon: <BarChart3 size={16} /> },
  { key: 'ANALYZING_CORRELATION', label: 'Correlation', icon: <Activity size={16} /> },
  { key: 'ANALYZING_VOLATILITY', label: 'Volatility', icon: <Zap size={16} /> },
  { key: 'DETECTING_TREND', label: 'Trend', icon: <TrendingUp size={16} /> },
  { key: 'GENERATING_SIGNALS', label: 'Signals', icon: <Bot size={16} /> },
  { key: 'RANKING_SIGNALS', label: 'Ranking', icon: <Zap size={16} /> },
  { key: 'AI_CLASSIFICATION', label: 'AI Class.', icon: <Zap size={16} /> },
  { key: 'COMPLETED', label: 'Done', icon: <CheckCircle2 size={16} /> },
];

const STEP_ORDER = STEPS.map(s => s.key);

const UNIVERSE_OPTIONS = [
  { value: 'NIFTY 50', label: 'NIFTY 50', count: '50 stocks' },
  { value: 'NIFTY NEXT 50', label: 'NIFTY Next 50', count: '50 stocks' },
  { value: 'NIFTY 100', label: 'NIFTY 100', count: '100 stocks' },
  { value: 'NIFTY 200', label: 'NIFTY 200', count: '200 stocks' },
  { value: 'NIFTY 500', label: 'NIFTY 500', count: '500 stocks' },
];

// ── Helpers ──────────────────────────────────────────────────────────────────

function getStepIndex(status: BotStatus): number {
  return STEP_ORDER.indexOf(status);
}

function ConvictionBadge({ conviction }: { conviction: string }) {
  const c = conviction ? conviction.toUpperCase() : '';
  const styles: Record<string, string> = {
    'VERY STRONG': 'bg-fuchsia-500/20 text-fuchsia-400 ring-fuchsia-500/30',
    STRONG: 'bg-emerald-500/20 text-emerald-400 ring-emerald-500/30',
    MODERATE: 'bg-amber-500/20 text-amber-400 ring-amber-500/30',
    WEAK: 'bg-slate-500/20 text-slate-400 ring-slate-500/30',
  };
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ring-1 ${styles[c] || styles.WEAK}`}>
      {conviction}
    </span>
  );
}

function AiTagBadge({ tag }: { tag: string }) {
  const styles: Record<string, string> = {
    'Strong Buy': 'bg-emerald-500/25 text-emerald-300 ring-emerald-500/40',
    'Buy': 'bg-green-500/20 text-green-400 ring-green-500/30',
    'Accumulate': 'bg-teal-500/20 text-teal-400 ring-teal-500/30',
    'Watchlist': 'bg-slate-500/20 text-slate-400 ring-slate-500/30',
    'Hold': 'bg-amber-500/15 text-amber-400 ring-amber-500/25',
    'Reduce': 'bg-orange-500/20 text-orange-400 ring-orange-500/30',
    'Sell': 'bg-red-500/20 text-red-400 ring-red-500/30',
    'Strong Sell': 'bg-red-600/30 text-red-300 ring-red-500/50',
  };
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ring-1 ${styles[tag] || styles['Watchlist']}`}>
      {tag}
    </span>
  );
}

function VolatilityBadge({ level }: { level: string }) {
  const l = level ? level.toUpperCase() : '';
  const styles: Record<string, string> = {
    HIGH: 'bg-red-500/15 text-red-400',
    MEDIUM: 'bg-amber-500/15 text-amber-400',
    LOW: 'bg-emerald-500/15 text-emerald-400',
  };
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded ${styles[l] || 'bg-slate-700 text-slate-400'}`}>
      {level}
    </span>
  );
}

function CorrelationBadge({ category }: { category: string }) {
  const styles: Record<string, string> = {
    HIGH: 'text-sky-400',
    MODERATE: 'text-amber-400',
    LOW: 'text-slate-400',
  };
  return <span className={`text-xs font-medium ${styles[category] || 'text-slate-500'}`}>{category}</span>;
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 75 ? 'from-emerald-500 to-green-400' : score >= 55 ? 'from-amber-500 to-yellow-400' : 'from-red-500 to-rose-400';
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-12 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full bg-gradient-to-r ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-mono text-slate-400">{score.toFixed(0)}</span>
    </div>
  );
}

function MarketBreadthPanel({ breadth, total }: { breadth: MarketBreadth; total: number }) {
  const advPct = total > 0 ? ((breadth.advancing / total) * 100).toFixed(0) : '0';
  const decPct = total > 0 ? ((breadth.declining / total) * 100).toFixed(0) : '0';
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-5">
      <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
        <Activity size={16} className="text-violet-400" />
        Market Breadth
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        {[
          { label: 'Advancing', value: breadth.advancing, pct: advPct, color: 'emerald' },
          { label: 'Declining', value: breadth.declining, pct: decPct, color: 'red' },
          { label: 'New Highs', value: breadth.new_highs, color: 'sky' },
          { label: 'New Lows', value: breadth.new_lows, color: 'rose' },
        ].map(m => (
          <div key={m.label} className={`bg-${m.color}-500/5 border border-${m.color}-500/15 rounded-xl p-3`}>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{m.label}</p>
            <p className={`text-2xl font-bold text-${m.color}-400 mt-1`}>{m.value}</p>
            {m.pct && <p className="text-[10px] text-slate-600">{m.pct}% of universe</p>}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-3 text-center">
        {[
          { label: '> 20 EMA', value: breadth.above_20_ema },
          { label: '> 50 EMA', value: breadth.above_50_ema },
          { label: '> 200 EMA', value: breadth.above_200_ema },
          { label: 'RSI > 60', value: breadth.rsi_greater_60 },
          { label: 'RSI < 40', value: breadth.rsi_less_40 },
          { label: 'Breakouts', value: breadth.breakouts },
        ].map(m => (
          <div key={m.label} className="bg-slate-900/50 rounded-lg p-2">
            <p className="text-[9px] font-semibold uppercase tracking-wider text-slate-600">{m.label}</p>
            <p className="text-sm font-bold text-slate-300 mt-0.5">{m.value}</p>
          </div>
        ))}
      </div>
      {breadth.relative_strength_leaders?.length > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-700/40">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-2">RS Leaders (1M)</p>
          <div className="flex flex-wrap gap-1.5">
            {breadth.relative_strength_leaders.map(sym => (
              <span key={sym} className="text-[10px] font-mono bg-violet-500/10 text-violet-400 px-2 py-0.5 rounded-full border border-violet-500/20">{sym}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SectorStrengthPanel({ sectors }: { sectors: Record<string, SectorResult> }) {
  const sorted = Object.values(sectors).sort((a, b) => b.trend_score - a.trend_score);
  if (sorted.length === 0) return null;
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-5">
      <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
        <BarChart3 size={16} className="text-fuchsia-400" />
        Sector Strength
      </h3>
      <div className="space-y-2">
        {sorted.slice(0, 8).map(sec => (
          <div key={sec.sector} className="flex items-center gap-3">
            <span className="text-xs text-slate-400 w-32 truncate flex-shrink-0">{sec.sector}</span>
            <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${sec.trend_score > 0 ? 'bg-emerald-500' : 'bg-red-500'}`}
                style={{ width: `${Math.min(100, Math.abs(sec.trend_score))}%`, marginLeft: sec.trend_score < 0 ? `${100 - Math.min(100, Math.abs(sec.trend_score))}%` : '0' }}
              />
            </div>
            <span className={`text-xs font-mono font-semibold w-12 text-right ${sec.trend_score > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {sec.trend_score > 0 ? '+' : ''}{sec.trend_score.toFixed(0)}%
            </span>
            <span className="text-[10px] text-slate-600 w-8">{sec.stock_count}s</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Signal Table ─────────────────────────────────────────────────────────────

function SignalTable({ signals }: { signals: BotSignal[] }) {
  const [sortBy, setSortBy] = useState<string>('score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [expanded, setExpanded] = useState<string | null>(null);

  const handleSort = (col: string) => {
    if (sortBy === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(col);
      setSortDir(col === 'score' || col === 'price_change_pct' ? 'desc' : 'asc');
    }
  };

  const sorted = [...signals].sort((a, b) => {
    const dir = sortDir === 'asc' ? 1 : -1;
    
    if (sortBy === 'conviction') {
      const o: Record<string, number> = { 'VERY STRONG': 0, 'STRONG': 1, 'MODERATE': 2, 'WEAK': 3 };
      const av = (a.conviction || '').toUpperCase();
      const bv = (b.conviction || '').toUpperCase();
      return ((o[av] ?? 4) - (o[bv] ?? 4)) * dir;
    }
    
    if (sortBy === 'signal_type') {
      const o: Record<string, number> = { 'BUY': 0, 'SELL': 1, 'WATCH': 2, 'HOLD': 3 };
      return ((o[a.signal_type] ?? 4) - (o[b.signal_type] ?? 4)) * dir;
    }

    const av = (a as any)[sortBy] ?? 0;
    const bv = (b as any)[sortBy] ?? 0;
    return (av > bv ? 1 : -1) * dir;
  });

  if (!signals.length) {
    return (
      <div className="text-center py-12 text-slate-500 bg-slate-900/20 rounded-2xl border border-slate-800/40">
        <Bot size={40} className="mx-auto mb-3 opacity-30 text-violet-400" />
        <p className="text-sm font-medium">No signals matching the selected filters.</p>
      </div>
    );
  }

  const thClass = "px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 transition-colors select-none";

  return (
    <div className="overflow-x-auto animate-in fade-in duration-300">
      <table className="w-full text-sm" id="bot-signals-unified-table">
        <thead>
          <tr className="border-b border-slate-700/50 bg-slate-800/20">
            <th className={thClass} onClick={() => handleSort('symbol')}>Stock</th>
            <th className={thClass} onClick={() => handleSort('signal_type')}>Signal</th>
            <th className={thClass} onClick={() => handleSort('score')}>Score</th>
            <th className={thClass}>AI Tag</th>
            <th className={thClass} onClick={() => handleSort('price_change_pct')}>% Change</th>
            <th className={thClass} onClick={() => handleSort('current_price')}>Price</th>
            <th className={thClass} onClick={() => handleSort('volatility_level')}>Volatility</th>
            <th className={thClass}>PCR</th>
            <th className={thClass} onClick={() => handleSort('conviction')}>Conviction</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/50 bg-slate-950/10">
          {sorted.map((s) => {
            const isExpanded = expanded === s.symbol;
            
            const signalStyles: Record<string, string> = {
              BUY: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
              SELL: 'bg-rose-500/10 text-rose-400 border border-rose-500/20',
              WATCH: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
              HOLD: 'bg-slate-500/10 text-slate-400 border border-slate-500/20',
            };

            return (
              <React.Fragment key={s.symbol}>
                <tr
                  className={`hover:bg-slate-800/30 transition-colors cursor-pointer ${isExpanded ? 'bg-slate-800/20' : ''}`}
                  onClick={() => setExpanded(isExpanded ? null : s.symbol)}
                >
                  <td className="px-4 py-3 font-bold text-slate-200">
                    <div className="flex flex-col">
                      <span>{s.symbol}</span>
                      {s.sector && <span className="text-[10px] font-medium text-slate-500 mt-0.5">{s.sector}</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-[10px] font-black uppercase px-2.5 py-1 rounded-lg ${signalStyles[s.signal_type] || signalStyles.HOLD}`}>
                      {s.signal_type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {s.score != null ? <ScoreBar score={s.score} /> : <span className="text-slate-600">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    {s.ai_tag ? <AiTagBadge tag={s.ai_tag} /> : <span className="text-slate-600">—</span>}
                  </td>
                  <td className="px-4 py-3 font-mono font-semibold">
                    {(() => {
                      const details = calculatePriceChange(s.current_price, undefined, s.price_change_pct);
                      const isUp = details.direction === 'up';
                      const isDown = details.direction === 'down';
                      return (
                        <span className={isUp ? 'text-green-500' : isDown ? 'text-rose-500' : 'text-slate-400'}>
                          {isUp ? '▲ +' : isDown ? '▼ ' : '▬ '}{Math.abs(details.changePercent).toFixed(2)}%
                        </span>
                      );
                    })()}
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-300">
                    ₹{s.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className="px-4 py-3"><VolatilityBadge level={s.volatility_level} /></td>
                  <td className="px-4 py-3">
                    {s.pcr_value != null ? (
                      <span className="font-mono text-slate-300">{s.pcr_value.toFixed(2)}</span>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3"><ConvictionBadge conviction={s.conviction} /></td>
                </tr>
                {isExpanded && s.ai_details && (
                  <tr className="bg-slate-900/40">
                    <td colSpan={9} className="px-5 py-4 border-t border-b border-slate-800/60">
                      <div className="flex flex-wrap gap-6 text-xs text-slate-400 mb-3 bg-slate-950/20 p-3 rounded-xl border border-slate-800/40">
                        <div>
                          <span className="font-semibold text-slate-500 uppercase tracking-wider text-[10px] block mb-0.5">Confidence</span>
                          <span className="text-slate-200 font-bold text-sm">{s.ai_details.confidence}%</span>
                        </div>
                        <div>
                          <span className="font-semibold text-slate-500 uppercase tracking-wider text-[10px] block mb-0.5">Risk Rating</span>
                          <span className={`font-bold text-sm ${s.ai_details.risk_level === 'Low' ? 'text-emerald-400' : s.ai_details.risk_level === 'Medium' ? 'text-amber-400' : 'text-rose-400'}`}>
                            {s.ai_details.risk_level}
                          </span>
                        </div>
                        <div>
                          <span className="font-semibold text-slate-500 uppercase tracking-wider text-[10px] block mb-0.5">Time Horizon</span>
                          <span className="text-slate-200 font-bold text-sm">{s.ai_details.time_horizon}</span>
                        </div>
                        {s.correlation != null && (
                          <div>
                            <span className="font-semibold text-slate-500 uppercase tracking-wider text-[10px] block mb-0.5">Index Correlation</span>
                            <span className="text-slate-200 font-mono font-bold text-sm">{(s.correlation * 100).toFixed(1)}% ({s.correlation_category})</span>
                          </div>
                        )}
                      </div>
                      <div className="text-xs text-slate-300 leading-relaxed max-w-4xl">
                        <span className="font-bold text-slate-400 block mb-1 text-[10px] uppercase tracking-wider">Scoring Reasoning & Confirmations</span>
                        {s.ai_details.reasoning}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────

const BotTab: React.FC = () => {
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<BotStatus>('IDLE');
  const [progress, setProgress] = useState(0);
  const [stepLabel, setStepLabel] = useState('');
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BotResult | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [scheduler, setScheduler] = useState<any>(null);
  const [selectedUniverse, setSelectedUniverse] = useState('NIFTY 500');
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  // Unified signals and filters state
  const [allSignals, setAllSignals] = useState<BotSignal[]>([]);
  const [signalFilter, setSignalFilter] = useState<'ALL' | 'BUY' | 'SELL' | 'WATCH' | 'HOLD'>('ALL');
  const [trendFilter, setTrendFilter] = useState<'ALL' | 'BULLISH' | 'BEARISH' | 'SIDEWAYS'>('ALL');
  const [riskFilter, setRiskFilter] = useState<'ALL' | 'LOW' | 'MEDIUM' | 'HIGH'>('ALL');
  const [instStrengthFilter, setInstStrengthFilter] = useState<'ALL' | 'VERY STRONG' | 'STRONG' | 'MODERATE' | 'WEAK'>('ALL');
  const [sectorFilter, setSectorFilter] = useState<string>('ALL');
  const [confidenceFilter, setConfidenceFilter] = useState<string>('ALL');
  const [priceMin, setPriceMin] = useState<string>('');
  const [priceMax, setPriceMax] = useState<string>('');
  const [changeFilter, setChangeFilter] = useState<'ALL' | 'POSITIVE' | 'NEGATIVE'>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showFilters, setShowFilters] = useState<boolean>(true);

  useEffect(() => {
    if (result) {
      const combined: BotSignal[] = [
        ...(result.buy_signals || []).map(s => ({ ...s, signal_type: 'BUY' as const })),
        ...(result.sell_signals || []).map(s => ({ ...s, signal_type: 'SELL' as const })),
        ...(result.hold_signals || []).map(s => ({ ...s, signal_type: 'HOLD' as const })),
        ...(result.watch_signals || []).map(s => ({ ...s, signal_type: 'WATCH' as const })),
      ];
      setAllSignals(combined);
    } else {
      setAllSignals([]);
    }
  }, [result]);

  const filteredSignals = allSignals.filter(s => {
    // 1. Signal Type
    if (signalFilter !== 'ALL' && s.signal_type !== signalFilter) return false;
    
    // 2. Trend
    if (trendFilter !== 'ALL') {
      const isBullish = (s.score ?? 0) >= 50 && s.price_change_pct >= 0;
      const isBearish = (s.score ?? 0) >= 50 && s.price_change_pct < 0;
      const isSideways = !isBullish && !isBearish;
      if (trendFilter === 'BULLISH' && !isBullish) return false;
      if (trendFilter === 'BEARISH' && !isBearish) return false;
      if (trendFilter === 'SIDEWAYS' && !isSideways) return false;
    }
    
    // 3. Risk
    if (riskFilter !== 'ALL') {
      const r = (s.ai_details?.risk_level || 'Medium').toUpperCase();
      if (r !== riskFilter) return false;
    }
    
    // 4. Institutional Strength (Conviction)
    if (instStrengthFilter !== 'ALL') {
      const c = (s.conviction || '').toUpperCase();
      if (c !== instStrengthFilter) return false;
    }
    
    // 5. Sector
    if (sectorFilter !== 'ALL' && s.sector !== sectorFilter) return false;
    
    // 6. Confidence
    if (confidenceFilter !== 'ALL') {
      const score = s.score ?? 0;
      if (score < parseFloat(confidenceFilter)) return false;
    }
    
    // 7. Price Range
    if (priceMin && s.current_price < parseFloat(priceMin)) return false;
    if (priceMax && s.current_price > parseFloat(priceMax)) return false;
    
    // 8. Daily Change
    if (changeFilter === 'POSITIVE' && s.price_change_pct < 0) return false;
    if (changeFilter === 'NEGATIVE' && s.price_change_pct >= 0) return false;
    
    // 9. Search Query
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!s.symbol.toLowerCase().includes(q)) return false;
    }
    
    return true;
  });

  // Load initial data on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        const lastRun = await api.getLastBotRun();
        if (lastRun?.status === 'success' && lastRun.data) {
          setResult(lastRun.data);
          setRunId(lastRun.run_id);
          setStatus('COMPLETED');
          setProgress(100);
        }

        const historyData = await api.getBotHistory(5);
        if (historyData?.status === 'success') {
          setHistory(historyData.data);
        }

        const schedulerData = await api.getBotSchedulerStatus();
        if (schedulerData?.status === 'success') {
          setScheduler(schedulerData.data);
        }
      } catch (err) {
        console.error('Failed to load bot initial data:', err);
      }
    };

    fetchData();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  // Poll status when running
  const pollStatus = useCallback(async (rid: string) => {
    try {
      const resp = await api.getBotStatus(rid);
      const d = resp?.data;
      if (!d) return;

      setStatus(d.status as BotStatus);
      setProgress(d.progress_pct);
      setStepLabel(d.current_step_label);
      setElapsed(d.elapsed_seconds);

      if (d.status === 'COMPLETED') {
        if (pollRef.current) clearInterval(pollRef.current);
        // Fetch results and refresh history
        try {
          const res = await api.getBotResults(rid);
          if (res?.data) setResult(res.data);
          
          const historyData = await api.getBotHistory(5);
          if (historyData?.status === 'success') {
            setHistory(historyData.data);
          }
        } catch (e) { console.error('Failed to fetch results/history:', e); }
      } else if (d.status === 'ERROR') {
        if (pollRef.current) clearInterval(pollRef.current);
        setError(d.error_message || 'An unknown error occurred');
      }
    } catch (e) {
      console.error('Status poll failed:', e);
    }
  }, []);

  const handleStart = async () => {
    setIsStarting(true);
    setError(null);
    setResult(null);
    setStatus('IDLE');
    setProgress(0);

    try {
      const data = await api.startBot(selectedUniverse);
      if (data.run_id) {
        setRunId(data.run_id);
        setStatus('LOADING_UNIVERSE');
        // Start polling
        pollRef.current = setInterval(() => pollStatus(data.run_id), 2000);
      } else if (data.status === 'already_running' && data.run_id) {
        setRunId(data.run_id);
        pollRef.current = setInterval(() => pollStatus(data.run_id), 2000);
      }
    } catch (e: any) {
      setError(e.message || 'Failed to start bot');
      setStatus('ERROR');
    } finally {
      setIsStarting(false);
    }
  };

  const isRunning = !['IDLE', 'COMPLETED', 'ERROR'].includes(status);
  const currentStepIdx = getStepIndex(status);

  return (
    <div className="space-y-6" id="bot-tab-container">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-600 flex items-center justify-center shadow-lg shadow-violet-500/25">
              <Bot size={26} className="text-white" />
            </div>
            {isRunning && (
              <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-emerald-400 rounded-full border-2 border-slate-900 animate-pulse" />
            )}
          </div>
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
              NIFTY 500 AI Signal Engine
            </h1>
            <div className="flex items-center gap-2">
              <p className="text-sm text-slate-400">Correlation, breadth, sector &amp; AI-powered signals</p>
              {scheduler?.enabled && (
                <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-[10px] font-semibold text-emerald-400">
                  <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                  Auto-run: {scheduler.morning_run} &amp; {scheduler.close_run} IST
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          {/* Universe Selector */}
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Universe</label>
            <select
              id="bot-universe-selector"
              value={selectedUniverse}
              onChange={e => setSelectedUniverse(e.target.value)}
              disabled={isRunning || isStarting}
              className="bg-slate-800 border border-slate-600 text-slate-200 text-sm rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-violet-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {UNIVERSE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label} — {opt.count}</option>
              ))}
            </select>
          </div>
          <button
            id="start-bot-button"
            onClick={handleStart}
            disabled={isRunning || isStarting}
            className={`
              flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm self-end
              transition-all duration-300 shadow-lg
              ${isRunning || isStarting
                ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white hover:from-violet-500 hover:to-fuchsia-500 hover:shadow-violet-500/25 hover:scale-[1.02] active:scale-[0.98]'
              }
            `}
          >
            {isRunning ? <Loader2 size={18} className="animate-spin" /> :
             isStarting ? <Loader2 size={18} className="animate-spin" /> :
             <Play size={18} />}
            {isRunning ? 'Running...' : isStarting ? 'Starting...' : 'Run Analysis'}
          </button>
        </div>
      </div>

      {/* Progress Steps */}
      {(isRunning || status === 'COMPLETED' || status === 'ERROR') && (
        <div className="bg-slate-800/50 backdrop-blur rounded-2xl border border-slate-700/50 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-300">Pipeline Progress</h3>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Clock size={14} />
              <span>{elapsed.toFixed(1)}s</span>
            </div>
          </div>

          {/* Step indicators */}
          <div className="flex items-center gap-1 mb-4">
            {STEPS.map((step, i) => {
              const isDone = currentStepIdx > i || status === 'COMPLETED';
              const isCurrent = status === step.key;
              const isPending = currentStepIdx < i && status !== 'COMPLETED';

              return (
                <React.Fragment key={step.key}>
                  <div className={`
                    flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-500
                    ${isDone ? 'bg-emerald-500/15 text-emerald-400' :
                      isCurrent ? 'bg-violet-500/20 text-violet-300 ring-1 ring-violet-500/30' :
                      'bg-slate-800/50 text-slate-600'}
                  `}>
                    {isDone ? <CheckCircle2 size={14} className="text-emerald-400" /> :
                     isCurrent ? <Loader2 size={14} className="animate-spin" /> :
                     step.icon}
                    <span className="hidden sm:inline">{step.label}</span>
                  </div>
                  {i < STEPS.length - 1 && (
                    <div className={`h-px flex-1 transition-colors duration-500 ${isDone ? 'bg-emerald-500/40' : 'bg-slate-700/50'}`} />
                  )}
                </React.Fragment>
              );
            })}
          </div>

          {/* Progress bar */}
          <div className="w-full bg-slate-700/50 rounded-full h-2 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all duration-700 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-slate-500 mt-2">{stepLabel} — {progress}%</p>
        </div>
      )}

      {/* Error State */}
      {status === 'ERROR' && error && (() => {
        if (error.startsWith('BOT_ERR_SYMBOLS_UNAVAILABLE')) {
          const parts = error.split('|');
          const errorCode = parts[0] || 'BOT_ERR_SYMBOLS_UNAVAILABLE';
          const cause = parts[1] || 'No active symbols found in DB, CSV, or fallback static list.';
          const suggestion = parts[2] || 'Refresh symbol master list or check API configuration.';
          return (
            <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-6 flex flex-col gap-4 text-sm shadow-lg shadow-red-500/5">
              <div className="flex items-center gap-3 border-b border-red-500/20 pb-4">
                <XCircle size={24} className="text-red-400 flex-shrink-0" />
                <div>
                  <h3 className="font-bold text-red-400 text-lg">Symbol Source Unavailable</h3>
                  <span className="text-[10px] font-mono bg-red-500/20 text-red-300 px-2 py-0.5 rounded mt-1 inline-block border border-red-500/30">
                    Error Code: {errorCode}
                  </span>
                </div>
              </div>
              <div className="space-y-4">
                <div>
                  <h4 className="font-bold text-red-300 uppercase tracking-wider text-xs flex items-center gap-1.5">
                    <span className="w-1 h-1.5 rounded-full bg-red-400" />
                    Cause
                  </h4>
                  <p className="text-slate-300 mt-1.5 leading-relaxed">{cause}</p>
                </div>
                <div>
                  <h4 className="font-bold text-emerald-400 uppercase tracking-wider text-xs flex items-center gap-1.5">
                    <span className="w-1 h-1.5 rounded-full bg-emerald-400" />
                    Recommended Action
                  </h4>
                  <p className="text-emerald-300/90 mt-1.5 font-medium leading-relaxed">{suggestion}</p>
                </div>
              </div>
            </div>
          );
        }

        return (
          <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 flex items-start gap-3">
            <XCircle size={20} className="text-red-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold text-red-400">Bot Error</p>
              <p className="text-sm text-red-300/80 mt-1">{error}</p>
            </div>
          </div>
        );
      })()}

      {/* Results */}
      {result && status === 'COMPLETED' && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { label: 'Universe', value: result.summary.universe || selectedUniverse, icon: <BarChart3 size={16} />, color: 'violet' },
              { label: 'Stocks Analyzed', value: `${result.summary.valid_stocks_count ?? result.summary.total_stocks_analyzed}${result.summary.total_universe_count ? `/${result.summary.total_universe_count}` : ''}`, icon: <BarChart3 size={16} />, color: 'slate' },
              { label: 'High Correlation', value: result.summary.high_correlation_count, icon: <Activity size={16} />, color: 'sky' },
              { label: 'Total Signals', value: result.summary.total_signals, icon: <Zap size={16} />, color: 'fuchsia' },
              { label: 'BUY Signals', value: result.summary.buy_count, icon: <ArrowUpCircle size={16} />, color: 'emerald' },
              { label: 'SELL Signals', value: result.summary.sell_count, icon: <ArrowDownCircle size={16} />, color: 'red' },
            ].map((card) => (
              <div key={card.label} className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
                <div className={`flex items-center gap-1.5 text-${card.color}-400 mb-2`}>
                  {card.icon}
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{card.label}</span>
                </div>
                <p className="text-lg font-bold text-slate-200">{card.value}</p>
              </div>
            ))}
          </div>

          {/* Market Trend */}
          {result.market_trend && (
            <div className={`rounded-2xl border p-5 ${
              result.market_trend.trend === 'BULLISH'
                ? 'bg-emerald-500/5 border-emerald-500/20'
                : 'bg-red-500/5 border-red-500/20'
            }`}>
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  {result.market_trend.trend === 'BULLISH'
                    ? <TrendingUp size={28} className="text-emerald-400" />
                    : <TrendingDown size={28} className="text-red-400" />
                  }
                  <div>
                    <p className="text-sm font-medium text-slate-400">NIFTY 500 Market Trend</p>
                    <p className={`text-2xl font-bold ${
                      result.market_trend.trend === 'BULLISH' ? 'text-emerald-400' : 'text-red-400'
                    }`}>
                      {result.market_trend.trend}
                    </p>
                  </div>
                </div>
                
                {/* Metrics Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-4 text-left md:text-right border-t border-slate-800 md:border-t-0 pt-4 md:pt-0">
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">Advance / Decline</p>
                    <p className="text-xs font-mono font-semibold text-slate-300">
                      <span className="text-emerald-400">{result.market_trend.advances ?? 0}</span>
                      <span className="text-slate-500"> / </span>
                      <span className="text-red-400">{result.market_trend.declines ?? 0}</span>
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">Above EMA 50</p>
                    <p className="text-xs font-mono font-semibold text-sky-400">
                      {result.market_trend.pct_above_ema50 !== undefined ? `${result.market_trend.pct_above_ema50.toFixed(1)}%` : '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">Above EMA 200</p>
                    <p className="text-xs font-mono font-semibold text-amber-400">
                      {result.market_trend.pct_above_ema200 !== undefined ? `${result.market_trend.pct_above_ema200.toFixed(1)}%` : '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">5-Day Mom</p>
                    <p className={`text-xs font-mono font-semibold ${(result.market_trend.momentum_5d ?? result.market_trend.momentum ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {(result.market_trend.momentum_5d ?? result.market_trend.momentum ?? 0) >= 0 ? '+' : ''}
                      {(result.market_trend.momentum_5d ?? result.market_trend.momentum ?? 0).toFixed(2)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">1-Month Mom</p>
                    <p className={`text-xs font-mono font-semibold ${(result.market_trend.momentum_1m ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {(result.market_trend.momentum_1m ?? 0) >= 0 ? '+' : ''}
                      {(result.market_trend.momentum_1m ?? 0).toFixed(2)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">Outperforming</p>
                    <p className="text-xs font-mono font-semibold text-fuchsia-400">
                      {result.market_trend.pct_outperforming !== undefined ? `${result.market_trend.pct_outperforming.toFixed(1)}%` : '—'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Data Source Notice */}
          <div className="flex items-center gap-2 px-4 py-2 bg-slate-900/40 border border-slate-800/40 rounded-xl text-xs">
            {result.summary.data_sources?.pcr === 'upstox' ? (
              <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                <CheckCircle2 size={14} className="flex-shrink-0" />
                <span>Live PCR from Upstox</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-amber-400/80 font-medium">
                <AlertTriangle size={14} className="flex-shrink-0" />
                <span>PCR unavailable (F&amp;O permission required)</span>
              </div>
            )}
          </div>

          {/* Market Breadth + Sector Strength */}
          {(result.market_breadth || result.sector_results) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {result.market_breadth && (
                <MarketBreadthPanel breadth={result.market_breadth} total={result.summary.valid_stocks_count ?? result.summary.total_stocks_analyzed} />
              )}
              {result.sector_results && Object.keys(result.sector_results).length > 0 && (
                <SectorStrengthPanel sectors={result.sector_results} />
              )}
            </div>
          )}

          {/* Signal Filter Chips / Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-4 mt-6">
            <div className="flex flex-wrap gap-2">
              {[
                { id: 'ALL', label: 'All Signals', count: allSignals.length, color: 'bg-slate-700/30 text-slate-300 border-slate-700/50 hover:bg-slate-700/50' },
                { id: 'BUY', label: 'BUY', count: allSignals.filter(s => s.signal_type === 'BUY').length, color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20' },
                { id: 'SELL', label: 'SELL', count: allSignals.filter(s => s.signal_type === 'SELL').length, color: 'bg-rose-500/10 text-rose-400 border-rose-500/20 hover:bg-rose-500/20' },
                { id: 'WATCH', label: 'WATCH', count: allSignals.filter(s => s.signal_type === 'WATCH').length, color: 'bg-amber-500/10 text-amber-400 border-amber-500/20 hover:bg-amber-500/20' },
                { id: 'HOLD', label: 'HOLD', count: allSignals.filter(s => s.signal_type === 'HOLD').length, color: 'bg-slate-500/10 text-slate-400 border-slate-500/20 hover:bg-slate-500/20' },
              ].map(chip => (
                <button
                  key={chip.id}
                  onClick={() => setSignalFilter(chip.id as any)}
                  className={`
                    flex items-center gap-2 px-4 py-2.5 rounded-xl border text-xs font-bold transition-all duration-300
                    ${signalFilter === chip.id 
                      ? 'bg-violet-600 border-violet-500 text-white shadow-lg shadow-violet-600/25 scale-[1.02]' 
                      : chip.color
                    }
                  `}
                >
                  <span>{chip.label}</span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] ${signalFilter === chip.id ? 'bg-white/20 text-white' : 'bg-slate-900/40'}`}>
                    {chip.count}
                  </span>
                </button>
              ))}
            </div>

            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-2 px-4 py-2.5 bg-slate-800/40 border border-slate-700/50 rounded-xl text-xs font-bold text-slate-400 hover:text-slate-200 transition-colors"
            >
              <SlidersHorizontal size={14} />
              <span>Filters</span>
              {showFilters ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
          </div>

          {/* Advanced Multi-Filters Panel */}
          {showFilters && (
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5 mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-in slide-in-from-top duration-300">
              {/* Search */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Search Symbol</label>
                <div className="relative">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Search by Symbol..."
                    className="w-full bg-slate-900/50 border border-slate-700/50 text-slate-200 text-xs rounded-xl pl-9 pr-3 py-2.5 focus:outline-none focus:ring-1 focus:ring-violet-500 placeholder:text-slate-600"
                  />
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                </div>
              </div>

              {/* Trend Filter */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Regime Trend</label>
                <select
                  value={trendFilter}
                  onChange={e => setTrendFilter(e.target.value as any)}
                  className="w-full bg-slate-900/50 border border-slate-700/50 text-slate-300 text-xs rounded-xl px-3 py-2.5 focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  <option value="ALL">All Trends</option>
                  <option value="BULLISH">Bullish</option>
                  <option value="BEARISH">Bearish</option>
                  <option value="SIDEWAYS">Sideways</option>
                </select>
              </div>

              {/* Risk Filter */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Risk Level</label>
                <select
                  value={riskFilter}
                  onChange={e => setRiskFilter(e.target.value as any)}
                  className="w-full bg-slate-900/50 border border-slate-700/50 text-slate-300 text-xs rounded-xl px-3 py-2.5 focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  <option value="ALL">All Risks</option>
                  <option value="LOW">Low Risk</option>
                  <option value="MEDIUM">Medium Risk</option>
                  <option value="HIGH">High Risk</option>
                </select>
              </div>

              {/* Institutional Strength (Conviction) */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Institutional Strength</label>
                <select
                  value={instStrengthFilter}
                  onChange={e => setInstStrengthFilter(e.target.value as any)}
                  className="w-full bg-slate-900/50 border border-slate-700/50 text-slate-300 text-xs rounded-xl px-3 py-2.5 focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  <option value="ALL">All Strengths</option>
                  <option value="VERY STRONG">Very Strong</option>
                  <option value="STRONG">Strong</option>
                  <option value="MODERATE">Moderate</option>
                  <option value="WEAK">Weak</option>
                </select>
              </div>

              {/* Sector Filter */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Sector</label>
                <select
                  value={sectorFilter}
                  onChange={e => setSectorFilter(e.target.value)}
                  className="w-full bg-slate-900/50 border border-slate-700/50 text-slate-300 text-xs rounded-xl px-3 py-2.5 focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  {['ALL', ...Array.from(new Set(allSignals.map(s => s.sector).filter(Boolean))).sort()].map(sec => (
                    <option key={sec} value={sec}>{sec === 'ALL' ? 'All Sectors' : sec}</option>
                  ))}
                </select>
              </div>

              {/* Confidence (Score) Filter */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Score Threshold</label>
                <select
                  value={confidenceFilter}
                  onChange={e => setConfidenceFilter(e.target.value)}
                  className="w-full bg-slate-900/50 border border-slate-700/50 text-slate-300 text-xs rounded-xl px-3 py-2.5 focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  <option value="ALL">Any Score</option>
                  <option value="90">Score &gt;= 90%</option>
                  <option value="80">Score &gt;= 80%</option>
                  <option value="70">Score &gt;= 70%</option>
                  <option value="50">Score &gt;= 50%</option>
                </select>
              </div>

              {/* Daily Change Filter */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Daily Change</label>
                <select
                  value={changeFilter}
                  onChange={e => setChangeFilter(e.target.value as any)}
                  className="w-full bg-slate-900/50 border border-slate-700/50 text-slate-300 text-xs rounded-xl px-3 py-2.5 focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  <option value="ALL">Any Change</option>
                  <option value="POSITIVE">Positive Movers</option>
                  <option value="NEGATIVE">Negative Movers</option>
                </select>
              </div>

              {/* Price Range Filter */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Price Range (₹)</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={priceMin}
                    onChange={e => setPriceMin(e.target.value)}
                    placeholder="Min"
                    className="w-1/2 bg-slate-900/50 border border-slate-700/50 text-slate-200 text-xs rounded-xl px-3 py-2.5 focus:outline-none focus:ring-1 focus:ring-violet-500 placeholder:text-slate-700"
                  />
                  <input
                    type="number"
                    value={priceMax}
                    onChange={e => setPriceMax(e.target.value)}
                    placeholder="Max"
                    className="w-1/2 bg-slate-900/50 border border-slate-700/50 text-slate-200 text-xs rounded-xl px-3 py-2.5 focus:outline-none focus:ring-1 focus:ring-violet-500 placeholder:text-slate-700"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Combined Signal Table */}
          <div className="bg-slate-800/40 border border-slate-700/40 rounded-2xl overflow-hidden mt-6">
            <div className="px-5 py-4 border-b border-slate-700/50 flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <Filter size={18} className="text-violet-400" />
                <h3 className="font-semibold text-slate-200">Signals Scanner Results</h3>
                <span className="text-xs bg-violet-500/20 text-violet-400 px-2 py-0.5 rounded-full font-semibold">
                  {filteredSignals.length} of {allSignals.length} opportunities
                </span>
              </div>
              
              {/* Reset button if filters active */}
              {(signalFilter !== 'ALL' || trendFilter !== 'ALL' || riskFilter !== 'ALL' || instStrengthFilter !== 'ALL' || sectorFilter !== 'ALL' || confidenceFilter !== 'ALL' || priceMin || priceMax || changeFilter !== 'ALL' || searchQuery) && (
                <button
                  onClick={() => {
                    setSignalFilter('ALL');
                    setTrendFilter('ALL');
                    setRiskFilter('ALL');
                    setInstStrengthFilter('ALL');
                    setSectorFilter('ALL');
                    setConfidenceFilter('ALL');
                    setPriceMin('');
                    setPriceMax('');
                    setChangeFilter('ALL');
                    setSearchQuery('');
                  }}
                  className="text-xs font-bold text-violet-400 hover:text-violet-300 transition-colors uppercase tracking-wider"
                >
                  Clear Filters
                </button>
              )}
            </div>
            <SignalTable signals={filteredSignals} />
          </div>
        </div>
      )}

      {/* Idle / First-Time State */}
      {status === 'IDLE' && !result && (
        <div className="text-center py-20">
          <div className="relative inline-block mb-6">
            <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20 flex items-center justify-center border border-violet-500/20">
              <Bot size={36} className="text-violet-400" />
            </div>
          </div>
          <h3 className="text-lg font-semibold text-slate-300 mb-2">NIFTY 500 AI Signal Engine — Ready</h3>
          <p className="text-sm text-slate-500 max-w-lg mx-auto mb-6">
            Select a universe, then run the engine to compute market breadth, sector strength,
            correlations with NIFTY 50, volatility analysis, and generate ranked BUY/SELL signals
            with AI conviction scoring.
          </p>
          <div className="flex flex-wrap justify-center gap-3 text-xs text-slate-500">
            {['Up to 500 Stocks', 'Historical Validation', 'Market Breadth', 'Sector Analysis', 'Correlation', 'ATR Volatility', 'EMA Trend', 'PCR', 'AI Score 0–100'].map((tag) => (
              <span key={tag} className="px-3 py-1.5 bg-slate-800/60 border border-slate-700/50 rounded-lg">{tag}</span>
            ))}
          </div>
        </div>
      )}

      {/* Run History */}
      {history.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 px-1">
            <History size={18} className="text-slate-400" />
            <h3 className="text-sm font-semibold text-slate-300">Run History</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {history.map((run) => (
              <div 
                key={run.run_id} 
                onClick={() => {
                  setRunId(run.run_id);
                  setStatus('COMPLETED');
                  setProgress(100);
                  api.getBotResults(run.run_id).then(res => {
                    if (res?.data) setResult(res.data);
                  });
                }}
                className={`
                  bg-slate-800/40 border border-slate-700/50 rounded-xl p-3 cursor-pointer transition-all
                  hover:bg-slate-800/60 hover:border-violet-500/30 group
                  ${runId === run.run_id ? 'ring-1 ring-violet-500/50 bg-slate-800/80 border-violet-500/50' : ''}
                `}
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="text-[10px] font-mono text-slate-500 group-hover:text-violet-400 transition-colors">
                    #{run.run_id}
                  </span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-bold uppercase ${
                    run.triggered_by === 'scheduler' ? 'bg-amber-500/10 text-amber-500' : 'bg-sky-500/10 text-sky-500'
                  }`}>
                    {run.triggered_by}
                  </span>
                </div>
                <div className="flex items-center gap-3 mb-2">
                  <div className="flex flex-col">
                    <span className="text-xs font-bold text-slate-300">
                      {new Date(run.started_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                    </span>
                    <span className="text-[10px] text-slate-500">
                      {new Date(run.started_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <div className="ml-auto flex items-center gap-2">
                    <div className="flex flex-col items-end">
                      <span className="text-xs font-bold text-emerald-400">+{run.buy_count}</span>
                      <span className="text-xs font-bold text-red-400">-{run.sell_count}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between text-[10px]">
                  <span className={`font-semibold ${run.market_trend === 'BULLISH' ? 'text-emerald-500' : 'text-red-500'}`}>
                    {run.market_trend}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {run.universe && (
                      <span className="text-violet-400/70 font-medium">{run.universe}</span>
                    )}
                    {run.pcr_source === 'upstox' && (
                      <span className="text-sky-500/70 font-medium">LIVE</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default BotTab;
