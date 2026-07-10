import React, { useState, useEffect, useCallback } from 'react';
import {
  RefreshCw, Database, CheckCircle, AlertTriangle, XCircle,
  BarChart3, Clock, Globe, Download, Shield, TrendingUp, ChevronDown, ChevronUp
} from 'lucide-react';
import { API_URL, getAuthHeaders } from '../services/api';
import { IndexInfo, IndexStats, IndexRefreshLog, ValidationReport } from '../types/indices';

// ─── Helpers ────────────────────────────────────────────────────────────────

const safeFixed = (v: any, d = 1) =>
  v === null || v === undefined || isNaN(Number(v)) ? '—' : Number(v).toFixed(d);

const statusColor = (pct: number) => {
  if (pct >= 95) return 'text-emerald-400';
  if (pct >= 70) return 'text-amber-400';
  return 'text-red-400';
};

const statusBg = (status: string) => {
  if (status === 'success') return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
  if (status === 'partial') return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
  if (status === 'failed' || status === 'never_run') return 'bg-red-500/10 text-red-400 border-red-500/20';
  return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
};

// ─── Component ───────────────────────────────────────────────────────────────

const IndexManagement: React.FC = () => {
  const [indices, setIndices] = useState<IndexInfo[]>([]);
  const [refreshLog, setRefreshLog] = useState<IndexRefreshLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState<string | null>(null);
  const [validating, setValidating] = useState<string | null>(null);
  const [validationResult, setValidationResult] = useState<ValidationReport | null>(null);
  const [expandedIndex, setExpandedIndex] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'indices' | 'log'>('indices');

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [indRes, logRes] = await Promise.all([
        fetch(`${API_URL}/api/indices`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/indices/refresh/log?limit=20`, { headers: getAuthHeaders() }),
      ]);
      if (indRes.ok) setIndices((await indRes.json()).indices || []);
      if (logRes.ok) setRefreshLog((await logRes.json()).log || []);
    } catch (e) {
      console.error('Failed to load index management data', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleRefresh = async (indexName?: string) => {
    const key = indexName || '__ALL__';
    setRefreshing(key);
    try {
      await fetch(`${API_URL}/api/indices/refresh`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ index_name: indexName || null }),
      });
      // Wait a moment then reload
      setTimeout(() => { fetchAll(); setRefreshing(null); }, 4000);
    } catch (e) {
      setRefreshing(null);
    }
  };

  const handleValidate = async (indexName: string) => {
    setValidating(indexName);
    setValidationResult(null);
    try {
      const res = await fetch(`${API_URL}/api/indices/validate`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ index_name: indexName }),
      });
      if (res.ok) setValidationResult(await res.json());
    } catch (e) {
      console.error('Validation failed', e);
    } finally {
      setValidating(null);
    }
  };

  // ── Overview stats
  const totalIndices = indices.length;
  const seededIndices = indices.filter(i => i.constituent_count > 0).length;
  const totalConstituents = indices.reduce((s, i) => s + i.constituent_count, 0);
  const avgCoverage = indices.length
    ? Math.round(indices.reduce((s, i) => s + i.coverage_pct, 0) / indices.length)
    : 0;

  // ── Group by category
  const grouped: Record<string, IndexInfo[]> = {};
  indices.forEach(idx => {
    const cat = idx.category || 'Other';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(idx);
  });
  const categoryOrder = ['Broad Market', 'Sector', 'Midcap', 'Smallcap'];

  return (
    <div className="min-h-screen bg-[#0a0b0f] text-slate-100 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Globe size={22} className="text-violet-400" />
            <h1 className="text-2xl font-bold text-white">Index Management</h1>
          </div>
          <p className="text-slate-400 text-sm">
            NSE index constituents · Database coverage · Auto-refresh status
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => handleRefresh()}
            disabled={refreshing === '__ALL__'}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={refreshing === '__ALL__' ? 'animate-spin' : ''} />
            {refreshing === '__ALL__' ? 'Refreshing All…' : 'Refresh All Indices'}
          </button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Total Indices', value: totalIndices, icon: <Globe size={16} />, color: 'violet' },
          { label: 'Seeded Indices', value: seededIndices, icon: <Database size={16} />, color: 'emerald' },
          { label: 'Total Constituents', value: totalConstituents.toLocaleString(), icon: <BarChart3 size={16} />, color: 'blue' },
          { label: 'Avg Coverage', value: `${avgCoverage}%`, icon: <Shield size={16} />, color: avgCoverage >= 90 ? 'emerald' : 'amber' },
        ].map(c => (
          <div key={c.label} className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
            <div className={`flex items-center gap-2 text-${c.color}-400 text-xs mb-2`}>
              {c.icon}
              <span>{c.label}</span>
            </div>
            <div className="text-2xl font-bold text-white">{c.value}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-800/40 rounded-lg p-1 w-fit">
        {(['indices', 'log'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors capitalize ${
              activeTab === tab
                ? 'bg-violet-600 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            {tab === 'indices' ? '📋 Indices' : '📜 Refresh Log'}
          </button>
        ))}
      </div>

      {/* Indices Tab */}
      {activeTab === 'indices' && (
        <div className="space-y-6">
          {loading ? (
            <div className="flex items-center justify-center py-20 text-slate-500">
              <RefreshCw size={20} className="animate-spin mr-3" /> Loading index data…
            </div>
          ) : (
            categoryOrder.filter(cat => grouped[cat]).map(cat => (
              <div key={cat}>
                <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <span>{cat === 'Broad Market' ? '📈' : cat === 'Sector' ? '🏭' : '📊'}</span>
                  {cat}
                  <span className="bg-slate-700 px-1.5 py-0.5 rounded text-slate-400">
                    {grouped[cat].length}
                  </span>
                </h2>
                <div className="space-y-2">
                  {grouped[cat].map(idx => {
                    const isExpanded = expandedIndex === idx.index_name;
                    const coverage = idx.coverage_pct ?? 0;
                    const seeded = idx.constituent_count > 0;
                    return (
                      <div
                        key={idx.index_name}
                        className="bg-slate-800/40 border border-slate-700/40 rounded-xl overflow-hidden"
                      >
                        {/* Row */}
                        <div className="flex items-center gap-4 px-4 py-3">
                          {/* Status icon */}
                          <div className="flex-shrink-0">
                            {!seeded ? (
                              <XCircle size={16} className="text-red-400" />
                            ) : coverage >= 95 ? (
                              <CheckCircle size={16} className="text-emerald-400" />
                            ) : (
                              <AlertTriangle size={16} className="text-amber-400" />
                            )}
                          </div>

                          {/* Name */}
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-sm text-white truncate">
                              {idx.display_name}
                            </div>
                            <div className="text-[10px] text-slate-500">
                              {idx.nse_index_code} · {idx.constituent_count} stocks
                            </div>
                          </div>

                          {/* Coverage bar */}
                          <div className="w-28 hidden sm:block">
                            <div className="flex items-center justify-between text-[10px] mb-0.5">
                              <span className={statusColor(coverage)}>{safeFixed(coverage)}%</span>
                              <span className="text-slate-600">coverage</span>
                            </div>
                            <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${coverage >= 95 ? 'bg-emerald-500' : coverage >= 70 ? 'bg-amber-500' : 'bg-red-500'}`}
                                style={{ width: `${Math.min(coverage, 100)}%` }}
                              />
                            </div>
                          </div>

                          {/* Last refreshed */}
                          <div className="text-[10px] text-slate-500 w-24 text-right hidden md:block">
                            {idx.last_refreshed
                              ? new Date(idx.last_refreshed).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
                              : 'Never'}
                          </div>

                          {/* Actions */}
                          <div className="flex gap-1.5">
                            <button
                              onClick={() => handleRefresh(idx.index_name)}
                              disabled={refreshing === idx.index_name}
                              title="Refresh from NSE"
                              className="p-1.5 rounded-lg bg-slate-700/60 hover:bg-violet-600/40 text-slate-400 hover:text-violet-300 transition-colors disabled:opacity-40"
                            >
                              <RefreshCw size={12} className={refreshing === idx.index_name ? 'animate-spin' : ''} />
                            </button>
                            <button
                              onClick={() => handleValidate(idx.index_name)}
                              disabled={validating === idx.index_name}
                              title="Validate constituents"
                              className="p-1.5 rounded-lg bg-slate-700/60 hover:bg-blue-600/40 text-slate-400 hover:text-blue-300 transition-colors disabled:opacity-40"
                            >
                              <Shield size={12} className={validating === idx.index_name ? 'animate-pulse' : ''} />
                            </button>
                            <button
                              onClick={() => setExpandedIndex(isExpanded ? null : idx.index_name)}
                              className="p-1.5 rounded-lg bg-slate-700/60 hover:bg-slate-600 text-slate-400 hover:text-white transition-colors"
                            >
                              {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                            </button>
                          </div>
                        </div>

                        {/* Expanded detail / validation result */}
                        {isExpanded && (
                          <div className="border-t border-slate-700/40 px-4 py-3 bg-slate-900/30">
                            {validating === idx.index_name ? (
                              <div className="flex items-center gap-2 text-slate-400 text-xs">
                                <RefreshCw size={12} className="animate-spin" />
                                Fetching and validating from NSE…
                              </div>
                            ) : validationResult && validationResult.index_name === idx.index_name ? (
                              <div className="space-y-3">
                                <div className="flex gap-4 text-xs">
                                  <span className="text-emerald-400">✓ {validationResult.matched_count} matched</span>
                                  {validationResult.auto_resolved_count > 0 && (
                                    <span className="text-amber-400">~ {validationResult.auto_resolved_count} auto-resolved</span>
                                  )}
                                  {validationResult.missing_count > 0 && (
                                    <span className="text-red-400">✗ {validationResult.missing_count} missing</span>
                                  )}
                                  <span className={statusColor(validationResult.coverage_pct)}>
                                    {safeFixed(validationResult.coverage_pct)}% coverage
                                  </span>
                                </div>
                                {validationResult.missing.length > 0 && (
                                  <div>
                                    <div className="text-xs text-red-400 font-medium mb-1">Missing Symbols:</div>
                                    <div className="flex flex-wrap gap-1">
                                      {validationResult.missing.map(m => (
                                        <span key={m.nse_symbol} className="px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 text-[10px]">
                                          {m.nse_symbol} ({m.reason})
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            ) : (
                              <div className="text-xs text-slate-500">
                                Click <Shield size={10} className="inline" /> Validate to check constituent coverage from NSE live data.
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Refresh Log Tab */}
      {activeTab === 'log' && (
        <div className="space-y-2">
          {refreshLog.length === 0 ? (
            <div className="text-center py-16 text-slate-500">No refresh history yet.</div>
          ) : (
            refreshLog.map((log, i) => (
              <div key={i} className="bg-slate-800/40 border border-slate-700/40 rounded-xl px-4 py-3 flex items-center gap-4">
                <span className={`text-[10px] px-2 py-0.5 rounded border ${statusBg(log.status)} font-medium`}>
                  {log.status}
                </span>
                <div className="flex-1">
                  <div className="text-sm font-medium text-white">{log.index_name}</div>
                  <div className="text-[10px] text-slate-500">
                    matched {log.matched_count} · missing {log.missing_count} · +{log.added_count} added · -{log.removed_count} removed
                  </div>
                </div>
                <div className={`text-sm font-semibold ${statusColor(log.coverage_pct)}`}>
                  {safeFixed(log.coverage_pct)}%
                </div>
                <div className="text-[10px] text-slate-500 text-right">
                  {log.refreshed_at ? new Date(log.refreshed_at).toLocaleString('en-IN') : '—'}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default IndexManagement;
