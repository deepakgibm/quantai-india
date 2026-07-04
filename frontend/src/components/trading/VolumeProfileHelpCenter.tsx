import React, { useState, useMemo } from 'react';
import { X, Search, BookOpen, GraduationCap, Zap, HelpCircle, Layers, Settings, ArrowUpRight } from 'lucide-react';

interface VolumeProfileHelpCenterProps {
  onClose: () => void;
  initialTopic?: string;
}

const GLOSSARY = [
  { term: "Acceptance", desc: "Price trading inside a zone for a sustained period, indicating agreement on fair value.", adv: "Indicates that market participants agree that the price is 'fair' given current information, leading to consolidation." },
  { term: "Auction", desc: "The process of moving price up and down to find buyers and sellers.", adv: "The core mechanic of price discovery where the market auctions high to find sellers and low to find buyers." },
  { term: "Composite Profile", desc: "Volume Profile aggregated over a long timeframe (e.g. 1 year) to identify historical zones.", adv: "Represents the long-term balance area of an asset, highlighting key high-volume pivots over multiple market cycles." },
  { term: "Delta", desc: "The difference between buying volume and selling volume.", adv: "Calculated by subtracting bid-side volume from ask-side volume at each price level to evaluate market orders imbalance." },
  { term: "Distribution", desc: "The shape or spread of volume traded across price levels.", adv: "A statistical spread of volume. Can be normal (D-shape), double distribution (B-shape), or skewed." },
  { term: "Fair Value", desc: "The price range where the highest number of transactions take place.", adv: "The price region where supply and demand are in equilibrium, represented by the Point of Control (POC)." },
  { term: "HVN (High Volume Node)", desc: "Prices with significant traded volume. Often act as support/resistance.", adv: "High Volume Nodes act as support/resistance zones because they represent heavy historical consensus and institutional blocks." },
  { term: "LVN (Low Volume Node)", desc: "Prices with very low traded volume. Price usually moves past these fast.", adv: "Represent areas of unfair value or rejection. Price tends to slice through these gaps rapidly with little rotational friction." },
  { term: "POC (Point of Control)", desc: "The price level where the highest volume was traded.", adv: "The absolute peak of the Volume Profile histogram. Represents the primary rotation anchor and fair value pivot." },
  { term: "VA (Value Area)", desc: "The price range where 70% of the session volume was traded.", adv: "One standard deviation of volume. Represents the boundaries of accepted fair value for the given lookback period." },
  { term: "VAH (Value Area High)", desc: "The upper boundary of the 70% Value Area.", adv: "Acts as a key resistance level. Sustained breakouts above VAH signify initiative buying accepting higher prices." },
  { term: "VAL (Value Area Low)", desc: "The lower boundary of the 70% Value Area.", adv: "Acts as a key support level. Breaks below VAL signify initiative selling rejecting the value area." },
  { term: "VWAP", desc: "Volume Weighted Average Price.", adv: "The average price weighted by intraday transactions volume. A major benchmark for institutional execution algorithms." }
];

const FAQS = [
  { q: "What is Volume Profile?", a: "Unlike standard volume bars which show volume over time, Volume Profile shows volume at specific price levels. This highlights price levels of high and low liquidity." },
  { q: "How is the POC calculated?", a: "The POC (Point of Control) is computed by finding the price bin (or tick range) that accumulated the highest sum of candle volume over the selected lookback period." },
  { q: "Why does price revisit the POC?", a: "The POC represents the most agreed-upon 'Fair Value'. If there is no new trend catalyst, the price naturally gravitates back to this level where liquidity is highest." },
  { q: "What is the Value Area?", a: "The Value Area is the range of prices that accounts for 70% of all volume traded. It is mathematically based on one standard deviation of the volume distribution." },
  { q: "Can the POC change?", a: "Yes. As new candles form with higher volume at different price ranges, the peak of the histogram can shift. A shifting POC is a strong indicator of trend development." }
];

