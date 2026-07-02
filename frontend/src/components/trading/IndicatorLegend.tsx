import React, { useCallback } from 'react';
import { Eye, EyeOff, X } from 'lucide-react';
import { IndicatorConfig } from './chartTypes';

// ============================================================================
// Indicator Legend Props
// ============================================================================

interface IndicatorLegendProps {
  indicators: IndicatorConfig[];
  currentValues: Record<string, number | null>;
  onToggleVisibility: (id: string) => void;
  onRemove: (id: string) => void;
}

// ============================================================================
// IndicatorLegend Component
// ============================================================================

/**
 * Floating, compact legend showing active indicators and their current values.
 * Positioned in the top-right of the chart area, avoiding the price scale.
 * Each row displays a color dot, label, live value, and action buttons.
 */
export const IndicatorLegend = React.memo<IndicatorLegendProps>(
  function IndicatorLegend({ indicators, currentValues, onToggleVisibility, onRemove }) {
    // Don't render anything if there are no indicators
    if (!indicators || indicators.length === 0) {
      return null;
    }

    const formatValue = useCallback((value: number | null): string => {
      if (value === null || value === undefined) return '—';
      return value.toFixed(2);
    }, []);

    return (
      <div className="absolute top-3 right-14 z-20 bg-slate-950/85 border border-slate-800/50 rounded-lg backdrop-blur-md px-2 py-1.5 min-w-[120px] max-w-[200px]">
        {indicators.map((indicator) => {
          const value = currentValues[indicator.id] ?? null;

          return (
            <div
              key={indicator.id}
              className="flex items-center gap-1.5 py-0.5 px-0.5 rounded hover:bg-slate-800/40 group transition-colors duration-150"
            >
              {/* Color dot */}
              <span
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: indicator.color }}
              />

              {/* Label */}
              <span
                className={`text-[9px] font-medium flex-shrink-0 ${
                  indicator.enabled ? 'text-slate-400' : 'text-slate-600 line-through'
                }`}
              >
                {indicator.label}
              </span>

              {/* Value */}
              <span
                className={`text-[10px] tabular-nums ml-auto flex-shrink-0 ${
                  indicator.enabled ? 'text-slate-200' : 'text-slate-600'
                }`}
              >
                {indicator.enabled ? formatValue(value) : '—'}
              </span>

              {/* Toggle visibility button */}
              <button
                onClick={() => onToggleVisibility(indicator.id)}
                className="p-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-150 hover:bg-slate-700/60 text-slate-500 hover:text-slate-300"
                title={indicator.enabled ? 'Hide indicator' : 'Show indicator'}
              >
                {indicator.enabled ? (
                  <Eye className="w-2.5 h-2.5" />
                ) : (
                  <EyeOff className="w-2.5 h-2.5" />
                )}
              </button>

              {/* Remove button */}
              <button
                onClick={() => onRemove(indicator.id)}
                className="p-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-150 hover:bg-red-900/40 text-slate-500 hover:text-red-400"
                title="Remove indicator"
              >
                <X className="w-2.5 h-2.5" />
              </button>
            </div>
          );
        })}
      </div>
    );
  }
);
