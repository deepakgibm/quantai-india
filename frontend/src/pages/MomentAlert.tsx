import React, { useState, useEffect, useRef, useMemo } from 'react';
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
import { getAuthHeaders, API_URL } from '../services/api';
import { isMarketOpen } from '../utils/marketHours';

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

    // Check market hours
    const checkMarketStatus = () => {
        // We import dynamically or assuming valid import exists from top level
        // For now, let's implement validation logic here or rely on the imported util
        // We need to import it at the top of the file
        return isMarketOpen();
    };

    const wsReconnectTimeout = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        const initializeConnection = () => {
            const marketOpen = checkMarketStatus();
            if (marketOpen) {
                connectWS();
            } else {
                console.log("Market closed. Using REST polling.");
                startRestPolling();
            }
        };

        initializeConnection();
        fetchWeek52Breakouts();

        // Refresh 52-week data every 5 minutes
        const week52Interval = setInterval(fetchWeek52Breakouts, 300000);

        return () => {
            cleanupConnections();
            clearInterval(week52Interval);
        };
    }, []);

    const cleanupConnections = () => {
        if (ws.current) {
            ws.current.onclose = null; // Prevent reconnect loop during intentional close
            ws.current.close();
            ws.current = null;
        }
        if (pollInterval.current) {
            clearInterval(pollInterval.current);
            pollInterval.current = null;
        }
        if (wsReconnectTimeout.current) {
            clearTimeout(wsReconnectTimeout.current);
            wsReconnectTimeout.current = null;
        }
        setIsConnected(false);
    };

    const fetchWeek52Breakouts = async (forceRefresh: boolean = false) => {
        try {
            setWeek52Loading(true);
            const url = `${API_URL}/api/scanner/week52-breakouts${forceRefresh ? '?force_refresh=true' : ''}`;
            const response = await fetch(url, {
                headers: getAuthHeaders()
            });
            if (response.ok) {
                const data = await response.json();
                setHighBreakouts(Array.isArray(data.high_breakouts) ? data.high_breakouts : []);
                setLowBreakdowns(Array.isArray(data.low_breakdowns) ? data.low_breakdowns : []);
            }
        } catch (error) {
            console.error('Error fetching 52-week breakouts:', error);
        } finally {
            setWeek52Loading(false);
        }
    };

    const handleDataUpdate = (message: any) => {
        if (message.type === 'bucket_update' && Array.isArray(message.data)) {
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
        // Clear any existing connections or timeouts first
        cleanupConnections();

        if (!checkMarketStatus()) {
            console.log("Market closed during connect attempt. Switching to REST.");
            startRestPolling();
            return;
        }

        setConnectionMode('WS');
        const wsUrl = `${API_URL.replace('http', 'ws')}/api/scanner/ws`;
        console.log(`Connecting to Market WS: ${wsUrl}`);
        
        try {
            const socket = new WebSocket(wsUrl);
            ws.current = socket;

            socket.onopen = () => {
                setIsConnected(true);
                wsRetryCount.current = 0;
                console.log('Market WS Connected');
            };

            socket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    handleDataUpdate(message);
                } catch (e) {
                    console.error('Error parsing WS message:', e);
                }
            };

            socket.onerror = (error) => {
                console.warn('Market WS Error:', error);
            };

            socket.onclose = (event) => {
                ws.current = null;
                setIsConnected(false);
                
                if (event.wasClean) {
                    console.log('Market WS Closed Cleanly');
                    return;
                }

                wsRetryCount.current += 1;
                if (wsRetryCount.current <= maxWsRetries) {
                    const delay = Math.min(1000 * Math.pow(2, wsRetryCount.current), 10000);
                    console.log(`Market WS Closed. Scheduling reconnect in ${delay}ms (Attempt ${wsRetryCount.current}/${maxWsRetries})`);
                    wsReconnectTimeout.current = setTimeout(connectWS, delay);
                } else {
                    console.log('Max WebSocket retries reached, switching to REST polling');
                    startRestPolling();
                }
            };
        } catch (e) {
            console.error('Failed to create WebSocket:', e);
            startRestPolling();
        }
    };

    const startRestPolling = () => {
        // Ensure no WS is running
        if (ws.current) {
            ws.current.onclose = null;
            ws.current.close();
            ws.current = null;
        }
        if (wsReconnectTimeout.current) {
            clearTimeout(wsReconnectTimeout.current);
            wsReconnectTimeout.current = null;
        }

        if (pollInterval.current) return; // Already polling

        setConnectionMode('REST');
        setIsConnected(true);
        console.log('Starting REST polling mode');

        fetchMomentumData();
        pollInterval.current = setInterval(fetchMomentumData, 5000);
    };

    const fetchMomentumData = async (forceRefresh: boolean = false) => {
        try {
            const url = `${API_URL}/api/scanner/momentum${forceRefresh ? '?force_refresh=true' : ''}`;
            const response = await fetch(url, {
                headers: getAuthHeaders()
            });
            if (response.ok) {
                const message = await response.json();
                handleDataUpdate(message);
            }
        } catch (error) {
            console.error('REST polling error:', error);
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
            await Promise.all([
                fetchMomentumData(true),
                fetchWeek52Breakouts(true)
            ]);
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
                                {isConnected ? `Connected (${connectionMode})` : 'Disconnected'}
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
