/**
 * Shared type definitions for the Unified Quant Research Workspace.
 * All workspace modes consume these canonical schemas.
 */

export interface StrategyParameterSpec {
  type: string;
  default: any;
  min?: number;
  max?: number;
  description?: string;
}

export interface StrategyInfo {
  id: string;
  name: string;
  category: string;
  description: string;
  parameters: Record<string, StrategyParameterSpec>;
}

export interface Trade {
  symbol: string;
  entry_time: string;
  exit_time: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  pnl: number;
  pnl_percent: number;
  holding_bars: number;
  exit_reason: string;
}

export interface BacktestResult {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  total_return_pct: number;
  cagr: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  profit_factor: number;
  avg_win: number;
  avg_loss: number;
  expectancy: number;
  avg_holding_period: number;
  initial_capital: number;
  final_capital: number;
  equity_curve: number[];
  drawdown_curve: number[];
  trades?: Trade[];
  equity_curve_recharts?: { date: string; equity: number }[];
}

export interface QuantRunResponse {
  success: boolean;
  symbol: string;
  timeframe: string;
  strategy: string;
  execution_type: string;
  metrics: BacktestResult;
}

export type WorkspaceMode =
  | 'discovery'
  | 'backtest'
  | 'portfolio';

export interface DiscoveryScan {
  loading: boolean;
  metrics?: BacktestResult;
  error?: string;
}

export interface PortfolioEntry {
  name: string;
  symbol: string;
  result: BacktestResult;
}
