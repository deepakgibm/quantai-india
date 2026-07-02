import React, { useCallback } from 'react';
import {
  MousePointer2,
  Crosshair,
  TrendingUp,
  Minus,
  SeparatorVertical,
  MoveUpRight,
  Square,
  GitBranchPlus,
  Type,
  ArrowUpRight,
  Ruler,
  Eraser,
  type LucideIcon,
} from 'lucide-react';
import { DRAWING_TOOLS } from './chartConstants';
import { DrawingToolType } from './chartTypes';

// ============================================================================
// ChartDrawingToolbar Props
// ============================================================================

export interface ChartDrawingToolbarProps {
  activeTool: DrawingToolType;
  onToolChange: (tool: DrawingToolType) => void;
  onClearAll: () => void;
}

// ============================================================================
// Icon Lookup Map
// ============================================================================

/** Static map from icon name (string) → lucide-react component. */
const ICON_MAP: Record<string, LucideIcon> = {
  MousePointer2,
  Crosshair,
  TrendingUp,
  Minus,
  SeparatorVertical,
  MoveUpRight,
  Square,
  GitBranchPlus,
  Type,
  ArrowUpRight,
  Ruler,
  Eraser,
};

// ============================================================================
// ChartDrawingToolbar Component
// ============================================================================

/**
 * Left-side floating vertical toolbar with drawing tool icons,
 * inspired by TradingView's drawing tools panel.
 *
 * - Positioned absolutely inside the chart container.
 * - Shows a tooltip on hover for each tool.
 * - Renders a visual separator before the eraser tool.
 */
export const ChartDrawingToolbar = React.memo<ChartDrawingToolbarProps>(
  function ChartDrawingToolbar({ activeTool, onToolChange, onClearAll }) {
    const handleToolClick = useCallback(
      (tool: DrawingToolType) => () => {
        if (tool === 'eraser') {
          onClearAll();
        } else {
          onToolChange(tool);
        }
      },
      [onToolChange, onClearAll]
    );

    return (
      <div
        className="absolute left-2 top-1/2 -translate-y-1/2 z-20
          flex flex-col items-center w-10 p-1.5 gap-0.5
          bg-slate-950/90 border border-slate-800/60 rounded-xl backdrop-blur-md
          shadow-lg shadow-black/30"
      >
        {DRAWING_TOOLS.map((tool) => {
          const IconComponent = ICON_MAP[tool.icon];
          const isActive = activeTool === tool.type;
          const isEraser = tool.type === 'eraser';

          return (
            <React.Fragment key={tool.type}>
              {/* Separator line before the eraser tool */}
              {isEraser && (
                <div className="w-6 h-px bg-slate-700/60 my-0.5" />
              )}

              <button
                onClick={handleToolClick(tool.type)}
                title={
                  tool.shortcut
                    ? `${tool.label} (${tool.shortcut})`
                    : tool.label
                }
                className={`
                  group relative flex items-center justify-center
                  w-7 h-7 rounded-lg p-1.5 transition-colors
                  ${
                    isActive
                      ? 'bg-violet-600/20 text-violet-400 border border-violet-500/30'
                      : 'text-slate-500 hover:text-slate-200 hover:bg-slate-800/40 border border-transparent'
                  }
                `}
              >
                {IconComponent && (
                  <IconComponent className="w-4 h-4" strokeWidth={1.75} />
                )}

                {/* Hover tooltip (appears to the right) */}
                <span
                  className="absolute left-full ml-2 px-2 py-1 rounded-md
                    text-[11px] font-medium text-slate-200
                    bg-slate-900 border border-slate-700/80
                    whitespace-nowrap opacity-0 pointer-events-none
                    group-hover:opacity-100 transition-opacity
                    shadow-md shadow-black/40 z-30"
                >
                  {tool.label}
                  {tool.shortcut && (
                    <span className="ml-1.5 text-slate-500">
                      {tool.shortcut}
                    </span>
                  )}
                </span>
              </button>
            </React.Fragment>
          );
        })}
      </div>
    );
  }
);
