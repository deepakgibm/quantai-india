import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';

interface StockMover {
    symbol: string;
    ltp: number;
    change_pct: number;
    prev_close: number;
    volume: number;
    day_high: number;
    day_low: number;
}

interface TopMoversData {
    as_of: string;
    gainers: StockMover[];
    losers: StockMover[];
    error?: string;
}

interface TopMoversCardProps {
    onSymbolClick?: (symbol: string) => void;
}

const TopMoversCard: React.FC<TopMoversCardProps> = ({ onSymbolClick }) => {
    const [data, setData] = useState<TopMoversData | null>(null);
    const [loading, setLoading] = useState(true);
    const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

    const fetchTopMovers = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/market/nifty100/top-movers');
            if (response.ok) {
                const result = await response.json();
                setData(result);
                setLastRefresh(new Date());
            }
        } catch (error) {
            console.error('Failed to fetch top movers:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTopMovers();

        // Auto-refresh every 60 seconds
        const interval = setInterval(fetchTopMovers, 60000);
        return () => clearInterval(interval);
    }, []);

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

    const StockRow: React.FC<{ stock: StockMover; isGainer: boolean }> = ({ stock, isGainer }) => (
        <div
            className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all hover:scale-[1.02] ${getChangeBg(stock.change_pct)}`}
            onClick={() => onSymbolClick?.(stock.symbol)}
            title={`Prev Close: ₹${stock.prev_close.toLocaleString()}\nDay High: ₹${stock.day_high.toLocaleString()}\nDay Low: ₹${stock.day_low.toLocaleString()}`}
        >
            <div className="flex items-center gap-3">
                <div className={`p-1.5 rounded-lg ${isGainer ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
                    {isGainer ? (
                        <TrendingUp size={14} className="text-green-600 dark:text-green-400" />
                    ) : (
                        <TrendingDown size={14} className="text-red-600 dark:text-red-400" />
                    )}
                </div>
                <div>
                    <p className="font-bold text-sm text-slate-800 dark:text-white">{stock.symbol}</p>
                    {stock.volume > 0 && (
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                            Vol: {formatVolume(stock.volume)}
                        </p>
                    )}
                </div>

            </div>
            <div className="text-right">
                <p className="font-bold text-sm text-slate-800 dark:text-white">
                    ₹{stock.ltp.toLocaleString()}
                </p>
                <p className={`text-xs font-semibold ${getChangeColor(stock.change_pct)}`}>
                    {stock.change_pct >= 0 ? '+' : ''}{stock.change_pct.toFixed(2)}%
                </p>
            </div>
        </div>
    );

    if (loading && !data) {
        return (
            <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
                <div className="flex items-center justify-center h-48">
                    <RefreshCw size={24} className="animate-spin text-slate-400" />
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-slate-800 dark:text-white">
                    NIFTY 100 - Top Gainers & Losers
                </h3>
                <div className="flex items-center gap-2">
                    {lastRefresh && (
                        <span className="text-xs text-slate-400">
                            {lastRefresh.toLocaleTimeString()}
                        </span>
                    )}
                    <button
                        onClick={fetchTopMovers}
                        className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                        title="Refresh"
                    >
                        <RefreshCw size={14} className={`text-slate-400 ${loading ? 'animate-spin' : ''}`} />
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
                            <p className="text-sm text-slate-400 text-center py-4">No data available</p>
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
                            <p className="text-sm text-slate-400 text-center py-4">No data available</p>
                        )}
                    </div>
                </div>
            </div>

            {/* Error state */}
            {data?.error && (
                <p className="text-xs text-red-500 mt-3 text-center">
                    Error: {data.error}
                </p>
            )}
        </div>
    );
};

export default TopMoversCard;
