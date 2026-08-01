import React from 'react';
import { Page } from '../types';
import { TrendingUp, Menu, X } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';

interface LandingNavbarProps {
    onNavigate: (page: Page) => void;
}

const LandingNavbar: React.FC<LandingNavbarProps> = ({ onNavigate }) => {
    const { user } = useAuth();
    const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

    return (
        <motion.nav 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="fixed top-0 left-0 right-0 z-50 bg-[#050816]/75 backdrop-blur-xl border-b border-blue-400/10"
        >
            <div className="max-w-[1440px] mx-auto px-6 lg:px-20">
                <div className="flex items-center justify-between h-20">
                    {/* Logo */}
                    <div 
                        className="flex items-center gap-2.5 cursor-pointer group" 
                        onClick={() => onNavigate(Page.LANDING)}
                    >
                        <div className="bg-gradient-to-br from-blue-500 to-violet-600 p-2 rounded-xl shadow-lg shadow-blue-500/20 group-hover:scale-105 transition-transform duration-300">
                            <TrendingUp className="text-white" size={18} />
                        </div>
                        <span className="text-xl font-bold text-white tracking-tight">
                            QuantAI<span className="bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent">India</span>
                        </span>
                    </div>

                    {/* Desktop Navigation Links */}
                    <div className="hidden md:flex items-center gap-10">
                        <a href="#features" className="text-slate-400 hover:text-white transition-colors text-sm font-medium tracking-wide">Features</a>
                        <a href="#workflow" className="text-slate-400 hover:text-white transition-colors text-sm font-medium tracking-wide">Workflow</a>
                        <a href="#metrics" className="text-slate-400 hover:text-white transition-colors text-sm font-medium tracking-wide">Performance</a>
                        <a href="#pricing" className="text-slate-400 hover:text-white transition-colors text-sm font-medium tracking-wide">Pricing</a>
                        <a href="#faq" className="text-slate-400 hover:text-white transition-colors text-sm font-medium tracking-wide">FAQ</a>
                    </div>

                    {/* Desktop CTA Action Buttons */}
                    <div className="hidden md:flex items-center gap-4">
                        {user ? (
                            <button
                                onClick={() => onNavigate(Page.DASHBOARD)}
                                className="relative group px-6 py-2.5 bg-gradient-to-r from-blue-500 to-violet-600 text-white rounded-full text-sm font-semibold transition-all hover:shadow-[0_0_20px_rgba(96,165,250,0.4)]"
                            >
                                Go to Dashboard
                            </button>
                        ) : (
                            <>
                                <button
                                    onClick={() => onNavigate(Page.LOGIN)}
                                    className="text-slate-300 hover:text-white transition-colors text-sm font-medium px-4 py-2"
                                >
                                    Log In
                                </button>
                                <button
                                    onClick={() => onNavigate(Page.SIGNUP)}
                                    className="relative group overflow-hidden rounded-full p-[1px] focus:outline-none"
                                >
                                    <span className="absolute inset-0 bg-gradient-to-r from-blue-500 to-violet-600 rounded-full" />
                                    <div className="relative px-6 py-2.5 bg-[#050816] rounded-full text-white text-sm font-semibold transition-all group-hover:bg-transparent duration-300">
                                        Get Started
                                    </div>
                                </button>
                            </>
                        )}
                    </div>

                    {/* Mobile Menu Toggle Button */}
                    <div className="flex md:hidden">
                        <button
                            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                            className="text-slate-400 hover:text-white p-2"
                        >
                            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
                        </button>
                    </div>
                </div>
            </div>

            {/* Mobile Menu Panel */}
            <AnimatePresence>
                {mobileMenuOpen && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3 }}
                        className="md:hidden bg-[#050816] border-b border-blue-400/10"
                    >
                        <div className="px-6 py-6 space-y-4 flex flex-col">
                            <a 
                                href="#features" 
                                onClick={() => setMobileMenuOpen(false)}
                                className="text-slate-400 hover:text-white text-base font-medium py-2 border-b border-slate-900"
                            >
                                Features
                            </a>
                            <a 
                                href="#workflow" 
                                onClick={() => setMobileMenuOpen(false)}
                                className="text-slate-400 hover:text-white text-base font-medium py-2 border-b border-slate-900"
                            >
                                Workflow
                            </a>
                            <a 
                                href="#metrics" 
                                onClick={() => setMobileMenuOpen(false)}
                                className="text-slate-400 hover:text-white text-base font-medium py-2 border-b border-slate-900"
                            >
                                Performance
                            </a>
                            <a 
                                href="#pricing" 
                                onClick={() => setMobileMenuOpen(false)}
                                className="text-slate-400 hover:text-white text-base font-medium py-2 border-b border-slate-900"
                            >
                                Pricing
                            </a>
                            <a 
                                href="#faq" 
                                onClick={() => setMobileMenuOpen(false)}
                                className="text-slate-400 hover:text-white text-base font-medium py-2 border-b border-slate-900"
                            >
                                FAQ
                            </a>
                            <div className="pt-4 space-y-4">
                                {user ? (
                                    <button
                                        onClick={() => {
                                            setMobileMenuOpen(false);
                                            onNavigate(Page.DASHBOARD);
                                        }}
                                        className="w-full text-center py-3 bg-gradient-to-r from-blue-500 to-violet-600 text-white rounded-xl font-semibold text-sm"
                                    >
                                        Go to Dashboard
                                    </button>
                                ) : (
                                    <>
                                        <button
                                            onClick={() => {
                                                setMobileMenuOpen(false);
                                                onNavigate(Page.LOGIN);
                                            }}
                                            className="w-full text-center py-3 text-slate-300 hover:text-white border border-slate-800 rounded-xl font-medium text-sm"
                                        >
                                            Log In
                                        </button>
                                        <button
                                            onClick={() => {
                                                setMobileMenuOpen(false);
                                                onNavigate(Page.SIGNUP);
                                            }}
                                            className="w-full text-center py-3 bg-gradient-to-r from-blue-500 to-violet-600 text-white rounded-xl font-semibold text-sm"
                                        >
                                            Get Started
                                        </button>
                                    </>
                                )}
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.nav>
    );
};

export default LandingNavbar;
