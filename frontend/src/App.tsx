import React, { useState, useEffect } from 'react';
import { Page } from './types';
import LandingPage from './pages/LandingPage';
import Login from './pages/Login';
import Signup from './pages/Signup';
import ForgotPassword from './pages/ForgotPassword';
import Dashboard from './pages/Dashboard';
import AIPrompt from './pages/AIPrompt';
import Orders from './pages/Orders';
import RiskManager from './pages/RiskManager';
import Settings from './pages/Settings';
import AlgoBuilder from './pages/AlgoBuilder';
import LiveMonitor from './pages/LiveMonitor';
import ETLStatus from './pages/ETLStatus';
import Backtest from './pages/Backtest';
import AuditReports from './pages/AuditReports';
import Scanner from './pages/Scanner';
import SectorHeatmapPage from './pages/SectorHeatmapPage';
import SectorAnalysisPage from './pages/SectorAnalysisPage';
import VolumeProfilePage from './pages/VolumeProfilePage';
import VolatilityDashboard from './pages/VolatilityDashboard';
import OptionFlow from './pages/OptionFlow';
import MomentAlert from './pages/MomentAlert';
import Week52Breakout from './pages/Week52Breakout';
import WalkForwardBacktest from './pages/WalkForwardBacktest';
import AdminIndices from './pages/AdminIndices';
import TradeScreener from './pages/TradeScreener';
import BotTab from './pages/BotTab';
import QuantWorkspace from './pages/QuantWorkspace';
import Sidebar from './components/Sidebar';
import { Menu } from 'lucide-react';
import { useAuth } from './contexts/AuthContext';
import { GlobalSymbolProvider } from './contexts/GlobalSymbolContext';


