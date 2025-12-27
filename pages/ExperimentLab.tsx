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
    Calendar,
    Filter,
    ChevronDown,
    ChevronRight,
    Award,
    Zap,
    Info,
    AlertCircle
} from 'lucide-react';
import SymbolSearch from '../components/SymbolSearch';
import { ExperimentLabHelpGuide } from '../components/HelpGuide';

// Strategy categories
const CATEGORIES = [
    { id: 'A', name: 'Single-Logic Baselines', count: 10, color: 'emerald' },
    { id: 'B', name: 'Price + Momentum', count: 8, color: 'blue' },
    { id: 'C', name: 'Breakout + Filter', count: 7, color: 'yellow' },
    { id: 'D', name: 'Trend + Momentum', count: 9, color: 'orange' },
    { id: 'E', name: 'Volume-Confirmed', count: 6, color: 'red' },
    { id: 'F', name: 'Mean Reversion', count: 6, color: 'purple' },
    { id: 'G', name: 'Multi-Indicator', count: 7, color: 'gray' },
    { id: 'H', name: 'Multi-Timeframe', count: 6, color: 'pink' },
    { id: 'I', name: 'Pattern + Indicator', count: 6, color: 'cyan' },
    { id: 'J', name: 'Experimental/Quant', count: 5, color: 'amber' },
];

interface Strategy {
    id: number;
    name: string;
    category: string;
    description: string;
}

interface BacktestResult {
    strategy_id: number;
    strategy_name: string;
    category: string;
    metrics: {
        total_trades: number;
        winning_trades: number;
        losing_trades: number;
        win_rate: number;
        total_pnl: number;
        total_return_pct: number;
        cagr: number;
        max_drawdown: number;
        max_drawdown_pct: number;
        sharpe_ratio: number;
        sortino_ratio: number;
        calmar_ratio: number;
        profit_factor: number;
        avg_win: number;
        avg_loss: number;
        avg_holding_period: number;
        initial_capital: number;
        final_capital: number;
        equity_curve: number[];
    };
    run_time_seconds: number;
}

