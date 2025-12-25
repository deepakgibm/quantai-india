import React from 'react';
import { User, Users, Cpu, GraduationCap } from 'lucide-react';

const LandingWhoItsFor: React.FC = () => {
    const cards = [
        {
            title: 'Retail Traders',
            description: 'Simple yet powerful tools to gain an edge in the daily markets.',
            icon: <User className="text-brand-500" size={24} />,
        },
        {
            title: 'Long-term Investors',
            description: 'Data-driven analysis to identify stable growth opportunities.',
            icon: <Users className="text-brand-400" size={24} />,
        },
        {
            title: 'Quant / Algo Traders',
            description: 'Build, test, and deploy automated strategies with ease.',
            icon: <Cpu className="text-teal-400" size={24} />,
        },
        {
            title: 'Finance Students',
            description: 'Learn market dynamics with real-time data and simulations.',
            icon: <GraduationCap className="text-brand-600" size={24} />,
        },
    ];

    return (
        <section id="who-it-is-for" className="py-20 bg-slate-50 dark:bg-slate-900/50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="text-center mb-16">
                    <h2 className="text-3xl md:text-5xl font-bold text-slate-900 dark:text-white mb-4">Built for Every Market Participant</h2>
                    <p className="text-slate-600 dark:text-slate-400">Tailored experiences for different trading styles and objectives.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {cards.map((card, idx) => (
                        <div key={idx} className="p-6 rounded-xl bg-white dark:bg-slate-800 shadow-xl shadow-slate-200/50 dark:shadow-none border border-slate-100 dark:border-slate-700">
                            <div className="w-12 h-12 rounded-lg bg-slate-50 dark:bg-slate-900 flex items-center justify-center mb-6">
                                {card.icon}
                            </div>
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">{card.title}</h3>
                            <p className="text-slate-600 dark:text-slate-400 text-sm leading-relaxed">{card.description}</p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
};

export default LandingWhoItsFor;
