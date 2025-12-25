import React, { useEffect, useState } from 'react';
import { Activity, Database, CheckCircle, AlertCircle, Clock, Server } from 'lucide-react';

interface Tracker {
    last_start: string | null;
    last_end: string | null;
    status: string;
    current_symbol_index: number;
    total_symbols: number;
}

const ETLStatus: React.FC = () => {
    const [tracker, setTracker] = useState<Tracker | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(true);

    const fetchStatus = async () => {
        try {
            const res = await fetch('http://localhost:8000/api/v1/etl/status');
            if (!res.ok) {
                if (res.status === 404) {
                    // Tracker file might not exist yet if script hasn't started or created it
                    setTracker(null);
                    setLoading(false);
                    return;
                }
                throw new Error(`HTTP ${res.status}`);
            }
            const data = await res.json();
            setTracker(data);
            setError(null);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 5000); // refresh every 5s
        return () => clearInterval(interval);
    }, []);

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'running':
            case 'loading':
                return 'text-blue-500';
            case 'completed':
            case 'success':
                return 'text-green-500';
            case 'error':
                return 'text-red-500';
            default:
                return 'text-gray-500';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'running':
            case 'loading':
                return <Activity className="w-6 h-6 animate-pulse" />;
            case 'completed':
            case 'success':
                return <CheckCircle className="w-6 h-6" />;
            case 'error':
                return <AlertCircle className="w-6 h-6" />;
            default:
                return <Clock className="w-6 h-6" />;
        }
    };

    if (loading && !tracker) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white">System Monitoring</h1>
                    <p className="text-slate-500 dark:text-slate-400">Real-time status of data ingestion and system health</p>
                </div>
                <div className="flex items-center space-x-2 text-sm text-slate-500">
                    <span className="relative flex h-3 w-3">
                        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${tracker?.status === 'loading' ? 'bg-green-400' : 'bg-gray-400'}`}></span>
                        <span className={`relative inline-flex rounded-full h-3 w-3 ${tracker?.status === 'loading' ? 'bg-green-500' : 'bg-gray-500'}`}></span>
                    </span>
                    <span>Live Updates</span>
                </div>
            </div>

            {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-center space-x-3 text-red-700 dark:text-red-400">
                    <AlertCircle className="w-5 h-5" />
                    <span>Error fetching status: {error}</span>
                </div>
            )}

            {!tracker && !error && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 flex items-center space-x-3 text-yellow-700 dark:text-yellow-400">
                    <Clock className="w-5 h-5" />
                    <span>Waiting for ETL process to start...</span>
                </div>
            )}

            {tracker && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {/* Status Card */}
                    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="font-semibold text-slate-700 dark:text-slate-300">Current Status</h3>
                            <div className={`${getStatusColor(tracker.status)}`}>
                                {getStatusIcon(tracker.status)}
                            </div>
                        </div>
                        <div className="text-3xl font-bold text-slate-900 dark:text-white capitalize">
                            {tracker.status}
                        </div>
                        <p className="text-sm text-slate-500 mt-2">
                            {tracker.status === 'loading' ? 'Data ingestion in progress' : 'Waiting for next job'}
                        </p>
                    </div>

                    {/* Progress Card */}
                    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="font-semibold text-slate-700 dark:text-slate-300">Progress</h3>
                            <Database className="w-6 h-6 text-brand-500" />
                        </div>
                        <div className="space-y-4">
                            <div>
                                <div className="flex justify-between text-sm mb-1">
                                    <span className="text-slate-500">Symbols Processed</span>
                                    <span className="font-medium text-slate-900 dark:text-white">
                                        {tracker.current_symbol_index} / {tracker.total_symbols}
                                    </span>
                                </div>
                                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2.5">
                                    <div
                                        className="bg-brand-500 h-2.5 rounded-full transition-all duration-500"
                                        style={{ width: `${(tracker.current_symbol_index / (tracker.total_symbols || 1)) * 100}%` }}
                                    ></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Time Range Card */}
                    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="font-semibold text-slate-700 dark:text-slate-300">Current Batch</h3>
                            <Server className="w-6 h-6 text-purple-500" />
                        </div>
                        <div className="space-y-2">
                            <div>
                                <p className="text-xs text-slate-500 uppercase tracking-wider">Start Date</p>
                                <p className="font-mono text-lg text-slate-900 dark:text-white">
                                    {tracker.last_start ? new Date(tracker.last_start).toLocaleDateString() : 'N/A'}
                                </p>
                            </div>
                            <div>
                                <p className="text-xs text-slate-500 uppercase tracking-wider">End Date</p>
                                <p className="font-mono text-lg text-slate-900 dark:text-white">
                                    {tracker.last_end ? new Date(tracker.last_end).toLocaleDateString() : 'N/A'}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Logs Section Placeholder */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
                <h3 className="font-semibold text-slate-700 dark:text-slate-300 mb-4">System Logs</h3>
                <div className="bg-slate-900 rounded-lg p-4 font-mono text-sm text-slate-300 h-48 overflow-y-auto">
                    <p className="text-green-400">$ system check --status</p>
                    <p>All systems operational.</p>
                    <p className="text-green-400">$ etl --status</p>
                    <p>{tracker ? JSON.stringify(tracker, null, 2) : 'Fetching status...'}</p>
                </div>
            </div>
        </div>
    );
};

export default ETLStatus;
