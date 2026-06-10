import React, { useState, useEffect } from 'react';
import { Briefcase, AlertTriangle, ShieldCheck, HelpCircle, Loader2, RefreshCw, Sparkles, TrendingDown } from 'lucide-react';
import { api } from '../services/api';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

const COLORS = ['#818cf8', '#34d399', '#fbbf24', '#f87171', '#c084fc', '#22d3ee'];

const PortfolioIntelligence: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPortfolioIntelligence = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getPortfolioIntelligence();
      if (response && response.status === 'success') {
        setData(response.analysis);
      } else {
        setError('Failed to fetch portfolio analysis');
      }
    } catch (e: any) {
      setError(e.message || 'Error communicating with analysis service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolioIntelligence();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 size={40} className="text-brand-500 animate-spin mb-4" />
        <p className="text-slate-400">Computing Portfolio Analytics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12 bg-rose-500/5 border border-rose-500/10 rounded-2xl p-6">
        <p className="text-rose-500 mb-4">{error}</p>
        <button onClick={fetchPortfolioIntelligence} className="px-4 py-2 bg-rose-500 text-white rounded-xl text-xs font-bold uppercase">Retry</button>
      </div>
    );
  }

  const {
    total_investment,
    total_value,
    pnl,
    pnl_percentage,
    health_score,
    diversification_score,
    risk_score,
    beta,
    risk_level,
    drawdown,
    allocations,
    recommendations
  } = data;

  const isProfit = pnl >= 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white font-display">Portfolio Intelligence Center</h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Analyze risk metrics, sector allocation, drawdown ratios, and review AI adjustments.
          </p>
        </div>
        <button
          onClick={fetchPortfolioIntelligence}
          className="flex items-center gap-2 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs font-bold rounded-xl transition-all uppercase tracking-wide shrink-0"
        >
          <RefreshCw size={13} /> Re-Compute
        </button>
      </div>

      {/* Main KPI Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm">
          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Portfolio Net Value</span>
          <span className="text-xl font-bold text-slate-900 dark:text-white font-mono block mt-2">
            ₹{total_value?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </span>
          <span className={`text-[10px] font-bold inline-flex items-center mt-1.5 ${isProfit ? 'text-emerald-500' : 'text-rose-500'}`}>
            {isProfit ? '▲' : '▼'} {isProfit ? '+' : ''}{pnl_percentage?.toFixed(2)}% (₹{pnl?.toLocaleString('en-IN', { maximumFractionDigits: 0 })})
          </span>
        </div>

        <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm">
          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Portfolio Health Score</span>
          <span className={`text-2xl font-black block mt-2 ${
            health_score >= 80 ? 'text-emerald-400' : health_score >= 50 ? 'text-amber-400' : 'text-rose-400'
          }`}>{health_score}/100</span>
          <div className="w-full bg-slate-100 dark:bg-slate-900 h-1.5 rounded-full mt-2.5 overflow-hidden">
            <div className={`h-full rounded-full ${
              health_score >= 80 ? 'bg-emerald-400' : health_score >= 50 ? 'bg-amber-400' : 'bg-rose-400'
            }`} style={{ width: `${health_score}%` }}></div>
          </div>
        </div>

        <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm">
          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Portfolio Beta (Risk)</span>
          <span className="text-xl font-bold text-slate-900 dark:text-white mt-2 block font-mono">
            {beta?.toFixed(2)}
          </span>
          <span className={`text-[10px] font-bold block mt-1.5 ${
            risk_level === 'HIGH' ? 'text-rose-500' : risk_level === 'LOW' ? 'text-emerald-500' : 'text-amber-500'
          }`}>{risk_level} RISK PROFILE</span>
        </div>

        <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm">
          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Peak Drawdown</span>
          <span className="text-xl font-bold text-slate-900 dark:text-white mt-2 block font-mono">
            -{drawdown?.toFixed(1)}%
          </span>
          <span className="text-[10px] text-slate-500 block mt-1.5">Max decline over 60D</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sector Allocation pie chart */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
          <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4 flex items-center gap-2">
            <Briefcase size={16} className="text-brand-500" /> Sector Allocations
          </h3>
          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={allocations}
                  dataKey="value"
                  nameKey="sector"
                  cx="50%"
                  cy="50%"
                  outerRadius={65}
                  fill="#8884d8"
                >
                  {allocations.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: any) => `₹${value.toLocaleString()}`} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-1.5 mt-4">
            {allocations.map((a: any, index: number) => (
              <div key={a.sector} className="flex items-center justify-between text-xs font-semibold">
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                  <span className="text-slate-500 dark:text-slate-300">{a.sector}</span>
                </div>
                <span className="font-mono text-slate-800 dark:text-slate-200">{a.percentage.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Drawdown & diversification bar chart */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-sm text-slate-800 dark:text-white flex items-center gap-2">
              <TrendingDown size={16} className="text-brand-500" /> Sector Value Exposure
            </h3>
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Sector Concentration</span>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={allocations} margin={{ left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:hidden" />
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" className="hidden dark:block" />
                <XAxis dataKey="sector" fontSize={10} stroke="#64748b" tickLine={false} />
                <YAxis fontSize={10} stroke="#64748b" tickLine={false} />
                <Tooltip formatter={(value: any) => `₹${value.toLocaleString()}`} />
                <Bar dataKey="value" fill="#818cf8" radius={[4, 4, 0, 0]}>
                  {allocations.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* AI Recommendations Panel */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 border border-brand-500/20 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-brand-500/10 rounded-full blur-3xl"></div>
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="text-brand-400" size={18} />
          <h3 className="text-white font-bold text-sm tracking-wide">AI Copilot Portfolio Recommendations</h3>
        </div>
        <div className="space-y-3">
          {recommendations.map((rec: string, index: number) => (
            <div
              key={index}
              className="flex items-start gap-3 bg-white/5 border border-white/5 rounded-xl p-4 text-slate-300 text-xs leading-relaxed"
            >
              <div className="w-5 h-5 rounded-full bg-brand-500/20 text-brand-400 flex items-center justify-center font-bold text-[10px] shrink-0">
                {index + 1}
              </div>
              <p className="font-medium">{rec}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default PortfolioIntelligence;
