import React from 'react';
import { TrendingUp, Twitter, Github, Linkedin } from 'lucide-react';

const LandingFooter: React.FC = () => {
    return (
        <footer className="bg-slate-950 text-slate-400 py-20 border-t border-slate-900">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-16">
                    <div className="col-span-1 md:col-span-1">
                        <div className="flex items-center gap-2 mb-6">
                            <div className="bg-brand-500 p-1.5 rounded-lg">
                                <TrendingUp className="text-white" size={20} />
                            </div>
                            <span className="text-xl font-bold text-white tracking-tight">QuantAI<span className="text-brand-500">India</span></span>
                        </div>
                        <p className="text-sm leading-relaxed mb-6">
                            Empowering Indian traders with institutional-grade AI analysis and real-time market insights.
                        </p>
                        <div className="flex gap-4">
                            <Twitter size={20} className="hover:text-brand-500 cursor-pointer transition-colors" />
                            <Github size={20} className="hover:text-white cursor-pointer transition-colors" />
                            <Linkedin size={20} className="hover:text-brand-500 cursor-pointer transition-colors" />
                        </div>
                    </div>

                    <div>
                        <h4 className="text-white font-bold mb-6">Product</h4>
                        <ul className="space-y-4 text-sm">
                            <li><a href="#" className="hover:text-white transition-colors">Features</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Algorithms</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Scanner</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">AI Prompt</a></li>
                        </ul>
                    </div>

                    <div>
                        <h4 className="text-white font-bold mb-6">Company</h4>
                        <ul className="space-y-4 text-sm">
                            <li><a href="#" className="hover:text-white transition-colors">About Us</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Careers</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Blog</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Support</a></li>
                        </ul>
                    </div>

                    <div>
                        <h4 className="text-white font-bold mb-6">Legal</h4>
                        <ul className="space-y-4 text-sm">
                            <li><a href="#" className="hover:text-white transition-colors">Privacy Policy</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Terms of Service</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Cookie Policy</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Risk Disclosure</a></li>
                        </ul>
                    </div>
                </div>

                <div className="pt-8 border-t border-slate-900 text-xs text-slate-500">
                    <p className="mb-4">
                        DISCLAIMER: Trading in equity and derivatives involves high risk. Past performance is not indicative of future results. All information provided is for educational and analytical purposes only. Please consult with a SEBI registered investment advisor before making any financial decisions.
                    </p>
                    <p>© 2025 QuantAI India. All rights reserved.</p>
                </div>
            </div>
        </footer>
    );
};

export default LandingFooter;
