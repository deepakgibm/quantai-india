import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { 
  TrendingUp, TrendingDown, RefreshCw, Search, Award, 
  Loader2, X, Download, Shield, LayoutGrid, ChevronRight,
  TrendingUp as TrendUpIcon, ArrowUpRight, ArrowDownRight, ArrowRight,
  Info
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import { api } from '../services/api';
import ErrorCard from '../components/ErrorCard';

class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean; error: any }> {
  state: { hasError: boolean; error: any } = { hasError: false, error: null };
  props!: { children: React.ReactNode };

  constructor(props: any) {
    super(props);
  }

  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }

  componentDidCatch(error: any, errorInfo: any) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6">
          <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-6 text-slate-100 max-w-xl mx-auto space-y-4">
            <h2 className="text-lg font-bold text-red-400 font-display">Sector Analysis Runtime Error</h2>
            <p className="text-sm text-slate-300">
              An unexpected rendering error occurred. Please refresh or try again.
            </p>
            <pre className="p-4 bg-slate-950/80 rounded-lg text-xs text-rose-400 overflow-x-auto font-mono">
              {this.state.error?.message || String(this.state.error)}
            </pre>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-xs font-bold transition-all text-white"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

const LineageTooltip: React.FC<{ fieldKey: string; lineageData?: any }> = ({ fieldKey, lineageData }) => {
  if (!lineageData || !lineageData[fieldKey]) return null;
  const item = lineageData[fieldKey];

  return (
    <span className="relative inline-block ml-1 align-middle group cursor-help">
      <Info 
        size={11} 
        className="text-slate-500 hover:text-slate-300 transition-colors"
      />
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 p-3 bg-slate-950/95 border border-slate-800 rounded-xl text-[10px] text-slate-300 shadow-2xl pointer-events-none opacity-0 group-hover:opacity-100 transition-all duration-200 z-50 normal-case font-normal font-sans tracking-normal text-left">
        <span className="block font-bold text-white mb-1.5 border-b border-slate-850 pb-1">{item.field_name} Lineage</span>
        <span className="block mb-1"><span className="text-slate-500 font-semibold uppercase tracking-wider text-[8px] mr-1">Source:</span>{item.source_api}</span>
        <span className="block mb-1"><span className="text-slate-500 font-semibold uppercase tracking-wider text-[8px] mr-1">Updated:</span>{item.last_updated}</span>
        <span className="block mb-1"><span className="text-slate-500 font-semibold uppercase tracking-wider text-[8px] mr-1">Logic:</span>{item.transformation_logic}</span>
        <span className="block"><span className="text-slate-500 font-semibold uppercase tracking-wider text-[8px] mr-1">Confidence:</span><span className="text-emerald-400 font-bold">{item.confidence_score}%</span></span>
      </span>
    </span>
  );
};

interface StockMetric {
  symbol: string;
  company_name: string;
  price: number;
  change_1d: number;
  change_1w: number;
  change_1m: number;
  change_3m: number;
  change_6m: number;
  change_1y: number;
  timeframe_return: number;
  rsi: number;
  volume: number;
  market_cap: number;
  pe_ratio: number;
  pb_ratio: number;
  dividend_yield: number;
  peg_ratio: number;
  above_20_dma: boolean;
  above_50_dma: boolean;
  above_200_dma: boolean;
  rating: string;
  sector: string;
}

interface SectorMetric {
  sector: string;
  stock_count: number;
  avg_return_1d: number;
  avg_return_1w: number;
  avg_return_1m: number;
  avg_return_3m: number;
  avg_return_6m: number;
  avg_return_1y: number;
  avg_rsi: number;
  avg_pe: number;
  avg_pb: number;
  avg_div_yield: number;
  avg_peg: number;
  pct_above_20_dma: number;
  pct_above_50_dma: number;
  pct_above_200_dma: number;
  advancing_count: number;
  declining_count: number;
  market_cap_contribution: number;
  volume_change: number;
  momentum_score: number;
  relative_strength: number;
  valuation_rating: string;
  trend: string;
  rotation_signal: string;
  gainers: StockMetric[];
  losers: StockMetric[];
}

