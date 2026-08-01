import React from 'react';
import { motion } from 'framer-motion';
import { 
    Brain, 
    LineChart, 
    BarChart3, 
    Activity, 
    Grid3x3, 
    Scan, 
    Shield, 
    PieChart,
    ChevronRight,
    ArrowUpRight,
    TrendingUp,
    Gauge
} from 'lucide-react';

interface FeatureCardProps {
    icon: React.ComponentType<{ className?: string; size?: number }>;
    iconColor: string;
    iconBg: string;
    iconGlow: string;
    title: string;
    description: string;
    tags: string[];
    tagColor: string;
    className?: string;
    children?: React.ReactNode;
}

const FeatureCard: React.FC<FeatureCardProps> = ({
    icon: Icon,
    iconColor,
    iconBg,
    iconGlow,
    title,
    description,
    tags,
    tagColor,
    className = '',
    children
}) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            whileHover={{ 
                y: -6, 
                borderColor: 'rgba(96,165,250,0.3)',
                boxShadow: '0 20px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(96,165,250,0.25)' 
            }}
            transition={{ duration: 0.3 }}
            className={`bg-[#0E1425] border border-blue-400/15 rounded-[24px] p-6 lg:p-8 flex flex-col justify-between overflow-hidden relative group ${className}`}
        >
            {/* Card inner glow */}
            <div className="absolute inset-0 bg-gradient-to-b from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            
            <div className="relative z-10 flex flex-col h-full justify-between">
                <div>
                    {/* Icon wrapper */}
                    <div className={`inline-flex p-3.5 rounded-2xl ${iconBg} ${iconColor} ${iconGlow} mb-6 transition-all duration-300 group-hover:scale-105`}>
                        <Icon size={22} />
                    </div>

                    {/* Title */}
                    <h3 className="text-xl font-bold text-white mb-2.5 tracking-tight group-hover:text-blue-300 transition-colors">
                        {title}
                    </h3>

                    {/* Description */}
                    <p className="text-slate-400 text-sm leading-relaxed font-normal">
                        {description}
                    </p>

                    {/* Extra visuals/children */}
                    {children && (
                        <div className="mt-6">
                            {children}
                        </div>
                    )}
                </div>

                {/* Tags */}
                <div className="flex flex-wrap gap-2 mt-6">
                    {tags.map((tag, idx) => (
                        <span 
                            key={idx}
                            className={`text-[9px] uppercase tracking-widest font-black px-2.5 py-1 rounded-full border ${tagColor}`}
                        >
                            {tag}
                        </span>
                    ))}
                </div>
            </div>
        </motion.div>
    );
};

