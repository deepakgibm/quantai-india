/**
 * QuantContext — Centralized workspace state for the Unified Quant Research Terminal.
 * Replaces all fragmented useState calls in the original QuantWorkspace.tsx monolith.
 * All mode panels consume state and actions via useQuantContext().
 */

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  ReactNode,
} from 'react';
import {
  StrategyInfo,
  BacktestResult,
  WalkForwardResult,
  MonteCarloResult,
  OptimizationResult,
  QuantRunResponse,
  WorkspaceMode,
  DiscoveryScan,
  PortfolioEntry,
  OptimizationParamConfig,
  buildParamGrid,
} from '../types/quant';
import { API_URL, getAuthHeaders } from '../services/api';

// ─── Context Shape ─────────────────────────────────────────────────────────

interface QuantContextValue {
  // ── Global inputs ──────────────────────────────────────────────────────
  selectedSymbol: string | null;
  setSelectedSymbol: (s: string | null) => void;
  timeframe: string;
  setTimeframe: (t: string) => void;
  startDate: string;
  setStartDate: (d: string) => void;
  endDate: string;
  setEndDate: (d: string) => void;
  capital: number;
  setCapital: (c: number) => void;

  // ── Strategy selection ────────────────────────────────────────────────
  strategies: StrategyInfo[];
  selectedStrategyId: string;
  setSelectedStrategyId: (id: string) => void;
  activeStrategy: StrategyInfo | null;
  strategyParams: Record<string, any>;
  handleParamChange: (key: string, val: any) => void;
  setStrategyParams: React.Dispatch<React.SetStateAction<Record<string, any>>>;
  riskMode: string;
  setRiskMode: (m: string) => void;
  riskPercent: number;
  setRiskPercent: (p: number) => void;
  executionType: string;
  setExecutionType: (t: string) => void;

  // ── Workspace mode ────────────────────────────────────────────────────
  activeMode: WorkspaceMode;
  setActiveMode: (m: WorkspaceMode) => void;

  // ── Results ───────────────────────────────────────────────────────────
  backtestData: BacktestResult | null;
  backtestRecharts: { date: string; equity: number; drawdown: number }[];
  walkForwardData: WalkForwardResult | null;
  monteCarloData: MonteCarloResult | null;
  optimizationData: OptimizationResult | null;
  discoveryScans: Record<string, DiscoveryScan>;
  portfolioData: PortfolioEntry[];

  // ── Optimization config ───────────────────────────────────────────────
  optParamConfigs: Record<string, OptimizationParamConfig>;
  setOptParamConfigs: React.Dispatch<React.SetStateAction<Record<string, OptimizationParamConfig>>>;
  maxWorkers: number;
  setMaxWorkers: (w: number) => void;

  // ── Monte Carlo settings ──────────────────────────────────────────────
  mcRuinThreshold: number;
  setMcRuinThreshold: (t: number) => void;
  mcSimRuns: number;
  setMcSimRuns: (r: number) => void;

  // ── Status ────────────────────────────────────────────────────────────
  loading: boolean;
  error: string | null;
  setError: (e: string | null) => void;

  // ── Derived memos ─────────────────────────────────────────────────────
  monteCarloChartData: Record<string, any>[];
  optimizationScatterData: Record<string, any>[];
  portfolioCombinedCurve: { date: string; equity: number; average: number }[];

  // ── Actions ───────────────────────────────────────────────────────────
  runBacktest: () => Promise<void>;
  runOptimization: () => Promise<void>;
  runWalkForward: () => Promise<void>;
  runMonteCarlo: () => Promise<void>;
  runDiscoveryScan: () => Promise<void>;
  addCurrentToPortfolio: () => void;
  removePortfolioItem: (idx: number) => void;
}

const QuantContext = createContext<QuantContextValue | null>(null);

export function useQuantContext(): QuantContextValue {
  const ctx = useContext(QuantContext);
  if (!ctx) throw new Error('useQuantContext must be used inside <QuantProvider>');
  return ctx;
}

// ─── Provider ──────────────────────────────────────────────────────────────

interface QuantProviderProps {
  children: ReactNode;
}

