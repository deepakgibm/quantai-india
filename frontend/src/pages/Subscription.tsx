import React, { useState, useEffect } from 'react';
import { CreditCard, Check, ShieldCheck, Loader2, Sparkles, Receipt } from 'lucide-react';
import { api } from '../services/api';

const Subscription: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Coupon input
  const [couponCode, setCouponCode] = useState('');
  const [discountPercent, setDiscountPercent] = useState<number>(0);
  const [couponError, setCouponError] = useState<string | null>(null);
  const [couponApplied, setCouponApplied] = useState(false);
  
  // Payment Simulation
  const [paying, setPaying] = useState(false);
  const [checkoutSession, setCheckoutSession] = useState<any>(null);

  const fetchSubscriptionDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getSubscriptionDashboard();
      if (response && response.status === 'success') {
        setData(response);
      } else {
        setError('Failed to fetch billing status');
      }
    } catch (e: any) {
      setError(e.message || 'Error communicating with billing server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubscriptionDashboard();
  }, []);

  const handleApplyCoupon = () => {
    setCouponError(null);
    setDiscountPercent(0);
    setCouponApplied(false);
    if (!couponCode) return;
    
    // Simulate/mock coupon verification for frontend robustness
    const code = couponCode.toUpperCase();
    if (code === 'WELCOME10') {
      setDiscountPercent(10);
      setCouponApplied(true);
    } else if (code === 'QUANT20') {
      setDiscountPercent(20);
      setCouponApplied(true);
    } else {
      setCouponError('Invalid or expired coupon code.');
    }
  };

  const handleSelectPlan = async (plan: string) => {
    setPaying(true);
    try {
      const checkoutRes = await api.createSubscriptionCheckout(plan, couponApplied ? couponCode : undefined);
      if (checkoutRes && checkoutRes.status === 'success') {
        setCheckoutSession(checkoutRes.session);
        // Simulate payment process (2 seconds delay)
        setTimeout(async () => {
          await completeSimulatedPayment(checkoutRes.session.subscription_id);
        }, 2000);
      }
    } catch (e: any) {
      alert(e.message || 'Checkout failed');
      setPaying(false);
    }
  };

  const completeSimulatedPayment = async (subscriptionId: number) => {
    try {
      const result = await api.verifySubscriptionPayment(subscriptionId, `pay_sim_${Date.now()}`);
      if (result && result.status === 'success') {
        setCheckoutSession(null);
        await fetchSubscriptionDashboard();
        alert('Payment completed successfully! Subscription activated.');
      }
    } catch (e: any) {
      alert(e.message || 'Payment confirmation failed');
    } finally {
      setPaying(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 size={40} className="text-brand-500 animate-spin mb-4" />
        <p className="text-slate-400">Loading Billing Dashboard...</p>
      </div>
    );
  }

  const currentPlan = data?.subscription?.plan_name || 'FREE';
  const plans = [
    {
      name: 'FREE',
      price: 0,
      description: 'Standard access for casual traders looking to inspect indices.',
      features: ['Nifty 50 basic tracking', '1 Daily AI Market prompt limit', 'Standard scanners (15m delay)', 'Academy introductory courses'],
      cta: 'Current Plan',
      disabled: currentPlan === 'FREE'
    },
    {
      name: 'PRO',
      price: 999,
      description: 'Advanced features for active swing traders and investors.',
      features: ['Real-time scanner engine', 'Unlimited AI prompts with context', 'Sector rotation heatmaps', 'Access to Pro Academy & Quizzes', 'Email research newsletters'],
      cta: currentPlan === 'PRO' ? 'Active Plan' : currentPlan === 'ELITE' ? 'Downgrade' : 'Upgrade to Pro',
      disabled: currentPlan === 'PRO'
    },
    {
      name: 'ELITE',
      price: 2999,
      description: 'Full institutional suite for quantitative algo developers.',
      features: ['HFT vector backtests & Walk-forward', 'Smart Money Concepts analytics', 'Chart Pattern recognition AI', 'Advanced risk limit engine', 'Elite certifications & newsletters'],
      cta: currentPlan === 'ELITE' ? 'Active Plan' : 'Go Elite',
      disabled: currentPlan === 'ELITE'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white font-display">Subscription Management</h1>
        <p className="text-xs text-slate-500 font-semibold mt-1">
          Choose a subscription tier, apply discount coupons, and view invoices.
        </p>
      </div>

      {/* Subscription Tier Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {plans.map((p) => {
          const discountAmt = p.price * (discountPercent / 100);
          const discountedPrice = p.price - discountAmt;
          const gst = discountedPrice * 0.18;
          const finalPrice = discountedPrice + gst;
          const isActive = currentPlan === p.name;

          return (
            <div
              key={p.name}
              className={`relative rounded-2xl p-6 border flex flex-col justify-between transition-all duration-300 ${
                isActive
                  ? 'bg-slate-900 border-brand-500/50 shadow-xl shadow-brand-500/5 text-white'
                  : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 hover:scale-[1.01]'
              }`}
            >
              {p.name === 'ELITE' && (
                <div className="absolute -top-3 right-6 bg-gradient-to-r from-brand-500 to-purple-600 text-white text-[9px] font-black uppercase tracking-widest px-3 py-1 rounded-full shadow flex items-center gap-1">
                  <Sparkles size={10} /> Best Value
                </div>
              )}

              <div>
                <h3 className="text-lg font-bold tracking-tight">{p.name} PLAN</h3>
                <p className={`text-xs mt-2 leading-relaxed ${isActive ? 'text-slate-400' : 'text-slate-500 dark:text-slate-400'}`}>
                  {p.description}
                </p>

                <div className="mt-5 flex items-baseline gap-1">
                  <span className="text-3xl font-black font-mono">₹{p.price > 0 ? (discountPercent > 0 ? discountedPrice : p.price) : 0}</span>
                  <span className="text-xs text-slate-500">/ month</span>
                </div>

                {p.price > 0 && discountPercent > 0 && (
                  <span className="text-[10px] text-emerald-500 font-bold block mt-1">
                    Coupon discount applied: -₹{discountAmt.toFixed(0)} ({discountPercent}% Off)
                  </span>
                )}

                {p.price > 0 && (
                  <span className="text-[10px] text-slate-400 block mt-1 font-mono">
                    +₹{gst.toFixed(0)} GST (18% inclusive final: ₹{finalPrice.toFixed(0)})
                  </span>
                )}

                {/* Features list */}
                <ul className="space-y-3 mt-6 border-t border-slate-100 dark:border-slate-700/50 pt-5">
                  {p.features.map((f, idx) => (
                    <li key={idx} className="flex items-start gap-2.5 text-xs">
                      <Check size={14} className="text-brand-500 mt-0.5 shrink-0" />
                      <span className={isActive ? 'text-slate-300' : 'text-slate-600 dark:text-slate-300'}>{f}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="mt-8">
                <button
                  disabled={p.disabled || paying}
                  onClick={() => handleSelectPlan(p.name)}
                  className={`w-full py-3 px-4 rounded-xl text-xs font-bold uppercase tracking-wider transition-all ${
                    isActive
                      ? 'bg-slate-800 text-slate-400 border border-slate-700 cursor-default'
                      : 'bg-gradient-to-r from-brand-600 to-purple-600 hover:from-brand-500 hover:to-purple-500 text-white shadow shadow-brand-500/10'
                  } disabled:opacity-50`}
                >
                  {paying && !isActive ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader2 size={13} className="animate-spin" /> Simulating Razorpay...
                    </span>
                  ) : (
                    p.cta
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Coupon Section */}
      {currentPlan !== 'ELITE' && (
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-6 shadow-sm max-w-md">
          <h3 className="font-bold text-sm text-slate-800 dark:text-white flex items-center gap-2">
            <Sparkles size={16} className="text-brand-500" /> Apply Coupon Code
          </h3>
          <div className="flex gap-2 mt-3">
            <input
              type="text"
              placeholder="e.g. WELCOME10, QUANT20"
              value={couponCode}
              onChange={(e) => setCouponCode(e.target.value)}
              className="flex-grow bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 text-xs uppercase font-mono focus:border-brand-500 focus:outline-none text-slate-800 dark:text-slate-100"
            />
            <button
              onClick={handleApplyCoupon}
              className="bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-slate-200 dark:text-slate-900 px-5 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0"
            >
              Apply
            </button>
          </div>
          {couponError && <p className="text-red-500 text-[10px] font-bold mt-2">{couponError}</p>}
          {couponApplied && (
            <p className="text-emerald-500 text-[10px] font-bold mt-2">
              Success! Coupon code applied ({discountPercent}% discount). Select upgrade above to pay.
            </p>
          )}
        </div>
      )}

      {/* Invoice History */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-6 shadow-sm">
        <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4 flex items-center gap-2">
          <Receipt size={16} className="text-brand-500" /> Invoice History
        </h3>
        
        {data?.invoices && data.invoices.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-700/50 text-[10px] text-slate-400 uppercase tracking-widest font-bold">
                  <th className="pb-3">Invoice Number</th>
                  <th className="pb-3">Date</th>
                  <th className="pb-3 text-right">Base Amount</th>
                  <th className="pb-3 text-right">Tax Inclusive Total</th>
                  <th className="pb-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/30 text-xs">
                {data.invoices.map((inv: any) => (
                  <tr key={inv.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-700/20">
                    <td className="py-3.5 font-bold text-brand-500 font-mono">{inv.invoice_number}</td>
                    <td className="py-3.5 text-slate-500">{inv.created_at}</td>
                    <td className="py-3.5 text-right font-mono">₹{inv.amount.toLocaleString()}</td>
                    <td className="py-3.5 text-right font-bold font-mono">₹{inv.total_amount.toLocaleString()}</td>
                    <td className="py-3.5 text-center">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        inv.status === 'PAID' ? 'bg-green-500/10 text-green-600' : 'bg-amber-500/10 text-amber-600'
                      }`}>
                        {inv.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-slate-500 italic">No invoices found. Plan transactions will appear here.</p>
        )}
      </div>
    </div>
  );
};

export default Subscription;
