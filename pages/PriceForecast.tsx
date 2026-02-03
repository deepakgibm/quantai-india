import React, { useState, useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import {
    Search, Play, TrendingUp, AlertCircle, Clock, Loader2,
    Zap, BarChart3, ChevronDown, ChevronUp,
    Terminal, Activity, ShieldAlert,
    BrainCircuit
} from 'lucide-react';
import { api, API_URL, getAuthHeaders } from '../services/api';
import { PriceForecastHelpGuide } from '../components/HelpGuide';

// ============================================================================
// Types & Constants
// ============================================================================

interface Algorithm {
    id: string;
    name: string;
    version: string;
    type: string;
    is_pro: boolean;
    recommended: boolean;
    supports_confidence_bands: boolean;
    supported_timeframes: string[];
    max_horizon: number;
    description: string;
    features_used: string[];
    estimated_latency_ms: number;
    training_status?: 'READY' | 'EXPIRED' | 'UNTRAINED' | 'FAILED';
    last_trained?: string;
}

interface ForecastCandle {
    timestamp: string;
    close: number;
    upper: number | null;
    lower: number | null;
    is_forecast: boolean;
}

interface ForecastResponse {
    request_id: string;
    symbol: string;
    exchange: string;
    timeframe: string;
    horizon: number;
    algorithm: { id: string; name: string; version: string };
    generated_at: string;
    candles_input: any[];
    forecast: ForecastCandle[];
    metrics: {
        confidence_score: number;
        predicted_move_pct: number;
        volatility_label: string;
        model_latency_ms: number;
    };
    error: string | null;
}

const TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '1d'];

// ============================================================================
// Component: PriceForecast v2.2
// ============================================================================

