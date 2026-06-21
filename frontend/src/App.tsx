import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Page } from './types';
import LandingPage from './pages/LandingPage';
import Login from './pages/Login';
import Signup from './pages/Signup';
import ForgotPassword from './pages/ForgotPassword';
import Dashboard from './pages/Dashboard';
import AIPrompt from './pages/AIPrompt';
import Scanner from './pages/Scanner';
import SectorHeatmapPage from './pages/SectorHeatmapPage';
import SectorAnalysisPage from './pages/SectorAnalysisPage';
import VolumeProfilePage from './pages/VolumeProfilePage';
import VolatilityDashboard from './pages/VolatilityDashboard';
import OptionFlow from './pages/OptionFlow';
import MomentAlert from './pages/MomentAlert';
import Week52Breakout from './pages/Week52Breakout';
import TradeScreener from './pages/TradeScreener';
import BotTab from './pages/BotTab';
import QuantWorkspace from './pages/QuantWorkspace';
import Subscription from './pages/Subscription';
import PortfolioIntelligence from './pages/PortfolioIntelligence';
import SignalCenter from './pages/SignalCenter';
import SMCAnalysis from './pages/SMCAnalysis';
import PatternLab from './pages/PatternLab';
import Academy from './pages/Academy';
import ResearchCenter from './pages/ResearchCenter';
import Affiliate from './pages/Affiliate';
import Watchlist from './pages/Watchlist';
import InstitutionalScanner from './pages/InstitutionalScanner';
import InstitutionalStockDetail from './pages/InstitutionalStockDetail';
import PriceDiagnosticPanel from './pages/PriceDiagnosticPanel';
import Sidebar from './components/Sidebar';
import { Menu } from 'lucide-react';
import { useAuth } from './contexts/AuthContext';
import { GlobalSymbolProvider } from './contexts/GlobalSymbolContext';

// Initialize React Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000, // 30 seconds
    },
  },
});

const InstitutionalStockDetailWrapper: React.FC = () => {
  const { symbol } = useParams<{ symbol: string }>();
  const navigate = useNavigate();
  return (
    <InstitutionalStockDetail
      symbol={symbol || 'RELIANCE'}
      onBack={() => navigate('/institutional-scanner')}
    />
  );
};

const PublicRoute: React.FC<{ element: React.ReactNode; activePage: Page }> = ({ element, activePage }) => {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    if (!loading && user) {
      navigate('/dashboard');
    }
  }, [user, loading, navigate]);

  if (loading) {
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

  return (
    <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'bg-slate-900 text-slate-100' : 'bg-slate-50 text-slate-900'}`}>
      <div className="relative">
        <div className="absolute top-4 right-4 z-50">
          <button
            onClick={toggleDarkMode}
            className="p-2 rounded-full bg-white/20 backdrop-blur hover:bg-white/30 transition-all border border-white/10"
          >
            {darkMode ? '☀️' : '🌙'}
          </button>
        </div>
        {element}
      </div>
    </div>
  );
};

const ProtectedRoute: React.FC<{ element: React.ReactNode; activePage: Page }> = ({ element, activePage }) => {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const [darkMode, setDarkMode] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      navigate('/login');
    }
  }, [user, loading, navigate]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  if (!user) return null;

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    if (!darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  const handleSidebarNavigate = (page: Page, symbol?: string) => {
    setSidebarOpen(false);
    let path = '/dashboard';
    if (page === Page.LANDING) path = '/';
    else if (page === Page.LOGIN) path = '/login';
    else if (page === Page.SIGNUP) path = '/signup';
    else if (page === Page.FORGOT_PASSWORD) path = '/forgot-password';
    else if (page === Page.DASHBOARD) path = '/dashboard';
    else if (page === Page.AI_PROMPT) path = '/ai-prompt';
    else if (page === Page.QUANT_WORKSPACE || page === Page.QUANT_BOT || page === Page.WALK_FORWARD_BACKTEST || page === Page.EXPERIMENT_LAB) path = '/quant-workspace';
    else if (page === Page.SCANNER) path = '/scanner';
    else if (page === Page.SECTOR_HEATMAP) path = '/sector-heatmap';
    else if (page === Page.SECTOR_ANALYSIS) path = '/sector-analysis';
    else if (page === Page.VOLUME_PROFILE) path = '/volume-profile';
    else if (page === Page.VOLATILITY_DASHBOARD) path = '/volatility';
    else if (page === Page.OPTION_FLOW) path = '/option-flow';
    else if (page === Page.MOMENT_ALERT) path = '/moment-alert';
    else if (page === Page.WEEK52_BREAKOUT) path = '/week52-breakout';
    else if (page === Page.TRADE_SCREENER) path = '/trade-screener';
    else if (page === Page.SIGNAL_BOT) path = '/signal-bot';
    else if (page === Page.SUBSCRIPTION) path = '/subscription';
    else if (page === Page.PORTFOLIO_INTELLIGENCE) path = '/portfolio-intelligence';
    else if (page === Page.SIGNAL_CENTER) path = '/signal-center';
    else if (page === Page.SMC_ANALYSIS) path = '/smc-analysis';
    else if (page === Page.PATTERN_LAB) path = '/pattern-lab';
    else if (page === Page.ACADEMY) path = '/academy';
    else if (page === Page.RESEARCH_CENTER) path = '/research-center';
    else if (page === Page.AFFILIATE) path = '/affiliate';
    else if (page === Page.WATCHLIST) path = '/watchlist';
    else if (page === Page.INSTITUTIONAL_SCANNER) path = '/institutional-scanner';
    else if (page === Page.INSTITUTIONAL_STOCK_DETAIL && symbol) {
      path = `/institutional-scanner/${symbol.toUpperCase()}`;
    }
    else if (page === Page.PRICE_DIAGNOSTICS) {
      path = '/diagnostics';
    }
    navigate(path);
  };

  const isFullBleed =
    activePage === Page.QUANT_WORKSPACE ||
    activePage === Page.QUANT_BOT ||
    activePage === Page.WALK_FORWARD_BACKTEST ||
    activePage === Page.EXPERIMENT_LAB;

  return (
    <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'bg-slate-900 text-slate-100' : 'bg-slate-50 text-slate-900'}`}>
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
            activePage={activePage}
            onNavigate={handleSidebarNavigate}
            onLogout={async () => {
              await logout();
              navigate('/');
            }}
            darkMode={darkMode}
            toggleDarkMode={toggleDarkMode}
          />
        </div>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden relative">
          {isFullBleed ? (
            <div className="h-full">{element}</div>
          ) : (
            <div className="p-6 lg:p-8 max-w-7xl mx-auto">{element}</div>
          )}
        </main>
      </div>
    </div>
  );
};

