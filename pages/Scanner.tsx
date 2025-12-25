import React, { useState, useEffect } from 'react';
import {
    Search,
    Play,
    RefreshCw,
    Download,
    TrendingUp,
    TrendingDown,
    Filter,
    ChevronDown,
    ChevronUp,
    Eye,
    Save,
    Check,
    Zap,
    BarChart2,
    Clock,
    Target,
    Layers,
    Activity,
    Info,
    X,
    BookOpen,
    ShieldCheck,
    Cpu,
    ZapOff
} from 'lucide-react';
import { api } from '../services/api';

interface Strategy {
    name: string;
    description: string;
    tier: string;
    min_bars: number;
}

interface ScanResult {
    symbol: string;
    index: string;
    timeframe: string;
    strategy: string;
    signal: 'Bullish' | 'Bearish' | 'Neutral';
    confidence_score: number;
    indicators: Record<string, number>;
    trend: string;
    support: number | null;
    resistance: number | null;
    volume_ratio: number;
    timestamp: string;
    // Derivatives & Decision fields
    pcr: number | 'N/A';
    oi_change: 'Long Buildup' | 'Short Buildup' | 'Short Covering' | 'Long Unwinding' | 'N/A';
    sentiment: 'Bullish' | 'Bearish' | 'Neutral' | 'N/A';
    market_interpretation: string;
    final_signal: 'Buy' | 'Sell' | 'Hold';
    signal_strength: 'Strong' | 'Moderate' | 'Weak';
    adjusted_confidence: number;
    has_derivatives: boolean;
}

