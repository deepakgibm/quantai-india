import React, { useEffect, useState } from 'react';
import { RefreshCw, AlertCircle, Clock } from 'lucide-react';

interface MarketStatus {
    status: string;
    is_open: boolean;
    trading_date: string;
    current_time: string;
    last_updated: string;
    next_event: string;
    data_source: string;
    message?: string;
}

export const MarketStatusBanner: React.FC = () => {
    const [status, setStatus] = useState<MarketStatus | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchStatus = async () => {
        try {
            const res = await fetch('/api/v1/market/status');
            if (!res.ok) throw new Error('Failed to fetch market status');
            const data = await res.json();
            setStatus(data);
            setError(null);
        } catch (err: any) {
            setError(err.message);
        }
    };

    const handleRefresh = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/v1/market/refresh', { method: 'POST' });
            if (!res.ok) throw new Error('Failed to refresh market data');
            const data = await res.json();
            setStatus(data);
            setError(null);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 60000); // Poll every minute
        return () => clearInterval(interval);
    }, []);

    if (!status) return null;

    const isMarketOpen = status.is_open;
    const isHoliday = status.status === 'HOLIDAY';
    const isWeekend = status.status === 'WEEKEND';

    let statusColor = 'bg-slate-100 text-slate-800 border-slate-200';
    let statusDot = 'bg-slate-400';
    
    if (isMarketOpen) {
        statusColor = 'bg-emerald-50 border-emerald-200 text-emerald-800';
        statusDot = 'bg-emerald-500 animate-pulse';
    } else if (isHoliday || isWeekend) {
        statusColor = 'bg-rose-50 border-rose-200 text-rose-800';
        statusDot = 'bg-rose-500';
    } else {
        // Pre/Post market
        statusColor = 'bg-amber-50 border-amber-200 text-amber-800';
        statusDot = 'bg-amber-500';
    }

    return (
        <div className={`w-full border-b px-4 py-2 flex items-center justify-between text-xs font-medium transition-colors ${statusColor}`}>
            <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                    <div className={`w-2.5 h-2.5 rounded-full ${statusDot}`} />
                    <span className="font-bold uppercase tracking-wider">
                        {isMarketOpen ? 'Market Open' : status.status === 'PRE_MARKET' ? 'Pre-Market' : status.status === 'CLOSED' ? 'Market Closed' : status.status}
                    </span>
                </div>
                
                <div className="hidden sm:flex items-center gap-3 text-slate-600">
                    <span className="flex items-center gap-1">
                        <Clock size={12} />
                        {status.current_time}
                    </span>
                    <span className="opacity-40">|</span>
                    <span>Trading Day: <strong>{status.trading_date}</strong></span>
                    <span className="opacity-40">|</span>
                    <span className="truncate max-w-[200px]">{status.next_event}</span>
                </div>
            </div>

            <div className="flex items-center gap-3">
                <div className="hidden md:flex flex-col items-end mr-2">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wide">Data Source</span>
                    <span className="font-semibold text-slate-700">{status.data_source || 'Verified Snapshot'}</span>
                </div>
                
                {error && (
                    <span className="flex items-center gap-1 text-rose-600" title={error}>
                        <AlertCircle size={14} />
                    </span>
                )}
                
                <button
                    onClick={handleRefresh}
                    disabled={loading}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-300 rounded-md shadow-sm hover:bg-slate-50 disabled:opacity-50 transition-all text-slate-700"
                >
                    <RefreshCw size={14} className={loading ? 'animate-spin text-indigo-600' : ''} />
                    <span>{loading ? 'Refreshing...' : 'Refresh Data'}</span>
                </button>
            </div>
        </div>
    );
};
