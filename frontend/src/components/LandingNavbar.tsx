import React from 'react';
import { Page } from '../types';
import { TrendingUp, LogOut } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface LandingNavbarProps {
    onNavigate: (page: Page) => void;
}

const LandingNavbar: React.FC<LandingNavbarProps> = ({ onNavigate }) => {
    const { user, logout } = useAuth();

    return (
        <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-900/80 backdrop-blur-md border-b border-slate-800">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    <div className="flex items-center gap-2 cursor-pointer" onClick={() => onNavigate(Page.LANDING)}>
                        <div className="bg-brand-500 p-1.5 rounded-lg">
                            <TrendingUp className="text-white" size={20} />
                        </div>
                        <span className="text-xl font-bold text-white tracking-tight">QuantAI<span className="text-brand-500">India</span></span>
                    </div>
                    <div className="hidden md:flex items-center gap-8">
                        <a href="#features" className="text-slate-300 hover:text-white transition-colors text-sm font-medium">Features</a>
                        <a href="#who-it-is-for" className="text-slate-300 hover:text-white transition-colors text-sm font-medium">Who It's For</a>
                        <a href="#pricing" className="text-slate-300 hover:text-white transition-colors text-sm font-medium">Pricing</a>
                    </div>
                    <div className="flex items-center gap-4">
                        {user ? (
                            <>
                                <button
                                    onClick={() => onNavigate(Page.DASHBOARD)}
                                    className="bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-lg shadow-brand-500/20"
                                >
                                    Go to Dashboard
                                </button>
                            </>
                        ) : (
                            <>
                                <button
                                    onClick={() => onNavigate(Page.LOGIN)}
                                    className="text-slate-300 hover:text-white transition-colors text-sm font-medium"
                                >
                                    Log In
                                </button>
                                <button
                                    onClick={() => onNavigate(Page.SIGNUP)}
                                    className="bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-lg shadow-brand-500/20"
                                >
                                    Get Started
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </nav>
    );
};

export default LandingNavbar;
