import React, { useState, useEffect } from 'react';
import { Compass, Search, Loader2, Sparkles, RefreshCw, Layers, Zap } from 'lucide-react';
import { api } from '../services/api';

const SMCAnalysis: React.FC = () => {
  const [symbol, setSymbol] = useState('RELIANCE');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSMCAnalysis = async (sym: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getSMCAnalysis(sym);
      if (response && response.status === 'success') {
        setData(response.analysis);
      } else {
        setError('Failed to fetch SMC patterns');
      }
    } catch (e: any) {
      setError(e.message || 'Error communicating with SMC engine.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSMCAnalysis(symbol);
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (symbol.trim()) {
      fetchSMCAnalysis(symbol.trim().toUpperCase());
    }
  };

  const handleQuickSelect = (sym: string) => {
    setSymbol(sym);
    fetchSMCAnalysis(sym);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white font-display">Smart Money Concepts</h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Algorithmic detection of structural shifts (BOS, CHOCH), Order Blocks, Fair Value Gaps, and Liquidity Pools.
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
          <p className="text-slate-400">Scanning {symbol} structure...</p>
        </div>
      ) : error ? (
        <div className="text-center py-12 bg-rose-500/5 border border-rose-500/10 rounded-2xl p-6">
          <p className="text-rose-500 mb-4">{error}</p>
          <button onClick={() => fetchSMCAnalysis(symbol)} className="px-4 py-2 bg-rose-500 text-white rounded-xl text-xs font-bold uppercase">Retry</button>
        </div>
      ) : data ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Order blocks and structure */}
          <div className="space-y-6">
            {/* Order Blocks */}
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm">
              <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                <Layers size={16} className="text-brand-500" /> Detected Order Blocks (OB)
              </h3>
              {data.order_blocks && data.order_blocks.length > 0 ? (
                <div className="space-y-3">
                  {data.order_blocks.map((ob: any, idx: number) => (
                    <div
                      key={idx}
                      className={`flex justify-between items-center rounded-xl p-3 border ${
                        ob.type === 'BULLISH'
                          ? 'bg-green-500/5 border-green-500/20'
                          : 'bg-rose-500/5 border-rose-500/20'
                      }`}
                    >
                      <div>
                        <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded ${
                          ob.type === 'BULLISH' ? 'bg-green-500/10 text-green-600' : 'bg-rose-500/10 text-rose-600'
                        }`}>{ob.type} OB</span>
                        <p className="text-xs text-slate-500 mt-2 font-medium">Zone: ₹{ob.low?.toFixed(1)} - ₹{ob.high?.toFixed(1)}</p>
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono">{ob.timestamp}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic">No significant order blocks detected in the last 50 candles.</p>
              )}
            </div>

            {/* Structure events */}
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm">
              <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                <Zap size={16} className="text-brand-500" /> Structural Shifts (BOS / CHOCH)
              </h3>
              {data.structural_events && data.structural_events.length > 0 ? (
                <div className="space-y-3">
                  {data.structural_events.map((se: any, idx: number) => (
                    <div
                      key={idx}
                      className="flex justify-between items-center rounded-xl p-3 border border-slate-100 dark:border-slate-700/30 bg-slate-50 dark:bg-slate-900/50"
                    >
                      <div>
                        <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded ${
                          se.type === 'BULLISH' ? 'bg-green-500/10 text-green-600' : 'bg-rose-500/10 text-rose-600'
                        }`}>{se.type} {se.event}</span>
                        <p className="text-xs text-slate-500 mt-2 font-medium">Breached level: ₹{se.level?.toFixed(2)}</p>
                        <p className="text-[9px] text-slate-400 mt-0.5 font-medium">Swing date: {se.origin_date}</p>
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono">{se.timestamp}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic">No structural break events detected.</p>
              )}
            </div>
          </div>

          {/* FVG and liquidity */}
          <div className="space-y-6">
            {/* Fair Value Gaps */}
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm">
              <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                <Layers size={16} className="text-brand-500" /> Fair Value Gaps (FVG)
              </h3>
              {data.fair_value_gaps && data.fair_value_gaps.length > 0 ? (
                <div className="space-y-3">
                  {data.fair_value_gaps.map((fvg: any, idx: number) => (
                    <div
                      key={idx}
                      className={`flex justify-between items-center rounded-xl p-3 border ${
                        fvg.type === 'BULLISH'
                          ? 'bg-green-500/5 border-green-500/20'
                          : 'bg-rose-500/5 border-rose-500/20'
                      }`}
                    >
                      <div>
                        <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded ${
                          fvg.type === 'BULLISH' ? 'bg-green-500/10 text-green-600' : 'bg-rose-500/10 text-rose-600'
                        }`}>{fvg.type} FVG</span>
                        <p className="text-xs text-slate-500 mt-2 font-medium">Gap: ₹{fvg.bottom?.toFixed(1)} - ₹{fvg.top?.toFixed(1)}</p>
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono">{fvg.timestamp}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic">No imbalance/FVG zones detected.</p>
              )}
            </div>

            {/* Liquidity zones */}
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm">
              <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                <Compass size={16} className="text-brand-500" /> Liquidity Zones (BSL / SSL)
              </h3>
              {data.liquidity_zones && data.liquidity_zones.length > 0 ? (
                <div className="space-y-3">
                  {data.liquidity_zones.map((lz: any, idx: number) => (
                    <div
                      key={idx}
                      className="flex justify-between items-center rounded-xl p-3 border border-slate-100 dark:border-slate-700/30 bg-slate-50 dark:bg-slate-900/50"
                    >
                      <div>
                        <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded bg-blue-500/10 text-blue-500">
                          {lz.type === 'BSL' ? 'Buy-side Liquidity' : 'Sell-side Liquidity'}
                        </span>
                        <p className="text-xs text-slate-500 mt-2 font-medium">Equal high/low cluster: ₹{lz.level?.toFixed(2)}</p>
                        <p className="text-[9px] text-slate-400 mt-0.5 font-medium">Stops range: ₹{lz.range_bottom?.toFixed(1)} - ₹{lz.range_top?.toFixed(1)}</p>
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono">{lz.timestamp}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic">No equal swing clusters / liquidity pools detected.</p>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default SMCAnalysis;
