import React, { useState } from 'react';
import { Calculator, X, RefreshCw } from 'lucide-react';

interface PositionSizeCalculatorProps {
  isOpen: boolean;
  onClose: () => void;
}

const PositionSizeCalculator: React.FC<PositionSizeCalculatorProps> = ({ isOpen, onClose }) => {
  const [capital, setCapital] = useState<number>(100000);
  const [riskPercent, setRiskPercent] = useState<number>(2.0);
  const [entryPrice, setEntryPrice] = useState<number>(1500);
  const [stopLoss, setStopLoss] = useState<number>(1450);

  if (!isOpen) return null;

  // Calculations
  const riskAmount = (capital * riskPercent) / 100.0;
  const stopLossDistance = Math.max(0.01, entryPrice - stopLoss);
  const stopLossPercent = (stopLossDistance / entryPrice) * 100.0;
  const recommendedQty = Math.floor(riskAmount / stopLossDistance);
  const allocatedCapital = recommendedQty * entryPrice;
  const capitalUsagePercent = (allocatedCapital / capital) * 100.0;
  const rMultiple = 3.0; // standard 1:3 RR target
  const targetPrice = entryPrice + (stopLossDistance * rMultiple);

  const resetCalculator = () => {
    setCapital(100000);
    setRiskPercent(2.0);
    setEntryPrice(1500);
    setStopLoss(1450);
  };

  return (
    <div className="fixed bottom-20 right-6 z-50 w-80 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-5 text-slate-100 flex flex-col gap-4 animate-in slide-in-from-bottom-5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2 text-brand-400">
          <Calculator size={18} />
          <h3 className="font-bold text-sm">Position Sizing Risk Calculator</h3>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={resetCalculator} className="p-1 hover:bg-slate-800 rounded text-slate-500 hover:text-slate-300">
            <RefreshCw size={13} />
          </button>
          <button onClick={onClose} className="p-1 hover:bg-slate-800 rounded text-slate-500 hover:text-slate-300">
            <X size={15} />
          </button>
        </div>
      </div>

      {/* Input controls */}
      <div className="space-y-3">
        <div>
          <label className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Trading Capital (₹)</label>
          <input
            type="number"
            value={capital}
            onChange={(e) => setCapital(parseFloat(e.target.value) || 0)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 mt-1 text-sm font-mono focus:border-brand-500 focus:outline-none"
          />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Risk per Trade (%)</label>
            <input
              type="number"
              value={riskPercent}
              onChange={(e) => setRiskPercent(parseFloat(e.target.value) || 0)}
              step="0.1"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 mt-1 text-sm font-mono focus:border-brand-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Risk Amount (₹)</label>
            <div className="w-full bg-slate-950 border border-slate-800/50 rounded-lg p-2 mt-1 text-sm font-mono text-slate-500">
              ₹{riskAmount.toFixed(0)}
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Entry Price (₹)</label>
            <input
              type="number"
              value={entryPrice}
              onChange={(e) => setEntryPrice(parseFloat(e.target.value) || 0)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 mt-1 text-sm font-mono focus:border-brand-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Stop Loss (₹)</label>
            <input
              type="number"
              value={stopLoss}
              onChange={(e) => setStopLoss(parseFloat(e.target.value) || 0)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 mt-1 text-sm font-mono focus:border-brand-500 focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Outputs */}
      <div className="bg-slate-950 rounded-xl p-3 border border-slate-800/40 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">Stop Loss Distance:</span>
          <span className="font-bold font-mono">₹{stopLossDistance.toFixed(2)} ({stopLossPercent.toFixed(2)}%)</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">Allocated Capital:</span>
          <span className="font-bold font-mono">₹{allocatedCapital.toLocaleString()} ({capitalUsagePercent.toFixed(1)}%)</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">Target (1:3 RR):</span>
          <span className="font-bold font-mono text-emerald-400">₹{targetPrice.toFixed(2)}</span>
        </div>
        <div className="flex flex-col items-center justify-center pt-2 mt-2 border-t border-slate-800/60">
          <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Recommended Quantity</span>
          <span className="text-2xl font-black text-brand-400 font-mono mt-1">{recommendedQty}</span>
          <span className="text-[9px] text-slate-500 mt-1">Shares of NSE Asset</span>
        </div>
      </div>
    </div>
  );
};

export default PositionSizeCalculator;
