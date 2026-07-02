import React, { useState, useRef, useCallback, useMemo, forwardRef, useImperativeHandle } from 'react';
import { ChartTimeframe, CrosshairData, IndicatorConfig, DrawingToolType, AdvancedChartData } from './chartTypes';
import { CHART_COLORS, DEFAULT_INDICATORS } from './chartConstants';
import { TradingChart, TradingChartHandle } from './TradingChart';
import { ChartTopToolbar } from './ChartTopToolbar';
import { ChartDrawingToolbar } from './ChartDrawingToolbar';
import { IndicatorLegend } from './IndicatorLegend';
import { useChartKeyboardShortcuts, ChartKeyboardActions } from './useChartKeyboardShortcuts';

// ============================================================================
// Types
// ============================================================================

interface TradingWorkspaceProps {
  // Chart data (from parent)
  chartData: AdvancedChartData | null;
  chartLoading: boolean;
  chartError: string | null;

  // Timeframe
  chartTimeframe: ChartTimeframe;
  onTimeframeChange: (tf: ChartTimeframe) => void;

  // Symbol
  symbolName: string;

  // Fullscreen
  isFullscreen: boolean;
  onToggleFullscreen: () => void;

  // Crosshair event (to sync analytics)
  onCrosshairMove?: (data: CrosshairData) => void;

  // Children: analytics panel rendered beside chart
  children?: React.ReactNode;

  // Whether analytics panel is visible
  showAnalytics?: boolean;
}

// ============================================================================
// Component
// ============================================================================

export const TradingWorkspace = React.memo(
  forwardRef<TradingChartHandle, TradingWorkspaceProps>((props, ref) => {
    const {
      chartData,
      chartLoading,
      chartError,
      chartTimeframe,
      onTimeframeChange,
      symbolName,
      isFullscreen,
      onToggleFullscreen,
      onCrosshairMove,
      children,
      showAnalytics = true,
    } = props;

    // State
    const [activeIndicators, setActiveIndicators] = useState<IndicatorConfig[]>(DEFAULT_INDICATORS);
    const [activeTool, setActiveTool] = useState<DrawingToolType>('cursor');
    const [showIndicatorManager, setShowIndicatorManager] = useState(false);
    const [crosshairValues, setCrosshairValues] = useState<Record<string, number | null>>({});

    // Refs
    const chartHandleRef = useRef<TradingChartHandle | null>(null);
    const workspaceRef = useRef<HTMLDivElement | null>(null);

    // Forward ref to parent
    useImperativeHandle(ref, () => chartHandleRef.current as TradingChartHandle);

  // Active indicator count
  const activeIndicatorCount = useMemo(
    () => activeIndicators.filter(i => i.enabled).length,
    [activeIndicators]
  );

  // ========================================================================
  // Crosshair handler — updates legend + forwards to parent
  // ========================================================================
  const handleCrosshairMove = useCallback((data: CrosshairData) => {
    setCrosshairValues(data.indicators);
    onCrosshairMove?.(data);
  }, [onCrosshairMove]);

  // ========================================================================
  // Toolbar actions
  // ========================================================================
  const handleScreenshot = useCallback(() => {
    const dataUrl = chartHandleRef.current?.takeScreenshot();
    if (dataUrl) {
      const link = document.createElement('a');
      link.href = dataUrl;
      link.download = `${symbolName}_${chartTimeframe}_chart.png`;
      link.click();
    }
  }, [symbolName, chartTimeframe]);

  const handleIndicatorsClick = useCallback(() => {
    setShowIndicatorManager(prev => !prev);
  }, []);

  // ========================================================================
  // Drawing tool actions
  // ========================================================================
  const handleToolChange = useCallback((tool: DrawingToolType) => {
    setActiveTool(tool);
  }, []);

  const handleClearDrawings = useCallback(() => {
    setActiveTool('cursor');
    // Drawing engine clear will be wired in Phase 2
  }, []);

  // ========================================================================
  // Indicator actions
  // ========================================================================
  const handleToggleIndicatorVisibility = useCallback((id: string) => {
    setActiveIndicators(prev =>
      prev.map(ind => ind.id === id ? { ...ind, enabled: !ind.enabled } : ind)
    );
  }, []);

  const handleRemoveIndicator = useCallback((id: string) => {
    setActiveIndicators(prev => prev.filter(ind => ind.id !== id));
  }, []);

  // ========================================================================
  // Keyboard shortcuts
  // ========================================================================
  const keyboardActions: ChartKeyboardActions = useMemo(() => ({
    onTimeframeChange,
    onToggleFullscreen,
    onUndoDrawing: () => { /* Phase 2 */ },
    onDeleteDrawing: () => { /* Phase 2 */ },
    onResetDrawings: handleClearDrawings,
  }), [onTimeframeChange, onToggleFullscreen, handleClearDrawings]);

  useChartKeyboardShortcuts(keyboardActions);

  // ========================================================================
  // Render
  // ========================================================================

  return (
    <div
      ref={workspaceRef}
      className={`flex flex-col w-full ${
        isFullscreen
          ? 'fixed inset-0 z-50 bg-slate-950'
          : ''
      }`}
    >
      {/* Top Toolbar */}
      <ChartTopToolbar
        timeframe={chartTimeframe}
        onTimeframeChange={onTimeframeChange}
        onIndicatorsClick={handleIndicatorsClick}
        onScreenshot={handleScreenshot}
        onFullscreen={onToggleFullscreen}
        isFullscreen={isFullscreen}
        symbolName={symbolName}
        activeIndicatorCount={activeIndicatorCount}
      />

      {/* Main content area */}
      <div className={`flex-1 flex ${isFullscreen ? 'h-[calc(100vh-40px)]' : ''}`}>
        {/* Chart area */}
        <div className={`relative flex-1 min-w-0 ${
          isFullscreen
            ? 'h-full'
            : showAnalytics ? 'lg:w-[80%]' : 'w-full'
        }`}>
          {/* Drawing toolbar (left floating) */}
          <ChartDrawingToolbar
            activeTool={activeTool}
            onToolChange={handleToolChange}
            onClearAll={handleClearDrawings}
          />

          {/* Indicator Legend (top-right floating) */}
          <IndicatorLegend
            indicators={activeIndicators}
            currentValues={crosshairValues}
            onToggleVisibility={handleToggleIndicatorVisibility}
            onRemove={handleRemoveIndicator}
          />

          {/* The chart itself */}
          <div className={`w-full ${
            isFullscreen
              ? 'h-full'
              : 'h-[75vh] min-h-[500px]'
          } bg-slate-950/40 rounded-lg overflow-hidden border border-slate-800/40`}>
            <TradingChart
              ref={chartHandleRef}
              chartData={chartData}
              chartLoading={chartLoading}
              chartError={chartError}
              timeframe={chartTimeframe}
              activeIndicators={activeIndicators}
              onCrosshairMove={handleCrosshairMove}
              isFullscreen={isFullscreen}
            />
          </div>
        </div>

        {/* Analytics side panel (passed as children) */}
        {showAnalytics && !isFullscreen && children && (
          <div className="hidden lg:block lg:w-[20%] min-w-[220px] max-w-[320px] overflow-y-auto pl-4 space-y-4">
            {children}
          </div>
        )}
      </div>
    </div>
  );
}));

TradingWorkspace.displayName = 'TradingWorkspace';