const SectorAnalysisPage: React.FC<{ onNavigate?: (page: any) => void }> = () => {
  const [data, setData] = useState<{ summary: any; sectors: SectorMetric[]; stocks: StockMetric[]; lineage?: any } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState<string>(() => localStorage.getItem('sector_timeframe') || '1D');
  
  // Interactive / UI States
  const [selectedSector, setSelectedSector] = useState<SectorMetric | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<keyof SectorMetric>('avg_return_1d');
  const [sortAsc, setSortAsc] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  const changeTimeframe = (tf: string) => {
    setTimeframe(tf);
    localStorage.setItem('sector_timeframe', tf);
  };

  const fetchSectorAnalysis = async (activeTimeframe: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getSectorAnalysisData(activeTimeframe);
      if (res && res.status === 'success') {
        setData(res);
        
        // Debugging logs required by specifications
        console.log("Sector Analysis Page Loaded");
        console.log("Nifty 500 Stocks Loaded:", res.stocks ? res.stocks.length : 0);
        console.log("Unique Sectors Found:", res.sectors ? res.sectors.length : 0);
        console.log("Sector Data Generated:", res.sectors ? res.sectors.length : 0);
        console.log("Heatmap Nodes:", res.sectors ? res.sectors.length : 0);
      } else {
        setError('Sector metrics could not be calculated');
      }
    } catch (err: any) {
      console.error('[SectorAnalysis] Fetch error:', err);
      setError(err.message || 'Sector mapping failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSectorAnalysis(timeframe);
  }, [timeframe]);

  // Performance Table Sorting & Searching
  const sortedAndFilteredSectors = useMemo(() => {
    if (!data?.sectors) return [];
    
    return data.sectors
      .filter(sec => sec.sector.toLowerCase().includes(searchQuery.toLowerCase()))
      .sort((a, b) => {
        const aVal = a[sortField];
        const bVal = b[sortField];
        
        if (aVal === undefined) return 1;
        if (bVal === undefined) return -1;
        
        if (typeof aVal === 'string') {
          return sortAsc 
            ? (aVal as string).localeCompare(bVal as string) 
            : (bVal as string).localeCompare(aVal as string);
        }
        
        return sortAsc 
          ? (aVal as number) - (bVal as number) 
          : (bVal as number) - (aVal as number);
      });
  }, [data, searchQuery, sortField, sortAsc]);

  // Pagination
  const paginatedSectors = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return sortedAndFilteredSectors.slice(startIndex, startIndex + itemsPerPage);
  }, [sortedAndFilteredSectors, currentPage]);

  const totalPages = Math.ceil(sortedAndFilteredSectors.length / itemsPerPage);

  const handleSort = (field: keyof SectorMetric) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
    setCurrentPage(1);
  };

  // CSV Export
  const exportToCSV = () => {
    const sectors = Array.isArray(data?.sectors) ? data.sectors : [];
    console.log("CSV Export sectors data:", sectors);
    console.log("Is Array:", Array.isArray(sectors));
    if (sectors.length === 0) return;
    const headers = ['Sector', 'Stocks', '1D %', '1W %', '1M %', '3M %', '6M %', '1Y %', 'Avg RSI', 'Trend', 'Avg PE', 'Avg PB', 'Valuation'];
    const rows = sectors.map(sec => [
      sec.sector,
      sec.stock_count,
      sec.avg_return_1d,
      sec.avg_return_1w,
      sec.avg_return_1m,
      sec.avg_return_3m,
      sec.avg_return_6m,
      sec.avg_return_1y,
      sec.avg_rsi,
      sec.trend,
      sec.avg_pe,
      sec.avg_pb,
      sec.valuation_rating
    ]);
    
    const csvContent = [headers.join(','), ...(Array.isArray(rows) ? rows : []).map(e => e.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `Sector_Analysis_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Heatmap Color Assignment
  const getHeatmapColor = (ret: number) => {
    if (ret >= 2.5) return 'bg-emerald-950/80 border-emerald-500 text-emerald-400';
    if (ret >= 0.8) return 'bg-emerald-900/40 border-emerald-600/60 text-emerald-300';
    if (ret > -0.8) return 'bg-slate-900/80 border-slate-700 text-slate-300';
    if (ret > -2.5) return 'bg-orange-950/40 border-orange-700/60 text-orange-400';
    return 'bg-rose-950/80 border-rose-600 text-rose-400';
  };

  const getValuationColor = (rating: string) => {
    if (rating === 'Undervalued') return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
    if (rating === 'Overvalued') return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
    return 'text-blue-400 bg-blue-500/10 border-blue-500/20';
  };

  const getTrendColor = (trend: string) => {
    if (trend === 'Bullish') return 'text-emerald-400 bg-emerald-500/10';
    if (trend === 'Bearish') return 'text-rose-400 bg-rose-500/10';
    return 'text-slate-400 bg-slate-800';
  };

  const renderTrendArrow = (trend: string) => {
    if (trend === 'Bullish') return <span className="font-bold text-emerald-400">↑</span>;
    if (trend === 'Bearish') return <span className="font-bold text-rose-400">↓</span>;
    return <span className="font-bold text-slate-500">→</span>;
  };

  // Sector Rotation leaders & laggards calculation
  const rotationData = useMemo(() => {
    if (!data?.sectors) return { leaders: [], laggards: [] };
    
    // Sort by momentum/relative strength/performance composite
    const sorted = [...data.sectors].sort((a, b) => b.momentum_score - a.momentum_score);
    return {
      leaders: sorted.slice(0, 5),
      laggards: sorted.slice(-5).reverse()
    };
  }, [data]);

  // Loading indicator
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] text-slate-400">
        <Loader2 className="w-12 h-12 text-indigo-500 animate-spin mb-4" />
        <p className="text-sm font-semibold tracking-wide uppercase">Assembling Sector Metrics...</p>
      </div>
    );
  }

  // Error boundary State
  if (error || !data || !data.sectors || data.sectors.length === 0) {
    return (
      <div className="p-6">
        <ErrorCard 
          message={error || "No sectors detected in dataset"} 
          title="Sector Mapping Failure" 
          onRetry={() => fetchSectorAnalysis(timeframe)} 
        />
      </div>
    );
  }

  const { summary } = data;

  return (
    <div className="space-y-8 pb-12">
      {/* Page Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-brand-500/20">
              <LayoutGrid className="text-white" size={20} />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white font-display">Sector Analysis</h1>
              <p className="text-xs text-slate-500 font-semibold mt-0.5">
                Sector rotational models, valuation tracking, and breadth indices across Nifty 500 stocks.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Timeframe Selector */}
          <div className="flex rounded-lg border border-slate-800 bg-slate-950 p-0.5">
            {['1D', '1W', '1M', '3M', '6M', '1Y'].map(tf => (
              <button
                key={tf}
                onClick={() => changeTimeframe(tf)}
                className={`px-2.5 py-1 rounded text-[10px] uppercase font-bold tracking-wider transition-all ${
                  timeframe === tf
                    ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>

          <button
            onClick={() => fetchSectorAnalysis(timeframe)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 rounded-lg hover:bg-slate-700 border border-slate-700 transition-colors"
          >
            <RefreshCw size={13} /> Refresh Analysis
          </button>
        </div>
      </div>

      {/* 1. Sector Overview Dashboard */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        {[
          { label: 'Total Sectors', val: summary.total_sectors, desc: 'Nifty 500 Constituents', trend: 'Neutral' },
          { label: 'Top Sector (1M)', val: summary.best_sector_1m, desc: `+${summary.best_sector_1m_val.toFixed(1)}% Return`, trend: 'Bullish' },
          { label: 'Laggard Sector (1M)', val: summary.worst_sector_1m, desc: `${summary.worst_sector_1m_val.toFixed(1)}% Return`, trend: 'Bearish' },
          { label: 'Strongest Momentum', val: summary.strongest_momentum_sector, desc: `Score: ${summary.strongest_momentum_val.toFixed(1)}`, trend: 'Bullish' },
          { label: 'Highest Volume', val: summary.highest_participation_sector, desc: 'High Institutional Flow', trend: 'Bullish' },
          { label: 'Valuation Choice', val: summary.most_attractive_valuation_sector, desc: `Avg PE: ${summary.most_attractive_valuation_pe.toFixed(1)}`, trend: 'Bullish' }
        ].map((card, i) => (
          <div key={i} className="bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between h-28 shadow-sm">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">{card.label}</span>
            <div className="my-1.5">
              <div className="text-sm font-black text-white truncate max-w-[150px]" title={card.val.toString()}>{card.val}</div>
              <div className="text-[10px] text-slate-400 font-semibold">{card.desc}</div>
            </div>
            <div className="flex items-center justify-between">
              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${getTrendColor(card.trend)}`}>
                {card.trend}
              </span>
              {renderTrendArrow(card.trend)}
            </div>
          </div>
        ))}
      </div>

      {/* 2. Interactive Sector Heatmap */}
      <div className="bg-slate-900/20 border border-slate-800/80 rounded-2xl p-6 shadow-md space-y-4">
        <div>
          <h2 className="text-sm font-bold text-slate-200">Sector Performance Heatmap</h2>
          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mt-0.5">Colored by 1-Month Return &bull; Click to drill down</p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {(() => {
            const sectors = Array.isArray(data?.sectors) ? data.sectors : [];
            console.log("Rendering Performance Heatmap, sectors:", sectors);
            console.log("Is Array:", Array.isArray(sectors));
            return sectors.map(sec => (
              <div
                key={sec.sector}
                onClick={() => setSelectedSector(sec)}
                className={`p-4 border rounded-xl cursor-pointer hover:scale-[1.02] transition-all flex flex-col justify-between h-28 shadow-lg ${getHeatmapColor(sec.avg_return_1m)}`}
              >
                <div className="font-bold text-xs line-clamp-2 leading-tight" title={sec.sector}>{sec.sector}</div>
                <div className="mt-2 flex items-baseline justify-between">
                  <span className="text-lg font-black">{sec.avg_return_1m >= 0 ? '+' : ''}{sec.avg_return_1m.toFixed(1)}%</span>
                  <span className="text-[9px] opacity-75 font-semibold">{sec.stock_count} stocks</span>
                </div>
              </div>
            ));
          })()}
        </div>
      </div>

      {/* 3. Performance Table & Sector Rotation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Table - 2/3 wide */}
        <div className="lg:col-span-2 bg-slate-900/20 border border-slate-800/80 rounded-2xl p-6 shadow-md space-y-4 flex flex-col justify-between">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/60">
            <div>
              <h2 className="text-sm font-bold text-slate-200">Sector Performance Table</h2>
              <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wide">Sortable overview of standard durations</p>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" size={12} />
                <input
                  type="text"
                  placeholder="Find sector..."
                  value={searchQuery}
                  onChange={e => { setSearchQuery(e.target.value); setCurrentPage(1); }}
                  className="pl-7 pr-3 py-1 bg-slate-950 border border-slate-800 rounded-lg text-[10px] text-slate-200 focus:outline-none focus:border-indigo-500 w-36 outline-none"
                />
              </div>
              <button
                onClick={exportToCSV}
                className="flex items-center gap-1 px-2.5 py-1 text-[10px] font-bold text-slate-300 bg-slate-800 border border-slate-700 hover:bg-slate-700 rounded-lg transition-colors"
              >
                <Download size={10} /> CSV
              </button>
            </div>
          </div>

          <div className="overflow-x-auto min-h-[300px]">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-800/50 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  <th onClick={() => handleSort('sector')} className="py-2.5 text-left cursor-pointer hover:text-slate-300">Sector</th>
                  <th onClick={() => handleSort('stock_count')} className="py-2.5 text-right cursor-pointer hover:text-slate-300">Stocks</th>
                  <th onClick={() => handleSort('avg_return_1d')} className="py-2.5 text-right cursor-pointer hover:text-slate-300">1D</th>
                  <th onClick={() => handleSort('avg_return_1w')} className="py-2.5 text-right cursor-pointer hover:text-slate-300">1W</th>
                  <th onClick={() => handleSort('avg_return_1m')} className="py-2.5 text-right cursor-pointer hover:text-slate-300">1M</th>
                  <th onClick={() => handleSort('avg_return_1y')} className="py-2.5 text-right cursor-pointer hover:text-slate-300">1Y</th>
                  <th onClick={() => handleSort('avg_rsi')} className="py-2.5 text-right cursor-pointer hover:text-slate-300">
                    RSI
                    <LineageTooltip fieldKey="rsi" lineageData={data?.lineage} />
                  </th>
                  <th onClick={() => handleSort('trend')} className="py-2.5 text-center cursor-pointer hover:text-slate-300">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40 text-slate-300">
                {(() => {
                  const sectors = Array.isArray(paginatedSectors) ? paginatedSectors : [];
                  console.log("Rendering Performance Table, paginatedSectors:", sectors);
                  console.log("Is Array:", Array.isArray(sectors));
                  return sectors.map(sec => (
                    <tr
                      key={sec.sector}
                      onClick={() => setSelectedSector(sec)}
                      className="hover:bg-slate-800/20 cursor-pointer transition-colors"
                    >
                      <td className="py-2.5 font-bold text-white max-w-[140px] truncate">{sec.sector}</td>
                      <td className="py-2.5 text-right font-semibold text-slate-400">{sec.stock_count}</td>
                      <td className={`py-2.5 text-right font-mono font-bold ${sec.avg_return_1d >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {sec.avg_return_1d >= 0 ? '+' : ''}{sec.avg_return_1d.toFixed(1)}%
                      </td>
                      <td className={`py-2.5 text-right font-mono ${sec.avg_return_1w >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {sec.avg_return_1w >= 0 ? '+' : ''}{sec.avg_return_1w.toFixed(1)}%
                      </td>
                      <td className={`py-2.5 text-right font-mono font-bold ${sec.avg_return_1m >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {sec.avg_return_1m >= 0 ? '+' : ''}{sec.avg_return_1m.toFixed(1)}%
                      </td>
                      <td className={`py-2.5 text-right font-mono ${sec.avg_return_1y >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {sec.avg_return_1y >= 0 ? '+' : ''}{sec.avg_return_1y.toFixed(0)}%
                      </td>
                      <td className={`py-2.5 text-right font-mono font-bold ${sec.avg_rsi >= 60 ? 'text-amber-400' : sec.avg_rsi <= 40 ? 'text-emerald-400' : 'text-slate-400'}`}>
                        {sec.avg_rsi.toFixed(0)}
                      </td>
                      <td className="py-2.5 text-center">
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${getTrendColor(sec.trend)}`}>
                          {sec.trend}
                        </span>
                      </td>
                    </tr>
                  ));
                })()}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-slate-800/40 pt-4 text-[10px] text-slate-500 font-bold uppercase tracking-wider">
              <span>Showing {(currentPage - 1) * itemsPerPage + 1} - {Math.min(currentPage * itemsPerPage, sortedAndFilteredSectors.length)} of {sortedAndFilteredSectors.length}</span>
              <div className="flex gap-1">
                <button
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(currentPage - 1)}
                  className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 disabled:opacity-30 rounded-lg text-slate-300 font-bold transition-all"
                >
                  Prev
                </button>
                <button
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage(currentPage + 1)}
                  className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 disabled:opacity-30 rounded-lg text-slate-300 font-bold transition-all"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Sector Rotation Dashboard */}
        <div className="bg-slate-900/20 border border-slate-800/80 rounded-2xl p-6 shadow-md space-y-5">
          <div>
            <h2 className="text-sm font-bold text-slate-200">Rotation & Relative Strength</h2>
            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mt-0.5">Top Momentum Leaders vs Laggards</p>
          </div>

          <div className="space-y-4">
            {/* Leaders */}
            <div>
              <h3 className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1 mb-2">
                <Award size={12} /> Rotation Leaders
              </h3>
              <div className="space-y-1.5">
                {(() => {
                  const leaders = Array.isArray(rotationData?.leaders) ? rotationData.leaders : [];
                  console.log("Rendering Rotation Leaders:", leaders);
                  console.log("Is Array:", Array.isArray(leaders));
                  return leaders.map((sec, idx) => (
                    <div
                      key={sec.sector}
                      onClick={() => setSelectedSector(sec)}
                      className="flex items-center justify-between text-xs p-2 rounded-lg bg-slate-900/60 border border-slate-800/60 hover:border-emerald-500/20 cursor-pointer transition-all"
                    >
                      <span className="font-bold text-slate-200">{idx + 1}. {sec.sector}</span>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-slate-400 text-[10px]">RS: {sec.relative_strength >= 0 ? '+' : ''}{sec.relative_strength.toFixed(1)}</span>
                        <span className="text-emerald-400 font-bold">↑</span>
                      </div>
                    </div>
                  ));
                })()}
              </div>
            </div>

            {/* Laggards */}
            <div>
              <h3 className="text-[10px] font-bold uppercase tracking-wider text-rose-400 flex items-center gap-1 mb-2">
                <Award size={12} /> Rotation Laggards
              </h3>
              <div className="space-y-1.5">
                {(() => {
                  const laggards = Array.isArray(rotationData?.laggards) ? rotationData.laggards : [];
                  console.log("Rendering Rotation Laggards:", laggards);
                  console.log("Is Array:", Array.isArray(laggards));
                  return laggards.map((sec, idx) => (
                    <div
                      key={sec.sector}
                      onClick={() => setSelectedSector(sec)}
                      className="flex items-center justify-between text-xs p-2 rounded-lg bg-slate-900/60 border border-slate-800/60 hover:border-rose-500/20 cursor-pointer transition-all"
                    >
                      <span className="font-bold text-slate-200">{idx + 1}. {sec.sector}</span>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-slate-400 text-[10px]">RS: {sec.relative_strength >= 0 ? '+' : ''}{sec.relative_strength.toFixed(1)}</span>
                        <span className="text-rose-400 font-bold">↓</span>
                      </div>
                    </div>
                  ));
                })()}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Valuation Analysis & Breadth Indicators */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Valuation Chart */}
        <div className="bg-slate-900/20 border border-slate-800/80 rounded-2xl p-6 shadow-md space-y-4">
          <div>
            <h2 className="text-sm font-bold text-slate-200">
              Sector Valuation Index (PE)
              <LineageTooltip fieldKey="pe_ratio" lineageData={data?.lineage} />
            </h2>
            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mt-0.5">Average PE compared to standard benchmarks</p>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={Array.isArray(data?.sectors) ? data.sectors : []} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <XAxis 
                  dataKey="sector" 
                  tick={{ fill: '#64748b', fontSize: 8, fontWeight: 'bold' }} 
                  angle={-45} 
                  textAnchor="end"
                  interval={0}
                  height={60}
                />
                <YAxis tick={{ fill: '#64748b', fontSize: 9 }} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                  labelClassName="text-white font-bold text-xs mb-1"
                  formatter={(value: any) => [`PE: ${value}`, 'Average PE']}
                />
                <ReferenceLine y={22} stroke="#10b981" strokeDasharray="3 3" label={{ value: 'Undervalued', fill: '#10b981', fontSize: 8, position: 'insideBottomLeft' }} />
                <ReferenceLine y={32} stroke="#f43f5e" strokeDasharray="3 3" label={{ value: 'Overvalued', fill: '#f43f5e', fontSize: 8, position: 'insideTopLeft' }} />
                <Bar dataKey="avg_pe" radius={[4, 4, 0, 0]}>
                  {(() => {
                    const sectors = Array.isArray(data?.sectors) ? data.sectors : [];
                    console.log("Rendering Valuation Chart, sectors:", sectors);
                    console.log("Is Array:", Array.isArray(sectors));
                    return sectors.map((entry, index) => {
                      const rating = entry.valuation_rating;
                      const fill = rating === 'Undervalued' ? '#10b981' : rating === 'Overvalued' ? '#f43f5e' : '#3b82f6';
                      return <Cell key={`cell-${index}`} fill={fill} />;
                    });
                  })()}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Breadth Progress Bars */}
        <div className="bg-slate-900/20 border border-slate-800/80 rounded-2xl p-6 shadow-md space-y-6">
          <div>
            <h2 className="text-sm font-bold text-slate-200">Market Breadth Indicators</h2>
            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mt-0.5">Average stocks trading above moving averages</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
            {[
              { label: 'Above 20 DMA', field: 'pct_above_20_dma' as keyof SectorMetric, color: 'from-blue-500 to-indigo-500' },
              { label: 'Above 50 DMA', field: 'pct_above_50_dma' as keyof SectorMetric, color: 'from-emerald-500 to-green-400' },
              { label: 'Above 200 DMA', field: 'pct_above_200_dma' as keyof SectorMetric, color: 'from-amber-500 to-yellow-400' }
            ].map(dma => {
              const sectors = Array.isArray(data?.sectors) ? data.sectors : [];
              const avg = sectors.length > 0 ? (sectors.reduce((sum, s) => sum + ((s[dma.field] as number) || 0), 0) / sectors.length) : 0;
              return (
                <div key={dma.label} className="bg-slate-950/60 border border-slate-900 rounded-xl p-4 flex flex-col justify-between h-36">
                  <div>
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">{dma.label}</span>
                    <div className="text-2xl font-black text-white mt-1.5">{avg.toFixed(0)}%</div>
                  </div>
                  <div>
                    <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden mb-1">
                      <div className={`h-full rounded-full bg-gradient-to-r ${dma.color}`} style={{ width: `${avg}%` }} />
                    </div>
                    <span className="text-[8px] text-slate-500 font-bold uppercase">Broad participation index</span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="space-y-3 border-t border-slate-800/40 pt-4">
            <h3 className="text-[10px] font-bold uppercase tracking-wider text-slate-500">DMA Breadth by Sector</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-[10px] text-slate-300">
              {(() => {
                const sectors = Array.isArray(data?.sectors) ? data.sectors.slice(0, 8) : [];
                console.log("Rendering DMA Breadth by Sector list, sectors:", sectors);
                console.log("Is Array:", Array.isArray(sectors));
                return sectors.map(sec => (
                  <div key={sec.sector} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-400 truncate max-w-[150px]">{sec.sector}</span>
                      <span className="font-mono text-slate-200">{sec.pct_above_50_dma.toFixed(0)}% above 50d</span>
                    </div>
                    <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-emerald-500" style={{ width: `${sec.pct_above_50_dma}%` }} />
                    </div>
                  </div>
                ));
              })()}
            </div>
          </div>
        </div>
      </div>

      {/* 5. Sector Constituents Drill-down View (Modal) */}
      {selectedSector && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
          onClick={() => setSelectedSector(null)}
        >
          <div 
            className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full max-h-[85vh] overflow-hidden shadow-2xl flex flex-col"
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="sticky top-0 bg-slate-950 border-b border-slate-800 p-5 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center font-black">
                  {selectedSector.stock_count}
                </div>
                <div>
                  <h2 className="text-md font-bold text-white">{selectedSector.sector} Constituents</h2>
                  <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mt-0.5">
                    Avg PE: {selectedSector.avg_pe.toFixed(1)} &bull; Avg RSI: {selectedSector.avg_rsi.toFixed(0)} &bull; {selectedSector.valuation_rating}
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedSector(null)}
                className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1">
              {/* Leaders and Laggards snapshot */}
              {selectedSector.stock_count > 5 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4">
                    <h3 className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 mb-2 flex items-center gap-1">
                      <TrendingUp size={10} /> Top Performers ({timeframe})
                    </h3>
                    <div className="space-y-1.5">
                      {(() => {
                        const gainers = Array.isArray(selectedSector?.gainers) ? selectedSector.gainers.slice(0, 3) : [];
                        console.log("Rendering Modal Top Performers, gainers:", gainers);
                        console.log("Is Array:", Array.isArray(gainers));
                        return gainers.map(st => (
                          <div key={st.symbol} className="flex items-center justify-between text-xs">
                            <span className="font-bold text-white">{st.symbol} <span className="text-[9px] text-slate-500 font-normal">{st.company_name}</span></span>
                            <span className="font-mono text-emerald-400 font-bold">+{st.change_1d.toFixed(1)}%</span>
                          </div>
                        ));
                      })()}
                    </div>
                  </div>

                  <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4">
                    <h3 className="text-[10px] font-bold uppercase tracking-wider text-rose-400 mb-2 flex items-center gap-1">
                      <TrendingDown size={10} /> Bottom Performers ({timeframe})
                    </h3>
                    <div className="space-y-1.5">
                      {(() => {
                        const losers = Array.isArray(selectedSector?.losers) ? selectedSector.losers.slice(0, 3) : [];
                        console.log("Rendering Modal Bottom Performers, losers:", losers);
                        console.log("Is Array:", Array.isArray(losers));
                        return losers.map(st => (
                          <div key={st.symbol} className="flex items-center justify-between text-xs">
                            <span className="font-bold text-white">{st.symbol} <span className="text-[9px] text-slate-500 font-normal">{st.company_name}</span></span>
                            <span className="font-mono text-rose-400 font-bold">{st.change_1d.toFixed(1)}%</span>
                          </div>
                        ));
                      })()}
                    </div>
                  </div>
                </div>
              )}

              {/* Table of all constituents */}
              <div className="border border-slate-800/80 rounded-xl overflow-hidden bg-slate-950/40">
                <div className="overflow-x-auto max-h-[350px]">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-950 border-b border-slate-800">
                      <tr className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                        <th className="px-4 py-3 text-left">Symbol</th>
                        <th className="px-4 py-3 text-left">Company Name</th>
                        <th className="px-4 py-3 text-right">Price</th>
                        <th className="px-4 py-3 text-right">{timeframe} %</th>
                        <th className="px-4 py-3 text-right">
                          RSI
                          <LineageTooltip fieldKey="rsi" lineageData={data?.lineage} />
                        </th>
                        <th className="px-4 py-3 text-right">
                          PE
                          <LineageTooltip fieldKey="pe_ratio" lineageData={data?.lineage} />
                        </th>
                        <th className="px-4 py-3 text-right">
                          M.Cap
                          <LineageTooltip fieldKey="market_cap" lineageData={data?.lineage} />
                        </th>
                        <th className="px-4 py-3 text-center">
                          Rating
                          <LineageTooltip fieldKey="macd" lineageData={data?.lineage} />
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/30 text-slate-300">
                      {(() => {
                        const stocks = Array.isArray(selectedSector?.stocks) ? selectedSector.stocks : [];
                        console.log("Rendering Modal Stocks List, stocks:", stocks);
                        console.log("Is Array:", Array.isArray(stocks));
                        return stocks.map(st => (
                          <tr key={st.symbol} className="hover:bg-slate-900/40 transition-colors">
                            <td className="px-4 py-2 font-bold text-white">{st.symbol}</td>
                            <td className="px-4 py-2 text-slate-500 truncate max-w-[150px]">{st.company_name}</td>
                            <td className="px-4 py-2 text-right font-mono font-semibold">₹{st.price.toFixed(1)}</td>
                            <td className={`px-4 py-2 text-right font-mono font-bold ${st.timeframe_return >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {st.timeframe_return >= 0 ? '+' : ''}{st.timeframe_return.toFixed(1)}%
                            </td>
                            <td className={`px-4 py-2 text-right font-mono ${st.rsi >= 70 ? 'text-amber-400' : st.rsi <= 30 ? 'text-emerald-400' : 'text-slate-400'}`}>
                              {st.rsi.toFixed(0)}
                            </td>
                            <td className="px-4 py-2 text-right font-mono">{st.pe_ratio.toFixed(1)}</td>
                            <td className="px-4 py-2 text-right text-slate-500">₹{(st.market_cap / 10000000).toFixed(0)} Cr</td>
                            <td className="px-4 py-2 text-center">
                              <span className={`text-[8px] font-black tracking-wider px-1.5 py-0.5 rounded-full ${
                                st.rating === 'BUY' ? 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20' :
                                st.rating === 'SELL' ? 'text-rose-400 bg-rose-500/10 border border-rose-500/20' :
                                'text-slate-400 bg-slate-800'
                              }`}>
                                {st.rating}
                              </span>
                            </td>
                          </tr>
                        ));
                      })()}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const SectorAnalysisPageWithErrorBoundary: React.FC<{ onNavigate?: (page: any) => void }> = (props) => (
  <ErrorBoundary>
    <SectorAnalysisPage {...props} />
  </ErrorBoundary>
);

export default SectorAnalysisPageWithErrorBoundary;
