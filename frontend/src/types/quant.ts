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

export interface WalkForwardWindow {
  window_id: number;
  train_start: string;
  train_end: string;
  test_start: string;
  test_end: string;
  is_sharpe: number;
  oos_return: number;
  oos_sharpe: number;
  oos_drawdown: number;
  oos_trades: number;
  best_parameters: Record<string, any>;
}

export interface WalkForwardResult {
  summary: {
    total_return: number;
    sharpe: number;
    max_drawdown: number;
    profitable_windows_pct: number;
    parameter_stability_score: number;
  };
  validation_passed: boolean;
  validation_messages: string[];
  window_results: WalkForwardWindow[];
  equity_curve: { date: string; equity: number }[];
}

export interface MonteCarloResult {
  num_simulations: number;
  risk_of_ruin_probability: number;
  median_equity: number[];
  upper_95_percentile: number[];
  lower_5_percentile: number[];
  sample_paths: number[][];
  worst_case_drawdown: number;
  average_max_drawdown: number;
  median_final_equity: number;
}

export interface OptimizationRun {
  params: Record<string, any>;
  metrics: {
    total_return_pct: number;
    sharpe_ratio: number;
    max_drawdown_pct: number;
    total_trades: number;
    win_rate: number;
    profit_factor: number;
  };
  status: string;
}

export interface OptimizationResult {
  total_runs: number;
  duration_seconds: number;
  best_run: OptimizationRun;
  all_runs: OptimizationRun[];
}

export type WorkspaceMode =
  | 'discovery'
  | 'backtest'
  | 'walk_forward'
  | 'monte_carlo'
  | 'optimization'
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

export interface OptimizationParamConfig {
  start: number;
  end: number;
  step: number;
}

/** Utility: build cartesian product of param grid from range configs */
export function buildParamGrid(
  configs: Record<string, OptimizationParamConfig>
): Record<string, any>[] {
  const specs = Object.entries(configs);
  if (specs.length === 0) return [];

  let grid: Record<string, any>[] = [{}];
  specs.forEach(([name, spec]) => {
    const values: number[] = [];
    const step = spec.step > 0 ? spec.step : 1;
    for (let v = spec.start; v <= spec.end; v = Math.round((v + step) * 1000) / 1000) {
      values.push(v);
    }
    const newGrid: Record<string, any>[] = [];
    grid.forEach(comb => {
      values.forEach(val => {
        newGrid.push({ ...comb, [name]: val });
      });
    });
    grid = newGrid;
  });
  return grid;
}
