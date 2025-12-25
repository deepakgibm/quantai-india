import React, { useState, useEffect } from 'react';
import {
    LineChart as LineChartIcon,
    Play,
    BarChart3,
    TrendingUp,
    Settings2,
    RefreshCw,
    CheckCircle,
    AlertTriangle,
    Calendar,
    DollarSign,
    Percent,
    Activity,
    Layers,
    Target,
    Shield
} from 'lucide-react';

// Chart Components
import EquityCurveChart from '../components/charts/EquityCurveChart';
import DrawdownChart from '../components/charts/DrawdownChart';
import MonteCarloFanChart from '../components/charts/MonteCarloFanChart';
import DistributionComparisonChart from '../components/charts/DistributionComparisonChart';

interface BacktestResult {
    status: string;
    run_id: string;
    strategy: string;
    symbol: string;
    metrics: {
        total_return_pct: number;
        sharpe_ratio: number;
        max_drawdown_pct: number;
        win_rate: number;
        total_trades: number;
        profit_factor: number;
        cagr: number;
        final_equity: number;
    };
    trade_count: number;
    duration_seconds: number;
    equity_curve?: { date: string; equity: number }[];
    drawdown_curve?: { date: string; drawdown: number }[];
    trade_returns?: number[];
    monte_carlo?: number[][];
}

interface Strategy {
    name: string;
    description: string;
    default_params: Record<string, any>;
}

// Helper functions to generate sample chart data
const generateSampleEquityCurve = (initial: number, returnPct: number): { date: string; equity: number }[] => {
    const data = [];
    const days = 252;
    let equity = initial;
    const dailyReturn = returnPct / 100 / days;
    const volatility = 0.015;

    for (let i = 0; i < days; i++) {
        const date = new Date(2023, 0, 1);
        date.setDate(date.getDate() + i);
        const randomFactor = 1 + dailyReturn + (Math.random() - 0.5) * volatility;
        equity *= randomFactor;
        data.push({ date: date.toISOString().slice(0, 10), equity });
    }
    return data;
};

const generateSampleDrawdown = (maxDD: number): { date: string; drawdown: number }[] => {
    const data = [];
    const days = 252;

    for (let i = 0; i < days; i++) {
        const date = new Date(2023, 0, 1);
        date.setDate(date.getDate() + i);
        // Create a wave pattern that reaches the max drawdown
        const phase = Math.sin(i * 0.05) * 0.5 + 0.5;
        const dd = -Math.abs(maxDD / 100) * phase * (0.3 + Math.random() * 0.7);
        data.push({ date: date.toISOString().slice(0, 10), drawdown: dd });
    }
    return data;
};

const generateSampleReturns = (numTrades: number): number[] => {
    const returns = [];
    for (let i = 0; i < numTrades; i++) {
        // Generate returns with slight positive bias
        returns.push((Math.random() - 0.45) * 0.1);
    }
    return returns;
};

const generateSampleMonteCarlo = (initial: number, numPaths: number, steps: number): number[][] => {
    const paths = [];
    for (let p = 0; p < numPaths; p++) {
        const path = [initial];
        for (let s = 1; s < steps; s++) {
            const growth = 1 + (Math.random() - 0.48) * 0.02;
            path.push(path[s - 1] * growth);
        }
        paths.push(path);
    }
    return paths;
};

const generatePlainEnglishSummary = (m: any, s: string, sym: string) => {
    const pf = m.profit_factor;
    const wr = m.win_rate;
    const dd = Math.abs(m.max_drawdown_pct);
    const tr = m.total_trades;
    const ret = m.total_return_pct;

    let verdict = "";
    let whatHappened = "";
    let riskExp = "";
    let reliability = "";
    let style = "";
    let classification: 'Strong' | 'Moderate' | 'Weak' = 'Moderate';

    // 1. Headline Verdict
    if (pf > 1.5 && dd < 15) {
        verdict = "This strategy performed consistently on this stock with controlled risk.";
        classification = 'Strong';
    } else if (ret > 0 && dd > 20) {
        verdict = "This strategy was profitable but experienced sharp temporary losses.";
        classification = 'Moderate';
    } else if (ret <= 0 || pf < 1.1) {
        verdict = "This strategy did not perform reliably for this stock.";
        classification = 'Weak';
    } else {
        verdict = "This strategy showed moderate performance with balanced risk and returns.";
    }

    // 2. What Happened
    if (pf > 1.3) {
        whatHappened = "Over the tested period, the strategy made profits more often than losses, showing a clear mathematical edge.";
    } else if (pf >= 1.0) {
        whatHappened = "The strategy barely broke even; while it didn't lose much, the gains were nearly equal to the losses.";
    } else {
        whatHappened = "The strategy struggled to maintain profitability, as losses outweighed the gains over the period.";
    }

    // 3. Risk Explanation
    if (dd < 10) {
        riskExp = "At its worst point, the strategy experienced very small temporary declines. This indicates a very stable path for your capital.";
    } else if (dd < 25) {
        riskExp = "At its worst point, the strategy temporarily lost a noticeable portion of its value before recovering. Short-term losses could feel uncomfortable but are part of the strategy's cycle.";
    } else {
        riskExp = "This strategy experienced heavy temporary losses. You would need significant emotional discipline to stay invested during its worst periods.";
    }

    // 4. Consistency
    if (tr > 100) {
        reliability = "Profits came from a large number of trades, making these historical results more statistically reliable.";
    } else if (tr > 30) {
        reliability = "The results are based on a moderate number of trades. While promising, they carry more uncertainty than a high-frequency system.";
    } else {
        reliability = "Most gains came from a very small number of trades. This makes the results less dependable and possibly due to specific lucky moments.";
    }

    // 5. Style
    if (dd > 25 || wr < 40) {
        style = "This behavior suggests a More Aggressive style where you must tolerate large swings for potential returns.";
    } else if (dd < 12 && wr > 50) {
        style = "The steady growth suggests a More Conservative style which prioritizes capital protection.";
    } else {
        style = "This strategy works only in specific market conditions and requires patience.";
    }

    return { verdict, whatHappened, riskExp, reliability, style, classification };
};

