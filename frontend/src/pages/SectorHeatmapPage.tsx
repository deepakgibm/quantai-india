import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { api } from '../services/api';
import { useGlobalSymbol } from '../contexts/GlobalSymbolContext';
import { Page } from '../types';
import { 
  TrendingUp, TrendingDown, ArrowLeft, Loader2, Search, Info, ZoomIn, 
  ZoomOut, Zap, LayoutGrid, Sparkles, BarChart2, Calendar, ShieldAlert 
} from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, CartesianGrid, Cell } from 'recharts';
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

// Normalize sector names to keep categories clean
const normalizeSector = (sec: string | null): string => {
  if (!sec) return 'Others';
  const lower = sec.toLowerCase().trim();

  if (lower.includes('financial') || lower.includes('bank') || lower.includes('insurance') || lower.includes('credit')) return 'Financial Services';
  if (lower.includes('it') || lower.includes('software') || lower.includes('computer') || lower.includes('technology')) return 'Technology';
  if (lower.includes('auto') || lower.includes('car') || lower.includes('vehicle') || lower.includes('automotive')) return 'Automobile';
  if (lower.includes('pharma') || lower.includes('health') || lower.includes('biotech') || lower.includes('medical') || lower.includes('hospital')) return 'Healthcare';
  if (lower.includes('consumer') || lower.includes('fmcg') || lower.includes('food') || lower.includes('beverage') || lower.includes('household')) return 'Consumer Goods';
  if (lower.includes('power') || lower.includes('energy') || lower.includes('oil') || lower.includes('gas') || lower.includes('petro') || lower.includes('utilities')) return 'Energy & Utilities';
  if (lower.includes('metal') || lower.includes('steel') || lower.includes('mining') || lower.includes('aluminium')) return 'Metals & Mining';
  if (lower.includes('construction') || lower.includes('infra') || lower.includes('cement') || lower.includes('real estate') || lower.includes('building')) return 'Construction & Materials';
  if (lower.includes('telecom') || lower.includes('communication') || lower.includes('media') || lower.includes('entertainment')) return 'Telecommunication';
  if (lower.includes('chemical') || lower.includes('fertilizer') || lower.includes('paints')) return 'Chemicals';
  if (lower.includes('textile') || lower.includes('apparel') || lower.includes('fashion') || lower.includes('garments')) return 'Textiles';
  if (lower.includes('retail') || lower.includes('ecommerce')) return 'Retail';
  if (lower.includes('logistics') || lower.includes('transport') || lower.includes('shipping')) return 'Logistics';

  return 'Miscellaneous';
};

