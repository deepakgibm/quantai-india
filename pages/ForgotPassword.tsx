import React, { useState } from 'react';
import { BrainCircuit, Loader2, ArrowLeft, Mail } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface ForgotPasswordProps {
    onBackToLogin: () => void;
}

const ForgotPassword: React.FC<ForgotPasswordProps> = ({ onBackToLogin }) => {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');
    const { resetPassword } = useAuth();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email) return setError('Please enter your email address');

        setLoading(true);
        setError('');
        setMessage('');

        try {
            await resetPassword(email);
            setMessage('Password reset email sent! Please check your inbox.');
        } catch (err: any) {
            setError(err.message || 'Failed to reset password. Please check your email.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-900 dark:to-slate-800 p-6">
            <div className="glass-panel w-full max-w-5xl h-[650px] rounded-3xl shadow-2xl overflow-hidden flex flex-col md:flex-row">

                {/* Left Side - Visual (Consitent with Login) */}
                <div className="w-full md:w-1/2 bg-brand-600 p-12 text-white flex flex-col justify-between relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-brand-500 rounded-full mix-blend-multiply filter blur-3xl opacity-50 -translate-y-1/2 translate-x-1/2"></div>
                    <div className="absolute bottom-0 left-0 w-64 h-64 bg-purple-600 rounded-full mix-blend-multiply filter blur-3xl opacity-50 translate-y-1/2 -translate-x-1/2"></div>

                    <div className="relative z-10">
                        <div className="flex items-center gap-3 mb-8">
                            <div className="w-10 h-10 bg-white/20 backdrop-blur-md rounded-xl flex items-center justify-center border border-white/30">
                                <BrainCircuit className="text-white" size={24} />
                            </div>
                            <span className="font-display font-bold text-2xl tracking-tight">QuantAI</span>
                        </div>
                        <h2 className="text-4xl font-display font-bold mb-6 leading-tight">
                            Secure Your Trading Journey.
                        </h2>
                        <p className="text-brand-100 text-lg leading-relaxed max-w-sm">
                            Don't lose access to your AI-powered trading tools. Resetting your password is quick and secure.
                        </p>
                    </div>
                </div>

                {/* Right Side - Form */}
                <div className="w-full md:w-1/2 bg-white dark:bg-slate-900 p-12 flex flex-col justify-center relative">
                    <div className="max-w-md mx-auto w-full">
                        <button
                            onClick={onBackToLogin}
                            className="flex items-center gap-2 text-slate-500 hover:text-brand-600 transition-colors mb-8 group"
                        >
                            <ArrowLeft size={18} className="group-hover:-translate-x-1 transition-transform" />
                            <span className="text-sm font-medium">Back to Login</span>
                        </button>

                        <h3 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">Reset Password</h3>
                        <p className="text-slate-500 dark:text-slate-400 mb-8">Enter your email and we'll send you instructions to reset your password.</p>

                        <form onSubmit={handleSubmit} className="space-y-5">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Email Address</label>
                                <div className="relative">
                                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                                        <Mail size={18} className="text-slate-400" />
                                    </div>
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="w-full pl-11 pr-4 py-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all outline-none text-slate-900 dark:text-white"
                                        placeholder="name@example.com"
                                        required
                                    />
                                </div>
                            </div>

                            {error && <p className="text-sm text-red-500 font-medium bg-red-50 dark:bg-red-900/20 p-3 rounded-lg border border-red-100 dark:border-red-900/50">{error}</p>}
                            {message && <p className="text-sm text-emerald-600 dark:text-emerald-400 font-medium bg-emerald-50 dark:bg-emerald-900/20 p-3 rounded-lg border border-emerald-100 dark:border-emerald-900/50">{message}</p>}

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full bg-brand-600 hover:bg-brand-700 text-white font-semibold py-3.5 rounded-xl transition-all shadow-lg shadow-brand-500/30 flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
                            >
                                {loading ? <Loader2 className="animate-spin" size={20} /> : 'Send Reset Link'}
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ForgotPassword;
