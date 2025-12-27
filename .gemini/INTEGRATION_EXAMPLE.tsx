/**
 * INTEGRATION EXAMPLE: Enhanced Walk-Forward Backtest Page
 * 
 * This example shows how to integrate the new StrategySelectionPanel
 * and SymbolSearch components into the existing WalkForwardBacktest page.
 * 
 * Replace the relevant sections in pages/WalkForwardBacktest.tsx with this code.
 */

import React, { useState, useEffect } from 'react';
import StrategySelectionPanel from '../components/StrategySelectionPanel';
import SymbolSearch from '../components/SymbolSearch';
import { Play, Settings2, BarChart2 } from 'lucide-react';

// Add these type definitions at the top of WalkForwardBacktest.tsx
interface StrategyParameter {
    type: string;
    default: any;
    min?: number;
    max?: number;
    description: string;
}

interface StrategyInfo {
    name: string;
    display_name: string;
    category: string;
    description: string;
    parameters: Record<string, StrategyParameter>;
    time_horizon: string;
    tier?: string;
    is_implemented: boolean;
}

// Add these state variables to the main component
const EnhancedWalkForwardBacktest: React.FC = () => {
    // Existing state...
    const [timeframe, setTimeframe] = useState('1D');
    const [capital, setCapital] = useState(100000);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<any | null>(null);

    // NEW: Enhanced symbol and strategy selection
    const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
    const [selectedStrategies, setSelectedStrategies] = useState<StrategyInfo[]>([]);

    // Walk-forward config
    const [wfConfig, setWfConfig] = useState({
        train_window: 252,
        test_window: 63,
        step_size: 21,
        anchored: false
    });

    // Run backtest with enhanced parameters
    const runBacktest = async () => {
        // Validation
        if (selectedSymbols.length === 0) {
            setError('Please select at least one symbol');
            return;
        }

        if (selectedStrategies.length === 0) {
            setError('Please select at least one strategy');
            return;
        }

        setLoading(true);
        setError(null);
        setResult(null);

        try {
            // Use the first selected strategy (multi-strategy support can be added later)
            const primaryStrategy = selectedStrategies[0];

            const requestBody = {
                symbols: selectedSymbols,
                exchange: 'NSE',
                strategy_type: 'RULE_BASED',  // Based on selected strategy
                strategy_name: primaryStrategy.name,  // e.g., 'macd_crossover'
                timeframe,
                trade_style: timeframe.includes('m') || timeframe.includes('h') ? 'INTRADAY' : 'SWING',
                walk_forward: wfConfig,
                capital,
                ml_model: 'NONE'
            };

            console.log('[Enhanced Backtest] Request:', requestBody);

            const response = await fetch('http://localhost:8000/api/v1/walk-forward', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();
            setResult(data);

            console.log('[Enhanced Backtest] Success:', data);
        } catch (err: any) {
            console.error('[Enhanced Backtest] Error:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6 p-6">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white">
                        <Play size={24} />
                    </div>
                    Enhanced Walk-Forward Backtest
                </h1>
                <p className="text-slate-500 dark:text-slate-400 mt-1">
                    Production-ready strategy testing with tier-based organization
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Configuration Panel */}
                <div className="lg:col-span-1 space-y-4">
                    {/* REPLACE EXISTING SYMBOL SELECTION WITH: */}
                    <div className="bg-white dark:bg-slate-800 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-700">
                        <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                            <BarChart2 size={18} />
                            Symbol Selection
                        </h3>
                        <SymbolSearch
                            selectedSymbols={selectedSymbols}
                            onSymbolsChange={setSelectedSymbols}
                            timeframe={timeframe}
                            maxSymbols={5}
                        />
                    </div>

                    {/* Timeframe Selection */}
                    <div className="bg-white dark:bg-slate-800 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-700">
                        <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                            <Settings2 size={18} />
                            Configuration
                        </h3>
                        <div className="space-y-3">
                            <div>
                                <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">
                                    Timeframe
                                </label>
                                <select
                                    value={timeframe}
                                    onChange={e => setTimeframe(e.target.value)}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
                                >
                                    <option value="1D">Daily</option>
                                    <option value="15m">15 Minutes</option>
                                    <option value="30m">30 Minutes</option>
                                    <option value="1h">1 Hour</option>
                                    <option value="5m">5 Minutes</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">
                                    Initial Capital
                                </label>
                                <input
                                    type="number"
                                    value={capital}
                                    onChange={e => setCapital(Number(e.target.value))}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white text-sm"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Run Button */}
                    <button
                        onClick={runBacktest}
                        disabled={loading || selectedSymbols.length === 0 || selectedStrategies.length === 0}
                        className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl font-medium hover:from-indigo-700 hover:to-purple-700 transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading ? (
                            <>
                                <RefreshCw className="animate-spin" size={20} />
                                Running Backtest...
                            </>
                        ) : (
                            <>
                                <Play size={20} />
                                Run Backtest
                            </>
                        )}
                    </button>

                    {/* Error Display */}
                    {error && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                            <p className="text-red-700 text-sm">{error}</p>
                        </div>
                    )}
                </div>

                {/* REPLACE EXISTING STRATEGY SELECTION WITH: */}
                <div className="lg:col-span-2">
                    <div className="bg-white dark:bg-slate-800 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-700">
                        <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
                            Strategy Selection
                        </h3>
                        <StrategySelectionPanel
                            selectedStrategies={selectedStrategies}
                            onSelectionChange={setSelectedStrategies}
                        />
                    </div>
                </div>
            </div>

            {/* Results Section - Keep existing results display */}
            {result && (
                <div className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
                    <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
                        Backtest Results
                    </h3>
                    {/* Your existing results rendering code here */}
                    <pre className="text-xs overflow-auto">
                        {JSON.stringify(result, null, 2)}
                    </pre>
                </div>
            )}
        </div>
    );
};

export default EnhancedWalkForwardBacktest;

/**
 * MIGRATION STEPS:
 * 
 * 1. Import the new components at the top of WalkForwardBacktest.tsx:
 *    import StrategySelectionPanel from '../components/StrategySelectionPanel';
 *    import SymbolSearch from '../components/SymbolSearch';
 * 
 * 2. Add the type interfaces (StrategyParameter, StrategyInfo)
 * 
 * 3. Add the new state variables:
 *    const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
 *    const [selectedStrategies, setSelectedStrategies] = useState<StrategyInfo[]>([]);
 * 
 * 4. Replace the symbol selection section with <SymbolSearch />
 * 
 * 5. Replace the strategy selection dropdown with <StrategySelectionPanel />
 * 
 * 6. Update the runBacktest function to use:
 *    - symbols: selectedSymbols
 *    - strategy_name: selectedStrategies[0]?.name
 * 
 * 7. Test the integration:
 *    - Verify symbols load and search works
 *    - Verify strategies group by tier
 *    - Verify backtest runs successfully
 */
