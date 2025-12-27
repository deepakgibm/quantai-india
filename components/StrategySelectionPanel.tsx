import React, { useState, useEffect, useCallback } from 'react';
import {
    Play,
    TrendingUp,
    BarChart2,
    Calendar,
    Settings2,
    AlertTriangle,
    CheckCircle,
    XCircle,
    ChevronDown,
    ChevronUp,
    RefreshCw,
    Info,
    HelpCircle,
    X,
    Search,
    Filter,
    Layers
} from 'lucide-react';

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

interface StrategyParameter {
    type: string;
    default: any;
    min?: number;
    max?: number;
    description: string;
}

interface StrategyInfo {
    name: string;
    display_name: string;
    category: string;
    description: string;
    parameters: Record<string, StrategyParameter>;
    time_horizon: string;
    tier?: string;
    is_implemented: boolean;
}

interface StrategyCategory {
    category_name: string;
    strategies: StrategyInfo[];
    tier?: string;
}

interface TierGroup {
    name: string;
    tier_id: string;
    categories: StrategyCategory[];
    expanded: boolean;
}

// ============================================================================
// STRATEGY SELECTOR COMPONENT WITH TIER GROUPING
// ============================================================================

interface StrategySelectionPanelProps {
    selectedStrategies: StrategyInfo[];
    onSelectionChange: (strategies: StrategyInfo[]) => void;
}

