import React from 'react';
import {
  Play,
  Grid,
  Briefcase,
  Info,
  SlidersHorizontal,
  Shield,
  Percent,
  ChevronRight,
} from 'lucide-react';
import { useQuantContext } from '../../../contexts/QuantContext';
import ActionButton from '../shared/ActionButton';

/**
 * Left configuration panel of the Quant Research Terminal.
 * Strategy selector, parameter tuning, execution settings, mode-specific action buttons.
 */
const WorkspaceSidebar: React.FC = () => {
  const {
    strategies, selectedStrategyId, setSelectedStrategyId,
    activeStrategy, strategyParams, handleParamChange,
    riskMode, setRiskMode, riskPercent, setRiskPercent,
    executionType, setExecutionType,
    activeMode, loading, error, setError,
    backtestData,
    runBacktest,
    runDiscoveryScan, addCurrentToPortfolio,
  } = useQuantContext();

  const params = activeStrategy?.parameters || {};
  const numericParams = Object.entries(params).filter(([, spec]) => typeof spec.default === 'number');

  return (
    <aside className="w-64 xl:w-72 bg-slate-950 border-r border-slate-800 flex flex-col overflow-y-auto shrink-0">
      {/* ── Strategy Select ──────────────────────────────────────────── */}
      <div className="p-4 border-b border-slate-800/80 space-y-3">
        <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
          <SlidersHorizontal size={11} /> Strategy
        </h3>
        <select
          value={selectedStrategyId}
          onChange={e => setSelectedStrategyId(e.target.value)}
          className="w-full px-3 py-2.5 rounded-lg border border-slate-700 bg-slate-900 text-white text-xs focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none"
        >
          {strategies.map(s => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        {activeStrategy?.description && (
          <p className="text-[10px] text-slate-500 leading-relaxed flex gap-1.5">
            <Info size={10} className="shrink-0 mt-0.5 text-slate-600" />
            {activeStrategy.description}
          </p>
        )}
        <div className="text-[10px] text-slate-600 uppercase font-bold">
          Category: <span className="text-slate-400">{activeStrategy?.category || '—'}</span>
        </div>
      </div>

      {/* ── Parameter Tuning ─────────────────────────────────────────── */}
      {numericParams.length > 0 && (
        <div className="p-4 border-b border-slate-800/80 space-y-3">
          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
            <SlidersHorizontal size={11} /> Parameters
          </h3>
          {numericParams.map(([key, spec]) => (
            <div key={key} className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-[10px] font-semibold text-slate-400">{key}</label>
                <span className="text-[10px] font-black text-brand-400">
                  {strategyParams[key] ?? spec.default}
                </span>
              </div>
              <input
                type="range"
                min={spec.min ?? 1}
                max={spec.max ?? 200}
                step={spec.type === 'float' ? 0.1 : 1}
                value={strategyParams[key] ?? spec.default}
                onChange={e => handleParamChange(key, spec.type === 'float' ? parseFloat(e.target.value) : parseInt(e.target.value))}
                className="w-full h-1.5 accent-brand-500 cursor-pointer"
              />
              <div className="flex justify-between text-[9px] text-slate-700">
                <span>{spec.min ?? 1}</span>
                <span>{spec.max ?? 200}</span>
              </div>
              {spec.description && (
                <p className="text-[9px] text-slate-600">{spec.description}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── Execution Config (backtest mode only) ────────────────────── */}
      {activeMode === 'backtest' && (
        <div className="p-4 border-b border-slate-800/80 space-y-3">
          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
            <Shield size={11} /> Execution
          </h3>

          {/* Execution fidelity toggle */}
          <div className="flex rounded-lg overflow-hidden border border-slate-700">
            {(['vectorized', 'event_driven'] as const).map(mode => (
              <button
                key={mode}
                onClick={() => setExecutionType(mode)}
                className={`flex-1 py-2 text-[10px] font-bold uppercase transition-colors ${
                  executionType === mode
                    ? 'bg-brand-600 text-white'
                    : 'bg-slate-900 text-slate-500 hover:text-slate-300'
                }`}
              >
                {mode === 'vectorized' ? 'Fast' : 'High-Fidelity'}
              </button>
            ))}
          </div>

          <p className="text-[9px] text-slate-600 leading-relaxed">
            {executionType === 'event_driven'
              ? 'Bar-by-bar simulation with NSE slippage, brokerage & tax.'
              : 'Vectorized batch mode — fast scans & optimization sweeps.'}
          </p>

          {/* Risk mode */}
          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
              <Percent size={10} /> Risk Mode
            </label>
            <select
              value={riskMode}
              onChange={e => setRiskMode(e.target.value)}
              className="w-full px-2.5 py-2 rounded-lg border border-slate-700 bg-slate-900 text-white text-xs outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="percent_capital">% of Capital</option>
              <option value="fixed_amount">Fixed Amount</option>
              <option value="kelly_criterion">Kelly Criterion</option>
            </select>
          </div>

          {/* Risk % slider */}
          <div className="space-y-1.5">
            <div className="flex justify-between">
              <label className="text-[10px] font-semibold text-slate-400">Risk per Trade</label>
              <span className="text-[10px] font-black text-amber-400">{riskPercent.toFixed(1)}%</span>
            </div>
            <input
              type="range" min={0.1} max={10} step={0.1}
              value={riskPercent}
              onChange={e => setRiskPercent(parseFloat(e.target.value))}
              className="w-full h-1.5 accent-amber-500 cursor-pointer"
            />
          </div>
        </div>
      )}

      {/* ── Action Buttons ────────────────────────────────────────────── */}
      <div className="p-4 space-y-2">
        {activeMode === 'discovery' && (
          <ActionButton
            onClick={runDiscoveryScan}
            loading={loading}
            icon={<Grid size={13} />}
            label="Scan All Strategies"
            loadingLabel="Scanning…"
          />
        )}
        {activeMode === 'backtest' && (
          <>
            <ActionButton
              onClick={runBacktest}
              loading={loading}
              icon={<Play size={13} />}
              label="Run Backtest"
              loadingLabel="Simulating…"
            />
            {backtestData && (
              <ActionButton
                onClick={addCurrentToPortfolio}
                loading={false}
                icon={<Briefcase size={13} />}
                label="Add to Portfolio"
                variant="secondary"
              />
            )}
          </>
        )}
        {activeMode === 'portfolio' && backtestData && (
          <ActionButton
            onClick={addCurrentToPortfolio}
            loading={false}
            icon={<Briefcase size={13} />}
            label="Add Current to Portfolio"
            variant="secondary"
          />
        )}
      </div>

      {/* ── Error Banner ──────────────────────────────────────────────── */}
      {error && (
        <div className="mx-4 mb-4 p-3 bg-red-950/60 border border-red-900/50 rounded-lg">
          <p className="text-[10px] text-red-400 leading-relaxed">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-[9px] text-red-500/70 hover:text-red-400 mt-1 uppercase font-bold"
          >
            Dismiss
          </button>
        </div>
      )}
    </aside>
  );
};

export default WorkspaceSidebar;
