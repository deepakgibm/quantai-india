import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Globe, Search, X, Check, RefreshCw } from 'lucide-react';
import { useGlobalSymbol } from '../contexts/GlobalSymbolContext';
import { UNIVERSE_OPTIONS } from '../types/indices';

interface UniverseFilterProps {
  size?: 'sm' | 'md';
  showCount?: boolean;
  className?: string;
  onChange?: (universe: string) => void;
  align?: 'left' | 'right';
}

const CATEGORY_ORDER = ['Broad Market', 'Sector', 'Midcap', 'Smallcap'];
const CATEGORY_LABELS: Record<string, string> = {
  'Broad Market': '📈 Broad Market',
  'Sector': '🏭 Sector Indices',
  'Midcap': '📊 Mid & Small Cap',
  'Smallcap': '📊 Mid & Small Cap',
};

const UniverseFilter: React.FC<UniverseFilterProps> = ({
  size = 'sm',
  showCount = true,
  className = '',
  onChange,
  align = 'right',
}) => {
  const { selectedUniverse, setSelectedUniverse, availableIndices, indicesLoading } = useGlobalSymbol();
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Keyboard navigation & Escape closer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!open) return;
      if (e.key === 'Escape') {
        setOpen(false);
        return;
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open]);

  // Focus input when dropdown opens
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setSearchQuery('');
      setFocusedIndex(-1);
    }
  }, [open]);

  const handleSelect = (value: string) => {
    setSelectedUniverse(value);
    onChange?.(value);
    setOpen(false);
  };

  // Build display label from either availableIndices (live) or UNIVERSE_OPTIONS (static)
  const displayLabel = (() => {
    if (selectedUniverse === 'ALL') return 'All Stocks';
    const live = availableIndices.find(i => i.index_name === selectedUniverse);
    if (live) return live.display_name;
    const stat = UNIVERSE_OPTIONS.find(o => o.value === selectedUniverse);
    return stat?.label ?? selectedUniverse;
  })();

  // Constituent count for the selected universe
  const selectedCount = (() => {
    const live = availableIndices.find(i => i.index_name === selectedUniverse);
    return live?.constituent_count ?? null;
  })();

  // Filter options based on search query
  const filteredOptions = UNIVERSE_OPTIONS.filter(opt =>
    opt.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
    opt.value.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group options by category
  const grouped: Record<string, typeof UNIVERSE_OPTIONS> = {};
  filteredOptions.forEach(opt => {
    const cat = opt.category === 'Smallcap' ? 'Midcap' : opt.category;
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(opt);
  });

  // Flattened options list for keyboard navigation
  const flatOptionsList = [
    ...(searchQuery === '' || 'all stocks'.includes(searchQuery.toLowerCase())
      ? [{ label: 'All Stocks', value: 'ALL', category: 'Broad Market' }]
      : []),
    ...CATEGORY_ORDER.filter(cat => grouped[cat]).flatMap(cat => grouped[cat])
  ];

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setFocusedIndex(prev => (prev + 1) % flatOptionsList.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setFocusedIndex(prev => (prev - 1 + flatOptionsList.length) % flatOptionsList.length);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (focusedIndex >= 0 && focusedIndex < flatOptionsList.length) {
        handleSelect(flatOptionsList[focusedIndex].value);
      }
    }
  };

  const isSmall = size === 'sm';

  return (
    <div ref={ref} className={`relative inline-block ${className}`}>
      {/* Trigger Button */}
      <button
        onClick={() => setOpen(prev => !prev)}
        className={`
          flex items-center gap-2.5 rounded-xl border font-bold transition-all duration-200
          ${isSmall
            ? 'px-4 py-2.5 text-xs'
            : 'px-5 py-3 text-sm'}
          bg-[#0E1425]/90 border-blue-400/10 text-slate-200
          hover:bg-[#0E1425] hover:border-blue-400/30 hover:text-white
          shadow-lg shadow-black/20 hover:shadow-blue-500/5
          ${open ? 'border-blue-400/35 bg-[#0E1425] ring-2 ring-blue-500/10' : ''}
        `}
      >
        <Globe size={isSmall ? 13 : 15} className="text-blue-400" />
        <span className="max-w-[140px] truncate">{displayLabel}</span>
        {showCount && selectedCount !== null && (
          <span className="text-slate-400 text-[10px] font-mono bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-400/10">
            {selectedCount}
          </span>
        )}
        {indicesLoading ? (
          <RefreshCw size={11} className="animate-spin text-slate-500" />
        ) : (
          <ChevronDown
            size={12}
            className={`text-slate-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          />
        )}
      </button>

      {/* Dropdown Container */}
      {open && (
        <div
          className={`
            absolute z-[999] mt-2 w-72 rounded-2xl border border-blue-400/20
            bg-[#0E1425]/95 backdrop-blur-xl shadow-2xl shadow-black/80
            ring-1 ring-blue-500/10 overflow-hidden flex flex-col
            ${align === 'right' ? 'right-0' : 'left-0'}
          `}
          style={{ top: '100%' }}
          onKeyDown={handleKeyDown}
        >
          {/* Search Header */}
          <div className="p-3 border-b border-blue-400/10 flex items-center gap-2 bg-slate-950/20">
            <Search size={14} className="text-slate-500 flex-shrink-0" />
            <input
              ref={inputRef}
              type="text"
              placeholder="Search index or sector..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full bg-transparent border-none text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-0 p-0"
            />
            {searchQuery && (
              <button 
                onClick={() => setSearchQuery('')}
                className="p-0.5 hover:bg-slate-800 rounded-md text-slate-400 hover:text-white"
              >
                <X size={12} />
              </button>
            )}
          </div>

          {/* Options List */}
          <div className="max-h-64 overflow-y-auto py-1 custom-scrollbar">
            {/* All Stocks option (filtered or top) */}
            {(searchQuery === '' || 'all stocks'.includes(searchQuery.toLowerCase())) && (
              <div className="px-1 py-0.5 border-b border-blue-400/5">
                {(() => {
                  const isSelected = selectedUniverse === 'ALL';
                  const isFocused = flatOptionsList[focusedIndex]?.value === 'ALL';
                  return (
                    <button
                      onClick={() => handleSelect('ALL')}
                      className={`
                        w-full text-left px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-between
                        ${isSelected
                          ? 'bg-blue-600/20 text-blue-300 border border-blue-500/20'
                          : isFocused 
                            ? 'bg-slate-800/60 text-white'
                            : 'text-slate-300 hover:bg-slate-800/40 hover:text-white'}
                      `}
                    >
                      <span className="flex items-center gap-1.5">🌐 All Stocks</span>
                      {isSelected ? (
                        <Check size={12} className="text-blue-400" />
                      ) : (
                        <span className="text-slate-500 text-[10px] font-mono">3200+</span>
                      )}
                    </button>
                  );
                })()}
              </div>
            )}

            {filteredOptions.length === 0 ? (
              <div className="px-4 py-8 text-center text-xs text-slate-500">
                No universes match "{searchQuery}"
              </div>
            ) : (
              CATEGORY_ORDER.filter(cat => grouped[cat]).map(cat => (
                <div key={cat} className="space-y-0.5 mt-1.5">
                  {/* Category Header */}
                  <div className="px-3.5 py-1 text-[9px] font-black text-slate-500 uppercase tracking-widest bg-slate-900/10">
                    {CATEGORY_LABELS[cat] || cat}
                  </div>
                  
                  {/* Category Options */}
                  {grouped[cat].map(opt => {
                    const liveData = availableIndices.find(i => i.index_name === opt.value);
                    const count = liveData?.constituent_count;
                    const isSelected = selectedUniverse === opt.value;
                    const optionIndex = flatOptionsList.findIndex(x => x.value === opt.value);
                    const isFocused = optionIndex === focusedIndex;

                    return (
                      <button
                        key={opt.value}
                        onClick={() => handleSelect(opt.value)}
                        className={`
                          w-full text-left px-3.5 py-2 text-xs transition-all flex items-center justify-between
                          ${isSelected
                            ? 'bg-blue-600/15 text-blue-300 font-bold border-l-2 border-blue-500'
                            : isFocused
                              ? 'bg-slate-800/60 text-white'
                              : 'text-slate-300 hover:bg-slate-850/40 hover:text-white'}
                        `}
                      >
                        <span className="truncate">{opt.label}</span>
                        {isSelected ? (
                          <Check size={12} className="text-blue-400 flex-shrink-0" />
                        ) : count ? (
                          <span className="text-slate-500 text-[10px] font-mono flex-shrink-0">{count}</span>
                        ) : null}
                      </button>
                    );
                  })}
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2.5 border-t border-blue-400/10 text-[10px] text-slate-500 bg-slate-950/20 flex items-center justify-between">
            <span>Constituents from NSE</span>
            <a
              href="/index-management"
              className="text-blue-400 hover:text-blue-350 hover:underline font-bold transition-all"
              onClick={() => setOpen(false)}
            >
              Manage Universe →
            </a>
          </div>
        </div>
      )}
    </div>
  );
};

export default UniverseFilter;