const StrategySelectionPanel: React.FC<StrategySelectionPanelProps> = ({
    selectedStrategies,
    onSelectionChange,
}) => {
    const [tierGroups, setTierGroups] = useState<TierGroup[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [filterImplemented, setFilterImplemented] = useState(false);

    // Fetch strategies organized by tier
    useEffect(() => {
        const fetchStrategies = async () => {
            setLoading(true);
            setError(null);

            try {
                const response = await fetch('http://localhost:8000/api/v1/backtest/strategies/by-tier');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();

                // Transform to tier groups
                const groups: TierGroup[] = [
                    {
                        name: data.tier_1?.name || 'Tier 1: Mean Reversion & Classic Breakouts',
                        tier_id: 'tier_1',
                        categories: data.tier_1?.categories || [],
                        expanded: true
                    },
                    {
                        name: data.tier_2?.name || 'Tier 2: Momentum & Trend Confirmation',
                        tier_id: 'tier_2',
                        categories: data.tier_2?.categories || [],
                        expanded: true
                    },
                    {
                        name: data.tier_3?.name || 'Tier 3: Advanced & Structural',
                        tier_id: 'tier_3',
                        categories: data.tier_3?.categories || [],
                        expanded: false
                    }
                ];

                setTierGroups(groups);
            } catch (err: any) {
                console.error('[Strategy Selection] Error:', err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchStrategies();
    }, []);

    const toggleTier = (tierId: string) => {
        setTierGroups(groups =>
            groups.map(g =>
                g.tier_id === tierId ? { ...g, expanded: !g.expanded } : g
            )
        );
    };

    const isSelected = (strategy: StrategyInfo) => {
        return selectedStrategies.some(s => s.name === strategy.name);
    };

    const toggleStrategy = (strategy: StrategyInfo) => {
        if (isSelected(strategy)) {
            onSelectionChange(selectedStrategies.filter(s => s.name !== strategy.name));
        } else {
            onSelectionChange([...selectedStrategies, strategy]);
        }
    };

    const selectAllInTier = (tierId: string) => {
        const tier = tierGroups.find(g => g.tier_id === tierId);
        if (!tier) return;

        const allStrategies = tier.categories.flatMap(cat => cat.strategies);
        const filtered = filterImplemented
            ? allStrategies.filter(s => s.is_implemented)
            : allStrategies;

        // Add all tier strategies
        const newSelection = [...selectedStrategies];
        filtered.forEach(strat => {
            if (!newSelection.some(s => s.name === strat.name)) {
                newSelection.push(strat);
            }
        });
        onSelectionChange(newSelection);
    };

    const deselectAllInTier = (tierId: string) => {
        const tier = tierGroups.find(g => g.tier_id === tierId);
        if (!tier) return;

        const tierStrategyNames = tier.categories
            .flatMap(cat => cat.strategies)
            .map(s => s.name);

        onSelectionChange(
            selectedStrategies.filter(s => !tierStrategyNames.includes(s.name))
        );
    };

    const filterStrategies = (strategies: StrategyInfo[]) => {
        let filtered = strategies;

        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            filtered = filtered.filter(s =>
                s.display_name.toLowerCase().includes(query) ||
                s.description.toLowerCase().includes(query)
            );
        }

        if (filterImplemented) {
            filtered = filtered.filter(s => s.is_implemented);
        }

        return filtered;
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center p-8">
                <RefreshCw className="animate-spin text-indigo-600" size={24} />
                <span className="ml-3 text-slate-600">Loading strategies...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-700 text-sm">{error}</p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Search & Filter Bar */}
            <div className="flex flex-col gap-2">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" size={16} />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        placeholder="Filter strategies..."
                        className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all"
                    />
                </div>
                <button
                    onClick={() => setFilterImplemented(!filterImplemented)}
                    className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 border ${filterImplemented
                        ? 'bg-indigo-600 border-indigo-500 text-white'
                        : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50'
                        }`}
                >
                    <Filter size={14} />
                    {filterImplemented ? 'Showing Implemented' : 'Showing All Strategies'}
                </button>
            </div>

            {/* Selection Stats */}
            <div className="bg-indigo-50 dark:bg-indigo-900/30 border border-indigo-200 dark:border-indigo-700 rounded-lg p-3">
                <div className="flex items-center justify-between text-sm">
                    <span className="text-indigo-700 dark:text-indigo-300 font-medium">
                        {selectedStrategies.length} {selectedStrategies.length === 1 ? 'strategy' : 'strategies'} selected
                    </span>
                    {selectedStrategies.length > 0 && (
                        <button
                            onClick={() => onSelectionChange([])}
                            className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-200 font-medium"
                        >
                            Clear All
                        </button>
                    )}
                </div>
            </div>

            {/* Tier Groups */}
            <div className="space-y-3">
                {tierGroups.map(tier => {
                    const allStrategiesInTier = tier.categories.flatMap(cat => cat.strategies);
                    const selectedInTier = selectedStrategies.filter(s =>
                        allStrategiesInTier.some(ts => ts.name === s.name)
                    ).length;
                    const totalInTier = allStrategiesInTier.length;

                    return (
                        <div
                            key={tier.tier_id}
                            className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden"
                        >
                            {/* Tier Header */}
                            <div className="bg-gradient-to-r from-indigo-500 to-purple-600 p-3">
                                <div className="flex flex-col gap-3">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2 min-w-0">
                                            <button
                                                onClick={() => toggleTier(tier.tier_id)}
                                                className="text-white hover:bg-white/10 rounded-lg p-1 transition flex-shrink-0"
                                            >
                                                {tier.expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                                            </button>
                                            <div className="min-w-0">
                                                <h3 className="text-white font-bold flex items-center gap-2 text-xs truncate">
                                                    <Layers size={14} className="flex-shrink-0" />
                                                    <span className="truncate">{tier.name}</span>
                                                </h3>
                                                <p className="text-white/70 text-[10px] mt-0.5 font-medium">
                                                    {selectedInTier}/{totalInTier} active
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => selectAllInTier(tier.tier_id)}
                                            className="flex-1 px-2 py-1 bg-white/10 hover:bg-white/20 text-white text-[10px] font-bold uppercase tracking-wider rounded border border-white/10 transition"
                                        >
                                            Select All
                                        </button>
                                        <button
                                            onClick={() => deselectAllInTier(tier.tier_id)}
                                            className="flex-1 px-2 py-1 bg-white/10 hover:bg-white/20 text-white text-[10px] font-bold uppercase tracking-wider rounded border border-white/10 transition"
                                        >
                                            Clear
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Tier Content */}
                            {tier.expanded && (
                                <div className="p-4 space-y-4">
                                    {tier.categories.map(category => {
                                        const filteredStrategies = filterStrategies(category.strategies);

                                        if (filteredStrategies.length === 0) return null;

                                        return (
                                            <div key={category.category_name}>
                                                <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                                                    {category.category_name}
                                                </h4>
                                                <div className="grid grid-cols-1 gap-2">
                                                    {filteredStrategies.map(strategy => {
                                                        const selected = isSelected(strategy);
                                                        return (
                                                            <button
                                                                key={strategy.name}
                                                                onClick={() => toggleStrategy(strategy)}
                                                                disabled={!strategy.is_implemented}
                                                                className={`group relative text-left p-2.5 rounded-xl border transition-all duration-200 ${selected
                                                                    ? 'bg-indigo-50 dark:bg-indigo-900/30 border-indigo-400 dark:border-indigo-500 shadow-sm shadow-indigo-500/10'
                                                                    : strategy.is_implemented
                                                                        ? 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-md'
                                                                        : 'bg-slate-50/50 dark:bg-slate-800/30 border-slate-200 dark:border-slate-700 opacity-60 cursor-not-allowed'
                                                                    }`}
                                                            >
                                                                <div className="flex items-start gap-2.5">
                                                                    {selected && (
                                                                        <CheckCircle
                                                                            size={14}
                                                                            className="text-indigo-600 dark:text-indigo-400 mt-0.5 flex-shrink-0"
                                                                        />
                                                                    )}
                                                                    <div className="min-w-0 flex-1">
                                                                        <h5 className={`text-xs font-bold leading-tight truncate ${selected
                                                                            ? 'text-indigo-700 dark:text-indigo-300'
                                                                            : 'text-slate-900 dark:text-white'
                                                                            }`}>
                                                                            {strategy.display_name}
                                                                        </h5>
                                                                        <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                                                                            {strategy.description}
                                                                        </p>
                                                                        {!strategy.is_implemented && (
                                                                            <span className="inline-flex mt-1.5 px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 text-[9px] font-bold uppercase tracking-tighter rounded">
                                                                                Planned
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            </button>
                                                        );
                                                    })}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default StrategySelectionPanel;
