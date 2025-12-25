import React, { useState, useEffect } from 'react';
import {
    AlertTriangle,
    Bell,
    CheckCircle2,
    XCircle,
    Activity,
    Pause,
    Play,
    RefreshCw,
    ChevronRight,
    Eye,
    Shield,
    TrendingDown
} from 'lucide-react';

interface MonitorStatus {
    strategy_name: string;
    is_paused: boolean;
    last_check: string | null;
    live_trade_count: number;
    total_alerts: number;
    unacknowledged_alerts: number;
}

interface DriftAlert {
    timestamp: string;
    alert_type: string;
    strategy_name: string;
    message: string;
    severity: string;
    action_required: string;
    acknowledged: boolean;
    acknowledged_by: string | null;
}

const DriftMonitor: React.FC = () => {
    const [monitors, setMonitors] = useState<MonitorStatus[]>([]);
    const [selectedMonitor, setSelectedMonitor] = useState<string | null>(null);
    const [alerts, setAlerts] = useState<DriftAlert[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Create monitor form
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [newMonitorName, setNewMonitorName] = useState('');
    const [backtestSharpe, setBacktestSharpe] = useState(1.0);

    useEffect(() => {
        fetchMonitors();
    }, []);

    const fetchMonitors = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/alerts/monitors');
            if (response.ok) {
                const data = await response.json();
                setMonitors(data.monitors || []);
            }
        } catch (err) {
            console.error('Failed to fetch monitors');
        }
    };

    const fetchAlerts = async (strategyName: string) => {
        try {
            const response = await fetch(`http://localhost:8000/api/alerts/monitor/${strategyName}/alerts`);
            if (response.ok) {
                const data = await response.json();
                setAlerts(data.alerts || []);
            }
        } catch (err) {
            console.error('Failed to fetch alerts');
        }
    };

    const createMonitor = async () => {
        setIsLoading(true);
        try {
            const response = await fetch('http://localhost:8000/api/alerts/monitor/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    strategy_name: newMonitorName,
                    backtest_returns: [0.02, -0.01, 0.03, 0.015, -0.005, 0.025, 0.01, -0.02, 0.04, 0.01],
                    backtest_sharpe: backtestSharpe,
                    check_interval_minutes: 60,
                    auto_pause_on_critical: true
                })
            });

            if (!response.ok) {
                throw new Error('Failed to create monitor');
            }

            setShowCreateForm(false);
            setNewMonitorName('');
            fetchMonitors();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const pauseMonitor = async (name: string) => {
        await fetch(`http://localhost:8000/api/alerts/monitor/${name}/pause?reason=Manual`, {
            method: 'POST'
        });
        fetchMonitors();
    };

    const resumeMonitor = async (name: string) => {
        await fetch(`http://localhost:8000/api/alerts/monitor/${name}/resume?resumed_by=User`, {
            method: 'POST'
        });
        fetchMonitors();
    };

    const acknowledgeAlert = async (strategyName: string, index: number) => {
        await fetch(`http://localhost:8000/api/alerts/monitor/${strategyName}/alerts/${index}/acknowledge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ acknowledged_by: 'User' })
        });
        fetchAlerts(strategyName);
    };

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'critical': return 'bg-red-100 text-red-700 border-red-200';
            case 'high': return 'bg-orange-100 text-orange-700 border-orange-200';
            case 'medium': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
            default: return 'bg-blue-100 text-blue-700 border-blue-200';
        }
    };

    const getSeverityIcon = (severity: string) => {
        switch (severity) {
            case 'critical': return <XCircle className="text-red-500" size={20} />;
            case 'high': return <AlertTriangle className="text-orange-500" size={20} />;
            case 'medium': return <Bell className="text-yellow-500" size={20} />;
            default: return <Activity className="text-blue-500" size={20} />;
        }
    };

    return (
        <div className="h-full flex flex-col gap-6 overflow-auto p-1">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-3 bg-gradient-to-br from-rose-500 to-pink-600 rounded-xl shadow-lg shadow-rose-500/20">
                        <Shield size={24} className="text-white" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Drift Monitor</h1>
                        <p className="text-sm text-slate-500 dark:text-slate-400">Real-time strategy performance monitoring</p>
                    </div>
                </div>
                <button
                    onClick={() => setShowCreateForm(true)}
                    className="px-4 py-2 bg-gradient-to-r from-rose-600 to-pink-600 text-white rounded-lg font-medium flex items-center gap-2"
                >
                    <Bell size={18} /> Create Monitor
                </button>
            </div>

            {/* Create Monitor Modal */}
            {showCreateForm && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 w-full max-w-md">
                        <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-4">Create Drift Monitor</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Strategy Name</label>
                                <input
                                    type="text"
                                    value={newMonitorName}
                                    onChange={(e) => setNewMonitorName(e.target.value)}
                                    className="w-full p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
                                    placeholder="MACrossover_RELIANCE"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Backtest Sharpe</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    value={backtestSharpe}
                                    onChange={(e) => setBacktestSharpe(Number(e.target.value))}
                                    className="w-full p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
                                />
                            </div>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setShowCreateForm(false)}
                                    className="flex-1 py-2 border border-slate-300 rounded-lg"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={createMonitor}
                                    disabled={isLoading || !newMonitorName}
                                    className="flex-1 py-2 bg-rose-600 text-white rounded-lg disabled:opacity-50"
                                >
                                    {isLoading ? 'Creating...' : 'Create'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Monitors List */}
                <div className="lg:col-span-1 bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-bold text-slate-800 dark:text-white">Active Monitors</h2>
                        <button onClick={fetchMonitors} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg">
                            <RefreshCw size={16} />
                        </button>
                    </div>

                    <div className="space-y-3">
                        {monitors.length === 0 ? (
                            <p className="text-sm text-slate-500 text-center py-8">No active monitors</p>
                        ) : (
                            monitors.map((m) => (
                                <div
                                    key={m.strategy_name}
                                    onClick={() => {
                                        setSelectedMonitor(m.strategy_name);
                                        fetchAlerts(m.strategy_name);
                                    }}
                                    className={`p-4 rounded-xl border cursor-pointer transition-all ${selectedMonitor === m.strategy_name
                                            ? 'border-rose-500 bg-rose-50 dark:bg-rose-900/20'
                                            : 'border-slate-200 dark:border-slate-700 hover:border-rose-300'
                                        }`}
                                >
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="font-semibold text-slate-800 dark:text-white">{m.strategy_name}</span>
                                        {m.is_paused ? (
                                            <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-700 rounded-full">Paused</span>
                                        ) : (
                                            <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded-full">Active</span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-4 text-sm text-slate-500">
                                        <span>{m.live_trade_count} trades</span>
                                        {m.unacknowledged_alerts > 0 && (
                                            <span className="flex items-center gap-1 text-red-500">
                                                <Bell size={14} /> {m.unacknowledged_alerts}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Alerts Panel */}
                <div className="lg:col-span-2 space-y-6">
                    {selectedMonitor ? (
                        <>
                            {/* Monitor Controls */}
                            <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h3 className="text-lg font-bold text-slate-800 dark:text-white">{selectedMonitor}</h3>
                                        <p className="text-sm text-slate-500">Monitoring live performance drift</p>
                                    </div>
                                    <div className="flex gap-3">
                                        {monitors.find(m => m.strategy_name === selectedMonitor)?.is_paused ? (
                                            <button
                                                onClick={() => resumeMonitor(selectedMonitor)}
                                                className="px-4 py-2 bg-green-600 text-white rounded-lg flex items-center gap-2"
                                            >
                                                <Play size={16} /> Resume
                                            </button>
                                        ) : (
                                            <button
                                                onClick={() => pauseMonitor(selectedMonitor)}
                                                className="px-4 py-2 bg-yellow-600 text-white rounded-lg flex items-center gap-2"
                                            >
                                                <Pause size={16} /> Pause
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Alerts */}
                            <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700">
                                <h3 className="text-lg font-bold text-slate-800 dark:text-white mb-4">Drift Alerts</h3>
                                {alerts.length === 0 ? (
                                    <div className="text-center py-8">
                                        <CheckCircle2 size={48} className="text-green-500 mx-auto mb-2" />
                                        <p className="text-slate-500">No drift detected</p>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {alerts.map((alert, i) => (
                                            <div
                                                key={i}
                                                className={`p-4 rounded-xl border ${getSeverityColor(alert.severity)} ${alert.acknowledged ? 'opacity-60' : ''
                                                    }`}
                                            >
                                                <div className="flex items-start gap-3">
                                                    {getSeverityIcon(alert.severity)}
                                                    <div className="flex-1">
                                                        <div className="flex items-center justify-between mb-1">
                                                            <span className="font-semibold">{alert.alert_type}</span>
                                                            <span className="text-xs">
                                                                {new Date(alert.timestamp).toLocaleString()}
                                                            </span>
                                                        </div>
                                                        <p className="text-sm mb-2">{alert.message}</p>
                                                        <div className="flex items-center justify-between">
                                                            <span className="text-xs px-2 py-1 bg-white/50 rounded">
                                                                {alert.action_required}
                                                            </span>
                                                            {!alert.acknowledged && (
                                                                <button
                                                                    onClick={() => acknowledgeAlert(selectedMonitor, i)}
                                                                    className="text-xs px-3 py-1 bg-white text-slate-700 rounded-lg"
                                                                >
                                                                    Acknowledge
                                                                </button>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </>
                    ) : (
                        <div className="bg-white dark:bg-slate-800 rounded-2xl p-12 border border-slate-200 dark:border-slate-700 flex flex-col items-center justify-center text-center">
                            <Eye size={48} className="text-slate-300 mb-4" />
                            <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">Select a Monitor</h3>
                            <p className="text-sm text-slate-500">Click on a monitor to view alerts and controls</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default DriftMonitor;
