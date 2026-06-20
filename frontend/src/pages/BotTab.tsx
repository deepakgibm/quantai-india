import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../services/api';
import {
  Bot, Play, Loader2, CheckCircle2, XCircle, Clock, TrendingUp,
  TrendingDown, ArrowUpCircle, ArrowDownCircle, Activity, BarChart3,
  Zap, RefreshCw, AlertTriangle, History
} from 'lucide-react';

// ── Types ────────────────────────────────────────────────────────────────────

interface BotSignal {
  symbol: string;
  signal_type: 'BUY' | 'SELL';
  correlation: number;
  correlation_category: string;
  price_change_pct: number;
  current_price: number;
  volatility_level: string;
  volatility_atr: number;
  pcr_value: number | null;
  pcr_source: string;
  conviction: string;
}

interface MarketTrend {
  trend: string;
  ema_50: number;
  ema_200: number;
  momentum: number;
  last_close: number;
}

interface BotSummary {
  total_stocks_analyzed: number;
  total_correlations: number;
  high_correlation_count: number;
  total_signals: number;
  buy_count: number;
  sell_count: number;
  execution_time_seconds: number;
  data_sources: { historical: string; live_quotes: number; pcr: string };
}

interface BotResult {
  run_id: string;
  market_trend: MarketTrend | null;
  buy_signals: BotSignal[];
  sell_signals: BotSignal[];
  summary: BotSummary;
  completed_at: string | null;
}

type BotStatus = 'IDLE' | 'COLLECTING_DATA' | 'ANALYZING_CORRELATION' |
  'ANALYZING_VOLATILITY' | 'DETECTING_TREND' | 'GENERATING_SIGNALS' |
  'COMPLETED' | 'ERROR';

// ── Step Config ──────────────────────────────────────────────────────────────

const STEPS: { key: BotStatus; label: string; icon: React.ReactNode }[] = [
  { key: 'COLLECTING_DATA', label: 'Collecting Data', icon: <BarChart3 size={16} /> },
  { key: 'ANALYZING_CORRELATION', label: 'Correlation Analysis', icon: <Activity size={16} /> },
  { key: 'ANALYZING_VOLATILITY', label: 'Volatility Analysis', icon: <Zap size={16} /> },
  { key: 'DETECTING_TREND', label: 'Market Trend', icon: <TrendingUp size={16} /> },
  { key: 'GENERATING_SIGNALS', label: 'Generating Signals', icon: <Bot size={16} /> },
  { key: 'COMPLETED', label: 'Complete', icon: <CheckCircle2 size={16} /> },
];

const STEP_ORDER = STEPS.map(s => s.key);

// ── Helpers ──────────────────────────────────────────────────────────────────

function getStepIndex(status: BotStatus): number {
  return STEP_ORDER.indexOf(status);
}

function ConvictionBadge({ conviction }: { conviction: string }) {
  const styles: Record<string, string> = {
    STRONG: 'bg-emerald-500/20 text-emerald-400 ring-emerald-500/30',
    MODERATE: 'bg-amber-500/20 text-amber-400 ring-amber-500/30',
    WEAK: 'bg-slate-500/20 text-slate-400 ring-slate-500/30',
  };
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ring-1 ${styles[conviction] || styles.WEAK}`}>
      {conviction}
    </span>
  );
}

function VolatilityBadge({ level }: { level: string }) {
  const styles: Record<string, string> = {
    HIGH: 'bg-red-500/15 text-red-400',
    MEDIUM: 'bg-amber-500/15 text-amber-400',
    LOW: 'bg-emerald-500/15 text-emerald-400',
  };
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded ${styles[level] || 'bg-slate-700 text-slate-400'}`}>
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

// ── Signal Table ─────────────────────────────────────────────────────────────

