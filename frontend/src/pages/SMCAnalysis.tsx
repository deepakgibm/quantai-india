import React, { useState, useEffect } from 'react';
import { Compass, Search, Loader2, Sparkles, RefreshCw, Layers, Zap, Eye, Plus } from 'lucide-react';
import { api, apiGet, apiPost, apiRequest, API_URL, getAuthHeaders } from '../services/api';
import { useGlobalSymbol } from '../contexts/GlobalSymbolContext';
import GlobalSymbolSearch from '../components/GlobalSymbolSearch';

const SMCAnalysis: React.FC = () => {
  const { selectedSymbol, setSelectedSymbol } = useGlobalSymbol();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [isInWatchlist, setIsInWatchlist] = useState(false);
  const [watchlistLoading, setWatchlistLoading] = useState(false);

  const checkWatchlist = async () => {
    try {
      const res = await apiGet<any[]>('/api/watchlist');
      if (res.success) {
        const found = res.data.some((item: any) => item.symbol.toUpperCase() === selectedSymbol.toUpperCase());
        setIsInWatchlist(found);
      }
    } catch (e) {
      console.warn("Failed to fetch watchlist status:", e);
    }
  };

  const handleWatchlistToggle = async () => {
    setWatchlistLoading(true);
    try {
      if (isInWatchlist) {
        const res = await apiRequest<{ status: string }>(
          `${API_URL}/api/watchlist/${selectedSymbol}`,
          { method: 'DELETE', headers: getAuthHeaders() }
        );
        if (res.success) {
          setIsInWatchlist(false);
        }
      } else {
        const res = await apiPost<any>('/api/watchlist', { symbol: selectedSymbol });
        if (res.success) {
          setIsInWatchlist(true);
        }
      }
    } catch (e) {
      console.error("Watchlist toggle error:", e);
    } finally {
      setWatchlistLoading(false);
    }
  };

  const [timeframe, setTimeframe] = useState<string>('1D');

  const fetchSMCAnalysis = async (sym: string, tf: string) => {
    setData(null);
    setLoading(true);
    setError(null);
    try {
      const response = await api.getSMCAnalysis(sym, tf);
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
    fetchSMCAnalysis(selectedSymbol, timeframe);
    checkWatchlist();
  }, [selectedSymbol, timeframe]);

  const handleQuickSelect = (sym: string) => {
    setSelectedSymbol(sym);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white font-display flex items-center gap-3">
            Smart Money Concepts
            <button
              onClick={handleWatchlistToggle}
              disabled={watchlistLoading}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-bold transition-all border ${
                isInWatchlist
                  ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-500 hover:bg-indigo-500/20'
                  : 'bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border-transparent'
              }`}
            >
              {isInWatchlist ? (
                <>
                  <Eye size={13} /> Tracked
                </>
              ) : (
                <>
                  <Plus size={13} /> Add Watchlist
                </>
              )}
            </button>
          </h1>
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
                selectedSymbol === s
                  ? 'bg-brand-600 text-white shadow'
                  : 'bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Search & Timeframe Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex gap-2 max-w-md w-full">
          <GlobalSymbolSearch />
        </div>
        
        {/* Timeframe Selector */}
        <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl w-fit border border-slate-200/40 dark:border-slate-700/30">
          {['5m', '15m', '30m', '1H', '1D'].map(tfOption => (
            <button
              key={tfOption}
              onClick={() => setTimeframe(tfOption)}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${
                timeframe === tfOption
                  ? 'bg-white dark:bg-slate-900 text-brand-600 dark:text-brand-400 shadow-sm border border-slate-200/50 dark:border-slate-800'
                  : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              {tfOption}
            </button>
          ))}
        </div>
      </div>

      {data && !loading && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200/60 dark:border-slate-800/80 rounded-2xl">
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Interval Timeframe</span>
            <div className="text-sm font-extrabold text-slate-800 dark:text-slate-100 font-mono mt-0.5">{data.timeframe || timeframe}</div>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Confidence Score</span>
            <div className="text-sm font-extrabold text-brand-600 dark:text-brand-400 font-mono mt-0.5">{data.confidenceScore ?? 75}%</div>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Data Quality Score</span>
            <div className="text-sm font-extrabold text-emerald-600 dark:text-emerald-400 font-mono mt-0.5">{data.dataQualityScore ?? 100}%</div>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Last Candle Time</span>
            <div className="text-xs font-semibold text-slate-500 mt-1 font-mono">{data.lastCandleTime ? new Date(data.lastCandleTime).toLocaleDateString() : 'N/A'}</div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center min-h-[40vh]">
          <Loader2 size={40} className="text-brand-500 animate-spin mb-4" />
          <p className="text-slate-400">Scanning {selectedSymbol} structure...</p>
        </div>
      ) : error ? (
        <div className="text-center py-12 bg-rose-500/5 border border-rose-500/10 rounded-2xl p-6">
          <p className="text-rose-500 mb-4">{error}</p>
          <button onClick={() => fetchSMCAnalysis(selectedSymbol, timeframe)} className="px-4 py-2 bg-rose-500 text-white rounded-xl text-xs font-bold uppercase">Retry</button>
        </div>
      ) : data ? (
        (() => {
          // Validate data lists before rendering
          const validOrderBlocks = data.order_blocks?.filter((ob: any) => ob.high && ob.low && ob.high > ob.low && ob.timestamp) || [];
          const validStructuralEvents = data.structural_events?.filter((se: any) => se.level && se.level > 0 && se.timestamp) || [];
          const validFVGs = data.fair_value_gaps?.filter((fvg: any) => fvg.top && fvg.bottom && fvg.top > fvg.bottom && fvg.timestamp) || [];
          const validLiquidity = data.liquidity_zones?.filter((lz: any) => lz.range_top && lz.range_bottom && lz.range_top >= lz.range_bottom && lz.level && lz.timestamp) || [];

          return (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Order blocks and structure */}
              <div className="space-y-6">
                {/* Order Blocks */}
                <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm">
                  <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                    <Layers size={16} className="text-brand-500" /> Detected Order Blocks (OB)
                  </h3>
                  {validOrderBlocks.length > 0 ? (
                    <div className="space-y-3">
                      {validOrderBlocks.map((ob: any, idx: number) => (
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
                    <p className="text-xs text-slate-500 italic">No significant order blocks detected in this timeframe.</p>
                  )}
                </div>

                {/* Structure events */}
                <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm">
                  <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                    <Zap size={16} className="text-brand-500" /> Structural Shifts (BOS / CHOCH)
                  </h3>
                  {validStructuralEvents.length > 0 ? (
                    <div className="space-y-3">
                      {validStructuralEvents.map((se: any, idx: number) => (
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
                  {validFVGs.length > 0 ? (
                    <div className="space-y-3">
                      {validFVGs.map((fvg: any, idx: number) => (
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
                  {validLiquidity.length > 0 ? (
                    <div className="space-y-3">
                      {validLiquidity.map((lz: any, idx: number) => (
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
          );
        })()
      ) : null}
    </div>
  );
};

export default SMCAnalysis;
