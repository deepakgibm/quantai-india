import React, { useState, useEffect, useMemo, useCallback, memo } from 'react';
import AgenticBotCard from '../components/AgenticBotCard';
import { Page, Stock, AlgoConfig } from '../types';
import { Zap, X, Loader2, Play } from 'lucide-react';

import { api } from '../services/api';
import TopMoversCard from '../components/TopMoversCard';

interface DashboardProps {
   onNavigate: (page: Page) => void;
}


const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
   const [prompt, setPrompt] = useState('');
   const [algorithms, setAlgorithms] = useState<AlgoConfig[]>([
      { id: '1', name: 'Trend Finder AI', description: 'Identifies strong trend continuation setups', active: false, performance: null },
      { id: '2', name: 'Breakout Detector', description: 'Catches volume-backed breakouts in real-time', active: false, performance: null },
      { id: '3', name: 'Top 10 Buy/Sell', description: 'Auto-picks top 10 BUY and SELL signals', active: false, performance: null },
      { id: '4', name: 'Momentum Scanner', description: 'Finds stocks with strong price momentum (ROC, MFI)', active: false, performance: null },
      { id: '5', name: 'Mean Reversion', description: 'Identifies oversold/overbought stocks for reversal plays', active: false, performance: null },
      { id: '6', name: 'Gap Scanner', description: 'Detects overnight gaps with follow-through potential', active: false, performance: null },
      { id: '7', name: 'Relative Strength', description: 'Finds stocks outperforming the market/sector', active: false, performance: null },
      { id: '8', name: 'VWAP Trading', description: 'Identifies stocks trading above/below VWAP with volume', active: false, performance: null },
      { id: '9', name: 'S/R Bounces', description: 'Detects price bouncing off key support/resistance levels', active: false, performance: null },
   ]);

   const [indices, setIndices] = useState([
      { name: 'NIFTY 50', value: 0, change: 0, percent: 0, loading: true },
      { name: 'BANK NIFTY', value: 0, change: 0, percent: 0, loading: true },
      { name: 'INDIA VIX', value: 0, change: 0, percent: 0, loading: true },
   ]);


   // Real-time Indices WebSocket & Polling
   useEffect(() => {
      let ws: WebSocket | null = null;
      let pollInterval: NodeJS.Timeout | null = null;
      let isSubscribed = true;

      const fetchIndices = async () => {
         try {
            const response = await api.getMarketIndices();
            if (response && isSubscribed && Array.isArray(response)) {
               // Improved merging logic: Only update if we have valid data, 
               // and merge with existing state to prevent flickering
               setIndices(prev => {
                  return response.map((newIdx: any) => {
                     const existing = prev.find(p => p.name === newIdx.name);
                     // If new value is 0 or null, keep existing value to prevent disappearance
                     if (!newIdx.value || newIdx.value === 0) {
                        return existing || newIdx;
                     }
                     return newIdx;
                  });
               });
            }
         } catch (e) {
            console.error('Failed to poll indices:', e);
         }
      };

      const startPolling = () => {
         if (pollInterval) return; // Already polling
         fetchIndices(); // Fetch immediately
         pollInterval = setInterval(fetchIndices, 10000); // Poll every 10 seconds (reduced frequency)
      };

      const connectWS = () => {
         try {
            ws = new WebSocket('ws://127.0.0.1:8000/api/scanner/ws/scanner');

            ws.onopen = () => {
               console.log('Dashboard WS connected');
               // DON'T stop REST polling - keep it as reliable backup
            };

            ws.onmessage = (event) => {
               try {
                  const message = JSON.parse(event.data);
                  // Only update if WS sends valid indices data
                  // Improved merging logic for WebSocket updates
                  if (message.indices && Array.isArray(message.indices) && isSubscribed) {
                     setIndices(prev => {
                        return message.indices.map((newIdx: any) => {
                           const existing = prev.find(p => p.name === newIdx.name);
                           // If new value is 0/null/undefined, preserve existing valid value
                           if (!newIdx.value || newIdx.value === 0) {
                              return existing || newIdx;
                           }
                           return newIdx;
                        });
                     });
                  }
               } catch (e) {
                  // Silently ignore parse errors - REST will handle data
               }
            };

            ws.onerror = () => {
               console.warn('Dashboard WS error, REST polling will handle data');
            };

            ws.onclose = () => {
               // WebSocket closed - REST polling continues
            };
         } catch (e) {
            console.warn('WS connection failed:', e);
         }
      };

      // Start REST polling immediately for reliable data
      startPolling();

      // Also try WebSocket for real-time updates (optional enhancement)
      connectWS();

      // Fetch engine performance once at startup
      const fetchEnginePerf = async () => {
         try {
            const data = await api.getEnginePerformance();
            if (data?.status === 'success' && data.engines) {
               setAlgorithms(prev => prev.map(algo => {
                  const perf = data.engines[algo.name];
                  if (perf) {
                     return {
                        ...algo,
                        // If it's not active, we still show the global performance/winrate from backend
                        performance: algo.performance || perf.performance,
                        winRate: perf.win_rate
                     };
                  }
                  return algo;
               }));
            }
         } catch (e) {
            console.warn("Failed to update engine performance from backend");
         }
      };

      fetchEnginePerf();

      return () => {
         isSubscribed = false;
         if (ws) ws.close();
         if (pollInterval) clearInterval(pollInterval);
      };
   }, []);




   // Memoized greeting based on time of day (only recalculates when window refocuses)
   const greeting = useMemo(() => {
      const hour = new Date().getHours();
      if (hour < 12) return 'Good Morning';
      if (hour < 17) return 'Good Afternoon';
      return 'Good Evening';
   }, []);

   // Modal and loading state for all AI scanners
   const [showScanModal, setShowScanModal] = useState(false);
   const [scanLoading, setScanLoading] = useState(false);
   const [scanResults, setScanResults] = useState<any>(null);
   const [scanError, setScanError] = useState<string | null>(null);
   const [currentScan, setCurrentScan] = useState<{ name: string, endpoint: string, algoId?: string } | null>(null);

   // Memoized callback to prevent re-renders
   const toggleAlgorithm = useCallback((id: string) => {
      setAlgorithms(prev =>
         prev.map(algo =>
            algo.id === id ? { ...algo, active: !algo.active } : algo
         )
      );
   }, []);

   // Map algorithm names to their API endpoints
   const algoEndpoints: Record<string, string> = {
      'Trend Finder AI': '/api/ai/trend-finder',
      'Breakout Detector': '/api/ai/breakout-detector',
      'Top 10 Buy/Sell': '/api/ai/top5-picks',
      'Momentum Scanner': '/api/ai/momentum-scanner',
      'Mean Reversion': '/api/ai/mean-reversion',
      'Gap Scanner': '/api/ai/gap-scanner',
      'Relative Strength': '/api/ai/relative-strength',
      'VWAP Trading': '/api/ai/vwap-scanner',
      'S/R Bounces': '/api/ai/sr-bounce'
   };

   // Memoized algorithm click handler
   const handleAlgorithmClick = useCallback(async (algo: AlgoConfig) => {
      const endpoint = algoEndpoints[algo.name];
      if (endpoint) {
         // Set algorithm to RUNNING state
         setAlgorithms(prev =>
            prev.map(a => a.id === algo.id ? { ...a, active: true } : a)
         );
         setCurrentScan({ name: algo.name, endpoint, algoId: algo.id });
         setShowScanModal(true);
         setScanLoading(true);
         setScanError(null);
         setScanResults(null);
         setScanError(null);
         setScanResults(null);
         try {
            const data = await api.runScanner(endpoint);
            setScanResults(data);

            // Calculate performance from scan results
            if (data?.stocks && data.stocks.length > 0) {
               let totalExpectedReturn = 0;
               let validStocks = 0;

               for (const stock of data.stocks) {
                  const currentPrice = stock.current_price || stock.price || 0;
                  const targetPrice = stock.target_price || stock.target_1 || 0;

                  if (currentPrice > 0 && targetPrice > 0) {
                     // Calculate expected return percentage
                     const expectedReturn = ((targetPrice - currentPrice) / currentPrice) * 100;
                     // For SELL actions, the return is inverted
                     const adjustedReturn = stock.action === 'SELL' ? -expectedReturn : expectedReturn;
                     totalExpectedReturn += adjustedReturn;
                     validStocks++;
                  }
               }

               // Calculate average expected return
               if (validStocks > 0) {
                  const avgReturn = totalExpectedReturn / validStocks;
                  // Update the algorithm's performance with calculated value
                  setAlgorithms(prev =>
                     prev.map(a => a.id === algo.id
                        ? { ...a, performance: Math.round(avgReturn * 10) / 10 }
                        : a
                     )
                  );
               }
            }
         } catch (err: any) {
            setScanError(err.message || 'Failed to load scan data');
         } finally {
            setScanLoading(false);
         }
      } else {
         toggleAlgorithm(algo.id);
      }
   }, [algoEndpoints, toggleAlgorithm]);

   // Memoized modal close handler
   const handleCloseModal = useCallback(() => {
      if (currentScan?.algoId) {
         setAlgorithms(prev =>
            prev.map(a => a.id === currentScan.algoId ? { ...a, active: false } : a)
         );
      }
      setShowScanModal(false);
      setCurrentScan(null);
   }, [currentScan]);

   // Remove hardcoded indices constant as it's now in state


   return (
      <div className="space-y-6">
         {/* Welcome & Stats Section */}
         <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* NIFTY 100 Top Movers */}
            <div className="col-span-1 lg:col-span-2">
               <TopMoversCard />
            </div>

            {/* Market Overview - Premium Light Design */}
            <div className="col-span-1 bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-700 flex flex-col">
               {/* Header */}
               <div className="flex items-center justify-between mb-5">
                  <div className="flex items-center gap-2">
                     <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                     <h3 className="font-bold text-slate-800 dark:text-white tracking-wide">Market Overview</h3>
                  </div>
                  <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                     {new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                  </span>
               </div>

               {/* Index Cards */}
               <div className="space-y-3 flex-1">
                  {indices.map((idx) => {
                     const isPositive = idx.percent >= 0;
                     const isVIX = idx.name === 'INDIA VIX';

                     return (
                        <div
                           key={idx.name}
                           className="relative overflow-hidden rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700/30 p-4 hover:border-slate-200 dark:hover:border-slate-600/50 hover:shadow-sm transition-all cursor-pointer group"
                        >
                           {/* Accent bar */}
                           <div className={`absolute left-0 top-0 bottom-0 w-1 ${isVIX
                              ? 'bg-amber-500'
                              : isPositive
                                 ? 'bg-green-500'
                                 : 'bg-red-500'
                              }`}></div>

                           <div className="flex items-center justify-between pl-3">
                              <div>
                                 <p className="text-xs text-slate-500 dark:text-slate-400 font-medium uppercase tracking-wider mb-1">
                                    {idx.name}
                                 </p>
                                 {idx.value === 0 ? (
                                    <div className="h-6 w-24 bg-slate-200 dark:bg-slate-700 rounded animate-pulse"></div>
                                 ) : (
                                    <p className="text-xl font-bold text-slate-900 dark:text-white font-mono">
                                       {idx.value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                                    </p>
                                 )}
                              </div>

                              <div className="text-right">
                                 {idx.value !== 0 && (
                                    <div className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg ${isVIX
                                       ? 'bg-amber-100 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400'
                                       : isPositive
                                          ? 'bg-green-100 dark:bg-green-500/10 text-green-600 dark:text-green-400'
                                          : 'bg-red-100 dark:bg-red-500/10 text-red-600 dark:text-red-400'
                                       }`}>
                                       {!isVIX && (
                                          <span className="text-xs">
                                             {isPositive ? '▲' : '▼'}
                                          </span>
                                       )}
                                       <span className="text-sm font-bold font-mono">
                                          {isPositive ? '+' : ''}{idx.percent.toFixed(2)}%
                                       </span>
                                    </div>
                                 )}
                              </div>
                           </div>
                        </div>
                     );
                  })}
               </div>
            </div>


         </div>

         {/* Agentic Bot Section */}
         <div className="mb-6">
            <AgenticBotCard />
         </div>

         {/* AI Trading Engines - Professional HFT Dashboard */}
         <div className="mt-6">
            <div className="flex items-center justify-between mb-4">
               <div className="flex items-center gap-3">
                  <h3 className="font-bold text-lg text-slate-800 dark:text-white">AI Trading Engines</h3>
                  <span className="text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-2 py-0.5 rounded-full">
                     {algorithms.filter(a => a.active).length} Active
                  </span>
               </div>

            </div>


            {/* 3-Column Responsive Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
               {algorithms.map((algo, index) => {
                  // Generate mock sparkline data for visual effect
                  const sparkData = Array.from({ length: 12 }, (_, i) => ({
                     v: algo.active ? 50 + Math.sin(i * 0.8 + index) * 30 + Math.random() * 10 : 50
                  }));

                  // Metrics from backend (via getEnginePerformance API)
                  const metrics = {
                     winRate: (algo as any).winRate || null,
                     dailyROI: algo.performance,
                     drawdown: (algo as any).drawdown || null,
                     signals: (algo as any).signals || 0
                  };

                  return (
                     <div
                        key={algo.id}
                        onClick={() => handleAlgorithmClick(algo)}
                        className={`
                           relative overflow-hidden rounded-xl p-4 cursor-pointer
                           transition-all duration-300 ease-out
                           hover:scale-[1.02] hover:shadow-xl
                           ${algo.active
                              ? 'bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 border border-emerald-500/30 shadow-lg shadow-emerald-500/10'
                              : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700'
                           }
                        `}
                     >
                        {/* Glassmorphism overlay for active */}
                        {algo.active && (
                           <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent pointer-events-none"></div>
                        )}

                        {/* Header Row */}
                        <div className="flex items-start justify-between mb-3 relative z-10">
                           <div className="flex items-center gap-2">
                              <div className={`p-2 rounded-lg ${algo.active
                                 ? 'bg-emerald-500/20 text-emerald-400'
                                 : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
                                 }`}>
                                 <Zap size={16} />
                              </div>
                              {algo.active && (
                                 <div className="flex items-center gap-1.5">
                                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                                    <span className="text-xs font-bold text-emerald-400 uppercase tracking-wide">Live</span>
                                 </div>
                              )}
                           </div>
                           <button
                              onClick={(e) => {
                                 e.stopPropagation();
                                 toggleAlgorithm(algo.id);
                              }}
                              className={`p-1.5 rounded-lg transition-all ${algo.active
                                 ? 'bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400'
                                 : 'bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-500'
                                 }`}
                           >
                              <Play size={14} fill="currentColor" />
                           </button>
                        </div>

                        {/* Title & Description */}
                        <h4 className={`font-bold text-sm mb-1 ${algo.active ? 'text-white' : 'text-slate-900 dark:text-white'}`}>
                           {algo.name}
                        </h4>
                        <p className={`text-xs mb-3 line-clamp-2 ${algo.active ? 'text-slate-400' : 'text-slate-500 dark:text-slate-400'}`}>
                           {algo.description}
                        </p>

                        {/* Sparkline */}
                        <div className="h-10 mb-3 relative">
                           <svg className="w-full h-full" viewBox="0 0 100 40" preserveAspectRatio="none">
                              <defs>
                                 <linearGradient id={`spark-grad-${algo.id}`} x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor={algo.active ? '#10b981' : '#64748b'} stopOpacity="0.3" />
                                    <stop offset="100%" stopColor={algo.active ? '#10b981' : '#64748b'} stopOpacity="0" />
                                 </linearGradient>
                              </defs>
                              <path
                                 d={`M 0 ${40 - sparkData[0].v * 0.4} ${sparkData.map((d, i) =>
                                    `L ${(i / (sparkData.length - 1)) * 100} ${40 - d.v * 0.4}`
                                 ).join(' ')} L 100 40 L 0 40 Z`}
                                 fill={`url(#spark-grad-${algo.id})`}
                              />
                              <path
                                 d={`M 0 ${40 - sparkData[0].v * 0.4} ${sparkData.map((d, i) =>
                                    `L ${(i / (sparkData.length - 1)) * 100} ${40 - d.v * 0.4}`
                                 ).join(' ')}`}
                                 fill="none"
                                 stroke={algo.active ? '#10b981' : '#64748b'}
                                 strokeWidth="1.5"
                              />
                           </svg>
                        </div>

                        {/* Metrics Grid */}
                        <div className={`grid grid-cols-3 gap-2 pt-3 border-t ${algo.active ? 'border-slate-700/50' : 'border-slate-100 dark:border-slate-700'
                           }`}>
                           <div>
                              <span className={`text-[10px] uppercase tracking-wide block ${algo.active ? 'text-slate-500' : 'text-slate-400'
                                 }`}>Win Rate</span>
                              <span className={`text-sm font-bold ${algo.active ? 'text-white' : 'text-slate-800 dark:text-slate-200'
                                 }`}>
                                 {metrics.winRate ? `${metrics.winRate}%` : '–'}
                              </span>
                           </div>
                           <div>
                              <span className={`text-[10px] uppercase tracking-wide block ${algo.active ? 'text-slate-500' : 'text-slate-400'
                                 }`}>Daily ROI</span>
                              <span className={`text-sm font-bold ${metrics.dailyROI === null
                                 ? 'text-slate-400'
                                 : metrics.dailyROI >= 0
                                    ? 'text-emerald-500'
                                    : 'text-rose-500'
                                 }`}>
                                 {metrics.dailyROI === null ? '–' : `${metrics.dailyROI > 0 ? '+' : ''}${metrics.dailyROI}%`}
                              </span>
                           </div>
                           <div>
                              <span className={`text-[10px] uppercase tracking-wide block ${algo.active ? 'text-slate-500' : 'text-slate-400'
                                 }`}>Drawdown</span>
                              <span className={`text-sm font-bold ${algo.active ? 'text-rose-400' : 'text-slate-400'
                                 }`}>
                                 {metrics.drawdown ? `${metrics.drawdown}%` : '–'}
                              </span>
                           </div>
                        </div>

                        {/* Signals badge for active */}
                        {algo.active && metrics.signals > 0 && (
                           <div className="absolute top-3 right-12 flex items-center gap-1 bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full">
                              <span className="text-[10px] font-bold">{metrics.signals} signals</span>
                           </div>
                        )}
                     </div>
                  );
               })}
            </div>
         </div>



         {/* AI Scanner Modal */}
         {
            showScanModal && currentScan && (

               <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                  <div className="bg-white dark:bg-slate-800 rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden shadow-2xl">
                     <div className="flex justify-between items-center p-6 border-b border-slate-200 dark:border-slate-700">
                        <div>
                           <h2 className="text-xl font-bold text-slate-900 dark:text-white">{currentScan.name}</h2>
                           <p className="text-sm text-slate-500 dark:text-slate-400">{scanResults?.description || 'Scanning...'}</p>
                        </div>
                        <button onClick={handleCloseModal} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg">
                           <X size={20} className="text-slate-500" />
                        </button>
                     </div>

                     <div className="p-6 overflow-y-auto max-h-[60vh]">
                        {scanLoading && (
                           <div className="flex flex-col items-center justify-center py-12">
                              <Loader2 size={40} className="text-brand-500 animate-spin mb-4" />
                              <p className="text-slate-500">Running {currentScan.name}...</p>
                           </div>
                        )}

                        {scanError && (
                           <div className="text-center py-8">
                              <p className="text-red-500 mb-4">{scanError}</p>
                              <button onClick={() => currentScan && handleAlgorithmClick(algorithms.find(a => a.name === currentScan.name) || algorithms[0])}
                                 className="px-4 py-2 bg-brand-500 text-white rounded-lg">Retry</button>
                           </div>
                        )}

                        {scanResults && !scanLoading && (
                           <div className="space-y-4">
                              {scanResults.stocks?.map((stock: any, idx: number) => (
                                 <div key={idx} className="bg-slate-50 dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                                    <div className="flex justify-between items-start mb-3">
                                       <div>
                                          <h3 className="font-bold text-lg text-slate-900 dark:text-white">{stock.symbol}</h3>
                                          <p className="text-sm text-slate-500">{stock.name}</p>
                                       </div>
                                       {/* Dynamic badge based on scan type */}
                                       {stock.trend && (
                                          <span className={`px-3 py-1 rounded-full text-xs font-bold ${stock.trend === 'BULLISH' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}>
                                             {stock.trend === 'BULLISH' ? '↑' : '↓'} {stock.trend}
                                          </span>
                                       )}
                                       {stock.action && (
                                          <span className={`px-3 py-1 rounded-full text-xs font-bold ${stock.action === 'BUY' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}>
                                             {stock.action}
                                          </span>
                                       )}
                                       {stock.breakout_type && (
                                          <span className="px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-600">
                                             {stock.breakout_type}
                                          </span>
                                       )}
                                       {stock.earnings_result && (
                                          <span className={`px-3 py-1 rounded-full text-xs font-bold ${stock.earnings_result === 'BEAT' ? 'bg-green-100 text-green-600' : stock.earnings_result === 'MISS' ? 'bg-red-100 text-red-600' : 'bg-yellow-100 text-yellow-600'}`}>
                                             {stock.earnings_result}
                                          </span>
                                       )}
                                    </div>

                                    {/* Strength/Confidence bar */}
                                    {(stock.strength || stock.confidence) && (
                                       <div className="mb-3">
                                          <div className="flex justify-between text-xs text-slate-500 mb-1">
                                             <span>{stock.strength ? 'Strength' : 'Confidence'}</span>
                                             <span>{stock.strength || stock.confidence}%</span>
                                          </div>
                                          <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full">
                                             <div className={`h-full rounded-full ${(stock.strength || stock.confidence) >= 70 ? 'bg-green-500' : (stock.strength || stock.confidence) >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                                style={{ width: `${stock.strength || stock.confidence}%` }} />
                                          </div>
                                       </div>
                                    )}

                                    {/* Volume ratio for breakouts */}
                                    {stock.volume_ratio && (
                                       <div className="mb-3 flex items-center gap-2">
                                          <span className="text-xs text-slate-500">Volume:</span>
                                          <span className="text-sm font-bold text-blue-600">{stock.volume_ratio}x avg</span>
                                       </div>
                                    )}

                                    {/* Price levels grid */}
                                    <div className="grid grid-cols-4 gap-2 text-center mb-3">
                                       <div className="bg-white dark:bg-slate-800 p-2 rounded-lg">
                                          <p className="text-xs text-slate-400">Current</p>
                                          <p className="font-bold text-slate-900 dark:text-white">₹{stock.current_price?.toLocaleString()}</p>
                                       </div>
                                       <div className="bg-white dark:bg-slate-800 p-2 rounded-lg">
                                          <p className="text-xs text-slate-400">{stock.entry_range ? 'Entry Range' : stock.breakout_level ? 'Breakout' : 'Entry'}</p>
                                          <p className="font-bold text-blue-600">{stock.entry_range || `₹${(stock.entry_price || stock.breakout_level)?.toLocaleString()}`}</p>
                                       </div>
                                       <div className="bg-white dark:bg-slate-800 p-2 rounded-lg">
                                          <p className="text-xs text-slate-400">{stock.target_1 ? 'Target 1' : 'Target'}</p>
                                          <p className="font-bold text-green-600">₹{(stock.target_1 || stock.target_price)?.toLocaleString()}</p>
                                       </div>
                                       <div className="bg-white dark:bg-slate-800 p-2 rounded-lg">
                                          <p className="text-xs text-slate-400">Stop Loss</p>
                                          <p className="font-bold text-red-600">₹{stock.stop_loss?.toLocaleString()}</p>
                                       </div>
                                    </div>

                                    {/* Extra info for specific scan types */}
                                    {stock.expected_move && (
                                       <p className="text-sm text-green-600 font-bold mb-2">Expected Move: {stock.expected_move}</p>
                                    )}
                                    {stock.earnings_surprise && (
                                       <p className="text-sm text-blue-600 font-bold mb-2">Earnings Surprise: {stock.earnings_surprise}</p>
                                    )}

                                    <p className="text-sm text-slate-600 dark:text-slate-400 italic">"{stock.reason}"</p>
                                 </div>
                              ))}
                           </div>
                        )}
                     </div>
                  </div>
               </div>
            )
         }
      </div >
   );

};

export default Dashboard;