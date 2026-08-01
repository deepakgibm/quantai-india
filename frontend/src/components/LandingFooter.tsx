import React from 'react';
import { Page } from '../types';
import { TrendingUp, Twitter, Github, Linkedin, Shield } from 'lucide-react';

const LandingFooter: React.FC = () => {
    return (
        <footer className="bg-[#050816] text-slate-400 py-24 border-t border-blue-400/10">
            <div className="max-w-[1440px] mx-auto px-6 lg:px-20">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-12 pb-16">
                    {/* Brand Column (col-span-2) */}
                    <div className="lg:col-span-2">
                        <div className="flex items-center gap-2.5 mb-6">
                            <div className="bg-gradient-to-br from-blue-500 to-violet-600 p-2 rounded-xl">
                                <TrendingUp className="text-white" size={18} />
                            </div>
                            <span className="text-xl font-bold text-white tracking-tight">
                                QuantAI<span className="bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent">India</span>
                            </span>
                        </div>
                        <p className="text-sm text-slate-400 leading-relaxed max-w-sm mb-6">
                            Empowering active Indian stock traders with institutional-grade AI analysis, swarm consensus decision-making, and high-frequency scanners.
                        </p>
                        <div className="flex gap-4">
                            <a href="#" className="p-2 bg-[#0E1425] border border-blue-400/10 rounded-xl hover:border-blue-400/30 hover:text-white transition-colors">
                                <Twitter size={16} />
                            </a>
                            <a href="#" className="p-2 bg-[#0E1425] border border-blue-400/10 rounded-xl hover:border-blue-400/30 hover:text-white transition-colors">
                                <Github size={16} />
                            </a>
                            <a href="#" className="p-2 bg-[#0E1425] border border-blue-400/10 rounded-xl hover:border-blue-400/30 hover:text-white transition-colors">
                                <Linkedin size={16} />
                            </a>
                        </div>
                    </div>

                    {/* Links Column 1 */}
                    <div>
                        <h4 className="text-white text-xs font-black uppercase tracking-wider mb-6">Product</h4>
                        <ul className="space-y-4 text-xs font-semibold">
                            <li><a href="#features" className="hover:text-white transition-colors">AI Swarm Committee</a></li>
                            <li><a href="#features" className="hover:text-white transition-colors">Technical Scanner</a></li>
                            <li><a href="#features" className="hover:text-white transition-colors">Sector Heatmaps</a></li>
                            <li><a href="#features" className="hover:text-white transition-colors">Algo Workspace</a></li>
                        </ul>
                    </div>

                    {/* Links Column 2 */}
                    <div>
                        <h4 className="text-white text-xs font-black uppercase tracking-wider mb-6">Platform</h4>
                        <ul className="space-y-4 text-xs font-semibold">
                            <li><a href="#workflow" className="hover:text-white transition-colors">Decision Workflow</a></li>
                            <li><a href="#metrics" className="hover:text-white transition-colors">Performance Growth</a></li>
                            <li><a href="#pricing" className="hover:text-white transition-colors">Subscription Pricing</a></li>
                            <li><a href="#faq" className="hover:text-white transition-colors">Support Desk FAQ</a></li>
                        </ul>
                    </div>

                    {/* Links Column 3 */}
                    <div>
                        <h4 className="text-white text-xs font-black uppercase tracking-wider mb-6">Legal</h4>
                        <ul className="space-y-4 text-xs font-semibold">
                            <li><a href="#" className="hover:text-white transition-colors">Privacy Policy</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Terms of Service</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Cookie Controls</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Risk Disclosures</a></li>
                        </ul>
                    </div>
                </div>

                {/* Regulatory Risk and Disclaimer Box */}
                <div className="pt-8 border-t border-blue-400/10 text-[10px] text-slate-500 space-y-4">
                    <div className="flex items-start gap-2.5 bg-blue-500/5 border border-blue-500/10 rounded-2xl p-4">
                        <Shield size={16} className="text-blue-400 shrink-0 mt-0.5" />
                        <p className="leading-relaxed">
                            <strong>REGULATORY DISCLAIMER:</strong> Trading in equity, derivatives, option contracts, and commodities involves high risk. Past performance of our AI models is not indicative of future results. QuantAI India is an analytical software provider and does not provide SEBI registered investment advice, discretionary automated trading execution services, or guaranteed returns. All signals, alerts, consensus debate summaries, and ratios are calculated automatically for research and analysis purposes only. Please consult with a registered investment advisor before placing active trades.
                        </p>
                    </div>
                    <div className="flex flex-wrap justify-between items-center gap-4 text-slate-600 font-mono text-[9px]">
                        <span>© 2026 QuantAI India. Developed for High-Growth Portfolio Strategy.</span>
                        <span>Designed in collaboration with official exchange feeds.</span>
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default LandingFooter;
