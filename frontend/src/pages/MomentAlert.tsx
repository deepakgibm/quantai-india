import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
    Zap,
    TrendingUp,
    TrendingDown,
    Activity,
    RefreshCw,
    Clock
} from 'lucide-react';
import { getAuthHeaders, API_URL, api } from '../services/api';
import { useMarketDataStream } from '../hooks/useMarketDataStream';
import { calculatePriceChange } from '../utils/marketPrice';

interface StockTick {
    symbol: string;
    ltp: number;
    prev_close?: number;
    change_pct?: number;
    momentum_score: number;
    bucket: string;
    pct_bucket?: string;
    direction?: string;
    correlation: number;
    source?: string;
    confidence?: string;
    last_update: string;
}

interface DataStatus {
    source: string;
    is_healthy: boolean;
    last_tick: string | null;
    stock_count: number;
    poll_interval: number;
}

interface Week52BreakoutStock {
    symbol: string;
    ltp: number;
    high_52w: number;
    low_52w: number;
    prev_close: number;
    change_pct: number;
    breakout_type: string;
    breakout_pct: number;
    days_data: number;
    volume: number;
    avg_volume: number;
    volume_ratio: number;
    industry: string;
    last_update: string;
}

const BUCKETS = [
    { id: 'STRONG_BULLISH', label: 'Strong Bullish', color: 'green', icon: TrendingUp },
    { id: 'MODERATE_BULLISH', label: 'Moderate Bullish', color: 'teal', icon: Activity },
    { id: 'NEUTRAL', label: 'Neutral', color: 'slate', icon: Clock },
    { id: 'MODERATE_BEARISH', label: 'Moderate Bearish', color: 'orange', icon: Activity },
    { id: 'STRONG_BEARISH', label: 'Strong Bearish', color: 'red', icon: TrendingDown },
];

