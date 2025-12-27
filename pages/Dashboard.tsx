import React, { useState, useEffect } from 'react';
import AgenticBotCard from '../components/AgenticBotCard';
import { Page, Stock, AlgoConfig } from '../types';
import { ArrowUpRight, ArrowDownRight, Zap, Play, Clock, TrendingUp, DollarSign, Activity, X, Loader2 } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';
import { api } from '../services/api';
import TopMoversCard from '../components/TopMoversCard';

interface DashboardProps {
   onNavigate: (page: Page) => void;
}

const mockData = [
   { name: '9:30', val: 4000 },
   { name: '10:30', val: 3000 },
   { name: '11:30', val: 5000 },
   { name: '12:30', val: 2780 },
   { name: '13:30', val: 1890 },
   { name: '14:30', val: 2390 },
   { name: '15:30', val: 3490 },
];

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
               // Only update if we got valid data with actual values
               const hasData = response.some((idx: any) => idx.value && idx.value > 0);
               if (hasData) {
                  setIndices(response);
               }
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
            ws = new WebSocket('ws://localhost:8000/api/scanner/ws/scanner');

            ws.onopen = () => {
               console.log('Dashboard WS connected');
               // DON'T stop REST polling - keep it as reliable backup
            };

            ws.onmessage = (event) => {
               try {
                  const message = JSON.parse(event.data);
                  // Only update if WS sends valid indices data
                  if (message.indices && Array.isArray(message.indices) && isSubscribed) {
                     const hasData = message.indices.some((idx: any) => idx.value && idx.value > 0);
                     if (hasData) {
                        setIndices(message.indices);
                     }
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

      return () => {
         isSubscribed = false;
         if (ws) ws.close();
         if (pollInterval) clearInterval(pollInterval);
      };
   }, []);




   // Dynamic greeting based on time of day
   const getGreeting = () => {
      const hour = new Date().getHours();
      if (hour < 12) return 'Good Morning';
      if (hour < 17) return 'Good Afternoon';
      return 'Good Evening';
   };

   // Modal and loading state for all AI scanners
   const [showScanModal, setShowScanModal] = useState(false);
   const [scanLoading, setScanLoading] = useState(false);
   const [scanResults, setScanResults] = useState<any>(null);
   const [scanError, setScanError] = useState<string | null>(null);
   const [currentScan, setCurrentScan] = useState<{ name: string, endpoint: string, algoId?: string } | null>(null);

   const toggleAlgorithm = (id: string) => {
      setAlgorithms(prev =>
         prev.map(algo =>
            algo.id === id ? { ...algo, active: !algo.active } : algo
         )
      );
   };

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

   const handleAlgorithmClick = async (algo: AlgoConfig) => {
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
         try {
            // Get token if available (optional - scanners work without auth now)
            const token = localStorage.getItem('access_token');
            const headers: Record<string, string> = {};
            if (token) {
               headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(`http://localhost:8000${endpoint}`, { headers });
            if (!response.ok) {
               const errorData = await response.json().catch(() => ({}));
               throw new Error(errorData.detail || `Server error: ${response.status}`);
            }
            const data = await response.json();
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
   };

   // Handle modal close - set algorithm back to IDLE
   const handleCloseModal = () => {
      if (currentScan?.algoId) {
         setAlgorithms(prev =>
            prev.map(a => a.id === currentScan.algoId ? { ...a, active: false } : a)
         );
      }
      setShowScanModal(false);
      setCurrentScan(null);
   };

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
                     const isPositive = idx.change >= 0;
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
                                          {isPositive ? '+' : ''}{idx.percent}%
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

         <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Scanners List */}
            <div className="lg:col-span-2 space-y-4">
               <div className="flex items-center justify-between">
                  <h3 className="font-bold text-lg text-slate-800 dark:text-white">AI Trading Engines</h3>
                  <button onClick={() => onNavigate(Page.ALGO_BUILDER)} className="text-brand-600 text-sm font-medium hover:underline">View All</button>
               </div>

               <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {algorithms.map(algo => (
                     <div key={algo.id} className="bg-white dark:bg-slate-800 p-5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-all cursor-pointer"
                        onClick={() => handleAlgorithmClick(algo)}>
                        <div className="flex justify-between items-start mb-3">
                           <div className={`p-2 rounded-lg ${algo.active ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'}`}>
                              <Zap size={18} />
                           </div>
                           <span className={`text-xs font-bold px-2 py-1 rounded-full ${algo.active ? 'bg-green-50 text-green-600 border border-green-100' : 'bg-slate-100 text-slate-500'}`}>
                              {algo.active ? 'RUNNING' : 'IDLE'}
                           </span>
                        </div>
                        <h4 className="font-bold text-slate-900 dark:text-white mb-1">{algo.name}</h4>
                        <p className="text-xs text-slate-500 dark:text-slate-400 h-10">{algo.description}</p>

                        <div className="mt-4 flex items-center justify-between pt-4 border-t border-slate-100 dark:border-slate-700">
                           <div>
                              <span className="text-xs text-slate-400 block">Performance</span>
                              <span className={`text-sm font-bold ${algo.performance === null ? 'text-slate-400' : algo.performance >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                 {algo.performance === null ? '–' : `${algo.performance > 0 ? '+' : ''}${algo.performance}%`}
                              </span>
                           </div>
                           <div className={`p-2 rounded-full transition-all ${algo.active ? 'bg-green-100 dark:bg-green-900/30' : 'bg-slate-100 dark:bg-slate-700'}`}>
                              <Play size={16} className={`${algo.active ? 'text-green-600 dark:text-green-400' : 'text-slate-600 dark:text-slate-300'}`} fill="currentColor" />
                           </div>
                        </div>
                     </div>
                  ))}
               </div>
            </div>

            {/* Equity Curve */}
            <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
               <div className="flex justify-between items-center mb-4">
                  <h3 className="font-bold text-slate-800 dark:text-white">Equity Curve</h3>
                  <select className="text-xs bg-slate-100 dark:bg-slate-700 rounded p-1 border-none outline-none">
                     <option>Intraday</option>
                     <option>Week</option>
                  </select>
               </div>
               <div className="h-40 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                     <LineChart data={mockData}>
                        <Tooltip
                           contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                           cursor={{ stroke: '#cbd5e1' }}
                        />
                        <Line type="monotone" dataKey="val" stroke="#0ea5e9" strokeWidth={2} dot={false} />
                     </LineChart>
                  </ResponsiveContainer>
               </div>
            </div>
         </div>

         {/* AI Scanner Modal */}
         {showScanModal && currentScan && (

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
         )}
      </div>
   );

};

export default Dashboard;