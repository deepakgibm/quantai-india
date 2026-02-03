import React, { useState, useEffect, useMemo } from 'react';
import {
    Zap,
    TrendingUp,
    TrendingDown,
    Activity,
    RefreshCw,
    Target,
    BarChart3,
    ArrowUpCircle,
    ArrowDownCircle,
    ArrowRight,
    Search,
    ArrowUpDown,
    ChevronUp,
    ChevronDown
} from 'lucide-react';
import { API_URL, getAuthHeaders } from '../services/api';
import { PriceWithSource } from '../components/PriceSourceBadge';

interface Week52BreakoutStock {
    symbol: string;
    ltp: number;
    high_52w: number;
    low_52w: number;
    change_pct: number;
    breakout_type: string; // "Breakout", "Yearly High", "Yearly Low"
    breakout_pct: number;
    volume_ratio: number;
    volume_strength: string;
    industry: string;
    timestamp: string;
}

type SortField = 'symbol' | 'ltp' | 'change_pct' | 'breakout_pct' | 'volume_ratio' | 'breakout_type';
type SortOrder = 'asc' | 'desc';

const Week52Breakout: React.FC = () => {
    const [highBreakouts, setHighBreakouts] = useState<Week52BreakoutStock[]>([]);
    const [lowBreakdowns, setLowBreakdowns] = useState<Week52BreakoutStock[]>([]);
    const [loading, setLoading] = useState(true);
    const [lastRefresh, setLastRefresh] = useState<string>('');

    // Search state
    const [searchQuery, setSearchQuery] = useState<string>('');

    // Sorting state for high breakouts
    const [highSortField, setHighSortField] = useState<SortField>('breakout_pct');
    const [highSortOrder, setHighSortOrder] = useState<SortOrder>('desc');

    // Sorting state for low breakdowns
    const [lowSortField, setLowSortField] = useState<SortField>('breakout_pct');
    const [lowSortOrder, setLowSortOrder] = useState<SortOrder>('desc');

    const fetchBreakouts = async (forceRefresh: boolean = true) => {
        try {
            setLoading(true);
            const url = `${API_URL}/api/scanner/week52-breakouts${forceRefresh ? '?force_refresh=true' : ''}`;
            const response = await fetch(url, {
                headers: getAuthHeaders()
            });
            if (response.ok) {
                const data = await response.json();

                // Extra safety: Filter out any rows with missing critical data
                const highs = Array.isArray(data.high_breakouts) ? data.high_breakouts : [];
                const lows = Array.isArray(data.low_breakdowns) ? data.low_breakdowns : [];

                const validHighs = highs.filter((s: Week52BreakoutStock) =>
                    s.symbol && s.industry && s.industry !== 'N/A'
                );
                const validLows = lows.filter((s: Week52BreakoutStock) =>
                    s.symbol && s.industry && s.industry !== 'N/A'
                );

                setHighBreakouts(validHighs);
                setLowBreakdowns(validLows);
                setLastRefresh(new Date().toLocaleTimeString());
            }
        } catch (error) {
            console.error('Error fetching 52-week breakouts:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchBreakouts();
        // Removed auto-polling to ensure refresh is user-triggered only
    }, []);

    // Sort function
    const sortStocks = (stocks: Week52BreakoutStock[], field: SortField, order: SortOrder) => {
        return [...stocks].sort((a, b) => {
            let aVal: any = a[field];
            let bVal: any = b[field];

            // Handle string comparison for symbol
            if (field === 'symbol') {
                aVal = aVal.toLowerCase();
                bVal = bVal.toLowerCase();
                return order === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }

            // Numeric comparison
            return order === 'asc' ? aVal - bVal : bVal - aVal;
        });
    };

    // Filter and sort high breakouts
    const filteredHighBreakouts = useMemo(() => {
        let filtered = highBreakouts;
        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase();
            filtered = highBreakouts.filter(stock =>
                stock.symbol.toLowerCase().includes(query) ||
                stock.industry.toLowerCase().includes(query)
            );
        }
        return sortStocks(filtered, highSortField, highSortOrder);
    }, [highBreakouts, searchQuery, highSortField, highSortOrder]);

    // Filter and sort low breakdowns
    const filteredLowBreakdowns = useMemo(() => {
        let filtered = lowBreakdowns;
        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase();
            filtered = lowBreakdowns.filter(stock =>
                stock.symbol.toLowerCase().includes(query) ||
                stock.industry.toLowerCase().includes(query)
            );
        }
        return sortStocks(filtered, lowSortField, lowSortOrder);
    }, [lowBreakdowns, searchQuery, lowSortField, lowSortOrder]);

    // Toggle sort handler
    const toggleSort = (
        field: SortField,
        currentField: SortField,
        currentOrder: SortOrder,
        setField: (f: SortField) => void,
        setOrder: (o: SortOrder) => void
    ) => {
        if (field === currentField) {
            setOrder(currentOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setField(field);
            setOrder('desc');
        }
    };

    // Sort button component
    const SortButton: React.FC<{
        label: string;
        field: SortField;
        currentField: SortField;
        currentOrder: SortOrder;
        onSort: (field: SortField) => void;
        color: string;
    }> = ({ label, field, currentField, currentOrder, onSort, color }) => {
        const isActive = field === currentField;
        return (
            <button
                onClick={() => onSort(field)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${isActive
                    ? `bg-${color}-500/20 text-${color}-600 dark:text-${color}-400 border border-${color}-500/30`
                    : 'bg-slate-100 dark:bg-slate-700/50 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                    }`}
            >
                {label}
                {isActive ? (
                    currentOrder === 'desc' ? <ChevronDown size={14} /> : <ChevronUp size={14} />
                ) : (
                    <ArrowUpDown size={12} className="opacity-50" />
                )}
            </button>
        );
    };

    return (
        <div className="flex flex-col h-full gap-8 p-2 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {/* Header section */}
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200/60 dark:border-slate-700/60 rounded-[40px] p-8 shadow-xl shadow-slate-200/30 dark:shadow-none">
                <div className="flex items-center gap-6">
                    <div className="p-4 bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 rounded-[28px] shadow-xl shadow-indigo-500/20 rotate-3">
                        <Target size={32} className="text-white" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-black text-slate-900 dark:text-white tracking-tight leading-none mb-2">52-Week Breakout</h1>
                        <p className="text-xs font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-2">
                            Analysis of stocks making yearly milestones
                            {lastRefresh && (
                                <span className="text-slate-400 font-medium normal-case tracking-normal ml-2">
                                    • Last updated {lastRefresh}
                                </span>
                            )}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {/* Search Input */}
                    <div className="relative">
                        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search stocks..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-11 pr-4 py-3 w-64 bg-slate-100 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600 rounded-2xl text-sm font-medium text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
                        />
                        {searchQuery && (
                            <button
                                onClick={() => setSearchQuery('')}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                            >
                                ✕
                            </button>
                        )}
                    </div>

                    <button
                        onClick={fetchBreakouts}
                        disabled={loading}
                        className="flex items-center gap-2 px-6 py-3 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl font-black text-sm hover:scale-105 transition-all shadow-lg active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                    >
                        <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                        {loading ? 'Refreshing...' : 'Refresh'}
                    </button>
                </div>
            </header>

            {/* Search Results Info */}
            {searchQuery && (
                <div className="flex items-center gap-2 px-4 py-2 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-2xl">
                    <Search size={16} className="text-indigo-500" />
                    <span className="text-sm font-medium text-indigo-700 dark:text-indigo-300">
                        Showing results for "{searchQuery}" —
                        <span className="font-bold"> {filteredHighBreakouts.length} highs</span> and
                        <span className="font-bold"> {filteredLowBreakdowns.length} lows</span> found
                    </span>
                </div>
            )}

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* 52-Week High Breakouts */}
                <section className="flex flex-col gap-6">
                    <div className="flex flex-col gap-4">
                        <div className="flex items-center justify-between px-4">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-emerald-500 text-white rounded-xl">
                                    <ArrowUpCircle size={20} />
                                </div>
                                <h2 className="text-xl font-black text-slate-900 dark:text-white uppercase tracking-tight">Yearly Highs</h2>
                            </div>
                            <span className="px-4 py-1.5 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-sm font-black rounded-full border border-emerald-500/20">
                                {filteredHighBreakouts.length} STOCKS
                            </span>
                        </div>

                        {/* Sort Controls for Highs */}
                        <div className="flex items-center gap-2 px-4 flex-wrap">
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Sort by:</span>
                            <SortButton
                                label="Symbol"
                                field="symbol"
                                currentField={highSortField}
                                currentOrder={highSortOrder}
                                onSort={(f) => toggleSort(f, highSortField, highSortOrder, setHighSortField, setHighSortOrder)}
                                color="emerald"
                            />
                            <SortButton
                                label="Price"
                                field="ltp"
                                currentField={highSortField}
                                currentOrder={highSortOrder}
                                onSort={(f) => toggleSort(f, highSortField, highSortOrder, setHighSortField, setHighSortOrder)}
                                color="emerald"
                            />
                            <SortButton
                                label="Change %"
                                field="change_pct"
                                currentField={highSortField}
                                currentOrder={highSortOrder}
                                onSort={(f) => toggleSort(f, highSortField, highSortOrder, setHighSortField, setHighSortOrder)}
                                color="emerald"
                            />
                            <SortButton
                                label="Breakout %"
                                field="breakout_pct"
                                currentField={highSortField}
                                currentOrder={highSortOrder}
                                onSort={(f) => toggleSort(f, highSortField, highSortOrder, setHighSortField, setHighSortOrder)}
                                color="emerald"
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 gap-4 max-h-[600px] overflow-y-auto pr-2">
                        {loading && highBreakouts.length === 0 ? (
                            Array(3).fill(0).map((_, i) => (
                                <div key={i} className="h-32 bg-slate-200/50 dark:bg-slate-700/50 animate-pulse rounded-[32px]" />
                            ))
                        ) : filteredHighBreakouts.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-20 bg-white/40 dark:bg-slate-800/40 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-[40px] opacity-50">
                                <TrendingUp size={48} className="text-slate-400 mb-4" />
                                <span className="font-bold text-slate-500">
                                    {searchQuery ? 'No matching stocks found' : 'No high breakouts detected'}
                                </span>
                            </div>
                        ) : (
                            filteredHighBreakouts.map((stock) => (
                                <div key={stock.symbol} className="group relative bg-white dark:bg-slate-800/80 backdrop-blur-md border border-slate-200/60 dark:border-slate-700/60 rounded-[32px] p-6 transition-all hover:shadow-2xl hover:shadow-emerald-500/10 hover:-translate-y-1">
                                    <div className="flex justify-between items-start mb-6">
                                        <div>
                                            <div className="flex items-center gap-2 mb-1">
                                                <h3 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight uppercase group-hover:text-emerald-500 transition-colors">
                                                    {stock.symbol}
                                                </h3>
                                                <span className={`px-2 py-0.5 rounded-lg text-[10px] font-black uppercase tracking-wider ${stock.breakout_type === 'Breakout'
                                                    ? 'bg-indigo-500 text-white'
                                                    : 'bg-emerald-500/10 text-emerald-600'
                                                    }`}>
                                                    {stock.breakout_type}
                                                </span>
                                            </div>
                                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                                {stock.industry}
                                            </p>
                                        </div>
                                        <div className="text-right">
                                            <PriceWithSource
                                                price={stock.ltp}
                                                source={(stock as any).price_source}
                                                className="justify-end text-xl"
                                            />
                                            <div className={`text-sm font-black ${stock.change_pct >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                                                {stock.change_pct >= 0 ? '↑' : '↓'} {Math.abs(stock.change_pct).toFixed(2)}%
                                            </div>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-3 gap-6">
                                        <div className="p-4 bg-emerald-500/5 rounded-2xl border border-emerald-500/10">
                                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest block mb-1">52W High</span>
                                            <span className="text-sm font-black text-emerald-600 dark:text-emerald-400 leading-none">
                                                ₹{stock.high_52w.toLocaleString()}
                                            </span>
                                        </div>
                                        <div className="p-4 bg-blue-500/5 rounded-2xl border border-blue-500/10">
                                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest block mb-1">Breakout %</span>
                                            <span className="text-sm font-black text-blue-600 dark:text-blue-400 leading-none">
                                                {stock.breakout_pct > 0 ? '+' : ''}{stock.breakout_pct.toFixed(2)}%
                                            </span>
                                        </div>
                                        <div className="p-4 bg-purple-500/5 rounded-2xl border border-purple-500/10">
                                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest block mb-1">Vol Ratio</span>
                                            <span className="text-sm font-black text-purple-600 dark:text-purple-400 leading-none">
                                                {stock.volume_ratio.toFixed(2)}x
                                            </span>
                                        </div>
                                    </div>

                                    <div className="mt-6 pt-6 border-t border-slate-100 dark:border-slate-700/50 flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <div className={`w-2 h-2 rounded-full animate-pulse ${stock.volume_strength === 'Strong' ? 'bg-emerald-500' :
                                                stock.volume_strength === 'Normal' ? 'bg-blue-500' : 'bg-slate-400'
                                                }`} />
                                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                                                {stock.volume_strength} Volume Support
                                            </span>
                                        </div>
                                        <button className="text-slate-400 hover:text-emerald-500 transition-colors">
                                            <ArrowRight size={20} />
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </section>

                {/* 52-Week Low Breakdowns */}
                <section className="flex flex-col gap-6">
                    <div className="flex flex-col gap-4">
                        <div className="flex items-center justify-between px-4">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-rose-500 text-white rounded-xl">
                                    <ArrowDownCircle size={20} />
                                </div>
                                <h2 className="text-xl font-black text-slate-900 dark:text-white uppercase tracking-tight">Yearly Lows</h2>
                            </div>
                            <span className="px-4 py-1.5 bg-rose-500/10 text-rose-600 dark:text-rose-400 text-sm font-black rounded-full border border-rose-500/20">
                                {filteredLowBreakdowns.length} STOCKS
                            </span>
                        </div>

                        {/* Sort Controls for Lows */}
                        <div className="flex items-center gap-2 px-4 flex-wrap">
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Sort by:</span>
                            <SortButton
                                label="Symbol"
                                field="symbol"
                                currentField={lowSortField}
                                currentOrder={lowSortOrder}
                                onSort={(f) => toggleSort(f, lowSortField, lowSortOrder, setLowSortField, setLowSortOrder)}
                                color="rose"
                            />
                            <SortButton
                                label="Price"
                                field="ltp"
                                currentField={lowSortField}
                                currentOrder={lowSortOrder}
                                onSort={(f) => toggleSort(f, lowSortField, lowSortOrder, setLowSortField, setLowSortOrder)}
                                color="rose"
                            />
                            <SortButton
                                label="Change %"
                                field="change_pct"
                                currentField={lowSortField}
                                currentOrder={lowSortOrder}
                                onSort={(f) => toggleSort(f, lowSortField, lowSortOrder, setLowSortField, setLowSortOrder)}
                                color="rose"
                            />
                            <SortButton
                                label="Breakdown %"
                                field="breakout_pct"
                                currentField={lowSortField}
                                currentOrder={lowSortOrder}
                                onSort={(f) => toggleSort(f, lowSortField, lowSortOrder, setLowSortField, setLowSortOrder)}
                                color="rose"
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 gap-4 max-h-[600px] overflow-y-auto pr-2">
                        {loading && lowBreakdowns.length === 0 ? (
                            Array(3).fill(0).map((_, i) => (
                                <div key={i} className="h-32 bg-slate-200/50 dark:bg-slate-700/50 animate-pulse rounded-[32px]" />
                            ))
                        ) : filteredLowBreakdowns.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-20 bg-white/40 dark:bg-slate-800/40 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-[40px] opacity-50">
                                <TrendingDown size={48} className="text-slate-400 mb-4" />
                                <span className="font-bold text-slate-500">
                                    {searchQuery ? 'No matching stocks found' : 'No low breakdowns detected'}
                                </span>
                            </div>
                        ) : (
                            filteredLowBreakdowns.map((stock) => (
                                <div key={stock.symbol} className="group relative bg-white dark:bg-slate-800/80 backdrop-blur-md border border-slate-200/60 dark:border-slate-700/60 rounded-[32px] p-6 transition-all hover:shadow-2xl hover:shadow-rose-500/10 hover:-translate-y-1">
                                    <div className="flex justify-between items-start mb-6">
                                        <div>
                                            <div className="flex items-center gap-2 mb-1">
                                                <h3 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight uppercase group-hover:text-rose-500 transition-colors">
                                                    {stock.symbol}
                                                </h3>
                                                <span className="px-2 py-0.5 bg-rose-500/10 text-rose-600 rounded-lg text-[10px] font-black uppercase tracking-wider">
                                                    {stock.breakout_type}
                                                </span>
                                            </div>
                                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                                {stock.industry}
                                            </p>
                                        </div>
                                        <div className="text-right">
                                            <div className="text-2xl font-black text-slate-900 dark:text-white">
                                                ₹{stock.ltp.toLocaleString()}
                                            </div>
                                            <div className={`text-sm font-black ${stock.change_pct >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                                                {stock.change_pct >= 0 ? '↑' : '↓'} {Math.abs(stock.change_pct).toFixed(2)}%
                                            </div>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-3 gap-6">
                                        <div className="p-4 bg-rose-500/5 rounded-2xl border border-rose-500/10">
                                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest block mb-1">52W Low</span>
                                            <span className="text-sm font-black text-rose-600 dark:text-rose-400 leading-none">
                                                ₹{stock.low_52w.toLocaleString()}
                                            </span>
                                        </div>
                                        <div className="p-4 bg-orange-500/5 rounded-2xl border border-orange-500/10">
                                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest block mb-1">Gap to Low %</span>
                                            <span className="text-sm font-black text-orange-600 dark:text-orange-400 leading-none">
                                                {stock.breakout_pct > 0 ? '+' : ''}{stock.breakout_pct.toFixed(2)}%
                                            </span>
                                        </div>
                                        <div className="p-4 bg-purple-500/5 rounded-2xl border border-purple-500/10">
                                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest block mb-1">Vol Ratio</span>
                                            <span className="text-sm font-black text-purple-600 dark:text-purple-400 leading-none">
                                                {stock.volume_ratio.toFixed(2)}x
                                            </span>
                                        </div>
                                    </div>

                                    <div className="mt-6 pt-6 border-t border-slate-100 dark:border-slate-700/50 flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <div className={`w-2 h-2 rounded-full animate-pulse ${stock.volume_ratio >= 1.5 ? 'bg-rose-500' : 'bg-slate-400'
                                                }`} />
                                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                                                {stock.volume_ratio >= 1.5 ? 'Heavy Selling Pressure' : 'Normal Volume'}
                                            </span>
                                        </div>
                                        <button className="text-slate-400 hover:text-rose-500 transition-colors">
                                            <ArrowRight size={20} />
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </section>
            </div>
        </div>
    );
};

export default Week52Breakout;