const Scanner: React.FC = () => {
    // Configuration state
    const [selectedIndices, setSelectedIndices] = useState<string[]>(['NIFTY 50']);
    const [selectedTimeframe, setSelectedTimeframe] = useState('15m');
    const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);
    const [strategySearch, setStrategySearch] = useState('');
    const [debouncedSearch, setDebouncedSearch] = useState('');
    const [isHelpOpen, setIsHelpOpen] = useState(false);

    // Data state
    const [strategies, setStrategies] = useState<Record<string, Strategy[]>>({});
    const [results, setResults] = useState<ScanResult[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isStrategiesLoading, setIsStrategiesLoading] = useState(true);
    const [strategyError, setStrategyError] = useState<string | null>(null);

    // Sort & Filter state
    const [sortBy, setSortBy] = useState<'confidence_score' | 'symbol'>('confidence_score');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const [resultFilter, setResultFilter] = useState<'all' | 'buy' | 'sell'>('all');

    // Debounce strategy search (300ms delay)
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(strategySearch);
        }, 300);
        return () => clearTimeout(timer);
    }, [strategySearch]);

    const indices = ['NIFTY 50', 'NIFTY 100', 'NIFTY 200', 'NIFTY 500'];
    const timeframes = [
        { value: '3m', label: '3M' },
        { value: '5m', label: '5M' },
        { value: '15m', label: '15M' },
        { value: '30m', label: '30M' },
        { value: '60m', label: '1H' },
        { value: '1d', label: '1D' }
    ];

    useEffect(() => {
        fetchStrategies();
    }, []);

    const fetchStrategies = async () => {
        setIsStrategiesLoading(true);
        setStrategyError(null);
        try {
            const data = await api.getStrategies();
            if (data && data.strategies) {
                setStrategies(data.strategies);
                const tier1 = data.strategies['Tier 1 - Highest Win Rate'] || [];
                const tier2 = data.strategies['Tier 2 - Solid Strategies'] || [];
                const autoSelected = [...tier1, ...tier2].map((s: Strategy) => s.name);
                setSelectedStrategies(autoSelected);
            } else {
                setStrategyError("No strategies found.");
            }
        } catch (error) {
            console.error('Failed to fetch strategies:', error);
            setStrategyError("Failed to load strategies. Check backend connection.");
        } finally {
            setIsStrategiesLoading(false);
        }
    };

    const toggleIndex = (index: string) => {
        setSelectedIndices(prev => prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index]);
    };

    const toggleStrategy = (name: string) => {
        setSelectedStrategies(prev => prev.includes(name) ? prev.filter(s => s !== name) : [...prev, name]);
    };

    const selectAllStrategies = (tier: string) => {
        const tierStrategies = strategies[tier]?.map(s => s.name) || [];
        setSelectedStrategies(prev => {
            const existing = prev.filter(s => !tierStrategies.includes(s));
            return [...existing, ...tierStrategies];
        });
    };

    const deselectAllStrategies = () => {
        setSelectedStrategies([]);
    };

    const deselectTier = (tier: string) => {
        const tierStrategies = strategies[tier]?.map(s => s.name) || [];
        setSelectedStrategies(prev => prev.filter(s => !tierStrategies.includes(s)));
    };

    const runScan = async () => {
        if (selectedIndices.length === 0 || selectedStrategies.length === 0) return;
        setIsLoading(true);
        setResults([]);
        try {
            const data = await api.runScan(selectedIndices, selectedTimeframe, selectedStrategies);
            if (data && data.results) setResults(data.results);
        } catch (error) {
            console.error('Scan failed:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const exportToCSV = () => {
        if (results.length === 0) return;
        const headers = ['Symbol', 'Index', 'Strategy', 'Signal', 'Confidence', 'PCR', 'Sentiment', 'Strength'];
        const rows = results.map(r => [
            r.symbol, r.index, r.strategy, r.signal,
            ((r.adjusted_confidence || r.confidence_score) * 100).toFixed(0) + '%',
            r.pcr, r.sentiment, r.signal_strength
        ]);
        const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `scanner_results_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
    };

    const sortedResults = results
        .filter(r => {
            if (resultFilter === 'buy') return r.final_signal === 'Buy';
            if (resultFilter === 'sell') return r.final_signal === 'Sell';
            return true;
        })
        .sort((a, b) => {
            const multiplier = sortOrder === 'asc' ? 1 : -1;
            if (sortBy === 'confidence_score') {
                return ((a.adjusted_confidence || a.confidence_score) - (b.adjusted_confidence || b.confidence_score)) * multiplier;
            }
            return a.symbol.localeCompare(b.symbol) * multiplier;
        });

    const filteredStrategies = (Object.entries(strategies) as [string, Strategy[]][]).reduce((acc, [tier, strats]) => {
        const filtered = strats.filter(s =>
            s.name.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
            s.description.toLowerCase().includes(debouncedSearch.toLowerCase())
        );
        if (filtered.length > 0) acc[tier] = filtered;
        return acc;
    }, {} as Record<string, Strategy[]>);

    return (
        <div className="flex h-full gap-5 overflow-hidden p-2">
            {/* Sidebar Strategy Browser */}
            <aside className="w-80 flex flex-col gap-4 flex-shrink-0 animate-in slide-in-from-left duration-500">
                <div className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200/60 dark:border-slate-700/60 rounded-3xl flex flex-col h-full shadow-2xl shadow-slate-200/50 dark:shadow-none overflow-hidden">
                    <div className="p-5 border-b border-slate-200/60 dark:border-slate-700/60">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-cyan-500 rounded-xl">
                                    <Zap size={20} className="text-white" />
                                </div>
                                <h2 className="text-lg font-black text-slate-800 dark:text-white tracking-tight">Strategy Lab</h2>
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => setIsHelpOpen(true)}
                                    className="p-2 text-slate-400 hover:text-cyan-500 hover:bg-cyan-50 dark:hover:bg-cyan-900/20 rounded-xl transition-all"
                                    title="Strategy Intelligence"
                                >
                                    <BookOpen size={18} />
                                </button>
                                <button
                                    onClick={deselectAllStrategies}
                                    className="p-2 text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 rounded-xl transition-all"
                                    title="Deselect All"
                                >
                                    <ZapOff size={18} />
                                </button>
                            </div>
                        </div>
                        <div className="relative">
                            <Search className="absolute left-3 top-3 text-slate-400" size={16} />
                            <input
                                type="text"
                                placeholder="Find a strategy..."
                                value={strategySearch}
                                onChange={(e) => setStrategySearch(e.target.value)}
                                className="w-full pl-10 pr-4 py-2.5 bg-slate-100/50 dark:bg-slate-900/50 rounded-2xl border border-transparent focus:border-cyan-500 focus:bg-white dark:focus:bg-slate-900 transition-all outline-none text-sm font-medium"
                            />
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto px-4 py-4 custom-scrollbar space-y-6">
                        {isStrategiesLoading ? (
                            <div className="flex flex-col items-center justify-center h-40">
                                <RefreshCw size={24} className="animate-spin text-cyan-500 mb-2" />
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Loading Logic...</span>
                            </div>
                        ) : strategyError ? (
                            <div className="p-4 text-center">
                                <p className="text-[10px] font-bold text-rose-500 uppercase mb-2">{strategyError}</p>
                                <button
                                    onClick={fetchStrategies}
                                    className="px-4 py-2 bg-slate-100 dark:bg-slate-900 rounded-xl text-[10px] font-black hover:bg-slate-200 dark:hover:bg-slate-800 transition-all"
                                >
                                    Retry Setup
                                </button>
                            </div>
                        ) : (
                            Object.entries(filteredStrategies).map(([tier, strats]) => (
                                <div key={tier} className="space-y-3">
                                    <div className="flex items-center justify-between px-1">
                                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{tier.split(' - ')[0]}</span>
                                        <div className="flex items-center gap-3">
                                            <button
                                                onClick={() => selectAllStrategies(tier)}
                                                className="text-[10px] font-bold text-cyan-500 hover:text-cyan-600 transition-colors uppercase tracking-widest"
                                            >
                                                All
                                            </button>
                                            <button
                                                onClick={() => deselectTier(tier)}
                                                className="text-[10px] font-bold text-rose-500 hover:text-rose-600 transition-colors uppercase tracking-widest"
                                            >
                                                None
                                            </button>
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        {strats.map(s => (
                                            <div
                                                key={s.name}
                                                onClick={() => toggleStrategy(s.name)}
                                                className={`group relative p-3.5 rounded-2xl border transition-all cursor-pointer ${selectedStrategies.includes(s.name)
                                                    ? 'bg-gradient-to-br from-white to-cyan-50 dark:from-slate-800 dark:to-cyan-950/20 border-cyan-200 dark:border-cyan-800 shadow-md'
                                                    : 'bg-white dark:bg-slate-800/40 border-transparent hover:border-slate-200 dark:hover:border-slate-700'
                                                    }`}
                                            >
                                                <div className="flex items-start justify-between gap-3 mb-1.5">
                                                    <span className={`text-xs font-black tracking-tight ${selectedStrategies.includes(s.name) ? 'text-cyan-600 dark:text-cyan-400' : 'text-slate-700 dark:text-slate-300'}`}>
                                                        {s.name}
                                                    </span>
                                                    <div className={`w-5 h-5 rounded-lg border transition-all flex items-center justify-center ${selectedStrategies.includes(s.name) ? 'bg-cyan-500 border-cyan-500 text-white' : 'border-slate-300 dark:border-slate-600'
                                                        }`}>
                                                        {selectedStrategies.includes(s.name) && <Check size={12} strokeWidth={4} />}
                                                    </div>
                                                </div>
                                                <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed line-clamp-2 transition-opacity group-hover:line-clamp-none">
                                                    {s.description}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 flex flex-col gap-5 overflow-hidden">
                {/* Top Control Bar */}
                <header className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200/60 dark:border-slate-700/60 rounded-3xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-xl shadow-slate-200/30 dark:shadow-none animate-in fade-in duration-700">
                    <div className="flex items-center gap-6">
                        <div className="flex flex-col gap-1.5">
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-1.5"><Target size={12} className="text-cyan-500" /> Indices</span>
                            <div className="flex gap-1.5">
                                {indices.map(idx => (
                                    <button
                                        key={idx}
                                        onClick={() => toggleIndex(idx)}
                                        className={`px-3 py-1.5 rounded-xl text-[10px] font-black transition-all border ${selectedIndices.includes(idx)
                                            ? 'bg-cyan-500 border-cyan-500 text-white shadow-lg shadow-cyan-500/20'
                                            : 'bg-slate-50 dark:bg-slate-900/50 border-slate-200 dark:border-slate-700 text-slate-500'
                                            }`}
                                    >
                                        {idx.replace('NIFTY ', '')}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <div className="w-px h-10 bg-slate-200 dark:bg-slate-700" />
                        <div className="flex flex-col gap-1.5">
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-1.5"><Clock size={12} className="text-cyan-500" /> Timeframe</span>
                            <div className="flex gap-1 bg-slate-100 dark:bg-slate-900 p-1 rounded-xl border border-slate-200 dark:border-slate-700">
                                {timeframes.map(tf => (
                                    <button
                                        key={tf.value}
                                        onClick={() => setSelectedTimeframe(tf.value)}
                                        className={`px-3 py-1 rounded-lg text-xs font-black transition-all ${selectedTimeframe === tf.value ? 'bg-white dark:bg-slate-700 text-cyan-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'
                                            }`}
                                    >
                                        {tf.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="hidden xl:flex flex-col items-end mr-2">
                            <span className="text-[10px] font-black text-amber-600 uppercase tracking-widest flex items-center gap-1.5">
                                <Activity size={12} /> Live Analysis
                            </span>
                            <span className="text-[9px] font-bold text-slate-400">SEBI Registered Framework</span>
                        </div>
                        <button
                            onClick={runScan}
                            disabled={isLoading || selectedIndices.length === 0 || selectedStrategies.length === 0}
                            className="h-12 px-8 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-700 hover:to-blue-700 text-white rounded-2xl font-black text-sm flex items-center gap-3 shadow-xl shadow-cyan-500/25 transition-all active:scale-95 disabled:opacity-50 disabled:grayscale"
                        >
                            {isLoading ? <RefreshCw size={20} className="animate-spin" /> : <Play size={20} fill="currentColor" />}
                            {isLoading ? 'Scanning...' : 'Execute Scan'}
                        </button>
                    </div>
                </header>

                {/* Main Results Table Container */}
                <div className="flex-1 bg-white/80 dark:bg-slate-800/80 backdrop-blur-xl border border-slate-200/60 dark:border-slate-700/60 rounded-3xl flex flex-col shadow-2xl shadow-slate-200/30 dark:shadow-none overflow-hidden animate-in slide-in-from-bottom duration-700">
                    {/* Results Table Header & Stats Row */}
                    <div className="p-6 border-b border-slate-200/60 dark:border-slate-700/60">
                        <div className="flex items-center justify-between mb-6">
                            <div className="flex items-center gap-3">
                                <div className="p-2.5 bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl shadow-lg shadow-slate-900/10">
                                    <BarChart2 size={24} className="text-white" />
                                </div>
                                <div>
                                    <h3 className="text-xl font-black text-slate-800 dark:text-white tracking-tight">Market Intelligence</h3>
                                    <p className="text-xs text-slate-500 font-bold tracking-tight uppercase">{results.length} Signal Matches Found Across Systems</p>
                                </div>
                            </div>
                            <button
                                onClick={exportToCSV}
                                disabled={results.length === 0}
                                className="flex items-center gap-2 px-4 py-2.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl text-xs font-black text-slate-700 dark:text-slate-300 hover:bg-white transition-all disabled:opacity-30"
                            >
                                <Download size={16} /> Export CSV
                            </button>
                        </div>

                        {results.length > 0 && (
                            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                                {[
                                    { label: 'Bullish Bias', val: results.filter(r => r.final_signal === 'Buy').length, color: 'emerald', icon: TrendingUp, type: 'buy' },
                                    { label: 'Bearish Bias', val: results.filter(r => r.final_signal === 'Sell').length, color: 'rose', icon: TrendingDown, type: 'sell' },
                                    { label: 'High Conviction', val: results.filter(r => r.signal_strength === 'Strong').length, color: 'violet', icon: Zap, type: 'all' },
                                    { label: 'Avg Confidence', val: (results.reduce((a, b) => a + (b.adjusted_confidence || b.confidence_score), 0) / results.length * 100).toFixed(0) + '%', color: 'cyan', icon: Target, type: 'all' },
                                ].map((stat, i) => (
                                    <div
                                        key={i}
                                        onClick={() => {
                                            if (stat.type === 'buy' || stat.type === 'sell') {
                                                setResultFilter(prev => prev === stat.type ? 'all' : stat.type as any);
                                            } else {
                                                setResultFilter('all');
                                            }
                                        }}
                                        className={`flex flex-col gap-1 p-3.5 bg-slate-50/50 dark:bg-slate-900/50 rounded-2xl border transition-all cursor-pointer hover:shadow-lg hover:shadow-slate-200/10 ${resultFilter === stat.type
                                            ? `ring-2 ring-${stat.color}-500/50 border-${stat.color}-500/50 bg-${stat.color}-50/10`
                                            : 'border-slate-200/30 dark:border-slate-700/30'
                                            }`}
                                    >
                                        <div className="flex items-center justify-between mb-1">
                                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{stat.label}</span>
                                            <stat.icon size={14} className={`text-${stat.color}-500`} />
                                        </div>
                                        <span className={`text-2xl font-black text-slate-800 dark:text-white`}>{stat.val}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Scrollable Table View */}
                    <div className="flex-1 overflow-auto custom-scrollbar">
                        {isLoading ? (
                            <div className="h-full flex flex-col items-center justify-center p-20 animate-in fade-in zoom-in duration-300">
                                <div className="relative w-24 h-24 mb-8">
                                    <div className="absolute inset-0 border-[6px] border-cyan-500/10 rounded-full" />
                                    <div className="absolute inset-0 border-[6px] border-t-cyan-500 rounded-full animate-spin shadow-lg shadow-cyan-500/20" />
                                    <Search className="absolute inset-0 m-auto text-cyan-500" size={32} />
                                </div>
                                <h4 className="text-xl font-black text-slate-800 dark:text-white mb-2 tracking-tight">Heavy Processing...</h4>
                                <p className="text-sm text-slate-400 font-bold uppercase tracking-widest">Scanning {selectedIndices.length} Markets • {selectedStrategies.length} Engines</p>
                            </div>
                        ) : results.length === 0 ? (
                            <div className="h-full flex flex-col items-center justify-center p-20 text-center animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <div className="p-8 bg-slate-50 dark:bg-slate-900/50 rounded-[40px] mb-8 border border-slate-200/50 dark:border-slate-800/50 shadow-inner">
                                    <Layers size={64} className="text-slate-200 dark:text-slate-700" />
                                </div>
                                <h4 className="text-2xl font-black text-slate-800 dark:text-white mb-3 tracking-tight">System Ready for Analysis</h4>
                                <p className="text-slate-400 font-medium max-w-sm mx-auto leading-relaxed">Select your preferred indices and specialized strategies from the <span className="text-cyan-500 font-black">Strategy Lab</span> to begin deep market scanning.</p>
                            </div>
                        ) : (
                            <table className="w-full text-left border-separate border-spacing-0">
                                <thead className="sticky top-0 bg-white/90 dark:bg-slate-900/90 backdrop-blur z-20 shadow-sm">
                                    <tr>
                                        {[
                                            { label: 'Asset', key: 'symbol' },
                                            { label: 'Decision', key: 'final_signal' },
                                            { label: 'Strength', key: 'signal_strength' },
                                            { label: 'Confidence', key: 'confidence_score' },
                                            { label: 'PCR', key: 'pcr' },
                                            { label: 'Sentiment', key: 'sentiment' },
                                            { label: 'System', key: 'strategy' }
                                        ].map(h => (
                                            <th
                                                key={h.key}
                                                onClick={() => { setSortBy(h.key as any); setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc'); }}
                                                className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest cursor-pointer hover:text-cyan-500 transition-colors"
                                            >
                                                <div className="flex items-center gap-2">
                                                    {h.label}
                                                    {sortBy === h.key && (sortOrder === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
                                                </div>
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                    {sortedResults.map((r, idx) => (
                                        <tr key={`${r.symbol}-${idx}`} className="group hover:bg-slate-50/80 dark:hover:bg-slate-700/20 transition-all">
                                            <td className="px-6 py-5">
                                                <div className="flex flex-col">
                                                    <span className="text-sm font-black text-slate-800 dark:text-white group-hover:text-cyan-600 transition-colors uppercase tracking-tight">{r.symbol}</span>
                                                    <span className="text-[10px] font-bold text-slate-400">{r.index}</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-5">
                                                <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-black shadow-sm ${r.final_signal === 'Buy' ? 'bg-emerald-500 text-white shadow-emerald-500/20' :
                                                    r.final_signal === 'Sell' ? 'bg-rose-500 text-white shadow-rose-500/20' :
                                                        'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300'
                                                    }`}>
                                                    {r.final_signal === 'Buy' && <TrendingUp size={14} strokeWidth={3} />}
                                                    {r.final_signal === 'Sell' && <TrendingDown size={14} strokeWidth={3} />}
                                                    {r.final_signal}
                                                </div>
                                            </td>
                                            <td className="px-6 py-5">
                                                <span className={`text-[10px] font-black uppercase px-2 py-1 rounded-lg border ${r.signal_strength === 'Strong' ? 'border-violet-200 bg-violet-50 text-violet-600 dark:bg-violet-900/20 dark:border-violet-900/50' :
                                                    r.signal_strength === 'Moderate' ? 'border-blue-200 bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:border-blue-900/50' :
                                                        'border-slate-200 bg-slate-50 text-slate-500 dark:bg-slate-700/50 dark:border-slate-700'
                                                    }`}>
                                                    {r.signal_strength}
                                                </span>
                                            </td>
                                            <td className="px-6 py-5">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-16 h-1.5 bg-slate-100 dark:bg-slate-900 rounded-full overflow-hidden">
                                                        <div
                                                            className={`h-full rounded-full transition-all duration-1000 ${(r.adjusted_confidence || r.confidence_score) > 0.7 ? 'bg-emerald-500' :
                                                                (r.adjusted_confidence || r.confidence_score) > 0.5 ? 'bg-amber-500' : 'bg-rose-500'
                                                                }`}
                                                            style={{ width: `${(r.adjusted_confidence || r.confidence_score) * 100}%` }}
                                                        />
                                                    </div>
                                                    <span className="text-[11px] font-black text-slate-700 dark:text-slate-300">
                                                        {((r.adjusted_confidence || r.confidence_score) * 100).toFixed(0)}%
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-5">
                                                <span className={`text-xs font-black ${typeof r.pcr === 'number' && r.pcr > 1 ? 'text-emerald-500' : 'text-slate-500'}`}>
                                                    {typeof r.pcr === 'number' ? r.pcr.toFixed(2) : '--'}
                                                </span>
                                            </td>
                                            <td className="px-6 py-5">
                                                <div className="flex items-center gap-1.5">
                                                    <div className={`w-1.5 h-1.5 rounded-full ${r.sentiment === 'Bullish' ? 'bg-emerald-500 ring-4 ring-emerald-500/20' : r.sentiment === 'Bearish' ? 'bg-rose-500 ring-4 ring-rose-500/20' : 'bg-slate-400'}`} />
                                                    <span className="text-[11px] font-black text-slate-700 dark:text-slate-300 uppercase tracking-tight">{r.sentiment}</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-5">
                                                <div className="flex items-center gap-2 group/info">
                                                    <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-900/50 px-2 py-1 rounded shadow-sm border border-slate-200/50 dark:border-slate-800/50">
                                                        {r.strategy}
                                                    </span>
                                                    <Info size={12} className="text-slate-300 group-hover/info:text-cyan-500 transition-colors cursor-help" title={r.market_interpretation} />
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>
            </main>

            {/* Strategy Intelligence Help Modal */}
            {isHelpOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 animate-in fade-in duration-300">
                    <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={() => setIsHelpOpen(false)} />
                    <div className="relative w-full max-w-4xl max-h-[90vh] bg-white dark:bg-slate-800 rounded-[40px] shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-700 flex flex-col animate-in zoom-in-95 duration-300">
                        {/* Modal Header */}
                        <div className="p-8 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between bg-gradient-to-r from-slate-50 to-white dark:from-slate-800 dark:to-slate-800/50">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-cyan-500 rounded-2xl shadow-lg shadow-cyan-500/20">
                                    <BookOpen size={28} className="text-white" />
                                </div>
                                <div>
                                    <h2 className="text-2xl font-black text-slate-800 dark:text-white tracking-tight">Strategy Intelligence</h2>
                                    <p className="text-sm text-slate-500 font-bold uppercase tracking-widest mt-1">Quantitative Framework & Logic Documentation</p>
                                </div>
                            </div>
                            <button
                                onClick={() => setIsHelpOpen(false)}
                                className="p-3 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-2xl transition-all"
                            >
                                <X size={24} className="text-slate-400" />
                            </button>
                        </div>

                        {/* Modal Content */}
                        <div className="flex-1 overflow-y-auto p-8 custom-scrollbar space-y-10">
                            {/* Intro Section */}
                            <section className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                <div className="space-y-4">
                                    <h3 className="text-lg font-black text-slate-800 dark:text-white flex items-center gap-2">
                                        <Cpu size={20} className="text-cyan-500" /> System Architecture
                                    </h3>
                                    <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed font-medium">
                                        The QuantAI Scanner utilizes a tiered hierarchy of professional trading models. Each signal is the result of thousands of calculations comparing historical price action, volume liquidity, and market sentiment.
                                    </p>
                                </div>
                                <div className="bg-slate-50 dark:bg-slate-900/50 rounded-3xl p-6 border border-slate-100 dark:border-slate-700/50">
                                    <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Signal Verification Tiers</h3>
                                    <div className="space-y-3">
                                        <div className="flex items-center gap-3">
                                            <div className="w-2 h-2 rounded-full bg-emerald-500" />
                                            <span className="text-xs font-black text-slate-700 dark:text-slate-300">Tier 1: High Win-Rate institutional setups</span>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <div className="w-2 h-2 rounded-full bg-cyan-500" />
                                            <span className="text-xs font-black text-slate-700 dark:text-slate-300">Tier 2: Solid momentum & trend following</span>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <div className="w-2 h-2 rounded-full bg-violet-500" />
                                            <span className="text-xs font-black text-slate-700 dark:text-slate-300">Tier 3: Advanced statistical mean-reversion</span>
                                        </div>
                                    </div>
                                </div>
                            </section>

                            {/* Core Strategy Logics */}
                            <section className="space-y-6">
                                <h3 className="text-xl font-black text-slate-800 dark:text-white tracking-tight px-1">Logic Clusters</h3>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    {[
                                        {
                                            title: 'VWAP Equilibrium',
                                            logic: 'Institutional benchmark. Models detect price reclaim of the session weighted average with volume confirmation.',
                                            icon: Activity,
                                            color: 'cyan'
                                        },
                                        {
                                            title: 'Liquidity Breakouts',
                                            logic: 'Scans for consolidation zones where volume is accumulating before a confirmed range expansion.',
                                            icon: Zap,
                                            color: 'amber'
                                        },
                                        {
                                            title: 'Mean Reversion',
                                            logic: 'Utilizes RSI and Bollinger extremes to identify overextended assets likely to return to their 20-period moving average.',
                                            icon: RefreshCw,
                                            color: 'violet'
                                        },
                                        {
                                            title: 'Trend Ribbons',
                                            logic: 'Multiple moving average filters ensure that signals are generated only in the direction of the dominant primary trend.',
                                            icon: Layers,
                                            color: 'emerald'
                                        }
                                    ].map((l, i) => (
                                        <div key={i} className="p-5 flex gap-4 items-start bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700 hover:border-cyan-500/30 transition-all rounded-3xl shadow-sm">
                                            <div className={`p-3 bg-${l.color}-50 dark:bg-${l.color}-900/20 rounded-2xl text-${l.color}-500`}>
                                                <l.icon size={20} />
                                            </div>
                                            <div>
                                                <h4 className="text-sm font-black text-slate-800 dark:text-white mb-1">{l.title}</h4>
                                                <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium leading-relaxed">{l.logic}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>

                            <section className="bg-gradient-to-br from-cyan-500 to-blue-600 rounded-[32px] p-8 text-white shadow-xl shadow-cyan-500/20">
                                <h3 className="text-lg font-black mb-4 flex items-center gap-2">
                                    <ShieldCheck size={24} /> Derivatives Intelligence Layer
                                </h3>
                                <p className="text-sm opacity-90 font-medium leading-relaxed mb-6">
                                    Every technical signal is cross-referenced with Option Chain data (PCR & Open Interest) to verify if institutional positioning supports the price action. A "High Conviction" signal requires both Technical and Derivative confluence.
                                </p>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-white/10 backdrop-blur-md rounded-2xl p-4 border border-white/10">
                                        <p className="text-[10px] font-black uppercase tracking-widest mb-1">PCR Logic</p>
                                        <p className="text-xs font-bold">PCR {'>'} 1.0 indicates bullish hedging/positioning.</p>
                                    </div>
                                    <div className="bg-white/10 backdrop-blur-md rounded-2xl p-4 border border-white/10">
                                        <p className="text-[10px] font-black uppercase tracking-widest mb-1">OI Logic</p>
                                        <p className="text-xs font-bold">Buildup confirms trend; Unwinding warns of exhaustion.</p>
                                    </div>
                                </div>
                            </section>
                        </div>

                        {/* Modal Footer */}
                        <div className="p-6 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-100 dark:border-slate-700 flex justify-center">
                            <button
                                onClick={() => setIsHelpOpen(false)}
                                className="px-10 py-3 bg-slate-800 dark:bg-slate-700 text-white rounded-2xl font-black text-sm hover:bg-slate-900 transition-all shadow-lg"
                            >
                                Understood
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Scanner;
