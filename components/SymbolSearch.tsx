import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, X, TrendingUp, Loader } from 'lucide-react';

interface SymbolSearchProps {
    selectedSymbols: string[];
    onSymbolsChange: (symbols: string[]) => void;
    timeframe: string;
    maxSymbols?: number;
}

interface SymbolOption {
    symbol: string;
    name?: string;
    exchange?: string;
}

const SymbolSearch: React.FC<SymbolSearchProps> = ({
    selectedSymbols,
    onSymbolsChange,
    timeframe,
    maxSymbols = 10
}) => {
    const [searchQuery, setSearchQuery] = useState('');
    const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
    const [filteredSymbols, setFilteredSymbols] = useState<string[]>([]);
    const [showDropdown, setShowDropdown] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [highlightedIndex, setHighlightedIndex] = useState(0);

    const searchRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Fetch available symbols when timeframe changes
    useEffect(() => {
        const fetchSymbols = async () => {
            setLoading(true);
            setError(null);

            try {
                const response = await fetch(
                    `/api/v1/walk-forward/symbols?timeframe=${timeframe}`
                );

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();

                if (data.symbols && data.symbols.length > 0) {
                    setAvailableSymbols(data.symbols);
                } else {
                    setError('No symbols available for this timeframe');
                }
            } catch (err: any) {
                console.error('[Symbol Search] Error:', err);
                setError('Failed to fetch symbols');
                // Fallback to hardcoded popular symbols
                setAvailableSymbols([
                    'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
                    'HINDUNILVR', 'SBIN', 'BHARTIARTL', 'KOTAKBANK', 'ITC'
                ]);
            } finally {
                setLoading(false);
            }
        };

        fetchSymbols();
    }, [timeframe]);

    // Debounced search with filtering
    useEffect(() => {
        if (!searchQuery.trim()) {
            setFilteredSymbols([]);
            return;
        }

        const query = searchQuery.toUpperCase();
        const filtered = availableSymbols
            .filter(symbol => {
                // Don't show already selected symbols
                if (selectedSymbols.includes(symbol)) return false;
                // Match query
                return symbol.includes(query);
            })
            .slice(0, 20); // Limit to 20 results

        setFilteredSymbols(filtered);
        setHighlightedIndex(0);
    }, [searchQuery, availableSymbols, selectedSymbols]);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
                setShowDropdown(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const addSymbol = useCallback((symbol: string) => {
        if (selectedSymbols.length >= maxSymbols) {
            setError(`Maximum ${maxSymbols} symbols allowed`);
            setTimeout(() => setError(null), 3000);
            return;
        }

        if (!selectedSymbols.includes(symbol)) {
            onSymbolsChange([...selectedSymbols, symbol]);
        }

        setSearchQuery('');
        setShowDropdown(false);
        inputRef.current?.focus();
    }, [selectedSymbols, onSymbolsChange, maxSymbols]);

    const removeSymbol = useCallback((symbol: string) => {
        onSymbolsChange(selectedSymbols.filter(s => s !== symbol));
    }, [selectedSymbols, onSymbolsChange]);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (!showDropdown || filteredSymbols.length === 0) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                setHighlightedIndex(prev =>
                    prev < filteredSymbols.length - 1 ? prev + 1 : 0
                );
                break;
            case 'ArrowUp':
                e.preventDefault();
                setHighlightedIndex(prev =>
                    prev > 0 ? prev - 1 : filteredSymbols.length - 1
                );
                break;
            case 'Enter':
                e.preventDefault();
                if (filteredSymbols[highlightedIndex]) {
                    addSymbol(filteredSymbols[highlightedIndex]);
                }
                break;
            case 'Escape':
                setShowDropdown(false);
                setSearchQuery('');
                break;
        }
    };

    // Quick add popular symbols
    const popularSymbols = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'SBIN', 'ICICIBANK'];
    const availablePopular = popularSymbols.filter(s =>
        availableSymbols.includes(s) && !selectedSymbols.includes(s)
    );

    return (
        <div className="space-y-3">
            {/* Search Input */}
            <div ref={searchRef} className="relative">
                <div className="relative">
                    <Search
                        className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400"
                        size={18}
                    />
                    <input
                        ref={inputRef}
                        type="text"
                        value={searchQuery}
                        onChange={e => {
                            setSearchQuery(e.target.value);
                            setShowDropdown(true);
                        }}
                        onFocus={() => setShowDropdown(true)}
                        onKeyDown={handleKeyDown}
                        placeholder={`Search from ${availableSymbols.length} symbols...`}
                        disabled={loading}
                        className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50"
                    />
                    {loading && (
                        <Loader
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-indigo-600 animate-spin"
                            size={18}
                        />
                    )}
                </div>

                {/* Dropdown */}
                {showDropdown && searchQuery.length > 0 && (
                    <div className="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg shadow-xl max-h-64 overflow-y-auto">
                        {filteredSymbols.length > 0 ? (
                            filteredSymbols.map((symbol, index) => (
                                <button
                                    key={symbol}
                                    onClick={() => addSymbol(symbol)}
                                    onMouseEnter={() => setHighlightedIndex(index)}
                                    className={`w-full px-4 py-2.5 text-left transition-colors flex items-center gap-2 ${index === highlightedIndex
                                        ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
                                        }`}
                                >
                                    <TrendingUp size={16} className="flex-shrink-0" />
                                    <span className="font-medium">{symbol}</span>
                                    <span className="ml-auto text-xs text-slate-500">NSE</span>
                                </button>
                            ))
                        ) : (
                            <div className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400 text-center">
                                No symbols found matching "{searchQuery}"
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Selected Symbols */}
            {selectedSymbols.length > 0 && (
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                            Selected ({selectedSymbols.length}/{maxSymbols})
                        </label>
                        {selectedSymbols.length > 0 && (
                            <button
                                onClick={() => onSymbolsChange([])}
                                className="text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 font-medium"
                            >
                                Clear All
                            </button>
                        )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {selectedSymbols.map(symbol => (
                            <span
                                key={symbol}
                                className="px-3 py-1.5 bg-gradient-to-r from-indigo-100 to-purple-100 dark:from-indigo-900/40 dark:to-purple-900/40 text-indigo-700 dark:text-indigo-300 rounded-full text-sm font-medium flex items-center gap-2 border border-indigo-200 dark:border-indigo-700"
                            >
                                {symbol}
                                <button
                                    onClick={() => removeSymbol(symbol)}
                                    className="hover:text-red-600 dark:hover:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-full p-0.5 transition"
                                >
                                    <X size={14} />
                                </button>
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Quick Add */}
            {availablePopular.length > 0 && selectedSymbols.length < maxSymbols && (
                <div>
                    <label className="text-xs text-slate-500 dark:text-slate-400 mb-1.5 block">
                        Quick add popular:
                    </label>
                    <div className="flex flex-wrap gap-1.5">
                        {availablePopular.slice(0, 8).map(symbol => (
                            <button
                                key={symbol}
                                onClick={() => addSymbol(symbol)}
                                className="px-2 py-1 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/30 hover:text-indigo-700 dark:hover:text-indigo-300 rounded text-xs font-medium transition"
                            >
                                +{symbol}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Error Message */}
            {error && (
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg p-2">
                    <p className="text-amber-700 dark:text-amber-300 text-xs">{error}</p>
                </div>
            )}

            {/* Stats */}
            <div className="text-xs text-slate-500 dark:text-slate-400">
                {availableSymbols.length} symbols available for {timeframe} timeframe
            </div>
        </div>
    );
};

export default SymbolSearch;
