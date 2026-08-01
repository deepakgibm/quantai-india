import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Award, Activity, ShieldAlert, ArrowUpRight } from 'lucide-react';

const LandingPerformanceMetrics: React.FC = () => {
    return (
        <section id="metrics" className="relative py-32 bg-[#050816] overflow-hidden">
            {/* Background elements */}
            <div className="absolute inset-0 bg-grid-pattern opacity-100 pointer-events-none" />
            <div className="absolute bottom-[10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-gradient-radial from-blue-500/10 to-transparent blur-[160px] pointer-events-none" />

            <div className="max-w-[1440px] mx-auto px-6 lg:px-20 relative z-10">
                {/* Section Header */}
                <div className="text-center max-w-3xl mx-auto mb-20">
                    <motion.span 
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-emerald-400/30 bg-emerald-500/10 text-emerald-300 text-xs font-semibold uppercase tracking-widest mb-4"
                    >
                        <span>Model Verification</span>
                    </motion.span>
                    
                    <motion.h2 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.1 }}
                        className="text-3xl sm:text-4xl lg:text-5xl font-serif font-bold text-white tracking-tight"
                    >
                        Engineered for Alpha
                    </motion.h2>
                    
                    <motion.p 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.2 }}
                        className="text-slate-400 text-base sm:text-lg mt-4 leading-relaxed font-normal"
                    >
                        Consistently outperforming benchmarks through rigorous statistical validation and multi-agent risk constraints.
                    </motion.p>
                </div>

                {/* Grid container */}
                <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 items-center">
                    
                    {/* Left: 4 Metric Cards (col-span-2) */}
                    <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
                        
                        {/* Metric 1 */}
                        <motion.div 
                            initial={{ opacity: 0, scale: 0.95 }}
                            whileInView={{ opacity: 1, scale: 1 }}
                            viewport={{ once: true }}
                            className="bg-[#0E1425] border border-blue-400/10 hover:border-blue-400/25 p-6 rounded-2xl flex flex-col justify-between"
                        >
                            <div>
                                <TrendingUp className="text-emerald-400 mb-4" size={20} />
                                <span className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Cumulative Return</span>
                                <h4 className="text-3xl font-black text-white mt-1">+342.1%</h4>
                            </div>
                            <span className="text-xs text-slate-400 mt-4 block border-t border-slate-800 pt-3">Consensus Swarm (vs Nifty +112%)</span>
                        </motion.div>

                        {/* Metric 2 */}
                        <motion.div 
                            initial={{ opacity: 0, scale: 0.95 }}
                            whileInView={{ opacity: 1, scale: 1 }}
                            viewport={{ once: true }}
                            transition={{ delay: 0.1 }}
                            className="bg-[#0E1425] border border-blue-400/10 hover:border-blue-400/25 p-6 rounded-2xl flex flex-col justify-between"
                        >
                            <div>
                                <Award className="text-blue-400 mb-4" size={20} />
                                <span className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Annualized Alpha</span>
                                <h4 className="text-3xl font-black text-white mt-1">+22.4%</h4>
                            </div>
                            <span className="text-xs text-slate-400 mt-4 block border-t border-slate-800 pt-3">Excess return above benchmark</span>
                        </motion.div>

                        {/* Metric 3 */}
                        <motion.div 
                            initial={{ opacity: 0, scale: 0.95 }}
                            whileInView={{ opacity: 1, scale: 1 }}
                            viewport={{ once: true }}
                            transition={{ delay: 0.2 }}
                            className="bg-[#0E1425] border border-blue-400/10 hover:border-blue-400/25 p-6 rounded-2xl flex flex-col justify-between"
                        >
                            <div>
                                <Activity className="text-violet-400 mb-4" size={20} />
                                <span className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Sharpe Ratio</span>
                                <h4 className="text-3xl font-black text-white mt-1">1.84</h4>
                            </div>
                            <span className="text-xs text-slate-400 mt-4 block border-t border-slate-800 pt-3">Nifty Sharpe benchmark: 0.88</span>
                        </motion.div>

                        {/* Metric 4 */}
                        <motion.div 
                            initial={{ opacity: 0, scale: 0.95 }}
                            whileInView={{ opacity: 1, scale: 1 }}
                            viewport={{ once: true }}
                            transition={{ delay: 0.3 }}
                            className="bg-[#0E1425] border border-blue-400/10 hover:border-blue-400/25 p-6 rounded-2xl flex flex-col justify-between"
                        >
                            <div>
                                <ShieldAlert className="text-red-400 mb-4" size={20} />
                                <span className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Max Drawdown</span>
                                <h4 className="text-3xl font-black text-white mt-1">-14.2%</h4>
                            </div>
                            <span className="text-xs text-slate-400 mt-4 block border-t border-slate-800 pt-3">Nifty Max Drawdown: -26.4%</span>
                        </motion.div>
                    </div>

                    {/* Right: Comparative Chart Visual (col-span-3) */}
                    <motion.div 
                        initial={{ opacity: 0, x: 40 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.6 }}
                        className="lg:col-span-3 bg-[#0E1425] border border-blue-400/15 rounded-3xl p-6 lg:p-8 relative overflow-hidden"
                    >
                        <div className="flex justify-between items-center pb-4 mb-6 border-b border-blue-400/10">
                            <div>
                                <h4 className="text-sm font-bold text-white uppercase tracking-tight">Performance Growth Chart</h4>
                                <span className="text-[10px] text-slate-500">Compounded Growth Model ($10k base simulation)</span>
                            </div>
                            <div className="flex gap-4 text-[10px] font-bold">
                                <div className="flex items-center gap-1.5">
                                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                                    <span className="text-slate-300">QuantAI Swarm</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
                                    <span className="text-slate-500">NIFTY 50 INDEX</span>
                                </div>
                            </div>
                        </div>

                        {/* Chart Line Visualization */}
                        <div className="h-64 relative flex flex-col justify-between">
                            {/* SVG Chart Curves */}
                            <svg viewBox="0 0 500 200" className="w-full h-full absolute inset-0 overflow-visible">
                                <defs>
                                    <linearGradient id="metricGlow" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#10b981" stopOpacity="0.15"/>
                                        <stop offset="100%" stopColor="#10b981" stopOpacity="0.0"/>
                                    </linearGradient>
                                </defs>
                                {/* Grid Lines */}
                                <line x1="0" y1="40" x2="500" y2="40" stroke="#ffffff" strokeOpacity="0.02" />
                                <line x1="0" y1="90" x2="500" y2="90" stroke="#ffffff" strokeOpacity="0.02" />
                                <line x1="0" y1="140" x2="500" y2="140" stroke="#ffffff" strokeOpacity="0.02" />
                                
                                {/* Nifty Index (Blue line) */}
                                <path d="M 0 170 Q 50 160 100 155 T 200 145 T 300 135 T 400 120 T 500 110" fill="none" stroke="#3b82f6" strokeWidth="2" strokeDasharray="3,3" opacity="0.6" />

                                {/* QuantAI Curve (Emerald line) */}
                                <path d="M 0 170 Q 50 150 100 130 T 200 105 T 300 70 T 400 45 T 500 20 L 500 200 L 0 200 Z" fill="url(#metricGlow)" />
                                <path d="M 0 170 Q 50 150 100 130 T 200 105 T 300 70 T 400 45 T 500 20" fill="none" stroke="#10b981" strokeWidth="3.5" strokeLinecap="round" />

                                {/* Interactive Indicator */}
                                <line x1="380" y1="0" x2="380" y2="200" stroke="#ffffff" strokeOpacity="0.05" />
                                <circle cx="380" cy="50" r="4" fill="#10b981" />
                                <circle cx="380" cy="125" r="4" fill="#3b82f6" />
                            </svg>

                            {/* Fake labels along lines */}
                            <div className="absolute right-4 top-2 text-[10px] bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded text-emerald-400 font-bold">
                                +342.15% Outperforming
                            </div>
                        </div>
                    </motion.div>
                </div>
            </div>
        </section>
    );
};

export default LandingPerformanceMetrics;
