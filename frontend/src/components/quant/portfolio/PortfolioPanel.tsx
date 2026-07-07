import React from 'react';
import { Briefcase, Trash2, Plus } from 'lucide-react';
import { useQuantContext } from '../../../contexts/QuantContext';
import KpiCard from '../shared/KpiCard';
import EmptyState from '../shared/EmptyState';
import QuantAreaChart from '../charts/QuantAreaChart';

const fmt = (n: number | null | undefined, d = 2) => 
  typeof n === 'number' && !isNaN(n) ? n.toFixed(d) : '—';
const fmtCcy = (n: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

const PALETTE = ['#818cf8', '#10b981', '#f59e0b', '#ef4444', '#a855f7', '#22d3ee'];

/**
 * Portfolio Mode Panel — multi-strategy equity comparison and combined curve.
 */
const PortfolioPanel: React.FC = () => {
  const {
    portfolioData, removePortfolioItem, portfolioCombinedCurve,
    backtestData, addCurrentToPortfolio, activeStrategy, setActiveMode
  } = useQuantContext();

  if (portfolioData.length === 0) {
    return (
      <EmptyState
        icon={<Briefcase size={48} />}
        title="Portfolio Comparison Empty"
        description="Run backtests and click 'Add to Portfolio' to compare multiple strategies side-by-side."
        action={
          backtestData ? (
            <button
              onClick={addCurrentToPortfolio}
              className="flex items-center gap-2 px-4 py-2 text-xs font-bold text-white bg-gradient-to-r from-brand-600 to-purple-600 rounded-lg hover:from-brand-500 hover:to-purple-500 transition-all uppercase"
            >
              <Plus size={13} /> Add Current Backtest
            </button>
          ) : (
            <button
              onClick={() => setActiveMode('backtest')}
              className="flex items-center gap-2 px-4 py-2 text-xs font-bold text-brand-400 border border-brand-800/50 rounded-lg hover:bg-brand-900/20 transition-all"
            >
              Go to Backtest
            </button>
          )
        }
      />
    );
  }

  return (
    <div className="space-y-5">
      {/* Portfolio cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {portfolioData.map((entry, idx) => {
          const m = entry.result;
          const color = PALETTE[idx % PALETTE.length];
          return (
            <div
              key={idx}
              className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3 relative hover:border-slate-700 transition-all"
            >
              {/* Color accent */}
              <div className="absolute top-0 left-0 right-0 h-0.5 rounded-t-xl" style={{ backgroundColor: color }} />

              <div className="flex items-start justify-between">
                <div>
                  <div className="text-white font-bold text-sm">{entry.name}</div>
                  <div className="text-slate-500 text-[10px] mt-0.5">{entry.symbol}</div>
                </div>
                <button
                  onClick={() => removePortfolioItem(idx)}
                  className="p-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-950/30 transition-all"
                >
                  <Trash2 size={13} />
                </button>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <KpiCard
                  label="Return"
                  value={`${m.total_return_pct >= 0 ? '+' : ''}${fmt(m.total_return_pct)}%`}
                  color={m.total_return_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}
                />
                <KpiCard
                  label="Sharpe"
                  value={fmt(m.sharpe_ratio)}
                  color={m.sharpe_ratio >= 1 ? 'text-brand-400' : 'text-slate-300'}
                />
                <KpiCard
                  label="Max DD"
                  value={`${fmt(m.max_drawdown_pct)}%`}
                  color={m.max_drawdown_pct < 15 ? 'text-amber-400' : 'text-red-400'}
                />
              </div>

              {/* Mini equity sparkline */}
              {entry.result.equity_curve_recharts && (
                <QuantAreaChart
                  data={entry.result.equity_curve_recharts}
                  dataKey="equity"
                  color={color}
                  gradientId={`portGrad${idx}`}
                  height={80}
                  yTickFormatter={() => ''}
                  tooltipFormatter={v => [fmtCcy(v as number), 'Equity']}
                />
              )}
            </div>
          );
        })}

        {/* Add current backtest card */}
        {backtestData && (
          <button
            onClick={addCurrentToPortfolio}
            className="bg-slate-900/40 border border-dashed border-slate-700 rounded-xl p-4 flex flex-col items-center justify-center gap-2 text-slate-600 hover:text-slate-400 hover:border-slate-600 transition-all min-h-[180px]"
          >
            <Plus size={24} />
            <span className="text-xs font-semibold">Add Current Backtest</span>
            <span className="text-[10px]">{activeStrategy?.name}</span>
          </button>
        )}
      </div>

      {/* Combined portfolio equity curve */}
      {portfolioCombinedCurve.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Briefcase size={12} /> Combined Portfolio Equity
            </h3>
            <span className="text-[10px] text-slate-600">{portfolioData.length} strategies</span>
          </div>
          <QuantAreaChart
            data={portfolioCombinedCurve}
            dataKey="equity"
            color="#a855f7"
            gradientId="portCombined"
            height={220}
            tooltipFormatter={v => [fmtCcy(v as number), 'Total Equity']}
          />
        </div>
      )}
    </div>
  );
};

export default PortfolioPanel;
