import React, { useCallback } from 'react';
import {
  Camera,
  Maximize2,
  Minimize2,
  SlidersHorizontal,
  BarChart2,
} from 'lucide-react';
import { TIMEFRAMES } from './chartConstants';
import { ChartTimeframe } from './chartTypes';

// ============================================================================
// ChartTopToolbar Props
// ============================================================================

export interface ChartTopToolbarProps {
  timeframe: ChartTimeframe;
  onTimeframeChange: (tf: ChartTimeframe) => void;
  onIndicatorsClick: () => void;
  onScreenshot: () => void;
  onFullscreen: () => void;
  isFullscreen: boolean;
  symbolName: string;
  activeIndicatorCount: number;
}

// ============================================================================
// ChartTopToolbar Component
// ============================================================================

/**
 * Professional top toolbar for the trading chart, inspired by TradingView.
 *
 * Layout:
 * ┌─────────────────────────────────────────────────────────────────────────┐
 * │ SYMBOL │ 5m 15m 30m 1H 4H 1D 1W │ Indicators(N) │ 📷 │ ⛶ Fullscreen │
 * └─────────────────────────────────────────────────────────────────────────┘
 */
export const ChartTopToolbar = React.memo<ChartTopToolbarProps>(
  function ChartTopToolbar({
    timeframe,
    onTimeframeChange,
    onIndicatorsClick,
    onScreenshot,
    onFullscreen,
    isFullscreen,
    symbolName,
    activeIndicatorCount,
  }) {
    // Memoize timeframe handler factory to avoid re-creating on every render
    const handleTimeframeClick = useCallback(
      (tf: ChartTimeframe) => () => {
        onTimeframeChange(tf);
      },
      [onTimeframeChange]
    );

    return (
      <div
        className="flex items-center h-10 px-2 gap-1
          bg-slate-950/80 border-b border-slate-800/60 backdrop-blur-md
          select-none"
      >
        {/* ── Symbol Name ── */}
        <div className="flex items-center gap-1.5 px-2 mr-1 border-r border-slate-800/60 h-full">
          <BarChart2 className="w-3.5 h-3.5 text-violet-400 flex-shrink-0" />
          <span className="text-xs font-semibold text-slate-200 tracking-wide whitespace-nowrap">
            {symbolName}
          </span>
        </div>

        {/* ── Timeframe Selector (scrollable on mobile) ── */}
        <div
          className="flex items-center gap-0.5 overflow-x-auto scrollbar-none
            border-r border-slate-800/60 pr-1 mr-1 h-full"
        >
          {TIMEFRAMES.map((tf) => {
            const isActive = tf.key === timeframe;
            return (
              <button
                key={tf.key}
                onClick={handleTimeframeClick(tf.key)}
                title={`${tf.label} (${tf.hotkey})`}
                className={`
                  px-2 py-1 rounded text-[11px] font-medium transition-colors
                  whitespace-nowrap flex-shrink-0
                  ${
                    isActive
                      ? 'bg-violet-600 text-white shadow-sm shadow-violet-600/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }
                `}
              >
                {tf.shortLabel}
              </button>
            );
          })}
        </div>

        {/* ── Spacer ── */}
        <div className="flex-1" />

        {/* ── Indicators Button ── */}
        <button
          onClick={onIndicatorsClick}
          title="Toggle indicators panel"
          className="flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-medium
            text-slate-400 hover:text-slate-200 hover:bg-slate-800/60
            transition-colors whitespace-nowrap"
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span>Indicators</span>
          {activeIndicatorCount > 0 && (
            <span
              className="inline-flex items-center justify-center min-w-[18px] h-[18px]
                rounded-full bg-violet-600/80 text-[10px] text-white px-1 leading-none"
            >
              {activeIndicatorCount}
            </span>
          )}
        </button>

        {/* ── Divider ── */}
        <div className="w-px h-5 bg-slate-800/60 mx-0.5" />

        {/* ── Screenshot Button ── */}
        <button
          onClick={onScreenshot}
          title="Take screenshot"
          className="p-1.5 rounded text-slate-400 hover:text-slate-200
            hover:bg-slate-800/60 transition-colors"
        >
          <Camera className="w-4 h-4" />
        </button>

        {/* ── Fullscreen Toggle ── */}
        <button
          onClick={onFullscreen}
          title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          className="flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium
            text-slate-400 hover:text-slate-200 hover:bg-slate-800/60
            transition-colors whitespace-nowrap"
        >
          {isFullscreen ? (
            <Minimize2 className="w-3.5 h-3.5" />
          ) : (
            <Maximize2 className="w-3.5 h-3.5" />
          )}
          <span className="hidden sm:inline">
            {isFullscreen ? 'Exit' : 'Fullscreen'}
          </span>
        </button>
      </div>
    );
  }
);
