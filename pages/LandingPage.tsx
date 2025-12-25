import React, { useEffect } from 'react';
import { Page } from '../types';
import LandingNavbar from '../components/LandingNavbar';
import LandingHero from '../components/LandingHero';
import LandingFeatures from '../components/LandingFeatures';
import LandingDashboardPreview from '../components/LandingDashboardPreview';
import LandingWhoItsFor from '../components/LandingWhoItsFor';
import LandingPricing from '../components/LandingPricing';
import LandingFooter from '../components/LandingFooter';
import { ChevronRight, Shield, Database, Lock } from 'lucide-react';

interface LandingPageProps {
    onNavigate: (page: Page) => void;
}

const LandingPage: React.FC<LandingPageProps> = ({ onNavigate }) => {
    useEffect(() => {
        // Ensure we start at the top
        window.scrollTo(0, 0);
    }, []);

    return (
        <div className="bg-slate-950 min-h-screen selection:bg-brand-500/30">
            <LandingNavbar onNavigate={onNavigate} />

            <main>
                <LandingHero onNavigate={onNavigate} />

                <LandingFeatures />

                <LandingDashboardPreview />

                <LandingWhoItsFor />

                <LandingPricing />

                {/* Trust & Compliance Section */}
                <section className="py-20 bg-slate-950 border-y border-slate-900">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
                            <div className="flex flex-col items-center text-center">
                                <div className="w-12 h-12 rounded-full bg-brand-500/10 flex items-center justify-center mb-4">
                                    <Shield className="text-brand-500" size={24} />
                                </div>
                                <h4 className="text-white font-bold mb-2">SEBI Compliant</h4>
                                <p className="text-slate-400 text-sm">We adhere to all regulatory guidelines and data protection standards.</p>
                            </div>
                            <div className="flex flex-col items-center text-center">
                                <div className="w-12 h-12 rounded-full bg-teal-500/10 flex items-center justify-center mb-4">
                                    <Database className="text-teal-500" size={24} />
                                </div>
                                <h4 className="text-white font-bold mb-2">99.99% Data Accuracy</h4>
                                <p className="text-slate-400 text-sm">Direct market feeds ensured by official exchange connectivity.</p>
                            </div>
                            <div className="flex flex-col items-center text-center">
                                <div className="w-12 h-12 rounded-full bg-brand-600/10 flex items-center justify-center mb-4">
                                    <Lock className="text-brand-600" size={24} />
                                </div>
                                <h4 className="text-white font-bold mb-2">Enterprise Security</h4>
                                <p className="text-slate-400 text-sm">Your strategy and financial data are encrypted and kept private.</p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Final CTA Section */}
                <section className="py-24 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-brand-500/10 blur-[120px] rounded-full -z-10 translate-x-1/2 -translate-y-1/2" />

                    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                        <h2 className="text-4xl md:text-6xl font-black text-white mb-6">Start Using the Platform in Minutes</h2>
                        <p className="text-xl text-slate-400 mb-10 leading-relaxed">
                            Join thousands of traders who are already leveraging AI to gain an unfair advantage in the stock market.
                        </p>
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                            <button
                                onClick={() => onNavigate(Page.SIGNUP)}
                                className="w-full sm:w-auto bg-brand-500 hover:bg-brand-600 text-white px-10 py-5 rounded-2xl font-black text-xl transition-all shadow-2xl shadow-brand-500/40 flex items-center justify-center gap-3 group"
                            >
                                Sign Up Free
                                <ChevronRight className="group-hover:translate-x-1 transition-transform" />
                            </button>
                            <button
                                onClick={() => onNavigate(Page.LOGIN)}
                                className="w-full sm:w-auto bg-slate-900 border border-slate-700 hover:bg-slate-800 text-white px-10 py-5 rounded-2xl font-black text-xl transition-all"
                            >
                                Login
                            </button>
                        </div>
                    </div>
                </section>
            </main>

            <LandingFooter />
        </div>
    );
};

export default LandingPage;