const MomentAlert: React.FC = () => {
    const [ticks, setTicks] = useState<StockTick[]>([]);
    const [dataStatus, setDataStatus] = useState<DataStatus | null>(null);
    const [lastUpdate, setLastUpdate] = useState<string>('');
    const [highBreakouts, setHighBreakouts] = useState<Week52BreakoutStock[]>([]);
    const [lowBreakdowns, setLowBreakdowns] = useState<Week52BreakoutStock[]>([]);
    const [week52Loading, setWeek52Loading] = useState(true);

    // ── Singleton WS via shared hook (no duplicate socket) ──────────────────
    const handleDataUpdate = useCallback((message: any) => {
        if (message.type === 'bucket_update' && Array.isArray(message.data)) {
            const sortedTicks = (message.data as StockTick[]).sort(
                (a, b) => b.momentum_score - a.momentum_score
            );
            setTicks(sortedTicks);
            setLastUpdate(message.timestamp);
            if (message.status) setDataStatus(message.status);
        }
    }, []);

    const { isConnected } = useMarketDataStream({ onMessage: handleDataUpdate });

    useEffect(() => {
        fetchWeek52Breakouts();
        const week52Interval = setInterval(fetchWeek52Breakouts, 300_000);
        return () => clearInterval(week52Interval);
    }, []);



    const fetchWeek52Breakouts = async (forceRefresh: boolean = false) => {
        try {
            setWeek52Loading(true);
            const data = await api.getWeek52Breakouts(forceRefresh);
            if (data) {
                setHighBreakouts(Array.isArray(data.high_breakouts) ? data.high_breakouts : []);
                setLowBreakdowns(Array.isArray(data.low_breakdowns) ? data.low_breakdowns : []);
            }
        } catch (error) {
            console.error('Error fetching 52-week breakouts:', error);
        } finally {
            setWeek52Loading(false);
        }
    };



    const bucketedStocks = useMemo(() => {
        const groups: Record<string, StockTick[]> = {};
        BUCKETS.forEach(b => {
            groups[b.id] = ticks.filter(t => {
                if (b.id === 'STRONG_BULLISH') return t.bucket === 'STRONG_BULLISH' || t.bucket === 'EXTREME_BULLISH';
                if (b.id === 'STRONG_BEARISH') return t.bucket === 'STRONG_BEARISH' || t.bucket === 'EXTREME_BEARISH';
                return t.bucket === b.id;
            });
        });
        console.log('[Momentum] Bucketed counts:', Object.fromEntries(Object.entries(groups).map(([k, v]) => [k, v.length])));
        return groups;
    }, [ticks]);

    const getBucketStocks = (bucketId: string) => {
        return bucketedStocks[bucketId] || [];
    };

    const [isRefreshing, setIsRefreshing] = useState(false);

    const handleRefresh = async () => {
        setIsRefreshing(true);
        try {
            await fetchWeek52Breakouts(true);
        } catch (error) {
            console.error('Refresh error:', error);
        } finally {
            setIsRefreshing(false);
        }
    };

    return (
        <div className="flex flex-col h-full gap-6 p-2 animate-in fade-in duration-700">
            {/* Header with Refresh Button */}
            <div className="flex items-center justify-between bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200/60 dark:border-slate-700/60 rounded-2xl px-6 py-4 shadow-lg">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl shadow-lg shadow-cyan-500/30">
                        <Zap size={24} className="text-white" />
                    </div>
                    <div>
                        <h1 className="text-xl font-black text-slate-900 dark:text-white tracking-tight">Momentum Alert</h1>
                        <div className="flex items-center gap-3 mt-1">
                            <div className={`flex items-center gap-1.5 text-xs font-semibold ${isConnected ? 'text-emerald-500' : 'text-rose-500'}`}>
                                <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`}></span>
                            {isConnected ? 'Live' : 'Reconnecting...'}
                            </div>
                            {lastUpdate && (
                                <span className="text-xs text-slate-400 flex items-center gap-1">
                                    <Clock size={12} />
                                    Updated: {new Date(lastUpdate).toLocaleTimeString()}
                                </span>
                            )}
                        </div>
                    </div>
                </div>
                <button
                    onClick={handleRefresh}
                    disabled={isRefreshing}
                    className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-bold text-sm rounded-xl shadow-lg shadow-cyan-500/30 hover:shadow-xl hover:shadow-cyan-500/40 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    <RefreshCw size={18} className={isRefreshing ? 'animate-spin' : ''} />
                    {isRefreshing ? 'Refreshing...' : 'Refresh'}
                </button>
            </div>

            {/* Diagnostic Stats Bar */}
            <div className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200/60 dark:border-slate-700/60 rounded-2xl p-4 shadow-lg flex flex-wrap items-center justify-around gap-4 text-center">
                <div>
                    <span className="block text-xs font-black uppercase text-slate-400">Total Ticks</span>
                    <span className="text-xl font-extrabold text-slate-800 dark:text-white">{ticks.length}</span>
                </div>
                <div className="h-8 w-px bg-slate-200 dark:bg-slate-700 hidden sm:block"></div>
                <div>
                    <span className="block text-xs font-black uppercase text-emerald-500">Strong Bullish</span>
                    <span className="text-xl font-extrabold text-emerald-500">{getBucketStocks('STRONG_BULLISH').length}</span>
                </div>
                <div className="h-8 w-px bg-slate-200 dark:bg-slate-700 hidden sm:block"></div>
                <div>
                    <span className="block text-xs font-black uppercase text-teal-500">Moderate Bullish</span>
                    <span className="text-xl font-extrabold text-teal-500">{getBucketStocks('MODERATE_BULLISH').length}</span>
                </div>
                <div className="h-8 w-px bg-slate-200 dark:bg-slate-700 hidden sm:block"></div>
                <div>
                    <span className="block text-xs font-black uppercase text-slate-500">Neutral</span>
                    <span className="text-xl font-extrabold text-slate-500">{getBucketStocks('NEUTRAL').length}</span>
                </div>
                <div className="h-8 w-px bg-slate-200 dark:bg-slate-700 hidden sm:block"></div>
                <div>
                    <span className="block text-xs font-black uppercase text-orange-500">Moderate Bearish</span>
                    <span className="text-xl font-extrabold text-orange-500">{getBucketStocks('MODERATE_BEARISH').length}</span>
                </div>
                <div className="h-8 w-px bg-slate-200 dark:bg-slate-700 hidden sm:block"></div>
                <div>
                    <span className="block text-xs font-black uppercase text-rose-500">Strong Bearish</span>
                    <span className="text-xl font-extrabold text-rose-500">{getBucketStocks('STRONG_BEARISH').length}</span>
                </div>
            </div>

            {/* Momentum Pulse Buckets */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
                {BUCKETS.map((bucket) => {
                    const bucketStocks = getBucketStocks(bucket.id);
                    return (
                        <div key={bucket.id} className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200/60 dark:border-slate-700/60 rounded-[32px] overflow-hidden flex flex-col shadow-lg transition-all hover:shadow-2xl">
                            <div className={`p-4 bg-${bucket.color}-500/10 border-b border-${bucket.color}-500/20 flex items-center justify-between`}>
                                <div className="flex items-center gap-2">
                                    <div className={`p-1.5 bg-${bucket.color}-500 text-white rounded-lg shadow-lg shadow-${bucket.color}-500/20`}>
                                        <bucket.icon size={14} />
                                    </div>
                                    <span className="font-black text-[10px] tracking-tight text-slate-800 dark:text-white uppercase">{bucket.label}</span>
                                </div>
                                <span className="text-[10px] font-black text-slate-400 bg-white/50 dark:bg-slate-900/50 px-2 py-0.5 rounded-full">{bucketStocks.length}</span>
                            </div>

                            <div className="flex-1 p-4 space-y-3 min-h-[150px] max-h-[350px] overflow-y-auto custom-scrollbar">
                                {bucketStocks.length === 0 ? (
                                    <div className="h-full flex flex-col items-center justify-center opacity-30">
                                        <Activity size={24} className="text-slate-400 mb-1" />
                                        <span className="text-[8px] font-black uppercase tracking-widest">No Pulse</span>
                                    </div>
                                ) : (
                                    bucketStocks.map(stock => (
                                        <div key={stock.symbol} className="p-3 bg-white dark:bg-slate-900/40 border border-slate-100 dark:border-slate-700/50 rounded-xl hover:border-cyan-500/30 transition-all">
                                            <div className="flex justify-between items-center">
                                                <h4 className="font-black text-xs text-slate-900 dark:text-white uppercase tracking-tight">{stock.symbol}</h4>
                                                <div className="text-right">
                                                    <span className="text-xs font-black text-slate-800 dark:text-slate-200 block">₹{stock.ltp.toLocaleString()}</span>
                                                    {(() => {
                                                        const details = calculatePriceChange(stock.ltp, stock.prev_close, stock.change_pct);
                                                        const isUp = details.direction === 'up';
                                                        const isDown = details.direction === 'down';
                                                        return (
                                                            <span className={`text-[10px] font-bold ${isUp ? 'text-green-500' : isDown ? 'text-rose-500' : 'text-slate-400'}`}>
                                                                {isUp ? '▲ +' : isDown ? '▼ ' : '▬ '}{Math.abs(details.changePercent).toFixed(2)}%
                                                            </span>
                                                        );
                                                    })()}
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

        </div>
    );
};

export default MomentAlert;
