import React, { useState, useEffect } from 'react';
import {
    Activity,
    Play,
    Square,
    RefreshCw,
    TrendingUp,
    Clock,
    Shield,
    CheckCircle,
    AlertTriangle,
    Database,
    Cpu,
    Zap
} from 'lucide-react';
import { getAuthHeaders, API_URL } from '../services/api';

interface TrainingStatus {
    is_running: boolean;
    pid: number | null;
    metrics: {
        stage: string;
        epoch: number;
        total_epochs: number;
        train_loss: number;
        val_loss: number;
        best_loss: number;
        last_update: string;
        reason?: string;
    };
    market_status: string;
    timestamp: string;
}

const MLTrainingControl: React.FC = () => {
    const [status, setStatus] = useState<TrainingStatus | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [epochs, setEpochs] = useState(50);
    const [batchSize, setBatchSize] = useState(32);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 5000);
        return () => clearInterval(interval);
    }, []);

    const fetchStatus = async () => {
        try {
            const response = await fetch(`${API_URL}/api/v1/ml/train/status`, {
                headers: getAuthHeaders()
            });
            if (response.ok) {
                const data = await response.json();
                setStatus(data);
            }
        } catch (err) {
            console.error('Failed to fetch training status:', err);
        }
    };

    const handleStart = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_URL}/api/v1/ml/train/start?epochs=${epochs}&batch_size=${batchSize}`, {
                method: 'POST',
                headers: getAuthHeaders()
            });
            const data = await response.json();
            if (data.status === 'success') {
                fetchStatus();
            } else {
                setError(data.message);
            }
        } catch (err: any) {
            setError('Failed to start training');
        } finally {
            setIsLoading(false);
        }
    };

    const handleStop = async () => {
        setIsLoading(true);
        try {
            const response = await fetch(`${API_URL}/api/v1/ml/train/stop`, {
                method: 'POST',
                headers: getAuthHeaders()
            });
            if (response.ok) {
                fetchStatus();
            }
        } catch (err) {
            setError('Failed to stop training');
        } finally {
            setIsLoading(false);
        }
    };

    const isMarketOpen = status?.market_status === 'OPEN';

    return (
        <div className="h-full flex flex-col gap-6 p-6 overflow-auto">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-blue-600 rounded-xl shadow-lg shadow-blue-500/20">
                        <Cpu size={24} className="text-white" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">AI Training Control</h1>
                        <div className="flex items-center gap-2 mt-0.5">
                            <div className={`w-2 h-2 rounded-full ${status?.is_running ? 'bg-green-500 animate-pulse' : 'bg-slate-400'}`} />
                            <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">
                                {status?.is_running ? `System Active (PID: ${status.pid})` : 'System Standby'}
                            </span>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <div className={`px-4 py-2 rounded-lg border flex items-center gap-2 ${isMarketOpen ? 'bg-amber-500/10 border-amber-500/30 text-amber-600' : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600'}`}>
                        <Clock size={16} />
                        <span className="text-xs font-bold font-mono">
                            MARKET: {status?.market_status || 'LOADING...'}
                        </span>
                    </div>
                    {isMarketOpen && (
                        <div className="hidden md:flex items-center gap-2 px-3 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-red-500 text-[10px] font-bold uppercase">
                            <AlertTriangle size={14} />
                            Training Gated
                        </div>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Control Panel */}
                <div className="lg:col-span-1 bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
                    <h2 className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                        <Zap size={16} className="text-amber-500" />
                        Execution Settings
                    </h2>

                    <div className="space-y-5">
                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-slate-500">Target Training Epochs</label>
                            <input
                                type="number"
                                value={epochs}
                                onChange={(e) => setEpochs(Number(e.target.value))}
                                disabled={status?.is_running}
                                className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl p-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all disabled:opacity-50"
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-slate-500">Batch Size (SGD)</label>
                            <select
                                value={batchSize}
                                onChange={(e) => setBatchSize(Number(e.target.value))}
                                disabled={status?.is_running}
                                className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl p-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all disabled:opacity-50"
                            >
                                <option value={16}>16 (Fine-grained)</option>
                                <option value={32}>32 (Standard)</option>
                                <option value={64}>64 (Hardware-optimized)</option>
                                <option value={128}>128 (Large Batch)</option>
                            </select>
                        </div>

                        <div className="pt-4 space-y-3">
                            {!status?.is_running ? (
                                <button
                                    onClick={handleStart}
                                    disabled={isLoading || isMarketOpen}
                                    className="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-blue-500/20 disabled:grayscale disabled:opacity-50"
                                >
                                    <Play size={18} fill="currentColor" />
                                    START TRAINING SESSION
                                </button>
                            ) : (
                                <button
                                    onClick={handleStop}
                                    disabled={isLoading}
                                    className="w-full py-4 bg-red-500 hover:bg-red-600 text-white rounded-xl font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-red-500/20"
                                >
                                    <Square size={18} fill="currentColor" />
                                    EMERGENCY ABORT
                                </button>
                            )}

                            {isMarketOpen && !status?.is_running && (
                                <p className="text-[10px] text-center text-slate-400 italic">
                                    Training disabled during live market hours to prioritize inference latency.
                                </p>
                            )}

                            {error && (
                                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-500 text-xs text-center font-medium">
                                    {error}
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="mt-8 pt-6 border-t border-slate-100 dark:border-slate-700 space-y-4">
                        <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-tighter text-slate-400">
                            <span>Auto-Stop Meta</span>
                            <span>Enabled</span>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-slate-100 dark:bg-slate-900 rounded-lg text-slate-500">
                                <Shield size={16} />
                            </div>
                            <div>
                                <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300">Residency Protection</h4>
                                <p className="text-[10px] text-slate-500">Auto-terminates at 09:15 IST</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Metrics Monitoring */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Status Header */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
                            <div className="flex items-center justify-between mb-4">
                                <span className="text-xs font-bold text-slate-400 uppercase">Process Stage</span>
                                <Activity size={16} className="text-blue-500" />
                            </div>
                            <div className="text-2xl font-black text-slate-800 dark:text-white uppercase tracking-tight">
                                {status?.is_running ? (status.metrics.stage || 'PROCESSING') : (status?.metrics.reason || 'IDLE')}
                            </div>
                            {status?.metrics.last_update && (
                                <div className="text-[10px] text-slate-500 mt-1">
                                    Last heartbeat: {new Date(status.metrics.last_update).toLocaleTimeString()}
                                </div>
                            )}
                        </div>

                        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
                            <div className="flex items-center justify-between mb-4">
                                <span className="text-xs font-bold text-slate-400 uppercase">Training Progress</span>
                                <RefreshCw size={16} className={status?.is_running ? 'text-blue-500 animate-spin' : 'text-slate-400'} />
                            </div>
                            <div className="flex items-end gap-2">
                                <span className="text-3xl font-black text-slate-800 dark:text-white">
                                    {status?.metrics.epoch || 0}
                                </span>
                                <span className="text-slate-400 mb-1 font-bold">/ {status?.metrics.total_epochs || epochs} EPOCHS</span>
                            </div>
                            <div className="w-full bg-slate-100 dark:bg-slate-900 h-1.5 rounded-full mt-4 overflow-hidden">
                                <div
                                    className="bg-blue-600 h-full transition-all duration-1000"
                                    style={{ width: `${((status?.metrics.epoch || 0) / (status?.metrics.total_epochs || epochs)) * 100}%` }}
                                />
                            </div>
                        </div>
                    </div>

                    {/* Analytics Dashboard */}
                    <div className="bg-slate-900 rounded-2xl p-8 border border-slate-800 shadow-2xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-8 opacity-10">
                            <TrendingUp size={120} className="text-blue-500" />
                        </div>

                        <h3 className="text-sm font-bold text-blue-400 uppercase tracking-widest mb-8 flex items-center gap-2">
                            <Activity size={18} />
                            Neural Dynamics
                        </h3>

                        <div className="grid grid-cols-2 md:grid-cols-3 gap-8 relative z-10">
                            <div className="space-y-1">
                                <p className="text-[10px] font-bold text-slate-500 uppercase">Training Loss (MSE)</p>
                                <p className="text-2xl font-mono font-bold text-white">
                                    {status?.metrics.train_loss?.toFixed(6) || '0.000000'}
                                </p>
                            </div>
                            <div className="space-y-1">
                                <p className="text-[10px] font-bold text-slate-500 uppercase">Validation Loss</p>
                                <p className="text-2xl font-mono font-bold text-white text-blue-400">
                                    {status?.metrics.val_loss?.toFixed(6) || '0.000000'}
                                </p>
                            </div>
                            <div className="space-y-1">
                                <p className="text-[10px] font-bold text-slate-500 uppercase">Best Observed Loss</p>
                                <p className="text-2xl font-mono font-bold text-emerald-400">
                                    {status?.metrics.best_loss?.toFixed(6) || '0.000000'}
                                </p>
                            </div>
                        </div>

                        <div className="mt-12 p-4 bg-slate-800/50 rounded-xl border border-slate-700/50 flex items-center gap-4">
                            <div className="p-3 bg-blue-500/10 rounded-lg">
                                <Database size={20} className="text-blue-400" />
                            </div>
                            <div>
                                <h4 className="text-sm font-bold text-white tracking-tight">Transformer V1 Architecture</h4>
                                <p className="text-xs text-slate-400">Processing 142k+ features from Parquet Feature Store</p>
                            </div>
                            <div className="ml-auto">
                                <CheckCircle size={20} className="text-emerald-500" />
                            </div>
                        </div>
                    </div>

                    {/* Log Stream Placeholder */}
                    <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm opacity-60">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Inference Weight Sync</h3>
                            <div className="flex items-center gap-1">
                                <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                                <span className="text-[10px] text-blue-500 font-bold">READY</span>
                            </div>
                        </div>
                        <p className="text-[11px] text-slate-500 italic">
                            Automated hot-swap enabled. Forecast API will pick up new weights immediately upon next best-loss save.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MLTrainingControl;