const STRATEGIES = [
  {
    title: "Strategy 1: POC Bounce Setup",
    concept: "Trading rotation back to the Point of Control during range-bound sessions.",
    entry: "Place Limit Buy order slightly above POC when price pullbacks from VAH.",
    stop: "Place Stop Loss below VAL (for longs) or above VAH (for shorts).",
    target: "Target VAH (for longs) or VAL (for shorts).",
    tips: "Only use this strategy when the profile shape is D-shaped (Balanced Market)."
  },
  {
    title: "Strategy 2: Value Area Breakout",
    concept: "Trading breakouts out of value area acceptance zones.",
    entry: "Buy when a daily candle closes above VAH with volume expansion.",
    stop: "Place Stop Loss inside the Value Area (e.g. at the POC).",
    target: "Target the next major historical High Volume Node (HVN).",
    tips: "Ensure the break is accompanied by rising volume to avoid false breakouts."
  },
  {
    title: "Strategy 3: LVN Slicing (Momentum)",
    concept: "Exploiting low liquidity zones (valleys) where price moves rapidly.",
    entry: "Enter market order as price enters an LVN gap.",
    stop: "Place Stop Loss just outside the boundary of the LVN.",
    target: "Target the opposite boundary where the next HVN begins.",
    tips: "Price moves extremely fast in these zones. Use market orders or tight stops."
  }
];

