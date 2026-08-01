import React, { useState, useEffect } from 'react';
import { API_URL, getAuthHeaders } from '../services/api';
import { 
  ArrowLeft, 
  TrendingUp, 
  Activity, 
  CheckCircle, 
  AlertCircle, 
  Newspaper, 
  Users, 
  Percent, 
  DollarSign, 
  Calendar,
  Grid,
  FileText
} from 'lucide-react';

interface DetailProps {
  symbol: string;
  onBack: () => void;
}

interface DetailData {
  symbol: string;
  company_name: string;
  sector: string;
  vcp: {
    vcp_score: number;
    num_contractions: number;
    latest_contraction_pct: number;
    volume_dry_up_pct: number;
    atr_contraction_pct: number;
    breakout_pivot: number;
    breakout_ready: boolean;
    category: string;
    trend_quality: number;
    volatility_compression: number;
  } | null;
  trend_template: {
    score: number;
    sma50: number;
    sma150: number;
    sma200: number;
    distance_to_52w_high: number;
    conditions: {
      price_above_sma50: boolean;
      price_above_sma150: boolean;
      price_above_sma200: boolean;
      sma50_above_sma150: boolean;
      sma150_above_sma200: boolean;
      price_above_52w_low_by_30pct: boolean;
      price_within_25pct_of_52w_high: boolean;
    };
  } | null;
  relative_strength: {
    rs_score: number;
    rank: number;
    sector_rank: number;
    industry_rank: number;
    return_6m: number;
    return_3m: number;
    return_1m: number;
  } | null;
  breakout: {
    is_breakout: boolean;
    breakout_price: number;
    current_price: number;
    breakout_pct: number;
    volume_surge_pct: number;
    confirmation_status: string;
    breakout_type: string;
  };
  darvas: {
    box_top: number;
    box_bottom: number;
    days_inside_box: number;
    breakout_status: string;
  } | null;
  patterns: Array<{
    pattern_type: string;
    confidence_score: number;
    breakout_pivot: number;
    breakout_status: string;
    details: any;
    updated_at: string;
  }>;
  fundamentals: {
    market_cap?: number;
    pe_ratio?: number;
    pb_ratio?: number;
    dividend_yield?: number;
    debt_to_equity?: number;
    roe?: number;
    roce?: number;
    eps?: number;
    sector_pe_benchmark?: number;
    sector_pb_benchmark?: number;
  } | null;
  news: Array<{
    id?: string;
    title: string;
    description?: string;
    source?: string;
    publish_date?: string;
    url?: string;
  }>;
  competitors: Array<{
    symbol: string;
    company_name?: string;
    close_price?: number;
    market_cap?: number;
    pe_ratio?: number;
  }>;
}

