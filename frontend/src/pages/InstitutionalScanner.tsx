import React, { useState, useEffect, useCallback } from 'react';
import { API_URL, getAuthHeaders } from '../services/api';
import { Page } from '../types';
import { useGlobalSymbol } from '../contexts/GlobalSymbolContext';
import UniverseFilter from '../components/UniverseFilter';
import { 
  TrendingUp, 
  Search, 
  Filter, 
  Download, 
  Play, 
  RefreshCw, 
  CheckCircle, 
  AlertCircle,
  HelpCircle,
  ArrowUpDown,
  Sliders,
  DollarSign
} from 'lucide-react';

const safeFixed = (val: any, decimals = 2): string => {
  if (val === null || val === undefined || isNaN(Number(val))) return '—';
  return Number(val).toFixed(decimals);
};

interface ScannerResult {
  symbol: string;
  company_name: string;
  sector: string;
  current_price: number;
  market_cap: number;
  rs_score: number;
  rs_rank: number;
  sector_rank: number;
  industry_rank: number;
  vcp_score: number;
  vcp_category: string;
  vcp_contractions: number;
  vcp_latest_contraction: number;
  volume_dry_up: number;
  atr_contraction: number;
  breakout_pivot: number;
  breakout_ready: boolean;
  trend_template_score: number;
  sma50: number;
  sma150: number;
  sma200: number;
  distance_52w_high: number;
  is_breakout: boolean;
  breakout_type: string;
  breakout_price: number;
  volume_surge: number;
  darvas_status: string;
  darvas_top: number;
  darvas_bottom: number;
  darvas_days: number;
  cup_handle_confidence: number;
  double_bottom_confidence: number;
  flat_base_length: number;
  flat_base_depth: number;
  volume_contraction: number;
  supply_drying_score: number;
  accumulation_score: number;
}

interface DashboardStats {
  total_scanned: number;
  vcp_candidates: number;
  breakout_ready: number;
  fresh_breakouts: number;
  near_52w_high: number;
  rs_leaders: number;
  last_updated: string | null;
}

interface ScannerProps {
  onNavigate: (page: Page, symbol?: string) => void;
}

