import React from 'react';
import { Activity } from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { useQuantContext } from '../../../contexts/QuantContext';
import KpiCard from '../shared/KpiCard';
import EmptyState from '../shared/EmptyState';
import { TOOLTIP_STYLE } from '../shared/DataTable';

const fmt = (n: number, d = 2) => n.toFixed(d);
const fmtCcy = (n: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

/**
 * Monte Carlo Mode Panel — probability cones, risk-of-ruin metrics, fan chart.
 */
const MonteCarloPanel: React.FC = () => {
  const { monteCarloData, monteCarloChartData } = useQuantContext();

  if (!monteCarloData) {
    return (
      <EmptyState
        icon={<Activity size={48} />}
        title="No Monte Carlo Results"
        description="Run a Backtest first to generate trade returns, then click 'Run Monte Carlo' to simulate probability distributions."
      />
    );
  }

  const m = monteCarloData;

  return (
    <div className="space-y-5">
      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard
          label="Risk of Ruin"
          value={`${fmt(m.risk_of_ruin_probability * 100)}%`}
          color={m.risk_of_ruin_probability < 0.05 ? 'text-emerald-400' : m.risk_of_ruin_probability < 0.15 ? 'text-amber-400' : 'text-red-400'}
          subtitle="Probability of total loss"
        />
        <KpiCard
          label="Median Final Equity"
          value={fmtCcy(m.median_final_equity)}
          color="text-brand-400"
          subtitle="50th percentile outcome"
        />
        <KpiCard
          label="Worst-Case Drawdown"
          value={`${fmt(m.worst_case_drawdown)}%`}
          color="text-red-400"
          subtitle="Absolute worst path"
        />
        <KpiCard
          label="Avg Max Drawdown"
          value={`${fmt(m.average_max_drawdown)}%`}
          color={m.average_max_drawdown < 20 ? 'text-amber-400' : 'text-red-400'}
          subtitle={`Across ${m.num_simulations.toLocaleString()} simulations`}
        />
      </div>

      {/* Monte Carlo Fan Chart */}
      {monteCarloChartData.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Activity size={12} /> Probability Fan Chart
            </h3>
            <div className="flex items-center gap-3 text-[10px]">
              <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-emerald-500 inline-block"/> P95</span>
              <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-indigo-400 inline-block"/> Median</span>
              <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-red-500 inline-block"/> P5</span>
              <span className="flex items-center gap-1"><span className="w-3 h-px bg-slate-600 inline-block border-dashed border-t"/> Sample Paths</span>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={monteCarloChartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis
                dataKey="tradeIndex"
                tick={{ fill: '#475569', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                label={{ value: 'Trade #', position: 'insideBottom', offset: -4, fill: '#475569', fontSize: 10 }}
              />
              <YAxis
                tick={{ fill: '#475569', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`}
                width={52}
              />
              <Tooltip
                contentStyle={{ ...TOOLTIP_STYLE, borderRadius: 8, fontSize: 11 }}
                formatter={(v: any) => [fmtCcy(v), '']}
              />

              {/* Band fills */}
              <Line type="monotone" dataKey="upper95" stroke="#10b981" strokeWidth={2} dot={false} name="95th Pct" isAnimationActive={false} />
              <Line type="monotone" dataKey="median"  stroke="#818cf8" strokeWidth={2.5} dot={false} name="Median"   isAnimationActive={false} />
              <Line type="monotone" dataKey="lower5"  stroke="#ef4444" strokeWidth={2} dot={false} name="5th Pct"  isAnimationActive={false} />

              {/* Sample paths */}
              {[0, 1, 2].map(i => (
                <Line
                  key={i}
                  type="monotone"
                  dataKey={`path_${i}`}
                  stroke="#475569"
                  strokeWidth={1}
                  strokeDasharray="4 3"
                  dot={false}
                  name={`Path ${i + 1}`}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Interpretation */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[10px] text-slate-500">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3">
          <div className="font-bold text-slate-400 mb-1">🟢 Best Case (P95)</div>
          <div className="text-white font-black text-base">{fmtCcy(m.upper_95_percentile[m.upper_95_percentile.length - 1] ?? 0)}</div>
          <div>Top 5% of all simulation paths</div>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3">
          <div className="font-bold text-slate-400 mb-1">🔵 Expected (Median)</div>
          <div className="text-white font-black text-base">{fmtCcy(m.median_final_equity)}</div>
          <div>50% of paths exceed this value</div>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3">
          <div className="font-bold text-slate-400 mb-1">🔴 Worst Case (P5)</div>
          <div className="text-white font-black text-base">{fmtCcy(m.lower_5_percentile[m.lower_5_percentile.length - 1] ?? 0)}</div>
          <div>Bottom 5% of all simulation paths</div>
        </div>
      </div>
    </div>
  );
};

export default MonteCarloPanel;
