import React from 'react';
import { motion } from 'framer-motion';
import { MessageSquare, Quote, Star } from 'lucide-react';

const testimonials = [
    {
        quote: "QuantAI has completely replaced my manual Excel sheet filters. The AI Swarm consensus has saved me hours of daily research and the accuracy is unmatched.",
        author: "Rajesh Malhotra",
        role: "Full-time Swing Trader",
        avatar: "RM",
        rating: 5
    },
    {
        quote: "The multi-agent architecture is a game-changer. It evaluates a stock from both fundamental and technical dimensions simultaneously without any emotional bias.",
        author: "Dr. Amit Krishnan",
        role: "Quantitative Researcher",
        avatar: "AK",
        rating: 5
    },
    {
        quote: "Real-time sector analysis and live breakout scanners are incredibly fast. The SEBI compliance and direct exchange data lineage give me massive confidence.",
        author: "Priyanjali Sharma",
        role: "Portfolio Manager",
        avatar: "PS",
        rating: 5
    }
];

const LandingTestimonials: React.FC = () => {
    return (
        <section id="testimonials" className="relative py-32 bg-[#050816] overflow-hidden border-t border-blue-400/10">
            {/* Background elements */}
            <div className="absolute inset-0 bg-grid-pattern opacity-100 pointer-events-none" />
            
            <div className="max-w-[1440px] mx-auto px-6 lg:px-20 relative z-10">
                {/* Section Header */}
                <div className="text-center max-w-3xl mx-auto mb-20">
                    <motion.span 
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-blue-400/30 bg-blue-500/10 text-blue-300 text-xs font-semibold uppercase tracking-widest mb-4"
                    >
                        <span>User Stories</span>
                    </motion.span>
                    
                    <motion.h2 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.1 }}
                        className="text-3xl sm:text-4xl lg:text-5xl font-serif font-bold text-white tracking-tight"
                    >
                        Trusted by Active Investors
                    </motion.h2>
                    
                    <motion.p 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.2 }}
                        className="text-slate-400 text-base sm:text-lg mt-4 leading-relaxed font-normal"
                    >
                        Hear from the community of quants, swing traders, and analysts leveraging our AI swarms daily.
                    </motion.p>
                </div>

                {/* Testimonials Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {testimonials.map((t, idx) => (
                        <motion.div 
                            key={idx}
                            initial={{ opacity: 0, y: 25 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, margin: '-50px' }}
                            transition={{ duration: 0.5, delay: idx * 0.1 }}
                            className="bg-[#0E1425] border border-blue-400/15 p-8 rounded-3xl relative flex flex-col justify-between hover:border-blue-400/30 transition-all duration-300"
                        >
                            <Quote className="absolute top-6 right-8 text-blue-400/5 pointer-events-none" size={60} />
                            
                            <div>
                                {/* Rating Stars */}
                                <div className="flex gap-1.5 mb-6 text-yellow-400">
                                    {[...Array(t.rating)].map((_, i) => (
                                        <Star key={i} size={14} className="fill-yellow-400" />
                                    ))}
                                </div>

                                <p className="text-slate-300 text-sm leading-relaxed mb-8 italic">
                                    "{t.quote}"
                                </p>
                            </div>

                            {/* User details */}
                            <div className="flex items-center gap-4 border-t border-blue-400/10 pt-6">
                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center font-bold text-xs text-white">
                                    {t.avatar}
                                </div>
                                <div>
                                    <h4 className="text-white text-sm font-extrabold">{t.author}</h4>
                                    <span className="text-[11px] text-slate-500 font-semibold">{t.role}</span>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
};

export default LandingTestimonials;