const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<Page>(Page.LANDING);
  const [darkMode, setDarkMode] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, loading, logout } = useAuth();
  const [isReady, setIsReady] = useState(false);

  // Sync current page with auth state
  useEffect(() => {
    if (!loading) {
      const isPublic = currentPage === Page.LANDING ||
        currentPage === Page.LOGIN ||
        currentPage === Page.SIGNUP ||
        currentPage === Page.FORGOT_PASSWORD;

      if (!user && !isPublic) {
        setCurrentPage(Page.LOGIN);
      } else if (user && (currentPage === Page.LOGIN || currentPage === Page.SIGNUP || currentPage === Page.FORGOT_PASSWORD)) {
        setCurrentPage(Page.DASHBOARD);
      }
      setIsReady(true);
    }
  }, [user, loading, currentPage]);

  if (loading || !isReady) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    if (!darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  const renderPage = () => {
    switch (currentPage) {
      case Page.LANDING:
        return <LandingPage onNavigate={setCurrentPage} />;
      case Page.LOGIN:
        return (
          <Login
            onLogin={() => setCurrentPage(Page.DASHBOARD)}
            onSwitchToSignup={() => setCurrentPage(Page.SIGNUP)}
            onForgotPassword={() => setCurrentPage(Page.FORGOT_PASSWORD)}
          />
        );
      case Page.SIGNUP:
        return (
          <Signup
            onSignup={() => setCurrentPage(Page.DASHBOARD)}
            onSwitchToLogin={() => setCurrentPage(Page.LOGIN)}
          />
        );
      case Page.FORGOT_PASSWORD:
        return (
          <ForgotPassword
            onBackToLogin={() => setCurrentPage(Page.LOGIN)}
          />
        );
      case Page.DASHBOARD:
        return <Dashboard onNavigate={setCurrentPage} />;
      case Page.AI_PROMPT:
        return <AIPrompt />;
      case Page.ORDERS:
        return <Orders />;
      case Page.RISK_MANAGER:
        return <RiskManager />;
      case Page.SETTINGS:
        return <Settings />;
      case Page.ALGO_BUILDER:
        return <AlgoBuilder />;
      case Page.LIVE_MONITOR:
        return <LiveMonitor />;
      case Page.ETL_STATUS:
        return <ETLStatus />;
      // ── Legacy quant routes → redirect to unified Quant Workspace ──────────
      case Page.QUANT_BOT:             // was: Backtest
      case Page.WALK_FORWARD_BACKTEST: // was: Walk-Forward
      case Page.EXPERIMENT_LAB:        // was: Experiment Lab
      case Page.QUANT_WORKSPACE:
        return <QuantWorkspace />;
      // ── End legacy redirects ──────────────────────────────────────────────
      case Page.AUDIT_REPORTS:
        return <AuditReports />;
      case Page.SCANNER:
        return <Scanner />;
      case Page.SECTOR_HEATMAP:
        return <SectorHeatmapPage onNavigate={setCurrentPage} />;
      case Page.SECTOR_ANALYSIS:
        return <SectorAnalysisPage onNavigate={setCurrentPage} />;
      case Page.VOLATILITY_DASHBOARD:
        return <VolatilityDashboard />;
      case Page.OPTION_FLOW:
        return <OptionFlow />;
      case Page.VOLUME_PROFILE:
        return <VolumeProfilePage onNavigate={setCurrentPage} />;
      case Page.MOMENT_ALERT:
        return <MomentAlert />;
      case Page.WEEK52_BREAKOUT:
        return <Week52Breakout />;
      case Page.ADMIN_INDICES:
        return <AdminIndices />;
      case Page.TRADE_SCREENER:
        return <TradeScreener />;
      case Page.SIGNAL_BOT:
        return <BotTab />;
      default:
        return <Dashboard onNavigate={setCurrentPage} />;
    }
  };

  const isPublicPage = currentPage === Page.LANDING ||
    currentPage === Page.LOGIN ||
    currentPage === Page.SIGNUP ||
    currentPage === Page.FORGOT_PASSWORD;

  // Quant Workspace uses a full-bleed layout (no max-width padding)
  const isFullBleed =
    currentPage === Page.QUANT_WORKSPACE ||
    currentPage === Page.QUANT_BOT ||
    currentPage === Page.WALK_FORWARD_BACKTEST ||
    currentPage === Page.EXPERIMENT_LAB;

  return (
    <GlobalSymbolProvider>
      <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'bg-slate-900 text-slate-100' : 'bg-slate-50 text-slate-900'}`}>
        {isPublicPage ? (
          <div className="relative">
            <div className="absolute top-4 right-4 z-50">
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-full bg-white/20 backdrop-blur hover:bg-white/30 transition-all border border-white/10"
              >
                {darkMode ? '☀️' : '🌙'}
              </button>
            </div>
            {renderPage()}
          </div>
        ) : (
          <div className="flex h-screen overflow-hidden">
            {/* Mobile Sidebar Toggle */}
            <div className="fixed top-0 left-0 p-4 z-50 lg:hidden">
              <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 bg-brand-600 text-white rounded-md shadow-lg">
                <Menu size={24} />
              </button>
            </div>

            {/* Sidebar */}
            <div className={`fixed inset-y-0 left-0 z-40 w-64 transform transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} ${darkMode ? 'bg-slate-900 border-r border-slate-800' : 'bg-white border-r border-slate-200'}`}>
              <Sidebar
                activePage={currentPage}
                onNavigate={(page) => {
                  setCurrentPage(page);
                  setSidebarOpen(false);
                }}
                onLogout={async () => {
                  await logout();
                  setCurrentPage(Page.LANDING);
                }}
                darkMode={darkMode}
                toggleDarkMode={toggleDarkMode}
              />
            </div>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto overflow-x-hidden relative">
              {isFullBleed ? (
                // Full-bleed layout for the Quant Research Terminal
                <div className="h-full">
                  {renderPage()}
                </div>
              ) : (
                <div className="p-6 lg:p-8 max-w-7xl mx-auto">
                  {renderPage()}
                </div>
              )}
            </main>
          </div>
        )}
      </div>
    </GlobalSymbolProvider>
  );
};

export default App;