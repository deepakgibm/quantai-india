import React from 'react';
import { Page } from '../types';
import {
  LayoutDashboard,
  BrainCircuit,
  Activity,
  ShieldAlert,
  Settings,
  LogOut,
  Search,
  Zap,
  Moon,
  Sun,
  Bell,
  Target,
  TrendingUp,
  Shield,
  Bot,
  BarChart2,
  Cpu,
  LayoutGrid,
  CreditCard,
  GraduationCap,
  Newspaper,
  Handshake,
  Award,
  Compass,
  BookOpen,
  Briefcase,
  Eye
} from 'lucide-react';

interface SidebarProps {
  activePage: Page;
  onNavigate: (page: Page) => void;
  onLogout: () => void;
  darkMode: boolean;
  toggleDarkMode: () => void;
}

interface NavItem {
  page: Page;
  icon: React.ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;
  label: string;
  badge?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: 'Markets',
    items: [
      { page: Page.DASHBOARD,            icon: LayoutDashboard, label: 'Dashboard' },
      { page: Page.VOLATILITY_DASHBOARD, icon: Activity,        label: 'Volatility Index' },
      { page: Page.OPTION_FLOW,          icon: TrendingUp,      label: 'Option Flow' },
      { page: Page.SECTOR_HEATMAP,       icon: Zap,             label: 'Sector Heatmap' },
      { page: Page.SECTOR_ANALYSIS,      icon: LayoutGrid,      label: 'Sector Analysis' },
      { page: Page.VOLUME_PROFILE,       icon: Cpu,             label: 'Volume Profile' },
    ],
  },
  {
    title: 'Research & Tools',
    items: [
      { page: Page.QUANT_WORKSPACE,      icon: BarChart2,       label: 'Research Terminal', badge: 'NEW' },
      { page: Page.RESEARCH_CENTER,      icon: Newspaper,       label: 'Research Center' },
      { page: Page.WATCHLIST,            icon: Eye,             label: 'Watchlist Portfolio' },
      { page: Page.PORTFOLIO_INTELLIGENCE, icon: Briefcase,     label: 'Portfolio Intel' },
      { page: Page.SMC_ANALYSIS,         icon: Compass,         label: 'SMC Analysis' },
      { page: Page.PATTERN_LAB,          icon: BookOpen,        label: 'Pattern Lab' },
      { page: Page.PRICE_DIAGNOSTICS,    icon: ShieldAlert,     label: 'Price Diagnostics' },
    ],
  },
  {
    title: 'Intelligence & Signals',
    items: [
      { page: Page.INSTITUTIONAL_SCANNER, icon: TrendingUp,     label: 'Institutional Scanner', badge: 'VCP' },
      { page: Page.TRADE_SCREENER,       icon: Shield,          label: 'Trade Screener' },
      { page: Page.SIGNAL_BOT,           icon: Bot,             label: 'Signal Bot' },
      { page: Page.SIGNAL_CENTER,        icon: Award,           label: 'Signal Performance' },
      { page: Page.AI_PROMPT,            icon: BrainCircuit,    label: 'AI Prompt' },
      { page: Page.SCANNER,              icon: Search,          label: 'Scanner' },
      { page: Page.MOMENT_ALERT,         icon: Bell,            label: 'Moment Alert' },
      { page: Page.WEEK52_BREAKOUT,      icon: Target,          label: '52-Week Breakout' },
    ],
  },
  {
    title: 'SaaS & Partners',
    items: [
      { page: Page.ACADEMY,              icon: GraduationCap,   label: 'Academy' },
      { page: Page.SUBSCRIPTION,         icon: CreditCard,      label: 'Subscription' },
      { page: Page.AFFILIATE,            icon: Handshake,       label: 'Affiliate' },
    ],
  },
];

const Sidebar: React.FC<SidebarProps> = ({
  activePage, onNavigate, onLogout, darkMode, toggleDarkMode,
}) => (
  <div className="flex flex-col h-full">
    {/* Logo */}
    <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center gap-3">
      <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center shadow-lg shadow-brand-500/20 shrink-0">
        <BrainCircuit className="text-white" size={20} />
      </div>
      <div>
        <h1 className="font-display font-bold text-lg tracking-tight">QuantAI</h1>
        <p className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">India Market</p>
      </div>
    </div>

    {/* Navigation sections */}
    <nav className="flex-1 py-4 px-3 space-y-5 overflow-y-auto">
      {NAV_SECTIONS.map(section => (
        <div key={section.title}>
          <div className="px-3 mb-1.5 text-[9px] font-bold text-slate-400 dark:text-slate-600 uppercase tracking-widest">
            {section.title}
          </div>
          <div className="space-y-0.5">
            {section.items.map(item => {
              const isActive = activePage === item.page;
              return (
                <button
                  key={item.page}
                  onClick={() => onNavigate(item.page)}
                  className={`
                    w-full flex items-center gap-3 px-3 py-2.5 rounded-lg
                    transition-all duration-200 group font-medium text-sm
                    ${isActive
                      ? 'bg-term-bg-tertiary text-term-info border-l-[3px] border-term-info rounded-l-none'
                      : 'text-term-text-secondary hover:bg-[#1F2937] hover:text-term-text-primary'
                    }
                  `}
                >
                  <item.icon
                    size={17}
                    strokeWidth={isActive ? 2.5 : 2}
                    className={`shrink-0 ${isActive
                      ? 'text-term-info'
                      : 'text-slate-500 group-hover:text-term-text-primary'
                    }`}
                  />
                  <span className="flex-1 truncate">{item.label}</span>
                  {item.badge && (
                    <span className="text-[9px] font-black bg-brand-600 text-white px-1.5 py-0.5 rounded-full shrink-0">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </nav>

    {/* Footer */}
    <div className="p-3 border-t border-slate-200 dark:border-slate-800 space-y-1.5">
      {/* Broker status */}
      <div className="px-3 py-2 mb-1">
        <div className="flex items-center gap-2 text-xs font-medium text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 p-2 rounded-lg border border-green-100 dark:border-green-900/50">
          <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse shrink-0" />
          Upstox Connected
        </div>
      </div>

      <button
        onClick={toggleDarkMode}
        className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-sm"
      >
        {darkMode ? <Sun size={16} /> : <Moon size={16} />}
        <span className="font-medium">{darkMode ? 'Light Mode' : 'Dark Mode'}</span>
      </button>

      <button
        onClick={onLogout}
        className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors text-sm"
      >
        <LogOut size={16} />
        <span className="font-medium">Logout</span>
      </button>
    </div>
  </div>
);

export default Sidebar;