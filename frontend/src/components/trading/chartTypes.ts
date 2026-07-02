import { UTCTimestamp } from 'lightweight-charts';

// ============================================================================
// Chart Timeframes
// ============================================================================

export type ChartTimeframe = '5m' | '15m' | '30m' | '1h' | '4h' | '1d' | '1w';

export interface TimeframeConfig {
  key: ChartTimeframe;
  label: string;
  shortLabel: string;
  hotkey: string;
  apiInterval: string;
}

// ============================================================================
// Chart Data Types (matches backend response)
// ============================================================================

export interface CandleData {
  time: UTCTimestamp | string | number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
  ema_20?: number;
  ema_50?: number;
  vwap?: number;
  rsi?: number;
  macd?: number;
  macd_signal?: number;
  macd_histogram?: number;
  bb_upper?: number;
  bb_middle?: number;
  bb_lower?: number;
  atr?: number;
  adx?: number;
  supertrend?: number;
  supertrend_direction?: number;
  obv?: number;
  cmf?: number;
}

export interface AdvancedChartData {
  candles: CandleData[];
  support_zones?: number[];
  resistance_zones?: number[];
  breakout_markers?: ChartMarker[];
  smart_money_zones?: SmartMoneyZone[];
  volume_profile?: VolumeProfileLevel[];
  available_history_days?: number;
  candle_count?: number;
}

export interface ChartMarker {
  time: UTCTimestamp | string | number;
  position: 'aboveBar' | 'belowBar' | 'inBar';
  color: string;
  shape: 'circle' | 'square' | 'arrowUp' | 'arrowDown';
  text: string;
  size?: number;
}

export interface SmartMoneyZone {
  start_time: UTCTimestamp;
  end_time: UTCTimestamp;
  price_high: number;
  price_low: number;
  type: 'accumulation' | 'distribution';
  strength: number;
}

export interface VolumeProfileLevel {
  price: number;
  volume: number;
  buy_volume: number;
  sell_volume: number;
  is_poc: boolean;
  is_hvn: boolean;
  is_lvn: boolean;
  is_vah: boolean;
  is_val: boolean;
}

// ============================================================================
// Indicator Configuration
// ============================================================================

export type IndicatorType =
  | 'ema' | 'sma' | 'vwap' | 'rsi' | 'macd' | 'atr' | 'adx'
  | 'bollinger' | 'supertrend' | 'ichimoku' | 'volume_profile'
  | 'donchian' | 'keltner' | 'cci' | 'obv' | 'cmf';

export type IndicatorPane = 'overlay' | 'separate';

export interface IndicatorConfig {
  id: string;
  type: IndicatorType;
  label: string;
  pane: IndicatorPane;
  enabled: boolean;
  color: string;
  secondaryColor?: string;
  params: Record<string, number>;
  lineWidth?: number;
}

// ============================================================================
// Drawing Types
// ============================================================================

export type DrawingToolType =
  | 'cursor' | 'crosshair' | 'trendline' | 'horizontal'
  | 'vertical' | 'ray' | 'rectangle' | 'fibonacci'
  | 'text' | 'arrow' | 'measure' | 'eraser';

export interface DrawingPoint {
  time: UTCTimestamp;
  price: number;
}

export interface Drawing {
  id: string;
  type: DrawingToolType;
  points: DrawingPoint[];
  style: DrawingStyle;
  symbol: string;
  timeframe: string;
  locked: boolean;
  visible: boolean;
}

export interface DrawingStyle {
  color: string;
  lineWidth: number;
  lineStyle: 'solid' | 'dashed' | 'dotted';
  fillColor?: string;
  fillOpacity?: number;
  fontSize?: number;
  text?: string;
}

// ============================================================================
// Crosshair Data (emitted on crosshair move)
// ============================================================================

export interface CrosshairData {
  time: UTCTimestamp | null;
  price: number | null;
  ohlc: {
    open: number;
    high: number;
    low: number;
    close: number;
  } | null;
  volume: number | null;
  indicators: Record<string, number | null>;
  changePercent: number | null;
  changeAbsolute: number | null;
}

// ============================================================================
// Layout Configuration
// ============================================================================

export type WorkspaceLayout = 'chart-analytics' | 'chart-only' | 'chart-chain' | 'multi-pane';

export interface LayoutConfig {
  id: WorkspaceLayout;
  label: string;
  chartSpan: number;    // Out of 10 grid columns
  analyticsSpan: number;
  analyticsVisible: boolean;
  panes: PaneConfig[];
}

export interface PaneConfig {
  id: string;
  type: 'price' | 'volume' | 'rsi' | 'macd' | 'adx' | 'custom';
  height: number; // percentage
  visible: boolean;
}
