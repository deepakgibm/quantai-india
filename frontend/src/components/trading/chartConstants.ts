import { ChartTimeframe, TimeframeConfig, IndicatorConfig, IndicatorType, DrawingToolType, LayoutConfig } from './chartTypes';

// ============================================================================
// Color Palette
// ============================================================================

export const CHART_COLORS = {
  // Background & Grid
  background: '#090d16',
  gridLines: '#1e293b',
  borderColor: '#1e293b',
  textColor: '#64748b',
  textPrimary: '#e2e8f0',
  textMuted: '#475569',

  // Candles
  bullish: '#10b981',
  bearish: '#ef4444',
  bullishFaded: '#10b98155',
  bearishFaded: '#ef444455',

  // Indicators
  ema20: '#F59E0B',
  ema50: '#3b82f6',
  vwap: '#8B5CF6',
  sma: '#06b6d4',
  rsi: '#f97316',
  macd: '#22d3ee',
  macdSignal: '#f472b6',
  macdHistogramUp: '#10b98188',
  macdHistogramDown: '#ef444488',
  bollingerUpper: '#6366f1',
  bollingerMiddle: '#818cf8',
  bollingerLower: '#6366f1',
  bollingerFill: '#6366f115',
  supertrend: '#22c55e',
  supertrendBear: '#ef4444',
  atr: '#a78bfa',
  adx: '#fb923c',
  obv: '#2dd4bf',
  cmf: '#e879f9',

  // Zones
  support: '#10B981',
  resistance: '#EF4444',
  poc: '#f59e0b',
  vah: '#6366f1',
  val: '#22d3ee',

  // Smart Money
  accumulation: '#10b98120',
  distribution: '#ef444420',

  // UI
  toolbarBg: '#0f172a',
  toolbarBorder: '#1e293b',
  toolbarHover: '#1e293b',
  toolbarActive: '#7c3aed',
  tooltipBg: '#0f172aee',
  tooltipBorder: '#1e293b',
} as const;

// ============================================================================
// Timeframe Definitions
// ============================================================================

export const TIMEFRAMES: TimeframeConfig[] = [
  { key: '5m',  label: '5 Minute',  shortLabel: '5m',  hotkey: '1', apiInterval: '5m' },
  { key: '15m', label: '15 Minute', shortLabel: '15m', hotkey: '2', apiInterval: '15m' },
  { key: '30m', label: '30 Minute', shortLabel: '30m', hotkey: '3', apiInterval: '30m' },
  { key: '1h',  label: '1 Hour',    shortLabel: '1H',  hotkey: '4', apiInterval: '1h' },
  { key: '4h',  label: '4 Hour',    shortLabel: '4H',  hotkey: '5', apiInterval: '4h' },
  { key: '1d',  label: 'Daily',     shortLabel: '1D',  hotkey: '6', apiInterval: '1d' },
  { key: '1w',  label: 'Weekly',    shortLabel: '1W',  hotkey: '7', apiInterval: '1w' },
];

// ============================================================================
// Default Indicator Configurations
// ============================================================================

export const DEFAULT_INDICATORS: IndicatorConfig[] = [
  { id: 'ema-20',  type: 'ema',  label: 'EMA 20',  pane: 'overlay',   enabled: true,  color: CHART_COLORS.ema20,    params: { period: 20 }, lineWidth: 1 },
  { id: 'ema-50',  type: 'ema',  label: 'EMA 50',  pane: 'overlay',   enabled: true,  color: CHART_COLORS.ema50,    params: { period: 50 }, lineWidth: 1 },
  { id: 'vwap',    type: 'vwap', label: 'VWAP',     pane: 'overlay',   enabled: true,  color: CHART_COLORS.vwap,     params: {},             lineWidth: 1 },
];

