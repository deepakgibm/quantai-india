import React, { useState, useMemo } from 'react';
import { 
  HelpCircle, 
  Search, 
  ArrowRight, 
  BookOpen, 
  Compass, 
  ChevronDown, 
  Activity, 
  Sliders, 
  Cpu, 
  Sparkles, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  BarChart2,
  FolderHeart,
  TrendingUp,
  Info
} from 'lucide-react';

interface FAQItem {
  question: string;
  answer: string;
  category: string;
}

const FAQ_ITEMS: FAQItem[] = [
  {
    category: 'General',
    question: 'What is the Quant Research Terminal?',
    answer: 'The Quant Research Terminal is an institutional-grade quantitative development environment. It enables traders to design, backtest, optimize, and validate algorithmic strategies using 100% real historical and live market data feeds from Upstox APIs.'
  },
  {
    category: 'Discovery',
    question: 'How is the strategy ranking calculated in Discovery?',
    answer: 'Strategies are ranked using a multi-factor scoring model. The algorithm assigns weights to Net Profit (30%), Sharpe Ratio (25%), Profit Factor (20%), Max Drawdown (15%), and Win Rate (10%). Strategies that perform well across all dimensions rank higher than those with volatile single-metric performance.'
  },
  {
    category: 'Walk-Forward',
    question: 'What is Walk-Forward Analysis and why should I use it?',
    answer: 'Walk-Forward Analysis is a technique that divides historical data into overlapping "training" (In-Sample) and "validation" (Out-of-Sample) windows. It simulates how a strategy would behave if periodically optimized in real-time, reducing curve-fitting and confirming parameter robustness.'
  },
  {
    category: 'Monte Carlo',
    question: 'How does Monte Carlo bootstrap sampling work?',
    answer: 'Monte Carlo simulation reshuffles and re-samples your actual historical trade sequence thousands of times (using bootstrap sampling). It generates distribution curves that project the probability of account drawdown, worst-case drawdown paths, and the exact probability of risk of ruin.'
  },
  {
    category: 'Data Source',
    question: 'Where does the market data come from?',
    answer: 'All OHLC candles, options chains, and spot quotes are fetched directly from Upstox API endpoints. The system contains zero mocked, simulated, or randomized market data, ensuring that every backtest represents realistic trading conditions.'
  },
  {
    category: 'Troubleshooting',
    question: 'Why am I seeing "No trades generated" during a backtest?',
    answer: 'This occurs when your strategy rules (e.g. MA crossovers or threshold levels) are too restrictive for the chosen historical date range or timeframe, or when the stock did not experience the required signal triggers. Try widening parameters or selecting a longer historical lookback.'
  }
];

