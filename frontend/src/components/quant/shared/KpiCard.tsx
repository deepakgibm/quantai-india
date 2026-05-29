import React from 'react';

interface KpiCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  /** Tailwind text color class e.g. 'text-emerald-400' */
  color?: string;
  icon?: React.ReactNode;
  /** Optional background accent class */
  accent?: string;
}

/**
 * Reusable institutional KPI metric card.
 * Used across Backtest, Walk-Forward, and Monte Carlo panels.
 */
const KpiCard: React.FC<KpiCardProps> = ({
  label,
  value,
  subtitle,
  color = 'text-white',
  icon,
  accent,
}) => (
  <div
    className={`relative bg-slate-900 border border-slate-800 rounded-xl p-4 text-center space-y-1.5 overflow-hidden transition-all duration-200 hover:border-slate-700 ${accent || ''}`}
  >
    {/* subtle glow accent top bar */}
    <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-slate-600 to-transparent opacity-50" />

    {icon && (
      <div className="flex justify-center mb-1 opacity-60">{icon}</div>
    )}

    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
      {label}
    </div>

    <div className={`text-xl font-black tabular-nums ${color}`}>
      {value}
    </div>

    {subtitle && (
      <div className="text-[10px] text-slate-600 font-semibold">{subtitle}</div>
    )}
  </div>
);

export default KpiCard;
