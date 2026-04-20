import React, { useState, useEffect, useCallback } from 'react';
import {
  Shield, TrendingUp, TrendingDown, AlertTriangle, ChevronDown, ChevronUp,
  RefreshCw, Filter, Search, Star, Target, BarChart3, PieChart, ArrowUpRight,
  ArrowDownRight, Zap, Award, Eye, DollarSign, Building2, Users, Briefcase,
  Loader2, X, ChevronRight, Clock, Activity, Globe
} from 'lucide-react';
import { api } from '../services/api';

// --- Types ---
interface StockScore {
  symbol: string;
  company_name?: string;
  sector?: string;
  cmp?: number;
  market_cap_cr?: number;
  overall_score: number;
  rank?: number;
  conviction_level?: string;
  promoter_score?: number;
  institutional_score?: number;
  earnings_score?: number;
  debt_score?: number;
  technical_score?: number;
  sector_score?: number;
  market_score?: number;
  order_book_score?: number;
  pct_from_52w_high?: number;
  relative_strength?: number;
  promoter_holding?: number;
  fii_holding?: number;
  dii_holding?: number;
  revenue_growth?: number;
  profit_growth?: number;
  roe_latest?: number;
  debt_to_equity?: number;
  score_breakdown?: Record<string, number>;
  // Conviction list extras
  why_buy?: string;
  risk_factors?: string;
  buy_zone_low?: number;
  buy_zone_high?: number;
  stop_loss?: number;
  target_1y?: number;
  target_3y?: number;
}

interface SectorData {
  sector: string;
  sector_score?: number;
  stock_count?: number;
  rotation_signal?: string;
  leaders?: Array<{ symbol: string; score: number }>;
  outlook_6m?: string;
}

type TabId = 'conviction' | 'rankings' | 'sectors' | 'portfolios' | 'avoid';

// --- Score Bar Component ---

const convictionColor = (level?: string) => {
  switch (level) {
    case 'EXTREME': return { bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30', ring: 'ring-emerald-500/20' };
    case 'VERY_HIGH': return { bg: 'bg-green-500/15', text: 'text-green-400', border: 'border-green-500/30', ring: 'ring-green-500/20' };
    case 'HIGH': return { bg: 'bg-blue-500/15', text: 'text-blue-400', border: 'border-blue-500/30', ring: 'ring-blue-500/20' };
    case 'MODERATE': return { bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30', ring: 'ring-amber-500/20' };
    case 'AVOID': return { bg: 'bg-red-500/15', text: 'text-red-400', border: 'border-red-500/30', ring: 'ring-red-500/20' };
    default: return { bg: 'bg-slate-500/15', text: 'text-slate-400', border: 'border-slate-500/30', ring: 'ring-slate-500/20' };
  }
};

const rotationColor = (signal?: string) => {
  switch (signal) {
    case 'ACCUMULATE': return 'text-emerald-400 bg-emerald-500/10';
    case 'HOLD': return 'text-blue-400 bg-blue-500/10';
    case 'REDUCE': return 'text-amber-400 bg-amber-500/10';
    case 'AVOID': return 'text-red-400 bg-red-500/10';
    default: return 'text-slate-400 bg-slate-500/10';
  }
};

const fmt = (v?: number | null, dec: number = 1) => v != null ? v.toFixed(dec) : '—';
const fmtPct = (v?: number | null) => v != null ? `${v >= 0 ? '+' : ''}${v.toFixed(1)}%` : '—';
const fmtCr = (v?: number | null) => {
  if (v == null) return '—';
  if (v >= 100000) return `₹${(v / 100000).toFixed(1)}L Cr`;
  if (v >= 1000) return `₹${(v / 1000).toFixed(1)}K Cr`;
  return `₹${v.toFixed(0)} Cr`;
};

// --- Score Bar Component ---
const ScoreBar: React.FC<{ score?: number; label: string; color?: string }> = ({ score, label, color }) => {
  const s = score ?? 0;
  const barColor = s >= 70 ? 'bg-emerald-500' : s >= 50 ? 'bg-blue-500' : s >= 30 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] text-slate-500 w-16 truncate" title={label}>{label}</span>
      <div className="flex-1 h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${color || barColor}`} style={{ width: `${Math.min(100, s)}%` }} />
      </div>
      <span className="text-[11px] text-slate-400 w-7 text-right font-mono">{fmt(s, 0)}</span>
    </div>
  );
};

