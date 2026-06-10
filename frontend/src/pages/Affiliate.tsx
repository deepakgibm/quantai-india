import React, { useState, useEffect } from 'react';
import { Handshake, Loader2, RefreshCw, Link2, Copy, Check, Users, Award, TrendingUp } from 'lucide-react';
import { api } from '../services/api';

const Affiliate: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState<string | null>(null);

  const fetchAffiliateData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getAffiliateDashboard();
      if (response && response.status === 'success') {
        setData(response.affiliates);
      } else {
        setError('Failed to load affiliate analytics');
      }
    } catch (e: any) {
      setError(e.message || 'Error communicating with affiliate service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAffiliateData();
  }, []);

  const handleCopyLink = (link: string, broker: string) => {
    navigator.clipboard.writeText(link);
    setCopiedLink(broker);
    setTimeout(() => setCopiedLink(null), 2000);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 size={40} className="text-brand-500 animate-spin mb-4" />
        <p className="text-slate-400">Loading Broker Affiliate metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12 bg-rose-500/5 border border-rose-500/10 rounded-2xl p-6">
        <p className="text-rose-500 mb-4">{error}</p>
        <button onClick={fetchAffiliateData} className="px-4 py-2 bg-rose-500 text-white rounded-xl text-xs font-bold uppercase">Retry</button>
      </div>
    );
  }

  // Aggregate totals
  const totalClicks = data.reduce((acc: number, item: any) => acc + item.clicks, 0);
  const totalConversions = data.reduce((acc: number, item: any) => acc + item.conversions, 0);
  const totalCommission = data.reduce((acc: number, item: any) => acc + item.commission, 0);
  const conversionRate = totalClicks > 0 ? (totalConversions / totalClicks) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white font-display flex items-center gap-2">
            <Handshake size={28} /> Broker Affiliate Center
          </h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Track partner broker referrals, conversion analytics, commission metrics, and copy links.
          </p>
        </div>
        <button
          onClick={fetchAffiliateData}
          className="flex items-center gap-2 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs font-bold rounded-xl transition-all uppercase tracking-wide shrink-0"
        >
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Commission Earned</span>
            <span className="text-2xl font-bold text-brand-500 block mt-2 font-mono">₹{totalCommission.toLocaleString()}</span>
          </div>
          <TrendingUp className="text-brand-500" size={28} />
        </div>

        <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Total Refer Clicks</span>
            <span className="text-2xl font-bold text-slate-900 dark:text-white block mt-2 font-mono">{totalClicks}</span>
          </div>
          <Users className="text-slate-400" size={28} />
        </div>

        <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Conversions</span>
            <span className="text-2xl font-bold text-slate-900 dark:text-white block mt-2 font-mono">{totalConversions}</span>
          </div>
          <Award className="text-slate-400" size={28} />
        </div>

        <div className="p-5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Conversion Rate</span>
            <span className="text-2xl font-bold text-slate-900 dark:text-white block mt-2 font-mono">{conversionRate.toFixed(1)}%</span>
          </div>
          <Handshake className="text-slate-400" size={28} />
        </div>
      </div>

      {/* Broker Links & Lists */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-6 shadow-sm">
        <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4">Partner Broker Integration Directory</h3>
        
        <div className="space-y-4">
          {data.map((aff: any) => (
            <div
              key={aff.broker_name}
              className="flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-xl p-4 border border-slate-100 dark:border-slate-700/50 bg-slate-50 dark:bg-slate-900/50"
            >
              <div className="space-y-1.5">
                <span className="text-xs font-black text-slate-800 dark:text-white">{aff.broker_name} REFERRALS</span>
                <div className="flex items-center gap-1.5 text-xs text-slate-500">
                  <span>Clicks: <strong className="text-slate-700 dark:text-slate-300 font-mono">{aff.clicks}</strong></span>
                  <span className="text-slate-300">|</span>
                  <span>Conversions: <strong className="text-slate-700 dark:text-slate-300 font-mono">{aff.conversions}</strong></span>
                  <span className="text-slate-300">|</span>
                  <span>Commission: <strong className="text-brand-500 font-mono">₹{aff.commission}</strong></span>
                </div>
              </div>

              {/* Action and link copy */}
              <div className="flex items-center gap-2 max-w-md w-full md:w-auto">
                <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-[10px] font-mono text-slate-500 truncate select-all flex-grow md:w-56">
                  {aff.referral_link}
                </div>
                
                <button
                  onClick={() => handleCopyLink(aff.referral_link, aff.broker_name)}
                  className={`p-2.5 rounded-lg border transition-all ${
                    copiedLink === aff.broker_name
                      ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-500'
                      : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 hover:text-brand-500'
                  }`}
                  title="Copy Link"
                >
                  {copiedLink === aff.broker_name ? <Check size={14} /> : <Copy size={14} />}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Affiliate;
