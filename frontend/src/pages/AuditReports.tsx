import React, { useState, useEffect } from 'react';
import {
    FileText,
    Download,
    Clock,
    CheckCircle2,
    AlertTriangle,
    Filter,
    RefreshCw,
    Eye,
    ChevronDown,
    Shield,
    Activity
} from 'lucide-react';

interface AuditLog {
    timestamp: string;
    event_type: string;
    strategy_name: string;
    action: string;
    details: Record<string, any>;
    user?: string;
    checksum?: string;
}

const AuditReports: React.FC = () => {
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [filter, setFilter] = useState<string>('all');
    const [expandedLog, setExpandedLog] = useState<number | null>(null);

    // Mock data - in production this would come from API
    useEffect(() => {
        fetchLogs();
    }, []);

    const fetchLogs = async () => {
        setIsLoading(true);
        // Simulated audit logs
        await new Promise(r => setTimeout(r, 500));
        setLogs([
            {
                timestamp: new Date().toISOString(),
                event_type: 'BACKTEST_RUN',
                strategy_name: 'MACrossover',
                action: 'Strategy backtest executed',
                details: {
                    symbol: 'RELIANCE',
                    start_date: '2023-01-01',
                    end_date: '2024-01-01',
                    sharpe: 1.24,
                    total_return: 15.4
                },
                user: 'system',
                checksum: 'sha256:a4f5e6...'
            },
            {
                timestamp: new Date(Date.now() - 3600000).toISOString(),
                event_type: 'OPTIMIZATION',
                strategy_name: 'MACrossover',
                action: 'Parameter optimization completed',
                details: {
                    method: 'bayesian',
                    iterations: 50,
                    best_params: { fast: 10, slow: 30 }
                },
                user: 'system',
                checksum: 'sha256:b7c8d9...'
            },
            {
                timestamp: new Date(Date.now() - 7200000).toISOString(),
                event_type: 'DRIFT_ALERT',
                strategy_name: 'RSI_Strategy',
                action: 'Drift detected - Sharpe degradation',
                details: {
                    severity: 'high',
                    sharpe_delta: -0.45,
                    action_taken: 'Strategy paused'
                },
                user: 'auto',
                checksum: 'sha256:c9d0e1...'
            },
            {
                timestamp: new Date(Date.now() - 86400000).toISOString(),
                event_type: 'TRADE_SIGNAL',
                strategy_name: 'MACrossover',
                action: 'Buy signal generated',
                details: {
                    symbol: 'TCS',
                    signal: 'BUY',
                    price: 3450.25,
                    quantity: 100
                },
                user: 'system',
                checksum: 'sha256:d1e2f3...'
            }
        ]);
        setIsLoading(false);
    };

    const getEventTypeColor = (type: string) => {
        switch (type) {
            case 'BACKTEST_RUN': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
            case 'OPTIMIZATION': return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400';
            case 'DRIFT_ALERT': return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
            case 'TRADE_SIGNAL': return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
            default: return 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300';
        }
    };

    const getEventIcon = (type: string) => {
        switch (type) {
            case 'BACKTEST_RUN': return <Activity size={16} />;
            case 'OPTIMIZATION': return <Filter size={16} />;
            case 'DRIFT_ALERT': return <AlertTriangle size={16} />;
            case 'TRADE_SIGNAL': return <CheckCircle2 size={16} />;
            default: return <FileText size={16} />;
        }
    };

    const filteredLogs = filter === 'all'
        ? logs
        : logs.filter(l => l.event_type === filter);

    const exportToJSON = () => {
        const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit_logs_${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
    };

    return (
        <div className="h-full flex flex-col gap-6 overflow-auto p-1">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-3 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl shadow-lg shadow-indigo-500/20">
                        <Shield size={24} className="text-white" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Audit & Reports</h1>
                        <p className="text-sm text-slate-500 dark:text-slate-400">SEBI-compliant immutable decision logs</p>
                    </div>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={fetchLogs}
                        className="p-2 bg-slate-100 dark:bg-slate-800 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700"
                    >
                        <RefreshCw size={18} className={isLoading ? 'animate-spin' : ''} />
                    </button>
                    <button
                        onClick={exportToJSON}
                        className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-medium flex items-center gap-2"
                    >
                        <Download size={18} /> Export JSON
                    </button>
                </div>
            </div>

            {/* Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                    <p className="text-sm text-slate-500 mb-1">Total Events</p>
                    <p className="text-2xl font-bold text-slate-800 dark:text-white">{logs.length}</p>
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                    <p className="text-sm text-slate-500 mb-1">Backtests</p>
                    <p className="text-2xl font-bold text-blue-600">{logs.filter(l => l.event_type === 'BACKTEST_RUN').length}</p>
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                    <p className="text-sm text-slate-500 mb-1">Drift Alerts</p>
                    <p className="text-2xl font-bold text-red-600">{logs.filter(l => l.event_type === 'DRIFT_ALERT').length}</p>
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                    <p className="text-sm text-slate-500 mb-1">Trade Signals</p>
                    <p className="text-2xl font-bold text-green-600">{logs.filter(l => l.event_type === 'TRADE_SIGNAL').length}</p>
                </div>
            </div>

            {/* Filters */}
            <div className="flex gap-2 flex-wrap">
                {['all', 'BACKTEST_RUN', 'OPTIMIZATION', 'DRIFT_ALERT', 'TRADE_SIGNAL'].map(f => (
                    <button
                        key={f}
                        onClick={() => setFilter(f)}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${filter === f
                                ? 'bg-indigo-600 text-white'
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200'
                            }`}
                    >
                        {f === 'all' ? 'All' : f.replace('_', ' ')}
                    </button>
                ))}
            </div>

            {/* Logs */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                <div className="p-4 border-b border-slate-200 dark:border-slate-700">
                    <h2 className="font-semibold text-slate-800 dark:text-white">Event Log ({filteredLogs.length})</h2>
                </div>

                <div className="divide-y divide-slate-100 dark:divide-slate-700">
                    {filteredLogs.map((log, i) => (
                        <div key={i} className="p-4">
                            <div
                                onClick={() => setExpandedLog(expandedLog === i ? null : i)}
                                className="flex items-center justify-between cursor-pointer"
                            >
                                <div className="flex items-center gap-4">
                                    <span className={`px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1 ${getEventTypeColor(log.event_type)}`}>
                                        {getEventIcon(log.event_type)}
                                        {log.event_type.replace('_', ' ')}
                                    </span>
                                    <div>
                                        <p className="font-medium text-slate-800 dark:text-white">{log.action}</p>
                                        <p className="text-sm text-slate-500">{log.strategy_name}</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4">
                                    <div className="text-right">
                                        <p className="text-sm text-slate-500">
                                            <Clock size={12} className="inline mr-1" />
                                            {new Date(log.timestamp).toLocaleString()}
                                        </p>
                                    </div>
                                    <ChevronDown
                                        size={18}
                                        className={`text-slate-400 transition-transform ${expandedLog === i ? 'rotate-180' : ''}`}
                                    />
                                </div>
                            </div>

                            {expandedLog === i && (
                                <div className="mt-4 p-4 bg-slate-50 dark:bg-slate-900 rounded-lg">
                                    <h4 className="text-sm font-semibold text-slate-600 dark:text-slate-400 mb-2">Details</h4>
                                    <pre className="text-xs text-slate-700 dark:text-slate-300 overflow-x-auto">
                                        {JSON.stringify(log.details, null, 2)}
                                    </pre>
                                    {log.checksum && (
                                        <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
                                            <p className="text-xs text-slate-500">
                                                <Shield size={12} className="inline mr-1" />
                                                Checksum: <code className="bg-slate-200 dark:bg-slate-800 px-1 rounded">{log.checksum}</code>
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}

                    {filteredLogs.length === 0 && (
                        <div className="p-12 text-center">
                            <FileText size={48} className="text-slate-300 mx-auto mb-4" />
                            <p className="text-slate-500">No audit logs found</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default AuditReports;