// === MAIN COMPONENT ===
const TradeScreener: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('conviction');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runningScreener, setRunningScreener] = useState(false);

  // Data states
  const [convictionList, setConvictionList] = useState<StockScore[]>([]);
  const [rankings, setRankings] = useState<StockScore[]>([]);
  const [avoidList, setAvoidList] = useState<StockScore[]>([]);
  const [sectors, setSectors] = useState<SectorData[]>([]);
  const [portfolios, setPortfolios] = useState<any>(null);
  const [status, setStatus] = useState<any>(null);

  // Filters
  const [sectorFilter, setSectorFilter] = useState('');
  const [convictionFilter, setConvictionFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Detail
  const [selectedStock, setSelectedStock] = useState<StockScore | null>(null);

  // Meta
  const [totalCount, setTotalCount] = useState(0);
  const [availableSectors, setAvailableSectors] = useState<string[]>([]);

  // --- API Calls ---
  const loadConvictionList = useCallback(async () => {
    try {
      const data = await api.getConvictionList('BUY');
      setConvictionList(data.data || []);
    } catch (e: any) { console.error('Conviction:', e); }
  }, []);

  const loadRankings = useCallback(async () => {
    try {
      const params: any = { limit: 100 };
      if (sectorFilter) params.sector = sectorFilter;
      if (convictionFilter) params.conviction = convictionFilter;
      const data = await api.getScreenerRankings(params);
      setRankings(data.data || []);
      setTotalCount(data.total_count || 0);
      setAvailableSectors(data.filters?.available_sectors || []);
    } catch (e: any) { console.error('Rankings:', e); }
  }, [sectorFilter, convictionFilter]);

  const loadAvoidList = useCallback(async () => {
    try {
      const data = await api.getAvoidList();
      setAvoidList(data.data || []);
    } catch (e: any) { console.error('Avoid:', e); }
  }, []);

  const loadSectors = useCallback(async () => {
    try {
      const data = await api.getScreenerSectorRotation();
      setSectors(data.data || []);
    } catch (e: any) { console.error('Sectors:', e); }
  }, []);

  const loadPortfolios = useCallback(async () => {
    try {
      const data = await api.getScreenerPortfolios();
      setPortfolios(data.portfolios || null);
    } catch (e: any) { console.error('Portfolios:', e); }
  }, []);

  const loadStatus = useCallback(async () => {
    try {
      const data = await api.getScreenerStatus();
      setStatus(data);
    } catch (e: any) { console.error('Status:', e); }
  }, []);

  const runScreener = async (skipFinancials = false) => {
    setRunningScreener(true);
    setError(null);
    try {
      const data = await api.runScreener(skipFinancials);
      if (data.status === 'success') {
        loadAll();
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunningScreener(false);
    }
  };

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([loadStatus(), loadConvictionList(), loadRankings(), loadSectors(), loadPortfolios(), loadAvoidList()]);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [loadStatus, loadConvictionList, loadRankings, loadSectors, loadPortfolios, loadAvoidList]);

  useEffect(() => { loadAll(); }, []);
  useEffect(() => { if (activeTab === 'rankings') loadRankings(); }, [sectorFilter, convictionFilter]);

  const filteredRankings = rankings.filter(s =>
    !searchQuery || s.symbol?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.sector?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // --- TAB CONTENT RENDERERS ---

  const tabs: { id: TabId; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: 'conviction', label: 'Conviction List', icon: <Star size={16} />, count: convictionList.length },
    { id: 'rankings', label: 'Full Rankings', icon: <BarChart3 size={16} />, count: totalCount },
    { id: 'sectors', label: 'Sector Rotation', icon: <PieChart size={16} />, count: sectors.length },
    { id: 'portfolios', label: 'Model Portfolios', icon: <Briefcase size={16} /> },
    { id: 'avoid', label: 'Avoid List', icon: <AlertTriangle size={16} />, count: avoidList.length },
  ];

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Shield className="text-white" size={22} />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
                Institutional Trade Screener
              </h1>
              <p className="text-xs text-slate-500 font-medium mt-0.5">
                NIFTY 500 · 8-Dimension Conviction Engine · {status?.total_stocks_scored || 0} Stocks Scored
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {status?.latest_score_date && (
            <div className="flex items-center gap-1.5 text-xs text-slate-500 bg-slate-800/50 px-3 py-1.5 rounded-lg border border-slate-700/50">
              <Clock size={12} /> Last Run: {status.latest_score_date}
            </div>
          )}
          <button
            onClick={() => loadAll()}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 rounded-lg hover:bg-slate-700 border border-slate-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button
            onClick={() => runScreener(true)}
            disabled={runningScreener}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-colors disabled:opacity-50 shadow-lg shadow-indigo-600/20"
          >
            {runningScreener ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
            {runningScreener ? 'Running...' : 'Run Screener'}
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2.5">
          <AlertTriangle size={16} /> {error}
          <button onClick={() => setError(null)} className="ml-auto"><X size={14} /></button>
        </div>
      )}

      {/* Status Bar: Score Distribution */}
      {status?.conviction_distribution && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {['EXTREME', 'VERY_HIGH', 'HIGH', 'MODERATE', 'AVOID'].map(level => {
            const c = convictionColor(level);
            const count = status.conviction_distribution?.[level] || 0;
            return (
              <div key={level} className={`${c.bg} ${c.border} border rounded-xl px-4 py-3 flex items-center gap-3`}>
                <div className={`w-2 h-2 rounded-full ${c.text === 'text-emerald-400' ? 'bg-emerald-400' : c.text === 'text-green-400' ? 'bg-green-400' : c.text === 'text-blue-400' ? 'bg-blue-400' : c.text === 'text-amber-400' ? 'bg-amber-400' : 'bg-red-400'}`} />
                <div>
                  <div className={`text-lg font-bold ${c.text}`}>{count}</div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">{level.replace('_', ' ')}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex gap-1 bg-slate-800/50 p-1 rounded-xl border border-slate-700/50 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
            }`}
          >
            {tab.icon}
            {tab.label}
            {tab.count != null && tab.count > 0 && (
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                activeTab === tab.id ? 'bg-white/20' : 'bg-slate-700'
              }`}>{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="flex flex-col items-center gap-3 text-slate-400">
            <Loader2 size={32} className="animate-spin text-indigo-400" />
            <span className="text-sm">Loading screener data...</span>
          </div>
        </div>
      )}

      {/* Tab Content */}
      {!loading && (
        <>
          {/* === CONVICTION LIST TAB === */}
          {activeTab === 'conviction' && (
            <div className="space-y-3">
              {convictionList.length === 0 ? (
                <div className="text-center py-16 text-slate-500">
                  <Shield size={48} className="mx-auto mb-3 opacity-30" />
                  <p className="text-sm">No conviction data yet. Run the screener to generate results.</p>
                </div>
              ) : (
                convictionList.map((stock, i) => (
                  <div
                    key={stock.symbol}
                    onClick={() => setSelectedStock(stock)}
                    className={`bg-slate-800/60 backdrop-blur border border-slate-700/50 rounded-xl p-4 cursor-pointer hover:border-indigo-500/30 hover:bg-slate-800/80 transition-all group`}
                  >
                    <div className="flex flex-col lg:flex-row lg:items-center gap-4">
                      {/* Rank Badge */}
                      <div className="flex items-center gap-4 min-w-0">
                        <div className={`w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold shrink-0 ${
                          i < 3 ? 'bg-gradient-to-br from-amber-500 to-orange-600 text-white shadow-lg shadow-amber-500/20' :
                          i < 10 ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30' :
                          'bg-slate-700 text-slate-400'
                        }`}>
                          #{stock.rank || i + 1}
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-white text-sm truncate">{stock.symbol}</span>
                            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${convictionColor(stock.conviction_level).bg} ${convictionColor(stock.conviction_level).text}`}>
                              {stock.conviction_level?.replace('_', ' ')}
                            </span>
                          </div>
                          <div className="text-xs text-slate-500 truncate">{stock.sector || stock.company_name}</div>
                        </div>
                      </div>

                      {/* Score & Price */}
                      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 lg:ml-auto text-xs">
                        {/* Overall Score */}
                        <div className="text-center">
                          <div className="text-lg font-black text-white">{fmt(stock.overall_score, 0)}</div>
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Score</div>
                        </div>
                        {/* CMP */}
                        <div className="text-center">
                          <div className="text-sm font-semibold text-slate-200">₹{fmt(stock.cmp, 2)}</div>
                          <div className="text-[10px] text-slate-500">CMP</div>
                        </div>
                        {/* Market Cap */}
                        <div className="text-center">
                          <div className="text-sm font-medium text-slate-300">{fmtCr(stock.market_cap_cr)}</div>
                          <div className="text-[10px] text-slate-500">M.Cap</div>
                        </div>
                        {/* ROE */}
                        <div className="text-center hidden sm:block">
                          <div className={`text-sm font-medium ${(stock.roe ?? 0) > 0.15 ? 'text-emerald-400' : 'text-slate-300'}`}>
                            {stock.roe != null ? `${(stock.roe * 100).toFixed(0)}%` : '—'}
                          </div>
                          <div className="text-[10px] text-slate-500">ROE</div>
                        </div>
                        {/* D/E */}
                        <div className="text-center hidden sm:block">
                          <div className={`text-sm font-medium ${(stock.debt_to_equity ?? 1) < 0.5 ? 'text-emerald-400' : 'text-slate-300'}`}>
                            {fmt(stock.debt_to_equity, 2)}
                          </div>
                          <div className="text-[10px] text-slate-500">D/E</div>
                        </div>
                        {/* FII */}
                        <div className="text-center hidden md:block">
                          <div className="text-sm font-medium text-slate-300">{fmt(stock.fii_holding)}%</div>
                          <div className="text-[10px] text-slate-500">FII</div>
                        </div>
                        {/* Revenue Growth */}
                        <div className="text-center hidden md:block">
                          <div className={`text-sm font-medium ${(stock.sales_growth ?? stock.revenue_growth ?? 0) > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {fmtPct(stock.sales_growth ?? stock.revenue_growth)}
                          </div>
                          <div className="text-[10px] text-slate-500">Rev Gr.</div>
                        </div>
                        {/* Target */}
                        {stock.target_1y && (
                          <div className="text-center hidden lg:block">
                            <div className="text-sm font-medium text-blue-400">₹{fmt(stock.target_1y, 0)}</div>
                            <div className="text-[10px] text-slate-500">1Y Target</div>
                          </div>
                        )}
                        <ChevronRight size={16} className="text-slate-600 group-hover:text-indigo-400 transition-colors hidden lg:block" />
                      </div>
                    </div>

                    {/* Why Buy */}
                    {stock.why_buy && (
                      <div className="mt-3 pt-3 border-t border-slate-700/50">
                        <div className="flex items-start gap-2 text-xs text-emerald-400/80">
                          <Zap size={12} className="mt-0.5 shrink-0" />
                          <span className="line-clamp-1">{stock.why_buy}</span>
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {/* === FULL RANKINGS TAB === */}
          {activeTab === 'rankings' && (
            <div className="space-y-4">
              {/* Filters */}
              <div className="flex flex-wrap gap-3 items-center">
                <div className="relative">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Search symbol or sector..."
                    className="pl-9 pr-4 py-2 text-xs bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none w-56"
                  />
                </div>
                <select
                  value={sectorFilter}
                  onChange={e => setSectorFilter(e.target.value)}
                  className="px-3 py-2 text-xs bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-indigo-500 focus:outline-none"
                >
                  <option value="">All Sectors</option>
                  {availableSectors.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <select
                  value={convictionFilter}
                  onChange={e => setConvictionFilter(e.target.value)}
                  className="px-3 py-2 text-xs bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-indigo-500 focus:outline-none"
                >
                  <option value="">All Conviction</option>
                  {['EXTREME', 'VERY_HIGH', 'HIGH', 'MODERATE', 'AVOID'].map(c => (
                    <option key={c} value={c}>{c.replace('_', ' ')}</option>
                  ))}
                </select>
                <span className="text-xs text-slate-500 ml-auto">{filteredRankings.length} / {totalCount} stocks</span>
              </div>

              {/* Rankings Table */}
              <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-slate-700/50">
                        {['#', 'Symbol', 'Sector', 'Score', 'Conv.', 'CMP', 'Prom', 'Inst', 'Earn', 'Debt', 'Tech', 'Sector', '52W%'].map(h => (
                          <th key={h} className="px-3 py-3 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/30">
                      {filteredRankings.map((s) => {
                        const cc = convictionColor(s.conviction_level);
                        return (
                          <tr key={s.symbol} onClick={() => setSelectedStock(s)} className="hover:bg-slate-700/30 cursor-pointer transition-colors">
                            <td className="px-3 py-2.5 font-mono text-slate-500">{s.rank}</td>
                            <td className="px-3 py-2.5 font-semibold text-white">{s.symbol}</td>
                            <td className="px-3 py-2.5 text-slate-400 max-w-[120px] truncate">{s.sector || '—'}</td>
                            <td className="px-3 py-2.5">
                              <span className="font-bold text-white">{fmt(s.overall_score, 0)}</span>
                            </td>
                            <td className="px-3 py-2.5">
                              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${cc.bg} ${cc.text}`}>
                                {s.conviction_level?.replace('_', ' ')}
                              </span>
                            </td>
                            <td className="px-3 py-2.5 text-slate-200 font-medium">₹{fmt(s.cmp, 2)}</td>
                            <td className="px-3 py-2.5 text-slate-400">{fmt(s.promoter_score, 0)}</td>
                            <td className="px-3 py-2.5 text-slate-400">{fmt(s.institutional_score, 0)}</td>
                            <td className="px-3 py-2.5 text-slate-400">{fmt(s.earnings_score, 0)}</td>
                            <td className="px-3 py-2.5 text-slate-400">{fmt(s.debt_score, 0)}</td>
                            <td className="px-3 py-2.5 text-slate-400">{fmt(s.technical_score, 0)}</td>
                            <td className="px-3 py-2.5 text-slate-400">{fmt(s.sector_score, 0)}</td>
                            <td className="px-3 py-2.5">
                              <span className={`${(s.pct_from_52w_high ?? -100) >= -10 ? 'text-emerald-400' : 'text-slate-500'}`}>
                                {fmtPct(s.pct_from_52w_high)}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                {filteredRankings.length === 0 && (
                  <div className="text-center py-12 text-slate-500 text-sm">No ranking data available.</div>
                )}
              </div>
            </div>
          )}

          {/* === SECTOR ROTATION TAB === */}
          {activeTab === 'sectors' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sectors.length === 0 ? (
                <div className="col-span-full text-center py-16 text-slate-500 text-sm">No sector data.</div>
              ) : (
                sectors.map(sector => (
                  <div key={sector.sector} className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 hover:border-indigo-500/20 transition-all">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h3 className="text-sm font-bold text-white">{sector.sector}</h3>
                        <span className="text-[10px] text-slate-500">{sector.stock_count} stocks</span>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-black text-white">{fmt(sector.sector_score, 0)}</div>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${rotationColor(sector.rotation_signal)}`}>
                          {sector.rotation_signal}
                        </span>
                      </div>
                    </div>

                    {/* Score Bar */}
                    <div className="mb-3">
                      <div className="w-full h-2 bg-slate-700/50 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${
                            (sector.sector_score ?? 0) >= 60 ? 'bg-gradient-to-r from-emerald-500 to-green-400' :
                            (sector.sector_score ?? 0) >= 40 ? 'bg-gradient-to-r from-blue-500 to-cyan-400' :
                            'bg-gradient-to-r from-amber-500 to-red-400'
                          }`}
                          style={{ width: `${Math.min(100, sector.sector_score ?? 0)}%` }}
                        />
                      </div>
                    </div>

                    {/* Outlook */}
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-[10px] text-slate-500">6M Outlook:</span>
                      <span className={`text-[10px] font-semibold ${
                        sector.outlook_6m === 'BULLISH' ? 'text-emerald-400' :
                        sector.outlook_6m === 'BEARISH' ? 'text-red-400' : 'text-slate-400'
                      }`}>{sector.outlook_6m || '—'}</span>
                    </div>

                    {/* Leaders */}
                    {sector.leaders && sector.leaders.length > 0 && (
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1.5">Leaders</div>
                        <div className="space-y-1">
                          {sector.leaders.slice(0, 3).map((l: any, i: number) => (
                            <div key={l.symbol} className="flex items-center justify-between text-xs">
                              <div className="flex items-center gap-1.5">
                                {i === 0 && <Award size={10} className="text-amber-400" />}
                                <span className="text-slate-300 font-medium">{l.symbol}</span>
                              </div>
                              <span className="text-slate-500 font-mono">{fmt(l.score, 0)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {/* === MODEL PORTFOLIOS TAB === */}
          {activeTab === 'portfolios' && (
            <div className="space-y-6">
              {!portfolios ? (
                <div className="text-center py-16 text-slate-500 text-sm">No portfolio data.</div>
              ) : (
                Object.entries(portfolios).map(([key, port]: [string, any]) => (
                  <div key={key} className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden">
                    <div className={`px-5 py-3 border-b border-slate-700/50 flex items-center justify-between ${
                      key === 'conservative' ? 'bg-gradient-to-r from-emerald-600/10 to-transparent' :
                      key === 'growth' ? 'bg-gradient-to-r from-blue-600/10 to-transparent' :
                      'bg-gradient-to-r from-purple-600/10 to-transparent'
                    }`}>
                      <div className="flex items-center gap-3">
                        {key === 'conservative' ? <Shield size={18} className="text-emerald-400" /> :
                         key === 'growth' ? <TrendingUp size={18} className="text-blue-400" /> :
                         <Zap size={18} className="text-purple-400" />}
                        <div>
                          <h3 className="text-sm font-bold text-white">{port.name}</h3>
                          <p className="text-[10px] text-slate-500">{port.description}</p>
                        </div>
                      </div>
                      <span className="text-xs text-slate-400 font-medium">{port.count} stocks</span>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b border-slate-700/30">
                            {['Symbol', 'Sector', 'Score', 'CMP', 'Buy Zone', 'Stop Loss', 'Target 1Y'].map(h => (
                              <th key={h} className="px-4 py-2.5 text-left text-[10px] font-semibold text-slate-500 uppercase">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700/20">
                          {(port.stocks || []).map((s: any) => (
                            <tr key={s.symbol} className="hover:bg-slate-700/20 transition-colors">
                              <td className="px-4 py-2.5 font-semibold text-white">{s.symbol}</td>
                              <td className="px-4 py-2.5 text-slate-400 max-w-[100px] truncate">{s.sector || '—'}</td>
                              <td className="px-4 py-2.5 font-bold text-white">{fmt(s.overall_score, 0)}</td>
                              <td className="px-4 py-2.5 text-slate-200">₹{fmt(s.cmp, 2)}</td>
                              <td className="px-4 py-2.5 text-emerald-400">₹{fmt(s.buy_zone_low, 0)} - ₹{fmt(s.buy_zone_high, 0)}</td>
                              <td className="px-4 py-2.5 text-red-400">₹{fmt(s.stop_loss, 0)}</td>
                              <td className="px-4 py-2.5 text-blue-400">₹{fmt(s.target_1y, 0)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {(!port.stocks || port.stocks.length === 0) && (
                      <div className="text-center py-8 text-slate-500 text-xs">No stocks in this portfolio.</div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {/* === AVOID LIST TAB === */}
          {activeTab === 'avoid' && (
            <div className="space-y-3">
              {avoidList.length === 0 ? (
                <div className="text-center py-16 text-slate-500 text-sm">No avoid data.</div>
              ) : (
                avoidList.map((s) => (
                  <div key={s.symbol} className="bg-slate-800/60 border border-red-500/20 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center gap-4">
                    <div className="flex items-center gap-3 min-w-0">
                      <AlertTriangle size={18} className="text-red-400 shrink-0" />
                      <div className="min-w-0">
                        <span className="font-bold text-white text-sm">{s.symbol}</span>
                        <div className="text-[10px] text-slate-500 truncate">{s.sector}</div>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-x-6 gap-y-1 sm:ml-auto text-xs">
                      <div><span className="text-slate-500">Score: </span><span className="font-bold text-red-400">{fmt(s.overall_score, 0)}</span></div>
                      <div><span className="text-slate-500">CMP: </span><span className="text-slate-300">₹{fmt(s.cmp, 2)}</span></div>
                      <div><span className="text-slate-500">D/E: </span><span className="text-red-400">{fmt(s.debt_to_equity, 2)}</span></div>
                      <div><span className="text-slate-500">Tech: </span><span className="text-slate-400">{fmt(s.technical_score, 0)}</span></div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </>
      )}

      {/* === STOCK DETAIL MODAL === */}
      {selectedStock && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={() => setSelectedStock(null)}>
          <div className="bg-slate-900 border border-slate-700/50 rounded-2xl max-w-lg w-full max-h-[85vh] overflow-y-auto shadow-2xl" onClick={e => e.stopPropagation()}>
            {/* Header */}
            <div className="sticky top-0 bg-slate-900 border-b border-slate-700/50 px-5 py-4 flex items-center justify-between z-10">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold ${
                  convictionColor(selectedStock.conviction_level).bg
                } ${convictionColor(selectedStock.conviction_level).text}`}>
                  #{selectedStock.rank || '—'}
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">{selectedStock.symbol}</h2>
                  <p className="text-xs text-slate-500">{selectedStock.sector || selectedStock.company_name}</p>
                </div>
              </div>
              <button onClick={() => setSelectedStock(null)} className="p-1.5 rounded-lg hover:bg-slate-800 transition-colors">
                <X size={18} className="text-slate-400" />
              </button>
            </div>

            <div className="p-5 space-y-5">
              {/* Score + Conviction */}
              <div className="flex items-center gap-4">
                <div className="text-center">
                  <div className="text-3xl font-black text-white">{fmt(selectedStock.overall_score, 0)}</div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider">Overall Score</div>
                </div>
                <div className={`px-3 py-1.5 rounded-lg text-sm font-bold ${convictionColor(selectedStock.conviction_level).bg} ${convictionColor(selectedStock.conviction_level).text}`}>
                  {selectedStock.conviction_level?.replace('_', ' ')}
                </div>
                <div className="ml-auto text-right">
                  <div className="text-xl font-bold text-white">₹{fmt(selectedStock.cmp, 2)}</div>
                  <div className="text-[10px] text-slate-500">{fmtCr(selectedStock.market_cap_cr)}</div>
                </div>
              </div>

              {/* Dimension Scores */}
              <div className="space-y-2 bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Scoring Dimensions</h3>
                <ScoreBar score={selectedStock.promoter_score} label="Promoter" />
                <ScoreBar score={selectedStock.institutional_score} label="Institut." />
                <ScoreBar score={selectedStock.earnings_score} label="Earnings" />
                <ScoreBar score={selectedStock.debt_score} label="Debt" />
                <ScoreBar score={selectedStock.order_book_score} label="Pipeline" />
                <ScoreBar score={selectedStock.sector_score} label="Sector" />
                <ScoreBar score={selectedStock.technical_score} label="Technical" />
                <ScoreBar score={selectedStock.market_score} label="Market" />
              </div>

              {/* Key Metrics */}
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'Promoter', value: `${fmt(selectedStock.promoter_holding)}%`, icon: <Users size={12} /> },
                  { label: 'FII Hold', value: `${fmt(selectedStock.fii_holding)}%`, icon: <Globe size={12} /> },
                  { label: 'DII Hold', value: `${fmt(selectedStock.dii_holding)}%`, icon: <Building2 size={12} /> },
                  { label: 'ROE', value: selectedStock.roe_latest != null || selectedStock.roe != null ? `${(((selectedStock.roe_latest ?? selectedStock.roe ?? 0) as number) * 100).toFixed(0)}%` : '—', icon: <TrendingUp size={12} /> },
                  { label: 'D/E', value: fmt(selectedStock.debt_to_equity, 2), icon: <Activity size={12} /> },
                  { label: '52W High%', value: fmtPct(selectedStock.pct_from_52w_high), icon: <Target size={12} /> },
                  { label: 'Rev Growth', value: fmtPct(selectedStock.revenue_growth ?? selectedStock.sales_growth), icon: <ArrowUpRight size={12} /> },
                  { label: 'Rel. Str.', value: fmtPct(selectedStock.relative_strength), icon: <BarChart3 size={12} /> },
                ].map(m => (
                  <div key={m.label} className="bg-slate-800/50 rounded-lg px-3 py-2.5 border border-slate-700/30 flex items-center gap-2">
                    <span className="text-slate-500">{m.icon}</span>
                    <div>
                      <div className="text-[10px] text-slate-500">{m.label}</div>
                      <div className="text-xs font-semibold text-white">{m.value}</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Trade Params */}
              {(selectedStock.buy_zone_low || selectedStock.target_1y) && (
                <div className="bg-indigo-600/5 border border-indigo-500/20 rounded-xl p-4 space-y-2">
                  <h3 className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Trade Parameters</h3>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div><span className="text-slate-500">Buy Zone: </span><span className="text-emerald-400 font-medium">₹{fmt(selectedStock.buy_zone_low, 0)} - ₹{fmt(selectedStock.buy_zone_high, 0)}</span></div>
                    <div><span className="text-slate-500">Stop Loss: </span><span className="text-red-400 font-medium">₹{fmt(selectedStock.stop_loss, 0)}</span></div>
                    <div><span className="text-slate-500">Target 1Y: </span><span className="text-blue-400 font-medium">₹{fmt(selectedStock.target_1y, 0)}</span></div>
                    <div><span className="text-slate-500">Target 3Y: </span><span className="text-purple-400 font-medium">₹{fmt(selectedStock.target_3y, 0)}</span></div>
                  </div>
                </div>
              )}

              {/* Why Buy / Risk */}
              {selectedStock.why_buy && (
                <div className="space-y-2">
                  <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-3">
                    <div className="text-[10px] text-emerald-400 font-semibold uppercase mb-1">Why Buy</div>
                    <p className="text-xs text-slate-300 leading-relaxed">{selectedStock.why_buy}</p>
                  </div>
                  {selectedStock.risk_factors && (
                    <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-3">
                      <div className="text-[10px] text-amber-400 font-semibold uppercase mb-1">Risk Factors</div>
                      <p className="text-xs text-slate-300 leading-relaxed">{selectedStock.risk_factors}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TradeScreener;
