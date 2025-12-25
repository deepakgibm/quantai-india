import React from 'react';
import { Zap, BarChart3, ShieldCheck, Cpu } from 'lucide-react';

const LandingFeatures: React.FC = () => {
    const features = [
        {
            title: 'Real-time Market Insights',
            description: 'Lightning-fast data feeds and real-time scanning for Nifty 500 stocks.',
            icon: <Zap className="text-brand-500" size={24} />,
        },
        {
            title: 'AI-Driven Trade Signals',
            description: 'Advanced machine learning models that identify high-probability trade setups.',
            icon: <Cpu className="text-brand-400" size={24} />,
        },
        {
            title: 'Backtesting & Performance',
            description: 'Test your strategies against historical data before risking real capital.',
            icon: <BarChart3 className="text-teal-400" size={24} />,
        },
        {
            title: 'Institutional Grade Security',
            description: 'Your data and trade executions are protected by state-of-the-art encryption.',
            icon: <ShieldCheck className="text-brand-600" size={24} />,
        },
    ];

    return (
        <section id="features" className="py-20 bg-slate-900">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="text-center mb-16">
                    <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">Precision Trading with Intelligence</h2>
                    <p className="text-slate-400 max-w-2xl mx-auto">Powerful tools designed for speed, accuracy, and data-backed decision making.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                    {features.map((feature, idx) => (
                        <div key={idx} className="p-8 rounded-2xl bg-slate-800/50 border border-slate-700 hover:border-brand-500/50 transition-all group">
                            <div className="w-12 h-12 rounded-xl bg-slate-900 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                                {feature.icon}
                            </div>
                            <h3 className="text-xl font-bold text-white mb-3">{feature.title}</h3>
                            <p className="text-slate-400 text-sm leading-relaxed">{feature.description}</p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
};

export default LandingFeatures;