export const AVAILABLE_INDICATORS: { type: IndicatorType; label: string; category: string; pane: 'overlay' | 'separate'; defaultParams: Record<string, number> }[] = [
  // Trend (Overlay)
  { type: 'ema',         label: 'EMA',               category: 'Trend',      pane: 'overlay',   defaultParams: { period: 20 } },
  { type: 'sma',         label: 'SMA',               category: 'Trend',      pane: 'overlay',   defaultParams: { period: 20 } },
  { type: 'vwap',        label: 'VWAP',              category: 'Trend',      pane: 'overlay',   defaultParams: {} },
  { type: 'supertrend',  label: 'SuperTrend',        category: 'Trend',      pane: 'overlay',   defaultParams: { period: 10, multiplier: 3 } },
  { type: 'ichimoku',    label: 'Ichimoku Cloud',    category: 'Trend',      pane: 'overlay',   defaultParams: { tenkan: 9, kijun: 26, senkou: 52 } },

  // Momentum (Separate Pane)
  { type: 'rsi',         label: 'RSI',               category: 'Momentum',   pane: 'separate',  defaultParams: { period: 14 } },
  { type: 'macd',        label: 'MACD',              category: 'Momentum',   pane: 'separate',  defaultParams: { fast: 12, slow: 26, signal: 9 } },
  { type: 'adx',         label: 'ADX',               category: 'Momentum',   pane: 'separate',  defaultParams: { period: 14 } },
  { type: 'cci',         label: 'CCI',               category: 'Momentum',   pane: 'separate',  defaultParams: { period: 20 } },

  // Volatility (Overlay)
  { type: 'bollinger',   label: 'Bollinger Bands',   category: 'Volatility', pane: 'overlay',   defaultParams: { period: 20, stdDev: 2 } },
  { type: 'atr',         label: 'ATR',               category: 'Volatility', pane: 'separate',  defaultParams: { period: 14 } },
  { type: 'keltner',     label: 'Keltner Channel',   category: 'Volatility', pane: 'overlay',   defaultParams: { period: 20, multiplier: 2 } },
  { type: 'donchian',    label: 'Donchian Channel',  category: 'Volatility', pane: 'overlay',   defaultParams: { period: 20 } },

  // Volume (Separate Pane)
  { type: 'obv',         label: 'OBV',               category: 'Volume',     pane: 'separate',  defaultParams: {} },
  { type: 'cmf',         label: 'CMF',               category: 'Volume',     pane: 'separate',  defaultParams: { period: 20 } },
  { type: 'volume_profile', label: 'Volume Profile', category: 'Volume',     pane: 'overlay',   defaultParams: { bins: 24 } },
];

// Indicator color palette for dynamically added indicators
export const INDICATOR_COLOR_PALETTE = [
  '#F59E0B', '#3b82f6', '#8B5CF6', '#06b6d4', '#f97316',
  '#22d3ee', '#f472b6', '#a78bfa', '#fb923c', '#2dd4bf',
  '#e879f9', '#84cc16', '#14b8a6', '#f43f5e', '#6366f1',
];

// ============================================================================
// Drawing Tool Definitions
// ============================================================================

export const DRAWING_TOOLS: { type: DrawingToolType; label: string; icon: string; shortcut?: string }[] = [
  { type: 'cursor',      label: 'Cursor',              icon: 'MousePointer2' },
  { type: 'crosshair',   label: 'Crosshair',           icon: 'Crosshair' },
  { type: 'trendline',   label: 'Trend Line',          icon: 'TrendingUp' },
  { type: 'horizontal',  label: 'Horizontal Line',     icon: 'Minus' },
  { type: 'vertical',    label: 'Vertical Line',       icon: 'SeparatorVertical' },
  { type: 'ray',         label: 'Ray',                 icon: 'MoveUpRight' },
  { type: 'rectangle',   label: 'Rectangle',           icon: 'Square' },
  { type: 'fibonacci',   label: 'Fibonacci Retracement', icon: 'GitBranchPlus' },
  { type: 'text',        label: 'Text Annotation',     icon: 'Type' },
  { type: 'arrow',       label: 'Arrow',               icon: 'ArrowUpRight' },
  { type: 'measure',     label: 'Measure Tool',        icon: 'Ruler',            shortcut: 'Alt+Click' },
  { type: 'eraser',      label: 'Erase All Drawings',  icon: 'Eraser' },
];

// ============================================================================
// Layout Presets
// ============================================================================

export const LAYOUT_PRESETS: LayoutConfig[] = [
  {
    id: 'chart-analytics',
    label: 'Chart + Analytics',
    chartSpan: 8,
    analyticsSpan: 2,
    analyticsVisible: true,
    panes: [{ id: 'price', type: 'price', height: 100, visible: true }],
  },
  {
    id: 'chart-only',
    label: 'Chart Only',
    chartSpan: 10,
    analyticsSpan: 0,
    analyticsVisible: false,
    panes: [{ id: 'price', type: 'price', height: 100, visible: true }],
  },
  {
    id: 'multi-pane',
    label: 'Multi-Pane',
    chartSpan: 8,
    analyticsSpan: 2,
    analyticsVisible: true,
    panes: [
      { id: 'price',  type: 'price',  height: 60, visible: true },
      { id: 'volume', type: 'volume', height: 20, visible: true },
      { id: 'rsi',    type: 'rsi',    height: 20, visible: true },
    ],
  },
];

// ============================================================================
// Chart Defaults
// ============================================================================

export const CHART_DEFAULTS = {
  minHeight: 500,
  defaultHeight: 700,
  fullscreenOffset: 140,   // px for toolbar
  tooltipMaxWidth: '95%',
  pollingInterval: 15000,  // 15 seconds
  maxPollFailures: 3,
  maxRetries: 2,
  resizeDebounce: 16,      // ~60fps
} as const;
