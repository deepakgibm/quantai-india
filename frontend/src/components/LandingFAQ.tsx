import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, HelpCircle } from 'lucide-react';

const faqs = [
    {
        q: "What is the source of the market data?",
        a: "We ingest real-time market feeds directly from verified exchange connectivity via Upstox API. All technical indicators and candle data are recalculated with pixel-perfect data lineage and high reliability."
    },
    {
        q: "Is this platform SEBI compliant?",
        a: "Yes, QuantAI is an analytical software platform for research and education. We do not run discretionary auto-trading or issue guaranteed financial tips. All tools are designed for decision support."
    },
    {
        q: "How does the AI Swarm consensus model work?",
        a: "It mimics an institutional investment committee. The workspace launches three specialized LLM agents (Technical, Fundamental, and Macro) who evaluate the stock from distinct angles, debate the metrics, and output a unified consensus score."
    },
    {
        q: "Can I backtest my strategies?",
        a: "Yes, the platform includes a Walk-Forward Backtesting suite and Algo Builder. You can backtest custom conditions across 300+ daily candles and forward-test them in live sandbox paper mode."
    },
    {
        q: "What is the difference between Free and Pro tiers?",
        a: "The Free tier supports EOD scanning, fundamental analysis, and standard indexes. The Pro tier unlocks live WebSocket updates, instant AI Swarm debate runs, advanced swing scanners, and multi-index support."
    }
];

interface AccordionItemProps {
    question: string;
    answer: string;
    isOpen: boolean;
    onClick: () => void;
}

const AccordionItem: React.FC<AccordionItemProps> = ({ question, answer, isOpen, onClick }) => {
    return (
        <div className="bg-[#0E1425] border border-blue-400/10 hover:border-blue-400/20 rounded-2xl overflow-hidden transition-all duration-300">
            <button
                onClick={onClick}
                className="w-full px-6 py-5 flex items-center justify-between text-left focus:outline-none"
            >
                <div className="flex items-center gap-3">
                    <HelpCircle size={16} className="text-blue-400 shrink-0" />
                    <span className="text-white text-sm sm:text-base font-extrabold tracking-tight">{question}</span>
                </div>
                {isOpen ? (
                    <ChevronUp size={16} className="text-slate-400" />
                ) : (
                    <ChevronDown size={16} className="text-slate-400" />
                )}
            </button>
            
            <AnimatePresence initial={false}>
                {isOpen && (
                    <motion.div
                        key="content"
                        initial="collapsed"
                        animate="open"
                        exit="collapsed"
                        variants={{
                            open: { opacity: 1, height: 'auto' },
                            collapsed: { opacity: 0, height: 0 }
                        }}
                        transition={{ duration: 0.3, ease: [0.04, 0.62, 0.23, 0.98] }}
                    >
                        <div className="px-6 pb-5 pt-1 text-slate-400 text-sm leading-relaxed border-t border-blue-400/5 font-normal">
                            {answer}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

const LandingFAQ: React.FC = () => {
    const [openIndex, setOpenIndex] = React.useState<number | null>(0);

    return (
        <section id="faq" className="relative py-32 bg-[#050816] overflow-hidden border-t border-blue-400/10">
            {/* Background elements */}
            <div className="absolute inset-0 bg-grid-pattern opacity-100 pointer-events-none" />
            <div className="absolute top-[20%] right-[-10%] w-[45%] h-[45%] rounded-full bg-gradient-radial from-violet-600/5 to-transparent blur-[160px] pointer-events-none" />

            <div className="max-w-[1440px] mx-auto px-6 lg:px-20 relative z-10">
                {/* Section Header */}
                <div className="text-center max-w-3xl mx-auto mb-20">
                    <motion.span 
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-blue-400/30 bg-blue-500/10 text-blue-300 text-xs font-semibold uppercase tracking-widest mb-4"
                    >
                        <span>Support Desk</span>
                    </motion.span>
                    
                    <motion.h2 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.1 }}
                        className="text-3xl sm:text-4xl lg:text-5xl font-serif font-bold text-white tracking-tight"
                    >
                        Frequently Asked Questions
                    </motion.h2>
                    
                    <motion.p 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.2 }}
                        className="text-slate-400 text-base sm:text-lg mt-4 leading-relaxed font-normal"
                    >
                        Everything you need to know about the platform, data lineage, and our SEBI compliance rules.
                    </motion.p>
                </div>

                {/* FAQ List */}
                <div className="max-w-3xl mx-auto space-y-4">
                    {faqs.map((faq, idx) => (
                        <AccordionItem
                            key={idx}
                            question={faq.q}
                            answer={faq.a}
                            isOpen={openIndex === idx}
                            onClick={() => setOpenIndex(openIndex === idx ? null : idx)}
                        />
                    ))}
                </div>
            </div>
        </section>
    );
};

export default LandingFAQ;