const InstitutionalScanner: React.FC<ScannerProps> = ({ onNavigate }) => {
  const { selectedUniverse } = useGlobalSymbol();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [results, setResults] = useState<ScannerResult[]>([]);
  const [filteredResults, setFilteredResults] = useState<ScannerResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanStatus, setScanStatus] = useState({ is_scanning: false, progress: 0.0 });
  const [activeTab, setActiveTab] = useState<'vcp' | 'trend' | 'rs' | 'breakout' | 'darvas' | 'cup_handle' | 'double_bottom' | 'flat_base' | 'volume'>('vcp');

  // Filters State
  const [mcapFilter, setMcapFilter] = useState<string>('all');
  const [sectorFilter, setSectorFilter] = useState<string>('all');
  const [minPrice, setMinPrice] = useState<string>('');
  const [maxPrice, setMaxPrice] = useState<string>('');
  const [minVcpScore, setMinVcpScore] = useState<string>('60');
  const [breakoutReadyOnly, setBreakoutReadyOnly] = useState<boolean>(false);
  const [near52wOnly, setNear52wOnly] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Sorting State
  const [sortField, setSortField] = useState<keyof ScannerResult>('vcp_score');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Load stats and scan data
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch Dashboard Stats
      const statsRes = await fetch(
        `${API_URL}/api/v1/institutional-scanner/dashboard?universe=${encodeURIComponent(selectedUniverse)}`,
        { headers: getAuthHeaders() }
      );
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }

      // Fetch Scan Results
      const resultsRes = await fetch(
        `${API_URL}/api/v1/institutional-scanner/results?universe=${encodeURIComponent(selectedUniverse)}`,
        { headers: getAuthHeaders() }
      );
      if (resultsRes.ok) {
        const resultsData = await resultsRes.json();
        setResults(resultsData);
        setFilteredResults(resultsData);
      }
      
      // Fetch Status
      const statusRes = await fetch(`${API_URL}/api/v1/institutional-scanner/status`, {
        headers: getAuthHeaders()
      });
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setScanStatus(statusData);
      }
    } catch (err) {
      console.error("Failed to load scanner data", err);
    } finally {
      setLoading(false);
    }
  }, [selectedUniverse]);

  // Poll scan status when scanning
  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (scanStatus.is_scanning) {
      timer = setInterval(async () => {
        try {
          const statusRes = await fetch(`${API_URL}/api/v1/institutional-scanner/status`, {
            headers: getAuthHeaders()
          });
          if (statusRes.ok) {
            const statusData = await statusRes.json();
            setScanStatus(statusData);
            if (!statusData.is_scanning) {
              clearInterval(timer);
              loadData(); // reload results when scan finishes
            }
          }
        } catch (e) {
          console.error("Failed to fetch scan status", e);
        }
      }, 3000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [scanStatus.is_scanning, loadData]);

  // Trigger scanning job
  const triggerScan = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/institutional-scanner/scan`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      if (res.ok) {
        setScanStatus({ is_scanning: true, progress: 0.0 });
      }
    } catch (e) {
      console.error("Failed to trigger scan", e);
    }
  };

  // Unique Sectors list for filter
  const sectors = Array.from(new Set(results.map(r => r.sector))).filter(Boolean);

  // Apply filters and sorting
  useEffect(() => {
    let data = [...results];

    // Search Query
    if (searchQuery) {
      const query = searchQuery.toUpperCase();
      data = data.filter(r => r.symbol.includes(query) || r.company_name.toUpperCase().includes(query));
    }

    // Market Cap Filter
    if (mcapFilter !== 'all') {
      const capLimit = 100000000 * 100; // Rs 100 Cr in Rs
      if (mcapFilter === 'large') {
        data = data.filter(r => r.market_cap >= 200000000000); // 20000Cr
      } else if (mcapFilter === 'mid') {
        data = data.filter(r => r.market_cap >= 50000000000 && r.market_cap < 200000000000);
      } else if (mcapFilter === 'small') {
        data = data.filter(r => r.market_cap < 50000000000);
      }
    }

    // Sector Filter
    if (sectorFilter !== 'all') {
      data = data.filter(r => r.sector === sectorFilter);
    }

    // Price Range Filter
    if (minPrice) {
      data = data.filter(r => r.current_price >= parseFloat(minPrice));
    }
    if (maxPrice) {
      data = data.filter(r => r.current_price <= parseFloat(maxPrice));
    }

    // VCP Score
    if (minVcpScore) {
      data = data.filter(r => r.vcp_score >= parseFloat(minVcpScore));
    }

    // Breakout Ready
    if (breakoutReadyOnly) {
      data = data.filter(r => r.breakout_ready);
    }

    // Near 52W High
    if (near52wOnly) {
      data = data.filter(r => r.distance_52w_high <= 5.0);
    }

    // Apply Sorting
    data.sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];

      if (typeof aVal === 'boolean' && typeof bVal === 'boolean') {
        return sortOrder === 'desc' 
          ? (bVal ? 1 : 0) - (aVal ? 1 : 0)
          : (aVal ? 1 : 0) - (bVal ? 1 : 0);
      }

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortOrder === 'desc' ? bVal - aVal : aVal - bVal;
      }

      return sortOrder === 'desc'
        ? String(bVal).localeCompare(String(aVal))
        : String(aVal).localeCompare(String(bVal));
    });

    setFilteredResults(data);
  }, [results, searchQuery, mcapFilter, sectorFilter, minPrice, maxPrice, minVcpScore, breakoutReadyOnly, near52wOnly, sortField, sortOrder]);

  const handleSort = (field: keyof ScannerResult) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  // CSV Export
  const exportData = (format: 'csv' | 'excel') => {
    if (filteredResults.length === 0) return;
    
    // Select headers based on active tab
    let cols: (keyof ScannerResult)[] = ['symbol', 'company_name', 'current_price', 'market_cap'];
    if (activeTab === 'vcp') {
      cols = [...cols, 'vcp_score', 'vcp_category', 'vcp_contractions', 'vcp_latest_contraction', 'volume_dry_up', 'atr_contraction', 'breakout_pivot', 'breakout_ready'];
    } else if (activeTab === 'trend') {
      cols = [...cols, 'trend_template_score', 'sma50', 'sma150', 'sma200', 'distance_52w_high'];
    } else if (activeTab === 'rs') {
      cols = [...cols, 'rs_score', 'rs_rank', 'sector_rank', 'industry_rank'];
    } else if (activeTab === 'breakout') {
      cols = [...cols, 'is_breakout', 'breakout_type', 'breakout_price', 'volume_surge'];
    } else if (activeTab === 'darvas') {
      cols = [...cols, 'darvas_status', 'darvas_top', 'darvas_bottom', 'darvas_days'];
    }
    
    const headers = cols.join(",") + "\n";
    const rows = filteredResults.map(row => 
      cols.map(col => `"${String(row[col]).replace(/"/g, '""')}"`).join(",")
    ).join("\n");
    
    const blob = new Blob([headers + rows], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const suffix = format === 'csv' ? 'csv' : 'csv'; // Simple fallback
    link.setAttribute("href", url);
    link.setAttribute("download", `institutional_scan_${activeTab}_${Date.now()}.${suffix}`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 text-slate-100 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-slate-900/50 p-6 rounded-2xl border border-slate-800 backdrop-blur">
        <div>
          <h1 className="text-3xl font-display font-black tracking-tight bg-gradient-to-r from-brand-400 to-purple-500 bg-clip-text text-transparent">
            Institutional VCP & Breakout Intelligence
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Professional volatility contraction and institutional accumulation scanner. Powered by real EOD market data.
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <UniverseFilter size="sm" showCount={true} />
          {scanStatus.is_scanning ? (
            <div className="flex items-center gap-3 bg-brand-900/20 px-4 py-2.5 rounded-xl border border-brand-500/30">
              <RefreshCw className="animate-spin text-brand-400" size={16} />
              <div className="text-xs font-semibold">
                Scanning NSE universe ({Math.round(scanStatus.progress)}%)
              </div>
              <div className="w-20 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div className="bg-brand-500 h-1.5" style={{ width: `${scanStatus.progress}%` }}></div>
              </div>
            </div>
          ) : (
            <button
              onClick={triggerScan}
              className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-brand-600 to-purple-600 hover:from-brand-500 hover:to-purple-500 text-white text-xs font-bold rounded-xl transition-all shadow-lg shadow-brand-500/10 hover:shadow-brand-500/20 active:scale-95"
            >
              <Play size={14} fill="white" />
              Run Universe Scan
            </button>
          )}
          
          <button
            onClick={loadData}
            className="p-2.5 bg-slate-800 hover:bg-slate-700 rounded-xl border border-slate-700 transition-colors text-slate-300"
            title="Refresh Scan Data"
          >
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      {/* 1. Institutional Opportunity Dashboard */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        {[
          { label: 'Total Stocks Scanned', val: stats?.total_scanned ?? 0, color: 'border-slate-800' },
          { label: 'VCP Candidates', val: stats?.vcp_candidates ?? 0, color: 'border-amber-500/30 text-amber-400' },
          { label: 'Breakout Ready Stocks', val: stats?.breakout_ready ?? 0, color: 'border-emerald-500/30 text-emerald-400' },
          { label: 'Fresh Breakouts', val: stats?.fresh_breakouts ?? 0, color: 'border-indigo-500/30 text-indigo-400' },
          { label: 'Near 52W High Stocks', val: stats?.near_52w_high ?? 0, color: 'border-sky-500/30 text-sky-400' },
          { label: 'Relative Strength Leaders', val: stats?.rs_leaders ?? 0, color: 'border-purple-500/30 text-purple-400' }
        ].map((c, i) => (
          <div key={i} className={`bg-slate-900/40 p-5 rounded-2xl border ${c.color} flex flex-col justify-between backdrop-blur`}>
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{c.label}</div>
            <div className="text-3xl font-display font-black tracking-tight mt-3">{c.val}</div>
          </div>
        ))}
      </div>

      {/* 2. Filters & Advanced Screening panel */}
      <div className="bg-slate-900/30 border border-slate-800 rounded-2xl p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2 font-display font-bold text-sm text-slate-300">
            <Sliders size={16} className="text-brand-400" />
            Advanced Scanner Filters
          </div>
          <button 
            onClick={() => {
              setMcapFilter('all');
              setSectorFilter('all');
              setMinPrice('');
              setMaxPrice('');
              setMinVcpScore('60');
              setBreakoutReadyOnly(false);
              setNear52wOnly(false);
              setSearchQuery('');
            }}
            className="text-xs font-semibold text-slate-500 hover:text-slate-300 transition-colors"
          >
            Clear Filters
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3.5 top-3.5 text-slate-500" size={16} />
            <input
              type="text"
              placeholder="Search symbol or company..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950/60 border border-slate-850 hover:border-slate-800 focus:border-brand-500 rounded-xl py-3 pl-10 pr-4 text-xs text-slate-200 placeholder-slate-600 focus:outline-none transition-all"
            />
          </div>

          {/* Market Cap */}
          <div>
            <select
              value={mcapFilter}
              onChange={(e) => setMcapFilter(e.target.value)}
              className="w-full bg-slate-950/60 border border-slate-850 hover:border-slate-800 focus:border-brand-500 rounded-xl p-3 text-xs text-slate-200 focus:outline-none transition-all"
            >
              <option value="all">Market Cap: All Caps</option>
              <option value="large">Large Cap (&gt;20,000 Cr)</option>
              <option value="mid">Mid Cap (5,000-20,000 Cr)</option>
              <option value="small">Small Cap (&lt;5,000 Cr)</option>
            </select>
          </div>

          {/* Sector */}
          <div>
            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              className="w-full bg-slate-950/60 border border-slate-850 hover:border-slate-800 focus:border-brand-500 rounded-xl p-3 text-xs text-slate-200 focus:outline-none transition-all"
            >
              <option value="all">Sector: All Sectors</option>
              {sectors.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* VCP Score */}
          <div>
            <select
              value={minVcpScore}
              onChange={(e) => setMinVcpScore(e.target.value)}
              className="w-full bg-slate-950/60 border border-slate-850 hover:border-slate-800 focus:border-brand-500 rounded-xl p-3 text-xs text-slate-200 focus:outline-none transition-all"
            >
              <option value="0">Min VCP Score: All</option>
              <option value="90">Elite (90-100)</option>
              <option value="80">Excellent (80-89)</option>
              <option value="70">Good (70-79)</option>
              <option value="60">Watchlist (60-69)</option>
            </select>
          </div>
        </div>

        {/* Extra Filters */}
        <div className="flex flex-wrap items-center gap-6 pt-2 text-xs font-semibold text-slate-400">
          <label className="flex items-center gap-2.5 cursor-pointer hover:text-slate-200 select-none">
            <input
              type="checkbox"
              checked={breakoutReadyOnly}
              onChange={(e) => setBreakoutReadyOnly(e.target.checked)}
              className="rounded border-slate-800 bg-slate-950 text-brand-600 focus:ring-brand-500 w-4 h-4"
            />
            Breakout Ready Only (VCP &lt;3% from pivot)
          </label>

          <label className="flex items-center gap-2.5 cursor-pointer hover:text-slate-200 select-none">
            <input
              type="checkbox"
              checked={near52wOnly}
              onChange={(e) => setNear52wOnly(e.target.checked)}
              className="rounded border-slate-800 bg-slate-950 text-brand-600 focus:ring-brand-500 w-4 h-4"
            />
            Near 52W High (Within 5%)
          </label>
        </div>
      </div>

      {/* Tabs Menu & Export */}
      <div className="flex flex-col md:flex-row justify-between items-stretch md:items-center gap-4 border-b border-slate-800 pb-1">
        <div className="flex items-center gap-1 overflow-x-auto no-scrollbar py-1">
          {[
            { id: 'vcp', label: 'VCP Scanner' },
            { id: 'trend', label: 'Minervini Trend' },
            { id: 'rs', label: 'RS Rankings' },
            { id: 'breakout', label: 'Breakouts' },
            { id: 'darvas', label: 'Darvas Box' },
            { id: 'cup_handle', label: 'Cup & Handle' },
            { id: 'double_bottom', label: 'Double Bottom' },
            { id: 'flat_base', label: 'Flat Base' },
            { id: 'volume', label: 'Volume Dry-Up' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`
                px-4 py-2.5 text-xs font-bold rounded-xl transition-all shrink-0
                ${activeTab === tab.id 
                  ? 'bg-slate-800 text-white border border-slate-700 shadow-sm' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }
              `}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 self-end md:self-auto">
          <button
            onClick={() => exportData('csv')}
            className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-xs font-bold text-slate-200 transition-colors"
          >
            <Download size={13} />
            Export CSV
          </button>
          <button
            onClick={() => exportData('excel')}
            className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-xs font-bold text-slate-200 transition-colors"
          >
            <Download size={13} />
            Export Excel
          </button>
        </div>
      </div>

      {/* Main Scanners Tables */}
      <div className="bg-slate-900/40 rounded-2xl border border-slate-800 overflow-hidden backdrop-blur">
        {loading ? (
          <div className="p-12 text-center text-slate-400 space-y-4">
            <RefreshCw className="animate-spin mx-auto text-blue-500" size={32} />
            <div className="space-y-1">
              <p className="font-bold text-sm text-slate-200">Loading {selectedUniverse} Universe...</p>
              <p className="text-xs text-slate-500">Fetching stocks and running institutional VCP scanner...</p>
            </div>
          </div>
        ) : filteredResults.length === 0 ? (
          <div className="p-16 text-center text-slate-400 space-y-6 max-w-md mx-auto">
            <div className="p-4 bg-slate-900/60 rounded-full w-fit mx-auto border border-slate-800">
              <AlertCircle className="text-slate-500" size={32} />
            </div>
            <div className="space-y-2">
              <p className="font-display font-bold text-base text-slate-200">No stocks matched the current scanner filters</p>
              <div className="text-xs text-slate-500 space-y-1 bg-slate-950/40 p-3 rounded-xl border border-slate-900 font-mono text-left">
                <div>• Universe: <span className="text-blue-400 font-bold">{selectedUniverse}</span></div>
                <div>• Stocks Scanned: <span className="text-slate-300 font-bold">{stats?.total_scanned ?? 0}</span></div>
              </div>
            </div>
            <p className="text-xs text-slate-500">
              Try adjusting your active filters (e.g. lowering the VCP score threshold, changing the market cap filter, or searching for a different symbol).
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-900/80 border-b border-slate-855 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('symbol')}>
                    <span className="flex items-center gap-1.5">Symbol <ArrowUpDown size={10} /></span>
                  </th>
                  <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('company_name')}>
                    <span className="flex items-center gap-1.5">Company Name <ArrowUpDown size={10} /></span>
                  </th>
                  <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('current_price')}>
                    <span className="flex items-center gap-1.5">Price <ArrowUpDown size={10} /></span>
                  </th>

                  {/* VCP SCANNER COLUMNS */}
                  {activeTab === 'vcp' && (
                    <>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('distance_52w_high')}>
                        <span className="flex items-center gap-1.5">Dist. 52W High <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('vcp_score')}>
                        <span className="flex items-center gap-1.5">VCP Score <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('vcp_contractions')}>
                        <span className="flex items-center gap-1.5">Contractions <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('vcp_latest_contraction')}>
                        <span className="flex items-center gap-1.5">Last Contraction <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('volume_dry_up')}>
                        <span className="flex items-center gap-1.5">Vol Dry-Up <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('breakout_pivot')}>
                        <span className="flex items-center gap-1.5">Pivot <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('breakout_ready')}>
                        <span className="flex items-center gap-1.5">Ready <ArrowUpDown size={10} /></span>
                      </th>
                    </>
                  )}

                  {/* TREND TEMPLATE SCANNER COLUMNS */}
                  {activeTab === 'trend' && (
                    <>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('trend_template_score')}>
                        <span className="flex items-center gap-1.5">Template Score <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('sma50')}>
                        <span className="flex items-center gap-1.5">SMA50 <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('sma150')}>
                        <span className="flex items-center gap-1.5">SMA150 <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('sma200')}>
                        <span className="flex items-center gap-1.5">SMA200 <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('distance_52w_high')}>
                        <span className="flex items-center gap-1.5">Dist. 52W High <ArrowUpDown size={10} /></span>
                      </th>
                    </>
                  )}

                  {/* RELATIVE STRENGTH COLUMNS */}
                  {activeTab === 'rs' && (
                    <>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('rs_score')}>
                        <span className="flex items-center gap-1.5">RS Score <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('rs_rank')}>
                        <span className="flex items-center gap-1.5">Overall Rank <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('sector_rank')}>
                        <span className="flex items-center gap-1.5">Sector Rank <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('industry_rank')}>
                        <span className="flex items-center gap-1.5">Industry Rank <ArrowUpDown size={10} /></span>
                      </th>
                    </>
                  )}

                  {/* BREAKOUT COLUMNS */}
                  {activeTab === 'breakout' && (
                    <>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('breakout_price')}>
                        <span className="flex items-center gap-1.5">Breakout Pivot <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('volume_surge')}>
                        <span className="flex items-center gap-1.5">Volume Surge % <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('breakout_type')}>
                        <span className="flex items-center gap-1.5">Type <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('is_breakout')}>
                        <span className="flex items-center gap-1.5">Status <ArrowUpDown size={10} /></span>
                      </th>
                    </>
                  )}

                  {/* DARVAS BOX COLUMNS */}
                  {activeTab === 'darvas' && (
                    <>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('darvas_top')}>
                        <span className="flex items-center gap-1.5">Box Top <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('darvas_bottom')}>
                        <span className="flex items-center gap-1.5">Box Bottom <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('darvas_days')}>
                        <span className="flex items-center gap-1.5">Days Inside <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('darvas_status')}>
                        <span className="flex items-center gap-1.5">Darvas Status <ArrowUpDown size={10} /></span>
                      </th>
                    </>
                  )}

                  {/* CUP & HANDLE COLUMNS */}
                  {activeTab === 'cup_handle' && (
                    <>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('breakout_pivot')}>
                        <span className="flex items-center gap-1.5">Pivot Price <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('cup_handle_confidence')}>
                        <span className="flex items-center gap-1.5">Confidence Score <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('flat_base_depth')}>
                        <span className="flex items-center gap-1.5">Cup Depth % <ArrowUpDown size={10} /></span>
                      </th>
                    </>
                  )}

                  {/* DOUBLE BOTTOM COLUMNS */}
                  {activeTab === 'double_bottom' && (
                    <>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('breakout_pivot')}>
                        <span className="flex items-center gap-1.5">Mid Pivot Price <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('double_bottom_confidence')}>
                        <span className="flex items-center gap-1.5">Confidence Score <ArrowUpDown size={10} /></span>
                      </th>
                    </>
                  )}

                  {/* FLAT BASE COLUMNS */}
                  {activeTab === 'flat_base' && (
                    <>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('flat_base_length')}>
                        <span className="flex items-center gap-1.5">Base Length (Days) <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('flat_base_depth')}>
                        <span className="flex items-center gap-1.5">Base Correction <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('breakout_pivot')}>
                        <span className="flex items-center gap-1.5">Base Pivot <ArrowUpDown size={10} /></span>
                      </th>
                    </>
                  )}

                  {/* VOLUME DRY-UP COLUMNS */}
                  {activeTab === 'volume' && (
                    <>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('volume_contraction')}>
                        <span className="flex items-center gap-1.5">Vol Contraction <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('supply_drying_score')}>
                        <span className="flex items-center gap-1.5">Supply Dry Score <ArrowUpDown size={10} /></span>
                      </th>
                      <th className="p-4 select-none cursor-pointer hover:bg-slate-800/50" onClick={() => handleSort('accumulation_score')}>
                        <span className="flex items-center gap-1.5">Accumulation Score <ArrowUpDown size={10} /></span>
                      </th>
                    </>
                  )}

                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-850/50 text-xs font-semibold">
                {filteredResults.map((row) => (
                  <tr 
                    key={row.symbol}
                    className="hover:bg-slate-800/20 transition-all group cursor-pointer"
                    onClick={() => onNavigate(Page.INSTITUTIONAL_STOCK_DETAIL, row.symbol)}
                  >
                    <td className="p-4 font-bold text-brand-400 group-hover:text-brand-300">
                      {row.symbol}
                    </td>
                    <td className="p-4 max-w-[200px] truncate text-slate-300">
                      {row.company_name}
                    </td>
                    <td className="p-4 font-mono text-slate-200">
                      ₹{row.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>

                    {/* VCP TABLE CELLS */}
                    {activeTab === 'vcp' && (
                      <>
                        <td className="p-4 font-mono text-slate-400">
                          {safeFixed(row.distance_52w_high, 2)}%
                        </td>
                        <td className="p-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            row.vcp_score >= 90 ? 'bg-amber-950/40 text-amber-400 border border-amber-500/20' :
                            row.vcp_score >= 80 ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-500/20' :
                            row.vcp_score >= 70 ? 'bg-sky-950/40 text-sky-400 border border-sky-500/20' :
                            'bg-slate-800/40 text-slate-400 border border-slate-700/20'
                          }`}>
                            {safeFixed(row.vcp_score, 1)} ({row.vcp_category})
                          </span>
                        </td>
                        <td className="p-4 text-center font-mono">{row.vcp_contractions}T</td>
                        <td className="p-4 font-mono text-amber-500">{safeFixed(row.vcp_latest_contraction, 2)}%</td>
                        <td className="p-4 font-mono text-emerald-500">{safeFixed(row.volume_dry_up, 2)}%</td>
                        <td className="p-4 font-mono">₹{safeFixed(row.breakout_pivot, 2)}</td>
                        <td className="p-4">
                          {row.breakout_ready ? (
                            <span className="flex items-center gap-1 text-emerald-400 font-bold text-[10px]">
                              <CheckCircle size={12} fill="rgba(16, 185, 129, 0.2)" /> Ready
                            </span>
                          ) : (
                            <span className="text-slate-500 font-bold text-[10px]">Consolidating</span>
                          )}
                        </td>
                      </>
                    )}

                    {/* TREND TEMPLATE CELLS */}
                    {activeTab === 'trend' && (
                      <>
                        <td className="p-4">
                          <div className="flex items-center gap-2">
                            <div className="w-16 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                              <div className="bg-brand-500 h-1.5" style={{ width: `${row.trend_template_score}%` }}></div>
                            </div>
                            <span className="font-mono text-slate-300">{safeFixed(row.trend_template_score, 0)}%</span>
                          </div>
                        </td>
                        <td className="p-4 font-mono text-slate-400">₹{safeFixed(row.sma50, 1)}</td>
                        <td className="p-4 font-mono text-slate-400">₹{safeFixed(row.sma150, 1)}</td>
                        <td className="p-4 font-mono text-slate-400">₹{safeFixed(row.sma200, 1)}</td>
                        <td className="p-4 font-mono text-slate-400">{safeFixed(row.distance_52w_high, 2)}%</td>
                      </>
                    )}

                    {/* RS RANKINGS CELLS */}
                    {activeTab === 'rs' && (
                      <>
                        <td className="p-4 font-mono font-bold text-slate-200">{safeFixed(row.rs_score, 1)}</td>
                        <td className="p-4 font-mono">#{row.rs_rank}</td>
                        <td className="p-4 font-mono text-slate-400">#{row.sector_rank}</td>
                        <td className="p-4 font-mono text-slate-400">#{row.industry_rank}</td>
                      </>
                    )}

                    {/* BREAKOUT CELLS */}
                    {activeTab === 'breakout' && (
                      <>
                        <td className="p-4 font-mono">₹{safeFixed(row.breakout_price, 2)}</td>
                        <td className={`p-4 font-mono ${row.volume_surge >= 50 ? 'text-emerald-400' : 'text-slate-400'}`}>
                          {safeFixed(row.volume_surge, 1)}%
                        </td>
                        <td className="p-4">
                          <span className="px-2 py-0.5 bg-slate-800 rounded text-[10px] text-slate-300">
                            {row.breakout_type}
                          </span>
                        </td>
                        <td className="p-4">
                          {row.is_breakout ? (
                            <span className="px-2 py-0.5 bg-emerald-950/40 text-emerald-400 border border-emerald-500/20 rounded text-[10px] font-bold">
                              Confirmed
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 bg-slate-800/40 text-slate-400 rounded text-[10px]">
                              Consolidating
                            </span>
                          )}
                        </td>
                      </>
                    )}

                    {/* DARVAS CELLS */}
                    {activeTab === 'darvas' && (
                      <>
                        <td className="p-4 font-mono">₹{safeFixed(row.darvas_top, 2)}</td>
                        <td className="p-4 font-mono">₹{safeFixed(row.darvas_bottom, 2)}</td>
                        <td className="p-4 font-mono">{row.darvas_days} Days</td>
                        <td className="p-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            row.darvas_status.includes('Breakout') ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-500/20' :
                            row.darvas_status.includes('Breakdown') ? 'bg-red-950/40 text-red-400 border border-red-500/20' :
                            'bg-slate-800/40 text-slate-400'
                          }`}>
                            {row.darvas_status}
                          </span>
                        </td>
                      </>
                    )}

                    {/* CUP & HANDLE CELLS */}
                    {activeTab === 'cup_handle' && (
                      <>
                        <td className="p-4 font-mono">₹{safeFixed(row.breakout_price, 2)}</td>
                        <td className="p-4 font-mono">{safeFixed(row.cup_handle_confidence, 1)} / 100</td>
                        <td className="p-4 font-mono">{safeFixed(row.flat_base_depth, 2)}%</td>
                      </>
                    )}

                    {/* DOUBLE BOTTOM CELLS */}
                    {activeTab === 'double_bottom' && (
                      <>
                        <td className="p-4 font-mono">₹{safeFixed(row.breakout_pivot, 2)}</td>
                        <td className="p-4 font-mono">{safeFixed(row.double_bottom_confidence, 1)} / 100</td>
                      </>
                    )}

                    {/* FLAT BASE CELLS */}
                    {activeTab === 'flat_base' && (
                      <>
                        <td className="p-4 font-mono">{row.flat_base_length} Days</td>
                        <td className="p-4 font-mono text-amber-500">{safeFixed(row.flat_base_depth, 2)}%</td>
                        <td className="p-4 font-mono">₹{safeFixed(row.breakout_pivot, 2)}</td>
                      </>
                    )}

                    {/* VOLUME CELLS */}
                    {activeTab === 'volume' && (
                      <>
                        <td className={`p-4 font-mono ${row.volume_contraction >= 40 ? 'text-emerald-400 font-bold' : 'text-slate-400'}`}>
                          {safeFixed(row.volume_contraction, 2)}%
                        </td>
                        <td className="p-4 font-mono">{safeFixed(row.supply_drying_score, 1)}</td>
                        <td className="p-4 font-mono">{safeFixed(row.accumulation_score, 1)}%</td>
                      </>
                    )}

                    <td className="p-4 text-right">
                      <button 
                        className="px-3 py-1.5 bg-slate-800 hover:bg-brand-600 hover:text-white rounded-lg border border-slate-700 hover:border-brand-500 transition-all text-[11px] font-bold"
                        onClick={(e) => {
                          e.stopPropagation();
                          onNavigate(Page.INSTITUTIONAL_STOCK_DETAIL, row.symbol);
                        }}
                      >
                        Analyze
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default InstitutionalScanner;
