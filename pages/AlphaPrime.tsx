import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';

interface AlphaSignal {
    symbol: string;
    timestamp: string;
    alpha_score: number;
    alpha_rank?: number;
    rsi?: number;
    macd_divergence?: number;
    confidence: number;
}

interface BacktestResults {
    total_return_pct: number;
    annual_return_pct: number;
    sharpe_ratio: number;
    max_drawdown_pct: number;
    win_rate_pct: number;
    total_trades: number;
    equity_curve: { [key: string]: number };
}

export default function AlphaPrimePage() {
    const [signals, setSignals] = useState<AlphaSignal[]>([]);
    const [backtestResults, setBacktestResults] = useState<BacktestResults | null>(null);
    const [isTraining, setIsTraining] = useState(false);
    const [isBacktesting, setIsBacktesting] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Fetch latest signals on mount
    useEffect(() => {
        fetchSignals();
    }, []);

    const fetchSignals = async () => {
        setLoading(true);
        try {
            const data = await api.alphaPrime.getSignals(20, 0.7);
            setSignals(data || []);
            setError(null);
        } catch (err) {
            setError('Failed to fetch signals');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleTrain = async () => {
        setIsTraining(true);
        try {
            const result = await api.alphaPrime.train(30, 100, 10);
            if (result && result.status === 'success') {
                alert(`Training complete! Test R²: ${result.metrics.test_r2.toFixed(4)}`);
                await fetchSignals(); // Refresh signals after training
            } else {
                alert('Training failed. Check console for details.');
            }
        } catch (err) {
            console.error('Training error:', err);
            alert('Training failed');
        } finally {
            setIsTraining(false);
        }
    };

    const handleBacktest = async () => {
        setIsBacktesting(true);
        const endDate = new Date().toISOString();
        const startDate = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString(); // 90 days ago

        try {
            const result = await api.alphaPrime.backtest(startDate, endDate, 1000000);
            if (result && result.status === 'success') {
                setBacktestResults(result.results);
            } else {
                alert('Backtest failed. Check console for details.');
            }
        } catch (err) {
            console.error('Backtest error:', err);
            alert('Backtest failed');
        } finally {
            setIsBacktesting(false);
        }
    };

    // Prepare equity curve data for chart
    const equityCurveData = backtestResults && backtestResults.equity_curve
        ? Object.entries(backtestResults.equity_curve).map(([timestamp, value]) => ({
            timestamp: new Date(timestamp).toLocaleDateString(),
            equity: value
        }))
        : [];

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-6">
            {/* Header */}
            <div className="max-w-7xl mx-auto mb-8">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-4xl font-bold text-white mb-2">AlphaPrime</h1>
                        <p className="text-purple-200">Smart Beta Multi-Factor Trading System</p>
                    </div>
                    <div className="flex gap-3">
                        <button
                            onClick={handleTrain}
                            disabled={isTraining}
                            className={`px-6 py-3 rounded-lg font-semibold transition-all ${isTraining
                                    ? 'bg-gray-600 cursor-not-allowed'
                                    : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600'
                                } text-white shadow-lg`}
                        >
                            {isTraining ? '🔄 Training...' : '🧠 Train Model'}
                        </button>
                        <button
                            onClick={handleBacktest}
                            disabled={isBacktesting}
                            className={`px-6 py-3 rounded-lg font-semibold transition-all ${isBacktesting
                                    ? 'bg-gray-600 cursor-not-allowed'
                                    : 'bg-gradient-to-r from-green-500 to-teal-500 hover:from-green-600 hover:to-teal-600'
                                } text-white shadow-lg`}
                        >
                            {isBacktesting ? '🔄 Running...' : '📊 Run Backtest'}
                        </button>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left Column: Signals */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Signals Card */}
                    <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-2xl font-bold text-white">Latest Alpha Signals</h2>
                            <button
                                onClick={fetchSignals}
                                className="px-4 py-2 bg-purple-500 hover:bg-purple-600 rounded-lg text-white text-sm font-semibold transition"
                            >
                                🔄 Refresh
                            </button>
                        </div>

                        {loading && <p className="text-purple-200">Loading signals...</p>}
                        {error && <p className="text-red-400">{error}</p>}

                        <div className="space-y-3 max-h-96 overflow-y-auto">
                            {signals.length === 0 && !loading && (
                                <p className="text-purple-200">No signals available. Train the model first.</p>
                            )}

                            {signals.map((signal, idx) => (
                                <div
                                    key={idx}
                                    className="bg-white/5 rounded-lg p-4 border border-white/10 hover:border-purple-500/50 transition"
                                >
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <div className="flex items-center gap-3">
                                                <span className="text-xl font-bold text-white">{signal.symbol}</span>
                                                <span className="text-sm text-purple-300">#{signal.alpha_rank || idx + 1}</span>
                                            </div>
                                            <div className="grid grid-cols-3 gap-4 mt-2 text-sm">
                                                <div>
                                                    <p className="text-gray-400">Alpha Score</p>
                                                    <p className="text-white font-semibold">{signal.alpha_score.toFixed(4)}</p>
                                                </div>
                                                <div>
                                                    <p className="text-gray-400">RSI</p>
                                                    <p className="text-white font-semibold">{signal.rsi?.toFixed(1) || 'N/A'}</p>
                                                </div>
                                                <div>
                                                    <p className="text-gray-400">MACD Div</p>
                                                    <p className="text-white font-semibold">{signal.macd_divergence?.toFixed(3) || 'N/A'}</p>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className="text-2xl font-bold text-green-400">
                                                {(signal.confidence * 100).toFixed(0)}%
                                            </div>
                                            <div className="text-sm text-gray-400">Confidence</div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Equity Curve */}
                    {backtestResults && (
                        <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
                            <h2 className="text-2xl font-bold text-white mb-4">Equity Curve</h2>
                            <ResponsiveContainer width="100%" height={300}>
                                <LineChart data={equityCurveData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff20" />
                                    <XAxis dataKey="timestamp" stroke="#ffffff60" />
                                    <YAxis stroke="#ffffff60" />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1e1b4b', border: '1px solid #7c3aed' }}
                                        labelStyle={{ color: '#fff' }}
                                    />
                                    <Legend />
                                    <Line type="monotone" dataKey="equity" stroke="#8b5cf6" strokeWidth={2} dot={false} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </div>

                {/* Right Column: Performance Stats */}
                <div className="space-y-6">
                    {/* Performance Metrics */}
                    {backtestResults && (
                        <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
                            <h2 className="text-xl font-bold text-white mb-4">Performance</h2>
                            <div className="space-y-4">
                                <div className="bg-white/5 rounded-lg p-3">
                                    <p className="text-sm text-gray-400">Total Return</p>
                                    <p className="text-2xl font-bold text-green-400">
                                        {backtestResults.total_return_pct.toFixed(2)}%
                                    </p>
                                </div>
                                <div className="bg-white/5 rounded-lg p-3">
                                    <p className="text-sm text-gray-400">Annual Return</p>
                                    <p className="text-2xl font-bold text-blue-400">
                                        {backtestResults.annual_return_pct.toFixed(2)}%
                                    </p>
                                </div>
                                <div className="bg-white/5 rounded-lg p-3">
                                    <p className="text-sm text-gray-400">Sharpe Ratio</p>
                                    <p className="text-2xl font-bold text-purple-400">
                                        {backtestResults.sharpe_ratio.toFixed(2)}
                                    </p>
                                </div>
                                <div className="bg-white/5 rounded-lg p-3">
                                    <p className="text-sm text-gray-400">Max Drawdown</p>
                                    <p className="text-2xl font-bold text-red-400">
                                        {backtestResults.max_drawdown_pct.toFixed(2)}%
                                    </p>
                                </div>
                                <div className="bg-white/5 rounded-lg p-3">
                                    <p className="text-sm text-gray-400">Win Rate</p>
                                    <p className="text-2xl font-bold text-yellow-400">
                                        {backtestResults.win_rate_pct.toFixed(1)}%
                                    </p>
                                </div>
                                <div className="bg-white/5 rounded-lg p-3">
                                    <p className="text-sm text-gray-400">Total Trades</p>
                                    <p className="text-2xl font-bold text-white">
                                        {backtestResults.total_trades}
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Quick Info */}
                    <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
                        <h2 className="text-xl font-bold text-white mb-4">About AlphaPrime</h2>
                        <div className="space-y-3 text-sm text-purple-200">
                            <p><strong className="text-white">Strategy:</strong> Multi-factor Smart Beta</p>
                            <p><strong className="text-white">Factors:</strong> RSI, MACD, ATR, Bollinger, VWAP, Volume</p>
                            <p><strong className="text-white">ML Model:</strong> Random Forest Regressor</p>
                            <p><strong className="text-white">Rebalance:</strong> Daily</p>
                            <p><strong className="text-white">Universe:</strong> Nifty 200</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
