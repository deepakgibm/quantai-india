import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { api } from '../services/api';
import { useGlobalSymbol } from '../contexts/GlobalSymbolContext';
import { Page } from '../types';
import { TrendingUp, TrendingDown, ArrowLeft, Loader2, Search, Info, ZoomIn, ZoomOut, Zap, LayoutGrid } from 'lucide-react';
import ErrorCard from '../components/ErrorCard';

interface TreemapNode {
  name: string;
  value: number; // market_cap
  colorValue: number; // change_pct / score
  symbol?: string;
  company_name?: string;
  price?: number;
  change_pct?: number;
  volume?: number;
  children?: TreemapNode[];
  x?: number;
  y?: number;
  width?: number;
  height?: number;
}

interface SectorHeatmapPageProps {
  onNavigate?: (page: Page) => void;
  isWidget?: boolean;
}

// Slice-and-dice treemap partitioner
const computeTreemapLayout = (
  node: TreemapNode,
  x: number,
  y: number,
  width: number,
  height: number
) => {
  node.x = x;
  node.y = y;
  node.width = width;
  node.height = height;

  if (node.children && node.children.length > 0) {
    const totalValue = node.children.reduce((sum, child) => sum + child.value, 0);
    let currentX = x;
    let currentY = y;

    const isHorizontal = width > height;

    node.children.forEach(child => {
      const percentage = totalValue > 0 ? child.value / totalValue : 0;

      if (isHorizontal) {
        const childWidth = width * percentage;
        computeTreemapLayout(child, currentX, y, childWidth, height);
        currentX += childWidth;
      } else {
        const childHeight = height * percentage;
        computeTreemapLayout(child, x, currentY, width, childHeight);
        currentY += childHeight;
      }
    });
  }
};

const getColorForValue = (value: number, mode: string) => {
  if (mode === 'performance' || mode === 'momentum' || mode === 'relative_strength') {
    const limit = 3.0; // 3% is full intensity
    const norm = Math.max(-1, Math.min(1, value / limit));
    if (norm > 0) {
      // Interpolate Slate (15, 23, 42) to Emerald Green (16, 185, 129)
      const r = Math.round(15 + (16 - 15) * norm);
      const g = Math.round(23 + (185 - 23) * norm);
      const b = Math.round(42 + (129 - 42) * norm);
      return `rgb(${r}, ${g}, ${b})`;
    } else {
      // Interpolate Slate (15, 23, 42) to Rose Red (244, 63, 94)
      const absNorm = Math.abs(norm);
      const r = Math.round(15 + (244 - 15) * absNorm);
      const g = Math.round(23 + (63 - 23) * absNorm);
      const b = Math.round(42 + (94 - 42) * absNorm);
      return `rgb(${r}, ${g}, ${b})`;
    }
  } else if (mode === 'volatility') {
    // Slate (15, 23, 42) to Orange (249, 115, 22)
    const norm = Math.max(0, Math.min(1, value / 6.0));
    const r = Math.round(15 + (249 - 15) * norm);
    const g = Math.round(23 + (115 - 23) * norm);
    const b = Math.round(42 + (22 - 42) * norm);
    return `rgb(${r}, ${g}, ${b})`;
  } else {
    // mode === 'delivery'
    // Slate (15, 23, 42) to Cyan (6, 182, 212)
    const norm = Math.max(0, Math.min(1, (value - 30) / 60));
    const r = Math.round(15 + (6 - 15) * norm);
    const g = Math.round(23 + (182 - 23) * norm);
    const b = Math.round(42 + (212 - 42) * norm);
    return `rgb(${r}, ${g}, ${b})`;
  }
};

