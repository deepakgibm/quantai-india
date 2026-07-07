import React from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart3, HelpCircle } from 'lucide-react';
import { useQuantContext } from '../../../contexts/QuantContext';
import SymbolSearch from '../../SymbolSearch';

const TIMEFRAMES = ['5m', '15m', '30m', '1H', '1D'];

/**
 * Workspace top header: branding, active terminal HUD, and global controls
 * (symbol, timeframe, date range, capital).
 */
const WorkspaceHeader: React.FC = () => {
  const navigate = useNavigate();
  const {
    selectedSymbol, setSelectedSymbol,
    timeframe, setTimeframe,
    startDate, setStartDate,
    endDate, setEndDate,
    capital, setCapital,
    activeStrategy,
  } = useQuantContext();

  return (
    <div className="bg-slate-900 border-b border-slate-800 px-6 py-4 relative overflow-hidden shrink-0">
      {/* Ambient glow effects */}
      <div className="absolute top-0 right-0 w-96 h-40 bg-brand-500/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-10 -left-10 w-64 h-40 bg-purple-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col xl:flex-row xl:items-center justify-between gap-4">
        {/* Brand + title */}
        <div className="flex items-center gap-4 shrink-0">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-brand-500 to-purple-600 shadow-lg shadow-brand-500/20">
            <BarChart3 size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-display font-black tracking-tight text-white">
              Quant Research Terminal
            </h1>
            <p className="text-slate-500 text-xs mt-0.5">
              Institutional-grade strategy discovery, backtesting & validation
            </p>
          </div>

          {/* Active context HUD */}
          <div className="hidden md:flex items-center gap-3 ml-4 bg-slate-950/60 px-4 py-2 rounded-lg border border-slate-800 backdrop-blur-sm">
            <div className="text-xs space-y-0.5">
              <div className="text-slate-600 font-semibold uppercase text-[10px]">Target</div>
              <div className="text-white font-bold flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                {selectedSymbol || '—'} · {timeframe}
              </div>
            </div>
            <div className="w-px h-8 bg-slate-800" />
            <div className="text-xs space-y-0.5">
              <div className="text-slate-600 font-semibold uppercase text-[10px]">Strategy</div>
              <div className="text-indigo-400 font-bold truncate max-w-[120px]">
                {activeStrategy?.name || '—'}
              </div>
            </div>
          </div>
        </div>

        {/* Global controls toolbar */}
        <div className="flex flex-wrap items-end gap-3">
          {/* Symbol */}
          <div className="min-w-[160px]">
            <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Symbol</label>
            <SymbolSearch
              selectedSymbols={selectedSymbol ? [selectedSymbol] : []}
              onSymbolsChange={syms => setSelectedSymbol(syms[0] || null)}
              timeframe={timeframe}
              maxSymbols={1}
            />
          </div>

          {/* Timeframe */}
          <div>
            <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Timeframe</label>
            <div className="flex gap-1">
              {TIMEFRAMES.map(tf => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-2.5 py-2 rounded-md text-xs font-bold transition-all ${
                    timeframe === tf
                      ? 'bg-brand-600 text-white shadow-lg shadow-brand-600/20'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {/* Date range */}
          <div>
            <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Date Range</label>
            <div className="flex gap-1.5 items-center">
              <input
                type="date"
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                className="px-2.5 py-2 rounded-md border border-slate-700 bg-slate-950 text-white text-xs outline-none focus:ring-1 focus:ring-brand-500"
              />
              <span className="text-slate-600 text-xs">→</span>
              <input
                type="date"
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                className="px-2.5 py-2 rounded-md border border-slate-700 bg-slate-950 text-white text-xs outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </div>

          {/* Capital */}
          <div>
            <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Capital</label>
            <div className="relative">
              <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 text-xs font-bold">₹</span>
              <input
                type="number"
                value={capital}
                onChange={e => setCapital(Number(e.target.value))}
                className="pl-6 pr-3 py-2 rounded-md border border-slate-700 bg-slate-950 text-white text-xs outline-none focus:ring-1 focus:ring-brand-500 w-28"
              />
            </div>
          </div>

          {/* Help Button */}
          <div className="flex items-center">
            <button
              onClick={() => navigate('/help')}
              className="p-2 bg-slate-850 hover:bg-slate-800 text-slate-400 hover:text-white rounded-md border border-slate-700 transition-all shadow-sm"
              title="Open Help Center & Documentation"
            >
              <HelpCircle size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WorkspaceHeader;
