import React, { useState, useEffect, useRef } from 'react';
import { 
  Sparkles, Send, Brain, ShieldAlert, Target, TrendingUp, RefreshCw, 
  Search, Play, AlertCircle, AlertTriangle, CheckCircle, HelpCircle, Layers, 
  ChevronDown, ChevronUp, User, PieChart, PlayCircle, BarChart3, Star, Clock
} from 'lucide-react';
import { getAuthHeaders, API_URL } from '../services/api';



interface SwarmEvent {
  type: string;
  agent_id?: string;
  task_id?: string;
  data?: any;
  timestamp?: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  thinking?: string;
  events?: any[];
}

const parseVerdictDetails = (text: string) => {
  if (!text) return null;
  
  const textClean = text.replace(/\*/g, '');
  
  let verdict = 'HOLD';
  if (/verdict:\s*(buy|strong buy)/i.test(textClean)) {
    verdict = 'BUY';
  } else if (/verdict:\s*(sell|strong sell)/i.test(textClean)) {
    verdict = 'SELL';
  } else if (/verdict:\s*hold/i.test(textClean)) {
    verdict = 'HOLD';
  } else if (/verdict\s*:\s*buy/i.test(textClean) || /decision\s*:\s*buy/i.test(textClean) || /recommendation\s*:\s*buy/i.test(textClean)) {
    verdict = 'BUY';
  }
  
  let confidence = '80%';
  const confMatch = textClean.match(/confidence\s*:\s*(\d+%?)/i);
  if (confMatch) {
    confidence = confMatch[1].endsWith('%') ? confMatch[1] : `${confMatch[1]}%`;
  }
  
  let targetPrice = '₹3,120';
  const targetMatch = textClean.match(/target\s*price\s*:\s*([^\n\r]+)/i) || textClean.match(/target\s*:\s*([^\n\r]+)/i);
  if (targetMatch) {
    targetPrice = targetMatch[1].trim();
  }
  
  let stopLoss = '₹2,860';
  const stopMatch = textClean.match(/stop\s*loss\s*:\s*([^\n\r]+)/i) || textClean.match(/stop\s*:\s*([^\n\r]+)/i);
  if (stopMatch) {
    stopLoss = stopMatch[1].trim();
  }
  
  let riskLevel = 'Medium';
  const riskMatch = textClean.match(/risk\s*profile\s*:\s*([^\n\r]+)/i) || textClean.match(/risk\s*:\s*([^\n\r]+)/i) || textClean.match(/risk\s*level\s*:\s*([^\n\r]+)/i);
  if (riskMatch) {
    riskLevel = riskMatch[1].trim();
  }

  let horizon = 'Swing';
  const horizonMatch = textClean.match(/horizon\s*:\s*([^\n\r]+)/i);
  if (horizonMatch) {
    horizon = horizonMatch[1].trim();
  }

  return { verdict, confidence, targetPrice, stopLoss, riskLevel, horizon };
};

