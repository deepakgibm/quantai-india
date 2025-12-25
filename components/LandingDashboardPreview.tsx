import React from 'react';

const LandingDashboardPreview: React.FC = () => {
    return (
        <section className="py-20 bg-slate-900 overflow-hidden">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="text-center mb-16">
                    <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">Powerful, intuitive, and data-rich.</h2>
                    <p className="text-slate-400">Everything you need in one powerful platform.</p>
                </div>

                <div className="relative mx-auto max-w-5xl">
                    {/* Glass background for the image */}
                    <div className="absolute -inset-4 bg-gradient-to-r from-brand-500/20 to-teal-500/20 rounded-3xl blur-2xl opacity-50 -z-10" />

                    <div className="rounded-2xl border border-slate-700/50 shadow-2xl overflow-hidden glass-panel">
                        <img
                            src="/dashboard-preview.png"
                            alt="Dashboard Preview"
                            className="w-full h-auto object-cover opacity-90"
                        />
                    </div>

                    {/* Floating UI Elements (Mock) */}
                    <div className="absolute -top-6 -right-6 hidden lg:block p-4 rounded-xl bg-slate-800 border border-brand-500/50 shadow-xl animate-bounce-slow">
                        <div className="flex items-center gap-3">
                            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                            <span className="text-xs font-bold text-white uppercase tracking-widest">Live: Nifty +1.2%</span>
                        </div>
                    </div>

                    <div className="absolute -bottom-6 -left-6 hidden lg:block p-4 rounded-xl bg-slate-800 border border-teal-500/50 shadow-xl animate-bounce-slow" style={{ animationDelay: '1s' }}>
                        <div className="flex items-center gap-3">
                            <span className="text-xs font-bold text-teal-400 uppercase tracking-widest">AI BUY SIGNAL: RELIANCE</span>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default LandingDashboardPreview;