const LandingFeatures: React.FC = () => {
    return (
        <section id="features" className="relative py-32 bg-[#050816] overflow-hidden">
            {/* Background elements */}
            <div className="absolute inset-0 bg-grid-pattern opacity-100 pointer-events-none" />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60%] h-[60%] rounded-full bg-gradient-radial from-violet-600/5 to-transparent blur-[200px] pointer-events-none" />

            <div className="max-w-[1440px] mx-auto px-6 lg:px-20 relative z-10">
                {/* Section Header */}
                <div className="text-center max-w-3xl mx-auto mb-20">
                    <motion.span 
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-blue-400/30 bg-blue-500/10 text-blue-300 text-xs font-semibold uppercase tracking-widest mb-4"
                    >
                        <span>Everything You Need</span>
                    </motion.span>
                    
                    <motion.h2 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.1 }}
                        className="text-3xl sm:text-4xl lg:text-6xl font-serif font-black text-white leading-tight tracking-tight"
                    >
                        Built for Serious Investors
                    </motion.h2>
                    
                    <motion.p 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.2 }}
                        className="text-slate-400 text-base sm:text-lg mt-4 leading-relaxed font-normal"
                    >
                        Eight powerful modules, one unified platform. Everything professional investors need to research, analyze and manage investments.
                    </motion.p>
                </div>

                {/* Bento Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
                    
                    {/* Card 1: AI Committee (col-span-2) */}
                    <FeatureCard
                        icon={Brain}
                        iconColor="text-blue-400"
                        iconBg="bg-blue-500/10"
                        iconGlow="shadow-glow-blue"
                        title="AI Investment Committee"
                        description="Multiple AI agents debate every stock before producing a final investment verdict similar to an institutional investment committee."
                        tags={['Multi Agent', 'Swarm AI', 'Consensus']}
                        tagColor="text-blue-400 bg-blue-500/5 border-blue-500/10"
                        className="md:col-span-2"
                    >
                        {/* Visual Debate Simulator */}
                        <div className="bg-[#050816] border border-blue-400/10 rounded-2xl p-4 flex flex-col gap-3">
                            <div className="flex items-center justify-between text-[10px] text-slate-500">
                                <span className="font-mono">VERDICT DEBATE IN PROGRESS</span>
                                <span className="text-emerald-400 font-bold">88% CONSENSUS</span>
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="flex items-center gap-1.5 bg-blue-500/10 border border-blue-500/20 px-2 py-1 rounded-lg">
                                    <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
                                    <span className="text-[10px] text-blue-300 font-bold uppercase">Macro Agent</span>
                                </div>
                                <span className="text-slate-500 text-xs">→</span>
                                <div className="flex items-center gap-1.5 bg-violet-500/10 border border-violet-500/20 px-2 py-1 rounded-lg">
                                    <div className="w-2 h-2 rounded-full bg-violet-400" />
                                    <span className="text-[10px] text-violet-300 font-bold uppercase">Technical Swarm</span>
                                </div>
                                <span className="text-slate-500 text-xs">→</span>
                                <div className="flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/20 px-2 py-1 rounded-lg">
                                    <div className="w-2 h-2 rounded-full bg-emerald-400" />
                                    <span className="text-[10px] text-emerald-300 font-bold uppercase">Consensus Verdict</span>
                                </div>
                            </div>
                        </div>
                    </FeatureCard>

                    {/* Card 2: Technical Analysis (col-span-1) */}
                    <FeatureCard
                        icon={LineChart}
                        iconColor="text-violet-400"
                        iconBg="bg-violet-500/10"
                        iconGlow="shadow-glow-purple"
                        title="Technical Analysis"
                        description="50+ indicators including RSI, MACD, EMA, VWAP, ATR, Bollinger Bands, and Supertrend recalculated in real time."
                        tags={['RSI', 'MACD', 'BOLLINGER', 'VWAP']}
                        tagColor="text-violet-400 bg-violet-500/5 border-violet-500/10"
                        className="md:col-span-1"
                    >
                        <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="bg-[#050816] p-2 rounded-lg border border-blue-400/5 flex justify-between">
                                <span className="text-slate-500">RSI (14)</span>
                                <span className="text-emerald-400 font-bold">64.5</span>
                            </div>
                            <div className="bg-[#050816] p-2 rounded-lg border border-blue-400/5 flex justify-between">
                                <span className="text-slate-500">MACD</span>
                                <span className="text-emerald-400 font-bold">Bullish</span>
                            </div>
                            <div className="bg-[#050816] p-2 rounded-lg border border-blue-400/5 flex justify-between">
                                <span className="text-slate-500">VWAP</span>
                                <span className="text-rose-400 font-bold">Below</span>
                            </div>
                            <div className="bg-[#050816] p-2 rounded-lg border border-blue-400/5 flex justify-between">
                                <span className="text-slate-500">200 DMA</span>
                                <span className="text-emerald-400 font-bold">Above</span>
                            </div>
                        </div>
                    </FeatureCard>

                    {/* Card 3: Fundamental Analysis */}
                    <FeatureCard
                        icon={BarChart3}
                        iconColor="text-emerald-400"
                        iconBg="bg-emerald-500/10"
                        iconGlow="shadow-glow-emerald"
                        title="Fundamental Analysis"
                        description="Deep scans of financial statements, balance sheets, and key ratios including PE, PB, ROE, ROCE, and Dividend Yield."
                        tags={['PE/PB', 'ROE', 'ROCE', 'REVENUE']}
                        tagColor="text-emerald-400 bg-emerald-500/5 border-emerald-500/10"
                    />

                    {/* Card 4: Market Breadth */}
                    <FeatureCard
                        icon={Activity}
                        iconColor="text-amber-400"
                        iconBg="bg-amber-500/10"
                        iconGlow="shadow-glow-amber"
                        title="Market Breadth"
                        description="Track Advance-Decline ratios, sector rotations, volume spikes, and index trends to trade with the overall market trend."
                        tags={['A/D Ratio', 'Volume', 'Sectors']}
                        tagColor="text-amber-400 bg-amber-500/5 border-amber-500/10"
                    />

                    {/* Card 5: Sector Heatmap */}
                    <FeatureCard
                        icon={Grid3x3}
                        iconColor="text-blue-400"
                        iconBg="bg-blue-500/10"
                        iconGlow="shadow-glow-blue"
                        title="Sector Heatmap"
                        description="Interactive live sector visualization to quickly identify leading and lagging sectors and flow of capital."
                        tags={['Live', 'Interactive', 'Sectors']}
                        tagColor="text-blue-400 bg-blue-500/5 border-blue-500/10"
                    >
                        {/* Mini Heatmap Grid */}
                        <div className="grid grid-cols-4 gap-1 h-12">
                            <div className="bg-emerald-500/80 rounded" />
                            <div className="bg-emerald-500/50 rounded" />
                            <div className="bg-rose-500/80 rounded" />
                            <div className="bg-emerald-500/30 rounded" />
                            <div className="bg-rose-500/40 rounded" />
                            <div className="bg-emerald-500/70 rounded" />
                            <div className="bg-rose-500/20 rounded" />
                            <div className="bg-emerald-500/60 rounded" />
                        </div>
                    </FeatureCard>

                    {/* Card 6: Swing Trading Scanner (col-span-2) */}
                    <FeatureCard
                        icon={Scan}
                        iconColor="text-violet-400"
                        iconBg="bg-violet-500/10"
                        iconGlow="shadow-glow-purple"
                        title="Swing Trading Scanner"
                        description="AI scans thousands of stocks in real-time to identify high-probability breakouts, support bounces, and momentum setups."
                        tags={['Auto Scan', 'High Probability', 'AI Filter']}
                        tagColor="text-violet-400 bg-violet-500/5 border-violet-500/10"
                        className="md:col-span-2"
                    >
                        <div className="bg-[#050816] border border-blue-400/10 rounded-2xl overflow-hidden text-xs">
                            <table className="w-full text-left">
                                <thead>
                                    <tr className="border-b border-blue-400/10 bg-blue-400/5 text-slate-500 text-[10px]">
                                        <th className="p-2">SYMBOL</th>
                                        <th className="p-2">BREAKOUT TYPE</th>
                                        <th className="p-2 text-right">VOL RATIO</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr className="border-b border-blue-400/5 text-slate-300">
                                        <td className="p-2 font-bold">RELIANCE</td>
                                        <td className="p-2 text-emerald-400">52W Breakout</td>
                                        <td className="p-2 text-right font-bold">3.2x</td>
                                    </tr>
                                    <tr className="text-slate-300">
                                        <td className="p-2 font-bold">TCS</td>
                                        <td className="p-2 text-emerald-400">MA Crossover</td>
                                        <td className="p-2 text-right font-bold">2.5x</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </FeatureCard>

                    {/* Card 7: Risk Management */}
                    <FeatureCard
                        icon={Shield}
                        iconColor="text-red-400"
                        iconBg="bg-red-500/10"
                        iconGlow="shadow-glow-red"
                        title="Risk Management"
                        description="Automatic position sizing calculators, optimal Stop Loss/Target targets, and custom Risk-Reward ratio managers."
                        tags={['Stop Loss', 'R:R', 'Position Size']}
                        tagColor="text-red-400 bg-red-500/5 border-red-500/10"
                    />

                    {/* Card 8: Portfolio Analytics (col-span-3) */}
                    <FeatureCard
                        icon={PieChart}
                        iconColor="text-emerald-400"
                        iconBg="bg-emerald-500/10"
                        iconGlow="shadow-glow-emerald"
                        title="Portfolio Analytics"
                        description="Analyze your portfolio performance, sector allocation weights, Sharpe Ratio risk, and returns performance compared against standard benchmarks."
                        tags={['Performance', 'Allocation', 'Returns', 'Risk']}
                        tagColor="text-emerald-400 bg-emerald-500/5 border-emerald-500/10"
                        className="md:col-span-3"
                    >
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                            <div className="bg-[#050816] p-3 rounded-xl border border-blue-400/5">
                                <span className="text-[10px] text-slate-500 block uppercase tracking-wider">Total Stocks</span>
                                <span className="text-lg font-black text-white mt-1 block">32 Constituent</span>
                            </div>
                            <div className="bg-[#050816] p-3 rounded-xl border border-blue-400/5">
                                <span className="text-[10px] text-slate-500 block uppercase tracking-wider">Annualized CAGR</span>
                                <span className="text-lg font-black text-emerald-400 mt-1 block">18.4%</span>
                            </div>
                            <div className="bg-[#050816] p-3 rounded-xl border border-blue-400/5">
                                <span className="text-[10px] text-slate-500 block uppercase tracking-wider">Sharpe Ratio</span>
                                <span className="text-lg font-black text-white mt-1 block">1.46 Low Risk</span>
                            </div>
                            <div className="bg-[#050816] p-3 rounded-xl border border-blue-400/5">
                                <span className="text-[10px] text-slate-500 block uppercase tracking-wider">Win Rate</span>
                                <span className="text-lg font-black text-emerald-400 mt-1 block">71.2%</span>
                            </div>
                        </div>
                    </FeatureCard>

                </div>
            </div>
        </section>
    );
};

export default LandingFeatures;