const VolumeProfileHelpCenter: React.FC<VolumeProfileHelpCenterProps> = ({ onClose, initialTopic }) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'theory' | 'strategies' | 'faq' | 'glossary'>(
    (initialTopic as any) || 'overview'
  );
  const [searchQuery, setSearchQuery] = useState('');
  const [mode, setMode] = useState<'beginner' | 'advanced'>('beginner');

  // Handle direct tab changes if initialTopic changes
  React.useEffect(() => {
    if (initialTopic) {
      setActiveTab(initialTopic as any);
    }
  }, [initialTopic]);

  // Glossary search filter
  const filteredGlossary = useMemo(() => {
    if (!searchQuery) return GLOSSARY;
    const q = searchQuery.toLowerCase();
    return GLOSSARY.filter(item => 
      item.term.toLowerCase().includes(q) || 
      item.desc.toLowerCase().includes(q) ||
      item.adv.toLowerCase().includes(q)
    );
  }, [searchQuery]);

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-slate-900 border-l border-slate-850 shadow-2xl flex flex-col font-sans text-slate-100">
      
      {/* Drawer Header */}
      <div className="p-4 border-b border-slate-850 flex items-center justify-between bg-slate-950/40">
        <div className="flex items-center gap-2">
          <BookOpen className="text-brand-400" size={20} />
          <h3 className="font-display font-bold text-sm text-white uppercase tracking-wider">
            Volume Profile Learning Center
          </h3>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Beginner / Advanced Mode Toggle */}
          <div className="flex bg-slate-950 p-0.5 rounded border border-slate-800 text-[9px] font-bold font-mono">
            <button
              onClick={() => setMode('beginner')}
              className={`px-2 py-0.5 rounded transition-all ${
                mode === 'beginner' ? 'bg-brand-655 text-white' : 'text-slate-500 hover:text-slate-350'
              }`}
            >
              Beginner
            </button>
            <button
              onClick={() => setMode('advanced')}
              className={`px-2 py-0.5 rounded transition-all ${
                mode === 'advanced' ? 'bg-brand-655 text-white' : 'text-slate-500 hover:text-slate-355'
              }`}
            >
              Advanced
            </button>
          </div>
          
          <button 
            onClick={onClose}
            className="p-1 rounded bg-slate-800 hover:bg-slate-750 text-slate-400 hover:text-white transition-colors"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Search Input */}
      <div className="p-3 border-b border-slate-850 bg-slate-950/20 relative">
        <Search className="absolute left-6 top-1/2 -translate-y-1/2 text-slate-500" size={14} />
        <input
          type="text"
          placeholder="Search glossary, FAQ, or strategies..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500/50 transition-colors"
        />
      </div>

      {/* Tabs list */}
      <div className="flex overflow-x-auto border-b border-slate-850 bg-slate-950/30 p-1 gap-1 text-[10px] font-mono font-bold shrink-0">
        {[
          { id: 'overview', label: 'Overview', icon: BookOpen },
          { id: 'theory', label: 'Auction Theory', icon: Layers },
          { id: 'strategies', label: 'Strategies', icon: Zap },
          { id: 'faq', label: 'FAQ', icon: HelpCircle },
          { id: 'glossary', label: 'Glossary', icon: GraduationCap },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded transition-all shrink-0 ${
                activeTab === tab.id
                  ? 'bg-slate-800 text-brand-400 border border-slate-700/50'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Icon size={12} /> {tab.label}
            </button>
          );
        })}
      </div>

      {/* Panel Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5 text-xs leading-relaxed font-sans text-slate-300">
        
        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h4 className="text-white font-bold font-display text-sm">Understanding Volume Profile</h4>
            <p>
              {mode === 'beginner' 
                ? "Volume Profile is an advanced charting study that shows the trading volume of an asset at specific price levels rather than over time. Standard volume bars tell you WHEN trades happened; Volume Profile tells you WHERE they happened."
                : "Volume Profile represents a horizontal volume distribution (probability mass function) over price levels. By converting time-series transaction records into price-discrete blocks, it reveals auction liquidity nodes and key order block locations."
              }
            </p>
            
            <div className="p-4 bg-slate-950/40 border border-slate-800 rounded-xl space-y-2">
              <h5 className="font-bold text-white text-[11px] uppercase tracking-wider">Benefits</h5>
              <ul className="list-disc pl-4 space-y-1 text-slate-300">
                <li>Identify exact horizontal support and resistance lines.</li>
                <li>Understand where institutions are accumulating shares.</li>
                <li>Predict where price will trend quickly vs consolidate.</li>
              </ul>
            </div>

            <div className="p-4 bg-slate-950/40 border border-slate-800 rounded-xl space-y-2">
              <h5 className="font-bold text-white text-[11px] uppercase tracking-wider">Limitations</h5>
              <ul className="list-disc pl-4 space-y-1 text-slate-300">
                <li>Volume Profile is a lagging indicator of completed auctions.</li>
                <li>Requires sufficient transaction records to generate high-resolution price bins.</li>
                <li>Needs to be confirmed with other momentum tools (RSI, ADX, or EMA).</li>
              </ul>
            </div>
          </div>
        )}

        {/* AUCTION THEORY TAB */}
        {activeTab === 'theory' && (
          <div className="space-y-4">
            <h4 className="text-white font-bold font-display text-sm">Auction Market Theory (AMT)</h4>
            <p>
              AMT states that the financial markets act as a continuous double auction. The purpose of this auction is to facilitate trade by moving prices up and down until buyers and sellers find equilibrium (Fair Value).
            </p>

            <div className="space-y-3">
              <div className="flex gap-3 items-start border-l-2 border-brand-500 pl-3">
                <div>
                  <h5 className="font-bold text-white">Acceptance vs. Rejection</h5>
                  <p className="mt-1">
                    {mode === 'beginner'
                      ? "If price enters a zone and starts consolidating (trading sideways), the market has 'Accepted' that price as fair value. If price enters a zone and immediately bounces away, the market has 'Rejected' it."
                      : "Acceptance is indicated by sideways accumulation and high volume formation at a specific price bracket. Rejection is characterized by long candle wicks, swift momentum legs, and Low Volume Node (LVN) formations."
                    }
                  </p>
                </div>
              </div>

              <div className="flex gap-3 items-start border-l-2 border-brand-500 pl-3">
                <div>
                  <h5 className="font-bold text-white">Fair Value & Point of Control</h5>
                  <p className="mt-1">
                    The Point of Control (POC) represents the absolute fair value. When price moves too far away from the POC, it becomes overvalued (above VAH) or undervalued (below VAL), triggering initiative participants to pull price back.
                  </p>
                </div>
              </div>
            </div>

            {/* Simple CSS AMT Diagram */}
            <div className="mt-5 p-4 bg-slate-950 border border-slate-850 rounded-xl flex flex-col items-center">
              <span className="text-[10px] font-mono text-slate-500 mb-2">Market Auction Profile Diagram</span>
              <div className="w-full max-w-[200px] h-[120px] relative flex flex-col justify-between items-center text-[9px] font-mono font-bold text-slate-400">
                <div className="w-16 h-4 border border-emerald-500/20 bg-emerald-950/20 text-emerald-400 rounded flex items-center justify-center">VAH (Overvalued)</div>
                <div className="w-28 h-6 border border-yellow-500/20 bg-yellow-950/20 text-yellow-400 rounded flex items-center justify-center">POC (Fair Value Anchor)</div>
                <div className="w-16 h-4 border border-red-500/20 bg-red-950/20 text-red-400 rounded flex items-center justify-center">VAL (Undervalued)</div>
              </div>
            </div>
          </div>
        )}

        {/* STRATEGIES TAB */}
        {activeTab === 'strategies' && (
          <div className="space-y-4">
            <h4 className="text-white font-bold font-display text-sm">Institutional Trading Setups</h4>
            
            <div className="space-y-4">
              {STRATEGIES.map((strat, i) => (
                <div key={i} className="p-4 bg-slate-950/50 border border-slate-850 rounded-xl space-y-2">
                  <div className="flex items-center gap-1 text-xs font-bold text-brand-400">
                    <ArrowUpRight size={14} /> {strat.title}
                  </div>
                  <p className="text-[11px] font-medium text-slate-450">{strat.concept}</p>
                  <div className="grid grid-cols-3 gap-2 pt-1.5 text-[10px] font-mono">
                    <div className="p-1.5 bg-slate-900 border border-slate-800 rounded">
                      <span className="text-slate-500 block uppercase font-bold text-[8px]">Entry</span>
                      <span className="text-slate-200 font-extrabold">{strat.entry}</span>
                    </div>
                    <div className="p-1.5 bg-slate-900 border border-slate-800 rounded">
                      <span className="text-slate-500 block uppercase font-bold text-[8px]">Stop Loss</span>
                      <span className="text-red-400 font-extrabold">{strat.stop}</span>
                    </div>
                    <div className="p-1.5 bg-slate-900 border border-slate-800 rounded">
                      <span className="text-slate-500 block uppercase font-bold text-[8px]">Target</span>
                      <span className="text-emerald-400 font-extrabold">{strat.target}</span>
                    </div>
                  </div>
                  <div className="text-[9px] text-slate-500 italic mt-1 font-medium">Tip: {strat.tips}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* FAQ TAB */}
        {activeTab === 'faq' && (
          <div className="space-y-4">
            <h4 className="text-white font-bold font-display text-sm">Frequently Asked Questions</h4>
            <div className="space-y-4">
              {FAQS.map((faq, i) => (
                <div key={i} className="space-y-1.5">
                  <h5 className="font-bold text-white flex items-start gap-1.5">
                    <span className="text-brand-500 font-mono">Q.</span> {faq.q}
                  </h5>
                  <p className="pl-4 text-[11px] text-slate-400">{faq.a}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* GLOSSARY TAB */}
        {activeTab === 'glossary' && (
          <div className="space-y-4">
            <h4 className="text-white font-bold font-display text-sm">Terminology Dictionary</h4>
            <div className="space-y-3">
              {filteredGlossary.map((item, i) => (
                <div key={i} className="border-b border-slate-850/60 pb-2">
                  <h5 className="font-bold text-white font-mono">{item.term}</h5>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    {mode === 'beginner' ? item.desc : item.adv}
                  </p>
                </div>
              ))}
              {filteredGlossary.length === 0 && (
                <div className="text-slate-500 text-center py-6">No matching glossary terms found.</div>
              )}
            </div>
          </div>
        )}

      </div>
      
      {/* Keyboard Shortcuts Footer */}
      <div className="p-3.5 border-t border-slate-850 bg-slate-950/40 text-[10px] font-mono text-slate-500 flex justify-between gap-2 shrink-0">
        <span>[H] Toggle Help</span>
        <span>[L] Toggle Legend</span>
        <span>[R] Reset Chart</span>
        <span>[ESC] Close Help</span>
      </div>
    </div>
  );
};

export default VolumeProfileHelpCenter;
