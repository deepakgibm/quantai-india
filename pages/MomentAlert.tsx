import React, { useState, useEffect, useRef } from 'react';
import {
    Zap,
    TrendingUp,
    TrendingDown,
    Activity,
    AlertCircle,
    ChevronRight,
    Maximize2,
    Filter,
    RefreshCw,
    Bell,
    Clock,
    ArrowUpCircle,
    ArrowDownCircle,
    Target,
    BarChart3
} from 'lucide-react';

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
    const [isConnected, setIsConnected] = useState(false);
    const [dataStatus, setDataStatus] = useState<DataStatus | null>(null);
    const [lastUpdate, setLastUpdate] = useState<string>('');
    const [connectionMode, setConnectionMode] = useState<'WS' | 'REST'>('WS');
    const [highBreakouts, setHighBreakouts] = useState<Week52BreakoutStock[]>([]);
    const [lowBreakdowns, setLowBreakdowns] = useState<Week52BreakoutStock[]>([]);
    const [week52Loading, setWeek52Loading] = useState(true);
    const ws = useRef<WebSocket | null>(null);
    const pollInterval = useRef<NodeJS.Timeout | null>(null);
    const wsRetryCount = useRef(0);
    const maxWsRetries = 3;

    useEffect(() => {
        connectWS();
        fetchWeek52Breakouts();

        // Refresh 52-week data every 5 minutes
        const week52Interval = setInterval(fetchWeek52Breakouts, 300000);

        return () => {
            if (ws.current) ws.current.close();
            if (pollInterval.current) clearInterval(pollInterval.current);
            clearInterval(week52Interval);
        };
    }, []);

    const fetchWeek52Breakouts = async () => {
        try {
            setWeek52Loading(true);
            const response = await fetch('http://localhost:8000/api/scanner/week52-breakouts');
            if (response.ok) {
                const data = await response.json();
                setHighBreakouts(data.high_breakouts || []);
                setLowBreakdowns(data.low_breakdowns || []);
            }
        } catch (error) {
            console.error('Error fetching 52-week breakouts:', error);
        } finally {
            setWeek52Loading(false);
        }
    };

    const handleDataUpdate = (message: any) => {
        if (message.type === 'bucket_update') {
            const sortedTicks = (message.data as StockTick[]).sort((a, b) => b.momentum_score - a.momentum_score);
            setTicks(sortedTicks);
            setLastUpdate(message.timestamp);

            // Update status info
            if (message.status) {
                setDataStatus(message.status);
            }
        }
    };

    const connectWS = () => {
        ws.current = new WebSocket('ws://localhost:8000/api/scanner/ws/scanner');

        ws.current.onopen = () => {
            setIsConnected(true);
            setConnectionMode('WS');
            wsRetryCount.current = 0;
            console.log('Connected to Scanner WS');

            // Stop REST polling if active
            if (pollInterval.current) {
                clearInterval(pollInterval.current);
                pollInterval.current = null;
            }
        };

        ws.current.onmessage = (event) => {
            const message = JSON.parse(event.data);
            handleDataUpdate(message);
        };

        ws.current.onerror = () => {
            console.warn('WebSocket error');
        };

        ws.current.onclose = () => {
            setIsConnected(false);
            wsRetryCount.current += 1;

            if (wsRetryCount.current < maxWsRetries) {
                console.log(`WebSocket closed, retrying (${wsRetryCount.current}/${maxWsRetries})...`);
                setTimeout(connectWS, 3000);
            } else {
                console.log('WebSocket failed, switching to REST polling');
                startRestPolling();
            }
        };
    };

    const startRestPolling = () => {
        setConnectionMode('REST');
        setIsConnected(true);
        console.log('Starting REST polling mode');

        // Initial fetch
        fetchMomentumData();

        // Poll every 5 seconds
        pollInterval.current = setInterval(fetchMomentumData, 5000);
    };

    const fetchMomentumData = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/scanner/momentum');
            if (response.ok) {
                const message = await response.json();
                handleDataUpdate(message);
            }
        } catch (error) {
            console.error('REST polling error:', error);
        }
    };

    const getBucketStocks = (bucketId: string) => {
        return ticks.filter(t => t.bucket === bucketId);
    };

    return (
        <div className="flex flex-col h-full gap-6 p-2 animate-in fade-in duration-700">
            {/* Momentum Pulse Buckets */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
                {BUCKETS.map((bucket) => {
                    const bucketStocks = ticks.filter(t => {
                        if (bucket.id === 'STRONG_BULLISH') return t.bucket === 'STRONG_BULLISH' || t.bucket === 'EXTREME_BULLISH';
                        if (bucket.id === 'STRONG_BEARISH') return t.bucket === 'STRONG_BEARISH' || t.bucket === 'EXTREME_BEARISH';
                        return t.bucket === bucket.id;
                    });
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
                                                    <span className={`text-[10px] font-bold ${stock.change_pct && stock.change_pct >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                                                        {stock.change_pct && stock.change_pct >= 0 ? '+' : ''}{stock.change_pct?.toFixed(2)}%
                                                    </span>
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