const ExperimentLab: React.FC = () => {
    // Form state
    const [selectedSymbols, setSelectedSymbols] = useState<string[]>(['RELIANCE']);
    const [selectedStrategies, setSelectedStrategies] = useState<number[]>([1]);
    const [timeframe, setTimeframe] = useState('1D');
    const [startDate, setStartDate] = useState('2023-01-01');
    const [endDate, setEndDate] = useState('2024-01-01');
    const [initialCapital, setInitialCapital] = useState(1000000);
    const [riskMode, setRiskMode] = useState('percent_capital');
    const [riskPercent, setRiskPercent] = useState(2);

    // UI state
    const [strategies, setStrategies] = useState<Strategy[]>([]);
    const [expandedCategory, setExpandedCategory] = useState<string | null>('A');
    const [isLoading, setIsLoading] = useState(false);
    const [results, setResults] = useState<BacktestResult[] | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchStrategies();
    }, []);

    const fetchStrategies = async () => {
        try {
            const response = await fetch('/api/v1/experiment-lab/strategies');
            if (response.ok) {
                const data = await response.json();
                setStrategies(data);
            }
        } catch (err) {
            console.error('Failed to fetch strategies:', err);
        }
    };


    const toggleStrategy = (id: number) => {
        setSelectedStrategies(prev =>
            prev.includes(id)
                ? prev.filter(s => s !== id)
                : [...prev, id]
        );
    };

    const selectCategory = (categoryId: string) => {
        const categoryStrategies = strategies
            .filter(s => s.category === categoryId)
            .map(s => s.id);

        const allSelected = categoryStrategies.every(id => selectedStrategies.includes(id));

        if (allSelected) {
            setSelectedStrategies(prev => prev.filter(id => !categoryStrategies.includes(id)));
        } else {
            setSelectedStrategies(prev => [...new Set([...prev, ...categoryStrategies])]);
        }
    };

    const runBacktest = async () => {
        if (selectedStrategies.length === 0) {
            setError('Please select at least one strategy');
            return;
        }

        if (selectedSymbols.length === 0) {
            setError('Please select a symbol');
            return;
        }

        setIsLoading(true);
        setError(null);
        setResults(null);

        try {
            const response = await fetch('/api/v1/experiment-lab/backtest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: selectedSymbols[0],
                    strategy_ids: selectedStrategies,
                    timeframe,
                    start_date: startDate,
                    end_date: endDate,
                    initial_capital: initialCapital,
                    risk_mode: riskMode,
                    risk_percent: riskPercent
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Backtest failed');
            }

            const data = await response.json();
            setResults(data.results);
        } catch (err: any) {
            setError(err.message || 'Failed to run backtest');
        } finally {
            setIsLoading(false);
        }
    };

    const MetricCard = ({ label, value, icon: Icon, color = 'blue', suffix = '', prefix = '' }: any) => (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
            <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
                <Icon size={16} className={`text-${color}-500`} />
            </div>
            <span className={`text-xl font-bold text-${color}-600 dark:text-${color}-400`}>
                {prefix}{typeof value === 'number' ? value.toFixed(2) : value}{suffix}
            </span>
        </div>
    );

    const getCategoryColor = (cat: string) => {
        const category = CATEGORIES.find(c => c.id === cat);
        return category?.color || 'gray';
    };

    return (
        <div className="h-full flex flex-col gap-6 overflow-auto p-1">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-3 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl shadow-lg shadow-violet-500/20">
                        <FlaskConical size={24} className="text-white" />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Strategy Experiment Lab</h1>
                            <span className="px-2 py-0.5 bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400 text-xs font-semibold rounded-full">BETA</span>
                        </div>
                        <p className="text-sm text-slate-500 dark:text-slate-400">70 Strategy Combinations • Backtesting Only</p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                        <AlertCircle size={16} className="text-amber-600" />
                        <span className="text-xs text-amber-700 dark:text-amber-400 font-medium">Simulation Only - No Live Trading</span>
                    </div>
                    <ExperimentLabHelpGuide />
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
                {/* Strategy Selector Panel */}
                <div className="xl:col-span-1 bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
                    <div className="p-4 border-b border-slate-200 dark:border-slate-700">
                        <h2 className="font-bold text-slate-800 dark:text-white flex items-center gap-2">
                            <Layers size={18} />
                            Strategies ({selectedStrategies.length} selected)
                        </h2>
                    </div>
                    <div className="max-h-[500px] overflow-y-auto">
                        {CATEGORIES.map(category => {
                            const categoryStrategies = strategies.filter(s => s.category === category.id);
                            const selectedCount = categoryStrategies.filter(s => selectedStrategies.includes(s.id)).length;
                            const isExpanded = expandedCategory === category.id;

                            return (
                                <div key={category.id} className="border-b border-slate-100 dark:border-slate-700">
                                    <div
                                        className="flex items-center justify-between p-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors"
                                        onClick={() => setExpandedCategory(isExpanded ? null : category.id)}
                                    >
                                        <div className="flex items-center gap-2">
                                            {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                            <span className={`w-6 h-6 rounded-full bg-${category.color}-100 dark:bg-${category.color}-900/30 text-${category.color}-600 dark:text-${category.color}-400 text-xs font-bold flex items-center justify-center`}>
                                                {category.id}
                                            </span>
                                            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{category.name}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-slate-500">{selectedCount}/{category.count}</span>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); selectCategory(category.id); }}
                                                className="text-xs px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                                            >
                                                {selectedCount === category.count ? 'Clear' : 'All'}
                                            </button>
                                        </div>
                                    </div>
                                    {isExpanded && (
                                        <div className="pl-8 pr-3 pb-3 space-y-1">
                                            {categoryStrategies.map(strategy => (
                                                <label
                                                    key={strategy.id}
                                                    className="flex items-start gap-2 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/30 cursor-pointer transition-colors"
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedStrategies.includes(strategy.id)}
                                                        onChange={() => toggleStrategy(strategy.id)}
                                                        className="mt-1 rounded border-slate-300 text-violet-600 focus:ring-violet-500"
                                                    />
                                                    <div>
                                                        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                                                            {strategy.id}. {strategy.name}
                                                        </span>
                                                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                                            {strategy.description}
                                                        </p>
                                                    </div>
                                                </label>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Configuration + Results Panel */}
                <div className="xl:col-span-3 space-y-6">
                    {/* Configuration */}
                    <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
                        <h2 className="text-lg font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                            <Settings2 size={18} />
                            Backtest Configuration
                        </h2>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">
                                    Target Symbol
                                </label>
                                <SymbolSearch
                                    selectedSymbols={selectedSymbols}
                                    onSymbolsChange={setSelectedSymbols}
                                    timeframe={timeframe}
                                    maxSymbols={1}
                                />
                            </div>

                            {/* Timeframe */}
                            <div>
                                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Timeframe</label>
                                <select
                                    value={timeframe}
                                    onChange={(e) => setTimeframe(e.target.value)}
                                    className="w-full p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                >
                                    <option value="5m">5 Minutes</option>
                                    <option value="15m">15 Minutes</option>
                                    <option value="30m">30 Minutes</option>
                                    <option value="1H">1 Hour</option>
                                    <option value="1D">Daily</option>
                                </select>
                            </div>

                            {/* Start Date */}
                            <div>
                                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Start Date</label>
                                <input
                                    type="date"
                                    value={startDate}
                                    onChange={(e) => setStartDate(e.target.value)}
                                    className="w-full p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                />
                            </div>

                            {/* End Date */}
                            <div>
                                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">End Date</label>
                                <input
                                    type="date"
                                    value={endDate}
                                    onChange={(e) => setEndDate(e.target.value)}
                                    className="w-full p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                />
                            </div>

                            {/* Initial Capital */}
                            <div>
                                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Capital (₹)</label>
                                <input
                                    type="number"
                                    value={initialCapital}
                                    onChange={(e) => setInitialCapital(Number(e.target.value))}
                                    className="w-full p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                />
                            </div>

                            {/* Risk Mode */}
                            <div>
                                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Risk Mode</label>
                                <select
                                    value={riskMode}
                                    onChange={(e) => setRiskMode(e.target.value)}
                                    className="w-full p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                >
                                    <option value="percent_capital">% of Capital</option>
                                    <option value="fixed_amount">Fixed Amount</option>
                                    <option value="atr_based">ATR-Based</option>
                                </select>
                            </div>

                            {/* Risk Percent */}
                            <div>
                                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Risk %</label>
                                <input
                                    type="number"
                                    value={riskPercent}
                                    onChange={(e) => setRiskPercent(Number(e.target.value))}
                                    step="0.5"
                                    min="0.5"
                                    max="10"
                                    className="w-full p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                />
                            </div>

                            {/* Run Button */}
                            <div className="flex items-end">
                                <button
                                    onClick={runBacktest}
                                    disabled={isLoading || selectedStrategies.length === 0}
                                    className="w-full py-2.5 px-4 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white rounded-lg font-semibold flex items-center justify-center gap-2 shadow-lg shadow-violet-500/20 transition-all disabled:opacity-50"
                                >
                                    {isLoading ? (
                                        <><RefreshCw size={18} className="animate-spin" /> Running...</>
                                    ) : (
                                        <><Play size={18} /> Run Backtest</>
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/50 rounded-xl p-4 flex items-start gap-3">
                            <AlertTriangle className="text-red-500 mt-0.5" size={20} />
                            <div>
                                <p className="font-semibold text-red-700 dark:text-red-400">Backtest Failed</p>
                                <p className="text-sm text-red-600 dark:text-red-300">{error}</p>
                            </div>
                        </div>
                    )}

                    {/* Results */}
                    {results && results.length > 0 && (
                        <div className="space-y-6">
                            {/* Summary */}
                            <div className="bg-gradient-to-r from-violet-50 to-purple-50 dark:from-violet-900/20 dark:to-purple-900/20 border border-violet-200 dark:border-violet-800/50 rounded-xl p-4">
                                <div className="flex items-center gap-3">
                                    <CheckCircle className="text-violet-500" size={24} />
                                    <div>
                                        <p className="font-semibold text-violet-700 dark:text-violet-400">Backtest Complete</p>
                                        <p className="text-sm text-violet-600 dark:text-violet-300">
                                            {results.length} strategies tested on {selectedSymbols[0]} ({timeframe})
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Results Table */}
                            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
                                <div className="p-4 border-b border-slate-200 dark:border-slate-700">
                                    <h3 className="font-bold text-slate-800 dark:text-white flex items-center gap-2">
                                        <BarChart3 size={18} />
                                        Strategy Results
                                    </h3>
                                </div>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="text-left text-slate-500 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
                                                <th className="px-4 py-3">Strategy</th>
                                                <th className="px-4 py-3 text-right">Return %</th>
                                                <th className="px-4 py-3 text-right">Sharpe</th>
                                                <th className="px-4 py-3 text-right">Max DD %</th>
                                                <th className="px-4 py-3 text-right">Win Rate</th>
                                                <th className="px-4 py-3 text-right">Trades</th>
                                                <th className="px-4 py-3 text-right">P/L (₹)</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {results.sort((a, b) => b.metrics.total_return_pct - a.metrics.total_return_pct).map((result, i) => (
                                                <tr
                                                    key={result.strategy_id}
                                                    className={`border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/30 ${i === 0 ? 'bg-violet-50 dark:bg-violet-900/10' : ''}`}
                                                >
                                                    <td className="px-4 py-3">
                                                        <div className="flex items-center gap-2">
                                                            {i === 0 && <Award size={16} className="text-amber-500" />}
                                                            <span className={`w-5 h-5 rounded bg-${getCategoryColor(result.category)}-100 dark:bg-${getCategoryColor(result.category)}-900/30 text-${getCategoryColor(result.category)}-600 text-xs font-bold flex items-center justify-center`}>
                                                                {result.category}
                                                            </span>
                                                            <span className="font-medium text-slate-700 dark:text-slate-300">{result.strategy_name}</span>
                                                        </div>
                                                    </td>
                                                    <td className={`px-4 py-3 text-right font-bold ${result.metrics.total_return_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                                        {result.metrics.total_return_pct >= 0 ? '+' : ''}{result.metrics.total_return_pct.toFixed(2)}%
                                                    </td>
                                                    <td className="px-4 py-3 text-right text-blue-600 dark:text-blue-400 font-medium">
                                                        {result.metrics.sharpe_ratio.toFixed(2)}
                                                    </td>
                                                    <td className="px-4 py-3 text-right text-orange-600 dark:text-orange-400">
                                                        -{result.metrics.max_drawdown_pct.toFixed(1)}%
                                                    </td>
                                                    <td className="px-4 py-3 text-right">
                                                        {result.metrics.win_rate.toFixed(1)}%
                                                    </td>
                                                    <td className="px-4 py-3 text-right text-slate-600 dark:text-slate-400">
                                                        {result.metrics.total_trades}
                                                    </td>
                                                    <td className={`px-4 py-3 text-right font-medium ${result.metrics.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                                        ₹{result.metrics.total_pnl.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            {/* Best Strategy Details */}
                            {results.length > 0 && (
                                <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
                                    <h3 className="text-lg font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                                        <Award size={18} className="text-amber-500" />
                                        Best Performer: {results.sort((a, b) => b.metrics.total_return_pct - a.metrics.total_return_pct)[0].strategy_name}
                                    </h3>
                                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                                        {(() => {
                                            const best = results.sort((a, b) => b.metrics.total_return_pct - a.metrics.total_return_pct)[0];
                                            return (
                                                <>
                                                    <MetricCard label="Total Return" value={best.metrics.total_return_pct} icon={TrendingUp} color="green" suffix="%" />
                                                    <MetricCard label="CAGR" value={best.metrics.cagr} icon={Activity} color="blue" suffix="%" />
                                                    <MetricCard label="Sharpe Ratio" value={best.metrics.sharpe_ratio} icon={Target} color="purple" />
                                                    <MetricCard label="Max Drawdown" value={-best.metrics.max_drawdown_pct} icon={Shield} color="orange" suffix="%" />
                                                    <MetricCard label="Win Rate" value={best.metrics.win_rate} icon={Zap} color="emerald" suffix="%" />
                                                    <MetricCard label="Profit Factor" value={best.metrics.profit_factor} icon={DollarSign} color="cyan" />
                                                </>
                                            );
                                        })()}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Empty State */}
                    {!results && !error && !isLoading && (
                        <div className="bg-white dark:bg-slate-800 rounded-2xl p-12 border border-slate-200 dark:border-slate-700 flex flex-col items-center justify-center text-center">
                            <div className="w-20 h-20 bg-gradient-to-br from-violet-100 to-purple-100 dark:from-violet-900/30 dark:to-purple-900/30 rounded-full flex items-center justify-center mb-4">
                                <FlaskConical size={40} className="text-violet-500" />
                            </div>
                            <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">Ready to Experiment</h3>
                            <p className="text-sm text-slate-500 max-w-md mb-4">
                                Select strategies from the panel, configure your backtest parameters, and click "Run Backtest" to see results.
                            </p>
                            <div className="flex gap-4 text-xs text-slate-400">
                                <span className="flex items-center gap-1"><CheckCircle size={14} /> 70 Strategies</span>
                                <span className="flex items-center gap-1"><CheckCircle size={14} /> 5 Timeframes</span>
                                <span className="flex items-center gap-1"><CheckCircle size={14} /> Full Metrics</span>
                            </div>
                        </div>
                    )}

                    {/* Loading */}
                    {isLoading && (
                        <div className="bg-white dark:bg-slate-800 rounded-2xl p-12 border border-slate-200 dark:border-slate-700 flex flex-col items-center justify-center">
                            <RefreshCw size={48} className="text-violet-500 animate-spin mb-4" />
                            <p className="text-slate-600 dark:text-slate-300">Running backtest for {selectedStrategies.length} strategies...</p>
                            <p className="text-sm text-slate-400">This may take a moment</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ExperimentLab;
