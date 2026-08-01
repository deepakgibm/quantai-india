import React from 'react';
import { motion } from 'framer-motion';
import { 
    Terminal, 
    Play, 
    Sparkles, 
    Bot, 
    TrendingUp, 
    ShieldCheck, 
    Zap,
    Code,
    Activity,
    LineChart
} from 'lucide-react';

const LandingDashboardPreview: React.FC = () => {
    return (
        <section className="relative py-32 bg-[#050816] overflow-hidden">
            {/* Background grids and shapes */}
            <div className="absolute inset-0 bg-grid-pattern opacity-100 pointer-events-none" />
            <div className="absolute top-[10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-gradient-radial from-blue-500/10 to-transparent blur-[160px] pointer-events-none" />
            
            <div className="max-w-[1440px] mx-auto px-6 lg:px-20 relative z-10">
                {/* Section Header */}
                <div className="text-center max-w-3xl mx-auto mb-20">
                    <motion.span 
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-blue-400/30 bg-blue-500/10 text-blue-300 text-xs font-semibold uppercase tracking-widest mb-4"
                    >
                        <span>Platform Interface</span>
                    </motion.span>
                    
                    <motion.h2 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.1 }}
                        className="text-3xl sm:text-4xl lg:text-5xl font-serif font-bold text-white tracking-tight"
                    >
                        Unified Multi-Agent Workspace
                    </motion.h2>
                    
                    <motion.p 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.2 }}
                        className="text-slate-400 text-base sm:text-lg mt-4 leading-relaxed font-normal"
                    >
                        Interact with your investment swarm, build strategies using plain English, monitor live breakout scanners, and manage risk parameters from a single interface.
                    </motion.p>
                </div>

                {/* Dashboard Mockup (interactive look) */}
                <motion.div 
                    initial={{ opacity: 0, y: 40 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.8 }}
                    className="relative w-full max-w-[1100px] mx-auto"
                >
                    {/* Shadow Glow */}
                    <div className="absolute -inset-2 bg-gradient-to-r from-blue-500/25 to-violet-500/25 rounded-3xl blur-xl opacity-60 -z-10" />

                    {/* Window Frame */}
                    <div className="bg-[#0E1425] border border-blue-400/20 rounded-3xl overflow-hidden shadow-[0_24px_60px_rgba(0,0,0,0.6)]">
                        
                        {/* Title Bar */}
                        <div className="bg-[#050816] px-6 py-4 flex items-center justify-between border-b border-blue-400/10">
                            <div className="flex items-center gap-2">
                                <span className="w-3.5 h-3.5 rounded-full bg-rose-500/60" />
                                <span className="w-3.5 h-3.5 rounded-full bg-yellow-500/60" />
                                <span className="w-3.5 h-3.5 rounded-full bg-emerald-500/60" />
                            </div>
                            <div className="bg-white/[0.03] border border-blue-400/10 rounded-full px-8 py-1.5 text-xs text-slate-400 font-mono tracking-wide w-96 text-center select-none">
                                workspace.quantai.in/session/9201a
                            </div>
                            <div className="w-14" />
                        </div>

                        {/* Layout Inner Grid */}
                        <div className="grid grid-cols-1 lg:grid-cols-4 min-h-[500px]">
                            
                            {/* Left Sidebar Menu */}
                            <div className="bg-[#050816]/50 p-6 border-r border-blue-400/10 flex flex-col gap-6">
                                <div className="text-[10px] font-black tracking-widest text-slate-500 uppercase">CORE MODULES</div>
                                <div className="space-y-1">
                                    <div className="flex items-center gap-3 px-3 py-2 bg-blue-500/10 border border-blue-500/20 rounded-xl text-xs font-bold text-white cursor-pointer">
                                        <Bot size={16} className="text-blue-400" />
                                        <span>Swarm Workspace</span>
                                    </div>
                                    <div className="flex items-center gap-3 px-3 py-2 text-slate-400 hover:text-white rounded-xl text-xs font-medium cursor-pointer transition-colors">
                                        <LineChart size={16} />
                                        <span>Sector Heatmap</span>
                                    </div>
                                    <div className="flex items-center gap-3 px-3 py-2 text-slate-400 hover:text-white rounded-xl text-xs font-medium cursor-pointer transition-colors">
                                        <Zap size={16} />
                                        <span>Momentum Alerts</span>
                                    </div>
                                    <div className="flex items-center gap-3 px-3 py-2 text-slate-400 hover:text-white rounded-xl text-xs font-medium cursor-pointer transition-colors">
                                        <Activity size={16} />
                                        <span>Swing Scanner</span>
                                    </div>
                                </div>

                                <div className="h-px bg-blue-400/10 my-1" />

                                <div className="text-[10px] font-black tracking-widest text-slate-500 uppercase">STRATEGY CONTROL</div>
                                <div className="space-y-1">
                                    <div className="flex items-center gap-3 px-3 py-2 text-slate-400 hover:text-white rounded-xl text-xs font-medium cursor-pointer transition-colors">
                                        <Code size={16} />
                                        <span>Algo Builder</span>
                                    </div>
                                    <div className="flex items-center gap-3 px-3 py-2 text-slate-400 hover:text-white rounded-xl text-xs font-medium cursor-pointer transition-colors">
                                        <ShieldCheck size={16} />
                                        <span>Risk Manager</span>
                                    </div>
                                </div>
                            </div>

                            {/* Main Content Area (3 cols) */}
                            <div className="lg:col-span-3 p-6 flex flex-col gap-6">
                                
                                {/* Inner Top Header */}
                                <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-blue-400/10">
                                    <div>
                                        <h4 className="text-sm font-black text-white uppercase tracking-tight">Interactive AI Swarm</h4>
                                        <p className="text-[11px] text-slate-500">Ask consensus agents to analyze any stock or draft a backtest strategy</p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="flex -space-x-1.5">
                                            <span className="w-6 h-6 rounded-full bg-blue-500 border border-[#0E1425] flex items-center justify-center text-[8px] font-black">TA</span>
                                            <span className="w-6 h-6 rounded-full bg-violet-500 border border-[#0E1425] flex items-center justify-center text-[8px] font-black">FA</span>
                                            <span className="w-6 h-6 rounded-full bg-emerald-500 border border-[#0E1425] flex items-center justify-center text-[8px] font-black">MA</span>
                                        </div>
                                        <span className="text-[10px] font-bold text-slate-400">9 Active Swarms</span>
                                    </div>
                                </div>

                                {/* Chat window preview */}
                                <div className="flex-1 bg-[#050816] rounded-2xl border border-blue-400/5 p-4 flex flex-col justify-between min-h-[300px]">
                                    <div className="space-y-4">
                                        {/* User message */}
                                        <div className="flex gap-3">
                                            <div className="w-7 h-7 rounded-xl bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-[9px] font-black text-blue-300">USER</div>
                                            <div className="flex-1 bg-white/[0.02] border border-blue-400/5 rounded-xl p-3.5">
                                                <p className="text-xs text-slate-300">Compare Tata Motors and Mahindra & Mahindra. Tell me which one has better technical setup and consensus score.</p>
                                            </div>
                                        </div>

                                        {/* Agent Message */}
                                        <div className="flex gap-3">
                                            <div className="w-7 h-7 rounded-xl bg-violet-500/15 border border-violet-500/30 flex items-center justify-center text-[9px] font-black text-violet-300">AI</div>
                                            <div className="flex-1 bg-white/[0.02] border border-blue-400/5 rounded-xl p-3.5 space-y-3">
                                                <p className="text-xs text-slate-300 leading-relaxed">
                                                    Analysis completed by the Swarm Consensus. Here is the direct breakdown:
                                                </p>
                                                
                                                <div className="grid grid-cols-2 gap-4">
                                                    <div className="border border-blue-500/20 bg-blue-500/5 rounded-lg p-3">
                                                        <div className="flex justify-between items-center text-[10px]">
                                                            <span className="font-bold text-white">TATA MOTORS</span>
                                                            <span className="text-emerald-400 font-bold">BULLISH (92%)</span>
                                                        </div>
                                                        <span className="text-[9px] text-slate-400 block mt-1">TA: High volume bounce off 200 DMA. FA: ROE increased to 22.1%.</span>
                                                    </div>
                                                    <div className="border border-violet-500/20 bg-violet-500/5 rounded-lg p-3">
                                                        <div className="flex justify-between items-center text-[10px]">
                                                            <span className="font-bold text-white">M&M</span>
                                                            <span className="text-yellow-400 font-bold">NEUTRAL (64%)</span>
                                                        </div>
                                                        <span className="text-[9px] text-slate-400 block mt-1">TA: Trading in narrow consolidative zone. FA: Valuations stretched.</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Console Box input at bottom */}
                                    <div className="mt-4 bg-[#0E1425] border border-blue-400/15 rounded-xl p-3 flex items-center justify-between">
                                        <div className="flex items-center gap-2.5">
                                            <Terminal size={14} className="text-slate-500" />
                                            <span className="text-xs text-slate-400 font-medium">Query active swarm (e.g. \"Evaluate RELIANCE target...\")</span>
                                        </div>
                                        <button className="bg-gradient-to-r from-blue-500 to-violet-600 px-3 py-1.5 rounded-lg text-[10px] font-black text-white uppercase tracking-wider flex items-center gap-1 shadow-lg shadow-blue-500/15">
                                            Execute <Play size={10} className="fill-white" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>
        </section>
    );
};

export default LandingDashboardPreview;
