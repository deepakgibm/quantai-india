import React, { useState, useEffect } from 'react';
import {
    FlaskConical,
    Play,
    TrendingUp,
    TrendingDown,
    BarChart3,
    Settings2,
    RefreshCw,
    CheckCircle,
    AlertTriangle,
    Layers,
    Target,
    Shield,
    Activity,
    DollarSign,
    Calendar
} from 'lucide-react';

// Chart components
import EquityCurveChart from '../components/charts/EquityCurveChart';
import DrawdownChart from '../components/charts/DrawdownChart';

interface OptimizationResult {
    best_params: Record<string, any>;
    best_metrics: Record<string, number>;
    best_objective: number;
    total_combinations: number;
    valid_combinations: number;
    method: string;
    elapsed_seconds: number;
    top_5: Array<{
        params: Record<string, any>;
        metrics: Record<string, number>;
        objective_value: number;
    }>;
}

const StrategyLab: React.FC = () => {
    // Form state
    const [symbol, setSymbol] = useState('RELIANCE');
    const [strategy, setStrategy] = useState('MACrossover');
    const [startDate, setStartDate] = useState('2023-01-01');
    const [endDate, setEndDate] = useState('2024-01-01');
    const [initialCapital, setInitialCapital] = useState(1000000);
    const [optimizationMethod, setOptimizationMethod] = useState('grid');
    const [objective, setObjective] = useState('sharpe');
    const [nIterations, setNIterations] = useState(50);

    // Parameter ranges for optimization
    const [fastPeriodRange, setFastPeriodRange] = useState([5, 10, 15, 20]);
    const [slowPeriodRange, setSlowPeriodRange] = useState([20, 30, 40, 50]);

    // Results
    const [isLoading, setIsLoading] = useState(false);
    const [result, setResult] = useState<OptimizationResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);

    useEffect(() => {
        fetchSymbols();
    }, []);

    const fetchSymbols = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/quant/symbols');
            if (response.ok) {
                const data = await response.json();
                setAvailableSymbols(data.symbols?.map((s: any) => s.symbol) || []);
            }
        } catch (err) {
            console.error('Failed to fetch symbols');
        }
    };

    const runOptimization = async () => {
        setIsLoading(true);
        setError(null);
        setResult(null);

        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch('http://localhost:8000/api/quant/optimize/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    symbol,
                    strategy,
                    start_date: startDate,
                    end_date: endDate,
                    initial_capital: initialCapital,
                    method: optimizationMethod,
                    n_iterations: nIterations,
                    objective,
                    param_grid: {
                        fast_period: fastPeriodRange,
                        slow_period: slowPeriodRange
                    }
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Optimization failed');
            }

            const data = await response.json();
            setResult(data);
        } catch (err: any) {
            setError(err.message || 'Failed to run optimization');
        } finally {
            setIsLoading(false);
        }
    };

    const MetricCard = ({ label, value, icon: Icon, color = 'blue', suffix = '' }: any) => (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
            <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
                <Icon size={16} className={`text-${color}-500`} />
            </div>
            <span className={`text-lg font-bold text-${color}-600 dark:text-${color}-400`}>
                {typeof value === 'number' ? value.toFixed(2) : value}{suffix}
            </span>
        </div>
    );

    return (
        <div className="h-full flex flex-col gap-6 overflow-auto p-1">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-3 bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl shadow-lg shadow-amber-500/20">
                        <FlaskConical size={24} className="text-white" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Strategy Lab</h1>
                        <p className="text-sm text-slate-500 dark:text-slate-400">Grid, Random & Bayesian Optimization</p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Configuration Panel */}
                <div className="lg:col-span-1 bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
                    <h2 className="text-lg font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                        <Settings2 size={18} /> Optimization Config
                    </h2>

                    <div className="space-y-4">
                        {/* Symbol */}
                        <div>
                            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Symbol</label>
                            <select
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value)}
                                className="w-full p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white"
                            >
                                {availableSymbols.length > 0 ? (
                                    availableSymbols.map(s => <option key={s} value={s}>{s}</option>)
                                ) : (
                                    <option value="RELIANCE">RELIANCE</option>
                                )}
                            </select>
                        </div>

                        {/* Optimization Method */}
                        <div>
                            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Method</label>
                            <select
                                value={optimizationMethod}
                                onChange={(e) => setOptimizationMethod(e.target.value)}
                                className="w-full p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white"
                            >
                                <option value="grid">Grid Search</option>
                                <option value="random">Random Search</option>
                                <option value="bayesian">Bayesian Optimization</option>
                            </select>
                        </div>

                        {/* Objective */}
                        <div>
                            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Objective</label>
                            <select
                                value={objective}
                                onChange={(e) => setObjective(e.target.value)}
                                className="w-full p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white"
                            >
                                <option value="sharpe">Sharpe Ratio</option>
                                <option value="return">Total Return</option>
                                <option value="calmar">Calmar Ratio</option>
                                <option value="sortino">Sortino Ratio</option>
                            </select>
                        </div>

                        {/* Date Range */}
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Start</label>
                                <input
                                    type="date"
                                    value={startDate}
                                    onChange={(e) => setStartDate(e.target.value)}
                                    className="w-full p-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">End</label>
                                <input
                                    type="date"
                                    value={endDate}
                                    onChange={(e) => setEndDate(e.target.value)}
                                    className="w-full p-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                />
                            </div>
                        </div>

                        {/* Parameter Ranges */}
                        <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
                            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Parameter Ranges</h3>
                            <div className="space-y-3">
                                <div>
                                    <label className="block text-xs text-slate-500 mb-1">Fast Period (comma separated)</label>
                                    <input
                                        type="text"
                                        value={fastPeriodRange.join(',')}
                                        onChange={(e) => setFastPeriodRange(e.target.value.split(',').map(Number))}
                                        className="w-full p-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs text-slate-500 mb-1">Slow Period (comma separated)</label>
                                    <input
                                        type="text"
                                        value={slowPeriodRange.join(',')}
                                        onChange={(e) => setSlowPeriodRange(e.target.value.split(',').map(Number))}
                                        className="w-full p-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Run Button */}
                        <button
                            onClick={runOptimization}
                            disabled={isLoading}
                            className="w-full py-3 px-4 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700 text-white rounded-xl font-semibold flex items-center justify-center gap-2 shadow-lg shadow-amber-500/20 transition-all disabled:opacity-50"
                        >
                            {isLoading ? (
                                <><RefreshCw size={18} className="animate-spin" /> Optimizing...</>
                            ) : (
                                <><Play size={18} /> Run Optimization</>
                            )}
                        </button>
                    </div>
                </div>

                {/* Results Panel */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Error */}
                    {error && (
                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/50 rounded-xl p-4 flex items-start gap-3">
                            <AlertTriangle className="text-red-500 mt-0.5" size={20} />
                            <div>
                                <p className="font-semibold text-red-700 dark:text-red-400">Optimization Failed</p>
                                <p className="text-sm text-red-600 dark:text-red-300">{error}</p>
                            </div>
                        </div>
                    )}

                    {/* Results */}
                    {result && (
                        <>
                            {/* Success Header */}
                            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-900/50 rounded-xl p-4 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <CheckCircle className="text-green-500" size={24} />
                                    <div>
                                        <p className="font-semibold text-green-700 dark:text-green-400">Optimization Complete</p>
                                        <p className="text-sm text-green-600 dark:text-green-300">
                                            {result.method} • {result.valid_combinations}/{result.total_combinations} valid • {result.elapsed_seconds.toFixed(1)}s
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Best Parameters */}
                            <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700">
                                <h3 className="text-lg font-bold text-slate-800 dark:text-white mb-4">Best Parameters</h3>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {Object.entries(result.best_params).map(([key, value]) => (
                                        <div key={key} className="bg-slate-50 dark:bg-slate-900 rounded-lg p-3">
                                            <span className="text-xs text-slate-500">{key}</span>
                                            <p className="text-lg font-bold text-amber-600">{String(value)}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Best Metrics */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <MetricCard label="Sharpe Ratio" value={result.best_metrics.sharpe_ratio} icon={Activity} color="blue" />
                                <MetricCard label="Total Return" value={result.best_metrics.total_return_pct} icon={TrendingUp} color="green" suffix="%" />
                                <MetricCard label="Max Drawdown" value={-result.best_metrics.max_drawdown_pct} icon={Shield} color="orange" suffix="%" />
                                <MetricCard label="Win Rate" value={result.best_metrics.win_rate} icon={Target} color="purple" suffix="%" />
                            </div>

                            {/* Top 5 Results */}
                            <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700">
                                <h3 className="text-lg font-bold text-slate-800 dark:text-white mb-4">Top 5 Configurations</h3>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="text-left text-slate-500 border-b border-slate-200 dark:border-slate-700">
                                                <th className="pb-3">Rank</th>
                                                <th className="pb-3">Fast</th>
                                                <th className="pb-3">Slow</th>
                                                <th className="pb-3">Sharpe</th>
                                                <th className="pb-3">Return</th>
                                                <th className="pb-3">Drawdown</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {result.top_5?.map((r, i) => (
                                                <tr key={i} className={`border-b border-slate-100 dark:border-slate-700 ${i === 0 ? 'bg-amber-50 dark:bg-amber-900/20' : ''}`}>
                                                    <td className="py-3 font-bold">{i + 1}</td>
                                                    <td className="py-3">{r.params.fast_period}</td>
                                                    <td className="py-3">{r.params.slow_period}</td>
                                                    <td className="py-3 text-blue-600">{r.metrics.sharpe_ratio?.toFixed(2)}</td>
                                                    <td className={`py-3 ${r.metrics.total_return_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                                        {r.metrics.total_return_pct?.toFixed(1)}%
                                                    </td>
                                                    <td className="py-3 text-orange-600">-{r.metrics.max_drawdown_pct?.toFixed(1)}%</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </>
                    )}

                    {/* Empty State */}
                    {!result && !error && !isLoading && (
                        <div className="bg-white dark:bg-slate-800 rounded-2xl p-12 border border-slate-200 dark:border-slate-700 flex flex-col items-center justify-center text-center">
                            <div className="w-20 h-20 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center mb-4">
                                <FlaskConical size={40} className="text-slate-400" />
                            </div>
                            <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">Ready to Optimize</h3>
                            <p className="text-sm text-slate-500 max-w-md">
                                Configure parameter ranges and click "Run Optimization" to find the best strategy parameters.
                            </p>
                        </div>
                    )}

                    {/* Loading */}
                    {isLoading && (
                        <div className="bg-white dark:bg-slate-800 rounded-2xl p-12 border border-slate-200 dark:border-slate-700 flex flex-col items-center justify-center">
                            <RefreshCw size={48} className="text-amber-500 animate-spin mb-4" />
                            <p className="text-slate-600 dark:text-slate-300">Running {optimizationMethod} optimization...</p>
                            <p className="text-sm text-slate-400">This may take a while</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default StrategyLab;
