import React, { useState, useEffect } from 'react';
import { Award, CheckCircle, XCircle, TrendingUp, TrendingDown, RefreshCw, Loader2, Play } from 'lucide-react';
import { api } from '../services/api';

const SignalCenter: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSignalCenter = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getSignalCenter();
      if (response && response.status === 'success') {
        setData(response.metrics);
      } else {
        setError('Failed to fetch signal performance');
      }
    } catch (e: any) {
      setError(e.message || 'Error communicating with signal tracker.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSignalCenter();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 size={40} className="text-brand-500 animate-spin mb-4" />
        <p className="text-slate-400">Loading Signal Performance metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12 bg-rose-500/5 border border-rose-500/10 rounded-2xl p-6">
        <p className="text-rose-500 mb-4">{error}</p>
        <button onClick={fetchSignalCenter} className="px-4 py-2 bg-rose-500 text-white rounded-xl text-xs font-bold uppercase">Retry</button>
      </div>
    );
  }

  const {
    total_signals,
    win_rate,
    wins,
    losses,
    monthly_performance,
    conviction_analysis,
    leaderboard,
    historical_signals
  } = data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white font-display">Signal Performance Center</h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Track historical bot signal accuracy, overall win rates, conviction confidence intervals, and ticker leaders.
          </p>
        </div>
        <button
          onClick={fetchSignalCenter}
          className="flex items-center gap-2 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs font-bold rounded-xl transition-all uppercase tracking-wide shrink-0"
        >
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {/* Accuracy Stats cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm flex flex-col justify-between">
          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Win Rate (Accuracy)</span>
          <span className="text-3xl font-black text-brand-500 block mt-2 font-mono">{win_rate?.toFixed(1)}%</span>
          <span className="text-[9px] text-slate-400 mt-2 block font-medium">Aggregate accuracy across all runs</span>
        </div>

        <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm flex flex-col justify-between">
          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Total Signals Tracked</span>
          <span className="text-2xl font-bold text-slate-900 dark:text-white block mt-2 font-mono">{total_signals}</span>
          <span className="text-[9px] text-slate-400 mt-2 block font-medium">Executed bot triggers</span>
        </div>

        <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Winning Signals</span>
            <span className="text-2xl font-bold text-emerald-500 block mt-2 font-mono">{wins}</span>
          </div>
          <CheckCircle className="text-emerald-500" size={28} />
        </div>

        <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Losing Signals</span>
            <span className="text-2xl font-bold text-rose-500 block mt-2 font-mono">{losses}</span>
          </div>
          <XCircle className="text-rose-500" size={28} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Leaderboard and Conviction */}
        <div className="space-y-6">
          {/* Conviction breakdown */}
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm">
            <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4 flex items-center gap-2">
              <Award size={16} className="text-brand-500" /> Conviction Analysis
            </h3>
            <div className="space-y-3">
              {conviction_analysis.map((c: any) => (
                <div key={c.conviction} className="space-y-1">
                  <div className="flex justify-between text-xs font-bold text-slate-700 dark:text-slate-300">
                    <span>{c.conviction} ({c.total} signals)</span>
                    <span className="font-mono text-brand-500">{c.win_rate}%</span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 dark:bg-slate-900 rounded-full overflow-hidden">
                    <div className="bg-brand-500 h-full rounded-full" style={{ width: `${c.win_rate}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Leaderboard */}
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm">
            <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4 flex items-center gap-2">
              <TrendingUp size={16} className="text-brand-500" /> Signal Leaders
            </h3>
            <div className="space-y-3">
              {leaderboard.map((l: any, idx: number) => (
                <div key={l.symbol} className="flex items-center justify-between text-xs font-semibold">
                  <div className="flex items-center gap-2">
                    <span className="w-4 text-[10px] text-slate-400 font-bold">{idx + 1}.</span>
                    <span className="font-bold text-slate-800 dark:text-white">{l.symbol}</span>
                    <span className="text-[10px] text-slate-400 font-normal">({l.total_signals} triggers)</span>
                  </div>
                  <span className="font-mono text-emerald-500 font-bold">{l.win_rate}% Win</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Historical signals table list */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-6 shadow-sm">
          <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4">Historical Performance Log</h3>
          <div className="overflow-y-auto max-h-[360px]">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-700/50 text-[10px] text-slate-400 uppercase tracking-widest font-bold">
                  <th className="pb-3">Ticker</th>
                  <th className="pb-3">Action</th>
                  <th className="pb-3">Conviction</th>
                  <th className="pb-3 text-right">Subsequent Change</th>
                  <th className="pb-3 text-center">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/30 text-xs">
                {historical_signals.map((s: any, idx: number) => {
                  const isBuy = s.signal_type === 'BUY';
                  const isProfit = s.price_change >= 0;
                  const isWin = (isBuy && isProfit) || (!isBuy && !isProfit);

                  return (
                    <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-700/20">
                      <td className="py-3 font-bold text-slate-900 dark:text-white">{s.symbol}</td>
                      <td className="py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          isBuy ? 'bg-emerald-500/10 text-emerald-600' : 'bg-rose-500/10 text-rose-600'
                        }`}>
                          {s.signal_type}
                        </span>
                      </td>
                      <td className="py-3 text-slate-400 font-semibold">{s.conviction}</td>
                      <td className={`py-3 text-right font-bold font-mono ${isProfit ? 'text-emerald-500' : 'text-rose-500'}`}>
                        {isProfit ? '+' : ''}{s.price_change?.toFixed(2)}%
                      </td>
                      <td className="py-3 text-center">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          isWin ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'
                        }`}>
                          {isWin ? 'WIN' : 'LOSS'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignalCenter;