const PriceForecast: React.FC = () => {
    // 1. Backend Configuration
    const baseUrl = API_URL;

    // 2. Form State
    const [symbol, setSymbol] = useState('RELIANCE');
    const [searchQuery, setSearchQuery] = useState('RELIANCE');
    const [timeframe, setTimeframe] = useState('5m');
    const [horizon, setHorizon] = useState(10);
    const [selectedAlgorithm, setSelectedAlgorithm] = useState<string>('adaptive_ensemble_v2');

    // 3. Data & UI State
    const [algorithms, setAlgorithms] = useState<Algorithm[]>([]);
    const [allSymbols, setAllSymbols] = useState<string[]>([]);
    const [filteredSymbols, setFilteredSymbols] = useState<string[]>([]);
    const [showSymbolDropdown, setShowSymbolDropdown] = useState(false);
    const [loading, setLoading] = useState(false);
    const [loadingAlgos, setLoadingAlgos] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
    const [showDebug, setShowDebug] = useState(false);
    const [lastApiStatus, setLastApiStatus] = useState<string>('Idle');
    const [lastTrained, setLastTrained] = useState<string | null>(null);

    // 4. Refs
    const chartRef = useRef<HTMLDivElement>(null);
    const chartInstance = useRef<echarts.ECharts | null>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Initial log for verification
    useEffect(() => {
        console.log("AI Forecast v2.2 Rendered");
    }, []);

    // 5. Load Algorithms, Symbols and Last Trained Status
    useEffect(() => {
        const fetchData = async () => {
            setLoadingAlgos(true);
            try {
                // Fetch Algos
                const algoUrl = new URL(`${baseUrl}/api/forecast/algorithms`);
                if (symbol) algoUrl.searchParams.append('symbol', symbol);
                if (timeframe) algoUrl.searchParams.append('timeframe', timeframe);

                const response = await fetch(algoUrl.toString(), {
                    headers: getAuthHeaders()
                });
                if (response.ok) {
                    const data = await response.json();
                    setAlgorithms(Array.isArray(data.algorithms) ? data.algorithms : []);
                    const recommended = Array.isArray(data.algorithms) ? data.algorithms.find((a: any) => a.recommended) : null;
                    if (recommended && !selectedAlgorithm) setSelectedAlgorithm(recommended.id);
                } else {
                    throw new Error('Algorithm fetch failed');
                }

                // Fetch Symbols
                const symbolData = await api.getSymbols();
                if (symbolData && Array.isArray(symbolData.symbols)) {
                    const symbolStrings = symbolData.symbols.map((s: any) =>
                        typeof s === 'string' ? s : s.symbol
                    ).filter(Boolean);
                    setAllSymbols(symbolStrings);
                }

                // Fetch Last Trained Timestamp
                const trainResponse = await fetch(`${baseUrl}/api/v1/ml/train/status`, {
                    headers: getAuthHeaders()
                });
                if (trainResponse.ok) {
                    const trainData = await trainResponse.json();
                    if (trainData.metrics?.last_update) {
                        setLastTrained(trainData.metrics.last_update);
                    }
                }
            } catch (err) {
                console.warn('Initial fetch failed, using fallbacks');
                setAlgorithms([{
                    id: 'adaptive_ensemble_v2',
                    name: 'Default Forecast (Fallback)',
                    version: '1.0',
                    type: 'ensemble',
                    recommended: true,
                    supports_confidence_bands: true,
                    supported_timeframes: TIMEFRAMES,
                    max_horizon: 50,
                    description: 'Local fallback algorithm when backend is unreachable.',
                    features_used: ['OHLCV'],
                    estimated_latency_ms: 100
                }]);
            } finally {
                setLoadingAlgos(false);
            }
        };
        fetchData();
    }, [baseUrl]);

    // Handle character search for symbols
    useEffect(() => {
        if (!searchQuery) {
            setFilteredSymbols([]);
            return;
        }
        const filtered = allSymbols.filter(s =>
            s.toLowerCase().includes(searchQuery.toLowerCase())
        ).slice(0, 10);
        setFilteredSymbols(filtered);
    }, [searchQuery, allSymbols]);

    // Click outside to close dropdown
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setShowSymbolDropdown(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // 6. Chart Initialization
    useEffect(() => {
        if (chartRef.current) {
            chartInstance.current = echarts.init(chartRef.current, 'dark');
            const handleResize = () => chartInstance.current?.resize();
            window.addEventListener('resize', handleResize);
            return () => {
                window.removeEventListener('resize', handleResize);
                chartInstance.current?.dispose();
            };
        }
    }, []);

    // Render Chart when data changes
    useEffect(() => {
        if (forecastData && chartInstance.current) renderChart();
    }, [forecastData]);

    const selectSymbol = (sym: string) => {
        setSymbol(sym);
        setSearchQuery(sym);
        setShowSymbolDropdown(false);
    };

    const runForecast = async () => {
        if (!symbol) return;
        setLoading(true);
        setError(null);
        setForecastData(null);
        setLastApiStatus('Calling POST /run...');

        try {
            const response = await fetch(`${baseUrl}/api/forecast/run`, {
                method: 'POST',
                headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: symbol.toUpperCase(),
                    exchange: 'NSE',
                    timeframe,
                    horizon: Number(horizon),
                    algorithm_id: selectedAlgorithm,
                    confidence_level: 0.95,
                    include_confidence_bands: true
                })
            });

            const data = await response.json();
            setLastApiStatus(`${response.status} ${response.statusText}`);

            if (!response.ok) {
                throw new Error(data.detail?.message || data.detail || 'Forecast failed');
            }

            setForecastData(data);
        } catch (err: any) {
            setError(err.message || 'API connection failed');
            setLastApiStatus('Error');
        } finally {
            setLoading(false);
        }
    };

    const renderChart = () => {
        if (!forecastData || !chartInstance.current) return;

        const hist = Array.isArray(forecastData.candles_input) ? forecastData.candles_input : [];
        const fore = Array.isArray(forecastData.forecast) ? forecastData.forecast : [];

        if (hist.length === 0 && fore.length === 0) return;

        // Ensure hist has at least one element for connectivity
        if (hist.length === 0 && fore.length > 0) {
            // Mock one historical point if missing to prevent chart crash
            // This is a rare edge case if API returns only forecast
        }

        const timestamps = [...hist, ...fore].map(c => new Date(c.timestamp).toLocaleString('en-IN', {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        }));

        const actuals = [...hist.map(c => [c.open, c.close, c.low, c.high]), ...fore.map(() => [null, null, null, null])];
        const predicts = [...hist.map(() => null), ...fore.map(c => c.close)];
        const uppers = [...hist.map(() => null), ...fore.map(c => c.upper)];
        const lowers = [...hist.map(() => null), ...fore.map(c => c.lower)];

        const option: echarts.EChartsOption = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'cross', lineStyle: { color: '#444', width: 1 } },
                backgroundColor: '#212933',
                borderColor: '#2d3748',
                textStyle: { color: '#e2e8f0' }
            },
            legend: {
                data: ['Historical', 'Forecast', 'Confidence Band'],
                textStyle: { color: '#94a3b8', fontSize: 11 },
                top: 10
            },
            grid: { left: '3%', right: '3%', bottom: '10%', top: '15%', containLabel: true },
            xAxis: {
                type: 'category',
                data: timestamps,
                axisLabel: { color: '#64748b', fontSize: 10, rotate: 0 },
                axisLine: { lineStyle: { color: '#2d3748' } },
                axisTick: { show: false }
            },
            yAxis: {
                type: 'value',
                scale: true,
                axisLabel: { color: '#64748b', fontSize: 10 },
                splitLine: { lineStyle: { color: '#252d37' } },
                axisLine: { show: false }
            },
            visualMap: {
                show: false,
                dimension: 0,
                pieces: [{
                    lte: hist.length - 1,
                    color: '#4caf50'
                }, {
                    gt: hist.length - 1,
                    color: '#1c7ed6'
                }]
            },
            series: [
                {
                    name: 'Historical',
                    type: 'line',
                    data: [...hist.map(c => c.close), ...fore.map(() => null)],
                    lineStyle: { color: '#4caf50', width: 2 },
                    symbol: 'none'
                },
                {
                    name: 'Forecast',
                    type: 'line',
                    data: [...hist.map(() => null), hist[hist.length - 1].close, ...fore.map(c => c.close)],
                    symbol: 'circle',
                    symbolSize: 4,
                    lineStyle: { color: '#1c7ed6', width: 2, type: 'dashed' },
                    itemStyle: { color: '#1c7ed6' },
                    connectNulls: true
                },
                {
                    name: 'Confidence Band', type: 'line', data: uppers, symbol: 'none', stack: 'band',
                    lineStyle: { opacity: 0 }, areaStyle: { color: 'rgba(28,126,214,0.1)' }
                },
                {
                    name: 'Lower Band', type: 'line', data: lowers, symbol: 'none', stack: 'band',
                    lineStyle: { opacity: 0 }, areaStyle: { color: 'rgba(28,126,214,0.1)' }
                },
                {
                    type: 'line',
                    markLine: {
                        silent: true,
                        symbol: 'none',
                        label: { show: true, position: 'end', formatter: 'Forecast Boundary', color: '#1c7ed6', fontSize: 10 },
                        lineStyle: { color: '#1c7ed6', width: 1, type: 'solid', opacity: 0.5 },
                        data: [{ xAxis: timestamps[hist.length - 1] }]
                    }
                }
            ]
        };

        chartInstance.current.setOption(option, true);
    };

    return (
        <div className="min-h-screen bg-[#191e23] text-[#e2e8f0] font-sans selection:bg-brand-500/30">
            <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">

                {/* 1. Integrated Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-[#2d3748]">
                    <div className="flex items-center gap-5">
                        <div className="p-3.5 rounded-xl bg-[#1c7ed6]/10 text-[#1c7ed6] border border-[#1c7ed6]/20">
                            <TrendingUp size={28} />
                        </div>
                        <div>
                            <div className="flex items-center gap-3">
                                <h1 className="text-2xl font-bold text-white tracking-tight">Price Forecast</h1>
                                <span className="px-2 py-0.5 bg-[#252d37] text-slate-400 text-[10px] font-bold rounded border border-[#2d3748]">
                                    TRANSFORMER V1
                                </span>
                                <PriceForecastHelpGuide />
                            </div>
                            <div className="flex items-center gap-4 mt-0.5">
                                <p className="text-slate-500 text-sm">Attention-based predictive modeling via Parquet Feature Store</p>
                                {lastTrained && (
                                    <div className="flex items-center gap-1.5 px-2 py-0.5 bg-indigo-500/10 border border-indigo-500/20 rounded text-[10px] text-indigo-400 font-bold uppercase tracking-wider">
                                        <Activity size={10} />
                                        Last Trained: {new Date(lastTrained).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className={`px-4 py-1.5 rounded-lg text-[10px] font-bold border flex items-center gap-2 ${loading ? 'bg-blue-500/5 text-blue-400 border-blue-500/20' : 'bg-green-500/5 text-green-400 border-green-500/20'}`}>
                            <div className={`w-1.5 h-1.5 rounded-full ${loading ? 'bg-blue-400 animate-pulse' : 'bg-green-500'}`} />
                            <span className="tracking-wider uppercase">{loading ? 'Engine Processing' : 'Service Online'}</span>
                        </div>
                    </div>
                </div>

                {/* 2. Main Layout Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">

                    {/* Left Panel: Configuration */}
                    <div className="lg:col-span-1 space-y-8">

                        {/* Parameters Form */}
                        <div className="space-y-6">
                            <div className="relative" ref={dropdownRef}>
                                <label className="text-[11px] font-bold text-slate-500 uppercase mb-2 block tracking-wider">Symbol</label>
                                <div className="relative">
                                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-600" size={16} />
                                    <input
                                        type="text"
                                        value={searchQuery}
                                        onChange={(e) => {
                                            setSearchQuery(e.target.value.toUpperCase());
                                            setShowSymbolDropdown(true);
                                        }}
                                        onFocus={() => setShowSymbolDropdown(true)}
                                        className="w-full bg-[#212933] border border-[#2d3748] rounded-lg pl-11 pr-4 py-3 text-sm text-white font-medium outline-none focus:border-[#1c7ed6] focus:ring-1 focus:ring-[#1c7ed6]/20 transition-all"
                                        placeholder="Search asset..."
                                    />
                                </div>

                                {showSymbolDropdown && filteredSymbols.length > 0 && (
                                    <div className="absolute z-50 left-0 right-0 mt-1 bg-[#212933] border border-[#2d3748] rounded-lg shadow-2xl max-h-48 overflow-y-auto">
                                        {filteredSymbols.map(sym => (
                                            <button
                                                key={sym}
                                                onClick={() => selectSymbol(sym)}
                                                className="w-full text-left px-5 py-2.5 hover:bg-[#1c7ed6]/10 text-slate-300 hover:text-white text-sm transition-all border-b border-[#2d3748] last:border-0"
                                            >
                                                {sym}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="flex-1">
                                    <label className="text-[11px] font-bold text-slate-500 uppercase mb-2 block tracking-wider">Interval</label>
                                    <select
                                        value={timeframe}
                                        onChange={(e) => setTimeframe(e.target.value)}
                                        className="w-full bg-[#212933] border border-[#2d3748] rounded-lg px-4 py-3 text-sm text-white font-medium outline-none focus:border-[#1c7ed6] transition-all cursor-pointer"
                                    >
                                        {TIMEFRAMES.map(tf => <option key={tf} value={tf}>{tf}</option>)}
                                    </select>
                                </div>
                                <div className="w-full">
                                    <label className="text-[11px] font-bold text-slate-500 uppercase mb-2 block tracking-wider">Horizon</label>
                                    <input
                                        type="number"
                                        value={horizon}
                                        onChange={(e) => setHorizon(parseInt(e.target.value) || 1)}
                                        className="w-full bg-[#212933] border border-[#2d3748] rounded-lg px-4 py-3 text-sm text-white font-medium outline-none focus:border-[#1c7ed6] transition-all"
                                    />
                                </div>
                            </div>

                            <button
                                onClick={runForecast}
                                disabled={loading || !symbol}
                                className="w-full bg-[#1c7ed6] hover:bg-[#1971c2] disabled:opacity-50 text-white font-bold py-3.5 rounded-lg shadow-lg active:translate-y-px transition-all flex items-center justify-center gap-3 text-sm"
                            >
                                {loading ? <Loader2 className="animate-spin w-4 h-4" /> : <Play size={16} fill="currentColor" />}
                                EXECUTE ANALYSIS
                            </button>
                        </div>

                        {/* Algorithm List */}
                        <div className="pt-6 border-t border-[#2d3748]">
                            <h3 className="text-[11px] font-bold text-slate-500 uppercase mb-4 tracking-wider">Available Models</h3>
                            {loadingAlgos ? (
                                <div className="flex items-center gap-3 py-4">
                                    <Loader2 className="animate-spin w-3 h-3 text-[#1c7ed6]" />
                                    <span className="text-xs text-slate-500 font-medium tracking-tight">Syncing algorithms...</span>
                                </div>
                            ) : (
                                <div className="space-y-2.5">
                                    {algorithms.map(algo => (
                                        <button
                                            key={algo.id}
                                            onClick={() => setSelectedAlgorithm(algo.id)}
                                            className={`w-full text-left px-4 py-3.5 rounded-xl border transition-all duration-200 ${selectedAlgorithm === algo.id ? 'bg-[#1c7ed6]/5 border-[#1c7ed6]/40 text-[#1c7ed6]' : 'bg-[#212933]/40 border-[#2d3748] text-slate-500 hover:border-slate-700'}`}
                                        >
                                            <div className="flex items-center justify-between mb-1.5">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-xs font-bold uppercase tracking-tight">{algo.name}</span>
                                                    {algo.is_pro && (
                                                        <span className="text-[8px] bg-[#1c7ed6] text-white px-1.5 py-0.5 rounded font-bold uppercase">PRO</span>
                                                    )}
                                                </div>
                                                {algo.training_status && (
                                                    <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded uppercase ${algo.training_status === 'READY' ? 'text-green-500 bg-green-500/10' : 'text-amber-500 bg-amber-500/10'}`}>
                                                        {algo.training_status}
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-[10px] leading-relaxed opacity-80 font-medium">{algo.description}</p>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Right Panel: Workspace */}
                    <div className="lg:col-span-3 space-y-6">

                        {/* Summary Bar */}
                        {forecastData && !loading && (
                            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                                <div className="bg-[#212933] p-4 rounded-xl border border-[#2d3748]">
                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">Predicted Delta</p>
                                    <div className={`flex items-baseline gap-2 text-xl font-bold ${forecastData.metrics.predicted_move_pct >= 0 ? 'text-[#4caf50]' : 'text-red-400'}`}>
                                        {forecastData.metrics.predicted_move_pct >= 0 ? '▲' : '▼'}
                                        {Math.abs(forecastData.metrics.predicted_move_pct).toFixed(2)}%
                                    </div>
                                </div>
                                <div className="bg-[#212933] p-4 rounded-xl border border-[#2d3748]">
                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">Confidence Level</p>
                                    <div className="text-xl font-bold text-white">
                                        {(forecastData.metrics.confidence_score * 100).toFixed(1)}%
                                    </div>
                                </div>
                                <div className="bg-[#212933] p-4 rounded-xl border border-[#2d3748]">
                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">Market Volatility</p>
                                    <div className="text-xl font-bold text-white uppercase tracking-tight">
                                        {forecastData.metrics.volatility_label}
                                    </div>
                                </div>
                                <div className="bg-[#212933] p-4 rounded-xl border border-[#2d3748]">
                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">Core Latency</p>
                                    <div className="text-xl font-bold text-[#1c7ed6]">
                                        {forecastData.metrics.model_latency_ms}ms
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Chart Workspace */}
                        <div className="bg-[#1b2229] rounded-2xl border border-[#2d3748] relative overflow-hidden min-h-[500px] shadow-sm">
                            {error && (
                                <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#191e23]/90 p-8">
                                    <div className="bg-red-400/5 border border-red-500/20 p-8 rounded-2xl text-center max-w-sm">
                                        <AlertCircle className="text-red-500 mx-auto mb-4" size={32} />
                                        <h4 className="text-white text-base font-bold mb-2">Service Error</h4>
                                        <p className="text-slate-500 text-xs mb-6 leading-relaxed font-medium">{error}</p>
                                        <button onClick={runForecast} className="w-full text-xs font-bold text-white bg-red-600 hover:bg-red-500 py-3 rounded-lg transition-all active:scale-95 uppercase">Retry Session</button>
                                    </div>
                                </div>
                            )}

                            {!forecastData && !loading && !error && (
                                <div className="absolute inset-0 flex flex-col items-center justify-center p-12 text-center">
                                    <BarChart3 size={40} className="text-slate-700 mb-5" />
                                    <h4 className="text-slate-500 font-bold uppercase tracking-wider text-[10px] mb-2">Waiting for Execution</h4>
                                    <p className="text-slate-600 text-xs max-w-[200px] leading-relaxed font-medium">Select a symbol and algorithm to begin predictive analysis.</p>
                                </div>
                            )}

                            {loading && (
                                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#191e23]/40 backdrop-blur-[2px]">
                                    <div className="w-12 h-12 border-4 border-[#2d3748] border-t-[#1c7ed6] rounded-full animate-spin mb-6" />
                                    <p className="text-slate-400 font-bold tracking-widest uppercase text-[9px] animate-pulse">Running Neural Inference</p>
                                </div>
                            )}

                            <div ref={chartRef} className="w-full h-[500px]" />
                        </div>

                        {/* Diagnostics Panel */}
                        <div className="bg-[#212933]/30 rounded-xl border border-[#2d3748] overflow-hidden">
                            <button
                                onClick={() => setShowDebug(!showDebug)}
                                className="w-full flex items-center justify-between px-6 py-4 hover:bg-[#212933]/50 transition-all font-bold text-[11px] uppercase tracking-widest text-slate-500"
                            >
                                <div className="flex items-center gap-3">
                                    <Terminal size={14} className="text-slate-600" />
                                    <span>Diagnostics Node</span>
                                </div>
                                <div className="flex items-center gap-4">
                                    <span className={`text-[9px] px-2 py-0.5 rounded-full border ${lastApiStatus.includes('200') ? 'bg-green-500/5 border-green-500/20 text-green-500/80' : 'bg-[#252d37] border-[#2d3748] text-slate-500'}`}>{lastApiStatus}</span>
                                    {showDebug ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                </div>
                            </button>

                            {showDebug && (
                                <div className="p-6 bg-black/20 border-t border-[#2d3748] space-y-6">
                                    <div className="grid grid-cols-3 gap-6">
                                        <div>
                                            <p className="text-[9px] text-slate-600 font-bold uppercase tracking-widest mb-1">Endpoints</p>
                                            <p className="text-xs font-mono text-[#1c7ed6] truncate">{baseUrl}</p>
                                        </div>
                                        <div>
                                            <p className="text-[9px] text-slate-600 font-bold uppercase tracking-widest mb-1">Active Model</p>
                                            <p className="text-xs font-mono text-white">{selectedAlgorithm}</p>
                                        </div>
                                        <div>
                                            <p className="text-[9px] text-slate-600 font-bold uppercase tracking-widest mb-1">Session ID</p>
                                            <p className="text-xs font-mono text-slate-500">{forecastData?.request_id || 'N/A'}</p>
                                        </div>
                                    </div>
                                    {forecastData && (
                                        <div className="space-y-2">
                                            <p className="text-[9px] text-slate-600 font-bold uppercase tracking-widest">Raw Inference Output</p>
                                            <pre className="text-[10px] font-mono bg-[#1b2229] p-4 rounded-lg overflow-auto max-h-[200px] text-slate-400 border border-[#2d3748] custom-scrollbar">
                                                {JSON.stringify(forecastData, null, 2)}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default PriceForecast;

