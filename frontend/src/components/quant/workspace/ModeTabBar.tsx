import React from 'react';
import {
  Grid,
  Play,
  TrendingUp,
  Activity,
  Sliders,
  Briefcase,
} from 'lucide-react';
import { useQuantContext } from '../../../contexts/QuantContext';
import { WorkspaceMode } from '../../../types/quant';

interface ModeConfig {
  mode: WorkspaceMode;
  icon: React.ReactNode;
  label: string;
  description: string;
}

const MODES: ModeConfig[] = [
  { mode: 'discovery',    icon: <Grid size={14} />,       label: 'Discovery',     description: 'Multi-strategy scan' },
  { mode: 'backtest',     icon: <Play size={14} />,       label: 'Backtest',      description: 'High-fidelity simulation' },
  { mode: 'portfolio',    icon: <Briefcase size={14} />,  label: 'Portfolio',     description: 'Multi-strategy compare' },
];

/**
 * Mode tab bar for the Quant Research Terminal.
 * Animated active indicator, description tooltips.
 */
const ModeTabBar: React.FC = () => {
  const { activeMode, setActiveMode, setError } = useQuantContext();

  return (
    <div className="flex items-stretch gap-0 bg-slate-950 border-b border-slate-800 shrink-0 overflow-x-auto">
      {MODES.map(({ mode, icon, label, description }) => {
        const isActive = activeMode === mode;
        return (
          <button
            key={mode}
            onClick={() => { setActiveMode(mode); setError(null); }}
            className={`
              relative flex flex-col items-center justify-center gap-0.5 px-5 py-3 min-w-[100px]
              text-xs font-semibold transition-all duration-200 shrink-0 group
              ${isActive
                ? 'text-white bg-slate-900/60'
                : 'text-slate-500 hover:text-slate-300 hover:bg-slate-900/30'
              }
            `}
            title={description}
          >
            {/* Active bottom indicator */}
            <div
              className={`absolute bottom-0 left-0 right-0 h-0.5 transition-all duration-300 ${
                isActive
                  ? 'bg-gradient-to-r from-brand-500 to-purple-500 opacity-100'
                  : 'bg-transparent opacity-0'
              }`}
            />

            <span className={`transition-colors ${isActive ? 'text-brand-400' : 'text-slate-600 group-hover:text-slate-400'}`}>
              {icon}
            </span>
            <span>{label}</span>
          </button>
        );
      })}
    </div>
  );
};

export default ModeTabBar;
