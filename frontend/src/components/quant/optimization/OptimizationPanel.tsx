import React from 'react';
import { Sliders, CheckCircle } from 'lucide-react';
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ZAxis,
} from 'recharts';
import { useQuantContext } from '../../../contexts/QuantContext';
import KpiCard from '../shared/KpiCard';
import EmptyState from '../shared/EmptyState';
import DataTable, { DataTableColumn, TOOLTIP_STYLE } from '../shared/DataTable';
import { OptimizationRun } from '../../../types/quant';

const fmt = (n: number, d = 2) => n.toFixed(d);

/**
 * Optimization Mode Panel — best parameter HUD, scatter plot, full combinations table.
 */
const OptimizationPanel: React.FC = () => {
  const { optimizationData, optimizationScatterData, setStrategyParams, setActiveMode } = useQuantContext();

  if (!optimizationData) {
    return (
      <EmptyState
        icon={<Sliders size={48} />}
        title="No Optimization Sweeps Run"
        description="Define parameter ranges in the left panel, then click 'Run Parameter Sweep' to find the optimal configuration."
      />
    );
  }

  const best = optimizationData.best_run;

  const allRunColumns: DataTableColumn<OptimizationRun>[] = [
    {
      key: 'params',
      label: 'Parameters',
      render: r => (
        <span className="text-[9px] font-mono text-slate-400">
          {Object.entries(r.params).map(([k, v]) => `${k}:${v}`).join(' · ')}
        </span>
      ),
    },
    {
      key: 'metrics.total_return_pct',
      label: 'Return',
      align: 'right',
      render: r => (
        <span className={r.metrics.total_return_pct >= 0 ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>
          {r.metrics.total_return_pct >= 0 ? '+' : ''}{fmt(r.metrics.total_return_pct)}%
        </span>
      ),
    },
    { key: 'metrics.sharpe_ratio', label: 'Sharpe', align: 'right', render: r => fmt(r.metrics.sharpe_ratio) },
    { key: 'metrics.max_drawdown_pct', label: 'Max DD', align: 'right', render: r => `${fmt(r.metrics.max_drawdown_pct)}%` },
    { key: 'metrics.win_rate', label: 'Win %', align: 'right', render: r => `${fmt(r.metrics.win_rate)}%` },
    { key: 'metrics.profit_factor', label: 'PF', align: 'right', render: r => fmt(r.metrics.profit_factor) },
    {
      key: 'action',
      label: '',
      align: 'right',
      render: r => (
        <button
          onClick={() => { setStrategyParams(r.params); setActiveMode('backtest'); }}
          className="text-[9px] text-brand-400 font-bold hover:text-brand-300 uppercase border border-brand-900/40 px-2 py-0.5 rounded hover:bg-brand-900/20 transition-colors"
        >
          Load Mix
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      {/* Stats bar */}
      <div className="flex items-center gap-4 text-xs text-slate-500">
        <span className="font-bold text-white">{optimizationData.total_runs}</span> combinations tested
        <span>·</span>
        <span className="font-bold text-white">{fmt(optimizationData.duration_seconds, 1)}s</span> elapsed
      </div>

      {/* Best combination HUD */}
      <div className="bg-gradient-to-br from-brand-950/60 to-purple-950/60 border border-brand-800/40 rounded-xl p-5 space-y-3">
        <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
          <CheckCircle size={16} /> Optimal Parameter Configuration
        </div>
        <div className="flex flex-wrap gap-2">
          {Object.entries(best.params).map(([k, v]) => (
            <div key={k} className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5">
              <div className="text-[9px] text-slate-500 uppercase">{k}</div>
              <div className="text-white font-black text-sm">{v}</div>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-3 gap-3 pt-1">
          <KpiCard
            label="Best Return"
            value={`${fmt(best.metrics.total_return_pct)}%`}
            color={best.metrics.total_return_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}
          />
          <KpiCard
            label="Best Sharpe"
            value={fmt(best.metrics.sharpe_ratio)}
            color="text-brand-400"
          />
          <KpiCard
            label="Max Drawdown"
            value={`${fmt(best.metrics.max_drawdown_pct)}%`}
            color="text-amber-400"
          />
        </div>
        <button
          onClick={() => { setStrategyParams(best.params); setActiveMode('backtest'); }}
          className="w-full py-2 px-4 text-xs font-bold text-white bg-gradient-to-r from-brand-600 to-purple-600 hover:from-brand-500 hover:to-purple-500 rounded-lg transition-all uppercase tracking-wider"
        >
          Load Optimal Config → Run Backtest
        </button>
      </div>

      {/* Scatter plot */}
      {optimizationScatterData.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Parameter Space — Sharpe vs Return
          </h3>
          <ResponsiveContainer width="100%" height={240}>
            <ScatterChart margin={{ top: 5, right: 10, bottom: 20, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                dataKey="xVal"
                type="number"
                tick={{ fill: '#475569', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                label={{ value: 'Param 1', position: 'insideBottom', offset: -12, fill: '#475569', fontSize: 10 }}
              />
              <YAxis
                dataKey="sharpe"
                type="number"
                tick={{ fill: '#475569', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                label={{ value: 'Sharpe', angle: -90, position: 'insideLeft', offset: 10, fill: '#475569', fontSize: 10 }}
              />
              <ZAxis dataKey="return" range={[40, 200]} />
              <Tooltip
                contentStyle={{ ...TOOLTIP_STYLE, borderRadius: 8, fontSize: 11 }}
                cursor={{ strokeDasharray: '3 3', stroke: '#334155' }}
                content={({ active, payload }) => {
                  if (active && payload?.length) {
                    const d = payload[0].payload;
                    return (
                      <div style={{ ...TOOLTIP_STYLE, borderRadius: 8, padding: '8px 12px', border: '1px solid #1e293b' }}>
                        <p className="text-slate-300 text-[10px] mb-1">{d.name}</p>
                        <p className="text-brand-400 text-xs font-bold">Sharpe: {fmt(d.sharpe)}</p>
                        <p className="text-emerald-400 text-xs">Return: {fmt(d.return)}%</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Scatter
                data={optimizationScatterData}
                fill="#6366f1"
                fillOpacity={0.75}
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* All combinations table */}
      {optimizationData.all_runs.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">All Combinations</h3>
            <span className="text-[10px] text-slate-600">{optimizationData.all_runs.length} results</span>
          </div>
          <DataTable
            columns={allRunColumns}
            rows={optimizationData.all_runs}
            maxHeight="300px"
          />
        </div>
      )}
    </div>
  );
};

export default OptimizationPanel;
