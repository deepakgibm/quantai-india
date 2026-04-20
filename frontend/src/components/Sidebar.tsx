import React from 'react';
import { Page } from '../types';
import {
  LayoutDashboard,
  BrainCircuit,
  Activity,
  List,
  ShieldAlert,
  Settings,
  LogOut,
  Search,
  Zap,
  Moon,
  Sun,
  Database,
  LineChart,
  Bell,
  Target,
  TrendingUp,
  FlaskConical,
  Shield
} from 'lucide-react';

interface SidebarProps {
  activePage: Page;
  onNavigate: (page: Page) => void;
  onLogout: () => void;
  darkMode: boolean;
  toggleDarkMode: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activePage, onNavigate, onLogout, darkMode, toggleDarkMode }) => {
  const navItems = [
    { page: Page.DASHBOARD, icon: LayoutDashboard, label: 'Dashboard' },
    { page: Page.SECTOR_HEATMAP, icon: Zap, label: 'Sector Heatmap' },
    { page: Page.TRADE_SCREENER, icon: Shield, label: 'Trade Screener' },
    { page: Page.AI_PROMPT, icon: BrainCircuit, label: 'AI Prompt' },
    { page: Page.SCANNER, icon: Search, label: 'Scanner' },
    { page: Page.MOMENT_ALERT, icon: Bell, label: 'Moment Alert' },
    { page: Page.WEEK52_BREAKOUT, icon: Target, label: '52-Week Breakout' },
    { page: Page.QUANT_BOT, icon: LineChart, label: 'Backtest' },
    { page: Page.WALK_FORWARD_BACKTEST, icon: TrendingUp, label: 'Walk-Forward' },
    { page: Page.EXPERIMENT_LAB, icon: FlaskConical, label: 'Experiment Lab' },
    { page: Page.PRICE_FORECAST, icon: TrendingUp, label: 'AI Forecast' },
    { page: Page.AI_TRAINING, icon: Activity, label: 'AI Training' },
    // { page: Page.ADMIN_INDICES, icon: List, label: 'Index Management' },
    { page: Page.ADMIN_MONITORING, icon: Activity, label: 'System Monitoring' },
    // { page: Page.ALGO_BUILDER, icon: Zap, label: 'Algo Builder' },
    // Hidden Pages (Moved to Tech Debt)
    // { page: Page.AUDIT_REPORTS, icon: Database, label: 'Audit & Reports' },
    // { page: Page.LIVE_MONITOR, icon: Activity, label: 'Live Monitor' },
    // { page: Page.RISK_MANAGER, icon: ShieldAlert, label: 'Risk Manager' },
    // { page: Page.ETL_STATUS, icon: Database, label: 'System Status' },
    // { page: Page.SETTINGS, icon: Settings, label: 'Settings' },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center shadow-lg shadow-brand-500/20">
          <BrainCircuit className="text-white" size={24} />
        </div>
        <div>
          <h1 className="font-display font-bold text-xl tracking-tight">QuantAI</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">India Market</p>
        </div>
      </div>

      <nav className="flex-1 py-6 px-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <button
            key={item.page}
            onClick={() => onNavigate(item.page)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 group font-medium ${activePage === item.page
              ? 'bg-brand-50 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400 shadow-sm ring-1 ring-brand-200 dark:ring-brand-800'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
          >
            <item.icon size={20} strokeWidth={activePage === item.page ? 2.5 : 2} className={`${activePage === item.page ? 'text-brand-600 dark:text-brand-400' : 'text-slate-400 group-hover:text-slate-600 dark:text-slate-500 dark:group-hover:text-slate-300'}`} />
            {item.label}
          </button>
        ))}
      </nav>

      <div className="p-4 border-t border-slate-200 dark:border-slate-800 space-y-2">
        <div className="px-4 py-2 mb-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Broker Status
          </div>
          <div className="flex items-center gap-2 text-sm font-medium text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 p-2 rounded border border-green-100 dark:border-green-900/50">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            Upstox Connected
          </div>
        </div>

        <button
          onClick={toggleDarkMode}
          className="w-full flex items-center gap-3 px-4 py-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          {darkMode ? <Sun size={18} /> : <Moon size={18} />}
          <span className="text-sm font-medium">{darkMode ? 'Light Mode' : 'Dark Mode'}</span>
        </button>

        <button
          onClick={onLogout}
          className="w-full flex items-center gap-3 px-4 py-2 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
        >
          <LogOut size={18} />
          <span className="text-sm font-medium">Logout</span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;