function SignalTable({ signals, type }: { signals: BotSignal[]; type: 'BUY' | 'SELL' }) {
  const [sortBy, setSortBy] = useState<string>('conviction');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const handleSort = (col: string) => {
    if (sortBy === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortBy(col); setSortDir('asc'); }
  };

  const sorted = [...signals].sort((a, b) => {
    const dir = sortDir === 'asc' ? 1 : -1;
    if (sortBy === 'conviction') {
      const o: Record<string, number> = { STRONG: 0, MODERATE: 1, WEAK: 2 };
      return ((o[a.conviction] || 3) - (o[b.conviction] || 3)) * dir;
    }
    const av = (a as any)[sortBy] ?? 0;
    const bv = (b as any)[sortBy] ?? 0;
    return (av > bv ? 1 : -1) * dir;
  });

  const accent = type === 'BUY' ? 'emerald' : 'red';
  const Icon = type === 'BUY' ? ArrowUpCircle : ArrowDownCircle;

  if (!signals.length) {
    return (
      <div className="text-center py-8 text-slate-500">
        <Icon size={32} className="mx-auto mb-2 opacity-40" />
        <p className="text-sm">No {type} signals generated</p>
      </div>
    );
  }

  const thClass = "px-3 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 transition-colors select-none";

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" id={`bot-${type.toLowerCase()}-signals-table`}>
        <thead>
          <tr className="border-b border-slate-700/50">
            <th className={thClass} onClick={() => handleSort('symbol')}>Stock</th>
            <th className={thClass} onClick={() => handleSort('correlation')}>Correlation</th>
            <th className={thClass} onClick={() => handleSort('price_change_pct')}>% Change</th>
            <th className={thClass} onClick={() => handleSort('current_price')}>Price</th>
            <th className={thClass} onClick={() => handleSort('volatility_level')}>Volatility</th>
            <th className={thClass}>PCR</th>
            <th className={thClass} onClick={() => handleSort('conviction')}>Conviction</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/50">
          {sorted.map((s, i) => (
            <tr key={s.symbol} className="hover:bg-slate-800/30 transition-colors">
              <td className="px-3 py-2.5 font-semibold text-slate-200">{s.symbol}</td>
              <td className="px-3 py-2.5">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono text-slate-300">{s.correlation.toFixed(2)}</span>
                  <CorrelationBadge category={s.correlation_category} />
                </div>
              </td>
              <td className={`px-3 py-2.5 font-mono font-semibold ${s.price_change_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {s.price_change_pct >= 0 ? '+' : ''}{s.price_change_pct.toFixed(2)}%
              </td>
              <td className="px-3 py-2.5 font-mono text-slate-300">₹{s.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
              <td className="px-3 py-2.5"><VolatilityBadge level={s.volatility_level} /></td>
              <td className="px-3 py-2.5">
                {s.pcr_value != null ? (
                  <div className="flex items-center gap-1">
                    <span className="font-mono text-slate-300">{s.pcr_value.toFixed(2)}</span>
                    {s.pcr_source === 'simulated' && (
                      <span className="text-[10px] bg-slate-700/80 text-slate-500 px-1 rounded">SIM</span>
                    )}
                  </div>
                ) : (
                  <span className="text-slate-600">—</span>
                )}
              </td>
              <td className="px-3 py-2.5"><ConvictionBadge conviction={s.conviction} /></td>
            </tr>
          ))}
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
  const pollRef = useRef<NodeJS.Timeout | null>(null);

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
      const data = await api.startBot();
      if (data.run_id) {
        setRunId(data.run_id);
        setStatus('COLLECTING_DATA');
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
      <div className="flex items-center justify-between">
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
              Signal Bot
            </h1>
            <div className="flex items-center gap-2">
              <p className="text-sm text-slate-400">NIFTY 500 correlation-based signal engine</p>
              {scheduler?.enabled && (
                <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-[10px] font-semibold text-emerald-400">
                  <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                  Auto-run: {scheduler.morning_run} & {scheduler.close_run} IST
                </div>
              )}
            </div>
          </div>
        </div>

        <button
          id="start-bot-button"
          onClick={handleStart}
          disabled={isRunning || isStarting}
          className={`
            flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm
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
          {isRunning ? 'Running...' : isStarting ? 'Starting...' : 'Start Bot'}
        </button>
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
              { label: 'Stocks Analyzed', value: result.summary.total_stocks_analyzed, icon: <BarChart3 size={16} />, color: 'slate' },
              { label: 'High Correlation', value: result.summary.high_correlation_count, icon: <Activity size={16} />, color: 'sky' },
              { label: 'Total Signals', value: result.summary.total_signals, icon: <Zap size={16} />, color: 'violet' },
              { label: 'BUY Signals', value: result.summary.buy_count, icon: <ArrowUpCircle size={16} />, color: 'emerald' },
              { label: 'SELL Signals', value: result.summary.sell_count, icon: <ArrowDownCircle size={16} />, color: 'red' },
              { label: 'Time', value: `${result.summary.execution_time_seconds}s`, icon: <Clock size={16} />, color: 'amber' },
            ].map((card) => (
              <div key={card.label} className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
                <div className={`flex items-center gap-1.5 text-${card.color}-400 mb-2`}>
                  {card.icon}
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{card.label}</span>
                </div>
                <p className="text-xl font-bold text-slate-200">{card.value}</p>
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
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {result.market_trend.trend === 'BULLISH'
                    ? <TrendingUp size={28} className="text-emerald-400" />
                    : <TrendingDown size={28} className="text-red-400" />
                  }
                  <div>
                    <p className="text-sm font-medium text-slate-400">NIFTY 50 Market Trend</p>
                    <p className={`text-2xl font-bold ${
                      result.market_trend.trend === 'BULLISH' ? 'text-emerald-400' : 'text-red-400'
                    }`}>
                      {result.market_trend.trend}
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-6 text-right">
                  <div>
                    <p className="text-[11px] text-slate-500 uppercase">Last Close</p>
                    <p className="text-sm font-mono font-semibold text-slate-300">
                      {result.market_trend.last_close.toLocaleString('en-IN')}
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] text-slate-500 uppercase">EMA 50</p>
                    <p className="text-sm font-mono font-semibold text-sky-400">
                      {result.market_trend.ema_50.toLocaleString('en-IN')}
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] text-slate-500 uppercase">EMA 200</p>
                    <p className="text-sm font-mono font-semibold text-amber-400">
                      {result.market_trend.ema_200.toLocaleString('en-IN')}
                    </p>
                  </div>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-2 text-sm">
                <span className="text-slate-500">5-Day Momentum:</span>
                <span className={`font-semibold ${result.market_trend.momentum >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {result.market_trend.momentum >= 0 ? '+' : ''}{result.market_trend.momentum}%
                </span>
              </div>
            </div>
          )}

          {/* Data Source Notice */}
          {result.summary.data_sources?.pcr === 'simulated' && (
            <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-500/10 border border-amber-500/20 rounded-xl text-sm text-amber-400/80">
              <AlertTriangle size={16} className="flex-shrink-0" />
              <span>PCR values are simulated. Real options data requires F&O segment access on Upstox.</span>
            </div>
          )}

          {/* BUY Signals */}
          <div className="bg-slate-800/40 border border-slate-700/40 rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-700/50 flex items-center gap-2">
              <ArrowUpCircle size={18} className="text-emerald-400" />
              <h3 className="font-semibold text-slate-200">BUY Signals</h3>
              <span className="ml-auto text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full font-semibold">
                {result.buy_signals?.length || 0}
              </span>
            </div>
            <SignalTable signals={result.buy_signals} type="BUY" />
          </div>

          {/* SELL Signals */}
          <div className="bg-slate-800/40 border border-slate-700/40 rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-700/50 flex items-center gap-2">
              <ArrowDownCircle size={18} className="text-red-400" />
              <h3 className="font-semibold text-slate-200">SELL Signals</h3>
              <span className="ml-auto text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full font-semibold">
                {result.sell_signals?.length || 0}
              </span>
            </div>
            <SignalTable signals={result.sell_signals} type="SELL" />
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
          <h3 className="text-lg font-semibold text-slate-300 mb-2">Ready to Analyze</h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto mb-6">
            The Signal Bot will analyze all NIFTY 500 stocks, compute correlations with NIFTY 50,
            assess volatility, detect market trend, and generate BUY/SELL signals.
          </p>
          <div className="flex flex-wrap justify-center gap-3 text-xs text-slate-500">
            {['500 Stocks', 'Correlation Analysis', 'ATR Volatility', 'EMA Trend', 'PCR Confirmation'].map((tag) => (
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
                  {run.pcr_source === 'upstox' && (
                    <span className="text-sky-500/70 font-medium">LIVE DATA</span>
                  )}
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
