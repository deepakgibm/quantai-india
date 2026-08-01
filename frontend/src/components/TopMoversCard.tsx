import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, RefreshCw, AlertCircle, Wifi, WifiOff, Clock } from 'lucide-react';
import { api } from '../services/api';
import { calculatePriceChange } from '../utils/marketPrice';

interface StockMover {
    symbol: string;
    ltp: number;
    change_pct: number;
    prev_close: number;
    volume: number;
    day_high: number;
    day_low: number;
    segment?: string;
}

interface CacheMetadata {
    cached_at?: string;
    ttl_seconds?: number;
    is_stale?: boolean;
}

interface TopMoversData {
    as_of: string;
    gainers: StockMover[];
    losers: StockMover[];
    source?: string;
    cache_metadata?: CacheMetadata;
    is_market_hours?: boolean;
    error?: string;
    error_code?: string;
    retry_after_seconds?: number;
}

interface TopMoversCardProps {
    onSymbolClick?: (symbol: string) => void;
}

// Data status types for explicit UI states
type DataStatus = 'loading' | 'live' | 'stale' | 'error' | 'market_closed';

const TopMoversCard: React.FC<TopMoversCardProps> = ({ onSymbolClick }) => {
    const [data, setData] = useState<TopMoversData | null>(null);
    const [status, setStatus] = useState<DataStatus>('loading');
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
    const [isRefreshing, setIsRefreshing] = useState(false);

    const fetchTopMovers = async (isForce = false) => {
        setIsRefreshing(true);

        try {
            // Use centralized API service instead of manual relative fetch
            // This ensures API_URL is used correctly (avoiding Nginx proxy issues)
            const result = await api.getGainersLosers(isForce);

            if (!result) {
                throw new Error('Failed to fetch gainers/losers from API');
            }

            // Check for error response from backend
            if (result.error || result.error_code) {
                setStatus('error');
                setErrorMessage(result.error || 'Market data temporarily unavailable');
                setData(null);
                setIsRefreshing(false);
                return;
            }

            // Check if we have valid data
            if (!result.gainers?.length && !result.losers?.length) {
                setStatus('error');
                setErrorMessage('No market data available');
                setData(null);
                setIsRefreshing(false);
                return;
            }

            // Determine data status based on source and metadata
            if (result.source === 'mock' && !result.gainers?.length) {
                // Only reject totally empty mock data
                setStatus('error');
                setErrorMessage('Live market data unavailable');
                setData(null);
                setIsRefreshing(false);
                return;
            }

            // Check for stale data
            if (result.cache_metadata?.is_stale) {
                setStatus('stale');
            } else if (result.is_market_hours === false) {
                setStatus('market_closed');
            } else {
                setStatus('live');
            }

            setData(result);
            setErrorMessage(null);
            setLastRefresh(new Date());

        } catch (error: any) {
            console.error('Top movers fetch failed:', error);

            if (error.name === 'AbortError') {
                setErrorMessage('Request timed out. Please try again.');
            } else {
                setErrorMessage(error.message || 'Failed to fetch market data');
            }

            setStatus('error');
            setData(null);
        } finally {
            setIsRefreshing(false);
        }
    };

    useEffect(() => {
        fetchTopMovers(false);

        // Auto-refresh every 60 seconds
        const interval = setInterval(() => fetchTopMovers(false), 60000);
        return () => clearInterval(interval);
    }, []);

    // Format volume for display
    const formatVolume = (vol: number): string => {
        if (vol >= 10000000) return `${(vol / 10000000).toFixed(1)}Cr`;
        if (vol >= 100000) return `${(vol / 100000).toFixed(1)}L`;
        if (vol >= 1000) return `${(vol / 1000).toFixed(1)}K`;
        return vol.toString();
    };

    const getChangeColor = (change: number): string => {
        if (change >= 0.2) return 'text-green-600 dark:text-green-400';
        if (change <= -0.2) return 'text-red-600 dark:text-red-400';
        return 'text-slate-500 dark:text-slate-400';
    };

    const getChangeBg = (change: number): string => {
        if (change >= 0.2) return 'bg-green-50 dark:bg-green-900/20';
        if (change <= -0.2) return 'bg-red-50 dark:bg-red-900/20';
        return 'bg-slate-50 dark:bg-slate-700/50';
    };

    // Status badge component for transparency
    const StatusBadge: React.FC = () => {
        switch (status) {
            case 'live':
                return (
                    <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400 font-medium">
                        <Wifi size={12} className="animate-pulse" />
                        LIVE
                    </span>
                );
            case 'stale':
                return (
                    <span className="flex items-center gap-1 text-xs text-yellow-600 dark:text-yellow-400 font-medium">
                        <Clock size={12} />
                        DELAYED
                    </span>
                );
            case 'market_closed':
                return (
                    <span className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 font-medium">
                        <WifiOff size={12} />
                        MARKET CLOSED
                    </span>
                );
            case 'error':
                return (
                    <span className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400 font-medium">
                        <AlertCircle size={12} />
                        UNAVAILABLE
                    </span>
                );
            default:
                return null;
        }
    };

    // Data source indicator
    const DataSourceBadge: React.FC = () => {
        if (!data?.source) return null;

        const sourceLabels: Record<string, string> = {
            'dragonfly': 'Cache',
            'cache': 'Cache',
            'upstox': 'Live API',
            'database': 'Historical',
            'yfinance': 'Fallback API'
        };

        return (
            <span className="text-xs text-slate-400 ml-2">
                via {sourceLabels[data.source] || data.source}
            </span>
        );
    };

    const StockRow: React.FC<{ stock: StockMover; isGainer: boolean }> = ({ stock, isGainer }) => {
        const details = calculatePriceChange(stock.ltp, stock.prev_close, stock.change_pct);
        const isUp = details.direction === 'up';
        const isDown = details.direction === 'down';
        
        return (
            <div
                className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all hover:scale-[1.02] ${
                    isUp ? 'bg-green-50 dark:bg-green-900/20' : isDown ? 'bg-red-50 dark:bg-red-900/20' : 'bg-slate-50 dark:bg-slate-700/50'
                }`}
                onClick={() => onSymbolClick?.(stock.symbol)}
                title={`Prev Close: ₹${details.previousClose.toLocaleString()}\nChange: ₹${details.change.toLocaleString()}`}
            >
                <div className="flex items-center gap-3">
                    <div className={`p-1.5 rounded-lg ${isUp ? 'bg-green-100 dark:bg-green-900/30' : isDown ? 'bg-red-100 dark:bg-red-900/30' : 'bg-slate-100 dark:bg-slate-800'}`}>
                        {isUp ? (
                            <TrendingUp size={14} className="text-green-600 dark:text-green-400" />
                        ) : (
                            <TrendingDown size={14} className="text-red-600 dark:text-red-400" />
                        )}
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <p className="font-bold text-sm text-slate-800 dark:text-white">{stock.symbol}</p>
                            {stock.segment && (
                                <span className={`text-[10px] font-bold px-1 rounded ${
                                    stock.segment === 'INDEX' ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300' : 
                                    stock.segment === 'F&O' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300' :
                                    'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                                }`}>
                                    {stock.segment}
                                </span>
                            )}
                        </div>
                        {stock.volume > 0 && (
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                                Vol: {formatVolume(stock.volume)}
                            </p>
                        )}
                    </div>

                </div>
                <div className="text-right">
                    <p className="font-bold text-sm text-slate-800 dark:text-white">
                        ₹{details.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </p>
                    <p className={`text-xs font-semibold ${
                        isUp ? 'text-green-600 dark:text-green-400' : isDown ? 'text-red-600 dark:text-red-400' : 'text-slate-500 dark:text-slate-400'
                    }`}>
                        {isUp ? '▲ +' : isDown ? '▼ ' : '▬ '}{Math.abs(details.changePercent).toFixed(2)}%
                    </p>
                </div>
            </div>
        );
    };

    // Loading state with explicit message
    if (status === 'loading' && !data) {
        return (
            <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
                <div className="flex flex-col items-center justify-center h-48 gap-3">
                    <RefreshCw size={24} className="animate-spin text-brand-500" />
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                        Fetching live market segments...
                    </p>
                </div>
            </div>
        );
    }

    // Error state with transparent message
    if (status === 'error' && !data) {
        return (
            <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="font-bold text-slate-800 dark:text-white">
                        Market Movers - All Segments
                    </h3>
                    <StatusBadge />
                </div>
                <div className="flex flex-col items-center justify-center h-40 gap-3">
                    <AlertCircle size={32} className="text-red-400" />
                    <p className="text-sm text-center text-slate-600 dark:text-slate-400">
                        {errorMessage || 'Market data temporarily unavailable'}
                    </p>
                    <button
                        onClick={fetchTopMovers}
                        disabled={isRefreshing}
                        className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
                    >
                        {isRefreshing ? 'Retrying...' : 'Try Again'}
                    </button>
                </div>
            </div>
        );
    }

    // Debug table logs before rendering (Step 7)
    const allStocks = data ? [...(data.gainers || []), ...(data.losers || [])] : [];
    if (allStocks.length > 0) {
        console.table(
            allStocks.map(x => ({
                symbol: x.symbol,
                ltp: x.ltp,
                prevClose: x.prev_close,
                change: x.ltp - x.prev_close,
                changePercent: x.change_pct
            }))
        );
    }

    return (
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
            {/* Header with status */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <h3 className="font-bold text-slate-800 dark:text-white">
                        Market Movers - All Segments
                    </h3>
                    <DataSourceBadge />
                </div>
                <div className="flex items-center gap-3">
                    <StatusBadge />
                    {lastRefresh && (
                        <span className="text-xs text-slate-400">
                            {lastRefresh.toLocaleTimeString()}
                        </span>
                    )}
                    <button
                        onClick={() => fetchTopMovers(true)}
                        disabled={isRefreshing}
                        className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50"
                        title="Refresh"
                    >
                        <RefreshCw size={14} className={`text-slate-400 ${isRefreshing ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </div>

            {/* Split Layout */}
            <div className="grid grid-cols-2 gap-4">
                {/* Gainers Column */}
                <div>
                    <div className="flex items-center gap-2 mb-3">
                        <div className="w-2 h-2 rounded-full bg-green-500"></div>
                        <span className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                            Top Gainers
                        </span>
                    </div>
                    <div className="space-y-2">
                        {data?.gainers && data.gainers.length > 0 ? (
                            data.gainers.map((stock) => (
                                <StockRow key={stock.symbol} stock={stock} isGainer={true} />
                            ))
                        ) : (
                            <p className="text-sm text-slate-400 text-center py-4">No gainers data</p>
                        )}
                    </div>
                </div>

                {/* Losers Column */}
                <div>
                    <div className="flex items-center gap-2 mb-3">
                        <div className="w-2 h-2 rounded-full bg-red-500"></div>
                        <span className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                            Top Losers
                        </span>
                    </div>
                    <div className="space-y-2">
                        {data?.losers && data.losers.length > 0 ? (
                            data.losers.map((stock) => (
                                <StockRow key={stock.symbol} stock={stock} isGainer={false} />
                            ))
                        ) : (
                            <p className="text-sm text-slate-400 text-center py-4">No losers data</p>
                        )}
                    </div>
                </div>
            </div>

            {/* Cache metadata footer (for transparency) */}
            {data?.cache_metadata?.cached_at && (
                <p className="text-xs text-slate-400 mt-3 text-center">
                    Data cached at {new Date(data.cache_metadata.cached_at).toLocaleTimeString()}
                    {data.cache_metadata.ttl_seconds && ` • Refreshes in ${data.cache_metadata.ttl_seconds}s`}
                </p>
            )}
        </div>
    );
};

export default TopMoversCard;
