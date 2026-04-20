import React from 'react';
import { Page } from '../types';
import { ChevronRight, Sparkles } from 'lucide-react';

interface LandingHeroProps {
    onNavigate: (page: Page) => void;
}

const LandingHero: React.FC<LandingHeroProps> = ({ onNavigate }) => {
    return (
        <section className="relative pt-32 pb-20 overflow-hidden">
            {/* Background Glow */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[500px] bg-gradient-to-b from-brand-500/10 to-transparent blur-3xl opacity-50 -z-10" />

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-semibold mb-8 animate-fade-in">
                    <Sparkles size={14} />
                    <span>New: AI-Powered Sector Analysis Live</span>
                </div>

                <h1 className="text-5xl md:text-7xl font-extrabold text-white tracking-tight mb-6">
                    AI-Powered Stock Analysis <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-teal-400">
                        for Smarter Trading
                    </span>
                </h1>

                <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
                    The all-in-one platform for real-time market insights, AI-driven trade signals, and automated scanning. Built for the modern Indian trader.
                </p>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                    <button
                        onClick={() => onNavigate(Page.SIGNUP)}
                        className="w-full sm:w-auto bg-brand-500 hover:bg-brand-600 text-white px-8 py-4 rounded-xl font-bold text-lg transition-all shadow-xl shadow-brand-500/25 flex items-center justify-center gap-2 group"
                    >
                        Get Started Free
                        <ChevronRight className="group-hover:translate-x-1 transition-transform" />
                    </button>
                    <button
                        onClick={() => onNavigate(Page.LOGIN)}
                        className="w-full sm:w-auto bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 px-8 py-4 rounded-xl font-bold text-lg transition-all"
                    >
                        Login to Dashboard
                    </button>
                </div>

                {/* Simple Stats or Social Proof */}
                <div className="mt-16 flex flex-wrap justify-center gap-12 grayscale opacity-40 hover:grayscale-0 hover:opacity-100 transition-all duration-500">
                    <div className="flex flex-col items-center">
                        <span className="text-2xl font-bold text-white">500+</span>
                        <span className="text-xs text-slate-500 uppercase tracking-widest">Nifty Stocks</span>
                    </div>
                    <div className="flex flex-col items-center">
                        <span className="text-2xl font-bold text-white">24/7</span>
                        <span className="text-xs text-slate-500 uppercase tracking-widest">Global Data</span>
                    </div>
                    <div className="flex flex-col items-center">
                        <span className="text-2xl font-bold text-white">99.9%</span>
                        <span className="text-xs text-slate-500 uppercase tracking-widest">Uptime</span>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default LandingHero;
