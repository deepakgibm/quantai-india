/**
 * Quant Research Terminal — Main orchestration shell.
 *
 * This file is intentionally minimal (~80 lines).
 * All state lives in QuantProvider (contexts/QuantContext.tsx).
 * All UI lives in modular components under components/quant/.
 */

import React from 'react';
import { QuantProvider, useQuantContext } from '../contexts/QuantContext';
import WorkspaceHeader from '../components/quant/workspace/WorkspaceHeader';
import ModeTabBar from '../components/quant/workspace/ModeTabBar';
import WorkspaceSidebar from '../components/quant/workspace/WorkspaceSidebar';
import DiscoveryPanel from '../components/quant/discovery/DiscoveryPanel';
import BacktestPanel from '../components/quant/backtest/BacktestPanel';
import PortfolioPanel from '../components/quant/portfolio/PortfolioPanel';

// ─── Inner workspace (must be inside QuantProvider) ──────────────────────────

function ActiveModePanel() {
  const { activeMode } = useQuantContext();
  switch (activeMode) {
    case 'discovery':    return <DiscoveryPanel />;
    case 'backtest':     return <BacktestPanel />;
    case 'portfolio':    return <PortfolioPanel />;
    default:             return <BacktestPanel />;
  }
}

function WorkspaceShell() {
  return (
    <div className="flex flex-col bg-slate-950" style={{ height: '100vh', overflow: 'hidden' }}>
      {/* Top bar: branding + global controls */}
      <WorkspaceHeader />

      {/* Mode tab bar */}
      <ModeTabBar />

      {/* Main content: config sidebar + active mode panel */}
      <div className="flex flex-1 overflow-hidden">
        <WorkspaceSidebar />

        {/* Scrollable main canvas */}
        <main className="flex-1 overflow-y-auto p-5 bg-slate-950">
          <ActiveModePanel />
        </main>
      </div>
    </div>
  );
}

// ─── Public export ────────────────────────────────────────────────────────────

export default function QuantWorkspace() {
  return (
    <QuantProvider>
      <WorkspaceShell />
    </QuantProvider>
  );
}
