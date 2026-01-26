import React from 'react';
import {
    TrendingUp,
    TrendingDown,
    ChevronDown,
    ChevronUp,
    Info
} from 'lucide-react';
import { PriceWithSource } from '../PriceSourceBadge';

interface ScanResult {
    symbol: string;
    index: string;
    timeframe: string;
    strategy: string;
    signal: 'Bullish' | 'Bearish' | 'Neutral';
    confidence_score: number;
    indicators: Record<string, number>;
    pcr: number | 'N/A';
    sentiment: 'Bullish' | 'Bearish' | 'Neutral' | 'N/A';
    market_interpretation: string;
    final_signal: 'Buy' | 'Sell' | 'Hold';
    signal_strength: 'Strong' | 'Moderate' | 'Weak';
    adjusted_confidence: number;
    price_source?: string;
}

interface ScannerResultsTableProps {
    results: ScanResult[];
    sortBy: 'confidence_score' | 'symbol';
    sortOrder: 'asc' | 'desc';
    onSortChange: (column: 'confidence_score' | 'symbol') => void;
}

const COLUMNS = [
    { label: 'Asset', key: 'symbol' },
    { label: 'Decision', key: 'final_signal' },
    { label: 'Strength', key: 'signal_strength' },
    { label: 'Confidence', key: 'confidence_score' },
    { label: 'PCR', key: 'pcr' },
    { label: 'Sentiment', key: 'sentiment' },
    { label: 'System', key: 'strategy' }
] as const;

const ScannerResultsTable: React.FC<ScannerResultsTableProps> = ({
    results,
    sortBy,
    sortOrder,
    onSortChange
}) => {
    return (
        <table className="w-full text-left border-separate border-spacing-0">
            <thead className="sticky top-0 bg-white/90 dark:bg-slate-900/90 backdrop-blur z-20 shadow-sm">
                <tr>
                    {COLUMNS.map(h => (
                        <th
                            key={h.key}
                            onClick={() => onSortChange(h.key as any)}
                            className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest cursor-pointer hover:text-cyan-500 transition-colors"
                        >
                            <div className="flex items-center gap-2">
                                {h.label}
                                {sortBy === h.key && (
                                    sortOrder === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />
                                )}
                            </div>
                        </th>
                    ))}
                </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {results.map((r, idx) => (
                    <tr key={`${r.symbol}-${idx}`} className="group hover:bg-slate-50/80 dark:hover:bg-slate-700/20 transition-all">
                        <td className="px-6 py-5">
                            <div className="flex flex-col">
                                <span className="text-sm font-black text-slate-800 dark:text-white group-hover:text-cyan-600 transition-colors uppercase tracking-tight">
                                    {r.symbol}
                                </span>
                                <PriceWithSource
                                    price={r.indicators?.price || r.indicators?.ltp}
                                    source={r.price_source}
                                    className="text-[10px]"
                                />
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
                                <div className={`w-1.5 h-1.5 rounded-full ${r.sentiment === 'Bullish' ? 'bg-emerald-500 ring-4 ring-emerald-500/20' :
                                        r.sentiment === 'Bearish' ? 'bg-rose-500 ring-4 ring-rose-500/20' : 'bg-slate-400'
                                    }`} />
                                <span className="text-[11px] font-black text-slate-700 dark:text-slate-300 uppercase tracking-tight">
                                    {r.sentiment}
                                </span>
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
    );
};

export default ScannerResultsTable;
