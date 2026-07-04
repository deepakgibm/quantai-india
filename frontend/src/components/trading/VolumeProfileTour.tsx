import React, { useState } from 'react';
import { X, ChevronRight, ChevronLeft, Award } from 'lucide-react';

interface TourStep {
  title: string;
  description: string;
  target?: string;
}

interface VolumeProfileTourProps {
  onClose: () => void;
}

const TOUR_STEPS: TourStep[] = [
  {
    title: "Step 1: Candlestick Chart Terminal",
    description: "This is the primary price feed showing hollow/solid candlesticks. You can drag to pan, scroll to zoom, and drag the vertical axis to scale the price levels.",
  },
  {
    title: "Step 2: Volume Profile Histogram",
    description: "The horizontal bars on the right side of the chart show the distribution of volume traded at each price level. Longer bars indicate heavier market interest.",
  },
  {
    title: "Step 3: Point of Control (POC)",
    description: "The yellow dashed line represents the single price level with the highest traded volume. Price tends to return to this level (acting as a gravity magnet).",
  },
  {
    title: "Step 4: Value Area High (VAH)",
    description: "The green dashed line represents the upper boundary of the Value Area, where 70% of the session volume was traded. Acceptance above VAH is a bullish indicator.",
  },
  {
    title: "Step 5: Value Area Low (VAL)",
    description: "The red dashed line represents the lower boundary of the Value Area. Breaks below VAL often trigger rapid selling or institutional rejection.",
  },
  {
    title: "Step 6: High Volume Nodes (HVNs)",
    description: "Indigo horizontal lines show minor peaks in volume distribution. These act as strong support and resistance areas where buyers and sellers exchange blocks.",
  },
  {
    title: "Step 7: Low Volume Nodes (LVNs)",
    description: "Rose horizontal lines show valleys in volume distribution. Because very little trading occurred here, price tends to cross these zones extremely quickly.",
  },
  {
    title: "Step 8: AI Market Verdict",
    description: "The top card in the right sidebar displays the consolidated bias score (0-100), the action recommendation (BUY/SELL/HOLD), and a detailed explanation of the triggers.",
  },
  {
    title: "Step 9: Risk Management Panel",
    description: "This panel automatically calculates the optimal Entry Zone, Stop Loss, and Targets (1, 2, and 3) based on the VAH, VAL, and current volatility of the asset.",
  }
];

const VolumeProfileTour: React.FC<VolumeProfileTourProps> = ({ onClose }) => {
  const [currentStep, setCurrentStep] = useState(0);

  const handleNext = () => {
    if (currentStep < TOUR_STEPS.length - 1) {
      setCurrentStep(prev => prev + 1);
    } else {
      handleComplete();
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const handleComplete = () => {
    localStorage.setItem('volume_profile_tour_completed', 'true');
    onClose();
  };

  const step = TOUR_STEPS[currentStep];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-850 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
        
        {/* Decorative elements */}
        <div className="absolute -right-16 -top-16 w-32 h-32 rounded-full bg-brand-500/10 blur-xl pointer-events-none" />
        <div className="absolute -left-16 -bottom-16 w-32 h-32 rounded-full bg-violet-500/10 blur-xl pointer-events-none" />
        
        {/* Header */}
        <div className="flex justify-between items-center mb-4 pb-3 border-b border-slate-850">
          <div className="flex items-center gap-2">
            <Award className="text-brand-400" size={18} />
            <span className="text-xs font-black font-mono tracking-widest text-slate-400 uppercase">Onboarding Guide</span>
          </div>
          <button 
            onClick={handleComplete} 
            className="text-slate-500 hover:text-white transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Step Content */}
        <div className="space-y-3 min-h-[140px]">
          <h3 className="text-base font-bold text-white font-display">
            {step.title}
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed font-medium">
            {step.description}
          </p>
        </div>

        {/* Progress & Controls */}
        <div className="mt-6 flex items-center justify-between pt-4 border-t border-slate-850">
          <div className="flex items-center gap-1">
            {TOUR_STEPS.map((_, idx) => (
              <span 
                key={idx}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  idx === currentStep ? 'w-4 bg-brand-500' : 'w-1.5 bg-slate-800'
                }`}
              />
            ))}
          </div>
          
          <div className="flex items-center gap-2.5">
            <button
              onClick={handleComplete}
              className="text-[10px] uppercase font-bold tracking-wider text-slate-500 hover:text-slate-300 transition-colors"
            >
              Skip
            </button>
            
            {currentStep > 0 && (
              <button
                onClick={handlePrev}
                className="p-1.5 rounded bg-slate-800 hover:bg-slate-750 text-slate-300 transition-colors border border-slate-700/40"
              >
                <ChevronLeft size={14} />
              </button>
            )}
            
            <button
              onClick={handleNext}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-brand-650 hover:bg-brand-600 text-white text-xs font-bold transition-all shadow-lg shadow-brand-500/10"
            >
              {currentStep === TOUR_STEPS.length - 1 ? 'Finish' : 'Next'} <ChevronRight size={12} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VolumeProfileTour;