export const SectorHeatmapPage: React.FC<SectorHeatmapPageProps> = ({ onNavigate, isWidget = false }) => {
  const { setSelectedSymbol } = useGlobalSymbol();
  const [heatmapData, setHeatmapData] = useState<any>(null);
  const [mode, setMode] = useState<string>('performance');
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{
    symbol: string;
    name: string;
    price: number;
    market_cap: number;
    change_pct: number;
    value: number;
    sector: string;
    x: number;
    y: number;
  } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 1000, height: 550 });

  // Handle Container Resizing
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(entries => {
      for (let entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({
          width: Math.max(width, 300),
          height: Math.max(height, 350)
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Fetch Heatmap API
  const fetchHeatmap = async (activeMode: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getHeatmapData(activeMode);
      if (data && data.status === 'success') {
        setHeatmapData(data);
      } else {
        setError('Failed to compute market heatmap hierarchy.');
      }
    } catch (err: any) {
      console.error('[SectorHeatmapPage] Fetch error:', err);
      setError(err.message || 'Failed to fetch heatmap data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHeatmap(mode);
  }, [mode]);

  // Compute Layout when dimensions or data changes
  const computedRoot = useMemo(() => {
    if (!heatmapData || !heatmapData.sectors || heatmapData.sectors.length === 0) return null;

    const root: TreemapNode = {
      name: 'Root',
      value: heatmapData.sectors.reduce((sum: number, s: any) => sum + s.total_market_cap, 0),
      colorValue: 0,
      children: heatmapData.sectors.map((s: any) => ({
        name: s.name,
        value: s.total_market_cap,
        colorValue: s.avg_value,
        children: s.stocks.map((st: any) => ({
          name: st.symbol,
          symbol: st.symbol,
          company_name: st.name,
          price: st.price,
          value: st.market_cap,
          colorValue: st.value,
          change_pct: st.change_pct,
          volume: st.volume
        }))
      }))
    };

    // Calculate layout for all sectors
    computeTreemapLayout(root, 0, 0, dimensions.width, dimensions.height);

    // Calculate nested layouts
    root.children?.forEach(sector => {
      if (sector.children && sector.x !== undefined && sector.y !== undefined && sector.width !== undefined && sector.height !== undefined) {
        const padTop = sector.width > 120 && sector.height > 60 ? 24 : 4; // leave margin for header if sector is large enough
        const padSide = 3;
        const padBot = 3;

        const targetX = sector.x + padSide;
        const targetY = sector.y + padTop;
        const targetW = Math.max(1, sector.width - padSide * 2);
        const targetH = Math.max(1, sector.height - (padTop + padBot));

        const sectorRoot: TreemapNode = {
          name: sector.name,
          value: sector.value,
          colorValue: sector.colorValue,
          children: sector.children
        };

        computeTreemapLayout(sectorRoot, targetX, targetY, targetW, targetH);
      }
    });

    return root;
  }, [heatmapData, dimensions]);

  // Zoomed Sector Layout
  const computedZoomedSector = useMemo(() => {
    if (!selectedSector || !heatmapData || !heatmapData.sectors) return null;
    const sector = heatmapData.sectors.find((s: any) => s.name === selectedSector);
    if (!sector) return null;

    const sectorRoot: TreemapNode = {
      name: sector.name,
      value: sector.total_market_cap,
      colorValue: sector.avg_value,
      children: sector.stocks.map((st: any) => ({
        name: st.symbol,
        symbol: st.symbol,
        company_name: st.name,
        price: st.price,
        value: st.market_cap,
        colorValue: st.value,
        change_pct: st.change_pct,
        volume: st.volume
      }))
    };

    computeTreemapLayout(sectorRoot, 0, 0, dimensions.width, dimensions.height);
    return sectorRoot;
  }, [selectedSector, heatmapData, dimensions]);

  // Click on a stock tile
  const handleStockClick = useCallback((symbol: string) => {
    setSelectedSymbol(symbol);
    if (!isWidget && onNavigate) {
      onNavigate(Page.VOLATILITY_DASHBOARD);
    }
  }, [setSelectedSymbol, onNavigate, isWidget]);

  const handleSectorClick = (sectorName: string) => {
    setSelectedSector(sectorName);
    setTooltip(null);
  };

  const handleMouseMove = (e: React.MouseEvent, node: TreemapNode, sectorName: string) => {
    if (!node.symbol) return;
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltip({
      symbol: node.symbol,
      name: node.company_name || '',
      price: node.price || 0,
      market_cap: node.value,
      change_pct: node.change_pct || 0,
      value: node.colorValue,
      sector: sectorName,
      x: e.clientX - rect.left + 15,
      y: e.clientY - rect.top + 15
    });
  };

  const handleMouseLeave = () => {
    setTooltip(null);
  };

  // Find matching symbols for highlighting
  const isQueryMatching = (symbol: string) => {
    if (!searchQuery.trim()) return false;
    return symbol.toUpperCase().includes(searchQuery.toUpperCase());
  };

  if (loading && !heatmapData) {
    return (
      <div className="space-y-6">
        {!isWidget && (
          <div className="pb-4 border-b border-slate-800">
            <h1 className="text-3xl font-display font-bold text-slate-100">Market Heatmap</h1>
            <p className="text-slate-500 font-medium">Loading sector maps and components...</p>
          </div>
        )}
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="w-10 h-10 text-emerald-500 animate-spin" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        {!isWidget && (
          <div className="pb-4 border-b border-slate-800">
            <h1 className="text-3xl font-display font-bold text-slate-100">Market Heatmap</h1>
            <p className="text-slate-500">Error loading map</p>
          </div>
        )}
        <ErrorCard message={error} onRetry={() => fetchHeatmap(mode)} title="Heatmap Compute Error" />
      </div>
    );
  }

  // Active Layout Nodes
  const rootNode = selectedSector ? computedZoomedSector : computedRoot;

  return (
    <div className="space-y-6">
      {/* Title Header */}
      {!isWidget ? (
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-3">
              {selectedSector ? (
                <button
                  onClick={() => setSelectedSector(null)}
                  className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors text-sm font-semibold"
                >
                  <ArrowLeft size={16} /> All Sectors
                </button>
              ) : (
                <h1 className="text-2xl font-bold tracking-tight text-white font-display">NIFTY 500 Heatmap</h1>
              )}
              {selectedSector && (
                <span className="text-lg font-bold text-white font-display">
                  &bull; {selectedSector}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 font-semibold mt-1">
              Grouped by sector, sized by market cap, colored by chosen metric.
            </p>
          </div>

          {/* Toolbar controls */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Mode Selector */}
            <div className="flex rounded-lg border border-slate-800 bg-slate-950 p-0.5">
              {['performance', 'volatility', 'momentum', 'delivery', 'relative_strength'].map(m => (
                <button
                  key={m}
                  onClick={() => {
                    setMode(m);
                    setTooltip(null);
                  }}
                  className={`px-2.5 py-1 rounded text-[10px] uppercase font-bold tracking-wider transition-all ${
                    mode === m
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {m.replace('_', ' ')}
                </button>
              ))}
            </div>

            {/* Search box to highlight stocks */}
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" size={13} />
              <input
                type="text"
                placeholder="Highlight stock..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-7 pr-3 py-1 bg-slate-950 border border-slate-800 rounded-lg text-[11px] text-slate-200 focus:outline-none focus:border-emerald-500 w-36 outline-none"
              />
            </div>
          </div>
        </div>
      ) : (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
          <div className="flex items-center gap-2">
            {selectedSector ? (
              <button
                onClick={() => setSelectedSector(null)}
                className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors text-xs font-semibold"
              >
                <ArrowLeft size={14} /> All Sectors
              </button>
            ) : (
              <h3 className="text-sm font-bold text-white font-display flex items-center gap-2">
                <LayoutGrid size={15} className="text-emerald-500" /> Market Heatmap (NIFTY 505)
              </h3>
            )}
            {selectedSector && (
              <span className="text-xs font-bold text-white font-display">
                &bull; {selectedSector}
              </span>
            )}
          </div>

          {/* Toolbar controls */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Mode Selector */}
            <div className="flex rounded-lg border border-slate-800 bg-slate-950 p-0.5">
              {['performance', 'volatility', 'momentum', 'delivery', 'relative_strength'].map(m => (
                <button
                  key={m}
                  onClick={() => {
                    setMode(m);
                    setTooltip(null);
                  }}
                  className={`px-2 py-0.5 rounded text-[9px] uppercase font-bold tracking-wider transition-all ${
                    mode === m
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {m.replace('_', ' ')}
                </button>
              ))}
            </div>

            {/* Search box to highlight stocks */}
            <div className="relative">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-500" size={11} />
              <input
                type="text"
                placeholder="Highlight stock..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-6 pr-2 py-0.5 bg-slate-950 border border-slate-800 rounded text-[9px] text-slate-200 focus:outline-none focus:border-emerald-500 w-28 outline-none"
              />
            </div>
          </div>
        </div>
      )}

      {/* SVG Canvas Map */}
      <div className="relative bg-slate-950/80 rounded-2xl border border-slate-900 p-2 shadow-2xl overflow-hidden min-h-[500px]">
        {/* Dimensions Container */}
        <div ref={containerRef} className="w-full h-full relative" style={{ minHeight: '520px' }}>
          {rootNode && rootNode.children && rootNode.children.length > 0 ? (
            <svg
              width={dimensions.width}
              height={dimensions.height}
              className="select-none overflow-hidden rounded-xl"
            >
              {selectedSector ? (
                // Zoomed Sector View: Render leaf nodes directly
                rootNode.children.map(stock => {
                  const tileColor = getColorForValue(stock.colorValue, mode);
                  const isHighlighted = isQueryMatching(stock.symbol || '');
                  const showLabel = (stock.width || 0) > 40 && (stock.height || 0) > 28;
                  const showName = (stock.width || 0) > 85 && (stock.height || 0) > 40;

                  return (
                    <g
                      key={stock.name}
                      transform={`translate(${stock.x}, ${stock.y})`}
                      className="cursor-pointer group"
                      onClick={() => handleStockClick(stock.symbol || '')}
                      onMouseMove={e => handleMouseMove(e, stock, selectedSector)}
                      onMouseLeave={handleMouseLeave}
                    >
                      <rect
                        width={stock.width}
                        height={stock.height}
                        fill={tileColor}
                        stroke="#090d16"
                        strokeWidth={1.5}
                        className={`transition-all duration-300 group-hover:brightness-125 ${
                          isHighlighted ? 'stroke-yellow-400 stroke-[3px]' : ''
                        }`}
                      />
                      {showLabel && (
                        <text
                          x={(stock.width || 0) / 2}
                          y={showName ? ((stock.height || 0) / 2) - 4 : (stock.height || 0) / 2}
                          textAnchor="middle"
                          alignmentBaseline="middle"
                          fill="#ffffff"
                          fontSize={Math.min(13, Math.max(8, (stock.width || 0) / 7))}
                          fontWeight="bold"
                        >
                          {stock.symbol}
                        </text>
                      )}
                      {showName && (
                        <text
                          x={(stock.width || 0) / 2}
                          y={((stock.height || 0) / 2) + 10}
                          textAnchor="middle"
                          alignmentBaseline="middle"
                          fill="#94a3b8"
                          fontSize={8}
                        >
                          {stock.colorValue >= 0 ? '+' : ''}{stock.colorValue.toFixed(1)}%
                        </text>
                      )}
                    </g>
                  );
                })
              ) : (
                // Full Market Nested Sector View
                computedRoot?.children?.map(sector => {
                  const sectorLabelVisible = (sector.width || 0) > 80 && (sector.height || 0) > 40;
                  
                  return (
                    <g key={sector.name}>
                      {/* Sector group boundary */}
                      <rect
                        x={sector.x}
                        y={sector.y}
                        width={sector.width}
                        height={sector.height}
                        fill="transparent"
                        stroke="#1e293b"
                        strokeWidth={2}
                      />

                      {/* Sector label */}
                      {sectorLabelVisible && sector.x !== undefined && sector.y !== undefined && (
                        <text
                          x={sector.x + 6}
                          y={sector.y + 15}
                          fill="#94a3b8"
                          fontSize={10}
                          fontWeight="bold"
                          className="uppercase font-sans cursor-pointer hover:fill-white hover:underline transition-colors"
                          onClick={() => handleSectorClick(sector.name)}
                        >
                          {sector.name} ({sector.colorValue >= 0 ? '+' : ''}{sector.colorValue.toFixed(1)}%)
                        </text>
                      )}

                      {/* Sector stocks (leaves) */}
                      {sector.children?.map(stock => {
                        const tileColor = getColorForValue(stock.colorValue, mode);
                        const isHighlighted = isQueryMatching(stock.symbol || '');
                        const showLabel = (stock.width || 0) > 30 && (stock.height || 0) > 18;
                        const showSubLabel = (stock.width || 0) > 45 && (stock.height || 0) > 30;

                        return (
                          <g
                            key={stock.symbol}
                            transform={`translate(${stock.x}, ${stock.y})`}
                            className="cursor-pointer group"
                            onClick={() => handleStockClick(stock.symbol || '')}
                            onMouseMove={e => handleMouseMove(e, stock, sector.name)}
                            onMouseLeave={handleMouseLeave}
                          >
                            <rect
                              width={stock.width}
                              height={stock.height}
                              fill={tileColor}
                              stroke="#090d16"
                              strokeWidth={1}
                              className={`transition-all duration-300 group-hover:brightness-125 ${
                                isHighlighted ? 'stroke-yellow-400 stroke-2' : ''
                              }`}
                            />
                            {showLabel && (
                              <text
                                x={(stock.width || 0) / 2}
                                y={showSubLabel ? ((stock.height || 0) / 2) - 4 : (stock.height || 0) / 2}
                                textAnchor="middle"
                                alignmentBaseline="middle"
                                fill="#ffffff"
                                fontSize={Math.min(10, Math.max(7, (stock.width || 0) / 6))}
                                fontWeight="bold"
                              >
                                {stock.symbol}
                              </text>
                            )}
                            {showSubLabel && (
                              <text
                                x={(stock.width || 0) / 2}
                                y={((stock.height || 0) / 2) + 7}
                                textAnchor="middle"
                                alignmentBaseline="middle"
                                fill="#cbd5e1"
                                opacity={0.8}
                                fontSize={7}
                                fontWeight="semibold"
                              >
                                {stock.change_pct !== undefined ? `${stock.change_pct >= 0 ? '+' : ''}${stock.change_pct.toFixed(1)}%` : ''}
                              </text>
                            )}
                          </g>
                        );
                      })}
                    </g>
                  );
                })
              )}
            </svg>
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-slate-500 font-medium">
              No sector nodes loaded.
            </div>
          )}

          {/* Floating Tooltip inside container */}
          {tooltip && (
            <div
              className="absolute z-40 bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs shadow-xl text-slate-100 max-w-[200px] pointer-events-none"
              style={{ left: tooltip.x, top: tooltip.y }}
            >
              <div className="font-bold flex items-center justify-between gap-2 border-b border-slate-800 pb-1.5 mb-1.5">
                <span className="text-sm text-white">{tooltip.symbol}</span>
                <span className="text-[10px] text-slate-500 font-medium truncate max-w-[80px]">
                  {tooltip.sector}
                </span>
              </div>
              <div className="text-[10px] text-slate-400 font-medium truncate mb-1">
                {tooltip.name}
              </div>
              <div className="space-y-1 mt-1 font-mono">
                <div className="flex justify-between gap-4">
                  <span className="text-slate-500 font-semibold">Price:</span>
                  <span className="font-bold text-white">₹{tooltip.price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-slate-500 font-semibold">Change:</span>
                  <span className={`font-bold ${tooltip.change_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {tooltip.change_pct >= 0 ? '+' : ''}{tooltip.change_pct.toFixed(2)}%
                  </span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-slate-500 font-semibold">
                    {mode.replace('_', ' ')}:
                  </span>
                  <span className="font-bold text-emerald-400">{tooltip.value.toFixed(2)}</span>
                </div>
                <div className="flex justify-between gap-4 pt-1 border-t border-slate-800/40 text-[9px]">
                  <span className="text-slate-500 font-semibold">Mkt Cap:</span>
                  <span className="text-slate-400">
                    ₹{(tooltip.market_cap / 10000000).toFixed(0)} Cr
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SectorHeatmapPage;
