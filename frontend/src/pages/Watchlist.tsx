import React, { useState, useEffect } from 'react';
import { 
  Eye, 
  Plus, 
  Trash2, 
  TrendingUp, 
  TrendingDown, 
  RefreshCw, 
  DollarSign, 
  TrendingUp as GainersIcon, 
  Loader2, 
  AlertCircle,
  HelpCircle,
  Search
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  AreaChart, 
  Area, 
  PieChart, 
  Pie, 
  Cell, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid 
} from 'recharts';
import { apiGet, apiPost, apiRequest, API_URL, getAuthHeaders } from '../services/api';
import { Page } from '../types';
import {
  useWatchlistQuery,
  useWatchlistPerformanceQuery,
  useWatchlistAnalyticsQuery,
  useAddWatchlistItemMutation,
  useRemoveWatchlistItemMutation
} from '../hooks/useApi';

interface WatchlistItem {
  id: number;
  symbol: string;
  company_name: string;
  exchange: string;
  added_at: string;
  watchlist_price: number;
  current_price: number;
  change_percent: number;
  change_amount: number;
  days_tracked: number;
  status: string;
}

interface PerformanceData {
  total_value: number;
  total_pnl: number;
  pnl_percent: number;
  total_invested: number;
  accuracy_percent: number;
}

interface AnalyticsData {
  best_pick: { symbol: string; company_name: string; change_percent: number } | null;
  worst_pick: { symbol: string; company_name: string; change_percent: number } | null;
  fastest_gainer: { symbol: string; company_name: string; change_percent: number; days_tracked: number } | null;
  accuracy_percent: number;
  winners_losers_chart: { name: string; value: number; color: string }[];
  top_performers_chart: { symbol: string; change_percent: number }[];
  roi_over_time_chart: { date: string; roi_percent: number; portfolio_value: number }[];
}

interface SearchResult {
  symbol: string;
  company_name: string;
  exchange: string;
  sector: string;
}

interface WatchlistProps {
  onNavigate?: (page: Page) => void;
}