const InstitutionalStockDetail: React.FC<DetailProps> = ({ symbol, onBack }) => {
  const [data, setData] = useState<DetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSubTab, setActiveSubTab] = useState<'patterns' | 'indicators' | 'news_competitors'>('patterns');

  useEffect(() => {
    const fetchDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_URL}/api/v1/institutional-scanner/detail/${symbol}`, {
          headers: getAuthHeaders()
        });
        if (!res.ok) {
          throw new Error(`Failed to load stock details (status ${res.status})`);
        }
        const json = await res.json();
        setData(json);
      } catch (err: any) {
        setError(err.message || 'Error occurred while loading data.');
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [symbol]);

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-500 bg-slate-900/20 rounded-2xl border border-slate-800 backdrop-blur">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500 mx-auto mb-4"></div>
        Fetching institutional analysis for {symbol}...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center bg-slate-900/30 rounded-2xl border border-slate-800/50 backdrop-blur text-slate-300">
        <AlertCircle className="mx-auto mb-4 text-red-500" size={32} />
        <h3 className="text-lg font-bold mb-2">Analysis Failed</h3>
        <p className="text-sm text-slate-400 mb-4">{error || 'Data is unavailable'}</p>
        <button onClick={onBack} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-xl text-xs font-bold transition-colors">
          Back to Scanner
        </button>
      </div>
    );
  }

  // Formatting helpers
  const fmtCurrency = (val?: number) => {
    if (val === undefined || val === null) return '—';
    return '₹' + val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const fmtCrore = (val?: number) => {
    if (val === undefined || val === null || val === 0) return '—';
    const crore = val / 10000000.0;
    return `₹${crore.toLocaleString('en-IN', { maximumFractionDigits: 1 })} Cr`;
  };

  return (
    <div className="space-y-6 text-slate-100 pb-12">
      {/* Top Navigation Bar */}
      <div className="flex items-center gap-4 bg-slate-900/50 p-4 rounded-xl border border-slate-800 backdrop-blur">
        <button
          onClick={onBack}
          className="p-2 bg-slate-800 hover:bg-slate-700 rounded-xl text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft size={16} />
        </button>
        <div>
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Institutional Detail</span>
          <div className="flex items-center gap-2 mt-0.5">
            <h1 className="text-xl font-display font-black tracking-tight text-white">{data.symbol}</h1>
            <span className="text-slate-500">·</span>
            <span className="text-sm text-slate-400 font-semibold">{data.company_name}</span>
            <span className="px-2 py-0.5 bg-brand-500/10 text-brand-400 rounded text-[9px] font-bold">Real-time Upstox Data</span>
          </div>
        </div>
      </div>

      {/* Main Layout Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Side: Overview & Fundamentals */}
        <div className="space-y-6">
          
          {/* Overview Card */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 backdrop-blur">
            <h3 className="font-display font-bold text-sm text-slate-300 border-b border-slate-800 pb-3 mb-4 flex items-center gap-2">
              <Grid size={15} className="text-brand-400" /> Key Overview
            </h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-[10px] font-bold text-slate-500 uppercase">Current Close</div>
                <div className="text-xl font-mono font-bold text-white mt-1">₹{data.breakout?.current_price?.toFixed(2) ?? '—'}</div>
              </div>
              <div>
                <div className="text-[10px] font-bold text-slate-500 uppercase">Sector</div>
                <div className="text-sm font-semibold text-slate-300 mt-1.5 truncate">{data.sector}</div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-850 grid grid-cols-2 gap-y-4 gap-x-2 text-xs font-semibold">
              <div>
                <div className="text-slate-500">Market Cap</div>
                <div className="text-slate-200 mt-1">{fmtCrore(data.fundamentals?.market_cap)}</div>
              </div>
              <div>
                <div className="text-slate-500">P/E Ratio</div>
                <div className="text-slate-200 mt-1">
                  {data.fundamentals?.pe_ratio?.toFixed(2) ?? '—'}
                  {data.fundamentals?.sector_pe_benchmark && (
                    <span className="text-[10px] text-slate-500 ml-1">(Sec: {data.fundamentals.sector_pe_benchmark?.toFixed(1) ?? '—'})</span>
                  )}
                </div>
              </div>
              <div>
                <div className="text-slate-500">P/B Ratio</div>
                <div className="text-slate-200 mt-1">
                  {data.fundamentals?.pb_ratio?.toFixed(2) ?? '—'}
                </div>
              </div>
              <div>
                <div className="text-slate-500">Debt to Equity</div>
                <div className="text-slate-200 mt-1">
                  {data.fundamentals?.debt_to_equity !== undefined && data.fundamentals.debt_to_equity !== null ? data.fundamentals.debt_to_equity.toFixed(2) : '—'}
                </div>
              </div>
              <div>
                <div className="text-slate-500">Dividend Yield</div>
                <div className="text-slate-200 mt-1">
                  {data.fundamentals?.dividend_yield !== undefined && data.fundamentals.dividend_yield !== null ? `${data.fundamentals.dividend_yield.toFixed(2)}%` : '—'}
                </div>
              </div>
              <div>
                <div className="text-slate-500">EPS</div>
                <div className="text-slate-200 mt-1">
                  {data.fundamentals?.eps !== undefined && data.fundamentals.eps !== null ? `₹${data.fundamentals.eps.toFixed(2)}` : '—'}
                </div>
              </div>
            </div>
          </div>

          {/* Pattern Summary Card */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 backdrop-blur">
            <h3 className="font-display font-bold text-sm text-slate-300 border-b border-slate-800 pb-3 mb-4 flex items-center gap-2">
              <FileText size={15} className="text-purple-400" /> Active Patterns
            </h3>
            
            {data.patterns.length === 0 ? (
              <div className="text-xs text-slate-500 italic py-2">No active chart pattern detected for this stock.</div>
            ) : (
              <div className="space-y-3">
                {data.patterns.map((p, idx) => (
                  <div key={idx} className="bg-slate-950/40 p-3.5 rounded-xl border border-slate-850/60 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-bold text-slate-200">{p.pattern_type}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">Pivot: ₹{p.breakout_pivot?.toFixed(1) ?? '—'}</div>
                    </div>
                    <div className="text-right">
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                        p.breakout_status === 'Confirmed' ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-400'
                      }`}>
                        {p.breakout_status}
                      </span>
                      <div className="text-[10px] text-brand-400 font-bold mt-1.5">{p.confidence_score?.toFixed(0) ?? '—'}% Conf.</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Detailed analysis tabs */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Sub Navigation */}
          <div className="flex gap-2 border-b border-slate-800 pb-1.5">
            {[
              { id: 'patterns', label: 'Technical Patterns & Geometry' },
              { id: 'indicators', label: 'Technical Indicators & MA' },
              { id: 'news_competitors', label: 'Upstox News & Peer Comparison' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveSubTab(tab.id as any)}
                className={`
                  px-4 py-2 text-xs font-bold rounded-xl transition-all
                  ${activeSubTab === tab.id 
                    ? 'bg-slate-800 text-white border border-slate-700' 
                    : 'text-slate-400 hover:text-slate-200'
                  }
                `}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab 1: Patterns */}
          {activeSubTab === 'patterns' && (
            <div className="space-y-6">
              
              {/* VCP Contraction Detail */}
              <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 backdrop-blur">
                <h3 className="font-display font-bold text-sm text-slate-300 border-b border-slate-800 pb-3 mb-4 flex items-center gap-2">
                  <TrendingUp size={16} className="text-amber-500" /> Volatility Contraction Pattern (VCP) Analysis
                </h3>
                
                {data.vcp ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-semibold">
                      <div className="bg-slate-950/30 p-3 rounded-xl border border-slate-850">
                        <div className="text-slate-500">VCP score</div>
                        <div className="text-lg font-bold text-white mt-1">{data.vcp.vcp_score?.toFixed(1) ?? '0.0'} / 100</div>
                      </div>
                      <div className="bg-slate-950/30 p-3 rounded-xl border border-slate-850">
                        <div className="text-slate-500">Contractions</div>
                        <div className="text-lg font-bold text-amber-400 mt-1">{data.vcp.num_contractions ?? 0}T</div>
                      </div>
                      <div className="bg-slate-950/30 p-3 rounded-xl border border-slate-850">
                        <div className="text-slate-500">Last Contraction</div>
                        <div className="text-lg font-bold text-amber-500 mt-1">{data.vcp.latest_contraction_pct?.toFixed(2) ?? '0.00'}%</div>
                      </div>
                      <div className="bg-slate-950/30 p-3 rounded-xl border border-slate-850">
                        <div className="text-slate-500">Breakout Pivot</div>
                        <div className="text-lg font-bold text-emerald-400 mt-1">₹{data.vcp.breakout_pivot?.toFixed(1) ?? '0.0'}</div>
                      </div>
                    </div>

                    <div className="p-4 bg-slate-950/40 border border-slate-850 rounded-xl space-y-3 text-xs font-semibold">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Volatility Compression Quality</span>
                        <span className="text-slate-200">{data.vcp.volatility_compression?.toFixed(1) ?? '0.0'}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">MA Trend Quality</span>
                        <span className="text-slate-200">{data.vcp.trend_quality?.toFixed(1) ?? '0.0'}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Volume contraction dry-up</span>
                        <span className="text-emerald-400">{data.vcp.volume_dry_up_pct?.toFixed(2) ?? '0.00'}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">ATR Contraction Percentage</span>
                        <span className="text-slate-200">{data.vcp.atr_contraction_pct?.toFixed(2) ?? '0.00'}%</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-slate-500 italic py-4">VCP pattern analysis is not available for this stock.</div>
                )}
              </div>

              {/* Darvas Box Tracker */}
              <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 backdrop-blur">
                <h3 className="font-display font-bold text-sm text-slate-300 border-b border-slate-800 pb-3 mb-4 flex items-center gap-2">
                  <Activity size={16} className="text-brand-400" /> Nicolas Darvas Box Details
                </h3>
                
                {data.darvas ? (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-semibold">
                    <div className="bg-slate-950/30 p-3 rounded-xl border border-slate-850">
                      <div className="text-slate-500">Box Top</div>
                      <div className="text-sm font-mono mt-1">₹{data.darvas.box_top?.toFixed(1) ?? '0.0'}</div>
                    </div>
                    <div className="bg-slate-950/30 p-3 rounded-xl border border-slate-850">
                      <div className="text-slate-500">Box Bottom</div>
                      <div className="text-sm font-mono mt-1">₹{data.darvas.box_bottom?.toFixed(1) ?? '0.0'}</div>
                    </div>
                    <div className="bg-slate-950/30 p-3 rounded-xl border border-slate-850">
                      <div className="text-slate-500">Days Inside Box</div>
                      <div className="text-sm mt-1">{data.darvas.days_inside_box ?? 0} Days</div>
                    </div>
                    <div className="bg-slate-950/30 p-3 rounded-xl border border-slate-850">
                      <div className="text-slate-500">Breakout Status</div>
                      <div className="text-sm mt-1">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          data.darvas.breakout_status?.includes('Breakout') ? 'bg-emerald-950/40 text-emerald-400' : 'bg-slate-800 text-slate-400'
                        }`}>
                          {data.darvas.breakout_status ?? 'Pending'}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-slate-500 italic py-4">Darvas Box tracking is not available.</div>
                )}
              </div>
            </div>
          )}

          {/* Tab 2: Indicators */}
          {activeSubTab === 'indicators' && (
            <div className="space-y-6">
              
              {/* Minervini Trend Template Check */}
              <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 backdrop-blur">
                <h3 className="font-display font-bold text-sm text-slate-300 border-b border-slate-800 pb-3 mb-4">
                  Mark Minervini Trend Template Screening Checklist
                </h3>
                
                {data.trend_template ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-semibold">
                      {[
                        { label: 'Price > SMA50', val: data.trend_template.conditions?.price_above_sma50 },
                        { label: 'Price > SMA150', val: data.trend_template.conditions?.price_above_sma150 },
                        { label: 'Price > SMA200', val: data.trend_template.conditions?.price_above_sma200 },
                        { label: 'SMA50 > SMA150', val: data.trend_template.conditions?.sma50_above_sma150 },
                        { label: 'SMA150 > SMA200', val: data.trend_template.conditions?.sma150_above_sma200 },
                        { label: 'Price > 52W Low by 30%', val: data.trend_template.conditions?.price_above_52w_low_by_30pct },
                        { label: 'Price within 25% of 52W High', val: data.trend_template.conditions?.price_within_25pct_of_52w_high }
                      ].map((item, i) => (
                        <div key={i} className="flex items-center justify-between p-3 bg-slate-950/20 border border-slate-850 rounded-xl">
                          <span className="text-slate-400">{item.label}</span>
                          {item.val ? (
                            <span className="flex items-center gap-1 text-emerald-400 font-bold">
                              <CheckCircle size={13} fill="rgba(16, 185, 129, 0.2)" /> Passed
                            </span>
                          ) : (
                            <span className="text-slate-500 font-bold">Failed</span>
                          )}
                        </div>
                      ))}
                    </div>

                    <div className="p-4 bg-slate-950/40 border border-slate-850 rounded-xl grid grid-cols-3 gap-4 text-center text-xs font-semibold">
                      <div>
                        <div className="text-slate-500">SMA50</div>
                        <div className="text-slate-200 mt-1 font-mono">₹{data.trend_template.sma50?.toFixed(1) ?? '0.0'}</div>
                      </div>
                      <div>
                        <div className="text-slate-500">SMA150</div>
                        <div className="text-slate-200 mt-1 font-mono">₹{data.trend_template.sma150?.toFixed(1) ?? '0.0'}</div>
                      </div>
                      <div>
                        <div className="text-slate-500">SMA200</div>
                        <div className="text-slate-200 mt-1 font-mono">₹{data.trend_template.sma200?.toFixed(1) ?? '0.0'}</div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-slate-500 italic py-4">Trend template metrics are not available.</div>
                )}
              </div>

              {/* Relative Strength Details */}
              <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 backdrop-blur">
                <h3 className="font-display font-bold text-sm text-slate-300 border-b border-slate-800 pb-3 mb-4">
                  Institutional Relative Strength (RS) Rankings
                </h3>
                
                {data.relative_strength ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-3 gap-4 text-center text-xs font-semibold">
                      <div className="bg-slate-950/30 p-3 rounded-xl border border-slate-850">
                        <div className="text-slate-500">Overall RS Rank</div>
                        <div className="text-lg font-bold text-white mt-1">#{data.relative_strength.rank}</div>
                      </div>
                      <div className="bg-slate-950/30 p-3 rounded-xl border border-slate-850">
                        <div className="text-slate-500">Sector Rank</div>
                        <div className="text-lg font-bold text-slate-300 mt-1">#{data.relative_strength.sector_rank}</div>
                      </div>
                      <div className="bg-slate-950/30 p-3 rounded-xl border border-slate-850">
                        <div className="text-slate-500">Industry Rank</div>
                        <div className="text-lg font-bold text-slate-300 mt-1">#{data.relative_strength.industry_rank}</div>
                      </div>
                    </div>

                    <div className="p-4 bg-slate-950/40 border border-slate-850 rounded-xl space-y-3 text-xs font-semibold">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Weighted RS Score</span>
                        <span className="text-slate-200 font-bold">{data.relative_strength.rs_score?.toFixed(1) ?? '0.0'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">6 Month Return</span>
                        <span className={`font-mono ${(data.relative_strength.return_6m ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {data.relative_strength.return_6m?.toFixed(2) ?? '0.00'}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">3 Month Return</span>
                        <span className={`font-mono ${(data.relative_strength.return_3m ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {data.relative_strength.return_3m?.toFixed(2) ?? '0.00'}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">1 Month Return</span>
                        <span className={`font-mono ${(data.relative_strength.return_1m ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {data.relative_strength.return_1m?.toFixed(2) ?? '0.00'}%
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-slate-500 italic py-4">RS Rank data is not available.</div>
                )}
              </div>
            </div>
          )}

          {/* Tab 3: News & Peer Comparison */}
          {activeSubTab === 'news_competitors' && (
            <div className="space-y-6">
              
              {/* Upstox Competitor Comparison */}
              <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 backdrop-blur">
                <h3 className="font-display font-bold text-sm text-slate-300 border-b border-slate-800 pb-3 mb-4 flex items-center gap-2">
                  <Users size={16} className="text-brand-400" /> Peer Competitor Comparison
                </h3>
                
                {data.competitors.length === 0 ? (
                  <div className="text-xs text-slate-500 italic py-4">No competitors fetched from Upstox API.</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs font-semibold">
                      <thead>
                        <tr className="border-b border-slate-800 text-[10px] text-slate-500 uppercase tracking-wider">
                          <th className="pb-2">Symbol</th>
                          <th className="pb-2">Company</th>
                          <th className="pb-2">Market Cap</th>
                          <th className="pb-2">P/E Ratio</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-850/50">
                        {data.competitors.map((peer, idx) => (
                          <tr key={idx} className="hover:bg-slate-800/10">
                            <td className="py-2.5 font-bold text-brand-400">{peer.symbol}</td>
                            <td className="py-2.5 text-slate-300 truncate max-w-[150px]">{peer.company_name || '—'}</td>
                            <td className="py-2.5 font-mono text-slate-300">{fmtCrore(peer.market_cap)}</td>
                            <td className="py-2.5 font-mono text-slate-300">{peer.pe_ratio ? peer.pe_ratio.toFixed(1) : '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Upstox News Feed */}
              <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 backdrop-blur">
                <h3 className="font-display font-bold text-sm text-slate-300 border-b border-slate-800 pb-3 mb-4 flex items-center gap-2">
                  <Newspaper size={16} className="text-purple-400" /> Recent Institutional News
                </h3>
                
                {data.news.length === 0 ? (
                  <div className="text-xs text-slate-500 italic py-4">No recent news fetched from Upstox APIs.</div>
                ) : (
                  <div className="space-y-4">
                    {data.news.map((item, idx) => (
                      <div key={idx} className="bg-slate-950/20 p-4 border border-slate-850 rounded-xl space-y-1">
                        <div className="text-xs font-bold text-slate-200">{item.title}</div>
                        {item.description && (
                          <p className="text-[11px] text-slate-400 leading-relaxed truncate">{item.description}</p>
                        )}
                        <div className="flex justify-between items-center text-[9px] text-slate-500 pt-2 font-bold uppercase">
                          <span>{item.source || 'Upstox Intelligence'}</span>
                          <span>{item.publish_date || 'Today'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default InstitutionalStockDetail;