const AppRoutes: React.FC = () => {
  const navigate = useNavigate();
  const handleNavigate = (page: Page, symbol?: string) => {
    let path = '/dashboard';
    if (page === Page.LANDING) path = '/';
    else if (page === Page.LOGIN) path = '/login';
    else if (page === Page.SIGNUP) path = '/signup';
    else if (page === Page.FORGOT_PASSWORD) path = '/forgot-password';
    else if (page === Page.DASHBOARD) path = '/dashboard';
    else if (page === Page.AI_PROMPT) path = '/ai-prompt';
    else if (page === Page.QUANT_WORKSPACE || page === Page.QUANT_BOT || page === Page.WALK_FORWARD_BACKTEST || page === Page.EXPERIMENT_LAB) path = '/quant-workspace';
    else if (page === Page.SCANNER) path = '/scanner';
    else if (page === Page.SECTOR_HEATMAP) path = '/sector-heatmap';
    else if (page === Page.SECTOR_ANALYSIS) path = '/sector-analysis';
    else if (page === Page.VOLUME_PROFILE) path = '/volume-profile';
    else if (page === Page.VOLATILITY_DASHBOARD) path = '/volatility';
    else if (page === Page.OPTION_FLOW) path = '/option-flow';
    else if (page === Page.MOMENT_ALERT) path = '/moment-alert';
    else if (page === Page.WEEK52_BREAKOUT) path = '/week52-breakout';
    else if (page === Page.TRADE_SCREENER) path = '/trade-screener';
    else if (page === Page.SIGNAL_BOT) path = '/signal-bot';
    else if (page === Page.SUBSCRIPTION) path = '/subscription';
    else if (page === Page.PORTFOLIO_INTELLIGENCE) path = '/portfolio-intelligence';
    else if (page === Page.SIGNAL_CENTER) path = '/signal-center';
    else if (page === Page.SMC_ANALYSIS) path = '/smc-analysis';
    else if (page === Page.PATTERN_LAB) path = '/pattern-lab';
    else if (page === Page.ACADEMY) path = '/academy';
    else if (page === Page.RESEARCH_CENTER) path = '/research-center';
    else if (page === Page.AFFILIATE) path = '/affiliate';
    else if (page === Page.WATCHLIST) path = '/watchlist';
    else if (page === Page.INSTITUTIONAL_SCANNER) path = '/institutional-scanner';
    else if (page === Page.INSTITUTIONAL_STOCK_DETAIL && symbol) {
      path = `/institutional-scanner/${symbol.toUpperCase()}`;
    }
    else if (page === Page.PRICE_DIAGNOSTICS) {
      path = '/diagnostics';
    }
    navigate(path);
  };

  return (
    <Routes>
      <Route path="/" element={<PublicRoute activePage={Page.LANDING} element={<LandingPage onNavigate={handleNavigate} />} />} />
      <Route path="/login" element={<PublicRoute activePage={Page.LOGIN} element={
        <Login
          onLogin={() => navigate('/dashboard')}
          onSwitchToSignup={() => navigate('/signup')}
          onForgotPassword={() => navigate('/forgot-password')}
        />
      } />} />
      <Route path="/signup" element={<PublicRoute activePage={Page.SIGNUP} element={
        <Signup
          onSignup={() => navigate('/dashboard')}
          onSwitchToLogin={() => navigate('/login')}
        />
      } />} />
      <Route path="/forgot-password" element={<PublicRoute activePage={Page.FORGOT_PASSWORD} element={
        <ForgotPassword
          onBackToLogin={() => navigate('/login')}
        />
      } />} />
      
      {/* Protected Routes */}
      <Route path="/dashboard" element={<ProtectedRoute activePage={Page.DASHBOARD} element={<Dashboard onNavigate={handleNavigate} />} />} />
      <Route path="/ai-prompt" element={<ProtectedRoute activePage={Page.AI_PROMPT} element={<AIPrompt />} />} />
      <Route path="/quant-workspace" element={<ProtectedRoute activePage={Page.QUANT_WORKSPACE} element={<QuantWorkspace />} />} />
      <Route path="/scanner" element={<ProtectedRoute activePage={Page.SCANNER} element={<Scanner />} />} />
      <Route path="/sector-heatmap" element={<ProtectedRoute activePage={Page.SECTOR_HEATMAP} element={<SectorHeatmapPage onNavigate={handleNavigate} />} />} />
      <Route path="/sector-analysis" element={<ProtectedRoute activePage={Page.SECTOR_ANALYSIS} element={<SectorAnalysisPage onNavigate={handleNavigate} />} />} />
      <Route path="/volume-profile" element={<ProtectedRoute activePage={Page.VOLUME_PROFILE} element={<VolumeProfilePage onNavigate={handleNavigate} />} />} />
      <Route path="/volatility" element={<ProtectedRoute activePage={Page.VOLATILITY_DASHBOARD} element={<VolatilityDashboard />} />} />
      <Route path="/option-flow" element={<ProtectedRoute activePage={Page.OPTION_FLOW} element={<OptionFlow />} />} />
      <Route path="/moment-alert" element={<ProtectedRoute activePage={Page.MOMENT_ALERT} element={<MomentAlert />} />} />
      <Route path="/week52-breakout" element={<ProtectedRoute activePage={Page.WEEK52_BREAKOUT} element={<Week52Breakout />} />} />
      <Route path="/trade-screener" element={<ProtectedRoute activePage={Page.TRADE_SCREENER} element={<TradeScreener />} />} />
      <Route path="/signal-bot" element={<ProtectedRoute activePage={Page.SIGNAL_BOT} element={<BotTab />} />} />
      <Route path="/subscription" element={<ProtectedRoute activePage={Page.SUBSCRIPTION} element={<Subscription />} />} />
      <Route path="/portfolio-intelligence" element={<ProtectedRoute activePage={Page.PORTFOLIO_INTELLIGENCE} element={<PortfolioIntelligence />} />} />
      <Route path="/signal-center" element={<ProtectedRoute activePage={Page.SIGNAL_CENTER} element={<SignalCenter />} />} />
      <Route path="/smc-analysis" element={<ProtectedRoute activePage={Page.SMC_ANALYSIS} element={<SMCAnalysis />} />} />
      <Route path="/pattern-lab" element={<ProtectedRoute activePage={Page.PATTERN_LAB} element={<PatternLab />} />} />
      <Route path="/academy" element={<ProtectedRoute activePage={Page.ACADEMY} element={<Academy />} />} />
      <Route path="/research-center" element={<ProtectedRoute activePage={Page.RESEARCH_CENTER} element={<ResearchCenter />} />} />
      <Route path="/affiliate" element={<ProtectedRoute activePage={Page.AFFILIATE} element={<Affiliate />} />} />
      <Route path="/watchlist" element={<ProtectedRoute activePage={Page.WATCHLIST} element={<Watchlist onNavigate={handleNavigate} />} />} />
      <Route path="/institutional-scanner" element={<ProtectedRoute activePage={Page.INSTITUTIONAL_SCANNER} element={<InstitutionalScanner onNavigate={handleNavigate} />} />} />
      <Route path="/institutional-scanner/:symbol" element={<ProtectedRoute activePage={Page.INSTITUTIONAL_STOCK_DETAIL} element={<InstitutionalStockDetailWrapper />} />} />
      <Route path="/diagnostics" element={<ProtectedRoute activePage={Page.PRICE_DIAGNOSTICS} element={<PriceDiagnosticPanel />} />} />
      
      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <GlobalSymbolProvider>
        <Router>
          <AppRoutes />
        </Router>
      </GlobalSymbolProvider>
    </QueryClientProvider>
  );
};

export default App;