import React from 'react';
import { TrendingUp, TrendingDown, Zap, Target } from 'lucide-react';

interface ScanResult {
    final_signal: 'Buy' | 'Sell' | 'Hold';
    signal_strength: 'Strong' | 'Moderate' | 'Weak';
    adjusted_confidence?: number;
    confidence_score: number;
}

interface ScannerStatsProps {
    results: ScanResult[];
    resultFilter: 'all' | 'buy' | 'sell';
    onFilterChange: (filter: 'all' | 'buy' | 'sell') => void;
}

interface StatCard {
    label: string;
    val: number | string;
    color: string;
    icon: React.ComponentType<{ size: number; className?: string }>;
    type: 'all' | 'buy' | 'sell';
}

const ScannerStats: React.FC<ScannerStatsProps> = ({ results, resultFilter, onFilterChange }) => {
    if (results.length === 0) return null;

    const stats: StatCard[] = [
        {
            label: 'Bullish Bias',
            val: results.filter(r => r.final_signal === 'Buy').length,
            color: 'emerald',
            icon: TrendingUp,
            type: 'buy'
        },
        {
            label: 'Bearish Bias',
            val: results.filter(r => r.final_signal === 'Sell').length,
            color: 'rose',
            icon: TrendingDown,
            type: 'sell'
        },
        {
            label: 'High Conviction',
            val: results.filter(r => r.signal_strength === 'Strong').length,
            color: 'violet',
            icon: Zap,
            type: 'all'
        },
        {
            label: 'Avg Confidence',
            val: (results.reduce((a, b) => a + (b.adjusted_confidence || b.confidence_score), 0) / results.length * 100).toFixed(0) + '%',
            color: 'cyan',
            icon: Target,
            type: 'all'
        },
    ];

    return (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {stats.map((stat, i) => (
                <div
                    key={i}
                    onClick={() => {
                        if (stat.type === 'buy' || stat.type === 'sell') {
                            onFilterChange(resultFilter === stat.type ? 'all' : stat.type);
                        } else {
                            onFilterChange('all');
                        }
                    }}
                    className={`flex flex-col gap-1 p-3.5 bg-slate-50/50 dark:bg-slate-900/50 rounded-2xl border transition-all cursor-pointer hover:shadow-lg hover:shadow-slate-200/10 ${resultFilter === stat.type
                            ? `ring-2 ring-${stat.color}-500/50 border-${stat.color}-500/50 bg-${stat.color}-50/10`
                            : 'border-slate-200/30 dark:border-slate-700/30'
                        }`}
                >
                    <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                            {stat.label}
                        </span>
                        <stat.icon size={14} className={`text-${stat.color}-500`} />
                    </div>
                    <span className="text-2xl font-black text-slate-800 dark:text-white">
                        {stat.val}
                    </span>
                </div>
            ))}
        </div>
    );
};

export default ScannerStats;
