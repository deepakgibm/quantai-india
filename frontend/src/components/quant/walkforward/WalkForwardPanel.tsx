import React from 'react';
import { TrendingUp, CheckCircle, AlertTriangle } from 'lucide-react';
import { useQuantContext } from '../../../contexts/QuantContext';
import KpiCard from '../shared/KpiCard';
import EmptyState from '../shared/EmptyState';
import QuantAreaChart from '../charts/QuantAreaChart';
import DataTable, { DataTableColumn } from '../shared/DataTable';
import { WalkForwardWindow } from '../../../types/quant';

const fmt = (n: number, d = 2) => n.toFixed(d);

/**
 * Walk-Forward Mode Panel — validation status, IS/OOS summary KPIs,
 * stitched OOS equity curve, rolling window results table.
 */
const WalkForwardPanel: React.FC = () => {
  const { walkForwardData } = useQuantContext();

  if (!walkForwardData) {
    return (
      <EmptyState
        icon={<TrendingUp size={48} />}
        title="No Walk-Forward Results"
        description="Define parameter sweep ranges in the left panel, then click 'Run Walk-Forward' to validate strategy robustness across rolling IS/OOS windows."
      />
    );
  }

  const { summary, validation_passed, validation_messages, window_results, equity_curve } = walkForwardData;

  const windowColumns: DataTableColumn<WalkForwardWindow>[] = [
    { key: 'window_id', label: '#', align: 'center', width: '40px' },
    { key: 'train_start', label: 'IS Start', render: w => w.train_start?.slice(0, 10) },
    { key: 'train_end',   label: 'IS End',   render: w => w.train_end?.slice(0, 10) },
    { key: 'test_start',  label: 'OOS Start', render: w => w.test_start?.slice(0, 10) },
    { key: 'test_end',    label: 'OOS End',   render: w => w.test_end?.slice(0, 10) },
    { key: 'is_sharpe',  label: 'IS Sharpe',  render: w => fmt(w.is_sharpe) },
    {
      key: 'oos_return',
      label: 'OOS Yield',
      align: 'right',
      render: w => (
        <span className={w.oos_return >= 0 ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>
          {w.oos_return >= 0 ? '+' : ''}{fmt(w.oos_return)}%
        </span>
      ),
    },
    { key: 'oos_sharpe',   label: 'OOS Sharpe', render: w => fmt(w.oos_sharpe) },
    { key: 'oos_drawdown', label: 'OOS DD',      render: w => `${fmt(w.oos_drawdown)}%` },
    { key: 'oos_trades',   label: 'Trades',      align: 'right' },
    {
      key: 'best_parameters',
      label: 'Best Params',
      render: w => (
        <span className="text-[9px] text-slate-500 font-mono">
          {Object.entries(w.best_parameters || {}).map(([k, v]) => `${k}:${v}`).join(', ') || '—'}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      {/* Validation status banner */}
      <div
        className={`flex items-start gap-3 p-4 rounded-xl border ${
          validation_passed
            ? 'bg-emerald-950/40 border-emerald-800/50 text-emerald-400'
            : 'bg-amber-950/40 border-amber-800/50 text-amber-400'
        }`}
      >
        {validation_passed ? <CheckCircle size={18} className="shrink-0 mt-0.5" /> : <AlertTriangle size={18} className="shrink-0 mt-0.5" />}
        <div>
          <div className="font-bold text-sm">{validation_passed ? 'Strategy Validated' : 'Validation Warning'}</div>
          <ul className="mt-1 space-y-0.5">
            {validation_messages.map((msg, i) => (
              <li key={i} className="text-xs opacity-80">{msg}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard
          label="OOS Total Return"
          value={`${summary.total_return >= 0 ? '+' : ''}${fmt(summary.total_return)}%`}
          color={summary.total_return >= 0 ? 'text-emerald-400' : 'text-red-400'}
        />
        <KpiCard
          label="OOS Sharpe"
          value={fmt(summary.sharpe)}
          color={summary.sharpe >= 1 ? 'text-emerald-400' : 'text-amber-400'}
        />
        <KpiCard
          label="OOS Max Drawdown"
          value={`${fmt(summary.max_drawdown)}%`}
          color={summary.max_drawdown < 15 ? 'text-amber-400' : 'text-red-400'}
        />
        <KpiCard
          label="Stability Score"
          value={`${fmt(summary.parameter_stability_score * 100, 0)}%`}
          color={summary.parameter_stability_score >= 0.7 ? 'text-emerald-400' : 'text-amber-400'}
          subtitle={`${fmt(summary.profitable_windows_pct)}% profitable windows`}
        />
      </div>

      {/* OOS Equity Curve */}
      {equity_curve.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <TrendingUp size={12} /> Stitched OOS Equity Curve
          </h3>
          <QuantAreaChart
            data={equity_curve}
            dataKey="equity"
            color="#818cf8"
            gradientId="wfEqGrad"
            height={200}
          />
        </div>
      )}

      {/* Rolling Windows Table */}
      {window_results.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Rolling Window Results</h3>
            <span className="text-[10px] text-slate-600">{window_results.length} windows</span>
          </div>
          <DataTable
            columns={windowColumns}
            rows={window_results}
            maxHeight="300px"
            keyExtractor={w => w.window_id}
          />
        </div>
      )}
    </div>
  );
};

export default WalkForwardPanel;
