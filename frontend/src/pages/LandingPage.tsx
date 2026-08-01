import React, { useEffect } from 'react';
import { Page } from '../types';
import LandingNavbar from '../components/LandingNavbar';
import LandingHero from '../components/LandingHero';
import LandingFeatures from '../components/LandingFeatures';
import LandingWorkflowTimeline from '../components/LandingWorkflowTimeline';
import LandingDashboardPreview from '../components/LandingDashboardPreview';
import LandingPerformanceMetrics from '../components/LandingPerformanceMetrics';
import LandingTestimonials from '../components/LandingTestimonials';
import LandingPricing from '../components/LandingPricing';
import LandingFAQ from '../components/LandingFAQ';
import LandingFooter from '../components/LandingFooter';

import { ChevronRight, Shield, Database, Lock, ArrowUpRight } from 'lucide-react';
import { motion } from 'framer-motion';

interface LandingPageProps {
    onNavigate: (page: Page) => void;
}

const LandingPage: React.FC<LandingPageProps> = ({ onNavigate }) => {
    useEffect(() => {
        // Ensure page resets to top on route change
        window.scrollTo(0, 0);
    }, []);

    return (
        <div className="bg-[#050816] min-h-screen selection:bg-blue-500/30 overflow-x-hidden font-sans">
            {/* Header / Navigation */}
            <LandingNavbar onNavigate={onNavigate} />

            <main>
                {/* Hero Section */}
                <LandingHero onNavigate={onNavigate} />

                {/* Features Section (Bento Grid) */}
                <LandingFeatures />

                {/* AI Workflow Timeline Section */}
                <LandingWorkflowTimeline />

                {/* Dashboard Workspace Preview Section */}
                <LandingDashboardPreview />

                {/* Performance Metrics Section */}
                <LandingPerformanceMetrics />

                {/* Testimonials Section */}
                <LandingTestimonials />

                {/* Pricing Plans Section */}
                <LandingPricing onNavigate={onNavigate} />

                {/* Trust & Lineage Indicators Section */}
                <section className="py-24 bg-[#050816] relative overflow-hidden border-t border-blue-400/10">
                    <div className="absolute inset-0 bg-grid-pattern opacity-100 pointer-events-none" />
                    <div className="max-w-[1440px] mx-auto px-6 lg:px-20 relative z-10">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                            
                            {/* Card 1: Compliant */}
                            <motion.div 
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.5 }}
                                className="bg-[#0E1425] border border-blue-400/15 p-8 rounded-3xl text-center flex flex-col items-center hover:border-blue-400/30 transition-all duration-300"
                            >
                                <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-6 text-blue-400 shadow-lg shadow-blue-500/5">
                                    <Shield size={20} />
                                </div>
                                <h4 className="text-white font-extrabold text-base mb-2 uppercase tracking-wide">SEBI Compliant Toolset</h4>
                                <p className="text-slate-400 text-sm leading-relaxed font-normal">
                                    We adhere strictly to regulatory guidelines, ensuring all products serve as analytics and decision-support calculators.
                                </p>
                            </motion.div>

                            {/* Card 2: Accuracy */}
                            <motion.div 
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.5, delay: 0.1 }}
                                className="bg-[#0E1425] border border-blue-400/15 p-8 rounded-3xl text-center flex flex-col items-center hover:border-blue-400/30 transition-all duration-300"
                            >
                                <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-6 text-emerald-400 shadow-lg shadow-emerald-500/5">
                                    <Database size={20} />
                                </div>
                                <h4 className="text-white font-extrabold text-base mb-2 uppercase tracking-wide">99.99% Ingestion Uptime</h4>
                                <p className="text-slate-400 text-sm leading-relaxed font-normal">
                                    Direct integration protocols keep live market feed pipelines fully operational, ensuring accurate tick capture.
                                </p>
                            </motion.div>

                            {/* Card 3: Security */}
                            <motion.div 
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.5, delay: 0.2 }}
                                className="bg-[#0E1425] border border-blue-400/15 p-8 rounded-3xl text-center flex flex-col items-center hover:border-blue-400/30 transition-all duration-300"
                            >
                                <div className="w-12 h-12 rounded-2xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center mb-6 text-violet-400 shadow-lg shadow-violet-500/5">
                                    <Lock size={20} />
                                </div>
                                <h4 className="text-white font-extrabold text-base mb-2 uppercase tracking-wide">Enterprise Vaulting</h4>
                                <p className="text-slate-400 text-sm leading-relaxed font-normal">
                                    Your custom algorithmic rules, watchlists, and portfolio metrics are secured using military-grade encryption.
                                </p>
                            </motion.div>
                        </div>
                    </div>
                </section>

                {/* FAQ Section */}
                <LandingFAQ />

                {/* Final Call to Action (CTA) Section */}
                <section className="py-32 relative overflow-hidden bg-[#050816] border-t border-blue-400/10">
                    <div className="absolute inset-0 bg-grid-pattern opacity-100 pointer-events-none" />
                    
                    {/* Glowing effect inside CTA */}
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[350px] bg-gradient-to-r from-blue-500/10 to-violet-600/10 rounded-full blur-[140px] pointer-events-none" />

                    <div className="max-w-4xl mx-auto px-6 text-center relative z-10">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.6 }}
                            className="bg-[#0E1425] border border-blue-400/20 rounded-[40px] p-8 sm:p-16 relative overflow-hidden shadow-[0_20px_50px_rgba(96,165,250,0.08)]"
                        >
                            <div className="absolute inset-0 bg-gradient-to-b from-blue-500/5 to-transparent pointer-events-none" />
                            
                            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-serif font-black text-white mb-6 leading-tight">
                                Launch Your Consensus <br />Swarm in Minutes
                            </h2>
                            <p className="text-slate-400 text-base sm:text-lg mb-10 leading-relaxed max-w-xl mx-auto font-normal">
                                Join thousands of active traders who are already leveraging AI swarms to identify high-probability swing setups.
                            </p>
                            
                            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                                <button
                                    onClick={() => onNavigate(Page.SIGNUP)}
                                    className="w-full sm:w-auto px-10 py-5 rounded-full bg-gradient-to-r from-blue-500 to-violet-600 hover:from-blue-600 hover:to-violet-700 text-white font-bold text-base shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all duration-300 flex items-center justify-center gap-2 group"
                                >
                                    Sign Up Free
                                    <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
                                </button>
                                <button
                                    onClick={() => onNavigate(Page.LOGIN)}
                                    className="w-full sm:w-auto px-10 py-5 rounded-full bg-white/[0.03] border border-blue-400/20 hover:bg-white/[0.08] text-slate-200 hover:text-white font-bold text-base transition-all duration-300"
                                >
                                    Log In to Console
                                </button>
                            </div>
                        </motion.div>
                    </div>
                </section>
            </main>

            {/* Footer */}
            <LandingFooter />
        </div>
    );
};

export default LandingPage;
