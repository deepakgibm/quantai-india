import React, { useEffect, useState } from 'react';
import { Activity, Database, CheckCircle, AlertCircle, Clock, Server, Trash2, RefreshCw, ShieldCheck, Zap } from 'lucide-react';
import { api } from '../services/api';

interface HealthCheck {
    status: string;
    timestamp: string;
    checks: {
        dragonfly?: { status: string; backend: string; latency_ms: number };
        database?: { status: string; backend: string; latency_ms: number };
        upstox_api?: { status: string; circuit: string };
        gemini_api?: { status: string; circuit: string };
    };
}

const AdminMonitoring: React.FC = () => {
    const [health, setHealth] = useState<HealthCheck | null>(null);
    const [etl, setEtl] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        try {
            const [healthData, etlData] = await Promise.all([
                api.getSystemHealth(),
                api.getEtlLogs()
            ]);
            setHealth(healthData);
            setEtl(etlData);
            setError(null);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 10000);
        return () => clearInterval(interval);
    }, []);

    const handleClearCache = async () => {
        if (!confirm('Clear metadata and strategy cache? This will force a refresh on next request.')) return;
        try {
            // We'll use a generic runScanner for cache clear if the endpoint exists
            // (Assuming /api/metrics/refresh exists or similar)
            await api.runScanner('/api/metrics/refresh');
            alert('Cache cleared successfully');
            fetchData();
        } catch (e: any) {
            alert('Cache clear failed: ' + e.message);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white">System Monitoring</h1>
                    <p className="text-slate-500 dark:text-slate-400">Health, connectivity, and data ingestion pipeline</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={handleClearCache}
                        className="flex items-center gap-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 px-4 py-2 rounded-lg transition-colors border border-slate-200 dark:border-slate-600"
                    >
                        <Trash2 size={18} />
                        <span>Clear Cache</span>
                    </button>
                    <button
                        onClick={fetchData}
                        className="p-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg transition-colors"
                    >
                        <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
                    </button>
                </div>
            </div>

            {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 flex items-center gap-3 text-red-600">
                    <AlertCircle size={20} />
                    <span>Connection issue: {error}</span>
                </div>
            )}

            {/* Health Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <HealthCard
                    title="DragonflyDB"
                    status={health?.checks.dragonfly?.status}
                    latency={health?.checks.dragonfly?.latency_ms}
                    icon={<Zap className="text-amber-500" />}
                    detail={health?.checks.dragonfly?.backend}
                />
                <HealthCard
                    title="PostgreSQL"
                    status={health?.checks.database?.status}
                    latency={health?.checks.database?.latency_ms}
                    icon={<Database className="text-brand-500" />}
                    detail={health?.checks.database?.backend}
                />
                <HealthCard
                    title="Upstox API"
                    status={health?.checks.upstox_api?.status}
                    icon={<ShieldCheck className="text-blue-500" />}
                    detail={`Circuit: ${health?.checks.upstox_api?.circuit || 'Unknown'}`}
                />
                <HealthCard
                    title="Gemini AI"
                    status={health?.checks.gemini_api?.status}
                    icon={<Activity className="text-purple-500" />}
                    detail={`Circuit: ${health?.checks.gemini_api?.circuit || 'Unknown'}`}
                />
            </div>

            {/* ETL Pipeline View */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
                <div className="p-6 border-b border-slate-100 dark:border-slate-700 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-green-500/10 rounded-lg">
                            <Server className="text-green-500" size={20} />
                        </div>
                        <div>
                            <h3 className="font-bold text-slate-900 dark:text-white">Data Ingestion (ETL)</h3>
                            <p className="text-xs text-slate-500">NIFTY 500 Historical & Minute candles</p>
                        </div>
                    </div>
                    {etl && (
                        <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${etl.status === 'loading' ? 'bg-blue-100 text-blue-600 animate-pulse' : 'bg-green-100 text-green-600'}`}>
                            {etl.status}
                        </span>
                    )}
                </div>

                <div className="p-6">
                    {!etl ? (
                        <div className="text-center py-10 text-slate-400">No ETL status available</div>
                    ) : (
                        <div className="space-y-6">
                            <div className="flex items-center justify-between">
                                <div className="space-y-1">
                                    <span className="text-sm text-slate-500 block">Ingestion Progress</span>
                                    <span className="text-2xl font-bold font-mono">{etl.current_symbol_index} / {etl.total_symbols} Symbols</span>
                                </div>
                                <div className="text-right space-y-1">
                                    <span className="text-sm text-slate-500 block">Last Update</span>
                                    <span className="text-sm font-medium">{new Date().toLocaleTimeString()}</span>
                                </div>
                            </div>

                            <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-3 overflow-hidden">
                                <div
                                    className="bg-brand-500 h-full transition-all duration-1000"
                                    style={{ width: `${(etl.current_symbol_index / (etl.total_symbols || 1)) * 100}%` }}
                                />
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="p-4 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-100 dark:border-slate-800">
                                    <p className="text-xs text-slate-500 uppercase font-bold mb-1">Last Job Start</p>
                                    <p className="font-mono text-sm">{etl.last_start ? new Date(etl.last_start).toLocaleString() : 'Never'}</p>
                                </div>
                                <div className="p-4 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-100 dark:border-slate-800">
                                    <p className="text-xs text-slate-500 uppercase font-bold mb-1">Last Job Completion</p>
                                    <p className="font-mono text-sm">{etl.last_end ? new Date(etl.last_end).toLocaleString() : 'Never'}</p>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

const HealthCard = ({ title, status, latency, icon, detail }: any) => (
    <div className="bg-white dark:bg-slate-800 p-5 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm flex flex-col justify-between">
        <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-slate-50 dark:bg-slate-900 rounded-lg">{icon}</div>
            <div className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest ${status === 'healthy' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                {status || 'Unknown'}
            </div>
        </div>
        <div>
            <h4 className="font-bold text-slate-700 dark:text-slate-200 text-sm mb-1">{title}</h4>
            <div className="flex justify-between items-end">
                <span className="text-xs text-slate-500">{detail || 'Operational'}</span>
                {latency && <span className="text-xs font-mono text-slate-400">{latency}ms</span>}
            </div>
        </div>
    </div>
);

export default AdminMonitoring;
