import React, { useState, useEffect } from 'react';
import { Play, DollarSign, TrendingUp, Shield, Percent, Loader2, CheckCircle2 } from 'lucide-react';
import { useQuantContext } from '../../../contexts/QuantContext';
import KpiCard from '../shared/KpiCard';
import EmptyState from '../shared/EmptyState';
import QuantAreaChart from '../charts/QuantAreaChart';
import DataTable, { DataTableColumn } from '../shared/DataTable';
import { Trade } from '../../../types/quant';

const fmt = (n: number | null | undefined, decimals = 2) => 
  typeof n === 'number' && !isNaN(n) ? n.toFixed(decimals) : '—';
const fmtCcy = (n: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

/**
 * Backtest Mode Panel — KPI cards, equity & drawdown charts, trade log table.
 */
const BacktestPanel: React.FC = () => {
  const { backtestData, backtestRecharts, loading } = useQuantContext();
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    if (loading) {
      setActiveStep(0);
      const timer1 = setTimeout(() => setActiveStep(1), 350);
      const timer2 = setTimeout(() => setActiveStep(2), 700);
      const timer3 = setTimeout(() => setActiveStep(3), 1050);
      return () => {
        clearTimeout(timer1);
        clearTimeout(timer2);
        clearTimeout(timer3);
      };
    }
  }, [loading]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[450px] bg-slate-900/40 border border-slate-800/80 rounded-2xl p-8 text-center backdrop-blur-sm relative overflow-hidden">
        {/* Glow effect */}
        <div className="absolute -top-40 -left-40 w-80 h-80 bg-blue-500/10 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute -bottom-40 -right-40 w-80 h-80 bg-violet-600/10 rounded-full blur-[100px] pointer-events-none" />

        <div className="relative mb-6">
          <div className="w-16 h-16 rounded-full border-4 border-slate-800 border-t-blue-500 animate-spin"></div>
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 className="w-6 h-6 text-blue-400 animate-pulse" />
          </div>
        </div>

        <div className="space-y-2 mb-8">
          <h3 className="text-base font-bold text-white tracking-wide">Executing Backtest Simulation</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Processing database candles, preloading technical indicators, evaluating strategy rules, and simulating bar-by-bar executions.
          </p>
        </div>

        {/* Stage Progress Tracker */}
        <div className="w-full max-w-xs bg-slate-950/80 border border-slate-800/80 rounded-xl p-4 space-y-4 text-left shadow-2xl relative z-10">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Simulation Steps</span>
            <span className="text-[10px] font-bold text-blue-400">{Math.round(((activeStep + 1) / 4) * 100)}%</span>
          </div>
          
          <div className="space-y-2.5">
            <div className="flex items-center gap-3">
              {activeStep > 0 ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              ) : activeStep === 0 ? (
                <Loader2 className="w-4 h-4 text-blue-400 animate-spin flex-shrink-0" />
              ) : (
                <div className="w-4 h-4 rounded-full border border-slate-700 flex-shrink-0" />
              )}
              <span className={`text-xs font-medium ${activeStep >= 0 ? 'text-white' : 'text-slate-500'}`}>
                Loading EOD Candles from DB
              </span>
            </div>

            <div className="flex items-center gap-3">
              {activeStep > 1 ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              ) : activeStep === 1 ? (
                <Loader2 className="w-4 h-4 text-blue-400 animate-spin flex-shrink-0" />
              ) : (
                <div className="w-4 h-4 rounded-full border border-slate-700 flex-shrink-0" />
              )}
              <span className={`text-xs font-medium ${activeStep >= 1 ? 'text-white' : 'text-slate-500'}`}>
                Preloading Technical Indicators
              </span>
            </div>

            <div className="flex items-center gap-3">
              {activeStep > 2 ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              ) : activeStep === 2 ? (
                <Loader2 className="w-4 h-4 text-blue-400 animate-spin flex-shrink-0" />
              ) : (
                <div className="w-4 h-4 rounded-full border border-slate-700 flex-shrink-0" />
              )}
              <span className={`text-xs font-medium ${activeStep >= 2 ? 'text-white' : 'text-slate-500'}`}>
                Running Strategy Crossover Signals
              </span>
            </div>

            <div className="flex items-center gap-3">
              {activeStep > 3 ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              ) : activeStep === 3 ? (
                <Loader2 className="w-4 h-4 text-blue-400 animate-spin flex-shrink-0" />
              ) : (
                <div className="w-4 h-4 rounded-full border border-slate-700 flex-shrink-0" />
              )}
              <span className={`text-xs font-medium ${activeStep >= 3 ? 'text-white' : 'text-slate-500'}`}>
                Compiling Portfolio MTM & Metrics
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

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
