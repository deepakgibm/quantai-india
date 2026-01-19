import React, { useState, useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { Search, Play, TrendingUp, AlertCircle, Clock, Loader2 } from 'lucide-react';
import { API_URL, getAuthHeaders } from '../services/api';

interface ForecastData {
    symbol: string;
    timeframe: string;
    timestamps: string[];
    actual: (number | null)[];
    predicted: (number | null)[];
    upper_band: (number | null)[];
    lower_band: (number | null)[];
    confidence: number;
    model_version: string;
    data_source: string;
    last_trained: string | null;
}

const TIMEFRAMES = ['5m', '15m', '1h', '1d'];

const PriceForecast: React.FC = () => {
    const [symbol, setSymbol] = useState('RELIANCE');
    const [timeframe, setTimeframe] = useState('5m');
    const [horizon, setHorizon] = useState(10);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [data, setData] = useState<ForecastData | null>(null);
    const chartRef = useRef<HTMLDivElement>(null);
    const chartInstance = useRef<echarts.ECharts | null>(null);

    // Initialize ECharts
    useEffect(() => {
        if (chartRef.current) {
            chartInstance.current = echarts.init(chartRef.current, 'dark');

            const handleResize = () => {
                chartInstance.current?.resize();
            };
            window.addEventListener('resize', handleResize);

            return () => {
                window.removeEventListener('resize', handleResize);
                chartInstance.current?.dispose();
            };
        }
    }, []);

    // Update chart when data changes
    useEffect(() => {
        if (data && chartInstance.current) {
            renderChart();
        }
    }, [data]);

    const fetchForecast = async () => {
        setLoading(true);
        setError(null);

        try {
            const url = `${API_URL}/api/v1/ml/predict?symbol=${symbol}&timeframe=${timeframe}&horizon=${horizon}`;
            const response = await fetch(url, {
                headers: getAuthHeaders()
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail?.message || 'Prediction failed');
            }

            const result: ForecastData = await response.json();
            setData(result);
        } catch (err: any) {
            setError(err.message || 'Failed to fetch forecast');
            setData(null);
        } finally {
            setLoading(false);
        }
    };

    const renderChart = () => {
        if (!data || !chartInstance.current) return;

        // Prepare data for chart
        const timestamps = data.timestamps.map(ts => new Date(ts).toLocaleString('en-IN', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }));

        // Find where prediction starts (first non-null predicted value)
        const predStartIdx = data.predicted.findIndex(v => v !== null);

        // Prepare candlestick data (for actual prices, we simulate OHLC from close)
        const actualData = data.actual.map((close, idx) => {
            if (close === null) return null;
            // Simulate OHLC from close (simplified for display)
            const open = idx > 0 && data.actual[idx - 1] ? data.actual[idx - 1] : close;
            const high = Math.max(open as number, close) * 1.002;
            const low = Math.min(open as number, close) * 0.998;
            return [open, close, low, high]; // ECharts format: [open, close, low, high]
        });

        const option: echarts.EChartsOption = {
            backgroundColor: 'transparent',
            title: {
                text: `${data.symbol} - Adaptive Price Forecast`,
                subtext: `Model: ${data.model_version} | Confidence: ${(data.confidence * 100).toFixed(1)}% | Source: ${data.data_source}`,
                left: 'center',
                textStyle: { color: '#e2e8f0', fontSize: 16 },
                subtextStyle: { color: '#94a3b8', fontSize: 12 }
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'cross' },
                backgroundColor: 'rgba(15, 23, 42, 0.95)',
                borderColor: '#334155',
                textStyle: { color: '#e2e8f0' },
                formatter: (params: any) => {
                    const items = Array.isArray(params) ? params : [params];
                    let result = `<strong>${items[0]?.axisValue || ''}</strong><br/>`;

                    items.forEach((item: any) => {
                        if (item.seriesName === 'Actual' && item.data) {
                            result += `${item.marker} Actual: ₹${item.data[1]?.toFixed(2) || 'N/A'}<br/>`;
                        } else if (item.seriesName === 'Predicted' && item.data !== null) {
                            result += `${item.marker} Predicted: ₹${item.data?.toFixed(2)}<br/>`;
                        } else if (item.seriesName === 'Confidence Band' && item.data) {
                            result += `${item.marker} Band: ₹${item.data[1]?.toFixed(2)} - ₹${item.data[2]?.toFixed(2)}<br/>`;
                        }
                    });

                    return result;
                }
            },
            legend: {
                data: ['Actual', 'Predicted', 'Confidence Band'],
                top: 50,
                textStyle: { color: '#94a3b8' }
            },
            grid: {
                left: '5%',
                right: '5%',
                bottom: '15%',
                top: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: timestamps,
                axisLine: { lineStyle: { color: '#475569' } },
                axisLabel: {
                    color: '#94a3b8',
                    rotate: 45,
                    fontSize: 10
                },
                splitLine: { show: false }
            },
            yAxis: {
                type: 'value',
                scale: true,
                axisLine: { lineStyle: { color: '#475569' } },
                axisLabel: {
                    color: '#94a3b8',
                    formatter: '₹{value}'
                },
                splitLine: {
                    lineStyle: { color: '#334155', type: 'dashed' }
                }
            },
            dataZoom: [
                {
                    type: 'inside',
                    start: 50,
                    end: 100
                },
                {
                    type: 'slider',
                    start: 50,
                    end: 100,
                    height: 20,
                    bottom: 10,
                    borderColor: '#475569',
                    fillerColor: 'rgba(59, 130, 246, 0.2)',
                    handleStyle: { color: '#3b82f6' },
                    textStyle: { color: '#94a3b8' }
                }
            ],
            series: [
                // Candlestick for actual prices
                {
                    name: 'Actual',
                    type: 'candlestick',
                    data: actualData,
                    itemStyle: {
                        color: '#22c55e',
                        color0: '#ef4444',
                        borderColor: '#22c55e',
                        borderColor0: '#ef4444'
                    }
                },
                // Line for predicted prices
                {
                    name: 'Predicted',
                    type: 'line',
                    data: data.predicted,
                    symbol: 'circle',
                    symbolSize: 6,
                    lineStyle: {
                        color: '#8b5cf6',
                        width: 2,
                        type: 'dashed'
                    },
                    itemStyle: { color: '#8b5cf6' },
                    connectNulls: false
                },
                // Area for confidence band
                {
                    name: 'Confidence Band',
                    type: 'custom',
                    renderItem: (params, api) => {
                        const xValue = api.value(0);
                        const upperValue = data.upper_band[params.dataIndex as number];
                        const lowerValue = data.lower_band[params.dataIndex as number];

                        if (upperValue === null || lowerValue === null) return;

                        const xPixel = api.coord([xValue, 0])[0];
                        const upperPixel = api.coord([xValue, upperValue])[1];
                        const lowerPixel = api.coord([xValue, lowerValue])[1];

                        const width = 10; // Band width

                        return {
                            type: 'rect',
                            shape: {
                                x: xPixel - width / 2,
                                y: upperPixel,
                                width: width,
                                height: lowerPixel - upperPixel
                            },
                            style: {
                                fill: 'rgba(139, 92, 246, 0.2)'
                            }
                        };
                    },
                    data: timestamps.map((_, idx) => [idx, data.upper_band[idx], data.lower_band[idx]]),
                    z: -1
                }
            ]
        };

        chartInstance.current.setOption(option, true);
    };

    const getSourceBadge = () => {
        if (!data) return null;

        const colors: Record<string, string> = {
            'LIVE': 'bg-green-500/20 text-green-400 border-green-500/30',
            'REST': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
            'DB': 'bg-amber-500/20 text-amber-400 border-amber-500/30',
            'DELAYED': 'bg-amber-500/20 text-amber-400 border-amber-500/30'
        };

        return colors[data.data_source] || 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-violet-500/20">
                        <TrendingUp className="w-6 h-6 text-violet-400" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-white">AI Price Forecast</h1>
                        <p className="text-sm text-slate-400">Adaptive ensemble prediction with confidence bands</p>
                    </div>
                </div>

                {data && (
                    <div className={`px-3 py-1.5 rounded-full border ${getSourceBadge()} flex items-center gap-2`}>
                        <div className="w-2 h-2 rounded-full bg-current animate-pulse"></div>
                        <span className="text-xs font-medium">{data.data_source}</span>
                    </div>
                )}
            </div>

            {/* Control Panel */}
            <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {/* Symbol Input */}
                    <div className="space-y-1.5">
                        <label className="text-xs text-slate-400 uppercase tracking-wide">Symbol</label>
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                                placeholder="e.g., RELIANCE"
                                className="w-full pl-10 pr-4 py-2.5 bg-slate-900/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                            />
                        </div>
                    </div>

                    {/* Timeframe Selector */}
                    <div className="space-y-1.5">
                        <label className="text-xs text-slate-400 uppercase tracking-wide">Timeframe</label>
                        <select
                            value={timeframe}
                            onChange={(e) => setTimeframe(e.target.value)}
                            className="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                        >
                            {TIMEFRAMES.map(tf => (
                                <option key={tf} value={tf}>{tf}</option>
                            ))}
                        </select>
                    </div>

                    {/* Horizon Slider */}
                    <div className="space-y-1.5">
                        <label className="text-xs text-slate-400 uppercase tracking-wide">
                            Prediction Horizon: {horizon} candles
                        </label>
                        <input
                            type="range"
                            min={1}
                            max={30}
                            value={horizon}
                            onChange={(e) => setHorizon(parseInt(e.target.value))}
                            className="w-full h-2.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-violet-500"
                        />
                    </div>

                    {/* Run Button */}
                    <div className="flex items-end">
                        <button
                            onClick={fetchForecast}
                            disabled={loading || !symbol}
                            className="w-full px-6 py-2.5 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 rounded-lg font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Predicting...
                                </>
                            ) : (
                                <>
                                    <Play className="w-4 h-4" />
                                    Run Prediction
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>

            {/* Error Display */}
            {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
                    <div>
                        <h4 className="font-medium text-red-400">Prediction Failed</h4>
                        <p className="text-sm text-red-300/80">{error}</p>
                    </div>
                </div>
            )}

            {/* Chart Area */}
            <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
                <div
                    ref={chartRef}
                    className="w-full h-[500px]"
                    style={{ minHeight: '500px' }}
                />

                {!data && !loading && !error && (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="text-center text-slate-500">
                            <TrendingUp className="w-12 h-12 mx-auto mb-3 opacity-50" />
                            <p>Enter a symbol and click "Run Prediction" to generate forecast</p>
                        </div>
                    </div>
                )}
            </div>

            {/* Model Info Panel */}
            {data && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                        <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Model Version</p>
                        <p className="text-lg font-bold text-white">{data.model_version}</p>
                    </div>

                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                        <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Confidence Score</p>
                        <div className="flex items-center gap-2">
                            <div className="h-2 flex-1 bg-slate-700 rounded-full">
                                <div
                                    className="h-full bg-gradient-to-r from-violet-500 to-purple-500 rounded-full"
                                    style={{ width: `${data.confidence * 100}%` }}
                                />
                            </div>
                            <span className="text-lg font-bold text-white">{(data.confidence * 100).toFixed(1)}%</span>
                        </div>
                    </div>

                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                        <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Data Source</p>
                        <p className="text-lg font-bold text-white flex items-center gap-2">
                            {data.data_source}
                            {data.data_source === 'DB' && (
                                <span className="text-xs text-amber-400">(Delayed)</span>
                            )}
                        </p>
                    </div>

                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                        <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Last Trained</p>
                        <p className="text-lg font-bold text-white flex items-center gap-2">
                            <Clock className="w-4 h-4 text-slate-400" />
                            {data.last_trained ? new Date(data.last_trained).toLocaleDateString() : 'On-demand'}
                        </p>
                    </div>
                </div>
            )}

            {/* Disclaimer */}
            <div className="text-center text-xs text-slate-500 py-4">
                <p>⚠️ Predictions are statistical forecasts based on historical patterns. Not investment advice.</p>
            </div>
        </div>
    );
};

export default PriceForecast;