export const HelpCenter: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'discovery' | 'backtest' | 'wfa' | 'montecarlo' | 'optimization' | 'portfolio'>('all');
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);

  const syncTimestamp = useMemo(() => {
    return new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }, []);

  const filteredFaqs = useMemo(() => {
    return FAQ_ITEMS.filter(faq => {
      const matchesSearch = faq.question.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            faq.answer.toLowerCase().includes(searchQuery.toLowerCase());
      if (!matchesSearch) return false;
      if (activeTab === 'all') return true;
      if (activeTab === 'discovery' && faq.category === 'Discovery') return true;
      if (activeTab === 'wfa' && faq.category === 'Walk-Forward') return true;
      if (activeTab === 'montecarlo' && faq.category === 'Monte Carlo') return true;
      if (activeTab === 'optimization' && faq.category === 'Optimization') return true;
      if (activeTab === 'portfolio' && faq.category === 'Portfolio') return true;
      return false;
    });
  }, [searchQuery, activeTab]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
      {/* Header Banner */}
      <div className="relative overflow-hidden bg-gradient-to-r from-slate-900 to-indigo-950 border border-slate-800 rounded-2xl p-8 mb-6 shadow-xl">
        <div className="absolute top-0 right-0 w-80 h-80 bg-brand-500/10 rounded-full blur-3xl -mr-16 -mt-16" />
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div>
            <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs uppercase tracking-wider mb-2">
              <Sparkles size={14} /> Help Center & Knowledge Base
            </div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">Quant Research Guide</h1>
            <p className="text-sm text-slate-400 mt-2 max-w-xl">
              Learn the institutional quantitative workflow. Transition seamlessly from strategy discovery and backtesting to robust walk-forward testing and risk management.
            </p>
          </div>
          
          {/* Transparency Panel */}
          <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 shrink-0 w-full md:w-80 backdrop-blur-md">
            <h3 className="text-xs font-black uppercase text-indigo-400 tracking-widest flex items-center gap-1.5 mb-2">
              <Info size={13} /> Data Source Transparency
            </h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center py-1 border-b border-slate-900">
                <span className="text-slate-500">Source:</span>
                <span className="font-bold text-slate-200">Upstox REST & WS APIs</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-slate-900">
                <span className="text-slate-500">Market Coverage:</span>
                <span className="text-slate-200">NIFTY 500 Equities</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-slate-900">
                <span className="text-slate-500">Sync Status:</span>
                <span className="flex items-center gap-1 text-emerald-400 font-bold">
                  <CheckCircle2 size={12} /> Synchronized
                </span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="text-slate-500">Last Checked:</span>
                <span className="font-mono text-[10px] text-slate-400">{syncTimestamp}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Columns: Workflow Guides */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Module Navigation Tabs */}
          <div className="flex flex-wrap gap-2 border-b border-slate-900 pb-3">
            {[
              { id: 'all', label: 'All Modules' },
              { id: 'discovery', label: 'Discovery' },
              { id: 'backtest', label: 'Backtest' },
              { id: 'wfa', label: 'Walk-Forward' },
              { id: 'montecarlo', label: 'Monte Carlo' },
              { id: 'optimization', label: 'Optimization' },
              { id: 'portfolio', label: 'Portfolio' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-3 py-1.5 text-xs font-bold rounded-lg border transition-all ${
                  activeTab === tab.id
                    ? 'bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-600/20'
                    : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Workflow Overview */}
          {(activeTab === 'all') && (
            <div className="bg-slate-900 border border-slate-800/80 rounded-xl p-6">
              <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <Compass className="text-indigo-400" size={18} /> Typical Quantitative Research Workflow
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative">
                {[
                  {
                    step: '01',
                    title: 'Discovery & Screening',
                    desc: 'Scan the NIFTY 500 universe using Strategy Discovery to find high-probability configurations and rank them.'
                  },
                  {
                    step: '02',
                    title: 'Backtesting',
                    desc: 'Perform bar-by-bar backtests on specific symbols. Examine key ratios, drawdowns, and execute-by-bar rules.'
                  },
                  {
                    step: '03',
                    title: 'Walk-Forward & MC',
                    desc: 'Validate robustness across overlapping test windows, and run Monte Carlo simulation to quantify risk of ruin.'
                  }
                ].map((item, idx) => (
                  <div key={idx} className="bg-slate-950 p-4 border border-slate-900 rounded-lg flex flex-col justify-between">
                    <div>
                      <span className="text-[10px] font-black text-indigo-500 block mb-1">{item.step}</span>
                      <h4 className="text-xs font-bold text-slate-200 mb-2">{item.title}</h4>
                      <p className="text-xs text-slate-400 leading-relaxed">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Detailed Section Guides */}
          <div className="space-y-4">
            {/* 1. Discovery Section */}
            {(activeTab === 'all' || activeTab === 'discovery') && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
                    <Sparkles size={18} />
                  </div>
                  <div>
                    <h3 className="font-bold text-white text-sm">Strategy Discovery Engine</h3>
                    <p className="text-xs text-slate-500">Scan symbols across timeframes to discover alpha configurations.</p>
                  </div>
                </div>
                <div className="text-xs text-slate-300 space-y-3 leading-relaxed">
                  <p>
                    <strong>Purpose:</strong> Strategy Discovery helps you find top-performing technical strategies on specific NIFTY 500 stocks. Instead of guessing parameter sets, the engine runs exhaustive historical analysis.
                  </p>
                  <p>
                    <strong>Key Parameters:</strong>
                  </p>
                  <ul className="list-disc pl-5 space-y-1 text-slate-400">
                    <li><strong className="text-slate-200">Symbol & Timeframe:</strong> Choose the asset (e.g. RELIANCE) and chart periodicity (e.g. 15m, 1D).</li>
                    <li><strong className="text-slate-200">Initial Capital:</strong> Allocated virtual funds to compute compounding return values.</li>
                    <li><strong className="text-slate-200">Date Range:</strong> Start and end dates for historical candle fetching.</li>
                  </ul>
                  <p>
                    <strong>Metric Glossary:</strong>
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3 bg-slate-950 p-3 rounded-lg border border-slate-900 font-mono text-[11px]">
                    <div>
                      <span className="block text-slate-500 text-[10px] uppercase">CAGR</span>
                      <span className="text-slate-200">Compound annual growth rate</span>
                    </div>
                    <div>
                      <span className="block text-slate-500 text-[10px] uppercase">Sharpe Ratio</span>
                      <span className="text-slate-200">Risk-adjusted return ratio</span>
                    </div>
                    <div>
                      <span className="block text-slate-500 text-[10px] uppercase">Win Rate</span>
                      <span className="text-slate-200">% of profitable trades</span>
                    </div>
                    <div>
                      <span className="block text-slate-500 text-[10px] uppercase">Profit Factor</span>
                      <span className="text-slate-200">Gross profit / Gross loss</span>
                    </div>
                    <div>
                      <span className="block text-slate-500 text-[10px] uppercase">Max Drawdown</span>
                      <span className="text-slate-200">Peak-to-trough account decline</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 2. Backtest Section */}
            {(activeTab === 'all' || activeTab === 'backtest') && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg">
                    <Activity size={18} />
                  </div>
                  <div>
                    <h3 className="font-bold text-white text-sm">Historical Backtesting</h3>
                    <p className="text-xs text-slate-500">Run sequential simulations to track trade executions.</p>
                  </div>
                </div>
                <div className="text-xs text-slate-300 space-y-3 leading-relaxed">
                  <p>
                    <strong>Configuration:</strong> Select your strategy (e.g. EMA Crossover or SuperTrend), customize parameter fields (Fast Period, Slow Period, Risk-Reward target), and press Run Backtest.
                  </p>
                  <p>
                    <strong>Execution Pipeline:</strong> The system fetches raw Upstox candles, runs indicator computations, identifies entry/exit triggers, and sequential bar-by-bar execution simulates order fills incorporating slippage and commission settings.
                  </p>
                  <p>
                    <strong>Analysis Panels:</strong>
                  </p>
                  <ul className="list-disc pl-5 space-y-1 text-slate-400">
                    <li><strong className="text-slate-200">Equity Curve:</strong> Visualizes cumulative portfolio value over time.</li>
                    <li><strong className="text-slate-200">Trade List:</strong> Complete history of entries, exits, stop loss triggers, and target price captures.</li>
                    <li><strong className="text-slate-200">Monthly Return Grid:</strong> Calendar matrix indicating monthly strategy gains or losses.</li>
                  </ul>
                </div>
              </div>
            )}

            {/* 3. Walk Forward Section */}
            {(activeTab === 'all' || activeTab === 'wfa') && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
                    <Cpu size={18} />
                  </div>
                  <div>
                    <h3 className="font-bold text-white text-sm">Walk-Forward Analysis (WFA)</h3>
                    <p className="text-xs text-slate-500">Determine strategy stability and robustness over shifting windows.</p>
                  </div>
                </div>
                <div className="text-xs text-slate-300 space-y-3 leading-relaxed">
                  <p>
                    <strong>Overfitting Risk:</strong> Backtest optimization can result in curve-fitting where a strategy works perfectly in the past but collapses on new data. WFA protects you from this.
                  </p>
                  <p>
                    <strong>Testing Windows:</strong> WFA splits historical data into overlapping In-Sample (IS) training segments where parameters are optimized, and immediately validates them in Out-of-Sample (OOS) segments.
                  </p>
                  <p>
                    <strong>Robustness Rating:</strong> The WFA dashboard scores your configuration based on OOS performance vs. IS parameters. A high robustness rating (&gt; 60%) suggests the strategy is stable.
                  </p>
                </div>
              </div>
            )}

            {/* 4. Monte Carlo Section */}
            {(activeTab === 'all' || activeTab === 'montecarlo') && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-purple-500/10 text-purple-400 rounded-lg">
                    <BarChart2 size={18} />
                  </div>
                  <div>
                    <h3 className="font-bold text-white text-sm">Monte Carlo Risk Simulation</h3>
                    <p className="text-xs text-slate-500">Calculate probability metrics using random bootstrap reshuffling.</p>
                  </div>
                </div>
                <div className="text-xs text-slate-300 space-y-3 leading-relaxed">
                  <p>
                    <strong>Methodology:</strong> Monte Carlo does not use randomly generated values. Instead, it extracts the actual list of trades from your backtest and runs bootstrap sampling (shuffling the order of trades 1,000+ times) to create simulated paths.
                  </p>
                  <p>
                    <strong>What it reveals:</strong> It reveals the probability of experiencing a consecutive streak of losing trades (consecutive drawdown) and identifies the risk of ruin.
                  </p>
                  <p>
                    <strong>Confidence Intervals:</strong>
                  </p>
                  <ul className="list-disc pl-5 space-y-1 text-slate-400">
                    <li><strong className="text-slate-200">95% Confidence:</strong> 95% of the simulated paths ended with a return better than this value.</li>
                    <li><strong className="text-slate-200">Risk of Ruin:</strong> The percentage of simulation runs where the account equity drops below a critical threshold (e.g. 50% loss).</li>
                  </ul>
                </div>
              </div>
            )}

            {/* 5. Optimization Section */}
            {(activeTab === 'all' || activeTab === 'optimization') && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg">
                    <Sliders size={18} />
                  </div>
                  <div>
                    <h3 className="font-bold text-white text-sm">Parameter Sweeps & Optimization</h3>
                    <p className="text-xs text-slate-500">Scan parameters across grid spaces to locate optimal setups.</p>
                  </div>
                </div>
                <div className="text-xs text-slate-300 space-y-3 leading-relaxed">
                  <p>
                    <strong>Grid Search:</strong> Optimizing involves testing combinations of values (e.g. Fast MA from 5 to 20, Slow MA from 20 to 50). The grid optimizer runs a backtest for every configuration and ranks them in a heatmap table.
                  </p>
                  <p>
                    <strong>Best Fit Criteria:</strong> Do not simply pick the highest Net Profit. Look for parameter "islands" where nearby values also yield stable, positive returns. Choosing isolated peaks increases curve-fitting risk.
                  </p>
                </div>
              </div>
            )}

            {/* 6. Portfolio Section */}
            {(activeTab === 'all' || activeTab === 'portfolio') && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-sky-500/10 text-sky-400 rounded-lg">
                    <FolderHeart size={18} />
                  </div>
                  <div>
                    <h3 className="font-bold text-white text-sm">Portfolio Management & Comparison</h3>
                    <p className="text-xs text-slate-500">Save, combine, and correlate multiple backtested configurations.</p>
                  </div>
                </div>
                <div className="text-xs text-slate-300 space-y-3 leading-relaxed">
                  <p>
                    <strong>Comparison:</strong> Compare strategies side-by-side. Save individual backtests, add them to your portfolio drawer, and inspect cumulative performance.
                  </p>
                  <p>
                    <strong>Diversification benefits:</strong> Combining uncorrelated strategies (e.g. a trend-following breakout model on metals + a mean reversion model on IT sector) smooths the equity curve and lowers portfolio-level drawdown.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: FAQ & Search & Troubleshooting */}
        <div className="space-y-6">
          
          {/* FAQ Search */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="text-sm font-bold text-white mb-3">Search FAQ & Articles</h3>
            <div className="relative mb-4">
              <input
                type="text"
                placeholder="Search guide..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2 pl-9 pr-4 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
              <Search className="absolute left-3 top-2.5 text-slate-500" size={14} />
            </div>

            {/* Search list */}
            <div className="space-y-3">
              {filteredFaqs.map((faq, idx) => {
                const isExpanded = expandedFaq === idx;
                return (
                  <div key={idx} className="border-b border-slate-900 pb-2.5 last:border-0 last:pb-0">
                    <button
                      onClick={() => setExpandedFaq(isExpanded ? null : idx)}
                      className="w-full text-left flex justify-between items-start gap-2 text-xs font-bold text-slate-300 hover:text-white transition-colors"
                    >
                      <span>{faq.question}</span>
                      <ChevronDown
                        size={14}
                        className={`text-slate-500 shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                      />
                    </button>
                    {isExpanded && (
                      <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
                        {faq.answer}
                      </p>
                    )}
                  </div>
                );
              })}
              {filteredFaqs.length === 0 && (
                <div className="text-center py-4 text-xs text-slate-600 font-medium">
                  No matches found for your search query.
                </div>
              )}
            </div>
          </div>

          {/* Troubleshooting Panel */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
              <AlertTriangle className="text-amber-500" size={16} /> Troubleshooting & Safeguards
            </h3>
            
            <div className="space-y-3.5 text-xs">
              <div className="flex gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                <div>
                  <h4 className="font-bold text-slate-200">No results returned / Slow execution</h4>
                  <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                    Check your date range. Fetching large tick data over years can trigger rate limit throttling on Upstox APIs. Shorten range or increase timeframe.
                  </p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                <div>
                  <h4 className="font-bold text-slate-200">Authentication / Rate Limits</h4>
                  <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                    The Upstox rate limits allow 200 API calls per minute. If you exceed this, wait 60 seconds. Make sure your Upstox login session has not expired.
                  </p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                <div>
                  <h4 className="font-bold text-slate-200">Invalid Symbol / Weekend data</h4>
                  <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                    Ensure symbol keys are correct (e.g. NSE_EQ|INE002A01018). Upstox feeds do not contain candles during weekends, holidays, or off-market hours.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
