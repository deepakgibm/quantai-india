import React, { useState, useEffect } from 'react';
import {
    Play,
    TrendingUp,
    BarChart2,
    Calendar,
    Settings2,
    AlertTriangle,
    CheckCircle,
    XCircle,
    ChevronDown,
    ChevronUp,
    RefreshCw,
    Info
} from 'lucide-react';

// Types
interface WalkForwardConfig {
    train_window: number;
    test_window: number;
    step_size: number;
    anchored: boolean;
}

interface WindowResult {
    window_id: number;
    train_start: string;
    train_end: string;
    test_start: string;
    test_end: string;
    oos_return: number;
    oos_sharpe: number;
    oos_max_drawdown: number;
    oos_win_rate: number;
    oos_trade_count: number;
    parameters: Record<string, any>;
}

interface WalkForwardSummary {
    total_return: number;
    cagr?: number;
    sharpe: number;
    sortino?: number;
    max_drawdown: number;
    win_rate: number;
    profitable_windows_pct: number;
    parameter_stability_score?: number;
    expectancy?: number;
}

interface WalkForwardResult {
    summary: WalkForwardSummary;
    oos_equity_curve: Array<{ timestamp: string; equity: number }>;
    window_results: WindowResult[];
    best_parameters_by_window: Array<Record<string, any>>;
    model_diagnostics?: {
        feature_importance?: Record<string, number>;
        confidence_decay?: number;
        drift_detected?: boolean;
        avg_prediction_confidence?: number;
    };
    validation_passed: boolean;
    validation_messages: string[];
    run_timestamp: string;
    duration_seconds: number;
}

// Available strategies
const STRATEGIES = {
    rule_based: [
        { name: 'trend_finder', label: 'Trend Finder', description: 'EMA crossover with ADX filter' },
        { name: 'breakout_detector', label: 'Breakout Detector', description: 'Price breakout with volume' },
        { name: 'momentum', label: 'Momentum', description: 'RSI + ROC momentum strategy' },
        { name: 'mean_reversion', label: 'Mean Reversion', description: 'Bollinger Band reversion' },
    ],
    ml: [
        { name: 'xgboost_classifier', label: 'XGBoost', description: 'Binary classification' },
        { name: 'lstm_sequence', label: 'LSTM', description: 'Sequence prediction' },
    ]
};

const TIMEFRAMES = [
    { value: '5m', label: '5 Minutes' },
    { value: '15m', label: '15 Minutes' },
    { value: '30m', label: '30 Minutes' },
    { value: '1h', label: '1 Hour' },
    { value: '1D', label: 'Daily' },
];

const PRESETS = {
    intraday: { train_window: 60, test_window: 10, step_size: 10 },
    swing: { train_window: 252, test_window: 63, step_size: 21 },
};

// Popular NSE symbols
const POPULAR_SYMBOLS = [
    'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
    'HINDUNILVR', 'SBIN', 'BHARTIARTL', 'KOTAKBANK', 'ITC',
    'BAJFINANCE', 'LT', 'AXISBANK', 'ASIANPAINT', 'MARUTI'
];

