import React from 'react';
import { motion } from 'framer-motion';
import { Database, Cpu, MessageSquare, ShieldCheck, ArrowDown } from 'lucide-react';

const steps = [
    {
        icon: Database,
        iconColor: 'text-blue-400',
        iconBg: 'bg-blue-500/10 border-blue-500/20',
        title: '01 / Market Ingestion & Hydration',
        description: 'Direct WebSocket connection receives ticks for Nifty 500 stocks. Simultaneously, EOD candles, PE ratios, and financial metrics are loaded from the PostgreSQL database.'
    },
    {
        icon: Cpu,
        iconColor: 'text-violet-400',
        iconBg: 'bg-violet-500/10 border-violet-500/20',
        title: '02 / Agent Swarm Dispatched',
        description: 'Dedicated AI Agents (Macro, Technical Indicators, and Ratios) analyze the constituent metrics concurrently. Indicator utilities calculate SMA, RSI, MACD, and Bollinger Bands.'
    },
    {
        icon: MessageSquare,
        iconColor: 'text-amber-400',
        iconBg: 'bg-amber-500/10 border-amber-500/20',
        title: '03 / Consensus Debate & Swarm Assembly',
        description: 'Agents debate findings via Swarm Consensus logic. Outliers are discarded, valuation ratings (e.g. Undervalued) are verified, and an overall consensus confidence score is computed.'
    },
    {
        icon: ShieldCheck,
        iconColor: 'text-emerald-400',
        iconBg: 'bg-emerald-500/10 border-emerald-500/20',
        title: '04 / Verdict & Risk Assessment',
        description: 'A formal buy/sell verdict is produced alongside precise target prices, stop-loss thresholds, and calculated position sizing based on portfolio risk tolerance.'
    }
];

const LandingWorkflowTimeline: React.FC = () => {
    return (
        <section id="workflow" className="relative py-32 bg-[#050816] overflow-hidden border-y border-blue-400/10">
            {/* Background highlights */}
            <div className="absolute top-[30%] left-[-10%] w-[45%] h-[45%] rounded-full bg-gradient-radial from-violet-600/5 to-transparent blur-[160px] pointer-events-none" />
            <div className="absolute bottom-[20%] right-[-10%] w-[45%] h-[45%] rounded-full bg-gradient-radial from-blue-500/5 to-transparent blur-[160px] pointer-events-none" />
            
            <div className="max-w-[1440px] mx-auto px-6 lg:px-20 relative z-10">
                {/* Section Header */}
                <div className="text-center max-w-3xl mx-auto mb-24">
                    <motion.span 
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-blue-400/30 bg-blue-500/10 text-blue-300 text-xs font-semibold uppercase tracking-widest mb-4"
                    >
                        <span>Decision Cycle</span>
                    </motion.span>
                    
                    <motion.h2 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.1 }}
                        className="text-3xl sm:text-4xl lg:text-5xl font-serif font-bold text-white tracking-tight"
                    >
                        The Swarm Workflow
                    </motion.h2>
                    
                    <motion.p 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.2 }}
                        className="text-slate-400 text-base sm:text-lg mt-4 leading-relaxed font-normal"
                    >
                        How the platform transitions raw data points into actionable institutional verdicts.
                    </motion.p>
                </div>

                {/* Timeline Grid */}
                <div className="relative max-w-4xl mx-auto">
                    {/* Vertical connecting line */}
                    <div className="absolute left-[31px] md:left-1/2 top-10 bottom-10 w-0.5 bg-gradient-to-b from-blue-500 via-violet-600 to-emerald-500 opacity-20" />

                    <div className="space-y-16">
                        {steps.map((step, idx) => {
                            const StepIcon = step.icon;
                            const isEven = idx % 2 === 0;
                            return (
                                <motion.div 
                                    key={idx}
                                    initial={{ opacity: 0, y: 30 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    viewport={{ once: true, margin: '-50px' }}
                                    transition={{ duration: 0.5, delay: idx * 0.1 }}
                                    className={`relative flex flex-col md:flex-row items-start md:items-center ${isEven ? 'md:flex-row-reverse' : ''}`}
                                >
                                    {/* Icon circle (centered) */}
                                    <div className="absolute left-0 md:left-1/2 -translate-x-[4px] md:-translate-x-1/2 z-20 flex items-center justify-center bg-[#050816] p-1.5 rounded-full border border-blue-400/20 shadow-[0_0_20px_rgba(96,165,250,0.1)]">
                                        <div className={`p-4 rounded-full border ${step.iconBg} ${step.iconColor}`}>
                                            <StepIcon size={22} />
                                        </div>
                                    </div>

                                    {/* Content Card (Half Width) */}
                                    <div className={`w-full md:w-1/2 pl-16 md:pl-0 ${isEven ? 'md:pr-16 md:text-right' : 'md:pl-16 md:text-left'}`}>
                                        <div className="bg-[#0E1425] border border-blue-400/10 rounded-2xl p-6 lg:p-8 hover:border-blue-400/20 hover:shadow-card-hover transition-all duration-300">
                                            <h4 className="text-white font-extrabold text-lg mb-2">
                                                {step.title}
                                            </h4>
                                            <p className="text-slate-400 text-sm leading-relaxed font-normal">
                                                {step.description}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Empty space for structural balance */}
                                    <div className="hidden md:block w-1/2" />
                                </motion.div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </section>
    );
};

export default LandingWorkflowTimeline;