export const VibeTrading: React.FC = () => {
  const [symbol, setSymbol] = useState('RELIANCE');
  const [searchTerm, setSearchTerm] = useState('RELIANCE');
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(false);

  const POPULAR_STOCKS = [
    { symbol: "RELIANCE", company_name: "Reliance Industries Ltd", sector: "Energy", index: "NIFTY 50" },
    { symbol: "TCS", company_name: "Tata Consultancy Services Ltd", sector: "Information Technology", index: "NIFTY 50" },
    { symbol: "HDFCBANK", company_name: "HDFC Bank Ltd", sector: "Financial Services", index: "NIFTY 50" },
    { symbol: "ICICIBANK", company_name: "ICICI Bank Ltd", sector: "Financial Services", index: "NIFTY 50" },
    { symbol: "INFY", company_name: "Infosys Ltd", sector: "Information Technology", index: "NIFTY 50" },
    { symbol: "SBIN", company_name: "State Bank of India", sector: "Financial Services", index: "NIFTY 50" },
    { symbol: "LT", company_name: "Larsen & Toubro Ltd", sector: "Construction", index: "NIFTY 50" },
    { symbol: "ITC", company_name: "ITC Ltd", sector: "Fast Moving Consumer Goods", index: "NIFTY 50" },
    { symbol: "BHARTIARTL", company_name: "Bharti Airtel Ltd", sector: "Telecommunication", index: "NIFTY 50" },
    { symbol: "TATAMOTORS", company_name: "Tata Motors Ltd", sector: "Automobile", index: "NIFTY 50" }
  ];

  // Load recent searches from LocalStorage
  useEffect(() => {
    const saved = localStorage.getItem('recent_searches');
    if (saved) {
      try {
        setRecentSearches(JSON.parse(saved));
      } catch (e) {
        console.error(e);
      }
    }
  }, []);

  // Click outside to close autocomplete dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced autocomplete query hook
  useEffect(() => {
    if (!searchTerm || searchTerm.trim().length === 0) {
      setSuggestions([]);
      return;
    }
    
    // Check if search matches current symbol exactly to prevent re-querying on selection
    if (searchTerm.toUpperCase() === symbol.toUpperCase() && suggestions.length === 0) {
      return;
    }

    const delayDebounceFn = setTimeout(async () => {
      setLoadingSuggestions(true);
      try {
        const response = await fetch(`${API_URL}/api/search/stocks?q=${encodeURIComponent(searchTerm)}`, {
          headers: getAuthHeaders()
        });
        if (response.ok) {
          const data = await response.json();
          setSuggestions(data.results || []);
        }
      } catch (err) {
        console.error("Error fetching autocomplete suggestions:", err);
      } finally {
        setLoadingSuggestions(false);
      }
    }, 200);

    return () => clearTimeout(delayDebounceFn);
  }, [searchTerm, symbol]);

  const selectStock = (sym: string, runImmediately: boolean = false) => {
    const upperSym = sym.toUpperCase();
    setSymbol(upperSym);
    setSearchTerm(upperSym);
    setShowDropdown(false);
    setHighlightedIndex(-1);
    
    // Save to LocalStorage
    const updated = [upperSym, ...recentSearches.filter(s => s !== upperSym)].slice(0, 10);
    setRecentSearches(updated);
    localStorage.setItem('recent_searches', JSON.stringify(updated));

    if (runImmediately) {
      setTimeout(() => {
        runSwarmCommittee(upperSym);
      }, 50);
    }
  };

  const highlightMatch = (textString: string, query: string) => {
    if (!query) return <span>{textString}</span>;
    const parts = textString.split(new RegExp(`(${query.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')})`, 'gi'));
    return (
      <span>
        {parts.map((part, i) => 
          part.toLowerCase() === query.toLowerCase() 
            ? <mark key={i} className="bg-brand-500/30 text-brand-300 font-semibold px-0.5 rounded">{part}</mark>
            : <span key={i}>{part}</span>
        )}
      </span>
    );
  };
  
  // Swarm / Committee state
  const [swarmEvents, setSwarmEvents] = useState<SwarmEvent[]>([]);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [pmVerdict, setPmVerdict] = useState<any>(null);
  const [explainableReport, setExplainableReport] = useState<any>(null);

  // Ref for autoscrolling swarm logs
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Autoscroll to bottom when new logs arrive
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [swarmEvents]);

  // Automatic polling refresh during market hours or if data is stale
  useEffect(() => {
    if (!pmVerdict || loading) return;
    const details = explainableReport || parseVerdictDetails(pmVerdict) || {};
    const isMarketOpen = details.is_market_open;
    const isStale = details.price_stale;
    
    if (isMarketOpen || isStale) {
      const intervalId = setInterval(() => {
        runSwarmCommittee(symbol);
      }, 10000);
      return () => clearInterval(intervalId);
    }
  }, [pmVerdict, symbol, loading, explainableReport]);
  


  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setShowDropdown(true);
      if (searchTerm.trim()) {
        if (suggestions.length > 0) {
          setHighlightedIndex(prev => (prev + 1) % suggestions.length);
        }
      } else {
        const emptyItemsCount = recentSearches.length + POPULAR_STOCKS.filter(p => !recentSearches.includes(p.symbol)).length;
        if (emptyItemsCount > 0) {
          setHighlightedIndex(prev => (prev + 1) % emptyItemsCount);
        }
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setShowDropdown(true);
      if (searchTerm.trim()) {
        if (suggestions.length > 0) {
          setHighlightedIndex(prev => (prev - 1 + suggestions.length) % suggestions.length);
        }
      } else {
        const emptyItemsCount = recentSearches.length + POPULAR_STOCKS.filter(p => !recentSearches.includes(p.symbol)).length;
        if (emptyItemsCount > 0) {
          setHighlightedIndex(prev => (prev - 1 + emptyItemsCount) % emptyItemsCount);
        }
      }
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (showDropdown) {
        if (searchTerm.trim()) {
          if (suggestions.length === 1) {
            selectStock(suggestions[0].symbol, true);
            return;
          }
          if (highlightedIndex >= 0 && highlightedIndex < suggestions.length) {
            selectStock(suggestions[highlightedIndex].symbol, true);
          } else if (searchTerm) {
            selectStock(searchTerm, true);
          }
        } else {
          const emptyItems = [
            ...recentSearches.map(s => {
              const pop = POPULAR_STOCKS.find(p => p.symbol === s);
              return { symbol: s, company_name: pop?.company_name || "Recent Search" };
            }),
            ...POPULAR_STOCKS.filter(p => !recentSearches.includes(p.symbol))
          ];
          if (highlightedIndex >= 0 && highlightedIndex < emptyItems.length) {
            selectStock(emptyItems[highlightedIndex].symbol, true);
          }
        }
      } else {
        runSwarmCommittee();
      }
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
      setHighlightedIndex(-1);
    } else if (e.key === 'Tab') {
      if (showDropdown) {
        if (searchTerm.trim() && highlightedIndex >= 0 && highlightedIndex < suggestions.length) {
          e.preventDefault();
          selectStock(suggestions[highlightedIndex].symbol);
        } else if (!searchTerm.trim()) {
          const emptyItems = [
            ...recentSearches.map(s => {
              const pop = POPULAR_STOCKS.find(p => p.symbol === s);
              return { symbol: s, company_name: pop?.company_name || "Recent Search" };
            }),
            ...POPULAR_STOCKS.filter(p => !recentSearches.includes(p.symbol))
          ];
          if (highlightedIndex >= 0 && highlightedIndex < emptyItems.length) {
            e.preventDefault();
            selectStock(emptyItems[highlightedIndex].symbol);
          }
        }
      }
    }
  };

  // Handle SSE streaming for Swarm Investment Committee
  const runSwarmCommittee = async (overrideSymbol?: any) => {
    const targetSymbol = (typeof overrideSymbol === 'string' ? overrideSymbol : null) || symbol;
    if (!targetSymbol) return;
    setLoading(true);
    setSwarmEvents([]);
    setPmVerdict(null);
    setExplainableReport(null);
    setActiveAgent(null);
    
    try {
      const response = await fetch(`${API_URL}/api/ai/committee`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({ symbol: targetSymbol.toUpperCase() })
      });
      
      if (!response.body) {
        throw new Error("No response body received from streaming endpoint.");
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          const cleaned = line.replace(/^data:\s*/, '').trim();
          if (!cleaned || cleaned === ': keepalive') continue;
          
          try {
            const event: SwarmEvent = JSON.parse(cleaned);
            setSwarmEvents(prev => [...prev, event]);
            
            if (event.type === 'worker_started' || event.type === 'worker_start') {
              setActiveAgent(event.agent_id || null);
            } else if (
              event.type === 'worker_completed' || 
              event.type === 'worker_failed' || 
              event.type === 'task_completed' || 
              event.type === 'task_failed' ||
              event.type === 'worker_end'
            ) {
              if (event.agent_id === activeAgent || event.agent_id) {
                setActiveAgent(null);
              }
              if (event.task_id === 'task-decision' && (event.type === 'task_completed' || event.type === 'worker_completed')) {
                const text = event.data?.summary || event.data?.result || event.data?.output || '';
                setPmVerdict(text);
                if (event.data?.explainable_report) {
                  setExplainableReport(event.data.explainable_report);
                }
              }
            }
          } catch (e) {
            console.error("Failed to parse event:", cleaned, e);
          }
        }
      }
    } catch (err: any) {
      console.error(err);
      setSwarmEvents(prev => [...prev, { type: 'error', data: { error: err.message || "Failed running swarm" } }]);
    } finally {
      setLoading(false);
    }
  };



  return (
    <div className="min-h-screen text-slate-100 flex flex-col bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800 p-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
        <div className="flex items-center gap-3">
          <Brain className="text-brand-500 w-8 h-8 animate-pulse" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-brand-400 to-emerald-400 bg-clip-text text-transparent">
              Vibe Trading / Coding
            </h1>
            <p className="text-xs text-slate-400">HKU Swarm Multi-Agent Reasoning Hub & Stock Evaluator</p>
          </div>
        </div>
        <div className="flex gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
          <span className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-brand-600 text-white shadow-lg select-none">
            Swarm Committee Workspace
          </span>
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* SWARM INVESTMENT COMMITTEE TAB */}
        <div className="flex flex-col lg:flex-row gap-6 flex-1">
            <div className="flex-1 bg-slate-950/60 rounded-xl border border-slate-800 p-6 flex flex-col">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Layers className="text-brand-500 w-5 h-5" /> Swarm DAG Execution Monitor
              </h2>
              
              <div className="flex gap-3 mb-6">
                <div ref={dropdownRef} className="relative flex-1">
                  <Search className="absolute left-3 top-2.5 text-slate-500 w-4 h-4" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => {
                      setSearchTerm(e.target.value);
                      setShowDropdown(true);
                      setHighlightedIndex(-1);
                    }}
                    onFocus={() => {
                      setShowDropdown(true);
                      setHighlightedIndex(-1);
                    }}
                    onKeyDown={handleKeyDown}
                    placeholder="Search Indian Stocks (e.g. RELIANCE, TCS, INFY)"
                    className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-sm focus:outline-none focus:border-brand-500 text-white"
                    role="combobox"
                    aria-expanded={showDropdown}
                    aria-autocomplete="list"
                    aria-controls="stock-search-listbox"
                    aria-haspopup="listbox"
                  />
                  
                  {showDropdown && (
                    <div 
                      id="stock-search-listbox"
                      role="listbox"
                      className="absolute left-0 right-0 mt-1.5 bg-slate-950/95 border border-slate-850 rounded-xl shadow-2xl z-50 max-h-[340px] overflow-y-auto flex flex-col backdrop-blur-md scrollbar-thin scrollbar-thumb-slate-800"
                    >
                      {loadingSuggestions ? (
                        <div className="p-4 flex items-center justify-center gap-2 text-xs text-slate-400">
                          <RefreshCw className="w-4 h-4 animate-spin text-brand-500" />
                          <span>Loading symbols...</span>
                        </div>
                      ) : searchTerm.trim() ? (
                        suggestions.length > 0 ? (
                          <div className="p-1.5 space-y-0.5">
                            {suggestions.map((item, idx) => {
                              const isHighlighted = idx === highlightedIndex;
                              return (
                                <div
                                  key={item.symbol}
                                  role="option"
                                  aria-selected={isHighlighted}
                                  onClick={() => selectStock(item.symbol)}
                                  onMouseEnter={() => setHighlightedIndex(idx)}
                                  className={`flex items-center justify-between px-3.5 py-2.5 rounded-lg cursor-pointer transition-all ${
                                    isHighlighted 
                                      ? 'bg-brand-600/20 text-white border-l-2 border-brand-500 pl-2.5' 
                                      : 'hover:bg-slate-900/60 text-slate-300'
                                  }`}
                                >
                                  <div className="flex flex-col text-left">
                                    <span className="font-bold text-sm tracking-wide text-white">
                                      {highlightMatch(item.symbol, searchTerm)}
                                    </span>
                                    <span className="text-[10px] text-slate-400 truncate max-w-[260px] md:max-w-[320px]">
                                      {highlightMatch(item.company_name, searchTerm)}
                                    </span>
                                  </div>
                                  
                                  <div className="flex items-center gap-2">
                                    <span className="text-[9px] px-2 py-0.5 bg-slate-900 border border-slate-850 text-slate-400 rounded-full">
                                      {item.sector}
                                    </span>
                                    {item.index && (
                                      <span className="text-[9px] px-2 py-0.5 bg-brand-950/60 border border-brand-800/40 text-brand-400 font-medium rounded-full">
                                        {item.index}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="p-5 text-center text-xs text-slate-400 flex flex-col items-center gap-2">
                            <AlertCircle className="w-8 h-8 text-slate-600 mb-1" />
                            <p className="font-semibold text-slate-350">No stocks found</p>
                            <p className="text-[10px] text-slate-500">Try searching by symbol or company name.</p>
                          </div>
                        )
                      ) : (
                        <div className="py-2.5 text-xs text-slate-400">
                          {recentSearches.length > 0 && (
                            <div className="mb-2">
                              <div className="px-3.5 py-1 text-[10px] uppercase font-bold tracking-wider text-slate-500 flex items-center gap-1.5">
                                <Clock className="w-3.5 h-3.5" /> Recent Searches
                              </div>
                              <div className="p-1 space-y-0.5">
                                {recentSearches.map((sym, idx) => {
                                  const pop = POPULAR_STOCKS.find(p => p.symbol === sym);
                                  const isHighlighted = idx === highlightedIndex;
                                  return (
                                    <div
                                      key={`recent-${sym}`}
                                      role="option"
                                      aria-selected={isHighlighted}
                                      onClick={() => selectStock(sym)}
                                      onMouseEnter={() => setHighlightedIndex(idx)}
                                      className={`flex items-center justify-between px-3.5 py-2 rounded-lg cursor-pointer transition-all ${
                                        isHighlighted 
                                          ? 'bg-brand-600/20 text-white border-l-2 border-brand-500 pl-2.5' 
                                          : 'hover:bg-slate-900/60 text-slate-350'
                                      }`}
                                    >
                                      <div className="flex flex-col text-left">
                                        <span className="font-bold text-white text-xs">{sym}</span>
                                        <span className="text-[9px] text-slate-500">{pop?.company_name || "Recent Search"}</span>
                                      </div>
                                      <span className="text-[9px] text-slate-500">{pop?.sector || ""}</span>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                          
                          <div>
                            <div className="px-3.5 py-1 text-[10px] uppercase font-bold tracking-wider text-slate-500 flex items-center gap-1.5">
                              <Star className="w-3.5 h-3.5 text-amber-550" /> Popular Stocks
                            </div>
                            <div className="p-1 space-y-0.5">
                              {POPULAR_STOCKS.filter(p => !recentSearches.includes(p.symbol)).map((item, idx) => {
                                const localIdx = recentSearches.length + idx;
                                const isHighlighted = localIdx === highlightedIndex;
                                return (
                                  <div
                                    key={`popular-${item.symbol}`}
                                    role="option"
                                    aria-selected={isHighlighted}
                                    onClick={() => selectStock(item.symbol)}
                                    onMouseEnter={() => setHighlightedIndex(localIdx)}
                                    className={`flex items-center justify-between px-3.5 py-2 rounded-lg cursor-pointer transition-all ${
                                      isHighlighted 
                                        ? 'bg-brand-600/20 text-white border-l-2 border-brand-500 pl-2.5' 
                                        : 'hover:bg-slate-900/60 text-slate-350'
                                    }`}
                                  >
                                    <div className="flex flex-col text-left">
                                      <span className="font-bold text-white text-xs">{item.symbol}</span>
                                      <span className="text-[9px] text-slate-500">{item.company_name}</span>
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                      <span className="text-[9px] text-slate-500">{item.sector}</span>
                                      <span className="text-[9px] px-1.5 py-0.5 bg-brand-950/40 text-brand-400 rounded-full font-medium">
                                        {item.index}
                                      </span>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                <button
                  onClick={runSwarmCommittee}
                  disabled={loading}
                  className="px-5 py-2 bg-brand-600 hover:bg-brand-500 text-white text-sm font-semibold rounded-lg flex items-center gap-2 shadow-lg disabled:opacity-50"
                >
                  {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  Debate Symbol
                </button>
              </div>

              {/* Agent Status Map */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {[
                  { id: 'bull_advocate', name: 'Bull Analyst', icon: TrendingUp },
                  { id: 'bear_advocate', name: 'Bear Analyst', icon: ShieldAlert },
                  { id: 'risk_officer', name: 'Risk Officer', icon: Target },
                  { id: 'portfolio_manager', name: 'Portfolio Manager', icon: Brain },
                ].map((agent) => {
                  const isActive = activeAgent === agent.id;
                  const isFinished = swarmEvents.some(
                    e => (e.type === 'worker_completed' || e.type === 'worker_failed' || e.type === 'task_completed' || e.type === 'task_failed' || e.type === 'worker_end') && 
                    e.agent_id === agent.id
                  );
                  return (
                    <div 
                      key={agent.id} 
                      className={`p-3 rounded-lg border flex items-center gap-3 transition-all ${
                        isActive 
                          ? 'bg-brand-950/40 border-brand-500/50 shadow-md shadow-brand-900/20' 
                          : isFinished 
                            ? 'bg-emerald-950/20 border-emerald-800/40' 
                            : 'bg-slate-900/40 border-slate-800'
                      }`}
                    >
                      <agent.icon className={`w-5 h-5 ${isActive ? 'text-brand-400' : isFinished ? 'text-emerald-400' : 'text-slate-500'}`} />
                      <div className="text-left">
                        <p className="text-xs font-semibold">{agent.name}</p>
                        <p className="text-[10px] text-slate-500">
                          {isActive ? 'Reasoning…' : isFinished ? 'Completed' : 'Idle'}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Live Swarm Stream Outputs */}
              <div className="flex-1 bg-slate-900/30 rounded-lg border border-slate-800/60 p-4 overflow-y-auto max-h-[350px]">
                <p className="text-xs text-slate-500 mb-2">Swarm Execution Logs:</p>
                {swarmEvents.length === 0 && <p className="text-xs text-slate-600">Enter a symbol and click Debate to launch the Swarm Agents.</p>}
                {swarmEvents.map((evt, idx) => (
                  <div key={idx} className="mb-2 text-xs font-mono text-slate-300 whitespace-pre-wrap break-words">
                    {(evt.type === 'worker_started' || evt.type === 'worker_start') && (
                      <span className="text-blue-400">[{evt.timestamp || new Date().toISOString()}] Agent {evt.agent_id} started.</span>
                    )}
                    {(evt.type === 'worker_completed' || evt.type === 'worker_end') && (
                      <span className="text-emerald-400">[{evt.timestamp || new Date().toISOString()}] Agent {evt.agent_id} completed.</span>
                    )}
                    {(evt.type === 'worker_failed' || evt.type === 'task_failed' || evt.type === 'error') && (
                      <span className="text-rose-400">[{evt.timestamp || new Date().toISOString()}] Error: {evt.data?.error || evt.data?.message}</span>
                    )}
                    {evt.type === 'worker_text' && (
                      <span className="text-slate-400">{evt.data?.content}</span>
                    )}
                    {evt.type === 'text_delta' && (
                      <span className="text-slate-400">{evt.data?.delta}</span>
                    )}
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            </div>
            {/* PM Decision Panel */}
            <div className="w-full lg:w-[560px] bg-slate-950/80 rounded-xl border border-slate-800 p-6 flex flex-col justify-between max-h-[900px] overflow-hidden">
              <div className="flex-1 flex flex-col overflow-hidden">
                <h3 className="text-lg font-semibold mb-4 flex items-center justify-between gap-2 flex-shrink-0">
                  <span className="flex items-center gap-2">
                    <Brain className="text-emerald-400 w-5 h-5" /> Swarm Committee Investment Verdict
                  </span>
                  {pmVerdict && (
                    <button
                      onClick={() => runSwarmCommittee(symbol)}
                      disabled={loading}
                      title="Force Refresh Latest Price"
                      className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-brand-500 rounded-lg text-[10px] text-slate-400 hover:text-white font-semibold transition-all flex items-center gap-1.5"
                    >
                      <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
                      Refresh
                    </button>
                  )}
                </h3>
                {pmVerdict ? (() => {
                  const details = explainableReport || parseVerdictDetails(pmVerdict) || {};
                  const votes = details.votes || {};
                  const indicators = details.indicators || {};
                  
                  const indKeys = Object.keys(indicators);
                  const bullishCount = indKeys.filter(k => indicators[k]?.status === 'Bullish').length;
                  const bearishCount = indKeys.filter(k => indicators[k]?.status === 'Bearish').length;
                  const totalSignals = indKeys.length;
                  const tfData = details.trend_timeframes || [];
                  const tfBullish = tfData.filter((t: any) => t.trend === 'Bullish').length;
                  const tfBearish = tfData.filter((t: any) => t.trend === 'Bearish').length;
                  const tfTotal = tfData.length;
                  
                  let consistencyError = null;
                  if (explainableReport && pmVerdict) {
                    const parsedConsensus = parseVerdictDetails(pmVerdict);
                    if (parsedConsensus) {
                      const cleanParsedVerdict = parsedConsensus.verdict?.trim().toUpperCase();
                      const cleanReportVerdict = explainableReport.verdict?.trim().toUpperCase();
                      if (cleanParsedVerdict && cleanReportVerdict && cleanParsedVerdict !== cleanReportVerdict) {
                        consistencyError = "Consensus Report does not match Portfolio Manager output. Inconsistent recommendations detected.";
                      }
                      const parsedTarget = parseFloat(parsedConsensus.targetPrice?.replace(/[^\d.]/g, '') || '0');
                      const reportTarget = parseFloat(String(explainableReport.target_price || '').replace(/[^\d.]/g, '') || '0');
                      if (parsedTarget > 0 && reportTarget > 0 && Math.abs(parsedTarget - reportTarget) > 0.05) {
                        consistencyError = "Consensus Report does not match Portfolio Manager output. Target price mismatch.";
                      }
                      const parsedStop = parseFloat(parsedConsensus.stopLoss?.replace(/[^\d.]/g, '') || '0');
                      const reportStop = parseFloat(String(explainableReport.stop_loss || '').replace(/[^\d.]/g, '') || '0');
                      if (parsedStop > 0 && reportStop > 0 && Math.abs(parsedStop - reportStop) > 0.05) {
                        consistencyError = "Consensus Report does not match Portfolio Manager output. Stop loss mismatch.";
                      }
                    }
                  }

                  if (consistencyError) {
                    return (
                      <div className="bg-rose-950/20 border border-rose-900/40 rounded-xl p-4 flex flex-col items-center justify-center text-center text-xs text-rose-400 py-12">
                        <AlertTriangle className="w-12 h-12 mb-3 text-rose-500 animate-pulse" />
                        <p className="font-bold text-sm mb-1 text-white">DecisionConsistencyError</p>
                        <p className="max-w-md leading-relaxed">{consistencyError}</p>
                      </div>
                    );
                  }
                  
                  return (
                    <div className="flex-1 overflow-y-auto pr-2 space-y-5 text-xs scrollbar-thin scrollbar-thumb-slate-800">
                      
                      {/* Data Source Warning */}
                      {details.data_source === 'simulated' && (
                        <div className="bg-amber-950/20 border border-amber-900/40 rounded-lg p-2.5 flex items-center gap-2 text-[10px] text-amber-400">
                          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                          <span>Analysis based on simulated data. Live Upstox data was unavailable.</span>
                        </div>
                      )}

                      {/* 1. Large Verdict Card */}
                      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 relative overflow-hidden">
                        <div className={`absolute top-0 right-0 w-24 h-24 bg-gradient-to-br ${details.verdict?.includes('BUY') ? 'from-emerald-500/10' : details.verdict?.includes('SELL') ? 'from-rose-500/10' : 'from-amber-500/10'} to-transparent rounded-bl-full pointer-events-none`} />
                        <h4 className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2">Verdict Executive Summary</h4>
                        <div className="flex items-baseline justify-between mb-3.5">
                          <span className={`text-4xl font-extrabold tracking-tight ${
                            details.verdict === 'BUY' ? 'text-emerald-400' :
                            details.verdict === 'SELL' ? 'text-rose-400' : 'text-amber-400'
                          }`}>
                            {details.verdict}
                          </span>
                          <span className="text-slate-400 text-xs font-semibold">
                            Confidence: <span className="text-white font-bold">{details.confidence}%</span>
                          </span>
                        </div>
                        
                        {/* Metrics Grid */}
                        <div className="grid grid-cols-3 gap-2 border-t border-slate-800/80 pt-3 text-[11px]">
                          <div>
                            <span className="text-slate-500 block mb-0.5 text-[9px] uppercase tracking-wider">Risk Level</span>
                            <span className="font-semibold text-slate-200">{details.risk_level}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block mb-0.5 text-[9px] uppercase tracking-wider">Horizon</span>
                            <span className="font-semibold text-slate-200">{details.horizon}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block mb-0.5 text-[9px] uppercase tracking-wider">Risk / Reward</span>
                            <span className="font-semibold text-slate-200">{details.risk_reward}</span>
                          </div>
                        </div>

                        <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-slate-850 text-[11px]">
                          <div>
                            <span className="text-slate-500 block mb-0.5 text-[9px] uppercase tracking-wider">Current Price</span>
                            <div className="flex items-center gap-1.5">
                              <span className="font-semibold text-slate-300">{details.current_price ? `₹${details.current_price}` : '—'}</span>
                              {details.is_market_open ? (
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" title="Market Open (Live)" />
                              ) : (
                                <span className="px-1 py-0.5 bg-slate-900 border border-slate-800 text-[7px] font-bold text-slate-400 rounded uppercase tracking-wide" title="Market Closed">
                                  Closed
                                </span>
                              )}
                            </div>
                          </div>
                          <div>
                            <span className="text-slate-500 block mb-0.5 text-[9px] uppercase tracking-wider">Target Price</span>
                            <span className="font-semibold text-emerald-400">{details.target_price ? `₹${details.target_price}` : '—'}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block mb-0.5 text-[9px] uppercase tracking-wider">Stop Loss</span>
                            <span className="font-semibold text-rose-400">{details.stop_loss ? `₹${details.stop_loss}` : '—'}</span>
                          </div>
                        </div>

                        {/* Data Freshness Indicator */}
                        <div className="mt-3 pt-2.5 border-t border-slate-800/40 flex flex-col gap-1 text-[9px] text-slate-500">
                          <div className="flex items-center justify-between">
                            <span>Last Price Update:</span>
                            <span className="font-semibold text-slate-400">
                              {details.price_updated_at ? (() => {
                                try {
                                  const date = new Date(details.price_updated_at);
                                  return date.toLocaleString('en-IN', {
                                    day: '2-digit',
                                    month: 'short',
                                    year: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit',
                                    second: '2-digit',
                                    hour12: true
                                  });
                                } catch (e) {
                                  return details.price_updated_at;
                                }
                              })() : '—'}
                              {details.price_source && ` (${details.price_source})`}
                            </span>
                          </div>
                          {details.price_stale && (
                            <div className="text-rose-400 font-semibold flex items-center gap-1.5 mt-0.5 bg-rose-950/20 border border-rose-900/30 p-2 rounded-lg text-[9px]">
                              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping inline-block" />
                              <span>⚠ Live market data may be outdated. Refreshing...</span>
                            </div>
                          )}
                        </div>
                        {/* Signal Summary & Weighted Score */}
                        <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-slate-800/40 text-[10px]">
                          <span className="text-slate-500">
                            Signals: <span className="text-emerald-400 font-bold">{details.signal_summary?.bullish || bullishCount}B</span> / <span className="text-rose-400 font-bold">{details.signal_summary?.bearish || bearishCount}S</span> / <span className="text-amber-400 font-bold">{details.signal_summary?.neutral || (totalSignals - bullishCount - bearishCount)}N</span>
                          </span>
                          <span className="text-slate-500">
                            Score: <span className={`font-bold ${(details.final_score || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>{details.final_score > 0 ? '+' : ''}{details.final_score?.toFixed(1) || '0.0'}</span>
                          </span>
                        </div>
                      </div>

                      {/* 2. Consensus Scorecard */}
                      <div className="bg-slate-900/30 border border-slate-800/60 rounded-xl p-4">
                        <h4 className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-3">Swarm Committee Votes</h4>
                        {votes.bull ? (
                        <div className="space-y-2">
                          {[
                            { name: 'Bull Analyst', vote: votes.bull?.vote || '—', sub: `Confidence ${votes.bull?.confidence || 0}%`, color: votes.bull?.vote === 'BUY' ? 'text-emerald-400' : votes.bull?.vote === 'SELL' ? 'text-rose-400' : 'text-slate-400' },
                            { name: 'Bear Analyst', vote: votes.bear?.vote || '—', sub: `Confidence ${votes.bear?.confidence || 0}%`, color: votes.bear?.vote === 'SELL' ? 'text-rose-400' : votes.bear?.vote === 'BUY' ? 'text-emerald-400' : 'text-slate-400' },
                            { name: 'Risk Officer', vote: votes.risk?.vote || '—', sub: votes.risk?.status || '', color: 'text-sky-400' },
                            { name: 'Portfolio Manager', vote: votes.pm?.vote || '—', sub: votes.pm?.status || '', color: 'text-brand-400' }
                          ].map((v, i) => (
                            <div key={i} className="flex justify-between items-center py-1 border-b border-slate-800/40 last:border-0">
                              <div>
                                <span className="font-medium text-slate-300">{v.name}</span>
                                <span className="text-[10px] text-slate-500 block">{v.sub}</span>
                              </div>
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold bg-slate-950 ${v.color}`}>{v.vote}</span>
                            </div>
                          ))}
                          <div className="mt-3 pt-2 border-t border-slate-800 flex justify-between items-center text-[10px]">
                            <span className="text-slate-400 font-semibold">Consensus Verdict</span>
                            <span className={`font-bold px-2 py-0.5 rounded border ${details.verdict?.includes('BUY') ? 'text-emerald-400 bg-emerald-950/40 border-emerald-900/30' : details.verdict?.includes('SELL') ? 'text-rose-400 bg-rose-950/40 border-rose-900/30' : 'text-amber-400 bg-amber-950/40 border-amber-900/30'}`}>{votes.consensus}</span>
                          </div>
                        </div>
                        ) : (
                          <p className="text-[10px] text-slate-500">Vote data unavailable.</p>
                        )}
                      </div>

                      {/* 3. Technical Indicator Summary */}
                      <div className="bg-slate-900/30 border border-slate-800/60 rounded-xl p-4">
                        <h4 className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-3">Technical Indicators</h4>
                        <div className="grid grid-cols-1 gap-2.5">
                          {[
                            { name: 'RSI (14)', key: 'rsi', label: 'Relative Strength Index', tooltip: 'Measures velocity & magnitude of price movements; values above 70 are overbought, below 30 oversold.' },
                            { name: 'MACD', key: 'macd', label: 'Moving Average Convergence Divergence', tooltip: 'Trend-following momentum indicator showing relationship between two moving averages.' },
                            { name: 'EMA 20', key: 'ema20', label: 'Exponential Moving Average 20', tooltip: 'Gives more weight to recent prices; acts as short-term dynamic support/resistance.' },
                            { name: 'EMA 50', key: 'ema50', label: 'Exponential Moving Average 50', tooltip: 'Indicates medium-term trend direction and key support anchors.' },
                            { name: 'ADX', key: 'adx', label: 'Average Directional Index', tooltip: 'Measures overall strength of a trend; values above 25 indicate a strong trend.' },
                            { name: 'Supertrend', key: 'supertrend', label: 'Volatility Stop Indicator', tooltip: 'Combines ATR and mid-price to define dynamic buy/sell stop lines.' },
                            { name: 'VWAP', key: 'vwap', label: 'Volume Weighted Average Price', tooltip: 'Average price intraday weighted by volume; key benchmark for institutional buyers.' },
                            { name: 'ATR (14)', key: 'atr', label: 'Average True Range', tooltip: 'Measures historical asset volatility; higher values represent larger daily price fluctuations.' },
                            { name: 'OBV', key: 'obv', label: 'On Balance Volume', tooltip: 'Uses volume flow to predict changes in stock price; confirms trend strength.' },
                            { name: 'Bollinger Bands', key: 'bollinger', label: 'Bollinger Envelopes', tooltip: 'Plots volatility bands above & below SMA; bands expand on high volatility, squeeze on low.' },
                            { name: 'Ichimoku Cloud', key: 'ichimoku', label: 'Ichimoku Kinko Hyo', tooltip: 'Comprehensive indicator showing support, resistance, trend direction, and momentum.' },
                            { name: 'Stochastic RSI', key: 'stoch_rsi', label: 'Stochastic Momentum Indicator', tooltip: 'Applies Stochastic formula to RSI values, showing high-sensitivity momentum shifts.' }
                          ].map((ind, i) => {
                            const data = indicators[ind.key] || { value: '-', status: 'Neutral', desc: '' };
                            return (
                              <div key={i} className="group relative bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/40 hover:border-slate-700/60 transition-all">
                                <div className="flex justify-between items-center mb-1">
                                  <div className="flex items-center gap-1">
                                    <span className="font-semibold text-slate-300">{ind.name}</span>
                                    <HelpCircle className="w-3.5 h-3.5 text-slate-600 hover:text-slate-400 cursor-help" />
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-slate-200 font-mono font-medium">{data.value}</span>
                                    <span className={`px-1.5 py-0.5 rounded-[3px] text-[8px] font-bold uppercase ${
                                      data.status === 'Bullish' ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-900/30' :
                                      data.status === 'Bearish' ? 'bg-rose-950/40 text-rose-400 border border-rose-900/30' :
                                      'bg-slate-900 text-slate-400 border border-slate-800'
                                    }`}>
                                      {data.status}
                                    </span>
                                  </div>
                                </div>
                                <p className="text-[10px] text-slate-400 leading-relaxed">{data.desc}</p>
                                <div className="flex justify-between items-center mt-1 pt-1 border-t border-slate-800/20">
                                  <span className="text-[9px] text-slate-500">Contribution</span>
                                  <span className={`text-[9px] font-bold ${data.score > 0 ? 'text-emerald-400' : data.score < 0 ? 'text-rose-400' : 'text-slate-500'}`}>{data.contribution || `${data.score > 0 ? '+' : ''}${data.score || 0} pts`}</span>
                                </div>
                                
                                {/* Tooltip */}
                                <div className="absolute hidden group-hover:block bg-slate-950 border border-slate-800 text-[10px] text-slate-300 p-2.5 rounded-lg z-50 w-64 shadow-2xl -top-16 left-4 transition-all">
                                  <p className="font-bold text-white mb-0.5">{ind.label}</p>
                                  <p className="leading-snug text-slate-400">{ind.tooltip}</p>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* 4. Price Action & Support/Resistance */}
                      <div className="bg-slate-900/30 border border-slate-800/60 rounded-xl p-4 space-y-4">
                        <div>
                          <h4 className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2.5">Price Action Analysis</h4>
                          <ul className="space-y-1.5">
                            {(details.price_action || []).map((p: string, i: number) => {
                              const isBearish = p.toLowerCase().includes('below') || p.toLowerCase().includes('lower') || p.toLowerCase().includes('bearish') || p.toLowerCase().includes('selling');
                              return (
                                <li key={i} className="flex items-start gap-2 text-slate-300">
                                  <span className={`font-bold ${isBearish ? 'text-rose-400' : 'text-emerald-400'}`}>{isBearish ? '✗' : '✓'}</span>
                                  <span className="leading-normal">{p}</span>
                                </li>
                              );
                            })}
                          </ul>
                        </div>
                        
                        <div className="border-t border-slate-800/60 pt-3">
                          <div className="flex justify-between items-center mb-2.5">
                            <h4 className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Support & Resistance</h4>
                            <span className="text-[9px] font-bold text-sky-400 bg-sky-950/40 px-1.5 py-0.5 rounded border border-sky-900/30">
                              {details.levels?.status || "Pivot Analysis"}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                            <div className="bg-slate-950/40 p-2 rounded border border-slate-800/40">
                              <span className="text-rose-400 block text-[9px] uppercase font-sans font-bold mb-1">Resistance</span>
                              <div className="flex justify-between"><span>R2:</span><span className="text-slate-300">₹{details.levels?.r2}</span></div>
                              <div className="flex justify-between"><span>R1:</span><span className="text-slate-300">₹{details.levels?.r1}</span></div>
                            </div>
                            <div className="bg-slate-950/40 p-2 rounded border border-slate-800/40">
                              <span className="text-emerald-400 block text-[9px] uppercase font-sans font-bold mb-1">Support</span>
                              <div className="flex justify-between"><span>S1:</span><span className="text-slate-300">₹{details.levels?.s1}</span></div>
                              <div className="flex justify-between"><span>S2:</span><span className="text-slate-300">₹{details.levels?.s2}</span></div>
                            </div>
                          </div>
                          <div className="bg-slate-950/30 p-2 rounded border border-slate-800/40 mt-2 flex justify-between items-center text-[10px]">
                            <span className="text-slate-400">Breakout Trigger Level</span>
                            <span className="text-emerald-400 font-bold font-mono">₹{details.levels?.breakout}</span>
                          </div>
                        </div>
                      </div>

                      {/* 5. Volume & Multi-Timeframe Trend */}
                      <div className="bg-slate-900/30 border border-slate-800/60 rounded-xl p-4 space-y-4">
                        <div>
                          <h4 className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2.5">Volume Analysis</h4>
                          <div className="grid grid-cols-2 gap-2 text-[11px] mb-2">
                            <div className="flex justify-between border-b border-slate-800/40 pb-1">
                              <span className="text-slate-500">Current Volume</span>
                              <span className="font-semibold text-slate-300">{details.volume?.current}</span>
                            </div>
                            <div className="flex justify-between border-b border-slate-800/40 pb-1">
                              <span className="text-slate-500">20-Day Average</span>
                              <span className="font-semibold text-slate-300">{details.volume?.average}</span>
                            </div>
                            <div className="flex justify-between border-b border-slate-800/40 pb-1">
                              <span className="text-slate-500">Relative Vol</span>
                              <span className="font-bold text-sky-400">{details.volume?.relative}</span>
                            </div>
                            <div className="flex justify-between border-b border-slate-800/40 pb-1">
                              <span className="text-slate-500">Delivery Ratio</span>
                              <span className="font-semibold text-slate-300">{details.volume?.delivery}</span>
                            </div>
                          </div>
                          <p className="text-[10px] text-slate-400 leading-relaxed bg-slate-950/20 p-2 rounded border border-slate-800/20">
                            Volume is <span className="text-white font-semibold">{details.volume?.relative}</span> of the 20-day benchmark, confirming active participant dynamics.
                          </p>
                        </div>

                        <div className="border-t border-slate-800/60 pt-3">
                          <div className="flex justify-between items-center mb-2.5">
                            <h4 className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Multi-Timeframe Trend</h4>
                            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${tfBullish > tfBearish ? 'text-emerald-400 bg-emerald-950/40 border-emerald-900/30' : tfBearish > tfBullish ? 'text-rose-400 bg-rose-950/40 border-rose-900/30' : 'text-amber-400 bg-amber-950/40 border-amber-900/30'}`}>
                              {details.tf_summary || `${tfBullish} / ${tfTotal} Bullish`}
                            </span>
                          </div>
                          <div className="grid grid-cols-5 gap-1 text-center text-[10px]">
                            {(details.trend_timeframes || []).map((t: any, i: number) => (
                              <div key={i} className="bg-slate-950/40 p-1.5 rounded border border-slate-800/40">
                                <span className="text-slate-500 block mb-1">{t.timeframe}</span>
                                <span className={`font-bold ${
                                  t.trend === 'Bullish' ? 'text-emerald-400' :
                                  t.trend === 'Bearish' ? 'text-rose-400' : 'text-amber-400'
                                }`}>
                                  {t.trend}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>

                      {/* 6. Risk Analysis */}
                      <div className="bg-slate-900/30 border border-slate-800/60 rounded-xl p-4">
                        <h4 className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2.5">Quantitative Risk Analysis</h4>
                        <div className="grid grid-cols-2 gap-2 text-[11px] mb-2">
                          <div className="flex justify-between border-b border-slate-800/40 pb-1">
                            <span className="text-slate-500">ATR Volatility</span>
                            <span className="font-semibold text-slate-300">{details.risk_metrics?.atr}</span>
                          </div>
                          <div className="flex justify-between border-b border-slate-800/40 pb-1">
                            <span className="text-slate-500">Expected Daily Move</span>
                            <span className="font-semibold text-slate-300">{details.risk_metrics?.expected_move}</span>
                          </div>
                          <div className="flex justify-between border-b border-slate-800/40 pb-1">
                            <span className="text-slate-500">Max Drawdown</span>
                            <span className="font-semibold text-slate-300">{details.risk_metrics?.max_drawdown}</span>
                          </div>
                          <div className="flex justify-between border-b border-slate-800/40 pb-1">
                            <span className="text-slate-500">Sharpe Ratio</span>
                            <span className="font-bold text-sky-400">{details.risk_metrics?.sharpe}</span>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-2 mt-2">
                          <div className="bg-slate-950/40 p-2 rounded border border-slate-800/40 text-center">
                            <span className="text-slate-500 block mb-0.5 text-[9px]">Stop Loss Prob.</span>
                            <span className="font-bold text-rose-400 text-xs">{details.risk_metrics?.prob_stop}</span>
                          </div>
                          <div className="bg-slate-950/40 p-2 rounded border border-slate-800/40 text-center">
                            <span className="text-slate-500 block mb-0.5 text-[9px]">Target Reach Prob.</span>
                            <span className="font-bold text-emerald-400 text-xs">{details.risk_metrics?.prob_target}</span>
                          </div>
                        </div>
                      </div>

                      {/* 7. Bull vs Bear Cases */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-emerald-950/10 border border-emerald-900/30 rounded-xl p-4">
                          <h4 className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider mb-2.5">Bull Factors</h4>
                          <ul className="space-y-1.5 text-[10px]">
                            {(details.bull_factors || []).map((f: string, i: number) => (
                              <li key={i} className="flex gap-1.5 text-slate-300 text-left">
                                <span className="text-emerald-400 font-bold">•</span>
                                <span className="leading-tight">{f}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                        
                        <div className="bg-rose-950/10 border border-rose-900/30 rounded-xl p-4">
                          <h4 className="text-[10px] text-rose-400 font-bold uppercase tracking-wider mb-2.5">Bear Factors</h4>
                          <ul className="space-y-1.5 text-[10px]">
                            {(details.bear_factors || []).map((f: string, i: number) => (
                              <li key={i} className="flex gap-1.5 text-slate-300 text-left">
                                <span className="text-rose-400 font-bold">•</span>
                                <span className="leading-tight">{f}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      {/* 8. Explainable Reasoning summary */}
                      <div className="bg-slate-900/30 border border-slate-800/60 rounded-xl p-4">
                        <h4 className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2">Why {details.verdict}?</h4>
                        {details.reasoning && details.reasoning.length > 0 ? (
                          <ul className="space-y-1.5 text-[11px] text-slate-300 text-left">
                            {details.reasoning.map((r: string, i: number) => (
                              <li key={i} className="flex gap-1.5 items-start">
                                <span className={`font-bold mt-0.5 ${details.verdict?.includes('BUY') ? 'text-emerald-400' : details.verdict?.includes('SELL') ? 'text-rose-400' : 'text-amber-400'}`}>•</span>
                                <span className="leading-tight">{r}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-[11px] text-slate-500">Reasoning data unavailable.</p>
                        )}
                      </div>

                      {/* 9. Confidence Breakdown */}
                      <div className="bg-slate-900/30 border border-slate-800/60 rounded-xl p-4">
                        <h4 className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-3">Confidence Breakdown</h4>
                        <div className="space-y-2 text-[11px]">
                          {(details.confidence_breakdown ? Object.values(details.confidence_breakdown).map((c: any) => ({ name: c.label || 'Unknown', val: c.value || 0 })) : []).map((c: any, i: number) => (
                            <div key={i} className="space-y-1">
                              <div className="flex justify-between text-[10px]">
                                <span className="text-slate-400">{c.name}</span>
                                <span className="font-semibold text-slate-200">{c.val}%</span>
                              </div>
                              <div className="h-1.5 w-full bg-slate-950 rounded-full overflow-hidden">
                                <div className="h-full bg-brand-500 rounded-full" style={{ width: `${c.val * 2.5}%` }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* 10. Strategy Recommendation */}
                      <div className="bg-slate-900/30 border border-slate-800/60 rounded-xl p-4">
                        <h4 className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2.5">Recommended Strategy</h4>
                        <div className="grid grid-cols-2 gap-2 text-[11px] mb-3">
                          <div className="flex justify-between border-b border-slate-800/40 pb-1">
                            <span className="text-slate-500">Trade Style</span>
                            <span className="font-semibold text-slate-300">{details.recommended_strategy?.style}</span>
                          </div>
                          <div className="flex justify-between border-b border-slate-800/40 pb-1">
                            <span className="text-slate-500">Holding Horizon</span>
                            <span className="font-semibold text-slate-300">{details.recommended_strategy?.holding}</span>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-[11px] font-mono bg-slate-950/40 p-2.5 rounded border border-slate-800/40">
                          <div className="flex justify-between">
                            <span className="text-slate-500">Entry Zone:</span>
                            <span className="text-emerald-400 font-bold">{details.recommended_strategy?.entry}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">Add on Dip:</span>
                            <span className="text-emerald-400 font-bold">{details.recommended_strategy?.add_on_dip}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">Partial Exit:</span>
                            <span className="text-slate-300 font-bold">{details.recommended_strategy?.partial}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">Final Target:</span>
                            <span className="text-emerald-400 font-bold">{details.recommended_strategy?.exit}</span>
                          </div>
                        </div>
                      </div>

                      {/* 11. Historical Statistics */}
                      <div className="bg-slate-900/30 border border-slate-800/60 rounded-xl p-4">
                        <h4 className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2.5">Historical Setup Performance</h4>
                        {details.historical_stats ? (
                          <div className="grid grid-cols-2 gap-2 text-[11px] mb-2">
                            <div className="flex justify-between border-b border-slate-800/40 pb-1">
                              <span className="text-slate-500">Occurrences</span>
                              <span className="font-semibold text-slate-300">{details.historical_stats.occurrences}</span>
                            </div>
                            <div className="flex justify-between border-b border-slate-800/40 pb-1">
                              <span className="text-slate-500">Success Rate</span>
                              <span className="font-bold text-emerald-400">{details.historical_stats.success_rate}</span>
                            </div>
                          </div>
                        ) : (
                          <p className="text-[10px] text-slate-500 leading-normal text-left">
                            Historical statistics unavailable. Connect the backtesting engine for historical setup performance data.
                          </p>
                        )}
                      </div>

                      {/* 12. Decision Audit Trail */}
                      {details.audit_trail && (
                        <details className="bg-slate-900/20 border border-slate-800/40 rounded-xl">
                          <summary className="p-3 text-[10px] text-slate-500 font-bold uppercase tracking-wider cursor-pointer hover:text-slate-400 select-none">Decision Audit Trail</summary>
                          <div className="px-3 pb-3 text-[10px] font-mono text-slate-400 space-y-1">
                            <div className="flex justify-between"><span>Data Source:</span><span className={details.audit_trail.data_source === 'live' ? 'text-emerald-400' : 'text-amber-400'}>{details.audit_trail.data_source}</span></div>
                            <div className="flex justify-between"><span>Data Points:</span><span>{details.audit_trail.data_points}</span></div>
                            <div className="flex justify-between"><span>Indicators:</span><span>{details.audit_trail.bullish_count}B / {details.audit_trail.bearish_count}S / {details.audit_trail.neutral_count}N</span></div>
                            <div className="border-t border-slate-800/40 pt-1 mt-1">
                              {details.audit_trail.category_breakdown && Object.entries(details.audit_trail.category_breakdown).map(([cat, data]: [string, any]) => (
                                <div key={cat} className="flex justify-between"><span>{cat} ({data.weight}):</span><span className={data.weighted_score >= 0 ? 'text-emerald-400' : 'text-rose-400'}>{data.weighted_score > 0 ? '+' : ''}{data.weighted_score}</span></div>
                              ))}
                            </div>
                            <div className="border-t border-slate-800/40 pt-1 mt-1 flex justify-between font-bold"><span>Final Score:</span><span className={details.audit_trail.final_score >= 0 ? 'text-emerald-400' : 'text-rose-400'}>{details.audit_trail.final_score > 0 ? '+' : ''}{details.audit_trail.final_score}</span></div>
                            <div className="flex justify-between font-bold"><span>Verdict:</span><span>{details.audit_trail.verdict}</span></div>
                            <div className="flex justify-between"><span>Confidence:</span><span>{details.audit_trail.confidence}%</span></div>
                          </div>
                        </details>
                      )}

                      {/* 12. Consensus Summary Report Text */}
                      <div className="bg-slate-900/30 border border-slate-850 p-4 rounded-xl">
                        <div className="flex items-center gap-2 mb-3">
                          <CheckCircle className="text-emerald-400 w-4 h-4" />
                          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">Consensus Report</span>
                        </div>
                        <div className="text-[11px] text-slate-300 whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto pr-1 text-left">
                          {pmVerdict}
                        </div>
                      </div>
                    </div>
                  );
                })() : (
                  <div className="flex flex-col items-center justify-center py-20 text-slate-600 flex-1">
                    <Brain className="w-12 h-12 mb-3" />
                    <p className="text-xs">Waiting for Portfolio Manager decision...</p>
                  </div>
                )}
              </div>
              <div className="mt-4 pt-4 border-t border-slate-800 text-center flex-shrink-0">
                <p className="text-[10px] text-slate-500">Every analysis weighs long triggers, downside risk filters, and asset volatility constraints.</p>
              </div>
            </div>
        </div>
      </div>
    </div>
  );
};

export default VibeTrading;
