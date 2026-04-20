import React, { useState } from 'react';
import { BrainCircuit, ArrowRight, CheckCircle, Loader2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface SignupProps {
  onSignup: () => void;
  onSwitchToLogin: () => void;
}

const Signup: React.FC<SignupProps> = ({ onSignup, onSwitchToLogin }) => {
  const [formData, setFormData] = useState({
    firstName: '', lastName: '', email: '', password: '', confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { signup, signInWithGoogle } = useAuth();

  const handleSubmit = async () => {
    if (!formData.email || !formData.password || !formData.firstName) {
      setError('Please fill in all required fields');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    setError('');
    try {
      await signup(formData.email, formData.password);
      onSignup();
    } catch (e: any) {
      console.error('Signup error:', e);
      setError(e.message || 'Signup failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError('');
    try {
      await signInWithGoogle();
      onSignup();
    } catch (err: any) {
      setError(err.message || 'Google sign in failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-900 dark:to-slate-800 p-6">
      <div className="glass-panel w-full max-w-5xl h-auto min-h-[650px] rounded-3xl shadow-2xl overflow-hidden flex flex-col md:flex-row">

        {/* Left Side - Benefits */}
        <div className="w-full md:w-1/2 bg-slate-900 p-12 text-white flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 mb-10">
              <div className="w-10 h-10 bg-brand-600 rounded-xl flex items-center justify-center">
                <BrainCircuit className="text-white" size={24} />
              </div>
              <span className="font-display font-bold text-2xl tracking-tight">QuantAI</span>
            </div>

            <h2 className="text-3xl font-display font-bold mb-6">Start your AI trading journey.</h2>

            <div className="space-y-6">
              <div className="flex items-start gap-4">
                <CheckCircle className="text-brand-500 mt-1" size={20} />
                <div>
                  <h4 className="font-semibold text-lg">Automated NIFTY Scanning</h4>
                  <p className="text-slate-400 text-sm">Our AI scans NIFTY 200 stocks in real-time to find breakout patterns.</p>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <CheckCircle className="text-brand-500 mt-1" size={20} />
                <div>
                  <h4 className="font-semibold text-lg">Risk Management Shield</h4>
                  <p className="text-slate-400 text-sm">Automatic position sizing and stop-loss protection based on your capital.</p>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <CheckCircle className="text-brand-500 mt-1" size={20} />
                <div>
                  <h4 className="font-semibold text-lg">Paper Trading Mode</h4>
                  <p className="text-slate-400 text-sm">Test strategies with virtual capital before deploying real money via Upstox.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-12 text-sm text-slate-500">
            © 2024 QuantAI India. SEBI Registration Pending.
          </div>
        </div>

        {/* Right Side - Form */}
        <div className="w-full md:w-1/2 bg-white dark:bg-slate-800 p-12 flex flex-col justify-center">
          <div className="max-w-md mx-auto w-full">
            <h3 className="text-3xl font-bold text-slate-900 dark:text-white mb-6">Create Account</h3>

            <form className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-1">First Name</label>
                  <input
                    type="text"
                    value={formData.firstName}
                    onChange={e => setFormData({ ...formData, firstName: e.target.value })}
                    className="w-full px-4 py-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 outline-none focus:border-brand-500 transition-colors dark:text-white" placeholder="Arjun"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Last Name</label>
                  <input
                    type="text"
                    value={formData.lastName}
                    onChange={e => setFormData({ ...formData, lastName: e.target.value })}
                    className="w-full px-4 py-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 outline-none focus:border-brand-500 transition-colors dark:text-white" placeholder="Kumar"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={e => setFormData({ ...formData, email: e.target.value })}
                  className="w-full px-4 py-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 outline-none focus:border-brand-500 transition-colors dark:text-white" placeholder="arjun@example.com"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Password</label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={e => setFormData({ ...formData, password: e.target.value })}
                  className="w-full px-4 py-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 outline-none focus:border-brand-500 transition-colors dark:text-white" placeholder="Create a strong password"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Confirm Password</label>
                <input
                  type="password"
                  value={formData.confirmPassword}
                  onChange={e => setFormData({ ...formData, confirmPassword: e.target.value })}
                  className="w-full px-4 py-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 outline-none focus:border-brand-500 transition-colors dark:text-white" placeholder="Confirm your password"
                />
              </div>

              {error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                </div>
              )}

              <button
                type="button"
                onClick={handleSubmit}
                disabled={loading}
                className="w-full bg-brand-600 hover:bg-brand-700 text-white font-semibold py-3.5 rounded-xl transition-all shadow-lg shadow-brand-500/30 flex items-center justify-center gap-2 mt-4 disabled:opacity-70"
              >
                {loading ? <Loader2 className="animate-spin" /> : <>Create Account <ArrowRight size={18} /></>}
              </button>

              <button
                type="button"
                onClick={handleGoogleLogin}
                disabled={loading}
                className="w-full bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-600 text-slate-700 dark:text-white font-semibold py-3.5 rounded-xl transition-all border border-slate-200 dark:border-slate-600 flex items-center justify-center gap-2 mt-4"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                Sign up with Google
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
              Already have an account? <button onClick={onSwitchToLogin} className="text-brand-600 font-semibold hover:underline">Login</button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Signup;
