import React from 'react';
import { Check } from 'lucide-react';

const LandingPricing: React.FC = () => {
    return (
        <section id="pricing" className="py-20 bg-slate-900 overflow-hidden relative">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-brand-500/5 blur-3xl rounded-full -z-10" />

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="text-center mb-12">
                    <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">Transparent Pricing for Everyone</h2>
                    <p className="text-slate-400">Scale your trading with plans that fit your needs.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 max-w-4xl mx-auto gap-8 items-center">
                    {/* Free Plan */}
                    <div className="p-8 rounded-2xl bg-slate-800/30 border border-slate-700/50">
                        <h3 className="text-lg font-semibold text-slate-300 mb-2">Free</h3>
                        <div className="text-4xl font-bold text-white mb-6">₹0<span className="text-lg text-slate-500 font-normal">/mo</span></div>
                        <ul className="space-y-4 mb-8">
                            <li className="flex items-center gap-3 text-slate-400 text-sm"><Check size={16} className="text-brand-500" /> Basic Scanning</li>
                            <li className="flex items-center gap-3 text-slate-400 text-sm"><Check size={16} className="text-brand-500" /> Delayed Charts</li>
                            <li className="flex items-center gap-3 text-slate-400 text-sm"><Check size={16} className="text-brand-500" /> Community Access</li>
                        </ul>
                        <button className="w-full py-3 rounded-lg border border-slate-700 text-white hover:bg-slate-700 transition-all font-semibold">Join for Free</button>
                    </div>

                    {/* Pro Plan */}
                    <div className="p-10 rounded-2xl bg-slate-800 border-2 border-brand-500 relative shadow-2xl shadow-brand-500/10 transform scale-105 z-10">
                        <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-brand-500 text-white text-xs font-bold px-3 py-1 rounded-full uppercase tracking-widest">Most Popular</div>
                        <h3 className="text-xl font-bold text-white mb-2">Pro</h3>
                        <div className="text-4xl font-bold text-white mb-6">₹2,499<span className="text-lg text-slate-500 font-normal">/mo</span></div>
                        <ul className="space-y-4 mb-8">
                            <li className="flex items-center gap-3 text-white text-sm"><Check size={16} className="text-brand-500" /> AI Trade Signals</li>
                            <li className="flex items-center gap-3 text-white text-sm"><Check size={16} className="text-brand-500" /> Real-time WebSocket Data</li>
                            <li className="flex items-center gap-3 text-white text-sm"><Check size={16} className="text-brand-500" /> Advanced Backtesting</li>
                            <li className="flex items-center gap-3 text-white text-sm"><Check size={16} className="text-brand-500" /> Multi-index Support</li>
                        </ul>
                        <button className="w-full py-3 rounded-lg bg-brand-500 text-white hover:bg-brand-600 transition-all font-bold shadow-lg shadow-brand-500/30">Get Pro Now</button>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default LandingPricing;
