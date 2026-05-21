import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, X, TrendingUp, Loader2 } from 'lucide-react';
import { useGlobalSymbol } from '../contexts/GlobalSymbolContext';
import { api } from '../services/api';

interface StockResult {
  symbol: string;
  company_name: string;
  exchange: string;
  sector: string;
  instrument_key: string;
}

export const GlobalSymbolSearch: React.FC = () => {
  const { selectedSymbol, setSelectedSymbol } = useGlobalSymbol();
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<StockResult[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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

  // Debounced search API call
  useEffect(() => {
    if (!searchQuery.trim()) {
      setResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.searchStocks(searchQuery);
        if (data && Array.isArray(data.results)) {
          setResults(data.results);
        } else {
          setResults([]);
        }
      } catch (err: any) {
        console.error('[Global Symbol Search] Error:', err);
        setError('Failed to fetch results');
        setResults([]);
      } finally {
        setLoading(false);
        setHighlightedIndex(0);
      }
    }, 300); // 300ms debounce

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleSelect = useCallback((symbol: string) => {
    setSelectedSymbol(symbol);
    setSearchQuery('');
    setShowDropdown(false);
    if (inputRef.current) {
      inputRef.current.blur();
    }
  }, [setSelectedSymbol]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showDropdown || results.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex(prev =>
          prev < results.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prev =>
          prev > 0 ? prev - 1 : results.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (results[highlightedIndex]) {
          handleSelect(results[highlightedIndex].symbol);
        }
        break;
      case 'Escape':
        setShowDropdown(false);
        setSearchQuery('');
        break;
    }
  };

  return (
    <div ref={searchRef} className="relative w-full max-w-md">
      <div className="relative">
        <Search
          className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 dark:text-slate-500"
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
          placeholder={`Active: ${selectedSymbol} | Search Symbol or Name...`}
          className="w-full pl-10 pr-10 py-2 rounded-lg border border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 text-sm font-medium focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 dark:focus:ring-emerald-500/50 dark:focus:border-emerald-500 transition-all outline-none"
        />
        {loading && (
          <Loader2
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-emerald-500 animate-spin"
            size={18}
          />
        )}
        {!loading && searchQuery && (
          <button
            onClick={() => {
              setSearchQuery('');
              setResults([]);
            }}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {showDropdown && (searchQuery.trim().length > 0) && (
        <div className="absolute z-50 w-full mt-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-xl max-h-72 overflow-y-auto">
          {results.length > 0 ? (
            <div className="py-1">
              {results.map((item, index) => (
                <button
                  key={item.symbol}
                  onClick={() => handleSelect(item.symbol)}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  className={`w-full px-4 py-2.5 text-left transition-colors flex items-center gap-3 border-b border-slate-50 dark:border-slate-800/40 last:border-b-0 ${
                    index === highlightedIndex
                      ? 'bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-400'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/50'
                  }`}
                >
                  <TrendingUp size={15} className="flex-shrink-0 text-slate-400" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm truncate">{item.symbol}</span>
                      <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 font-mono">
                        {item.exchange}
                      </span>
                    </div>
                    {item.company_name && (
                      <div className="text-xs text-slate-400 dark:text-slate-500 truncate mt-0.5">
                        {item.company_name}
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="px-4 py-3.5 text-sm text-slate-500 dark:text-slate-400 text-center font-medium">
              {loading ? 'Searching NIFTY 500...' : `No stocks found matching "${searchQuery}"`}
            </div>
          )}
          {error && (
            <div className="px-4 py-2 text-xs text-red-500 bg-red-50 dark:bg-red-950/20 border-t border-red-100 dark:border-red-900/30 text-center">
              {error}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default GlobalSymbolSearch;
