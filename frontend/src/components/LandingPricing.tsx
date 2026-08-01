import React from 'react';
import { motion } from 'framer-motion';
import { Check, Sparkles } from 'lucide-react';
import { Page } from '../types';

interface LandingPricingProps {
    onNavigate: (page: Page) => void;
}

const LandingPricing: React.FC<LandingPricingProps> = ({ onNavigate }) => {
    return (
        <section id="pricing" className="relative py-32 bg-[#050816] overflow-hidden border-t border-blue-400/10">
            {/* Background elements */}
            <div className="absolute inset-0 bg-grid-pattern opacity-100 pointer-events-none" />
            <div className="absolute top-[30%] left-[-10%] w-[50%] h-[50%] rounded-full bg-gradient-radial from-blue-500/5 to-transparent blur-[160px] pointer-events-none" />
            <div className="absolute bottom-[20%] right-[-10%] w-[45%] h-[45%] rounded-full bg-gradient-radial from-violet-600/5 to-transparent blur-[160px] pointer-events-none" />

            <div className="max-w-[1440px] mx-auto px-6 lg:px-20 relative z-10">
                {/* Section Header */}
                <div className="text-center max-w-3xl mx-auto mb-20">
                    <motion.span 
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-blue-400/30 bg-blue-500/10 text-blue-300 text-xs font-semibold uppercase tracking-widest mb-4"
                    >
                        <span>Subscription Plans</span>
                    </motion.span>
                    
                    <motion.h2 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.1 }}
                        className="text-3xl sm:text-4xl lg:text-5xl font-serif font-bold text-white tracking-tight"
                    >
                        Transparent Pricing for Everyone
                    </motion.h2>
                    
                    <motion.p 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.2 }}
                        className="text-slate-400 text-base sm:text-lg mt-4 leading-relaxed font-normal"
                    >
                        Scale your trading with plans that fit your requirements. No hidden fees or lock-ins.
                    </motion.p>
                </div>

                {/* Pricing Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 max-w-4xl mx-auto gap-8 items-stretch">
                    
                    {/* Free Plan */}
                    <motion.div 
                        initial={{ opacity: 0, x: -30 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.5 }}
                        className="p-8 lg:p-10 rounded-[32px] bg-[#0E1425] border border-blue-400/15 flex flex-col justify-between hover:border-blue-400/30 transition-all duration-300 relative group"
                    >
                        <div className="absolute inset-0 bg-gradient-to-b from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-[32px]" />
                        
                        <div className="relative z-10">
                            <h3 className="text-xl font-bold text-slate-300 mb-2">Free Starter</h3>
                            <p className="text-xs text-slate-500 mb-6">Explore the power of AI analysis and basics.</p>
                            <div className="text-4xl lg:text-5xl font-black text-white mb-8 flex items-baseline">
                                ₹0<span className="text-sm text-slate-500 font-bold ml-1 uppercase tracking-wider">/ Month</span>
                            </div>
                            
                            <ul className="space-y-4 mb-10">
                                <li className="flex items-center gap-3 text-slate-400 text-sm font-medium">
                                    <Check size={16} className="text-blue-400 shrink-0" /> 
                                    <span>Daily Stock Scanner Access</span>
                                </li>
                                <li className="flex items-center gap-3 text-slate-400 text-sm font-medium">
                                    <Check size={16} className="text-blue-400 shrink-0" /> 
                                    <span>Delayed Interactive Charts</span>
                                </li>
                                <li className="flex items-center gap-3 text-slate-400 text-sm font-medium">
                                    <Check size={16} className="text-blue-400 shrink-0" /> 
                                    <span>Community Forums Access</span>
                                </li>
                                <li className="flex items-center gap-3 text-slate-400 text-sm font-medium">
                                    <Check size={16} className="text-blue-400 shrink-0" /> 
                                    <span>SEBI Data Lineage Traceback</span>
                                </li>
                            </ul>
                        </div>

                        <button 
                            onClick={() => onNavigate(Page.SIGNUP)}
                            className="w-full py-4 rounded-full border border-blue-400/20 text-slate-300 hover:text-white hover:bg-blue-400/10 font-bold text-sm transition-all duration-300 relative z-10"
                        >
                            Get Started Free
                        </button>
                    </motion.div>

                    {/* Pro Plan */}
                    <motion.div 
                        initial={{ opacity: 0, x: 30 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.5 }}
                        className="p-10 rounded-[32px] bg-[#0E1425] border-2 border-blue-500/80 relative shadow-[0_20px_50px_rgba(96,165,250,0.15)] flex flex-col justify-between group transform scale-105 z-10"
                    >
                        {/* Popular Badge */}
                        <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-gradient-to-r from-blue-500 to-violet-600 text-white text-[10px] font-black uppercase px-4 py-1.5 rounded-full tracking-widest shadow-lg shadow-blue-500/25 flex items-center gap-1">
                            <Sparkles size={10} /> Most Popular
                        </div>

                        <div className="absolute inset-0 bg-gradient-to-b from-blue-500/10 to-transparent opacity-100 rounded-[32px] pointer-events-none" />

                        <div className="relative z-10">
                            <h3 className="text-xl font-bold text-white mb-2">Professional Trader</h3>
                            <p className="text-xs text-blue-300/60 mb-6">Institutional-grade algorithms for serious trading.</p>
                            <div className="text-4xl lg:text-5xl font-black text-white mb-8 flex items-baseline">
                                ₹2,499<span className="text-sm text-slate-400 font-bold ml-1 uppercase tracking-wider">/ Month</span>
                            </div>
                            
                            <ul className="space-y-4 mb-10">
                                <li className="flex items-center gap-3 text-white text-sm font-semibold">
                                    <Check size={16} className="text-blue-400 shrink-0" /> 
                                    <span>Real-time AI Swarm Signals</span>
                                </li>
                                <li className="flex items-center gap-3 text-white text-sm font-semibold">
                                    <Check size={16} className="text-blue-400 shrink-0" /> 
                                    <span>WebSocket live stream data feed</span>
                                </li>
                                <li className="flex items-center gap-3 text-white text-sm font-semibold">
                                    <Check size={16} className="text-blue-400 shrink-0" /> 
                                    <span>Walk-forward backtesting platform</span>
                                </li>
                                <li className="flex items-center gap-3 text-white text-sm font-semibold">
                                    <Check size={16} className="text-blue-400 shrink-0" /> 
                                    <span>Unlimited swing scan breakout rules</span>
                                </li>
                                <li className="flex items-center gap-3 text-white text-sm font-semibold">
                                    <Check size={16} className="text-blue-400 shrink-0" /> 
                                    <span>Algo Builder and live monitors</span>
                                </li>
                            </ul>
                        </div>

                        <button 
                            onClick={() => onNavigate(Page.SIGNUP)}
                            className="w-full py-4 rounded-full bg-gradient-to-r from-blue-500 to-violet-600 hover:from-blue-600 hover:to-violet-700 text-white font-bold text-sm shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all duration-300 relative z-10"
                        >
                            Activate Pro Membership
                        </button>
                    </motion.div>
                </div>
            </div>
        </section>
    );
};

export default LandingPricing;
