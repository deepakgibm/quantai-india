export enum Page {
  LANDING = 'LANDING',
  LOGIN = 'LOGIN',
  SIGNUP = 'SIGNUP',
  DASHBOARD = 'DASHBOARD',
  AI_PROMPT = 'AI_PROMPT',
  ORDERS = 'ORDERS',
  RISK_MANAGER = 'RISK_MANAGER',
  ALGO_BUILDER = 'algo_builder',
  LIVE_MONITOR = 'live_monitor',
  ETL_STATUS = 'ETL_STATUS',
  QUANT_BOT = 'quant_bot',
  AUDIT_REPORTS = 'audit_reports',
  SCANNER = 'scanner',
  SETTINGS = 'SETTINGS',
  SECTOR_HEATMAP = 'SECTOR_HEATMAP',
  MOMENT_ALERT = 'MOMENT_ALERT',
  WEEK52_BREAKOUT = 'WEEK52_BREAKOUT',
  FORGOT_PASSWORD = 'FORGOT_PASSWORD',
  WALK_FORWARD_BACKTEST = 'walk_forward_backtest',
  EXPERIMENT_LAB = 'experiment_lab',
  ADMIN_INDICES = 'ADMIN_INDICES',
  TRADE_SCREENER = 'TRADE_SCREENER',
  SIGNAL_BOT = 'SIGNAL_BOT',
  VOLATILITY_DASHBOARD = 'VOLATILITY_DASHBOARD',
  OPTION_FLOW = 'OPTION_FLOW',
  QUANT_WORKSPACE = 'quant_workspace',
  SECTOR_ANALYSIS = 'SECTOR_ANALYSIS',
  VOLUME_PROFILE = 'VOLUME_PROFILE',
  SUBSCRIPTION = 'subscription',
  PORTFOLIO_INTELLIGENCE = 'portfolio_intelligence',
  SIGNAL_CENTER = 'signal_center',
  SMC_ANALYSIS = 'smc_analysis',
  PATTERN_LAB = 'pattern_lab',
  ACADEMY = 'academy',
  RESEARCH_CENTER = 'research_center',
  AFFILIATE = 'affiliate',
}

export interface Stock {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: string;
}

export interface Order {
  id: string;
  timestamp: string;
  stock: string;
  type: 'BUY' | 'SELL';
  quantity: number;
  entryPrice: number;
  exitPrice?: number;
  pnl?: number;
  algo: string;
  status: 'OPEN' | 'CLOSED';
}

export interface AlgoLog {
  id: string;
  time: string;
  message: string;
  type: 'INFO' | 'WARNING' | 'SUCCESS' | 'ERROR';
}

export interface AlgoConfig {
  id: string;
  name: string;
  description: string;
  active: boolean;
  performance: number | null;
}