const Watchlist: React.FC<WatchlistProps> = ({ onNavigate }) => {
  // Config & State
  const [virtualInvestment, setVirtualInvestment] = useState<number>(10000);

  // React Query Hooks
  const {
    data: watchlistItems = [],
    isLoading: watchlistLoading,
    isFetching: watchlistFetching,
    error: watchlistError,
    refetch: refetchWatchlist
  } = useWatchlistQuery();

  const {
    data: performance,
    isLoading: perfLoading,
    isFetching: perfFetching,
    error: perfError,
    refetch: refetchPerf
  } = useWatchlistPerformanceQuery(virtualInvestment);

  const {
    data: analytics,
    isLoading: analyticsLoading,
    isFetching: analyticsFetching,
    error: analyticsError,
    refetch: refetchAnalytics
  } = useWatchlistAnalyticsQuery(virtualInvestment);

  const addMutation = useAddWatchlistItemMutation();
  const removeMutation = useRemoveWatchlistItemMutation();

  const loading = watchlistLoading || perfLoading || analyticsLoading;
  const refreshing = watchlistFetching || perfFetching || analyticsFetching;
  const error = (watchlistError || perfError || analyticsError)
    ? ((watchlistError?.message || perfError?.message || analyticsError?.message || 'Sync Error') as string)
    : null;

  // Add Item Form State
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState<boolean>(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');
  const [customPrice, setCustomPrice] = useState<string>('');
  const [formError, setFormError] = useState<string | null>(null);

  const adding = addMutation.isPending;

  // Fetch all Watchlist data (manual trigger alias)
  const fetchData = async (isSilent: boolean = false) => {
    await Promise.all([
      refetchWatchlist(),
      refetchPerf(),
      refetchAnalytics()
    ]);
  };

  // Handle Search input change
  useEffect(() => {
    const delayDebounce = setTimeout(async () => {
      if (searchQuery.trim().length >= 1) {
        setSearching(true);
        try {
          const res = await apiGet<{ results: SearchResult[] }>(`/api/search/stocks?q=${searchQuery.trim()}`);
          if (res.success) {
            setSearchResults(res.data.results || []);
          }
        } catch (e) {
          console.error('Search error:', e);
        } finally {
          setSearching(false);
        }
      } else {
        setSearchResults([]);
      }
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [searchQuery]);

  // Add Item to Watchlist
  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSymbol) return;
    
    setFormError(null);

    try {
      const payload: any = { symbol: selectedSymbol };
      if (customPrice && parseFloat(customPrice) > 0) {
        payload.watchlist_price = parseFloat(customPrice);
      }

      await addMutation.mutateAsync(payload);
      
      // Reset form
      setSearchQuery('');
      setSelectedSymbol('');
      setCustomPrice('');
      setSearchResults([]);
    } catch (err: any) {
      setFormError(err.message || 'Error adding symbol to watchlist.');
    }
  };

  // Remove Item from Watchlist
  const handleRemoveItem = async (symbol: string) => {
    if (!window.confirm(`Are you sure you want to remove ${symbol} from your watchlist?`)) return;

    try {
      await removeMutation.mutateAsync(symbol);
    } catch (e: any) {
      alert(e.message || 'Error occurred while deleting.');
    }
  };

  // Render Status Badge
  const renderStatusBadge = (status: string) => {
    let classes = 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
    if (status === 'Strong Winner') classes = 'bg-green-500/10 text-green-500 border border-green-500/20';
    else if (status === 'Winner') classes = 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/10';
    else if (status === 'Loser') classes = 'bg-rose-500/10 text-rose-500 border border-rose-500/10';
    else if (status === 'Strong Loser') classes = 'bg-red-500/10 text-red-500 border border-red-500/20';
    else if (status === 'Neutral') classes = 'bg-amber-500/10 text-amber-500 border border-amber-500/10';

    return (
      <span className={`px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-wide ${classes}`}>
        {status}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 size={40} className="text-brand-500 animate-spin mb-4" />
        <p className="text-slate-400 font-medium text-sm">Compiling Virtual Portfolio metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16 max-w-md mx-auto">
        <AlertCircle size={48} className="text-rose-500 mx-auto mb-4" />
        <h2 className="text-lg font-bold mb-2">Watchlist Sync Error</h2>
        <p className="text-slate-400 text-sm mb-6">{error}</p>
        <button 
          onClick={() => fetchData()} 
          className="px-5 py-2.5 bg-brand-500 hover:bg-brand-600 text-white rounded-xl text-xs font-bold uppercase tracking-wider shadow-lg shadow-brand-500/20 transition-all"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white font-display flex items-center gap-2">
            <Eye className="text-brand-500" size={28} /> Watchlist Portfolio Tracker
          </h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Track "What If I Invested" virtual portfolio performance, baseline returns, and ROI analytics.
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Investment Configurator */}
          <div className="flex items-center gap-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-3 py-1.5 rounded-xl shadow-sm">
            <span className="text-[10px] font-black text-slate-400 uppercase tracking-wide">Investment/Stock:</span>
            <div className="flex items-center gap-1">
              <span className="text-xs font-bold text-slate-500">₹</span>
              <input
                type="number"
                value={virtualInvestment}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  if (val > 0) setVirtualInvestment(val);
                }}
                className="w-20 bg-transparent text-slate-800 dark:text-white font-mono text-xs font-bold focus:outline-none border-b border-slate-200 dark:border-slate-700 focus:border-brand-500 text-right"
              />
            </div>
          </div>

          <button
            onClick={() => fetchData(true)}
            disabled={refreshing}
            className="flex items-center justify-center w-10 h-10 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 rounded-xl transition-all shadow-sm shrink-0"
            title="Refresh Quotes"
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Stats Cards Grid */}
      {performance && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm flex items-center justify-between">
            <div>
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Virtual Portfolio Value</span>
              <span className="text-xl font-bold text-slate-900 dark:text-white block mt-2 font-mono">
                ₹{performance.total_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </span>
              <span className="text-[10px] text-slate-400 mt-1 block">
                Capital Deployed: ₹{performance.total_invested.toLocaleString()}
              </span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-brand-500/10 flex items-center justify-center text-brand-500">
              <DollarSign size={20} />
            </div>
          </div>

          <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm flex items-center justify-between">
            <div>
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Virtual ROI %</span>
              <span className={`text-xl font-bold block mt-2 font-mono flex items-center gap-1 ${
                performance.total_pnl >= 0 ? 'text-green-500' : 'text-rose-500'
              }`}>
                {performance.total_pnl >= 0 ? '+' : ''}
                {performance.pnl_percent.toFixed(2)}%
              </span>
              <span className="text-[10px] text-slate-400 mt-1 block">
                Total ROI on Deployed Cash
              </span>
            </div>
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              performance.total_pnl >= 0 ? 'bg-green-500/10 text-green-500' : 'bg-rose-500/10 text-rose-500'
            }`}>
              {performance.total_pnl >= 0 ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
            </div>
          </div>

          <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm flex items-center justify-between">
            <div>
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Virtual Profit/Loss</span>
              <span className={`text-xl font-bold block mt-2 font-mono ${
                performance.total_pnl >= 0 ? 'text-green-500' : 'text-rose-500'
              }`}>
                {performance.total_pnl >= 0 ? '₹+' : '₹'}
                {performance.total_pnl.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </span>
              <span className="text-[10px] text-slate-400 mt-1 block flex items-center gap-1">
                Net gain from watch list
              </span>
            </div>
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              performance.total_pnl >= 0 ? 'bg-green-500/10 text-green-500' : 'bg-rose-500/10 text-rose-500'
            }`}>
              <DollarSign size={20} />
            </div>
          </div>

          <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm flex items-center justify-between">
            <div>
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Watchlist Accuracy</span>
              <span className="text-xl font-bold text-slate-900 dark:text-white block mt-2 font-mono">
                {performance.accuracy_percent.toFixed(1)}%
              </span>
              <span className="text-[10px] text-slate-400 mt-1 block">
                % of Stocks with Positive P&L
              </span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center text-purple-500">
              <GainersIcon size={20} />
            </div>
          </div>
        </div>
      )}

      {/* Main Layout Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Watchlist Add & Table */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Add Stock Form */}
          <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm">
            <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-3">Add Stock to Watchlist</h3>
            
            <form onSubmit={handleAddItem} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                
                {/* Search Box */}
                <div className="relative md:col-span-2">
                  <div className="flex items-center bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2">
                    <Search className="text-slate-400 shrink-0 mr-2" size={16} />
                    <input
                      type="text"
                      placeholder="Search stock symbol or company name (e.g., RELIANCE)..."
                      value={searchQuery}
                      onChange={(e) => {
                        setSearchQuery(e.target.value);
                        setSelectedSymbol('');
                      }}
                      className="w-full bg-transparent text-slate-800 dark:text-white text-xs font-medium focus:outline-none"
                    />
                    {searching && <Loader2 size={14} className="text-slate-400 animate-spin" />}
                  </div>

                  {/* Dropdown Results */}
                  {searchResults.length > 0 && (
                    <div className="absolute top-full left-0 right-0 z-50 mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg max-h-60 overflow-y-auto">
                      {searchResults.map((res) => (
                        <div
                          key={res.symbol}
                          onClick={() => {
                            setSelectedSymbol(res.symbol);
                            setSearchQuery(`${res.symbol} - ${res.company_name}`);
                            setSearchResults([]);
                          }}
                          className="px-4 py-2.5 hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer flex justify-between items-center text-xs"
                        >
                          <div>
                            <strong className="text-slate-800 dark:text-white">{res.symbol}</strong>
                            <span className="text-[10px] text-slate-400 ml-2 font-medium">{res.company_name}</span>
                          </div>
                          <span className="text-[9px] font-black uppercase bg-slate-100 dark:bg-slate-900 text-slate-500 px-1.5 py-0.5 rounded">
                            {res.exchange}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Custom Entry Price */}
                <div className="flex items-center bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2">
                  <span className="text-slate-400 text-xs mr-2 font-semibold">₹</span>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Entry Price (optional)"
                    value={customPrice}
                    onChange={(e) => setCustomPrice(e.target.value)}
                    className="w-full bg-transparent text-slate-800 dark:text-white text-xs font-mono focus:outline-none"
                  />
                </div>
              </div>

              {formError && (
                <p className="text-rose-500 text-[10px] font-bold flex items-center gap-1">
                  <AlertCircle size={12} /> {formError}
                </p>
              )}

              <div className="flex items-center justify-between">
                <p className="text-[10px] text-slate-400 font-medium">
                  If entry price is omitted, it will resolve via LTP or fallback EOD close.
                </p>
                <button
                  type="submit"
                  disabled={!selectedSymbol || adding}
                  className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider flex items-center gap-1.5 transition-all ${
                    selectedSymbol && !adding
                      ? 'bg-brand-500 hover:bg-brand-600 text-white shadow-lg shadow-brand-500/15'
                      : 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-600 cursor-not-allowed'
                  }`}
                >
                  {adding ? <Loader2 size={12} className="animate-spin" /> : <Plus size={14} />} Add Symbol
                </button>
              </div>
            </form>
          </div>

          {/* Watchlist Table */}
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700/50 flex justify-between items-center">
              <h3 className="font-bold text-sm text-slate-800 dark:text-white">Tracked Watchlist Stock Indexes</h3>
              <span className="text-[10px] font-bold bg-slate-100 dark:bg-slate-900 text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded-full">
                {watchlistItems.length} Stocks
              </span>
            </div>

            {watchlistItems.length === 0 ? (
              <div className="py-16 text-center">
                <Eye className="text-slate-300 dark:text-slate-600 mx-auto mb-3" size={32} />
                <p className="text-slate-400 text-sm font-medium">Your watchlist is currently empty.</p>
                <p className="text-slate-500 text-[10px] mt-1 max-w-xs mx-auto">
                  Add stock symbols above or from SMC Analysis / Pattern Lab headers to start tracking returns.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left">
                  <thead>
                    <tr className="border-b border-slate-100 dark:border-slate-700 text-[10px] font-bold text-slate-400 uppercase tracking-wider bg-slate-50/50 dark:bg-slate-900/30">
                      <th className="px-5 py-3.5">Stock</th>
                      <th className="px-5 py-3.5 text-right">Entry Price</th>
                      <th className="px-5 py-3.5 text-right">Live Price</th>
                      <th className="px-5 py-3.5 text-right">Virtual Returns</th>
                      <th className="px-5 py-3.5 text-center">Days</th>
                      <th className="px-5 py-3.5 text-center">Status</th>
                      <th className="px-5 py-3.5 text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50 text-xs">
                    {watchlistItems.map((item) => {
                      const returnVal = (virtualInvestment / item.watchlist_price) * (item.current_price || item.watchlist_price) - virtualInvestment;
                      
                      return (
                        <tr key={item.id} className="hover:bg-slate-50/30 dark:hover:bg-slate-900/20 transition-colors">
                          <td className="px-5 py-4">
                            <div>
                              <strong className="text-slate-800 dark:text-white block font-display">{item.symbol}</strong>
                              <span className="text-[10px] text-slate-400 block truncate max-w-[150px]" title={item.company_name}>
                                {item.company_name}
                              </span>
                            </div>
                          </td>
                          <td className="px-5 py-4 text-right font-mono font-medium text-slate-700 dark:text-slate-300">
                            ₹{item.watchlist_price.toFixed(2)}
                          </td>
                          <td className="px-5 py-4 text-right font-mono font-black text-slate-800 dark:text-white">
                            ₹{item.current_price ? item.current_price.toFixed(2) : '-'}
                          </td>
                          <td className={`px-5 py-4 text-right font-mono font-bold ${
                            item.change_percent >= 0 ? 'text-green-500' : 'text-rose-500'
                          }`}>
                            <div>
                              <span className="block">
                                {item.change_percent >= 0 ? '+' : ''}
                                {item.change_percent ? item.change_percent.toFixed(2) : '0.00'}%
                              </span>
                              <span className="text-[9px] text-slate-400 block mt-0.5 font-medium">
                                {returnVal >= 0 ? '₹+' : '₹'}
                                {returnVal.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                              </span>
                            </div>
                          </td>
                          <td className="px-5 py-4 text-center font-mono font-medium text-slate-500">
                            {item.days_tracked}
                          </td>
                          <td className="px-5 py-4 text-center">
                            {renderStatusBadge(item.status)}
                          </td>
                          <td className="px-5 py-4 text-center">
                            <button
                              onClick={() => handleRemoveItem(item.symbol)}
                              className="p-1.5 text-slate-400 hover:text-rose-500 hover:bg-rose-500/5 rounded-lg transition-colors"
                              title="Delete Item"
                            >
                              <Trash2 size={13} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Analytics Cards & Performance Charts */}
        <div className="space-y-6">
          
          {/* Pick Analytics Cards */}
          {analytics && (
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm space-y-4">
              <h3 className="font-bold text-sm text-slate-800 dark:text-white border-b border-slate-100 dark:border-slate-700/50 pb-2">
                Watchlist Pick Insights
              </h3>

              {/* Best Pick Card */}
              {analytics.best_pick ? (
                <div className="p-3 bg-green-500/5 border border-green-500/10 rounded-xl flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="text-[9px] font-black text-green-500 uppercase tracking-widest block">Top Performer</span>
                    <strong className="text-xs text-slate-800 dark:text-white font-display block">
                      {analytics.best_pick.symbol}
                    </strong>
                    <span className="text-[9px] text-slate-400 block truncate max-w-[150px]">
                      {analytics.best_pick.company_name}
                    </span>
                  </div>
                  <span className="text-sm font-black text-green-500 font-mono">
                    +{analytics.best_pick.change_percent.toFixed(1)}%
                  </span>
                </div>
              ) : (
                <div className="text-center py-2 text-[10px] text-slate-400">No winner insight yet</div>
              )}

              {/* Fastest Gainer Card */}
              {analytics.fastest_gainer ? (
                <div className="p-3 bg-purple-500/5 border border-purple-500/10 rounded-xl flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="text-[9px] font-black text-purple-500 uppercase tracking-widest block">Fastest Gainer</span>
                    <strong className="text-xs text-slate-800 dark:text-white font-display block">
                      {analytics.fastest_gainer.symbol}
                    </strong>
                    <span className="text-[9px] text-slate-400 block truncate max-w-[150px]">
                      {analytics.fastest_gainer.company_name}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-black text-purple-500 font-mono block">
                      +{analytics.fastest_gainer.change_percent.toFixed(1)}%
                    </span>
                    <span className="text-[9px] text-slate-400 block mt-0.5">
                      in {analytics.fastest_gainer.days_tracked} days
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-center py-2 text-[10px] text-slate-400">No speed insight yet</div>
              )}

              {/* Worst Pick Card */}
              {analytics.worst_pick ? (
                <div className="p-3 bg-rose-500/5 border border-rose-500/10 rounded-xl flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="text-[9px] font-black text-rose-500 uppercase tracking-widest block">Underperformer</span>
                    <strong className="text-xs text-slate-800 dark:text-white font-display block">
                      {analytics.worst_pick.symbol}
                    </strong>
                    <span className="text-[9px] text-slate-400 block truncate max-w-[150px]">
                      {analytics.worst_pick.company_name}
                    </span>
                  </div>
                  <span className="text-sm font-black text-rose-500 font-mono">
                    {analytics.worst_pick.change_percent.toFixed(1)}%
                  </span>
                </div>
              ) : (
                <div className="text-center py-2 text-[10px] text-slate-400">No loser insight yet</div>
              )}
            </div>
          )}

          {/* Recharts Pie Chart: Winner/Loser distribution */}
          {analytics && analytics.winners_losers_chart.length > 0 && (
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm">
              <h3 className="font-bold text-sm text-slate-800 dark:text-white border-b border-slate-100 dark:border-slate-700/50 pb-2 mb-4">
                ROI Distribution
              </h3>
              <div className="h-44 w-full flex items-center justify-center relative">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={analytics.winners_losers_chart.filter(x => x.value > 0)}
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={65}
                      paddingAngle={4}
                      dataKey="value"
                    >
                      {analytics.winners_losers_chart.map((entry, idx) => (
                        <Cell key={`cell-${idx}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ background: '#1E293B', border: 'none', borderRadius: '8px' }} 
                      itemStyle={{ color: '#F8FAFC', fontSize: '10px' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                {/* Accuracy Overlay */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">Win Rate</span>
                  <span className="text-lg font-black text-slate-800 dark:text-white font-mono mt-0.5">
                    {analytics.accuracy_percent.toFixed(0)}%
                  </span>
                </div>
              </div>
              
              {/* Legend */}
              <div className="grid grid-cols-3 gap-2 mt-4 text-[10px] font-bold text-center">
                {analytics.winners_losers_chart.map((entry) => (
                  <div key={entry.name} className="p-1.5 rounded-lg border border-slate-100 dark:border-slate-700/50 bg-slate-50/50 dark:bg-slate-900/30">
                    <span className="block text-slate-400 uppercase tracking-wide">{entry.name}</span>
                    <span className="block mt-1 text-xs font-black font-mono" style={{ color: entry.color }}>
                      {entry.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recharts Bar Chart: Top 10 Performers */}
          {analytics && analytics.top_performers_chart.length > 0 && (
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm">
              <h3 className="font-bold text-sm text-slate-800 dark:text-white border-b border-slate-100 dark:border-slate-700/50 pb-2 mb-4">
                Top Performers Return %
              </h3>
              <div className="h-44 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={analytics.top_performers_chart}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#33415510" />
                    <XAxis 
                      dataKey="symbol" 
                      tick={{ fill: '#94A3B8', fontSize: 9, fontWeight: 700 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis 
                      tick={{ fill: '#94A3B8', fontSize: 9, fontWeight: 700 }}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(val) => `${val}%`}
                    />
                    <Tooltip 
                      cursor={{ fill: 'rgba(99, 102, 241, 0.05)' }}
                      contentStyle={{ background: '#1E293B', border: 'none', borderRadius: '8px' }} 
                      itemStyle={{ color: '#F8FAFC', fontSize: '10px' }}
                      labelStyle={{ color: '#94A3B8', fontSize: '9px', fontWeight: 700 }}
                      formatter={(val: number) => [`${val.toFixed(2)}%`, 'Gain']}
                    />
                    <Bar dataKey="change_percent" fill="#10B981" radius={[4, 4, 0, 0]}>
                      {analytics.top_performers_chart.map((entry, idx) => (
                        <Cell 
                          key={`cell-${idx}`} 
                          fill={entry.change_percent >= 0 ? '#10B981' : '#EF4444'} 
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

        </div>
      </div>

      {/* ROI Over Time Line Chart: Full width bottom section */}
      {analytics && analytics.roi_over_time_chart.length > 0 && (
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-6 shadow-sm">
          <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-700/50 pb-3 mb-6">
            <div>
              <h3 className="font-bold text-sm text-slate-800 dark:text-white">Daily Virtual ROI Equity Curve</h3>
              <p className="text-[10px] text-slate-400 font-semibold mt-0.5">
                Compounded portfolio growth over time starting from the oldest watchlist symbol entry date.
              </p>
            </div>
            {analytics.roi_over_time_chart && analytics.roi_over_time_chart.length > 0 && (
              <div className="px-3 py-1 bg-brand-500/10 text-brand-500 text-[10px] font-black uppercase tracking-wider rounded-lg border border-brand-500/20 font-mono">
                Net: {analytics.roi_over_time_chart[analytics.roi_over_time_chart.length - 1].roi_percent >= 0 ? '+' : ''}
                {analytics.roi_over_time_chart[analytics.roi_over_time_chart.length - 1].roi_percent.toFixed(2)}%
              </div>
            )}
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={analytics.roi_over_time_chart}>
                <defs>
                  <linearGradient id="colorRoi" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366F1" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#6366F1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#33415515" />
                <XAxis 
                  dataKey="date" 
                  tick={{ fill: '#94A3B8', fontSize: 10, fontWeight: 700 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis 
                  tick={{ fill: '#94A3B8', fontSize: 10, fontWeight: 700 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(val) => `${val}%`}
                />
                <Tooltip 
                  contentStyle={{ background: '#1E293B', border: 'none', borderRadius: '12px' }} 
                  itemStyle={{ color: '#F8FAFC', fontSize: '11px' }}
                  labelStyle={{ color: '#94A3B8', fontSize: '10px', fontWeight: 700 }}
                  formatter={(val: number, name: string) => {
                    if (name === 'roi_percent') return [`${val.toFixed(2)}%`, 'ROI'];
                    if (name === 'portfolio_value') return [`₹${val.toLocaleString()}`, 'Portfolio Value'];
                    return [val, name];
                  }}
                />
                <Area 
                  type="monotone" 
                  dataKey="roi_percent" 
                  stroke="#6366F1" 
                  strokeWidth={3}
                  fillOpacity={1} 
                  fill="url(#colorRoi)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};

export default Watchlist;
