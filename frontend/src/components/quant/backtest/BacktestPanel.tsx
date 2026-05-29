import React from 'react';
import { Play, DollarSign, TrendingUp, Shield, Percent } from 'lucide-react';
import { useQuantContext } from '../../../contexts/QuantContext';
import KpiCard from '../shared/KpiCard';
import EmptyState from '../shared/EmptyState';
import QuantAreaChart from '../charts/QuantAreaChart';
import DataTable, { DataTableColumn } from '../shared/DataTable';
import { Trade } from '../../../types/quant';

const fmt = (n: number, decimals = 2) => n.toFixed(decimals);
const fmtCcy = (n: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

/**
 * Backtest Mode Panel — KPI cards, equity & drawdown charts, trade log table.
 */
const BacktestPanel: React.FC = () => {
  const { backtestData, backtestRecharts } = useQuantContext();

  if (!backtestData) {
    return (
      <EmptyState
        icon={<Play size={48} />}
        title="No Backtest Results"
        description="Configure your strategy and parameters in the left panel, then click 'Run Backtest'."
      />
    );
  }

  const m = backtestData;

  const tradeColumns: DataTableColumn<Trade>[] = [
    { key: 'entry_time', label: 'Entry', render: t => t.entry_time?.slice(0, 10) },
    { key: 'exit_time',  label: 'Exit',  render: t => t.exit_time?.slice(0, 10) },
    { key: 'entry_price', label: 'Entry ₹', render: t => fmt(t.entry_price) },
    { key: 'exit_price',  label: 'Exit ₹',  render: t => fmt(t.exit_price) },
    { key: 'quantity', label: 'Qty', align: 'right' },
    {
      key: 'pnl',
      label: 'PnL',
      align: 'right',
      render: t => (
        <span className={t.pnl >= 0 ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>
          {t.pnl >= 0 ? '+' : ''}{fmt(t.pnl)}
        </span>
      ),
    },
    {
      key: 'pnl_percent',
      label: 'PnL %',
      align: 'right',
      render: t => (
        <span className={t.pnl_percent >= 0 ? 'text-emerald-400' : 'text-red-400'}>
          {t.pnl_percent >= 0 ? '+' : ''}{fmt(t.pnl_percent)}%
        </span>
      ),
    },
    { key: 'holding_bars', label: 'Bars', align: 'right' },
    { key: 'exit_reason', label: 'Reason', render: t => (
      <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-slate-800 text-slate-400">{t.exit_reason || '—'}</span>
    )},
  ];

  return (
    <div className="space-y-5">
      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-3">
        <KpiCard
          label="Total PnL"
          value={fmtCcy(m.total_pnl)}
          color={m.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}
          subtitle={`${m.total_return_pct >= 0 ? '+' : ''}${fmt(m.total_return_pct)}% return`}
          icon={<DollarSign size={14} />}
        />
        <KpiCard
          label="CAGR"
          value={`${fmt(m.cagr)}%`}
          color="text-brand-400"
          subtitle="Annual growth rate"
        />
        <KpiCard
          label="Sharpe"
          value={fmt(m.sharpe_ratio)}
          color={m.sharpe_ratio >= 1 ? 'text-emerald-400' : m.sharpe_ratio >= 0.5 ? 'text-amber-400' : 'text-red-400'}
          subtitle={`Sortino: ${fmt(m.sortino_ratio)}`}
        />
        <KpiCard
          label="Max Drawdown"
          value={`${fmt(m.max_drawdown_pct)}%`}
          color={m.max_drawdown_pct < 15 ? 'text-amber-400' : 'text-red-400'}
          subtitle={`Calmar: ${fmt(m.calmar_ratio)}`}
          icon={<Shield size={14} />}
        />
        <KpiCard
          label="Win Rate"
          value={`${fmt(m.win_rate)}%`}
          color={m.win_rate >= 50 ? 'text-emerald-400' : 'text-amber-400'}
          subtitle={`${m.winning_trades}W / ${m.losing_trades}L of ${m.total_trades}`}
          icon={<Percent size={14} />}
        />
      </div>

      {/* Secondary KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard label="Profit Factor" value={fmt(m.profit_factor)} color={m.profit_factor >= 1.5 ? 'text-emerald-400' : 'text-amber-400'} />
        <KpiCard label="Expectancy" value={`₹${fmt(m.expectancy)}`} color={m.expectancy >= 0 ? 'text-brand-400' : 'text-red-400'} />
        <KpiCard label="Avg Win" value={`₹${fmt(m.avg_win)}`} color="text-emerald-400" />
        <KpiCard label="Avg Loss" value={`₹${fmt(m.avg_loss)}`} color="text-red-400" />
      </div>

      {/* Equity Curve */}
      {backtestRecharts.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <TrendingUp size={12} /> Equity Curve
            </h3>
            <div className="text-xs font-black text-emerald-400">
              {fmtCcy(m.final_capital)} final
            </div>
          </div>
          <QuantAreaChart
            data={backtestRecharts}
            dataKey="equity"
            color="#10b981"
            gradientId="eqGrad"
            height={200}
            tooltipFormatter={v => [fmtCcy(v as number), 'Equity']}
          />
        </div>
      )}

      {/* Drawdown Chart */}
      {backtestRecharts.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Shield size={12} /> Drawdown
          </h3>
          <QuantAreaChart
            data={backtestRecharts}
            dataKey="drawdown"
            color="#ef4444"
            gradientId="ddGrad"
            height={120}
            yTickFormatter={v => `${v.toFixed(1)}%`}
            tooltipFormatter={v => [`${(v as number).toFixed(2)}%`, 'Drawdown']}
          />
        </div>
      )}

      {/* Trade Log */}
      {m.trades && m.trades.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Trade Log</h3>
            <span className="text-[10px] text-slate-600">{m.trades.length} trades</span>
          </div>
          <DataTable
            columns={tradeColumns}
            rows={m.trades}
            maxHeight="280px"
            keyExtractor={(t, i) => `${t.entry_time}-${i}`}
          />
        </div>
      )}
    </div>
  );
};

export default BacktestPanel;
