import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { TOOLTIP_STYLE } from '../shared/DataTable';

interface QuantAreaChartProps {
  data: Record<string, any>[];
  dataKey: string;
  color: string;
  gradientId: string;
  xKey?: string;
  height?: number;
  yTickFormatter?: (v: number) => string;
  tooltipFormatter?: (v: number) => [string, string];
  /** Fill opacity at top of gradient (0–1) */
  fillOpacity?: number;
  /** Additional Area lines to overlay (e.g., upper95/lower5 bands) */
  additionalAreas?: {
    dataKey: string;
    color: string;
    gradientId: string;
    fillOpacity?: number;
    strokeDasharray?: string;
  }[];
}

/**
 * Parameterized AreaChart with dark institutional theme.
 * Replaces the 3 near-identical equity/drawdown/portfolio chart blocks.
 */
const QuantAreaChart: React.FC<QuantAreaChartProps> = ({
  data,
  dataKey,
  color,
  gradientId,
  xKey = 'date',
  height = 220,
  yTickFormatter = v => `₹${(v / 1000).toFixed(0)}k`,
  tooltipFormatter,
  fillOpacity = 0.15,
  additionalAreas = [],
}) => {
  const allGradients = [
    { id: gradientId, color },
    ...additionalAreas.map(a => ({ id: a.gradientId, color: a.color })),
  ];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <defs>
          {allGradients.map(g => (
            <linearGradient key={g.id} id={g.id} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={g.color} stopOpacity={0.25} />
              <stop offset="95%" stopColor={g.color} stopOpacity={0.02} />
            </linearGradient>
          ))}
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />

        <XAxis
          dataKey={xKey}
          tick={{ fill: '#475569', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={v => (typeof v === 'string' ? v.slice(0, 7) : v)}
        />

        <YAxis
          tick={{ fill: '#475569', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={yTickFormatter}
          width={52}
        />

        <Tooltip
          contentStyle={{ ...TOOLTIP_STYLE, borderRadius: 8, fontSize: 11 }}
          labelStyle={{ color: '#94a3b8', marginBottom: 4 }}
          formatter={tooltipFormatter}
        />

        {/* Primary area */}
        <Area
          type="monotone"
          dataKey={dataKey}
          stroke={color}
          strokeWidth={2}
          fill={`url(#${gradientId})`}
          fillOpacity={fillOpacity}
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
          isAnimationActive={false}
        />

        {/* Additional overlay areas */}
        {additionalAreas.map(a => (
          <Area
            key={a.dataKey}
            type="monotone"
            dataKey={a.dataKey}
            stroke={a.color}
            strokeWidth={1.5}
            strokeDasharray={a.strokeDasharray}
            fill={`url(#${a.gradientId})`}
            fillOpacity={a.fillOpacity ?? 0.05}
            dot={false}
            activeDot={false}
            isAnimationActive={false}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
};

export default QuantAreaChart;