export function QuantProvider({ children }: QuantProviderProps) {
  // Global inputs
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('symbol') || 'RELIANCE';
  });
  const [timeframe, setTimeframe] = useState('1D');
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 2);
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [capital, setCapital] = useState(100000);

  // Strategy selection
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState('');
  const [riskMode, setRiskMode] = useState('percent_capital');
  const [riskPercent, setRiskPercent] = useState(2.0);
  const [executionType, setExecutionType] = useState('event_driven');
  const [strategyParams, setStrategyParams] = useState<Record<string, any>>({});

  // Workspace mode
  const [activeMode, setActiveMode] = useState<WorkspaceMode>('backtest');

  // Results
  const [backtestData, setBacktestData] = useState<BacktestResult | null>(null);
  const [backtestRecharts, setBacktestRecharts] = useState<{ date: string; equity: number; drawdown: number }[]>([]);
  const [walkForwardData, setWalkForwardData] = useState<WalkForwardResult | null>(null);
  const [monteCarloData, setMonteCarloData] = useState<MonteCarloResult | null>(null);
  const [optimizationData, setOptimizationData] = useState<OptimizationResult | null>(null);
  const [discoveryScans, setDiscoveryScans] = useState<Record<string, DiscoveryScan>>({});
  const [portfolioData, setPortfolioData] = useState<PortfolioEntry[]>([]);

  // Optimization config
  const [optParamConfigs, setOptParamConfigs] = useState<Record<string, OptimizationParamConfig>>({});
  const [maxWorkers, setMaxWorkers] = useState(4);

  // Monte Carlo settings
  const [mcRuinThreshold, setMcRuinThreshold] = useState(50.0);
  const [mcSimRuns, setMcSimRuns] = useState(500);

  // Status
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync selectedSymbol to URL query parameters
  useEffect(() => {
    console.log("QUANTCONTEXT selectedSymbol EFFECT TRIGGERED. selectedSymbol:", selectedSymbol);
    const params = new URLSearchParams(window.location.search);
    console.log("QUANTCONTEXT URL search before update:", window.location.search);
    if (selectedSymbol) {
      params.set('symbol', selectedSymbol);
    } else {
      params.delete('symbol');
    }
    const newSearch = params.toString();
    const newPath = window.location.pathname + (newSearch ? `?${newSearch}` : '');
    window.history.replaceState(null, '', newPath);
    console.log("QUANTCONTEXT URL search after update:", window.location.search);
  }, [selectedSymbol]);

  // Clear dependent states when symbol is cleared (null)
  useEffect(() => {
    console.log("QUANTCONTEXT state cleanup EFFECT TRIGGERED. selectedSymbol:", selectedSymbol);
    if (selectedSymbol === null) {
      console.log("QUANTCONTEXT CLEARING dependent states");
      setBacktestData(null);
      setBacktestRecharts([]);
      setWalkForwardData(null);
      setMonteCarloData(null);
      setOptimizationData(null);
      setDiscoveryScans({});
      setPortfolioData([]);
    }
  }, [selectedSymbol]);

  // ── Fetch strategies ──────────────────────────────────────────────────
  const fetchStrategies = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/quant/strategies`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error('Failed to load strategies');
      const data = await res.json();
      const merged: StrategyInfo[] = [
        ...data.core_strategies.map((s: any) => ({ ...s })),
        ...data.lab_strategies.map((s: any) => ({
          ...s,
          parameters: {
            fast_period: { type: 'int', default: 10, min: 2, max: 100, description: 'Fast moving average' },
            slow_period: { type: 'int', default: 20, min: 5, max: 200, description: 'Slow moving average' },
          },
        })),
      ];
      setStrategies(merged);
      if (merged.length > 0) setSelectedStrategyId(merged[0].id);
    } catch (err: any) {
      console.error(err);
      setError('Could not retrieve strategy listings.');
    }
  }, []);

  useEffect(() => { fetchStrategies(); }, [fetchStrategies]);

  // ── Active strategy + param defaults ─────────────────────────────────
  const activeStrategy = useMemo(
    () => strategies.find(s => s.id === selectedStrategyId) || null,
    [strategies, selectedStrategyId]
  );

  useEffect(() => {
    if (!activeStrategy) return;
    const defaults: Record<string, any> = {};
    const optDefaults: Record<string, OptimizationParamConfig> = {};
    (Object.entries(activeStrategy.parameters || {}) as [string, import('../types/quant').StrategyParameterSpec][]).forEach(([k, spec]) => {
      defaults[k] = spec.default;
      if (typeof spec.default === 'number') {
        const val = spec.default as number;
        optDefaults[k] = {
          start: spec.min ?? Math.max(1, Math.floor(val * 0.5)),
          end: spec.max ?? Math.floor(val * 1.5),
          step: spec.type === 'float' ? 0.5 : Math.max(1, Math.floor(val * 0.2)),
        };
      }
    });
    setStrategyParams(defaults);
    setOptParamConfigs(optDefaults);
  }, [activeStrategy]);


  const handleParamChange = (key: string, val: any) => {
    setStrategyParams(prev => ({ ...prev, [key]: val }));
  };

  // ── Derived memos ─────────────────────────────────────────────────────
  const monteCarloChartData = useMemo(() => {
    if (!monteCarloData) return [];
    const len = monteCarloData.median_equity.length;
    return Array.from({ length: len }).map((_, i) => {
      const pt: Record<string, any> = {
        tradeIndex: i,
        median: Math.round(monteCarloData.median_equity[i]),
        upper95: Math.round(monteCarloData.upper_95_percentile[i]),
        lower5: Math.round(monteCarloData.lower_5_percentile[i]),
      };
      for (let p = 0; p < Math.min(5, monteCarloData.sample_paths.length); p++) {
        pt[`path_${p}`] = Math.round(monteCarloData.sample_paths[p][i]);
      }
      return pt;
    });
  }, [monteCarloData]);

  const optimizationScatterData = useMemo(() => {
    if (!optimizationData?.all_runs) return [];
    return optimizationData.all_runs.map(run => {
      const keys = Object.keys(run.params);
      const xKey = keys[0] || 'param1';
      const yKey = keys[1] || 'param2';
      return {
        xVal: Number(run.params[xKey]),
        yVal: Number(run.params[yKey] || 0),
        sharpe: run.metrics.sharpe_ratio,
        return: run.metrics.total_return_pct,
        name: `${xKey}:${run.params[xKey]} | ${yKey}:${run.params[yKey] ?? 'N/A'}`,
      };
    });
  }, [optimizationData]);

  const portfolioCombinedCurve = useMemo(() => {
    if (portfolioData.length === 0) return [];
    let maxIdx = 0;
    let maxLen = 0;
    portfolioData.forEach((p, idx) => {
      const len = p.result.equity_curve_recharts?.length || 0;
      if (len > maxLen) { maxLen = len; maxIdx = idx; }
    });
    const dates = portfolioData[maxIdx].result.equity_curve_recharts?.map(pt => pt.date) || [];
    return dates.map((date, dayIdx) => {
      let totalValue = 0;
      let count = 0;
      portfolioData.forEach(p => {
        const curve = p.result.equity_curve_recharts || [];
        const ptVal = curve[dayIdx]?.equity ?? (curve[curve.length - 1]?.equity || capital);
        totalValue += ptVal;
        count++;
      });
      return {
        date,
        equity: Math.round(totalValue * 100) / 100,
        average: Math.round((totalValue / count) * 100) / 100,
      };
    });
  }, [portfolioData, capital]);

  // ── Actions ───────────────────────────────────────────────────────────
  const runBacktest = useCallback(async () => {
    if (!selectedSymbol) {
      setError("Please select a symbol before running a backtest.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/quant/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
          symbol: selectedSymbol,
          timeframe,
          strategy_id: selectedStrategyId,
          start_date: startDate,
          end_date: endDate,
          initial_capital: capital,
          risk_mode: riskMode,
          risk_percent: riskPercent,
          execution_type: executionType,
          strategy_params: strategyParams,
        }),
      });
      if (!res.ok) { const b = await res.json(); throw new Error(b.detail || 'Backtest execution failed'); }
      const data: QuantRunResponse = await res.json();
      const metrics = data.metrics;
      setBacktestData(metrics);
      const chartPoints = (metrics.equity_curve_recharts || []).map((pt, idx) => ({
        date: pt.date,
        equity: pt.equity,
        drawdown: Math.round((metrics.drawdown_curve?.[idx] ?? 0) * 100) / 100,
      }));
      setBacktestRecharts(chartPoints);
    } catch (err: any) {
      setError(err.message || 'An error occurred during backtest.');
    } finally {
      setLoading(false);
    }
  }, [selectedSymbol, timeframe, selectedStrategyId, startDate, endDate, capital, riskMode, riskPercent, executionType, strategyParams]);

  const runOptimization = useCallback(async () => {
    if (!selectedSymbol) {
      setError("Please select a symbol before running optimization.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const grid = buildParamGrid(optParamConfigs);
      if (grid.length === 0) throw new Error('No numeric parameters found to optimize.');
      if (grid.length > 100 && !window.confirm(`You are about to scan ${grid.length} parameter configurations. Continue?`)) {
        setLoading(false);
        return;
      }
      const res = await fetch(`${API_URL}/api/v1/quant/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
          symbol: selectedSymbol, timeframe, strategy_id: selectedStrategyId,
          start_date: startDate, end_date: endDate, initial_capital: capital,
          param_grid: grid, max_workers: maxWorkers,
        }),
      });
      if (!res.ok) { const b = await res.json(); throw new Error(b.detail || 'Optimization failed'); }
      setOptimizationData(await res.json());
    } catch (err: any) {
      setError(err.message || 'Strategy parameter optimization failed.');
    } finally {
      setLoading(false);
    }
  }, [optParamConfigs, selectedSymbol, timeframe, selectedStrategyId, startDate, endDate, capital, maxWorkers]);

  const runWalkForward = useCallback(async () => {
    if (!selectedSymbol) {
      setError("Please select a symbol before running walk-forward validation.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const grid = buildParamGrid(optParamConfigs);
      if (grid.length === 0) throw new Error('Please select parameters to optimize in rolling windows.');
      const res = await fetch(`${API_URL}/api/v1/quant/walk-forward`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
          symbol: selectedSymbol, timeframe, strategy_id: selectedStrategyId,
          start_date: startDate, end_date: endDate, initial_capital: capital,
          param_grid: grid.slice(0, 50),
          train_window_bars: 120, test_window_bars: 30, step_bars: 30, anchored: false,
        }),
      });
      if (!res.ok) { const b = await res.json(); throw new Error(b.detail || 'Walk-Forward run failed'); }
      setWalkForwardData(await res.json());
    } catch (err: any) {
      setError(err.message || 'Walk-forward validation failed.');
    } finally {
      setLoading(false);
    }
  }, [optParamConfigs, selectedSymbol, timeframe, selectedStrategyId, startDate, endDate, capital]);

  const runMonteCarlo = useCallback(async () => {
    if (!backtestData?.trades?.length) {
      setError('Run a backtest first to generate trade return distributions for Monte Carlo.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const returns = backtestData.trades.map(t => t.pnl_percent);
      const res = await fetch(`${API_URL}/api/v1/quant/monte-carlo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
          trade_returns_pct: returns,
          initial_capital: capital,
          num_simulations: mcSimRuns,
          num_trades_per_path: Math.max(30, returns.length),
          risk_of_ruin_pct: mcRuinThreshold,
        }),
      });
      if (!res.ok) { const b = await res.json(); throw new Error(b.detail || 'Monte Carlo failed'); }
      setMonteCarloData(await res.json());
    } catch (err: any) {
      setError(err.message || 'Monte Carlo simulation failed.');
    } finally {
      setLoading(false);
    }
  }, [backtestData, capital, mcSimRuns, mcRuinThreshold]);

  const runDiscoveryScan = useCallback(async () => {
    const selectedSymbols = selectedSymbol ? [selectedSymbol] : [];
    console.log("Selected Symbols:", selectedSymbols);
    if (!selectedSymbol) {
      setError("Please select a symbol before running a strategy discovery scan.");
      return;
    }
    setLoading(true);
    setError(null);
    const initial: Record<string, DiscoveryScan> = {};
    strategies.forEach(s => { initial[s.id] = { loading: true }; });
    setDiscoveryScans(initial);
    
    const currentState = {
      selectedSymbol,
      timeframe,
      startDate,
      endDate,
      capital,
      strategies,
      discoveryScans: initial
    };
    console.log("Current State:", currentState);

    // Prime the cache using the first strategy sequentially
    if (strategies.length > 0) {
      const firstStrat = strategies[0];
      const payload = {
        symbol: selectedSymbol, timeframe, strategy_id: firstStrat.id,
        start_date: startDate, end_date: endDate, initial_capital: capital,
        risk_mode: 'percent_capital', risk_percent: 2.0,
        execution_type: 'vectorized', strategy_params: {},
      };
      console.log("Priming payload:", payload);
      try {
        const res = await fetch(`${API_URL}/api/v1/quant/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const b = await res.json();
          console.log("Priming API Response (Error):", b);
          setDiscoveryScans(p => ({ ...p, [firstStrat.id]: { loading: false, error: b.detail || 'Scan failed' } }));
        } else {
          const data: QuantRunResponse = await res.json();
          console.log("Priming API Response:", data);
          setDiscoveryScans(p => ({ ...p, [firstStrat.id]: { loading: false, metrics: data.metrics } }));
        }
      } catch (err: any) {
        console.error("Priming API Response (Exception):", err);
        setDiscoveryScans(p => ({ ...p, [firstStrat.id]: { loading: false, error: err.message } }));
      }
    }

    // Run the remaining strategies in parallel (they will benefit from the primed cache!)
    const remainingStrategies = strategies.slice(1);
    await Promise.all(
      remainingStrategies.map(async strat => {
        const payload = {
          symbol: selectedSymbol, timeframe, strategy_id: strat.id,
          start_date: startDate, end_date: endDate, initial_capital: capital,
          risk_mode: 'percent_capital', risk_percent: 2.0,
          execution_type: 'vectorized', strategy_params: {},
        };
        console.log("Payload:", payload);

        try {
          const res = await fetch(`${API_URL}/api/v1/quant/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
            body: JSON.stringify(payload),
          });
          
          if (!res.ok) {
            const b = await res.json();
            console.log("API Response (Error):", b);
            setDiscoveryScans(p => ({ ...p, [strat.id]: { loading: false, error: b.detail || 'Scan failed' } }));
          } else {
            const data: QuantRunResponse = await res.json();
            console.log("API Response:", data);
            const mappedResults = data.metrics;
            console.log("Mapped Results:", mappedResults);
            setDiscoveryScans(p => ({ ...p, [strat.id]: { loading: false, metrics: mappedResults } }));
          }
        } catch (err: any) {
          console.error("API Response (Exception):", err);
          setDiscoveryScans(p => ({ ...p, [strat.id]: { loading: false, error: err.message } }));
        }
      })
    );
    setLoading(false);
  }, [strategies, selectedSymbol, timeframe, startDate, endDate, capital]);

  const addCurrentToPortfolio = useCallback(() => {
    if (!backtestData || !activeStrategy || !selectedSymbol) return;
    const isDup = portfolioData.some(p => p.name === activeStrategy.name && p.symbol === selectedSymbol);
    if (isDup) return;
    setPortfolioData(prev => [...prev, { name: activeStrategy.name, symbol: selectedSymbol, result: backtestData }]);
  }, [backtestData, activeStrategy, portfolioData, selectedSymbol]);

  const removePortfolioItem = useCallback((idx: number) => {
    setPortfolioData(prev => prev.filter((_, i) => i !== idx));
  }, []);

  // ── Context value ─────────────────────────────────────────────────────
  const value: QuantContextValue = {
    selectedSymbol, setSelectedSymbol,
    timeframe, setTimeframe,
    startDate, setStartDate,
    endDate, setEndDate,
    capital, setCapital,
    strategies, selectedStrategyId, setSelectedStrategyId,
    activeStrategy, strategyParams, handleParamChange, setStrategyParams,
    riskMode, setRiskMode,
    riskPercent, setRiskPercent,
    executionType, setExecutionType,
    activeMode, setActiveMode,
    backtestData, backtestRecharts,
    walkForwardData, monteCarloData, optimizationData,
    discoveryScans, portfolioData,
    optParamConfigs, setOptParamConfigs,
    maxWorkers, setMaxWorkers,
    mcRuinThreshold, setMcRuinThreshold,
    mcSimRuns, setMcSimRuns,
    loading, error, setError,
    monteCarloChartData, optimizationScatterData, portfolioCombinedCurve,
    runBacktest, runOptimization, runWalkForward, runMonteCarlo, runDiscoveryScan,
    addCurrentToPortfolio, removePortfolioItem,
  };

  return <QuantContext.Provider value={value}>{children}</QuantContext.Provider>;
}