const WalkForwardBacktest: React.FC = () => {
    // Config state
    const [symbols, setSymbols] = useState<string[]>(['RELIANCE']);
    const [symbolInput, setSymbolInput] = useState('');
    const [strategyType, setStrategyType] = useState<'RULE_BASED' | 'ML'>('RULE_BASED');
    const [strategyName, setStrategyName] = useState('trend_finder');
    const [timeframe, setTimeframe] = useState('15m');
    const [tradeStyle, setTradeStyle] = useState<'INTRADAY' | 'SWING'>('INTRADAY');
    const [wfConfig, setWfConfig] = useState<WalkForwardConfig>({
        train_window: 60,
        test_window: 10,
        step_size: 10,
        anchored: false
    });
    const [capital, setCapital] = useState(100000);
    const [mlModel, setMlModel] = useState<'NONE' | 'XGBOOST' | 'LSTM'>('NONE');

    // Result state
    const [result, setResult] = useState<WalkForwardResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // UI state
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [selectedWindow, setSelectedWindow] = useState<number | null>(null);

    // Apply preset when trade style changes
    useEffect(() => {
        const preset = PRESETS[tradeStyle.toLowerCase() as keyof typeof PRESETS];
        if (preset) {
            setWfConfig(prev => ({ ...prev, ...preset }));
        }
    }, [tradeStyle]);

    // Add symbol
    const addSymbol = () => {
        const sym = symbolInput.trim().toUpperCase();
        if (sym && !symbols.includes(sym)) {
            setSymbols([...symbols, sym]);
            setSymbolInput('');
        }
    };

    // Remove symbol
    const removeSymbol = (sym: string) => {
        setSymbols(symbols.filter(s => s !== sym));
    };

    // Run backtest
    const runBacktest = async () => {
        if (symbols.length === 0) {
            setError('Please select at least one symbol');
            return;
        }

        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const response = await fetch('/api/v1/backtest/walk-forward', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbols,
                    exchange: 'NSE',
                    strategy_type: strategyType,
                    strategy_name: strategyName,
                    timeframe,
                    trade_style: tradeStyle,
                    walk_forward: wfConfig,
                    capital,
                    ml_model: strategyType === 'ML' ? mlModel : 'NONE'
                })
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Backtest failed');
            }

            const data = await response.json();
            setResult(data);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // Format percentage
    const formatPct = (val: number) => `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;

    // Format date
    const formatDate = (dateStr: string) => {
        const d = new Date(dateStr);
        return d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: '2-digit' });
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                        <div className="p-2 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg">
                            <TrendingUp size={24} />
                        </div>
                        Walk-Forward Backtest
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-1">
                        Pardo-compliant strategy validation with rolling IS/OOS windows
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Configuration Panel */}
                <div className="lg:col-span-1 space-y-4">
                    {/* Symbol Selection */}
                    <div className="bg-white dark:bg-slate-800 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-700">
                        <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                            <BarChart2 size={18} />
                            Symbols
                        </h3>

                        <div className="flex gap-2 mb-3">
                            <input
                                type="text"
                                value={symbolInput}
                                onChange={e => setSymbolInput(e.target.value)}
                                onKeyPress={e => e.key === 'Enter' && addSymbol()}
                                placeholder="Enter symbol..."
                                className="flex-1 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
                            />
                            <button
                                onClick={addSymbol}
                                className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"
                            >
                                Add
                            </button>
                        </div>

                        <div className="flex flex-wrap gap-2 mb-3">
                            {symbols.map(sym => (
                                <span
                                    key={sym}
                                    className="px-3 py-1 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-full text-sm flex items-center gap-1"
                                >
                                    {sym}
                                    <button onClick={() => removeSymbol(sym)} className="hover:text-red-500">×</button>
                                </span>
                            ))}
                        </div>

                        <div className="flex flex-wrap gap-1.5">
                            {POPULAR_SYMBOLS.slice(0, 8).map(sym => (
                                <button
                                    key={sym}
                                    onClick={() => !symbols.includes(sym) && setSymbols([...symbols, sym])}
                                    disabled={symbols.includes(sym)}
                                    className={`px-2 py-1 rounded text-xs ${symbols.includes(sym)
                                            ? 'bg-slate-200 dark:bg-slate-600 text-slate-400 cursor-not-allowed'
                                            : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/30'
                                        }`}
                                >
                                    {sym}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Strategy Selection */}
                    <div className="bg-white dark:bg-slate-800 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-700">
                        <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                            <Settings2 size={18} />
                            Strategy
                        </h3>

                        <div className="space-y-4">
                            {/* Strategy Type */}
                            <div className="flex gap-2">
                                {(['RULE_BASED', 'ML'] as const).map(type => (
                                    <button
                                        key={type}
                                        onClick={() => {
                                            setStrategyType(type);
                                            setStrategyName(type === 'ML' ? 'xgboost_classifier' : 'trend_finder');
                                            setMlModel(type === 'ML' ? 'XGBOOST' : 'NONE');
                                        }}
                                        className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${strategyType === type
                                                ? 'bg-indigo-600 text-white'
                                                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
                                            }`}
                                    >
                                        {type === 'RULE_BASED' ? 'Rule-Based' : 'ML Model'}
                                    </button>
                                ))}
                            </div>

                            {/* Strategy Name */}
                            <select
                                value={strategyName}
                                onChange={e => setStrategyName(e.target.value)}
                                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
                            >
                                {(strategyType === 'RULE_BASED' ? STRATEGIES.rule_based : STRATEGIES.ml).map(s => (
                                    <option key={s.name} value={s.name}>{s.label}</option>
                                ))}
                            </select>

                            {/* Timeframe */}
                            <select
                                value={timeframe}
                                onChange={e => setTimeframe(e.target.value)}
                                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
                            >
                                {TIMEFRAMES.map(tf => (
                                    <option key={tf.value} value={tf.value}>{tf.label}</option>
                                ))}
                            </select>

                            {/* Trade Style */}
                            <div className="flex gap-2">
                                {(['INTRADAY', 'SWING'] as const).map(style => (
                                    <button
                                        key={style}
                                        onClick={() => setTradeStyle(style)}
                                        className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${tradeStyle === style
                                                ? 'bg-emerald-600 text-white'
                                                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
                                            }`}
                                    >
                                        {style}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Walk-Forward Config */}
                    <div className="bg-white dark:bg-slate-800 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-700">
                        <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                            <Calendar size={18} />
                            Walk-Forward Windows
                        </h3>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">Train Window (sessions)</label>
                                <input
                                    type="number"
                                    value={wfConfig.train_window}
                                    onChange={e => setWfConfig({ ...wfConfig, train_window: parseInt(e.target.value) || 60 })}
                                    min={20}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
                                />
                            </div>

                            <div>
                                <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">Test Window (sessions)</label>
                                <input
                                    type="number"
                                    value={wfConfig.test_window}
                                    onChange={e => setWfConfig({ ...wfConfig, test_window: parseInt(e.target.value) || 10 })}
                                    min={5}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
                                />
                            </div>

                            <div>
                                <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">Step Size</label>
                                <input
                                    type="number"
                                    value={wfConfig.step_size}
                                    onChange={e => setWfConfig({ ...wfConfig, step_size: parseInt(e.target.value) || 10 })}
                                    min={5}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
                                />
                            </div>

                            <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                                <input
                                    type="checkbox"
                                    checked={wfConfig.anchored}
                                    onChange={e => setWfConfig({ ...wfConfig, anchored: e.target.checked })}
                                    className="rounded border-slate-300 dark:border-slate-600"
                                />
                                Anchored (train from start)
                            </label>
                        </div>
                    </div>

                    {/* Advanced Options */}
                    <button
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        className="w-full flex items-center justify-between px-4 py-3 bg-slate-100 dark:bg-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600"
                    >
                        <span>Advanced Options</span>
                        {showAdvanced ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                    </button>

                    {showAdvanced && (
                        <div className="bg-white dark:bg-slate-800 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-700">
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">Initial Capital (₹)</label>
                                    <input
                                        type="number"
                                        value={capital}
                                        onChange={e => setCapital(parseInt(e.target.value) || 100000)}
                                        min={10000}
                                        step={10000}
                                        className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
                                    />
                                </div>

                                {strategyType === 'ML' && (
                                    <div>
                                        <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">ML Model</label>
                                        <select
                                            value={mlModel}
                                            onChange={e => setMlModel(e.target.value as typeof mlModel)}
                                            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
                                        >
                                            <option value="XGBOOST">XGBoost</option>
                                            <option value="LSTM">LSTM</option>
                                        </select>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Run Button */}
                    <button
                        onClick={runBacktest}
                        disabled={loading || symbols.length === 0}
                        className={`w-full py-4 rounded-xl font-semibold text-white shadow-lg flex items-center justify-center gap-2 transition ${loading || symbols.length === 0
                                ? 'bg-slate-400 cursor-not-allowed'
                                : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700'
                            }`}
                    >
                        {loading ? (
                            <>
                                <RefreshCw size={20} className="animate-spin" />
                                Running Backtest...
                            </>
                        ) : (
                            <>
                                <Play size={20} />
                                Run Walk-Forward Backtest
                            </>
                        )}
                    </button>

                    {error && (
                        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm flex items-start gap-2">
                            <AlertTriangle size={18} className="flex-shrink-0 mt-0.5" />
                            {error}
                        </div>
                    )}
                </div>

                {/* Results Panel */}
                <div className="lg:col-span-2 space-y-4">
                    {!result && !loading && (
                        <div className="bg-white dark:bg-slate-800 rounded-xl p-12 shadow-sm border border-slate-200 dark:border-slate-700 text-center">
                            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                                <TrendingUp size={32} className="text-slate-400" />
                            </div>
                            <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">
                                Configure and Run Backtest
                            </h3>
                            <p className="text-slate-500 dark:text-slate-400 text-sm max-w-md mx-auto">
                                Select symbols, choose a strategy, and configure walk-forward windows to start
                                your Pardo-compliant strategy evaluation.
                            </p>
                        </div>
                    )}

                    {loading && (
                        <div className="bg-white dark:bg-slate-800 rounded-xl p-12 shadow-sm border border-slate-200 dark:border-slate-700 text-center">
                            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
                                <RefreshCw size={32} className="text-indigo-600 dark:text-indigo-400 animate-spin" />
                            </div>
                            <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">
                                Running Walk-Forward Analysis...
                            </h3>
                            <p className="text-slate-500 dark:text-slate-400 text-sm">
                                Generating windows, optimizing parameters, and evaluating OOS performance
                            </p>
                        </div>
                    )}

                    {result && (
                        <>
                            {/* Validation Status */}
                            <div className={`p-4 rounded-xl flex items-start gap-3 ${result.validation_passed
                                    ? 'bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800'
                                    : 'bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800'
                                }`}>
                                {result.validation_passed ? (
                                    <CheckCircle size={24} className="text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                                ) : (
                                    <AlertTriangle size={24} className="text-amber-600 dark:text-amber-400 flex-shrink-0" />
                                )}
                                <div>
                                    <h4 className={`font-semibold ${result.validation_passed
                                            ? 'text-emerald-700 dark:text-emerald-300'
                                            : 'text-amber-700 dark:text-amber-300'
                                        }`}>
                                        {result.validation_passed ? 'Strategy Validation Passed' : 'Strategy Validation Warning'}
                                    </h4>
                                    <ul className="mt-1 text-sm space-y-0.5">
                                        {result.validation_messages.map((msg, i) => (
                                            <li key={i} className={`
                        ${result.validation_passed ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}
                      `}>{msg}</li>
                                        ))}
                                    </ul>
                                </div>
                            </div>

                            {/* Summary Metrics */}
                            <div className="bg-white dark:bg-slate-800 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-700">
                                <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Summary Metrics (OOS Only)</h3>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                                        <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Total Return</div>
                                        <div className={`text-xl font-bold ${result.summary.total_return >= 0 ? 'text-emerald-600' : 'text-red-600'
                                            }`}>
                                            {formatPct(result.summary.total_return)}
                                        </div>
                                    </div>
                                    <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                                        <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Sharpe Ratio</div>
                                        <div className="text-xl font-bold text-slate-900 dark:text-white">
                                            {result.summary.sharpe.toFixed(2)}
                                        </div>
                                    </div>
                                    <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                                        <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Max Drawdown</div>
                                        <div className="text-xl font-bold text-red-600">
                                            {result.summary.max_drawdown.toFixed(2)}%
                                        </div>
                                    </div>
                                    <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                                        <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Win Rate</div>
                                        <div className="text-xl font-bold text-slate-900 dark:text-white">
                                            {result.summary.win_rate.toFixed(1)}%
                                        </div>
                                    </div>
                                </div>

                                <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700 flex items-center gap-6 text-sm text-slate-600 dark:text-slate-400">
                                    <div>
                                        <span className="font-medium">Profitable Windows:</span>{' '}
                                        <span className={result.summary.profitable_windows_pct >= 60 ? 'text-emerald-600' : 'text-amber-600'}>
                                            {result.summary.profitable_windows_pct.toFixed(1)}%
                                        </span>
                                    </div>
                                    {result.summary.parameter_stability_score !== undefined && (
                                        <div>
                                            <span className="font-medium">Param Stability:</span>{' '}
                                            <span>{(result.summary.parameter_stability_score * 100).toFixed(0)}%</span>
                                        </div>
                                    )}
                                    <div>
                                        <span className="font-medium">Duration:</span>{' '}
                                        <span>{result.duration_seconds.toFixed(2)}s</span>
                                    </div>
                                </div>
                            </div>

                            {/* Window Timeline */}
                            <div className="bg-white dark:bg-slate-800 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-700">
                                <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                                    <Calendar size={18} />
                                    Walk-Forward Timeline
                                </h3>

                                <div className="overflow-x-auto">
                                    <div className="flex gap-2 min-w-max pb-2">
                                        {result.window_results.map((w, i) => (
                                            <button
                                                key={w.window_id}
                                                onClick={() => setSelectedWindow(selectedWindow === i ? null : i)}
                                                className={`flex-shrink-0 p-3 rounded-lg border transition ${selectedWindow === i
                                                        ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30'
                                                        : 'border-slate-200 dark:border-slate-700 hover:border-indigo-300'
                                                    }`}
                                            >
                                                <div className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                                                    Window {w.window_id + 1}
                                                </div>
                                                <div className="flex gap-1 mb-2">
                                                    <div className="h-2 w-8 bg-slate-300 dark:bg-slate-600 rounded" title="IS" />
                                                    <div className={`h-2 w-4 rounded ${w.oos_return >= 0 ? 'bg-emerald-500' : 'bg-red-500'}`} title="OOS" />
                                                </div>
                                                <div className={`text-sm font-bold ${w.oos_return >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                                    {formatPct(w.oos_return)}
                                                </div>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Selected Window Details */}
                                {selectedWindow !== null && result.window_results[selectedWindow] && (
                                    <div className="mt-4 p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                            <div>
                                                <div className="text-slate-500 dark:text-slate-400">Train Period</div>
                                                <div className="font-medium text-slate-900 dark:text-white">
                                                    {formatDate(result.window_results[selectedWindow].train_start)} → {formatDate(result.window_results[selectedWindow].train_end)}
                                                </div>
                                            </div>
                                            <div>
                                                <div className="text-slate-500 dark:text-slate-400">Test Period</div>
                                                <div className="font-medium text-slate-900 dark:text-white">
                                                    {formatDate(result.window_results[selectedWindow].test_start)} → {formatDate(result.window_results[selectedWindow].test_end)}
                                                </div>
                                            </div>
                                            <div>
                                                <div className="text-slate-500 dark:text-slate-400">OOS Sharpe</div>
                                                <div className="font-medium text-slate-900 dark:text-white">
                                                    {result.window_results[selectedWindow].oos_sharpe.toFixed(2)}
                                                </div>
                                            </div>
                                            <div>
                                                <div className="text-slate-500 dark:text-slate-400">Trades</div>
                                                <div className="font-medium text-slate-900 dark:text-white">
                                                    {result.window_results[selectedWindow].oos_trade_count}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Window Results Table */}
                            <div className="bg-white dark:bg-slate-800 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-700">
                                <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Window-by-Window Results</h3>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-slate-200 dark:border-slate-700">
                                                <th className="text-left py-3 px-4 font-medium text-slate-600 dark:text-slate-400">Window</th>
                                                <th className="text-left py-3 px-4 font-medium text-slate-600 dark:text-slate-400">Test Period</th>
                                                <th className="text-right py-3 px-4 font-medium text-slate-600 dark:text-slate-400">Return</th>
                                                <th className="text-right py-3 px-4 font-medium text-slate-600 dark:text-slate-400">Sharpe</th>
                                                <th className="text-right py-3 px-4 font-medium text-slate-600 dark:text-slate-400">Max DD</th>
                                                <th className="text-right py-3 px-4 font-medium text-slate-600 dark:text-slate-400">Win Rate</th>
                                                <th className="text-right py-3 px-4 font-medium text-slate-600 dark:text-slate-400">Trades</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {result.window_results.map(w => (
                                                <tr key={w.window_id} className="border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30">
                                                    <td className="py-3 px-4 font-medium text-slate-900 dark:text-white">
                                                        #{w.window_id + 1}
                                                    </td>
                                                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                                                        {formatDate(w.test_start)} → {formatDate(w.test_end)}
                                                    </td>
                                                    <td className={`py-3 px-4 text-right font-medium ${w.oos_return >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                                        {formatPct(w.oos_return)}
                                                    </td>
                                                    <td className="py-3 px-4 text-right text-slate-900 dark:text-white">
                                                        {w.oos_sharpe.toFixed(2)}
                                                    </td>
                                                    <td className="py-3 px-4 text-right text-red-600">
                                                        {w.oos_max_drawdown.toFixed(2)}%
                                                    </td>
                                                    <td className="py-3 px-4 text-right text-slate-900 dark:text-white">
                                                        {w.oos_win_rate.toFixed(1)}%
                                                    </td>
                                                    <td className="py-3 px-4 text-right text-slate-600 dark:text-slate-400">
                                                        {w.oos_trade_count}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            {/* Info Panel */}
                            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4 flex items-start gap-3">
                                <Info size={20} className="text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                                <div className="text-sm text-blue-700 dark:text-blue-300">
                                    <p className="font-medium mb-1">Walk-Forward Analysis (Pardo Method)</p>
                                    <p className="text-blue-600 dark:text-blue-400">
                                        Results show only Out-of-Sample (OOS) performance. In-Sample metrics are used for
                                        optimization but never exposed, preventing data leakage and overfitting detection.
                                    </p>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default WalkForwardBacktest;
