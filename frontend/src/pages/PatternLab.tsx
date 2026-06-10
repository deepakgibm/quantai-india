import React, { useState, useEffect } from 'react';
import { BookOpen, Search, Loader2, Sparkles, RefreshCw, BarChart2, Award } from 'lucide-react';
import { api } from '../services/api';

const PatternLab: React.FC = () => {
  const [symbol, setSymbol] = useState('RELIANCE');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPatterns = async (sym: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getPatternRecognition(sym);
      if (response && response.status === 'success') {
        setData(response.patterns);
      } else {
        setError('Failed to fetch pattern analysis');
      }
    } catch (e: any) {
      setError(e.message || 'Error communicating with pattern engine.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatterns(symbol);
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (symbol.trim()) {
      fetchPatterns(symbol.trim().toUpperCase());
    }
  };

  const handleQuickSelect = (sym: string) => {
    setSymbol(sym);
    fetchPatterns(sym);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white font-display">AI Pattern Recognition Lab</h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Real-time scanner recognizing Candlestick profiles, Fibonacci Harmonics, and Triangle/Flag structures.
          </p>
        </div>

        {/* Quick buttons */}
        <div className="flex gap-2">
          {['RELIANCE', 'TCS', 'BHEL'].map(s => (
            <button
              key={s}
              onClick={() => handleQuickSelect(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                symbol === s
                  ? 'bg-brand-600 text-white shadow'
                  : 'bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="flex gap-2 max-w-md">
        <input
          type="text"
          placeholder="Search Symbol (e.g. INFY, SBIN)"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="flex-grow bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 text-xs font-bold focus:border-brand-500 focus:outline-none text-slate-800 dark:text-slate-100"
        />
        <button
          type="submit"
          className="bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-slate-200 dark:text-slate-900 px-5 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 flex items-center gap-1.5"
        >
          <Search size={14} /> Scan
        </button>
      </form>

      {loading ? (
        <div className="flex flex-col items-center justify-center min-h-[40vh]">
          <Loader2 size={40} className="text-brand-500 animate-spin mb-4" />
          <p className="text-slate-400">Scanning {symbol} charts...</p>
        </div>
      ) : error ? (
        <div className="text-center py-12 bg-rose-500/5 border border-rose-500/10 rounded-2xl p-6">
          <p className="text-rose-500 mb-4">{error}</p>
          <button onClick={() => fetchPatterns(symbol)} className="px-4 py-2 bg-rose-500 text-white rounded-xl text-xs font-bold uppercase">Retry</button>
        </div>
      ) : data ? (
        <div className="space-y-6">
          {/* Top section: Harmonic and Chart Geometric patterns */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Chart Geometric Patterns */}
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm">
              <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                <BarChart2 size={16} className="text-brand-500" /> Chart Formations (Triangles & Flags)
              </h3>
              {data.chart_patterns && data.chart_patterns.length > 0 ? (
                <div className="space-y-3">
                  {data.chart_patterns.map((cp: any, idx: number) => (
                    <div
                      key={idx}
                      className="rounded-xl p-4 border border-slate-100 dark:border-slate-700/30 bg-slate-50 dark:bg-slate-900/50 space-y-2"
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-bold text-slate-900 dark:text-white">{cp.pattern}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-brand-500/10 text-brand-500">
                          {cp.type}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-center pt-2">
                        <div className="bg-white dark:bg-slate-800 p-2 rounded-lg border border-slate-100 dark:border-slate-700/50">
                          <p className="text-[9px] text-slate-400 font-bold uppercase">Trigger</p>
                          <p className="text-xs font-bold font-mono mt-0.5 text-blue-500">₹{cp.trigger_price?.toFixed(1)}</p>
                        </div>
                        <div className="bg-white dark:bg-slate-800 p-2 rounded-lg border border-slate-100 dark:border-slate-700/50">
                          <p className="text-[9px] text-slate-400 font-bold uppercase">Target</p>
                          <p className="text-xs font-bold font-mono mt-0.5 text-emerald-500">₹{cp.target?.toFixed(1)}</p>
                        </div>
                        <div className="bg-white dark:bg-slate-800 p-2 rounded-lg border border-slate-100 dark:border-slate-700/50">
                          <p className="text-[9px] text-slate-400 font-bold uppercase">Direction</p>
                          <p className="text-xs font-bold mt-0.5 text-slate-700 dark:text-slate-300">{cp.direction}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic">No significant geometric formations detected.</p>
              )}
            </div>

            {/* Harmonic Patterns */}
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm">
              <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                <Award size={16} className="text-brand-500" /> Harmonic Formations (XA-AB-BC-CD)
              </h3>
              {data.harmonic_patterns && data.harmonic_patterns.length > 0 ? (
                <div className="space-y-3">
                  {data.harmonic_patterns.map((hp: any, idx: number) => (
                    <div
                      key={idx}
                      className="rounded-xl p-4 border border-brand-500/10 bg-brand-500/5 space-y-3"
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-bold text-slate-900 dark:text-white">{hp.pattern}</span>
                        <span className="text-xs font-bold text-emerald-400">{hp.accuracy}% Accuracy Match</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-center">
                        <div className="bg-white dark:bg-slate-800 p-2.5 rounded-lg">
                          <p className="text-[9px] text-slate-400 uppercase font-bold">Target Target</p>
                          <p className="text-xs font-bold text-emerald-500 font-mono">₹{hp.target_price?.toFixed(1)}</p>
                        </div>
                        <div className="bg-white dark:bg-slate-800 p-2.5 rounded-lg">
                          <p className="text-[9px] text-slate-400 uppercase font-bold">Stop Loss</p>
                          <p className="text-xs font-bold text-rose-500 font-mono">₹{hp.stop_loss?.toFixed(1)}</p>
                        </div>
                      </div>
                      <div className="border-t border-slate-200 dark:border-slate-700/50 pt-2.5">
                        <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wide">Ratio breakdown:</span>
                        <div className="flex gap-3 mt-1.5 text-[10px] font-bold font-mono">
                          {Object.entries(hp.ratio_breakdown).map(([k, v]: any) => (
                            <span key={k} className="bg-slate-100 dark:bg-slate-900 px-2 py-0.5 rounded text-slate-600 dark:text-slate-300">
                              {k}: {v}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic">No harmonic structures identified.</p>
              )}
            </div>
          </div>

          {/* Bottom section: Candlestick Patterns list table */}
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-6 shadow-sm">
            <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4">Detected Candlestick Signals</h3>
            {data.candlestick_patterns && data.candlestick_patterns.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-100 dark:border-slate-700/50 text-[10px] text-slate-400 uppercase tracking-widest font-bold">
                      <th className="pb-3">Date</th>
                      <th className="pb-3">Pattern</th>
                      <th className="pb-3">Trigger Price</th>
                      <th className="pb-3">Outlook</th>
                      <th className="pb-3">Description</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-700/30 text-xs">
                    {data.candlestick_patterns.map((cp: any, idx: number) => (
                      <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-700/20">
                        <td className="py-3.5 text-slate-500 font-mono">{cp.timestamp}</td>
                        <td className="py-3.5 font-bold text-slate-900 dark:text-white">{cp.pattern}</td>
                        <td className="py-3.5 font-mono">₹{cp.price?.toFixed(1)}</td>
                        <td className="py-3.5">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            cp.type === 'BULLISH' ? 'bg-green-500/10 text-green-600' : cp.type === 'BEARISH' ? 'bg-rose-500/10 text-rose-600' : 'bg-slate-100 text-slate-600'
                          }`}>
                            {cp.type}
                          </span>
                        </td>
                        <td className="py-3.5 text-slate-500 dark:text-slate-400 font-medium italic">"{cp.description}"</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No candlestick patterns detected.</p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default PatternLab;