const BacktestSummaryCard = ({ result }: { result: BacktestResult }) => {
    const summary = generatePlainEnglishSummary(result.metrics, result.strategy, result.symbol);

    return (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-xl shadow-slate-200/20 dark:shadow-none animate-in slide-in-from-bottom duration-500">
            <div className="p-6 border-b border-slate-100 dark:border-slate-700 bg-gradient-to-r from-slate-50 to-white dark:from-slate-800 dark:to-slate-800/50 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-violet-500 rounded-xl shadow-lg shadow-violet-500/20">
                        <BarChart3 size={20} className="text-white" />
                    </div>
                    <h3 className="text-lg font-black text-slate-800 dark:text-white tracking-tight">Backtest Summary</h3>
                </div>
                <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border ${summary.classification === 'Strong' ? 'bg-emerald-50 border-emerald-200 text-emerald-600' :
                    summary.classification === 'Moderate' ? 'bg-amber-50 border-amber-200 text-amber-600' :
                        'bg-rose-50 border-rose-200 text-rose-600'
                    }`}>
                    {summary.classification} Performance
                </span>
            </div>

            <div className="p-8 space-y-8">
                {/* 1. Headline Verdict */}
                <div>
                    <p className="text-xl font-bold text-slate-800 dark:text-white leading-tight">
                        "{summary.verdict}"
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* 2. What Happened */}
                    <div className="space-y-2">
                        <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                            <Activity size={14} className="text-violet-500" /> Performance Narrative
                        </h4>
                        <p className="text-sm text-slate-600 dark:text-slate-300 font-medium leading-relaxed">
                            {summary.whatHappened}
                        </p>
                    </div>

                    {/* 3. Risk Explanation */}
                    <div className="space-y-2">
                        <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                            <Shield size={14} className="text-rose-500" /> Risk in Human Terms
                        </h4>
                        <p className="text-sm text-slate-600 dark:text-slate-300 font-medium leading-relaxed">
                            {summary.riskExp}
                        </p>
                    </div>

                    {/* 4. Consistency */}
                    <div className="space-y-2">
                        <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                            <Target size={14} className="text-cyan-500" /> Reliability Check
                        </h4>
                        <p className="text-sm text-slate-600 dark:text-slate-300 font-medium leading-relaxed">
                            {summary.reliability}
                        </p>
                    </div>

                    {/* 5. Style Suitability */}
                    <div className="space-y-2">
                        <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                            <Layers size={14} className="text-amber-500" /> Suitability Profile
                        </h4>
                        <p className="text-sm text-slate-600 dark:text-slate-300 font-medium leading-relaxed italic">
                            "{summary.style}"
                        </p>
                    </div>
                </div>

                {/* 6. Mandatory Disclaimer */}
                <div className="pt-6 border-t border-slate-100 dark:border-slate-700">
                    <div className="flex items-start gap-3 p-4 bg-slate-50 dark:bg-slate-900/50 rounded-2xl border border-slate-100 dark:border-slate-700/50">
                        <Shield size={16} className="text-slate-400 shrink-0 mt-0.5" />
                        <p className="text-[11px] text-slate-400 font-bold uppercase leading-snug">
                            Mandatory Disclaimer: <span className="font-medium normal-case block mt-1">This analysis is based on historical data. Market conditions change, and similar results may not occur in the future. This is not financial advice.</span>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

const QuantBot: React.FC = () => {
    // Form state
    const [symbol, setSymbol] = useState('RELIANCE');
    const [strategy, setStrategy] = useState('MACrossover');
    const [startDate, setStartDate] = useState('2023-01-01');
    const [endDate, setEndDate] = useState('2024-01-01');
    const [initialCapital, setInitialCapital] = useState(1000000);

    // Strategy params
    const [fastPeriod, setFastPeriod] = useState(10);
    const [slowPeriod, setSlowPeriod] = useState(30);
    const [maType, setMaType] = useState('EMA');
    const [positionSizePct, setPositionSizePct] = useState(10);

    // Results state
    const [isLoading, setIsLoading] = useState(false);
    const [result, setResult] = useState<BacktestResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Available symbols and strategies
    const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
    const [strategies, setStrategies] = useState<Strategy[]>([]);

    // Fetch available data on mount
    useEffect(() => {
        fetchStrategies();
        fetchSymbols();
    }, []);

    const fetchStrategies = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/quant/strategies');
            if (response.ok) {
                const data = await response.json();
                setStrategies(data.strategies || []);
            }
        } catch (err) {
            console.error('Failed to fetch strategies');
        }
    };

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

    const runBacktest = async () => {
        setIsLoading(true);
        setError(null);
        setResult(null);

        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch('http://localhost:8000/api/quant/backtest/run', {
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
                    params: {
                        fast_period: fastPeriod,
                        slow_period: slowPeriod,
                        ma_type: maType,
                        position_size_pct: positionSizePct
                    }
                })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Backtest failed');
            }

            const data = await response.json();
            setResult(data);
        } catch (err: any) {
            setError(err.message || 'Failed to run backtest');
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
                    <div className="p-3 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl shadow-lg shadow-violet-500/20">
                        <LineChartIcon size={24} className="text-white" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Backtest</h1>
                        <p className="text-sm text-slate-500 dark:text-slate-400">Production-Grade Backtesting Engine</p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Configuration Panel */}
                <div className="lg:col-span-1 bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
                    <h2 className="text-lg font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                        <Settings2 size={18} /> Configuration
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

                        {/* Strategy */}
                        <div>
                            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Strategy</label>
                            <select
                                value={strategy}
                                onChange={(e) => setStrategy(e.target.value)}
                                className="w-full p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white"
                            >
                                <option value="MACrossover">MA Crossover</option>
                            </select>
                        </div>

                        {/* Date Range */}
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Start Date</label>
                                <input
                                    type="date"
                                    value={startDate}
                                    onChange={(e) => setStartDate(e.target.value)}
                                    className="w-full p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">End Date</label>
                                <input
                                    type="date"
                                    value={endDate}
                                    onChange={(e) => setEndDate(e.target.value)}
                                    className="w-full p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white"
                                />
                            </div>
                        </div>

                        {/* Capital */}
                        <div>
                            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Initial Capital (₹)</label>
                            <input
                                type="number"
                                value={initialCapital}
                                onChange={(e) => setInitialCapital(Number(e.target.value))}
                                className="w-full p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white"
                            />
                        </div>

                        {/* Strategy Params */}
                        <div className="pt-4 border-t border-slate-200 dark:border-slate-700">
                            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Strategy Parameters</h3>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-xs text-slate-500 mb-1">Fast Period</label>
                                    <input
                                        type="number"
                                        value={fastPeriod}
                                        onChange={(e) => setFastPeriod(Number(e.target.value))}
                                        className="w-full p-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs text-slate-500 mb-1">Slow Period</label>
                                    <input
                                        type="number"
                                        value={slowPeriod}
                                        onChange={(e) => setSlowPeriod(Number(e.target.value))}
                                        className="w-full p-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-3 mt-3">
                                <div>
                                    <label className="block text-xs text-slate-500 mb-1">MA Type</label>
                                    <select
                                        value={maType}
                                        onChange={(e) => setMaType(e.target.value)}
                                        className="w-full p-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                    >
                                        <option value="EMA">EMA</option>
                                        <option value="SMA">SMA</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs text-slate-500 mb-1">Position %</label>
                                    <input
                                        type="number"
                                        value={positionSizePct}
                                        onChange={(e) => setPositionSizePct(Number(e.target.value))}
                                        className="w-full p-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Run Button */}
                        <button
                            onClick={runBacktest}
                            disabled={isLoading}
                            className="w-full py-3 px-4 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white rounded-xl font-semibold flex items-center justify-center gap-2 shadow-lg shadow-violet-500/20 transition-all disabled:opacity-50"
                        >
                            {isLoading ? (
                                <><RefreshCw size={18} className="animate-spin" /> Running Backtest...</>
                            ) : (
                                <><Play size={18} /> Run Backtest</>
                            )}
                        </button>
                    </div>
                </div>

                {/* Results Panel */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Error State */}
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
                    {result && (
                        <>
                            {/* Success Header */}
                            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-900/50 rounded-xl p-4 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <CheckCircle className="text-green-500" size={24} />
                                    <div>
                                        <p className="font-semibold text-green-700 dark:text-green-400">Backtest Complete</p>
                                        <p className="text-sm text-green-600 dark:text-green-300">
                                            Run ID: {result.run_id} • {result.trade_count} trades • {result.duration_seconds.toFixed(2)}s
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Metrics Grid */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <MetricCard
                                    label="Total Return"
                                    value={result.metrics.total_return_pct}
                                    icon={TrendingUp}
                                    color={result.metrics.total_return_pct >= 0 ? 'green' : 'red'}
                                    suffix="%"
                                />
                                <MetricCard
                                    label="Sharpe Ratio"
                                    value={result.metrics.sharpe_ratio}
                                    icon={Activity}
                                    color="blue"
                                />
                                <MetricCard
                                    label="Max Drawdown"
                                    value={-result.metrics.max_drawdown_pct}
                                    icon={Shield}
                                    color="orange"
                                    suffix="%"
                                />
                                <MetricCard
                                    label="Win Rate"
                                    value={result.metrics.win_rate}
                                    icon={Target}
                                    color="purple"
                                    suffix="%"
                                />
                                <MetricCard
                                    label="CAGR"
                                    value={result.metrics.cagr}
                                    icon={BarChart3}
                                    color="indigo"
                                    suffix="%"
                                />
                                <MetricCard
                                    label="Profit Factor"
                                    value={result.metrics.profit_factor}
                                    icon={DollarSign}
                                    color="emerald"
                                />
                                <MetricCard
                                    label="Total Trades"
                                    value={result.metrics.total_trades}
                                    icon={Layers}
                                    color="slate"
                                />
                                <MetricCard
                                    label="Final Equity"
                                    value={`₹${(result.metrics.final_equity / 100000).toFixed(1)}L`}
                                    icon={DollarSign}
                                    color="green"
                                />
                            </div>

                            {/* Charts Section */}
                            <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700">
                                <h3 className="text-lg font-bold text-slate-800 dark:text-white mb-4">📈 Performance Charts</h3>

                                {/* Equity Curve */}
                                <div className="mb-6">
                                    <EquityCurveChart
                                        data={result.equity_curve || generateSampleEquityCurve(initialCapital, result.metrics.total_return_pct)}
                                        initialCapital={initialCapital}
                                        height={280}
                                    />
                                </div>

                                {/* Drawdown Chart */}
                                <div className="mb-6">
                                    <DrawdownChart
                                        data={result.drawdown_curve || generateSampleDrawdown(result.metrics.max_drawdown_pct)}
                                        height={180}
                                    />
                                </div>
                            </div>

                            {/* Distribution Comparison */}
                            <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700">
                                <h3 className="text-lg font-bold text-slate-800 dark:text-white mb-4">📊 Distribution Analysis</h3>
                                <DistributionComparisonChart
                                    backtestReturns={result.trade_returns || generateSampleReturns(result.metrics.total_trades)}
                                    liveReturns={[]}
                                    height={250}
                                />
                            </div>

                            {/* Monte Carlo Simulation */}
                            <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700">
                                <h3 className="text-lg font-bold text-slate-800 dark:text-white mb-4">🎲 Monte Carlo Risk Simulation</h3>
                                <MonteCarloFanChart
                                    simulations={result.monte_carlo || generateSampleMonteCarlo(initialCapital, 100, 50)}
                                    height={320}
                                />
                            </div>

                            <BacktestSummaryCard result={result} />
                        </>
                    )}

                    {/* Empty State */}
                    {!result && !error && !isLoading && (
                        <div className="bg-white dark:bg-slate-800 rounded-2xl p-12 border border-slate-200 dark:border-slate-700 flex flex-col items-center justify-center text-center">
                            <div className="w-20 h-20 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center mb-4">
                                <BarChart3 size={40} className="text-slate-400" />
                            </div>
                            <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">No Backtest Results</h3>
                            <p className="text-sm text-slate-500 max-w-md">
                                Configure your strategy parameters and click "Run Backtest" to see performance metrics.
                            </p>
                        </div>
                    )}

                    {/* Loading State */}
                    {isLoading && (
                        <div className="bg-white dark:bg-slate-800 rounded-2xl p-12 border border-slate-200 dark:border-slate-700 flex flex-col items-center justify-center">
                            <RefreshCw size={48} className="text-violet-500 animate-spin mb-4" />
                            <p className="text-slate-600 dark:text-slate-300">Running backtest...</p>
                            <p className="text-sm text-slate-400">This may take a few seconds</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default QuantBot;
