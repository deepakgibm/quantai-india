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
import { API_URL, getAuthHeaders } from '../services/api';

// Chart Components
import EquityCurveChart from '../components/charts/EquityCurveChart';
import DrawdownChart from '../components/charts/DrawdownChart';
import MonteCarloFanChart from '../components/charts/MonteCarloFanChart';
import DistributionComparisonChart from '../components/charts/DistributionComparisonChart';
import SymbolSearch from '../components/SymbolSearch';
import StrategySelectionPanel from '../components/StrategySelectionPanel';
import { BacktestHelpGuide } from '../components/HelpGuide';

interface StrategyInfo {
    name: string;
    display_name: string;
    category: string;
    description: string;
    parameters: any;
    time_horizon: string;
    is_implemented: boolean;
}

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
        const phase = Math.sin(i * 0.05) * 0.5 + 0.5;
        const dd = -Math.abs(maxDD / 100) * phase * (0.3 + Math.random() * 0.7);
        data.push({ date: date.toISOString().slice(0, 10), drawdown: dd });
    }
    return data;
};

const generateSampleReturns = (numTrades: number): number[] => {
    const returns = [];
    for (let i = 0; i < numTrades; i++) {
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

    if (pf > 1.3) {
        whatHappened = "Over the tested period, the strategy made profits more often than losses, showing a clear mathematical edge.";
    } else if (pf >= 1.0) {
        whatHappened = "The strategy barely broke even; while it didn't lose much, the gains were nearly equal to the losses.";
    } else {
        whatHappened = "The strategy struggled to maintain profitability, as losses outweighed the gains over the period.";
    }

    if (dd < 10) {
        riskExp = "At its worst point, the strategy experienced very small temporary declines. This indicates a very stable path for your capital.";
    } else if (dd < 25) {
        riskExp = "At its worst point, the strategy temporarily lost a noticeable portion of its value before recovering.";
    } else {
        riskExp = "This strategy experienced heavy temporary losses. You would need significant emotional discipline to stay invested.";
    }

    if (tr > 100) {
        reliability = "Profits came from a large number of trades, making these historical results more statistically reliable.";
    } else if (tr > 30) {
        reliability = "The results are based on a moderate number of trades.";
    } else {
        reliability = "Most gains came from a very small number of trades. This makes the results less dependable.";
    }

    if (dd > 25 || wr < 40) {
        style = "This behavior suggests a More Aggressive style where you must tolerate large swings.";
    } else if (dd < 12 && wr > 50) {
        style = "The steady growth suggests a More Conservative style.";
    } else {
        style = "This strategy works only in specific market conditions.";
    }

    return { verdict, whatHappened, riskExp, reliability, style, classification };
};

const BacktestSummaryCard = ({ result }: { result: BacktestResult }) => {
    const summary = generatePlainEnglishSummary(result.metrics, result.strategy, result.symbol);

    return (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-xl">
            <div className="p-6 border-b border-slate-100 dark:border-slate-700 bg-gradient-to-r from-slate-50 to-white dark:from-slate-800 dark:to-slate-800/50 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-violet-500 rounded-xl">
                        <BarChart3 size={20} className="text-white" />
                    </div>
                    <h3 className="text-lg font-black text-slate-800 dark:text-white uppercase">Human Insight</h3>
                </div>
                <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border ${summary.classification === 'Strong' ? 'bg-emerald-50 border-emerald-200 text-emerald-600' :
                    summary.classification === 'Moderate' ? 'bg-amber-50 border-amber-200 text-amber-600' :
                        'bg-rose-50 border-rose-200 text-rose-600'
                    }`}>
                    {summary.classification} Performance
                </span>
            </div>

            <div className="p-8 space-y-8">
                <p className="text-xl font-bold text-slate-800 dark:text-white leading-tight">"{summary.verdict}"</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-2">
                        <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                            <Activity size={14} className="text-violet-500" /> Performance
                        </h4>
                        <p className="text-sm text-slate-600 dark:text-slate-300 font-medium leading-relaxed">{summary.whatHappened}</p>
                    </div>
                    <div className="space-y-2">
                        <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                            <Shield size={14} className="text-rose-500" /> Risk Analysis
                        </h4>
                        <p className="text-sm text-slate-600 dark:text-slate-300 font-medium leading-relaxed">{summary.riskExp}</p>
                    </div>
                    <div className="space-y-2">
                        <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                            <Target size={14} className="text-cyan-500" /> Reliability
                        </h4>
                        <p className="text-sm text-slate-600 dark:text-slate-300 font-medium leading-relaxed">{summary.reliability}</p>
                    </div>
                    <div className="space-y-2">
                        <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                            <Layers size={14} className="text-amber-500" /> Style
                        </h4>
                        <p className="text-sm text-slate-600 dark:text-slate-300 font-medium leading-relaxed italic">"{summary.style}"</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

const Backtest: React.FC = () => {
    // Form state
    const [selectedSymbols, setSelectedSymbols] = useState<string[]>(['RELIANCE']);
    const [timeframe, setTimeframe] = useState('1D');
    const [selectedStrategies, setSelectedStrategies] = useState<StrategyInfo[]>([{
        name: 'MACrossover',
        display_name: 'MA Crossover',
        category: 'Trend & Momentum',
        description: 'Moving Average Crossover Strategy',
        parameters: {},
        time_horizon: 'Intraday',
        is_implemented: true
    }]);
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

    const runBacktest = async () => {
        setIsLoading(true);
        setError(null);
        setResult(null);

        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`${API_URL}/api/quant/backtest/run`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    symbol: selectedSymbols[0],
                    strategy: selectedStrategies[0]?.name || 'MACrossover',
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

    const MetricCard = ({ label, value, icon: Icon, color = 'indigo', suffix = '' }: any) => (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 shadow-sm">
            <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{label}</span>
                <Icon size={16} className={`text-${color}-500`} />
            </div>
            <span className={`text-xl font-bold text-slate-900 dark:text-white`}>
                {typeof value === 'number' ? value.toFixed(2) : value}{suffix}
            </span>
        </div>
    );

    return (
        <div className="h-full flex flex-col gap-6 p-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-3 bg-indigo-600 rounded-xl shadow-lg shadow-indigo-500/20 text-white">
                        <LineChartIcon size={24} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Strategy Backtest</h1>
                        <p className="text-sm text-slate-500">Test trading ideas with institutional-grade data</p>
                    </div>
                </div>
                <BacktestHelpGuide />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Column 1: Config & Symbols */}
                <div className="lg:col-span-3 border border-slate-200 dark:border-slate-800 rounded-2xl bg-white dark:bg-slate-800/50 p-6 flex flex-col h-fit">
                    <h2 className="text-lg font-bold text-slate-800 dark:text-white mb-6 flex items-center gap-2">
                        <Settings2 className="text-indigo-600" size={20} /> Parameters
                    </h2>

                    <div className="space-y-5">
                        {/* Timeframe */}
                        <div>
                            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Timeframe</label>
                            <select
                                value={timeframe}
                                onChange={(e) => setTimeframe(e.target.value)}
                                className="w-full p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white"
                            >
                                <option value="15m">15 Minute</option>
                                <option value="30m">30 Minute</option>
                                <option value="1H">1 Hour</option>
                                <option value="1D">Daily</option>
                            </select>
                        </div>

                        {/* Symbol Search */}
                        <div>
                            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">Stock Details</label>
                            <SymbolSearch
                                selectedSymbols={selectedSymbols}
                                onSymbolsChange={setSelectedSymbols}
                                timeframe={timeframe}
                                maxSymbols={1}
                            />
                        </div>

                        {/* Dates */}
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="block text-xs font-semibold text-slate-500 mb-1 uppercase">Start</label>
                                <input
                                    type="date"
                                    value={startDate}
                                    onChange={(e) => setStartDate(e.target.value)}
                                    className="w-full p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-semibold text-slate-500 mb-1 uppercase">End</label>
                                <input
                                    type="date"
                                    value={endDate}
                                    onChange={(e) => setEndDate(e.target.value)}
                                    className="w-full p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white text-sm"
                                />
                            </div>
                        </div>

                        {/* Capital */}
                        <div>
                            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Capital (₹)</label>
                            <input
                                type="number"
                                value={initialCapital}
                                onChange={(e) => setInitialCapital(Number(e.target.value))}
                                className="w-full p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-white"
                            />
                        </div>

                        <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
                            <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-4">Indicators</h3>
                            <div className="space-y-4">
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <label className="block text-xs text-slate-500 mb-1">Fast</label>
                                        <input
                                            type="number"
                                            value={fastPeriod}
                                            onChange={(e) => setFastPeriod(Number(e.target.value))}
                                            className="w-full p-2 rounded-lg bg-slate-100 dark:bg-slate-900 border-none text-sm"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs text-slate-500 mb-1">Slow</label>
                                        <input
                                            type="number"
                                            value={slowPeriod}
                                            onChange={(e) => setSlowPeriod(Number(e.target.value))}
                                            className="w-full p-2 rounded-lg bg-slate-100 dark:bg-slate-900 border-none text-sm"
                                        />
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <select
                                        value={maType}
                                        onChange={(e) => setMaType(e.target.value)}
                                        className="w-full p-2 rounded-lg bg-slate-100 dark:bg-slate-900 border-none text-sm"
                                    >
                                        <option value="EMA">EMA</option>
                                        <option value="SMA">SMA</option>
                                    </select>
                                    <input
                                        type="number"
                                        value={positionSizePct}
                                        onChange={(e) => setPositionSizePct(Number(e.target.value))}
                                        placeholder="Size %"
                                        className="w-full p-2 rounded-lg bg-slate-100 dark:bg-slate-900 border-none text-sm"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                    <button
                        onClick={runBacktest}
                        disabled={isLoading || selectedSymbols.length === 0}
                        className="mt-8 w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 rounded-2xl shadow-lg transition-all flex items-center justify-center gap-2"
                    >
                        {isLoading ? <RefreshCw className="animate-spin" size={20} /> : <><Play size={20} /> Run Project</>}
                    </button>
                </div>

                {/* Column 2: Strategy Explorer */}
                <div className="lg:col-span-3 border border-slate-200 dark:border-slate-800 rounded-2xl bg-white dark:bg-slate-800/50 p-6 flex flex-col h-[800px]">
                    <h2 className="text-lg font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
                        <Layers className="text-indigo-600" size={20} /> Strategy Explorer
                    </h2>
                    <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                        <StrategySelectionPanel
                            selectedStrategies={selectedStrategies}
                            onSelectionChange={(strats) => {
                                if (strats.length > 0) {
                                    setSelectedStrategies([strats[strats.length - 1]]);
                                } else {
                                    setSelectedStrategies([]);
                                }
                            }}
                        />
                    </div>
                </div>

                {/* Column 3-4: Results Display */}
                <div className="lg:col-span-6 space-y-6">
                    {error && (
                        <div className="bg-rose-50 border border-rose-200 text-rose-700 p-4 rounded-xl flex items-center gap-3">
                            <AlertTriangle size={20} />
                            <p className="text-sm font-medium">{error}</p>
                        </div>
                    )}

                    {!result && !isLoading && !error && (
                        <div className="h-full flex flex-col items-center justify-center text-center p-12 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-3xl">
                            <div className="p-4 bg-slate-100 dark:bg-slate-800 rounded-full mb-4">
                                <Activity size={48} className="text-slate-400" />
                            </div>
                            <h3 className="text-xl font-bold text-slate-800 dark:text-white">Ready to Backtest</h3>
                            <p className="text-slate-500 mt-2 max-w-xs">Configure your parameters and select a strategy to see performance results here.</p>
                        </div>
                    )}

                    {isLoading && (
                        <div className="h-full flex flex-col items-center justify-center p-12">
                            <RefreshCw className="animate-spin text-indigo-600 mb-4" size={48} />
                            <p className="text-slate-600 font-medium">Processing market data and executing strategy...</p>
                        </div>
                    )}

                    {result && (
                        <div className="space-y-6">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <MetricCard label="Return" value={result.metrics.total_return_pct} icon={TrendingUp} color="emerald" suffix="%" />
                                <MetricCard label="Drawdown" value={Math.abs(result.metrics.max_drawdown_pct)} icon={Shield} color="rose" suffix="%" />
                                <MetricCard label="Win Rate" value={result.metrics.win_rate} icon={Target} color="indigo" suffix="%" />
                                <MetricCard label="Total Trades" value={result.metrics.total_trades} icon={Layers} color="slate" />
                            </div>

                            <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl border border-slate-200 dark:border-slate-700">
                                <h3 className="font-bold mb-4 flex items-center gap-2"><TrendingUp size={18} /> Equity Growth</h3>
                                <EquityCurveChart data={result.equity_curve || generateSampleEquityCurve(initialCapital, result.metrics.total_return_pct)} initialCapital={initialCapital} height={250} />
                            </div>

                            <BacktestSummaryCard result={result} />

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl border border-slate-200 dark:border-slate-700">
                                    <h3 className="font-bold mb-4 flex items-center gap-2"><BarChart3 size={18} /> Drawdowns</h3>
                                    <DrawdownChart data={result.drawdown_curve || generateSampleDrawdown(result.metrics.max_drawdown_pct)} height={150} />
                                </div>
                                <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl border border-slate-200 dark:border-slate-700">
                                    <h3 className="font-bold mb-4 flex items-center gap-2"><Target size={18} /> Monte Carlo</h3>
                                    <MonteCarloFanChart simulations={result.monte_carlo || generateSampleMonteCarlo(initialCapital, 50, 60)} height={150} />
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Backtest;
