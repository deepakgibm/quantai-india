import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Terminal, PlayCircle, AlertTriangle, RefreshCw, TrendingUp, ChevronDown, Search, Clock, Target, Shield, Zap } from 'lucide-react';

// Expert Trading Prompts
const EXPERT_PROMPTS = [
   {
      id: 'momentum',
      name: '🚀 Short-Term Momentum Buy (1–3 Days)',
      icon: Zap,
      category: 'Momentum',
      prompt: `Identify NSE stocks showing strong short-term momentum for the next 1–3 trading days.
Filter for high volume breakout, bullish candle confirmation, RSI between 55–70, and price above 20-EMA.
Provide entry price, stop loss, target, and confidence score.`,
      description: 'Momentum-based positional trades'
   },
   {
      id: 'intraday',
      name: '📈 Intraday Day Trading Buy (Today Only)',
      icon: Clock,
      category: 'Day Trade',
      prompt: `Scan NSE stocks suitable for intraday long trades today.
Focus on stocks with pre-market strength, VWAP support, high relative volume, and bullish 5-minute structure.
Provide precise buy level, intraday stop loss, target, and volatility risk.`,
      description: 'Day trading during market hours (9:15–3:15)'
   },
   {
      id: 'weekly',
      name: '📊 Weekly Swing Trade Buy (5–7 Days)',
      icon: TrendingUp,
      category: 'Swing Trade',
      prompt: `Find stocks suitable for weekly swing trading with a holding period of 5–7 days.
Look for consolidation breakout, higher-high higher-low structure, rising volume, and sector strength.
Include entry zone, stop loss, target range, and trend strength score.`,
      description: 'Swing trading with controlled risk'
   },
   {
      id: 'lowrisk',
      name: '🛡️ Low-Risk High-Probability Setup',
      icon: Shield,
      category: 'Conservative',
      prompt: `Identify low-risk, high-probability buy setups in NSE stocks.
Focus on pullbacks to moving averages, strong support zones, bullish reversal patterns, and favorable risk-reward (≥ 1:2).
Provide trade rationale and risk score.`,
      description: 'Capital preservation and consistency'
   },
   {
      id: 'topranked',
      name: '🏆 AI-Ranked Top Buy Picks (Today)',
      icon: Target,
      category: 'AI Picks',
      prompt: `Analyze all NSE stocks and rank the top buy opportunities for today using AI-weighted scoring.
Consider trend strength, momentum, volume surge, sentiment signals, and volatility.
Output the top 5 stocks with rank, reason to buy, entry, stop loss, and target.`,
      description: 'Automated decision support'
   }
];

