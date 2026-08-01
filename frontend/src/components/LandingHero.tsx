import React from 'react';
import { Page } from '../types';
import { ChevronRight, Play, Sparkles, CheckCircle2, TrendingUp, ArrowUpRight, Cpu, Layers } from 'lucide-react';
import { motion } from 'framer-motion';

interface LandingHeroProps {
    onNavigate: (page: Page) => void;
}

const LandingHero: React.FC<LandingHeroProps> = ({ onNavigate }) => {
    return (
        <section className="relative min-h-screen pt-32 pb-24 overflow-hidden bg-[#050816] flex flex-col justify-center">
            {/* Background elements */}
            <div className="absolute inset-0 bg-grid-pattern opacity-100 pointer-events-none" />
            
            {/* Radial gradients for high-end SaaS feel */}
            <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] rounded-full bg-gradient-radial from-blue-500/10 to-transparent blur-[160px] pointer-events-none" />
            <div className="absolute bottom-[10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-gradient-radial from-violet-600/10 to-transparent blur-[160px] pointer-events-none" />

            <div className="max-w-[1440px] mx-auto px-6 lg:px-20 w-full relative z-10">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
                    
                    {/* Left Column: Heading and CTAs */}
                    <motion.div 
                        initial="hidden"
                        animate="visible"
                        variants={{
                            hidden: { opacity: 0 },
                            visible: {
                                opacity: 1,
                                transition: {
                                    staggerChildren: 0.15
                                }
                            }
                        }}
                        className="flex flex-col space-y-8 text-left"
                    >
                        {/* AI Badge */}
                        <motion.div 
                            variants={{
                                hidden: { opacity: 0, y: 15 },
                                visible: { opacity: 1, y: 0 }
                            }}
                            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-blue-400/20 bg-blue-500/5 text-blue-300 text-xs font-semibold w-fit tracking-wide"
                        >
                            <Sparkles size={14} className="text-blue-400 animate-pulse" />
                            <span>AI Powered Investment Research</span>
                        </motion.div>

                        {/* Title */}
                        <motion.h1 
                            variants={{
                                hidden: { opacity: 0, y: 20 },
                                visible: { opacity: 1, y: 0 }
                            }}
                            className="text-4xl sm:text-5xl lg:text-7xl font-serif font-black leading-[1.1] text-white tracking-tight"
                        >
                            Professional AI <br />
                            Stock Analysis for <br />
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-violet-400 to-emerald-400">
                                Serious Investors
                            </span>
                        </motion.h1>

                        {/* Description */}
                        <motion.p 
                            variants={{
                                hidden: { opacity: 0, y: 20 },
                                visible: { opacity: 1, y: 0 }
                            }}
                            className="text-slate-400 text-base sm:text-lg lg:text-xl leading-relaxed max-w-xl font-normal"
                        >
                            Analyze thousands of Indian stocks using institutional-grade AI, technical indicators, fundamental analysis, and multi-agent investment intelligence.
                        </motion.p>

                        {/* CTAs */}
                        <motion.div 
                            variants={{
                                hidden: { opacity: 0, y: 20 },
                                visible: { opacity: 1, y: 0 }
                            }}
                            className="flex flex-col sm:flex-row items-center gap-4 pt-2"
                        >
                            <button
                                onClick={() => onNavigate(Page.SIGNUP)}
                                className="w-full sm:w-auto px-8 py-4 rounded-full bg-gradient-to-r from-blue-500 to-violet-600 hover:from-blue-600 hover:to-violet-700 text-white font-bold text-base shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all duration-300 flex items-center justify-center gap-2 group"
                            >
                                Start Free Trial
                                <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
                            </button>
                            <button
                                onClick={() => onNavigate(Page.LOGIN)}
                                className="w-full sm:w-auto px-8 py-4 rounded-full bg-white/[0.03] border border-blue-400/20 hover:bg-white/[0.08] text-slate-200 hover:text-white font-bold text-base transition-all duration-300 flex items-center justify-center gap-2"
                            >
                                <Play size={16} className="text-blue-400fill-blue-400" />
                                Live Demo
                            </button>
                        </motion.div>

                        {/* Trust Badges */}
                        <motion.div 
                            variants={{
                                hidden: { opacity: 0, y: 20 },
                                visible: { opacity: 1, y: 0 }
                            }}
                            className="grid grid-cols-2 sm:flex sm:items-center gap-x-6 gap-y-3 pt-6 border-t border-blue-400/10"
                        >
                            <div className="flex items-center gap-2 text-sm text-slate-400">
                                <CheckCircle2 size={16} className="text-emerald-500" />
                                <span>Real-time Data</span>
                            </div>
                            <div className="flex items-center gap-2 text-sm text-slate-400">
                                <CheckCircle2 size={16} className="text-emerald-500" />
                                <span>AI Powered</span>
                            </div>
                            <div className="flex items-center gap-2 text-sm text-slate-400">
                                <CheckCircle2 size={16} className="text-emerald-500" />
                                <span>NIFTY 500 Coverage</span>
                            </div>
                            <div className="flex items-center gap-2 text-sm text-slate-400">
                                <CheckCircle2 size={16} className="text-emerald-500" />
                                <span>Institutional Research</span>
                            </div>
                        </motion.div>
                    </motion.div>

                    {/* Right Column: Premium Dashboard Preview */}
                    <motion.div 
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.8, delay: 0.2 }}
                        className="relative w-full aspect-[4/3] lg:aspect-auto lg:h-[550px] flex items-center justify-center"
                    >
                        {/* Glow Behind */}
                        <div className="absolute inset-0 bg-gradient-to-tr from-blue-500/10 to-violet-500/10 blur-3xl opacity-50 rounded-full" />

                        {/* Main mock container (Floating) */}
                        <div className="relative w-full max-w-[520px] bg-[#0E1425] border border-blue-400/20 rounded-3xl p-5 shadow-[0_20px_50px_rgba(0,0,0,0.5)] overflow-hidden animate-float">
                            
                            {/* Dashboard Header Mock */}
                            <div className="flex justify-between items-center pb-4 mb-4 border-b border-blue-400/10">
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full bg-red-500/60" />
                                    <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                                    <div className="w-3 h-3 rounded-full bg-green-500/60" />
                                </div>
                                <span className="text-[10px] font-mono tracking-widest text-slate-500 uppercase">QuantAI Dashboard v2.0</span>
                            </div>

                            {/* Mini Stock Chart Visual */}
                            <div className="bg-[#050816] rounded-2xl p-4 border border-blue-400/5">
                                <div className="flex justify-between items-center mb-3">
                                    <div>
                                        <span className="text-xs font-bold text-slate-400">RELIANCE INDUSTRIES</span>
                                        <div className="flex items-baseline gap-2 mt-0.5">
                                            <span className="text-lg font-black text-white">₹2,847.35</span>
                                            <span className="text-[10px] font-bold text-emerald-400">+2.45%</span>
                                        </div>
                                    </div>
                                    <div className="px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 rounded text-[9px] font-bold text-emerald-400 uppercase">
                                        Active Feed
                                    </div>
                                </div>
                                
                                {/* SVG Chart Line */}
                                <svg viewBox="0 0 400 120" className="w-full h-24 overflow-visible">
                                    <defs>
                                        <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor="#10b981" stopOpacity="0.25"/>
                                            <stop offset="100%" stopColor="#10b981" stopOpacity="0.0"/>
                                        </linearGradient>
                                    </defs>
                                    {/* Grid Lines */}
                                    <line x1="0" y1="30" x2="400" y2="30" stroke="#ffffff" strokeOpacity="0.03" strokeWidth="1" />
                                    <line x1="0" y1="60" x2="400" y2="60" stroke="#ffffff" strokeOpacity="0.03" strokeWidth="1" />
                                    <line x1="0" y1="90" x2="400" y2="90" stroke="#ffffff" strokeOpacity="0.03" strokeWidth="1" />
                                    {/* Area Fill */}
                                    <path d="M 0 110 Q 40 85 80 95 T 160 60 T 240 70 T 320 30 T 400 15 L 400 120 L 0 120 Z" fill="url(#chartGradient)" />
                                    {/* Stroke Line */}
                                    <path d="M 0 110 Q 40 85 80 95 T 160 60 T 240 70 T 320 30 T 400 15" fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" />
                                    {/* Glowing point */}
                                    <circle cx="400" cy="15" r="4" fill="#10b981" className="animate-ping" />
                                    <circle cx="400" cy="15" r="3.5" fill="#10b981" />
                                </svg>
                            </div>

                            {/* Grid below */}
                            <div className="grid grid-cols-2 gap-4 mt-4">
                                <div className="bg-[#050816] rounded-2xl p-4 border border-blue-400/5 flex flex-col justify-between">
                                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Sector Performance</span>
                                    <div className="space-y-2 mt-2">
                                        <div className="flex justify-between items-center text-xs">
                                            <span className="text-slate-400">Nifty Energy</span>
                                            <span className="text-emerald-400 font-bold">+1.8%</span>
                                        </div>
                                        <div className="flex justify-between items-center text-xs">
                                            <span className="text-slate-400">Nifty IT</span>
                                            <span className="text-emerald-400 font-bold">+1.2%</span>
                                        </div>
                                        <div className="flex justify-between items-center text-xs">
                                            <span className="text-slate-400">Nifty Bank</span>
                                            <span className="text-rose-400 font-bold">-0.4%</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="bg-[#050816] rounded-2xl p-4 border border-blue-400/5 flex flex-col justify-between">
                                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Swarm Consensus</span>
                                    <div className="flex items-center gap-3 mt-3">
                                        <div className="flex -space-x-2">
                                            <div className="w-7 h-7 rounded-full bg-blue-500 border border-[#0E1425] flex items-center justify-center text-[9px] font-bold">A1</div>
                                            <div className="w-7 h-7 rounded-full bg-purple-500 border border-[#0E1425] flex items-center justify-center text-[9px] font-bold">A2</div>
                                            <div className="w-7 h-7 rounded-full bg-emerald-500 border border-[#0E1425] flex items-center justify-center text-[9px] font-bold">A3</div>
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">Bullish</span>
                                            <span className="text-[9px] text-slate-400">8/9 Agents Agree</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* OVERLAID CARD 1: BUY Signal (Top Right) */}
                        <motion.div 
                            initial={{ x: 60, y: -40, opacity: 0 }}
                            animate={{ x: 0, y: 0, opacity: 1 }}
                            transition={{ delay: 0.6, duration: 0.6 }}
                            className="absolute top-4 right-[-10px] bg-[#0E1425]/95 border border-emerald-500/30 rounded-2xl p-4 shadow-xl max-w-[170px] backdrop-blur-md flex flex-col gap-1.5 animate-float-delayed"
                        >
                            <div className="flex items-center justify-between">
                                <span className="text-[9px] font-extrabold text-slate-500 uppercase tracking-widest">Active Call</span>
                                <span className="flex h-2 w-2 relative">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                                </span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="bg-emerald-500/10 p-1.5 rounded-lg text-emerald-400">
                                    <TrendingUp size={16} />
                                </div>
                                <div>
                                    <h4 className="text-xs font-black text-white leading-tight">BUY Signal</h4>
                                    <span className="text-[8px] text-slate-400 font-medium">Confidence: 94%</span>
                                </div>
                            </div>
                            <div className="h-px bg-blue-400/10 my-1" />
                            <div className="flex justify-between items-center text-[10px]">
                                <span className="text-slate-400">Risk Profile:</span>
                                <span className="text-yellow-400 font-bold">Medium</span>
                            </div>
                        </motion.div>

                        {/* OVERLAID CARD 2: Portfolio Metric (Bottom Left) */}
                        <motion.div 
                            initial={{ x: -60, y: 40, opacity: 0 }}
                            animate={{ x: 0, y: 0, opacity: 1 }}
                            transition={{ delay: 0.8, duration: 0.6 }}
                            className="absolute bottom-6 left-[-20px] bg-[#0E1425]/95 border border-blue-400/30 rounded-2xl p-4 shadow-xl max-w-[190px] backdrop-blur-md flex flex-col gap-1.5"
                        >
                            <span className="text-[9px] font-extrabold text-slate-500 uppercase tracking-widest">Performance Metrics</span>
                            <div className="flex items-baseline gap-2">
                                <span className="text-xl font-black text-white">+8.2%</span>
                                <span className="text-[10px] text-emerald-400 font-bold flex items-center gap-0.5">
                                    <ArrowUpRight size={10} /> vs NIFTY 50
                                </span>
                            </div>
                            <span className="text-[9px] text-slate-400 font-medium">Calculated across live active model portfolios</span>
                            <div className="flex gap-1.5 mt-1">
                                <div className="h-3 w-4/12 bg-blue-500/20 border border-blue-500/30 rounded-sm" />
                                <div className="h-3 w-5/12 bg-violet-500/20 border border-violet-500/30 rounded-sm" />
                                <div className="h-3 w-3/12 bg-emerald-500/20 border border-emerald-500/30 rounded-sm" />
                            </div>
                        </motion.div>
                    </motion.div>
                </div>
            </div>

            {/* Scrolling Ticker Bar at bottom */}
            <div className="absolute bottom-0 left-0 right-0 py-4 bg-[#050816] border-y border-blue-400/10 overflow-hidden w-full select-none">
                <div className="flex whitespace-nowrap animate-ticker gap-16 min-w-full">
                    <div className="flex items-center gap-12 font-mono text-xs text-slate-500">
                        <span>NIFTY 50: <span className="text-emerald-400 font-bold">24,521.15 (+1.14%)</span></span>
                        <span>BANK NIFTY: <span className="text-emerald-400 font-bold">52,341.60 (+0.85%)</span></span>
                        <span>RELIANCE: <span className="text-emerald-400 font-bold">₹2,847.35 (+2.45%)</span></span>
                        <span>TCS: <span className="text-emerald-400 font-bold">₹4,123.00 (+1.90%)</span></span>
                        <span>HDFC BANK: <span className="text-rose-400 font-bold">₹1,689.50 (-0.35%)</span></span>
                        <span>INFOSYS: <span className="text-emerald-400 font-bold">₹1,745.20 (+1.15%)</span></span>
                        <span>ICICI BANK: <span className="text-rose-400 font-bold">₹1,215.10 (-0.12%)</span></span>
                    </div>
                    {/* Repeated list for continuous scrolling */}
                    <div className="flex items-center gap-12 font-mono text-xs text-slate-500">
                        <span>NIFTY 50: <span className="text-emerald-400 font-bold">24,521.15 (+1.14%)</span></span>
                        <span>BANK NIFTY: <span className="text-emerald-400 font-bold">52,341.60 (+0.85%)</span></span>
                        <span>RELIANCE: <span className="text-emerald-400 font-bold">₹2,847.35 (+2.45%)</span></span>
                        <span>TCS: <span className="text-emerald-400 font-bold">₹4,123.00 (+1.90%)</span></span>
                        <span>HDFC BANK: <span className="text-rose-400 font-bold">₹1,689.50 (-0.35%)</span></span>
                        <span>INFOSYS: <span className="text-emerald-400 font-bold">₹1,745.20 (+1.15%)</span></span>
                        <span>ICICI BANK: <span className="text-rose-400 font-bold">₹1,215.10 (-0.12%)</span></span>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default LandingHero;