export const SectorHeatmapPage: React.FC<SectorHeatmapPageProps> = React.memo(({ onNavigate, isWidget = false }) => {
  const { setSelectedSymbol } = useGlobalSymbol();
  
  // Views: heatmap or analysis
  const [viewMode, setViewMode] = useState<'heatmap' | 'analysis'>('heatmap');

  // Heatmap State
  const [heatmapData, setHeatmapData] = useState<any>(null);
  const [mode, setMode] = useState<string>('performance');
  const [timeframe, setTimeframe] = useState<string>(() => localStorage.getItem('sector_timeframe') || '1D');
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

  // Analysis State
  const [analysisData, setAnalysisData] = useState<any>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [selectedAnalysisSector, setSelectedAnalysisSector] = useState<string | null>(null);
  const [stockSearchQuery, setStockSearchQuery] = useState('');

  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 1000, height: 550 });
  const [showDebug, setShowDebug] = useState(false);
  const [lastRefreshTime, setLastRefreshTime] = useState<string>('');
  
  useEffect(() => {
    document.title = "Sector Heatmap & Analysis | QuantAI India";
  }, []);

  const changeTimeframe = (tf: string) => {
    setTimeframe(tf);
    localStorage.setItem('sector_timeframe', tf);
  };

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
  }, [viewMode]);

  // Fetch Heatmap API
  const fetchHeatmap = async (activeMode: string, activeTimeframe: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getHeatmapData(activeMode, activeTimeframe);
      
      const rawSectors = data?.sectors || [];
      const groupedMap = new Map<string, any>();
      
      rawSectors.forEach((s: any) => {
        const normName = normalizeSector(s.name);
        if (!groupedMap.has(normName)) {
          groupedMap.set(normName, {
            name: normName,
            total_market_cap: 0,
            avg_value: 0,
            stocks: []
          });
        }
        
        const group = groupedMap.get(normName);
        group.total_market_cap += s.total_market_cap || 0;
        group.stocks.push(...(s.stocks || []));
      });
      
      const groupedSectors = Array.from(groupedMap.values()).map(g => {
        if (g.stocks.length > 0 && g.total_market_cap > 0) {
          g.avg_value = g.stocks.reduce((acc: number, st: any) => acc + ((st.value || 0) * (st.market_cap || 0)), 0) / g.total_market_cap;
        }
        return g;
      });

      if (data && data.status === 'success') {
        setHeatmapData({ ...data, sectors: groupedSectors });
        setLastRefreshTime(new Date().toLocaleTimeString());
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

  // Fetch Sector Analysis API
  const fetchAnalysis = async (activeTimeframe: string) => {
    setAnalysisLoading(true);
    setAnalysisError(null);
    try {
      const data = await api.getSectorAnalysisData(activeTimeframe);
      if (data && data.status === 'success') {
        setAnalysisData(data);
      } else {
        setAnalysisError('Failed to fetch sector analysis metrics.');
      }
    } catch (err: any) {
      console.error('[SectorHeatmapPage] Fetch Analysis error:', err);
      setAnalysisError(err.message || 'Failed to fetch sector analysis.');
    } finally {
      setAnalysisLoading(false);
    }
  };

  useEffect(() => {
    if (viewMode === 'heatmap') {
      fetchHeatmap(mode, timeframe);
    } else {
      fetchAnalysis(timeframe);
    }
  }, [mode, timeframe, viewMode]);

  // COLOR GENERATOR
  const getColorForValue = (val: number, currentMode: string) => {
    if (currentMode === 'volatility') {
      // Volatility mapping (Purple hues)
      const absVal = Math.min(10, Math.max(0, val));
      const factor = absVal / 10;
      return `rgba(139, 92, 246, ${0.15 + factor * 0.85})`;
    } else if (currentMode === 'delivery') {
      // Delivery mapping (Cyan hues)
      const clamped = Math.min(100, Math.max(0, val));
      const factor = clamped / 100;
      return `rgba(6, 182, 212, ${0.2 + factor * 0.8})`;
    } else {
      // Return performance based (Green / Red hues)
      if (val > 0) {
        const intensity = Math.min(1.0, val / 3.5); // Max out at +3.5%
        return `rgba(16, 185, 129, ${0.15 + intensity * 0.85})`;
      } else if (val < 0) {
        const intensity = Math.min(1.0, Math.abs(val) / 3.5); // Max out at -3.5%
        return `rgba(239, 68, 68, ${0.15 + intensity * 0.85})`;
      }
      return '#1e293b'; // Slate 800 for flat
    }
  };

  // BUILD TREEMAP NODES
  const computedRoot = useMemo(() => {
    if (!heatmapData?.sectors) return null;

    const children: TreemapNode[] = heatmapData.sectors
      .filter((s: any) => s.stocks.length > 0)
      .map((s: any) => {
        const sectorValue = s.total_market_cap || 1;
        const sectorColorValue = s.avg_value || 0;

        const stockChildren: TreemapNode[] = s.stocks.map((st: any) => ({
          name: st.symbol,
          value: st.market_cap || 1,
          colorValue: st.value || 0,
          symbol: st.symbol,
          company_name: st.name,
          price: st.price,
          change_pct: st.change_pct,
          volume: st.volume
        }));

        return {
          name: s.name,
          value: sectorValue,
          colorValue: sectorColorValue,
          children: stockChildren
        };
      });

    const root: TreemapNode = {
      name: 'NIFTY 500',
      value: children.reduce((sum, c) => sum + c.value, 0),
      colorValue: 0,
      children
    };

    computeTreemapLayout(root, 0, 0, dimensions.width, dimensions.height);
    return root;
  }, [heatmapData, dimensions, mode]);

  // BUILD ZOOMED SECTOR NODES
  const computedZoomedSector = useMemo(() => {
    if (!selectedSector || !heatmapData?.sectors) return null;

    const sec = heatmapData.sectors.find((s: any) => s.name === selectedSector);
    if (!sec) return null;

    const children: TreemapNode[] = sec.stocks.map((st: any) => ({
      name: st.symbol,
      value: st.market_cap || 1,
      colorValue: st.value || 0,
      symbol: st.symbol,
      company_name: st.name,
      price: st.price,
      change_pct: st.change_pct,
      volume: st.volume
    }));

    const root: TreemapNode = {
      name: sec.name,
      value: children.reduce((sum, c) => sum + c.value, 0),
      colorValue: sec.avg_value || 0,
      children
    };

    computeTreemapLayout(root, 0, 0, dimensions.width, dimensions.height);
    return root;
  }, [heatmapData, selectedSector, dimensions, mode]);

  // Highlights stocks matching search query
  const isQueryMatching = useCallback((symbol: string) => {
    if (!searchQuery) return false;
    return symbol.toUpperCase().includes(searchQuery.toUpperCase());
  }, [searchQuery]);

  // Interactivity Actions
  const handleStockClick = (symbol: string) => {
    setSelectedSymbol(symbol);
    if (onNavigate) {
      onNavigate(Page.QUANT_WORKSPACE);
    }
  };

  const handleSectorClick = (sectorName: string) => {
    setSelectedSector(sectorName);
    setSearchQuery('');
  };

  const handleMouseMove = (e: React.MouseEvent, node: TreemapNode, sectorName: string) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left + 15;
    const y = e.clientY - rect.top + 15;
    
    setTooltip({
      symbol: node.symbol || '',
      name: node.company_name || '',
      price: node.price || 0,
      market_cap: node.value || 0,
      change_pct: node.change_pct || 0,
      value: node.colorValue || 0,
      sector: sectorName,
      x,
      y
    });
  };

  const handleMouseLeave = () => {
    setTooltip(null);
  };

  // Recharts Bar Data processing
  const chartData = useMemo(() => {
    if (!analysisData?.sectors) return [];
    return [...analysisData.sectors]
      .sort((a, b) => b.avg_return_timeframe - a.avg_return_timeframe)
      .map(s => ({
        name: s.sector,
        returnVal: s.avg_return_timeframe,
        stockCount: s.stock_count,
        valuation: s.valuation_rating
      }));
  }, [analysisData]);

  // Active analysis sector stocks details
  const filteredStocks = useMemo(() => {
    if (!analysisData?.sectors || !selectedAnalysisSector) return [];
    const secObj = analysisData.sectors.find((s: any) => s.sector === selectedAnalysisSector);
    if (!secObj?.stocks) return [];
    
    return secObj.stocks.filter((st: any) => 
      st.symbol.toUpperCase().includes(stockSearchQuery.toUpperCase()) ||
      st.company_name.toUpperCase().includes(stockSearchQuery.toUpperCase())
    );
  }, [analysisData, selectedAnalysisSector, stockSearchQuery]);

  return (
    <div className="space-y-6">
      {/* Top Banner Header */}
      {!isWidget && (
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight text-white font-display flex items-center gap-2">
                <LayoutGrid size={22} className="text-emerald-400" /> Sector Heatmap & Analysis
              </h1>
            </div>
            <p className="text-xs text-slate-500 font-semibold mt-1">
              Data-driven heatmap visualization and institutional financial diagnostics of NSE sectors.
            </p>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-lg p-0.5 self-start lg:self-auto">
            <button
              onClick={() => setViewMode('heatmap')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold transition-all ${
                viewMode === 'heatmap'
                  ? 'bg-slate-800 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Zap size={14} /> Treemap Heatmap
            </button>
            <button
              onClick={() => setViewMode('analysis')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold transition-all ${
                viewMode === 'analysis'
                  ? 'bg-slate-800 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <BarChart2 size={14} /> Charts & Metrics
            </button>
          </div>
        </div>
      )}

      {/* HEATMAP VIEW */}
      {viewMode === 'heatmap' && (
        <>
          {/* Sub Toolbar Controls */}
          <div className="flex flex-col md:flex-row items-center justify-between gap-3 bg-slate-900/30 border border-slate-800/60 p-3 rounded-xl">
            <div className="flex items-center gap-2">
              {selectedSector ? (
                <button
                  onClick={() => setSelectedSector(null)}
                  className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors text-xs font-bold px-2.5 py-1 bg-slate-850 border border-slate-800 rounded-lg"
                >
                  <ArrowLeft size={13} /> {selectedSector}
                </button>
              ) : (
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Configure Grid:</span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {/* Mode Selector */}
              <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded-lg p-0.5">
                {['performance', 'volatility', 'momentum', 'delivery', 'relative_strength'].map(m => (
                  <button
                    key={m}
                    onClick={() => {
                      setMode(m);
                      setTooltip(null);
                    }}
                    className={`px-2.5 py-1 rounded text-[9px] uppercase font-bold tracking-wider transition-all ${
                      mode === m
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {m.replace('_', ' ')}
                  </button>
                ))}
              </div>

              {/* Timeframe Selector */}
              <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded-lg p-0.5">
                {['1D', '1W', '1M', '3M', '6M', '1Y'].map(tf => (
                  <button
                    key={tf}
                    onClick={() => changeTimeframe(tf)}
                    className={`px-2.5 py-1 rounded text-[9px] uppercase font-bold tracking-wider transition-all ${
                      timeframe === tf
                        ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {tf}
                  </button>
                ))}
              </div>

              {/* Search to highlight */}
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" size={12} />
                <input
                  type="text"
                  placeholder="Find stock..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="pl-7 pr-3 py-1 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-emerald-500 w-32 outline-none"
                />
              </div>
            </div>
          </div>

          {/* Loading / Error States */}
          {loading && !heatmapData ? (
            <div className="flex items-center justify-center min-h-[400px]">
              <Loader2 className="w-10 h-10 text-emerald-500 animate-spin" />
            </div>
          ) : error ? (
            <ErrorCard message={error} onRetry={() => fetchHeatmap(mode, timeframe)} title="Heatmap Compute Error" />
          ) : (
            <>
              {/* Summary panel */}
              {heatmapData?.market_summary && (
                <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-2xl p-5 shadow-xl transition-all duration-300">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-800/60 pb-3 mb-4 gap-3">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
                        <Sparkles size={16} className="animate-pulse" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-200">Market Summary Panel</h3>
                        <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">
                          AI Analytics &bull; <span className="text-slate-400">{mode.replace('_', ' ')} basis</span>
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-500 text-[10px] font-bold uppercase tracking-wider">Signal:</span>
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-black tracking-wider ${
                          heatmapData.market_summary.signal === 'BUY'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : heatmapData.market_summary.signal === 'SELL'
                              ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                              : 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                        }`}>
                          {heatmapData.market_summary.signal}
                        </span>
                      </div>
                      <span className="text-slate-800">|</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-500 text-[10px] font-bold uppercase tracking-wider">Sentiment:</span>
                        <span className={`text-xs font-bold ${
                          heatmapData.market_summary.sentiment.includes('Bullish')
                            ? 'text-emerald-400'
                            : heatmapData.market_summary.sentiment.includes('Bearish')
                              ? 'text-rose-400'
                              : 'text-yellow-400'
                        }`}>
                          {heatmapData.market_summary.sentiment}
                        </span>
                      </div>
                      <span className="text-slate-800">|</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-500 text-[10px] font-bold uppercase tracking-wider">Confidence:</span>
                        <span className="text-xs font-black text-slate-200">{heatmapData.market_summary.confidence}%</span>
                      </div>
                    </div>
                  </div>

                  <p className="text-sm text-slate-300 leading-relaxed font-sans mb-3">
                    {heatmapData.market_summary.summary}
                  </p>
                  <p className="text-xs text-slate-400 leading-relaxed font-sans italic border-l-2 border-emerald-500/50 pl-3">
                    <strong>Actionable Insight:</strong> {heatmapData.market_summary.actionable_insight}
                  </p>
                </div>
              )}

              {/* Main SVG Treemap Display */}
              <div className="bg-slate-950 border border-slate-900 rounded-2xl p-2.5 shadow-2xl relative overflow-hidden">
                <div ref={containerRef} className="w-full relative min-h-[500px]" style={{ height: dimensions.height }}>
                  {computedRoot ? (
                    <svg
                      width={dimensions.width}
                      height={dimensions.height}
                      className="select-none overflow-hidden rounded-xl"
                    >
                      {selectedSector ? (
                        // Zoomed Sector View
                        (Array.isArray(rootNode?.children) ? rootNode.children : []).map(stock => {
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
                        // Full nested Sector View
                        (Array.isArray(computedRoot?.children) ? computedRoot.children : []).map(sector => {
                          const sectorLabelVisible = (sector.width || 0) > 80 && (sector.height || 0) > 40;
                          
                          return (
                            <g key={sector.name}>
                              <rect
                                x={sector.x}
                                y={sector.y}
                                width={sector.width}
                                height={sector.height}
                                fill="transparent"
                                stroke="#1e293b"
                                strokeWidth={2}
                              />
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
                              {(Array.isArray(sector?.children) ? sector.children : []).map(stock => {
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

                  {/* Tooltip */}
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
            </>
          )}
        </>
      )}

      {/* ANALYSIS CHARTS & METRICS VIEW */}
      {viewMode === 'analysis' && (
        <>
          {/* Analysis control config toolbar */}
          <div className="flex flex-col md:flex-row items-center justify-between gap-3 bg-slate-900/30 border border-slate-800/60 p-3 rounded-xl">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Calendar size={13} className="text-indigo-400" /> Choose Analysis Candle Interval:
            </span>
            <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded-lg p-0.5">
              {['1D', '1W', '1M', '3M', '6M', '1Y'].map(tf => (
                <button
                  key={tf}
                  onClick={() => changeTimeframe(tf)}
                  className={`px-3 py-1 rounded text-[10px] uppercase font-bold tracking-wider transition-all ${
                    timeframe === tf
                      ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {analysisLoading && !analysisData ? (
            <div className="flex items-center justify-center min-h-[400px]">
              <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
            </div>
          ) : analysisError ? (
            <ErrorCard message={analysisError} onRetry={() => fetchAnalysis(timeframe)} title="Analysis Load Error" />
          ) : (
            <div className="space-y-6">
              {/* Summary Cards */}
              {analysisData?.summary && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between">
                    <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">Top Sector ({timeframe})</span>
                    <span className="text-base font-bold text-emerald-400 truncate mt-2">
                      {analysisData.summary.best_sector_1m || 'N/A'}
                    </span>
                    <span className="text-xs text-slate-400 font-semibold mt-1">
                      +{analysisData.summary.best_sector_1m_val?.toFixed(2)}% avg return
                    </span>
                  </div>

                  <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between">
                    <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">Weakest Sector ({timeframe})</span>
                    <span className="text-base font-bold text-red-400 truncate mt-2">
                      {analysisData.summary.worst_sector_1m || 'N/A'}
                    </span>
                    <span className="text-xs text-slate-400 font-semibold mt-1">
                      {analysisData.summary.worst_sector_1m_val?.toFixed(2)}% avg return
                    </span>
                  </div>

                  <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between">
                    <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">Strongest Momentum</span>
                    <span className="text-base font-bold text-white truncate mt-2">
                      {analysisData.summary.strongest_momentum_sector || 'N/A'}
                    </span>
                    <span className="text-xs text-indigo-400 font-semibold mt-1">
                      Score: {analysisData.summary.strongest_momentum_val?.toFixed(1)}
                    </span>
                  </div>

                  <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between">
                    <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">Lowest Median PE</span>
                    <span className="text-base font-bold text-amber-400 truncate mt-2">
                      {analysisData.summary.most_attractive_valuation_sector || 'N/A'}
                    </span>
                    <span className="text-xs text-slate-400 font-semibold mt-1">
                      PE Ratio: {analysisData.summary.most_attractive_valuation_pe?.toFixed(1)}
                    </span>
                  </div>
                </div>
              )}

              {/* Bar Chart and Overview Table */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Sector Performance Chart */}
                <div className="lg:col-span-1 bg-slate-900/20 border border-slate-800/80 rounded-xl p-4 flex flex-col">
                  <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2">
                    <BarChart2 size={16} className="text-emerald-400" /> Sector Returns Performance
                  </h3>
                  <div className="flex-1 min-h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={chartData}
                        layout="vertical"
                        margin={{ top: 5, right: 15, left: -10, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                        <XAxis type="number" stroke="#94a3b8" fontSize={9} tickFormatter={(v) => `${v}%`} />
                        <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={9} width={80} />
                        <RechartsTooltip
                          contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }}
                          labelStyle={{ color: '#ffffff', fontWeights: 'bold' }}
                          itemStyle={{ color: '#10b981' }}
                          formatter={(value: any) => [`${parseFloat(value).toFixed(2)}%`, 'Average Return']}
                        />
                        <Bar dataKey="returnVal">
                          {chartData.map((entry, index) => (
                            <Cell 
                              key={`cell-${index}`} 
                              fill={entry.returnVal >= 0 ? 'rgba(16, 185, 129, 0.85)' : 'rgba(239, 68, 68, 0.85)'} 
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Sector Metrics Table */}
                <div className="lg:col-span-2 bg-slate-900/20 border border-slate-800/80 rounded-xl p-4 overflow-hidden flex flex-col">
                  <h3 className="text-sm font-bold text-slate-200 mb-4">Sector Heatmap Metrics</h3>
                  <div className="flex-1 overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-500">
                          <th className="py-2.5 font-bold uppercase tracking-wider">Sector Name</th>
                          <th className="py-2.5 font-bold uppercase tracking-wider text-center">Stocks</th>
                          <th className="py-2.5 font-bold uppercase tracking-wider text-right">Avg Return</th>
                          <th className="py-2.5 font-bold uppercase tracking-wider text-center">Valuation</th>
                          <th className="py-2.5 font-bold uppercase tracking-wider text-center">RSI</th>
                          <th className="py-2.5 font-bold uppercase tracking-wider text-center">Signal</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-850">
                        {analysisData?.sectors?.map((s: any) => (
                          <tr 
                            key={s.sector} 
                            onClick={() => setSelectedAnalysisSector(s.sector)}
                            className={`cursor-pointer hover:bg-slate-800/40 transition-colors ${
                              selectedAnalysisSector === s.sector ? 'bg-indigo-950/20 text-indigo-400 font-bold border-l-2 border-indigo-500' : ''
                            }`}
                          >
                            <td className="py-3 font-semibold text-slate-200">{s.sector}</td>
                            <td className="py-3 text-center text-slate-400 font-mono">{s.stock_count}</td>
                            <td className={`py-3 text-right font-mono font-bold ${
                              s.avg_return_timeframe >= 0 ? 'text-emerald-400' : 'text-red-400'
                            }`}>
                              {s.avg_return_timeframe >= 0 ? '+' : ''}{s.avg_return_timeframe.toFixed(2)}%
                            </td>
                            <td className="py-3 text-center">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                s.valuation_rating === 'Undervalued'
                                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/25'
                                  : s.valuation_rating === 'Overvalued'
                                    ? 'bg-red-500/10 text-red-400 border border-red-500/25'
                                    : 'bg-blue-500/10 text-blue-400 border border-blue-500/25'
                              }`}>
                                {s.valuation_rating}
                              </span>
                            </td>
                            <td className="py-3 text-center font-mono text-slate-300">{s.avg_rsi?.toFixed(0)}</td>
                            <td className="py-3 text-center">
                              <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                s.rotation_signal === 'ACCUMULATE'
                                  ? 'text-emerald-400 bg-emerald-500/10'
                                  : s.rotation_signal === 'AVOID'
                                    ? 'text-red-400 bg-red-500/10'
                                    : s.rotation_signal === 'REDUCE'
                                      ? 'text-amber-400 bg-amber-500/10'
                                      : 'text-slate-400 bg-slate-500/10'
                              }`}>
                                {s.rotation_signal}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              {/* Detailed Stocks list for selected sector */}
              {selectedAnalysisSector && (
                <div className="bg-slate-900/10 border border-slate-800/80 rounded-xl p-5 shadow-lg">
                  <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-slate-800 pb-3 mb-4 gap-3">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        Stocks in {selectedAnalysisSector}
                      </h3>
                      <p className="text-xs text-slate-500">
                        Click on any symbol to load it in the Research Terminal.
                      </p>
                    </div>

                    <div className="relative">
                      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" size={13} />
                      <input
                        type="text"
                        placeholder="Search stock..."
                        value={stockSearchQuery}
                        onChange={(e) => setStockSearchQuery(e.target.value)}
                        className="pl-8 pr-3 py-1 bg-slate-950 border border-slate-850 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-indigo-500 w-44 outline-none"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                    {filteredStocks.map((st: any) => (
                      <div
                        key={st.symbol}
                        onClick={() => handleStockClick(st.symbol)}
                        className="bg-slate-950/40 hover:bg-slate-900 border border-slate-850 hover:border-indigo-500/30 rounded-lg p-3 cursor-pointer transition-all flex flex-col justify-between"
                      >
                        <div className="flex justify-between items-center">
                          <span className="font-bold text-slate-200 text-xs">{st.symbol}</span>
                          <span className={`text-[10px] font-black ${
                            st.change_1d >= 0 ? 'text-emerald-400' : 'text-red-400'
                          }`}>
                            {st.change_1d >= 0 ? '+' : ''}{st.change_1d?.toFixed(1)}%
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-500 truncate mt-1">{st.company_name}</span>
                        <div className="flex justify-between items-center mt-3 pt-1 border-t border-slate-900/60 text-[10px]">
                          <span className="text-slate-400 font-mono">₹{st.price?.toFixed(2)}</span>
                          <span className="text-slate-500 font-semibold">PE: {st.pe_ratio?.toFixed(1) || 'N/A'}</span>
                        </div>
                      </div>
                    ))}
                    {filteredStocks.length === 0 && (
                      <div className="col-span-full text-center py-6 text-slate-500 text-xs font-semibold">
                        No stocks found matching "{stockSearchQuery}" in this sector.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
});

export default SectorHeatmapPage;