const AIPrompt: React.FC = () => {
   const [input, setInput] = useState('');
   const [isAnalyzing, setIsAnalyzing] = useState(false);
   const [results, setResults] = useState<any[] | null>(null);
   const [error, setError] = useState<string | null>(null);

   // Dropdown state
   const [isDropdownOpen, setIsDropdownOpen] = useState(false);
   const [selectedPrompt, setSelectedPrompt] = useState<typeof EXPERT_PROMPTS[0] | null>(null);
   const [searchFilter, setSearchFilter] = useState('');
   const dropdownRef = useRef<HTMLDivElement>(null);

   // Close dropdown when clicking outside
   useEffect(() => {
      const handleClickOutside = (event: MouseEvent) => {
         if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
            setIsDropdownOpen(false);
         }
      };
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
   }, []);

   // Filter prompts based on search
   const filteredPrompts = EXPERT_PROMPTS.filter(p =>
      p.name.toLowerCase().includes(searchFilter.toLowerCase()) ||
      p.category.toLowerCase().includes(searchFilter.toLowerCase()) ||
      p.description.toLowerCase().includes(searchFilter.toLowerCase())
   );

   const handleSelectPrompt = (prompt: typeof EXPERT_PROMPTS[0]) => {
      setSelectedPrompt(prompt);
      setInput(prompt.prompt);
      setIsDropdownOpen(false);
      setSearchFilter('');
   };

   const handleRun = async () => {
      if (!input.trim()) return;
      setIsAnalyzing(true);
      setResults(null);
      setError(null);

      try {
         const token = localStorage.getItem('access_token');

         const response = await fetch('http://localhost:8000/api/ai/prompt', {
            method: 'POST',
            headers: {
               'Content-Type': 'application/json',
               'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
               prompt: input,
               prompt_type: selectedPrompt?.id || 'custom'
            })
         });

         if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            if (response.status === 401) {
               throw new Error("Session expired. Please log in again.");
            } else if (response.status === 429) {
               throw new Error("AI rate limit exceeded. Please wait a minute and try again.");
            } else if (response.status === 500) {
               const detail = errorData?.detail || "AI processing error";
               throw new Error(`Server error: ${detail}`);
            }
            throw new Error(errorData?.detail || `API error: ${response.status}`);
         }

         const data = await response.json();

         if (data.suggested_stocks && Array.isArray(data.suggested_stocks) && data.suggested_stocks.length > 0) {
            setResults(data.suggested_stocks);
         } else if (data.response) {
            try {
               const cleanText = data.response.trim().replace(/^```json\s*/, '').replace(/```$/, '');
               const parsedData = JSON.parse(cleanText);

               if (Array.isArray(parsedData)) {
                  setResults(parsedData);
               } else {
                  setResults([parsedData]);
               }
            } catch (parseError) {
               setResults([{
                  symbol: "SCAN RESULT",
                  action: "WAIT",
                  confidence: 75,
                  reason: data.response.substring(0, 200),
                  price: 0
               }]);
            }
         } else {
            throw new Error("No response from AI");
         }

      } catch (err: any) {
         console.error("AI Execution Error:", err);
         setError(err.message || "Unable to connect to the AI Strategy Engine. Please ensure the backend is running.");
      } finally {
         setIsAnalyzing(false);
      }
   };

   return (
      <div className="h-full flex flex-col gap-6">
         <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-700 flex-shrink-0">
            <div className="flex items-center gap-2 mb-4">
               <div className="p-2 bg-brand-100 dark:bg-brand-900/30 rounded-lg text-brand-600 dark:text-brand-400">
                  <TrendingUp size={20} />
               </div>
               <div>
                  <h2 className="text-lg font-bold text-slate-800 dark:text-white">AI Stock Scanner Pro</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Powered by Gemini 2.5 Flash • NSE Cash Segment</p>
               </div>
            </div>

            {/* Expert Prompt Dropdown */}
            <div className="mb-4" ref={dropdownRef}>
               <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">
                  Select Trading Strategy
               </label>
               <div className="relative">
                  <button
                     onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                     className="w-full flex items-center justify-between p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-left hover:border-brand-500 transition-colors"
                  >
                     <div className="flex items-center gap-3">
                        {selectedPrompt ? (
                           <>
                              <selectedPrompt.icon size={20} className="text-brand-500" />
                              <div>
                                 <p className="font-medium text-slate-800 dark:text-white">{selectedPrompt.name}</p>
                                 <p className="text-xs text-slate-500">{selectedPrompt.description}</p>
                              </div>
                           </>
                        ) : (
                           <>
                              <Sparkles size={20} className="text-slate-400" />
                              <span className="text-slate-500">Choose an expert trading prompt...</span>
                           </>
                        )}
                     </div>
                     <ChevronDown size={20} className={`text-slate-400 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {/* Dropdown Panel */}
                  {isDropdownOpen && (
                     <div className="absolute z-50 w-full mt-2 bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                        {/* Search Input */}
                        <div className="p-3 border-b border-slate-100 dark:border-slate-700">
                           <div className="relative">
                              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                              <input
                                 type="text"
                                 value={searchFilter}
                                 onChange={(e) => setSearchFilter(e.target.value)}
                                 placeholder="Search strategies..."
                                 className="w-full pl-10 pr-4 py-2.5 bg-slate-50 dark:bg-slate-900 rounded-lg border-none outline-none text-sm text-slate-800 dark:text-slate-200 placeholder-slate-400"
                                 autoFocus
                              />
                           </div>
                        </div>

                        {/* Prompt Options */}
                        <div className="max-h-80 overflow-y-auto">
                           {filteredPrompts.length > 0 ? (
                              filteredPrompts.map((prompt) => (
                                 <button
                                    key={prompt.id}
                                    onClick={() => handleSelectPrompt(prompt)}
                                    className={`w-full flex items-start gap-3 p-4 text-left hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors border-b border-slate-100 dark:border-slate-700 last:border-b-0 ${selectedPrompt?.id === prompt.id ? 'bg-brand-50 dark:bg-brand-900/20' : ''
                                       }`}
                                 >
                                    <div className={`p-2 rounded-lg ${selectedPrompt?.id === prompt.id ? 'bg-brand-100 dark:bg-brand-900/30 text-brand-600' : 'bg-slate-100 dark:bg-slate-700 text-slate-500'}`}>
                                       <prompt.icon size={18} />
                                    </div>
                                    <div className="flex-1">
                                       <p className="font-medium text-slate-800 dark:text-white text-sm">{prompt.name}</p>
                                       <p className="text-xs text-slate-500 mt-0.5">{prompt.description}</p>
                                       <span className="inline-block mt-2 text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400">
                                          {prompt.category}
                                       </span>
                                    </div>
                                 </button>
                              ))
                           ) : (
                              <div className="p-8 text-center text-slate-400">
                                 <Search size={24} className="mx-auto mb-2 opacity-50" />
                                 <p className="text-sm">No strategies found</p>
                              </div>
                           )}
                        </div>
                     </div>
                  )}
               </div>
            </div>

            {/* Custom Prompt Input */}
            <div className="relative group">
               <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-2">
                  Prompt <span className="text-slate-400 font-normal">(Edit or write your own)</span>
               </label>
               <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Select a strategy above or type your custom prompt here...

Example: 'Find 3 breakout stocks in Nifty Auto sector with high volume and RSI above 60'"
                  className="w-full h-32 p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 outline-none focus:ring-2 focus:ring-brand-500 resize-none text-slate-800 dark:text-slate-200 font-mono text-sm transition-all focus:bg-white dark:focus:bg-slate-900"
               />
               <div className="absolute bottom-4 right-4 flex gap-2">
                  <button
                     onClick={handleRun}
                     disabled={isAnalyzing || !input.trim()}
                     className={`bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-xl font-medium flex items-center gap-2 transition-all shadow-lg shadow-brand-500/20 ${isAnalyzing || !input.trim() ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'}`}
                  >
                     {isAnalyzing ? (
                        <><RefreshCw size={18} className="animate-spin" /> Scanning Market...</>
                     ) : (
                        <><Send size={18} /> Run Scan</>
                     )}
                  </button>
               </div>
            </div>
         </div>

         {/* Results Area */}
         <div className="flex-1 bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-4">
               <h3 className="font-bold text-slate-700 dark:text-slate-300 flex items-center gap-2">
                  <Terminal size={18} /> Live Signal Console
               </h3>
               {results && (
                  <span className="flex items-center gap-1 text-xs font-medium text-green-600 bg-green-50 dark:bg-green-900/20 px-2.5 py-1 rounded-full border border-green-100 dark:border-green-900/50">
                     <Sparkles size={12} /> {results.length} Signals Found
                  </span>
               )}
            </div>

            <div className="flex-1 overflow-y-auto space-y-4 pr-2 scrollbar-thin scrollbar-thumb-slate-200 dark:scrollbar-thumb-slate-700">
               {!results && !isAnalyzing && !error && (
                  <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-4">
                     <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center">
                        <Sparkles size={32} className="opacity-30" />
                     </div>
                     <div className="text-center">
                        <p className="text-sm font-medium mb-2">Select a trading strategy to start scanning</p>
                        <p className="text-xs opacity-75">NSE Cash Segment • Real-time Analysis • AI-Powered</p>
                     </div>
                  </div>
               )}

               {error && (
                  <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-900/50 rounded-xl text-red-600 dark:text-red-400 flex items-start gap-3">
                     <AlertTriangle size={20} className="mt-0.5 flex-shrink-0" />
                     <div>
                        <p className="text-sm font-bold">Scan Failed</p>
                        <p className="text-sm opacity-90">{error}</p>
                     </div>
                  </div>
               )}

               {isAnalyzing && (
                  <div className="space-y-4">
                     {[1, 2, 3].map((i) => (
                        <div key={i} className="p-4 rounded-xl border border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30 animate-pulse flex gap-4">
                           <div className="w-16 h-16 rounded-lg bg-slate-200 dark:bg-slate-700 flex-shrink-0"></div>
                           <div className="flex-1 space-y-2">
                              <div className="h-4 w-1/3 bg-slate-200 dark:bg-slate-700 rounded"></div>
                              <div className="h-3 w-1/4 bg-slate-200 dark:bg-slate-700 rounded"></div>
                              <div className="h-3 w-full bg-slate-200 dark:bg-slate-700 rounded"></div>
                           </div>
                        </div>
                     ))}
                  </div>
               )}

               {results?.map((res, idx) => (
                  <div key={idx} className="p-5 rounded-xl border border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 hover:bg-white dark:hover:bg-slate-800 hover:shadow-md transition-all duration-200 group">
                     <div className="flex flex-col lg:flex-row items-start gap-5">
                        {/* Action Badge */}
                        <div className={`flex-shrink-0 w-full lg:w-20 h-20 rounded-xl flex flex-col items-center justify-center font-black text-white shadow-lg ${res.action === 'BUY' ? 'bg-gradient-to-br from-green-400 to-green-600 shadow-green-500/20' :
                           res.action === 'SELL' ? 'bg-gradient-to-br from-red-400 to-red-600 shadow-red-500/20' :
                              'bg-gradient-to-br from-yellow-400 to-yellow-600 shadow-yellow-500/20'
                           }`}>
                           <span className="text-lg">{res.action}</span>
                           {res.trade_type && <span className="text-xs opacity-75 font-medium">{res.trade_type}</span>}
                        </div>

                        {/* Stock Info */}
                        <div className="flex-1 min-w-0 w-full">
                           <div className="flex justify-between items-start mb-3">
                              <div>
                                 <h4 className="font-bold text-xl text-slate-900 dark:text-white tracking-tight">{res.symbol}</h4>
                                 {res.name && <p className="text-sm text-slate-500">{res.name}</p>}
                              </div>
                              <div className="flex items-center gap-3">
                                 {res.risk_reward && (
                                    <div className="text-center">
                                       <span className="text-xs text-slate-400 block">R:R</span>
                                       <span className="text-sm font-bold text-brand-600">{res.risk_reward}</span>
                                    </div>
                                 )}
                                 <div className="text-center">
                                    <span className="text-xs text-slate-400 block">Confidence</span>
                                    <div className={`px-2.5 py-1 rounded-md text-sm font-bold text-white ${res.confidence >= 80 ? 'bg-green-500' :
                                       res.confidence >= 60 ? 'bg-blue-500' :
                                          res.confidence >= 40 ? 'bg-yellow-500' : 'bg-slate-400'
                                       }`}>
                                       {res.confidence}%
                                    </div>
                                 </div>
                              </div>
                           </div>

                           {/* Trade Levels Grid */}
                           <div className="grid grid-cols-4 gap-2 mb-3">
                              <div className="bg-white dark:bg-slate-800 p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-center">
                                 <p className="text-xs text-slate-400 mb-0.5">Current</p>
                                 <p className="font-bold text-slate-900 dark:text-white">₹{res.price?.toLocaleString() || res.current_price?.toLocaleString() || 'N/A'}</p>
                              </div>
                              <div className="bg-white dark:bg-slate-800 p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-center">
                                 <p className="text-xs text-slate-400 mb-0.5">Entry</p>
                                 <p className="font-bold text-blue-600">₹{res.entry_price?.toLocaleString() || res.entry?.toLocaleString() || 'N/A'}</p>
                              </div>
                              <div className="bg-white dark:bg-slate-800 p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-center">
                                 <p className="text-xs text-slate-400 mb-0.5">Target</p>
                                 <p className="font-bold text-green-600">₹{res.target_price?.toLocaleString() || res.target?.toLocaleString() || 'N/A'}</p>
                              </div>
                              <div className="bg-white dark:bg-slate-800 p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-center">
                                 <p className="text-xs text-slate-400 mb-0.5">Stop Loss</p>
                                 <p className="font-bold text-red-600">₹{res.stop_loss?.toLocaleString() || 'N/A'}</p>
                              </div>
                           </div>

                           {/* Reason */}
                           <div className="p-3 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">AI Analysis</span>
                              {res.reason || res.key_reason}
                           </div>
                        </div>

                        {/* Execute Button */}
                        <div className="w-full lg:w-auto self-center">
                           {res.action !== 'WAIT' && (
                              <button className="w-full lg:w-auto px-6 py-3 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl font-bold hover:opacity-90 transition-opacity flex items-center justify-center gap-2 shadow-lg">
                                 <PlayCircle size={18} /> Execute
                              </button>
                           )}
                        </div>
                     </div>
                  </div>
               ))}
            </div>
         </div>
      </div>
   );
};

export default AIPrompt;