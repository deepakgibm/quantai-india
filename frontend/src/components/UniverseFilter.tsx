import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Globe, RefreshCw } from 'lucide-react';
import { useGlobalSymbol } from '../contexts/GlobalSymbolContext';
import { UNIVERSE_OPTIONS } from '../types/indices';

interface UniverseFilterProps {
  size?: 'sm' | 'md';
  showCount?: boolean;
  className?: string;
  onChange?: (universe: string) => void;
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
}) => {
  const { selectedUniverse, setSelectedUniverse, availableIndices, indicesLoading } = useGlobalSymbol();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

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

  // Group options by category
  const grouped: Record<string, typeof UNIVERSE_OPTIONS> = {};
  UNIVERSE_OPTIONS.forEach(opt => {
    const cat = opt.category === 'Smallcap' ? 'Midcap' : opt.category;
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(opt);
  });

  const isSmall = size === 'sm';

  return (
    <div ref={ref} className={`relative inline-block ${className}`}>
      {/* Trigger Button */}
      <button
        onClick={() => setOpen(prev => !prev)}
        className={`
          flex items-center gap-2 rounded-lg border font-medium transition-all duration-200
          ${isSmall
            ? 'px-3 py-1.5 text-xs'
            : 'px-4 py-2 text-sm'}
          bg-slate-800/80 border-slate-600/60 text-slate-200
          hover:bg-slate-700/80 hover:border-violet-500/60 hover:text-white
          ${open ? 'border-violet-500/80 bg-slate-700/80 ring-1 ring-violet-500/30' : ''}
        `}
      >
        <Globe size={isSmall ? 12 : 14} className="text-violet-400" />
        <span className="max-w-[140px] truncate">{displayLabel}</span>
        {showCount && selectedCount !== null && (
          <span className="text-slate-500 text-[10px]">({selectedCount})</span>
        )}
        {indicesLoading ? (
          <RefreshCw size={10} className="animate-spin text-slate-500" />
        ) : (
          <ChevronDown
            size={12}
            className={`text-slate-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          />
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div
          className="
            absolute z-50 mt-1 w-64 rounded-xl border border-slate-600/60
            bg-slate-900/95 backdrop-blur-md shadow-2xl shadow-black/50
            ring-1 ring-violet-500/10
            overflow-hidden
          "
          style={{ top: '100%', left: 0 }}
        >
          {/* All Stocks option */}
          <div className="p-1.5 border-b border-slate-700/60">
            <button
              onClick={() => handleSelect('ALL')}
              className={`
                w-full text-left px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                ${selectedUniverse === 'ALL'
                  ? 'bg-violet-600/30 text-violet-300 border border-violet-500/30'
                  : 'text-slate-300 hover:bg-slate-700/60 hover:text-white'}
              `}
            >
              🌐 All Stocks
              <span className="ml-1 text-slate-500 text-[10px]">(3200+)</span>
            </button>
          </div>

          <div className="max-h-72 overflow-y-auto py-1">
            {CATEGORY_ORDER.filter(cat => grouped[cat]).map(cat => (
              <div key={cat}>
                {/* Category header */}
                <div className="px-3 py-1 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                  {CATEGORY_LABELS[cat] || cat}
                </div>
                {grouped[cat].map(opt => {
                  const liveData = availableIndices.find(i => i.index_name === opt.value);
                  const count = liveData?.constituent_count;
                  const isSelected = selectedUniverse === opt.value;
                  return (
                    <button
                      key={opt.value}
                      onClick={() => handleSelect(opt.value)}
                      className={`
                        w-full text-left px-3 py-1.5 text-xs transition-colors flex items-center justify-between
                        ${isSelected
                          ? 'bg-violet-600/25 text-violet-300'
                          : 'text-slate-300 hover:bg-slate-700/50 hover:text-white'}
                      `}
                    >
                      <span className="truncate">{opt.label}</span>
                      {count ? (
                        <span className="text-slate-500 text-[10px] ml-2 flex-shrink-0">{count}</span>
                      ) : null}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="px-3 py-1.5 border-t border-slate-700/60 text-[10px] text-slate-500 flex items-center gap-1">
            <span>Last refreshed from NSE •</span>
            <a
              href="/index-management"
              className="text-violet-400 hover:text-violet-300"
              onClick={() => setOpen(false)}
            >
              Manage →
            </a>
          </div>
        </div>
      )}
    </div>
  );
};

export default UniverseFilter;
