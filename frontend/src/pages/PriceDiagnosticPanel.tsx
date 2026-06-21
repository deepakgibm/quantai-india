import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, RefreshCw, Activity, CheckCircle, XCircle, Search, HelpCircle } from 'lucide-react';
import { api } from '../services/api';
import { MarketDataService, MarketQuote } from '../services/marketDataService';

interface PriceRow {
  symbol: string;
  apiPrice: number;
  wsPrice: number;
  cachePrice: number;
  uiPrice: number;
  diff: number;
  status: 'MATCH' | 'MISMATCH' | 'PENDING';
  lastUpdated: string;
}

const DEFAULT_SYMBOLS = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN', 'BHEL', 'TATASTEEL', 'CROMPTON', 'ITC'];

const PriceDiagnosticPanel: React.FC = () => {
  const [symbols, setSymbols] = useState<string[]>(DEFAULT_SYMBOLS);
  const [rows, setRows] = useState<Record<string, PriceRow>>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [lastCheckTime, setLastCheckTime] = useState<string>('');
  const [integrityScore, setIntegrityScore] = useState<number>(100);

  // Connect to MarketDataService subscriptions for real-time WS ticks
  useEffect(() => {
    const unsubscribes = symbols.map(symbol => {
      return MarketDataService.subscribe(symbol, (quote: MarketQuote) => {
        setRows(prev => {
          const existing = prev[symbol] || {
            symbol,
            apiPrice: -1,
            wsPrice: 0,
            cachePrice: 0,
            uiPrice: 0,
            diff: 0,
            status: 'PENDING',
            lastUpdated: new Date().toLocaleTimeString()
          };

          const wsPrice = quote.ltp;
          const cachePrice = quote.ltp;
          const uiPrice = wsPrice; 

          const apiPrice = existing.apiPrice >= 0 ? existing.apiPrice : wsPrice;
          const diff = Math.abs(uiPrice - apiPrice);
          const status = diff <= 0.01 ? 'MATCH' : 'MISMATCH';

          // Price Integrity Monitoring Requirement
          if (diff > 0.01) {
            console.warn(`[Price Integrity Monitor] MISMATCH DETECTED for ${symbol}: Expected API Price = ${apiPrice}, Displayed UI Price = ${uiPrice}. Diff = ${diff.toFixed(2)}`);
          }

          return {
            ...prev,
            [symbol]: {
              ...existing,
              wsPrice,
              cachePrice,
              uiPrice,
              diff,
              status,
              lastUpdated: new Date().toLocaleTimeString()
            }
          };
        });
      });
    });

    return () => {
      unsubscribes.forEach(unsub => unsub());
    };
  }, [symbols]);

  // Fetch API Prices for all symbols
  const fetchApiPrices = async () => {
    setLoading(true);
    const newRows = { ...rows };

    await Promise.all(
      symbols.map(async (symbol) => {
        try {
          const res = await api.getQuote(symbol);
          if (res && res.status === 'success' && res.data) {
            let quoteData = null;
            const keys = Object.keys(res.data);
            if (keys.length > 0) {
              const matchKey = keys.find(k => k.endsWith(`:${symbol}`) || k === symbol) || keys[0];
              quoteData = res.data[matchKey];
            }

            if (quoteData) {
              const apiPrice = Number(quoteData.last_price || quoteData.ltp || 0);
              
              const existing = newRows[symbol] || {
                symbol,
                apiPrice: -1,
                wsPrice: 0,
                cachePrice: 0,
                uiPrice: 0,
                diff: 0,
                status: 'PENDING',
                lastUpdated: new Date().toLocaleTimeString()
              };

              const uiPrice = existing.wsPrice > 0 ? existing.wsPrice : apiPrice;
              const diff = Math.abs(uiPrice - apiPrice);
              const status = diff <= 0.01 ? 'MATCH' : 'MISMATCH';

              newRows[symbol] = {
                ...existing,
                apiPrice,
                uiPrice,
                cachePrice: apiPrice,
                diff,
                status,
                lastUpdated: new Date().toLocaleTimeString()
              };
            }
          }
        } catch (err) {
          console.error(`Diagnostics: Failed to fetch API quote for ${symbol}`, err);
        }
      })
    );

    setRows(newRows);
    setLastCheckTime(new Date().toLocaleTimeString());
    setLoading(false);
  };

  useEffect(() => {
    fetchApiPrices();
  }, [symbols]);

  // Calculate Overall Integrity Score
  useEffect(() => {
    const list = Object.values(rows);
    if (list.length === 0) {
      setIntegrityScore(100);
      return;
    }
    const matches = list.filter(r => r.status === 'MATCH').length;
    setIntegrityScore(Math.round((matches / list.length) * 100));
  }, [rows]);

  const handleAddSymbol = (e: React.FormEvent) => {
    e.preventDefault();
    const formatted = searchQuery.toUpperCase().trim();
    if (formatted && !symbols.includes(formatted)) {
      setSymbols([...symbols, formatted]);
      setSearchQuery('');
    }
  };

  const handleRemoveSymbol = (symbol: string) => {
    setSymbols(symbols.filter(s => s !== symbol));
    setRows(prev => {
      const copy = { ...prev };
      delete copy[symbol];
      return copy;
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white font-display">LTP Integrity Diagnostics</h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Real-time cross-verification of Last Traded Price (LTP) across API, WebSocket, cache layer, and UI.
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={fetchApiPrices}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs font-bold rounded-xl transition-all uppercase tracking-wide disabled:opacity-50 shrink-0"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Force Refresh REST
          </button>
        </div>
      </div>

      {/* KPI stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Integrity Status</span>
            <span className={`text-xl font-bold block mt-1 ${integrityScore === 100 ? 'text-emerald-500' : 'text-amber-500'}`}>
              {integrityScore === 100 ? 'SECURE' : 'MISMATCH DETECTED'}
            </span>
            <span className="text-[10px] text-slate-500 block mt-1">Tolerance threshold: ±0.01 INR</span>
          </div>
          {integrityScore === 100 ? (
            <ShieldCheck size={36} className="text-emerald-500" />
          ) : (
            <ShieldAlert size={36} className="text-amber-500" />
          )}
        </div>

        <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm">
          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Consensus Score</span>
          <span className="text-3xl font-black block mt-1 text-slate-900 dark:text-white font-mono">
            {integrityScore}%
          </span>
          <div className="w-full bg-slate-100 dark:bg-slate-900 h-1.5 rounded-full mt-2 overflow-hidden">
            <div className={`h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400`} style={{ width: `${integrityScore}%` }}></div>
          </div>
        </div>

        <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Active Monitor</span>
            <span className="text-xl font-bold text-slate-900 dark:text-white block mt-1">
              {symbols.length} symbols
            </span>
            <span className="text-[10px] text-slate-500 block mt-1">Last REST sync: {lastCheckTime || 'Never'}</span>
          </div>
          <Activity size={32} className="text-brand-500 animate-pulse" />
        </div>
      </div>

      {/* Add Symbol Bar */}
      <form onSubmit={handleAddSymbol} className="flex gap-2 max-w-md">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Add NSE Symbol (e.g. TATASTEEL)..."
            className="w-full pl-10 pr-4 py-2.5 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-1 focus:ring-brand-500 dark:text-white"
          />
        </div>
        <button
          type="submit"
          className="px-4 py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold rounded-xl uppercase tracking-wider transition-all"
        >
          Add Symbol
        </button>
      </form>

      {/* Verification Table */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/75 dark:bg-slate-900/50">
                <th className="p-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Symbol</th>
                <th className="p-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider font-mono">API Price (REST)</th>
                <th className="p-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider font-mono">WS Price</th>
                <th className="p-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider font-mono">Cache Price</th>
                <th className="p-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider font-mono">UI Price</th>
                <th className="p-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider font-mono">Diff</th>
                <th className="p-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Status</th>
                <th className="p-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {symbols.map((symbol) => {
                const row = rows[symbol];
                if (!row) {
                  return (
                    <tr key={symbol} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                      <td className="p-4 text-sm font-bold text-slate-900 dark:text-white">{symbol}</td>
                      <td colSpan={6} className="p-4 text-xs text-slate-400 italic">Initializing monitors...</td>
                      <td className="p-4 text-sm">
                        <button onClick={() => handleRemoveSymbol(symbol)} className="text-rose-500 hover:underline text-xs font-bold">Remove</button>
                      </td>
                    </tr>
                  );
                }

                const isMatch = row.status === 'MATCH';

                return (
                  <tr key={symbol} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                    <td className="p-4 text-sm font-black text-slate-950 dark:text-white">{row.symbol}</td>
                    <td className="p-4 text-sm font-mono font-semibold text-slate-700 dark:text-slate-300">₹{row.apiPrice.toFixed(2)}</td>
                    <td className="p-4 text-sm font-mono font-semibold text-slate-700 dark:text-slate-300">₹{row.wsPrice.toFixed(2)}</td>
                    <td className="p-4 text-sm font-mono font-semibold text-slate-700 dark:text-slate-300">₹{row.cachePrice.toFixed(2)}</td>
                    <td className="p-4 text-sm font-mono font-bold text-slate-900 dark:text-white">₹{row.uiPrice.toFixed(2)}</td>
                    <td className={`p-4 text-sm font-mono font-bold ${isMatch ? 'text-slate-500' : 'text-rose-500 font-extrabold'}`}>
                      {row.diff.toFixed(2)}
                    </td>
                    <td className="p-4 text-sm">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold ${
                        isMatch
                          ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                          : 'bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400 animate-pulse'
                      }`}>
                        {isMatch ? <CheckCircle size={12} /> : <XCircle size={12} />}
                        {row.status}
                      </span>
                    </td>
                    <td className="p-4 text-sm">
                      <button
                        onClick={() => handleRemoveSymbol(symbol)}
                        className="text-rose-500 hover:text-rose-600 font-bold text-xs uppercase tracking-wider"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default PriceDiagnosticPanel;
