import React from 'react';
import { Grid, RefreshCw, AlertTriangle, CheckCircle, Play } from 'lucide-react';
import { useQuantContext } from '../../../contexts/QuantContext';
import KpiCard from '../shared/KpiCard';
import EmptyState from '../shared/EmptyState';

/**
 * Discovery Mode Panel — multi-strategy parallel scan and ranking.
 */
const DiscoveryPanel: React.FC = () => {
  const { strategies, discoveryScans, setSelectedStrategyId, setActiveMode } = useQuantContext();
  const hasAnyResults = Object.values(discoveryScans).some(s => !s.loading && (s.metrics || s.error));

  if (!hasAnyResults && Object.keys(discoveryScans).length === 0) {
    return (
      <EmptyState
        icon={<Grid size={48} />}
        title="Strategy Discovery Lab"
        description="Scan all registered strategies on the selected symbol to surface the highest-performing candidates."
      />
    );
  }

  // Sort by Sharpe ratio descending (scanned strategies first)
  const sorted = strategies
    .map(s => ({ strat: s, scan: discoveryScans[s.id] }))
    .sort((a, b) => {
      const aS = a.scan?.metrics?.sharpe_ratio ?? -Infinity;
      const bS = b.scan?.metrics?.sharpe_ratio ?? -Infinity;
      return bS - aS;
    });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-white font-bold text-base">Strategy Discovery Lab</h2>
          <p className="text-slate-500 text-xs mt-0.5">
            {sorted.filter(s => s.scan?.metrics).length} of {strategies.length} strategies scanned
          </p>
        </div>
        {hasAnyResults && (
          <div className="flex items-center gap-2 text-xs text-emerald-400 font-bold">
            <CheckCircle size={14} />
            Scan Complete
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {sorted.map(({ strat, scan }, rank) => {
          const isLoading = scan?.loading;
          const hasMetrics = !!scan?.metrics;
          const m = scan?.metrics;
          const isTopPick = rank === 0 && hasMetrics;

          return (
            <div
              key={strat.id}
              className={`bg-slate-900 border rounded-xl p-4 space-y-3 transition-all duration-200 ${
                isTopPick
                  ? 'border-emerald-600/50 shadow-lg shadow-emerald-600/10'
                  : 'border-slate-800 hover:border-slate-700'
              }`}
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-2">
                <div>
                  {isTopPick && (
                    <div className="text-[9px] font-bold text-emerald-400 uppercase tracking-widest mb-1">
                      ★ Top Performer
                    </div>
                  )}
                  <div className="text-white font-bold text-sm truncate">{strat.name}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">{strat.category}</div>
                </div>
                {isLoading && <RefreshCw size={14} className="text-slate-500 animate-spin shrink-0 mt-1" />}
                {scan?.error && <AlertTriangle size={14} className="text-red-500 shrink-0 mt-1" />}
              </div>

              {/* Metrics */}
              {hasMetrics && m && (
                <div className="grid grid-cols-3 gap-2">
                  <KpiCard
                    label="Return"
                    value={`${m.total_return_pct >= 0 ? '+' : ''}${m.total_return_pct.toFixed(1)}%`}
                    color={m.total_return_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}
                  />
                  <KpiCard
                    label="Sharpe"
                    value={m.sharpe_ratio.toFixed(2)}
                    color={m.sharpe_ratio >= 1 ? 'text-brand-400' : 'text-slate-300'}
                  />
                  <KpiCard
                    label="Max DD"
                    value={`${m.max_drawdown_pct.toFixed(1)}%`}
                    color={m.max_drawdown_pct < 15 ? 'text-amber-400' : 'text-red-400'}
                  />
                </div>
              )}

              {scan?.error && (
                <p className="text-[10px] text-red-400 bg-red-950/40 rounded p-2">{scan.error}</p>
              )}

              {isLoading && (
                <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-brand-500 to-purple-500 animate-pulse w-2/3 rounded-full" />
                </div>
              )}

              {/* Load action */}
              {hasMetrics && (
                <button
                  onClick={() => { setSelectedStrategyId(strat.id); setActiveMode('backtest'); }}
                  className="w-full py-1.5 px-3 text-[10px] font-bold text-brand-400 border border-brand-900/50 rounded-lg hover:bg-brand-900/20 transition-colors flex items-center justify-center gap-1.5 uppercase"
                >
                  <Play size={10} /> Load in Backtester
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default DiscoveryPanel;
