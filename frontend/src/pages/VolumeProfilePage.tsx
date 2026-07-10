import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, Target, Cpu, Scale, Percent, RefreshCw, 
  HelpCircle, Eye, EyeOff, Download, ArrowUpRight, ArrowDownRight, ChevronRight,
  Info, Sparkles, BookOpen, AlertTriangle
} from 'lucide-react';
import { createChart, ColorType, CrosshairMode, IChartApi, ISeriesApi, UTCTimestamp } from 'lightweight-charts';
import { useGlobalSymbol } from '../contexts/GlobalSymbolContext';
import { api } from '../services/api';
import GlobalSymbolSearch from '../components/GlobalSymbolSearch';
import ErrorCard from '../components/ErrorCard';

// Sub-components
import VolumeProfileTour from '../components/trading/VolumeProfileTour';
import VolumeProfileHelpCenter from '../components/trading/VolumeProfileHelpCenter';

interface PricePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema20?: number | null;
  ema50?: number | null;
  ema200?: number | null;
  vwap?: number | null;
  volume_ma?: number | null;
  atr?: number | null;
  swing_high?: number | null;
  swing_low?: number | null;
  bos?: boolean;
  choch?: boolean;
  sweep?: boolean;
}

interface HistogramBin {
  price_min: number;
  price_max: number;
  volume: number;
}

interface TimeframeData {
  shape: string;
  verdict: string;
}

interface RiskManagement {
  entry_zone: string;
  stop_loss: number;
  target_1: number;
  target_2: number;
  target_3?: number;
  risk_reward_ratio: number;
}

interface SectorIntegration {
  sector_name: string;
  sector_score: number;
  sector_rank: number;
  relative_strength_rank: number;
}

interface VolumeProfileData {
  status: string;
  symbol: string;
  company_name: string;
  sector: string;
  price: number;
  poc: number;
  vah: number;
  val: number;
  hvn: number[];
  lvn: number[];
  shape: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  verdict: string;
  confidence: number;
  risk_score: number;
  institutional_bias: string;
  summary: string;
  factors: string[];
  histogram: HistogramBin[];
  price_history: PricePoint[];
  timeframes: {
    daily: TimeframeData;
    weekly: TimeframeData;
    monthly: TimeframeData;
  };
  risk_management: RiskManagement;
  sector_integration: SectorIntegration;
}

const TRADING_TIPS = [
  "POC acts like a gravity magnet: price frequently rotates back to it when session momentum fades.",
  "Low Volume Nodes (LVNs) represent rejection. Price tends to slice through these gaps extremely fast.",
  "Value Area High (VAH) breakouts are strong bullish triggers when backed by rising volume.",
  "Always trade Volume Profile setups in alignment with the broader sector relative strength."
];

interface VolumeProfilePageProps {
  onNavigate?: (page: any) => void;
}

const VolumeProfilePage: React.FC<VolumeProfilePageProps> = () => {
  const { selectedSymbol } = useGlobalSymbol();
  const [data, setData] = useState<VolumeProfileData | null>(null);
  const [lookback, setLookback] = useState<number>(90);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  // Layout / Toggles
  const [showHistogram, setShowHistogram] = useState(true);
  const [showValueArea, setShowValueArea] = useState(true);
  const [showPoc, setShowPoc] = useState(true);
  const [showHvnLvn, setShowHvnLvn] = useState(true);
  const [showEmas, setShowEmas] = useState(true);
  const [showVwap, setShowVwap] = useState(true);
  const [showStructure, setShowStructure] = useState(true);
  const [chartType, setChartType] = useState<'candles' | 'line'>('candles');

  // Help & Guided Tour states
  const [showHelp, setShowHelp] = useState(false);
  const [helpTab, setHelpTab] = useState('overview');
  const [showTour, setShowTour] = useState(false);
  const [showLegend, setShowLegend] = useState(true);
  const [showAiVerdictExplain, setShowAiVerdictExplain] = useState(false);

  // Rotating tips state
  const [tipIndex, setTipIndex] = useState(0);

  const chartContainerRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const lineSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  
  const ema20SeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const ema50SeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const ema200SeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const vwapSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  // Fetch Volume Profile data
  useEffect(() => {
    const fetchVolumeProfile = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.getVolumeProfileData(selectedSymbol, lookback);
        if (response && response.status === 'success') {
          setData(response);
        } else {
          setError('Failed to fetch volume profile analysis data.');
        }
      } catch (err: any) {
        console.error('Error fetching volume profile:', err);
        setError(err.message || 'Failed to connect to Volume Profile API.');
      } finally {
        setLoading(false);
      }
    };

    fetchVolumeProfile();
  }, [selectedSymbol, lookback, refreshTrigger]);

  // Auto tour trigger on first visit
  useEffect(() => {
    const completed = localStorage.getItem('volume_profile_tour_completed');
    if (!completed) {
      setShowTour(true);
    }
  }, []);

  // Keyboard Shortcuts registration
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const active = document.activeElement?.tagName;
      if (active === 'INPUT' || active === 'TEXTAREA') return;

      if (e.code === 'KeyH') {
        e.preventDefault();
        setShowHelp(prev => !prev);
      } else if (e.code === 'KeyL') {
        e.preventDefault();
        setShowLegend(prev => !prev);
      } else if (e.code === 'KeyR') {
        e.preventDefault();
        if (chartRef.current) {
          chartRef.current.timeScale().fitContent();
        }
      } else if (e.code === 'Escape') {
        setShowHelp(false);
        setShowAiVerdictExplain(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Rotating tips timer
  useEffect(() => {
    const interval = setInterval(() => {
      setTipIndex(prev => (prev + 1) % TRADING_TIPS.length);
    }, 8500);
    return () => clearInterval(interval);
  }, []);

  // Volume Profile Bin calculation algorithm on visible candles
  const calculateVisibleProfile = (visibleCandles: PricePoint[], numBins: number = 45) => {
    if (visibleCandles.length === 0) return null;
    const highs = visibleCandles.map(c => c.high);
    const lows = visibleCandles.map(c => c.low);
    const closes = visibleCandles.map(c => c.close);
    const volumes = visibleCandles.map(c => c.volume);
    
    const pMin = Math.min(...lows);
    const pMax = Math.max(...highs);
    
    const w = (pMax - pMin) / numBins;
    const binVolumes = new Array(numBins).fill(0);
    const binRanges = Array.from({ length: numBins }, (_, i) => [pMin + i * w, pMin + (i + 1) * w]);
    
    for (let idx = 0; idx < visibleCandles.length; idx++) {
      const L = lows[idx];
      const H = highs[idx];
      const C = closes[idx];
      const V = volumes[idx];
      
      if (H > L) {
        for (let i = 0; i < numBins; i++) {
          const [bLow, bHigh] = binRanges[i];
          const overlap = Math.max(0, Math.min(H, bHigh) - Math.max(L, bLow));
          const prop = overlap / (H - L);
          binVolumes[i] += V * prop;
        }
      } else {
        const iBin = Math.min(numBins - 1, Math.max(0, Math.floor((C - pMin) / w)));
        binVolumes[iBin] += V;
      }
    }
    
    const maxVol = Math.max(...binVolumes);
    const pocIdx = binVolumes.indexOf(maxVol);
    const pocPrice = pMin + (pocIdx + 0.5) * w;
    
    // Value Area (70% Volume)
    const totalVol = binVolumes.reduce((a, b) => a + b, 0);
    const targetVol = 0.70 * totalVol;
    let iLow = pocIdx;
    let iHigh = pocIdx;
    let accumVol = binVolumes[pocIdx];
    
    while (accumVol < targetVol) {
      if (iLow > 0 && iHigh < numBins - 1) {
        const volAbove = binVolumes[iHigh + 1];
        const volBelow = binVolumes[iLow - 1];
        if (volAbove >= volBelow) {
          iHigh++;
          accumVol += volAbove;
        } else {
          iLow--;
          accumVol += volBelow;
        }
      } else if (iLow > 0) {
        iLow--;
        accumVol += binVolumes[iLow];
      } else if (iHigh < numBins - 1) {
        iHigh++;
        accumVol += binVolumes[iHigh];
      } else {
        break;
      }
    }
    
    const vahPrice = pMin + (iHigh + 1) * w;
    const valPrice = pMin + iLow * w;
    
    return {
      poc: pocPrice,
      vah: vahPrice,
      val: valPrice,
      maxVolume: maxVol,
      histogram: binVolumes.map((vol, i) => ({
        priceMin: binRanges[i][0],
        priceMax: binRanges[i][1],
        volume: vol
      }))
    };
  };

  // Synchronized canvas drawer
  const drawCanvasOverlay = () => {
    const canvas = canvasRef.current;
    const chart = chartRef.current;
    const candleSeries = candleSeriesRef.current;
    
    if (!canvas || !chart || !candleSeries || !data || !data.price_history) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const container = chartContainerRef.current;
    if (container) {
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
    }
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const timeScale = chart.timeScale();
    const visibleRange = timeScale.getVisibleLogicalRange();
    if (!visibleRange) return;
    
    const fromIndex = Math.max(0, Math.floor(visibleRange.from));
    const toIndex = Math.min(data.price_history.length - 1, Math.ceil(visibleRange.to));
    
    const visibleCandles = data.price_history.slice(fromIndex, toIndex + 1);
    if (visibleCandles.length === 0) return;
    
    const profile = calculateVisibleProfile(visibleCandles);
    if (!profile) return;
    
    const maxVolume = profile.maxVolume || 1.0;
    
    // Draw Bins
    if (showHistogram) {
      profile.histogram.forEach(bin => {
        const yTop = candleSeries.priceToCoordinate(bin.priceMax);
        const yBottom = candleSeries.priceToCoordinate(bin.priceMin);
        if (yTop === null || yBottom === null) return;
        
        const height = yBottom - yTop;
        const maxBarWidth = canvas.width * 0.28;
        const barWidth = (bin.volume / maxVolume) * maxBarWidth;
        
        const isPocBin = bin.priceMin <= profile.poc && bin.priceMax >= profile.poc;
        const insideVa = bin.priceMin >= profile.val && bin.priceMax <= profile.vah;
        
        if (isPocBin && showPoc) {
          ctx.fillStyle = 'rgba(234, 179, 8, 0.4)';
        } else if (insideVa && showValueArea) {
          ctx.fillStyle = 'rgba(79, 70, 229, 0.25)';
        } else {
          ctx.fillStyle = 'rgba(71, 85, 105, 0.12)';
        }
        
        const xOffset = canvas.width - barWidth - 65;
        ctx.fillRect(xOffset, yTop, barWidth, Math.max(1, height - 1));
      });
    }
    
    // Draw levels
    if (showPoc) {
      const yPoc = candleSeries.priceToCoordinate(profile.poc);
      if (yPoc !== null) {
        ctx.strokeStyle = 'rgba(234, 179, 8, 0.75)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 2]);
        ctx.beginPath();
        ctx.moveTo(10, yPoc);
        ctx.lineTo(canvas.width - 70, yPoc);
        ctx.stroke();
        ctx.fillStyle = '#eab308';
        ctx.font = 'bold 9px monospace';
        ctx.fillText(`POC ₹${profile.poc.toFixed(2)}`, 12, yPoc - 4);
      }
    }
    
    if (showValueArea) {
      const yVah = candleSeries.priceToCoordinate(profile.vah);
      const yVal = candleSeries.priceToCoordinate(profile.val);
      
      if (yVah !== null) {
        ctx.strokeStyle = 'rgba(16, 185, 129, 0.6)';
        ctx.lineWidth = 1;
        ctx.setLineDash([6, 3]);
        ctx.beginPath();
        ctx.moveTo(10, yVah);
        ctx.lineTo(canvas.width - 70, yVah);
        ctx.stroke();
        ctx.fillStyle = '#10b981';
        ctx.font = 'bold 9px monospace';
        ctx.fillText(`VAH ₹${profile.vah.toFixed(2)}`, 12, yVah - 4);
      }
      
      if (yVal !== null) {
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.6)';
        ctx.lineWidth = 1;
        ctx.setLineDash([6, 3]);
        ctx.beginPath();
        ctx.moveTo(10, yVal);
        ctx.lineTo(canvas.width - 70, yVal);
        ctx.stroke();
        ctx.fillStyle = '#ef4444';
        ctx.font = 'bold 9px monospace';
        ctx.fillText(`VAL ₹${profile.val.toFixed(2)}`, 12, yVal - 4);
      }
    }

    // Static HVN/LVN lines
    if (showHvnLvn && data) {
      data.hvn.forEach((hvn, i) => {
        const yCoord = candleSeries.priceToCoordinate(hvn);
        if (yCoord !== null) {
          ctx.strokeStyle = 'rgba(99, 102, 241, 0.4)';
          ctx.lineWidth = 0.5;
          ctx.setLineDash([3, 5]);
          ctx.beginPath();
          ctx.moveTo(10, yCoord);
          ctx.lineTo(canvas.width - 70, yCoord);
          ctx.stroke();
          ctx.fillStyle = '#818cf8';
          ctx.font = '8px monospace';
          ctx.fillText(`HVN ${i+1}: ₹${hvn}`, canvas.width - 150, yCoord - 3);
        }
      });

      data.lvn.forEach((lvn, i) => {
        const yCoord = candleSeries.priceToCoordinate(lvn);
        if (yCoord !== null) {
          ctx.strokeStyle = 'rgba(244, 63, 94, 0.4)';
          ctx.lineWidth = 0.5;
          ctx.setLineDash([3, 5]);
          ctx.beginPath();
          ctx.moveTo(10, yCoord);
          ctx.lineTo(canvas.width - 70, yCoord);
          ctx.stroke();
          ctx.fillStyle = '#fda4af';
          ctx.font = '8px monospace';
          ctx.fillText(`LVN ${i+1}: ₹${lvn}`, canvas.width - 150, yCoord - 3);
        }
      });
    }
  };

  // Mount TV Chart
  useEffect(() => {
    if (!chartContainerRef.current || !data || !data.price_history || data.price_history.length === 0) return;

    const container = chartContainerRef.current;
    container.innerHTML = '';

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 750,
      layout: {
        background: { type: ColorType.Solid, color: '#090d16' },
        textColor: '#64748b',
      },
      grid: {
        vertLines: { color: '#161e2e' },
        horzLines: { color: '#161e2e' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: '#38bdf8', width: 1, style: 3, labelBackgroundColor: '#0369a1' },
        horzLine: { color: '#38bdf8', width: 1, style: 3, labelBackgroundColor: '#0369a1' },
      },
      rightPriceScale: { borderColor: '#1e293b', visible: true },
      timeScale: { borderColor: '#1e293b', timeVisible: true, secondsVisible: false },
    });

    chartRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10b981', downColor: '#ef4444', borderVisible: false, wickUpColor: '#10b981', wickDownColor: '#ef4444'
    });
    candleSeriesRef.current = candleSeries;

    const lineSeries = chart.addLineSeries({ color: '#38bdf8', lineWidth: 2 });
    lineSeriesRef.current = lineSeries;

    const ema20Series = chart.addLineSeries({ color: '#3b82f6', lineWidth: 1, visible: showEmas });
    ema20SeriesRef.current = ema20Series;

    const ema50Series = chart.addLineSeries({ color: '#a855f7', lineWidth: 1, visible: showEmas });
    ema50SeriesRef.current = ema50Series;

    const ema200Series = chart.addLineSeries({ color: '#f97316', lineWidth: 1, visible: showEmas });
    ema200SeriesRef.current = ema200Series;

    const vwapSeries = chart.addLineSeries({ color: '#06b6d4', lineWidth: 2, visible: showVwap });
    vwapSeriesRef.current = vwapSeries;

    const formattedData = data.price_history.map(c => {
      const ts = Math.floor(new Date(c.date).getTime() / 1000) as UTCTimestamp;
      return { time: ts, open: c.open, high: c.high, low: c.low, close: c.close };
    });

    if (chartType === 'candles') {
      candleSeries.setData(formattedData);
      lineSeries.setData([]);
    } else {
      candleSeries.setData([]);
      lineSeries.setData(formattedData.map(d => ({ time: d.time, value: d.close })));
    }

    // Set Indicator states
    ema20Series.setData(data.price_history.filter(c => c.ema20 !== null).map(c => ({
      time: Math.floor(new Date(c.date).getTime() / 1000) as UTCTimestamp, value: c.ema20 as number
    })));
    ema50Series.setData(data.price_history.filter(c => c.ema50 !== null).map(c => ({
      time: Math.floor(new Date(c.date).getTime() / 1000) as UTCTimestamp, value: c.ema50 as number
    })));
    ema200Series.setData(data.price_history.filter(c => c.ema200 !== null).map(c => ({
      time: Math.floor(new Date(c.date).getTime() / 1000) as UTCTimestamp, value: c.ema200 as number
    })));
    vwapSeries.setData(data.price_history.filter(c => c.vwap !== null).map(c => ({
      time: Math.floor(new Date(c.date).getTime() / 1000) as UTCTimestamp, value: c.vwap as number
    })));

    // Render markers
    if (showStructure) {
      const markers: any[] = [];
      data.price_history.forEach(c => {
        const time = (Math.floor(new Date(c.date).getTime() / 1000)) as UTCTimestamp;
        
        if (c.choch) {
          markers.push({ time, position: 'aboveBar', color: '#a855f7', shape: 'arrowDown', text: 'CHoCH' });
        } else if (c.bos) {
          markers.push({ time, position: 'aboveBar', color: '#f43f5e', shape: 'arrowDown', text: 'BOS' });
        } else if (c.sweep) {
          markers.push({ time, position: 'belowBar', color: '#3b82f6', shape: 'arrowUp', text: 'SWEEP' });
        } else if (c.swing_high !== null) {
          markers.push({ time, position: 'aboveBar', color: '#e2e8f0', shape: 'circle', size: 0.5 });
        } else if (c.swing_low !== null) {
          markers.push({ time, position: 'belowBar', color: '#e2e8f0', shape: 'circle', size: 0.5 });
        }
      });
      
      if (chartType === 'candles') {
        candleSeries.setMarkers(markers);
      } else {
        lineSeries.setMarkers(markers);
      }
    } else {
      candleSeries.setMarkers([]);
      lineSeries.setMarkers([]);
    }

    chart.timeScale().fitContent();

    chart.timeScale().subscribeVisibleLogicalRangeChange(() => {
      requestAnimationFrame(drawCanvasOverlay);
    });

    const resizeObserver = new ResizeObserver(entries => {
      for (let entry of entries) {
        const { width, height } = entry.contentRect;
        chart.resize(width, height);
        requestAnimationFrame(drawCanvasOverlay);
      }
    });
    
    resizeObserver.observe(container);

    setTimeout(() => {
      requestAnimationFrame(drawCanvasOverlay);
    }, 100);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [data, showHistogram, showValueArea, showPoc, showHvnLvn, showEmas, showVwap, showStructure, chartType]);

  const handleRefresh = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'BUY': return 'text-emerald-400 border-emerald-500/20 bg-emerald-950/40 cursor-pointer hover:bg-emerald-900/40';
      case 'SELL': return 'text-red-400 border-red-500/20 bg-red-950/40 cursor-pointer hover:bg-red-900/40';
      default: return 'text-slate-400 border-slate-800 bg-slate-800/50 cursor-pointer hover:bg-slate-750';
    }
  };

  const getShapeColor = (shape: string) => {
    if (shape.includes('P-shape')) return 'text-emerald-400 bg-emerald-950/40 border border-emerald-500/20';
    if (shape.includes('b-shape')) return 'text-red-400 bg-red-950/40 border border-red-500/20';
    if (shape.includes('Double Distribution')) return 'text-indigo-400 bg-indigo-950/40 border border-indigo-500/20';
    if (shape.includes('Trend Day')) return 'text-cyan-400 bg-cyan-950/40 border border-cyan-500/20';
    return 'text-slate-300 bg-slate-800/80 border border-slate-700/50';
  };

  const formattedPrice = (val: number) => `₹${val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const handleExportPNG = () => {
    const container = chartContainerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const tvCanvas = container.querySelector('canvas');
    if (!tvCanvas) return;

    const combinedCanvas = document.createElement('canvas');
    combinedCanvas.width = tvCanvas.width;
    combinedCanvas.height = tvCanvas.height;

    const ctx = combinedCanvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(tvCanvas, 0, 0);
      ctx.drawImage(canvas, 0, 0);
      const link = document.createElement('a');
      link.download = `VolumeProfile_${selectedSymbol}.png`;
      link.href = combinedCanvas.toDataURL();
      link.click();
    }
  };

  const handleExportCSV = () => {
    if (!data || !data.price_history) return;
    const headers = 'Date,Open,High,Low,Close,Volume,EMA20,EMA50,EMA200,VWAP\n';
    const rows = data.price_history.map(c => 
      `${c.date},${c.open},${c.high},${c.low},${c.close},${c.volume},${c.ema20 || ''},${c.ema50 || ''},${c.ema200 || ''},${c.vwap || ''}`
    ).join('\n');
    
    const blob = new Blob([headers + rows], { type: 'text/csv' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `VolumeProfileData_${selectedSymbol}.csv`;
    link.click();
  };

  if (loading && !data) {
    return (
      <div className="space-y-6 text-slate-100 font-sans">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white font-display flex items-center gap-2">
              <Cpu className="text-brand-500 animate-spin" size={24} /> Volume Profile Workstation
            </h2>
          </div>
        </div>
        <div className="space-y-6 animate-pulse">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-24 bg-slate-900/60 border border-slate-880 rounded-xl"></div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 h-[750px] bg-slate-900/60 border border-slate-880 rounded-xl"></div>
            <div className="h-[750px] bg-slate-900/60 border border-slate-880 rounded-xl"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6 font-sans">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <h2 className="text-2xl font-bold tracking-tight text-white font-display">Volume Profile Terminal</h2>
          <GlobalSymbolSearch />
        </div>
        <ErrorCard message={error || 'No analysis data found.'} onRetry={handleRefresh} title="Volume Profile Engine Error" />
      </div>
    );
  }

  return (
    <div className="space-y-6 text-slate-100 font-sans selection:bg-brand-500/30 relative">
      
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-2xl font-bold tracking-tight text-white font-display">Volume Profile Terminal</h2>
            <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20">WORKSTATION</span>
          </div>
          <p className="text-sm text-slate-400 font-medium mt-0.5">
            {data.company_name} ({data.symbol}) • <span className="text-slate-500">{data.sector}</span>
          </p>
        </div>
        
        <div className="flex flex-wrap items-center gap-3">
          {/* Tour Restart button */}
          <button
            onClick={() => setShowTour(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-950/80 border border-slate-800 hover:bg-slate-900 text-slate-450 hover:text-white transition-colors text-xs font-bold font-mono"
            title="Start Onboarding Tour"
          >
            <Sparkles size={13} className="text-brand-500 animate-pulse" /> Tour
          </button>

          {/* Floating Help Button */}
          <button
            onClick={() => { setShowHelp(true); setHelpTab('overview'); }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-655 hover:bg-brand-600 border border-brand-500/20 text-white transition-all text-xs font-bold shadow-lg shadow-brand-500/10"
          >
            <HelpCircle size={14} /> Help & Learn
          </button>

          {/* Lookbacks */}
          <div className="flex items-center bg-slate-950/80 border border-slate-800 rounded-lg p-1">
            {[30, 60, 90, 180, 360, 720].map((days) => (
              <button
                key={days}
                onClick={() => setLookback(days)}
                className={`px-2.5 py-1 text-[10px] font-mono font-bold rounded transition-all ${
                  lookback === days 
                    ? 'bg-brand-600 text-white shadow' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
                }`}
              >
                {days === 720 ? '2Y' : days === 360 ? '1Y' : `${days}D`}
              </button>
            ))}
          </div>

          <GlobalSymbolSearch />

          <button
            onClick={handleRefresh}
            className="p-2 rounded-lg bg-slate-950/80 border border-slate-800 hover:bg-slate-900 text-slate-450 hover:text-white transition-colors"
            title="Recalculate Volume Profile"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin text-brand-400' : ''} />
          </button>
        </div>
      </div>

      {/* STATS TILES ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Spot Price */}
        <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md hover:border-slate-700/60 transition-all flex flex-col justify-between relative group">
          <button 
            onClick={() => { setShowHelp(true); setHelpTab('glossary'); }}
            className="absolute top-3 right-3 text-slate-500 hover:text-brand-400 transition-colors opacity-0 group-hover:opacity-100"
            title="Info"
          >
            <Info size={12} />
          </button>
          <div className="flex justify-between items-center text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            <span>Market Price</span>
            <Activity size={12} className="text-brand-500 animate-pulse" />
          </div>
          <div className="my-2 text-2xl font-bold font-mono text-slate-100">{formattedPrice(data.price)}</div>
          <div className="text-[10px] text-slate-400 font-semibold">
            POC Deviation: <span className={`font-bold font-mono ${data.price >= data.poc ? 'text-emerald-400' : 'text-red-400'}`}>{(((data.price - data.poc) / data.poc) * 100).toFixed(2)}%</span>
          </div>
        </div>

        {/* POC */}
        <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md hover:border-slate-700/60 transition-all flex flex-col justify-between relative group">
          <button 
            onClick={() => { setShowHelp(true); setHelpTab('glossary'); }}
            className="absolute top-3 right-3 text-slate-500 hover:text-brand-400 transition-colors opacity-0 group-hover:opacity-100"
            title="Info"
          >
            <Info size={12} />
          </button>
          <div className="flex justify-between items-center text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            <span>Point of Control (POC)</span>
            <span className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
          </div>
          <div className="my-2 text-2xl font-bold font-mono text-yellow-400">{formattedPrice(data.poc)}</div>
          <div className="text-[10px] text-slate-400 font-semibold">Highest traded price by volume.</div>
        </div>

        {/* Value Area */}
        <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md hover:border-slate-700/60 transition-all flex flex-col justify-between relative group">
          <button 
            onClick={() => { setShowHelp(true); setHelpTab('theory'); }}
            className="absolute top-3 right-3 text-slate-500 hover:text-brand-400 transition-colors opacity-0 group-hover:opacity-100"
            title="Info"
          >
            <Info size={12} />
          </button>
          <div className="flex justify-between items-center text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            <span>Value Area (70%)</span>
            <Scale size={12} className="text-indigo-400" />
          </div>
          <div className="my-1.5 text-xs font-bold font-mono text-slate-200">
            <div>VAH: <span className="text-emerald-400 font-extrabold">{formattedPrice(data.vah)}</span></div>
            <div className="mt-0.5">VAL: <span className="text-red-400 font-extrabold">{formattedPrice(data.val)}</span></div>
          </div>
          <div className="text-[10px] text-slate-400 font-semibold">Acceptance range limits.</div>
        </div>

        {/* Profile Shape */}
        <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl backdrop-blur-md hover:border-slate-700/60 transition-all flex flex-col justify-between relative group">
          <button 
            onClick={() => { setShowHelp(true); setHelpTab('theory'); }}
            className="absolute top-3 right-3 text-slate-500 hover:text-brand-400 transition-colors opacity-0 group-hover:opacity-100"
            title="Info"
          >
            <Info size={12} />
          </button>
          <div className="flex justify-between items-center text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            <span>Auction Profile Structure</span>
            <Percent size={12} className="text-cyan-400" />
          </div>
          <div className="my-2">
            <span className={`text-xs font-bold px-2 py-1 rounded font-mono block text-center ${getShapeColor(data.shape)}`}>
              {data.shape}
            </span>
          </div>
          <div className="text-[10px] text-slate-400 font-semibold">Bias: <span className="text-slate-200 font-bold">{data.institutional_bias}</span></div>
        </div>
      </div>

      {/* WORKSTATION GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* CHART SECTION (70%) */}
        <div className="lg:col-span-8 bg-slate-900/40 border border-slate-850 rounded-2xl p-3 shadow-2xl relative">
          
          {/* Chart top controls bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 mb-3 border-b border-slate-850 text-xs">
            <div className="flex items-center gap-3">
              <button 
                onClick={() => setChartType(chartType === 'candles' ? 'line' : 'candles')}
                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-750 text-slate-350 font-bold text-[10px] uppercase font-mono border border-slate-700/50"
              >
                {chartType === 'candles' ? 'Line' : 'Candles'}
              </button>
              
              <div className="flex rounded-md border border-slate-800 bg-slate-950 p-0.5">
                {[
                  { name: 'Hist', state: showHistogram, setState: setShowHistogram },
                  { name: 'VA', state: showValueArea, setState: setShowValueArea },
                  { name: 'POC', state: showPoc, setState: setShowPoc },
                  { name: 'Nodes', state: showHvnLvn, setState: setShowHvnLvn },
                ].map(t => (
                  <button
                    key={t.name}
                    onClick={() => t.setState(!t.state)}
                    className={`px-2 py-0.5 rounded text-[9px] uppercase font-bold tracking-wider font-mono transition-all ${
                      t.state ? 'bg-brand-650 text-white' : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    {t.name}
                  </button>
                ))}
              </div>
              
              <div className="flex rounded-md border border-slate-800 bg-slate-950 p-0.5">
                {[
                  { name: 'EMA', state: showEmas, setState: setShowEmas },
                  { name: 'VWAP', state: showVwap, setState: setShowVwap },
                  { name: 'Struct', state: showStructure, setState: setShowStructure },
                ].map(t => (
                  <button
                    key={t.name}
                    onClick={() => t.setState(!t.state)}
                    className={`px-2 py-0.5 rounded text-[9px] uppercase font-bold tracking-wider font-mono transition-all ${
                      t.state ? 'bg-indigo-650 text-white' : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    {t.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Export buttons */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowLegend(prev => !prev)}
                className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors text-[10px] font-bold border border-slate-700/50 ${
                  showLegend ? 'bg-slate-800 text-brand-400' : 'bg-slate-950/40 text-slate-400 hover:text-slate-200'
                }`}
                title="Toggle Chart Legend"
              >
                Legend
              </button>
              <button 
                onClick={handleExportPNG}
                className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-350 hover:text-white transition-colors border border-slate-700/50 text-[10px] font-bold"
              >
                <Download size={11} /> PNG
              </button>
              <button 
                onClick={handleExportCSV}
                className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-350 hover:text-white transition-colors border border-slate-700/50 text-[10px] font-bold"
              >
                <Download size={11} /> CSV
              </button>
            </div>
          </div>

          {/* MAIN CANVAS CONTAINER */}
          <div className="relative w-full h-[750px] overflow-hidden rounded-xl bg-[#090d16] border border-slate-900">
            {/* Collapsible Chart Legend Overlay */}
            {showLegend && (
              <div className="absolute top-4 left-4 z-30 w-52 p-3 bg-slate-950/90 border border-slate-850 rounded-xl backdrop-blur-md text-[10px] space-y-2 select-none shadow-xl">
                <div className="font-bold font-mono text-slate-450 border-b border-slate-850 pb-1 flex justify-between items-center">
                  <span>CHART LEGEND</span>
                  <button onClick={() => setShowLegend(false)} className="text-slate-500 hover:text-white">✕</button>
                </div>
                <div className="space-y-1.5 text-slate-400">
                  <div className="flex items-center justify-between"><span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-yellow-500" /> POC</span> <span className="text-[9px] text-slate-600">Fair Value Point</span></div>
                  <div className="flex items-center justify-between"><span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-emerald-500" /> VAH</span> <span className="text-[9px] text-slate-600">Value High</span></div>
                  <div className="flex items-center justify-between"><span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-red-500" /> VAL</span> <span className="text-[9px] text-slate-600">Value Low</span></div>
                  <div className="flex items-center justify-between"><span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-indigo-500" /> HVN</span> <span className="text-[9px] text-slate-600">Support / Resistance</span></div>
                  <div className="flex items-center justify-between"><span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-rose-500" /> LVN</span> <span className="text-[9px] text-slate-600">Slippage Valley</span></div>
                  <div className="flex items-center justify-between"><span className="flex items-center gap-1.5"><span className="w-2.5 h-1.5 bg-slate-800 rounded-sm" /> Histogram</span> <span className="text-[9px] text-slate-600">Volume Profile Bins</span></div>
                </div>
              </div>
            )}

            {/* TV Lightweight Chart Div */}
            <div ref={chartContainerRef} className="absolute inset-0 z-10 w-full h-full" />
            
            {/* Transparent HTML5 Canvas Overlay */}
            <canvas ref={canvasRef} className="absolute inset-0 z-20 pointer-events-none w-full h-full" />
          </div>
        </div>

        {/* SIDEBAR ANALYSIS PANEL (30%) */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* Rotating Trading Tip Card */}
          <div className="p-4 bg-gradient-to-r from-violet-950/20 to-brand-950/20 border border-slate-850 rounded-xl flex gap-3 items-start relative overflow-hidden shadow-inner">
            <Sparkles className="text-brand-400 shrink-0 mt-0.5" size={16} />
            <div className="space-y-1">
              <span className="text-[9px] font-mono font-black uppercase text-brand-400 tracking-wider">Trading tip</span>
              <p className="text-[11px] font-medium leading-relaxed text-slate-350">
                {TRADING_TIPS[tipIndex]}
              </p>
            </div>
          </div>

          {/* QUANT RECOMMENDATIONS & SCORES */}
          <div className="p-5 bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800/80 rounded-xl relative overflow-hidden shadow-xl group">
            <button 
              onClick={() => { setShowHelp(true); setHelpTab('strategies'); }}
              className="absolute top-4 right-4 text-slate-500 hover:text-brand-400 transition-colors opacity-0 group-hover:opacity-100"
              title="Learn about AI rules"
            >
              <Info size={12} />
            </button>
            <div className="absolute top-0 right-0 p-3 text-[9px] font-bold font-mono text-slate-500 uppercase tracking-widest pointer-events-none">QUANT MODEL</div>
            
            <h3 className="font-display font-semibold text-xs text-slate-400 uppercase tracking-wider mb-4">
              AI Market Verdict
            </h3>

            <div className="flex items-center gap-3 mb-5">
              <button 
                onClick={() => setShowAiVerdictExplain(prev => !prev)}
                className={`text-2xl font-black px-4 py-2 rounded-xl border tracking-wide font-display shadow-inner transition-colors ${getActionColor(data.action)}`}
                title="Click for detailed reasoning"
              >
                {data.verdict}
              </button>
              <div className="flex-1">
                <div className="text-[10px] font-bold text-slate-500 uppercase">Confidence Score</div>
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex-1 bg-slate-800/50 h-2 rounded-full overflow-hidden border border-slate-700/20">
                    <div 
                      className={`h-full rounded-full transition-all duration-700 bg-brand-500`}
                      style={{ width: `${data.confidence}%` }}
                    />
                  </div>
                  <span className="text-xs font-black font-mono text-brand-400">{data.confidence}%</span>
                </div>
              </div>
            </div>

            {/* Collapsible reasoning popup */}
            {showAiVerdictExplain && (
              <div className="mb-4 p-4 bg-slate-950 border border-slate-850 rounded-xl space-y-2 text-xs leading-relaxed">
                <div className="flex justify-between items-center border-b border-slate-850 pb-1.5 mb-1.5 font-bold font-display text-white">
                  <span>Verdict Analysis Details</span>
                  <button onClick={() => setShowAiVerdictExplain(false)} className="text-slate-500 hover:text-white">✕</button>
                </div>
                <div><span className="text-slate-500 font-bold uppercase text-[9px] block">Trigger Logic</span> Price position relative to VAH/VAL/POC indicators.</div>
                <div><span className="text-slate-500 font-bold uppercase text-[9px] block">Directional Conviction</span> {data.confidence}% based on historical profile boundaries.</div>
                <div><span className="text-slate-500 font-bold uppercase text-[9px] block">Scenario Invalid If</span> Price breaks and closes past the opposite boundary (VAH/VAL).</div>
              </div>
            )}

            <div className="space-y-3">
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider border-b border-slate-800/60 pb-1.5">Auction Market Theory Signals</div>
              {data.factors.map((factor, index) => {
                const isBullish = factor.toLowerCase().includes('bullish') || factor.toLowerCase().includes('above') || factor.toLowerCase().includes('support') || factor.toLowerCase().includes('buyers');
                const isBearish = factor.toLowerCase().includes('bearish') || factor.toLowerCase().includes('below') || factor.toLowerCase().includes('resistance') || factor.toLowerCase().includes('sellers');
                
                return (
                  <div key={index} className="flex gap-2 items-start text-xs font-medium text-slate-200">
                    {isBullish ? (
                      <ArrowUpRight size={14} className="text-emerald-400 shrink-0 mt-0.5" />
                    ) : isBearish ? (
                      <ArrowDownRight size={14} className="text-red-400 shrink-0 mt-0.5" />
                    ) : (
                      <ChevronRight size={14} className="text-slate-500 shrink-0 mt-0.5" />
                    )}
                    <span className="leading-snug">{factor}</span>
                  </div>
                );
              })}
            </div>

            <div className="mt-4 pt-4 border-t border-slate-800/60 text-xs text-slate-400 leading-relaxed font-sans font-semibold italic">
              " {data.summary} "
            </div>
          </div>

          {/* RISK MANAGEMENT PANEL */}
          <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-xl shadow-md relative group">
            <button 
              onClick={() => { setShowHelp(true); setHelpTab('strategies'); }}
              className="absolute top-4 right-4 text-slate-500 hover:text-brand-400 transition-colors opacity-0 group-hover:opacity-100"
              title="Learn about R:R setups"
            >
              <Info size={12} />
            </button>
            <h3 className="font-display font-semibold text-xs text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-1.5">
              <Target size={14} className="text-brand-500" /> Risk Management
            </h3>

            <div className="space-y-3 font-mono text-sm">
              <div className="flex justify-between items-center py-1 border-b border-slate-800/50">
                <span className="text-slate-500 font-bold text-xs">Entry Zone</span>
                <span className="text-slate-100 font-extrabold">{data.risk_management.entry_zone}</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-slate-800/50">
                <span className="text-slate-500 font-bold text-xs">Stop Loss</span>
                <span className="text-red-400 font-extrabold">{formattedPrice(data.risk_management.stop_loss)}</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-slate-800/50">
                <span className="text-slate-500 font-bold text-xs">Target 1</span>
                <span className="text-emerald-400 font-extrabold">{formattedPrice(data.risk_management.target_1)}</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-slate-800/50">
                <span className="text-slate-500 font-bold text-xs">Target 2</span>
                <span className="text-emerald-400 font-extrabold">{formattedPrice(data.risk_management.target_2)}</span>
              </div>
              {data.risk_management.target_3 && (
                <div className="flex justify-between items-center py-1 border-b border-slate-800/50">
                  <span className="text-slate-500 font-bold text-xs">Target 3 (Swing)</span>
                  <span className="text-emerald-400 font-extrabold">{formattedPrice(data.risk_management.target_3)}</span>
                </div>
              )}
              <div className="flex justify-between items-center py-1">
                <span className="text-slate-500 font-bold text-xs">Risk Reward</span>
                <span className="text-brand-400 font-black px-2.5 py-0.5 rounded bg-brand-500/10 border border-brand-500/20 text-xs">
                  1 : {data.risk_management.risk_reward_ratio}
                </span>
              </div>
            </div>
          </div>

          {/* TIMEFRAME MATRIX */}
          <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-xl shadow-md">
            <h3 className="font-display font-semibold text-xs text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-1.5">
              <Activity size={14} className="text-brand-500" /> Timeframe Matrix
            </h3>

            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500 font-bold">
                  <th className="py-2">Timeframe</th>
                  <th className="py-2">Structure</th>
                  <th className="py-2 text-right">Verdict</th>
                </tr>
              </thead>
              <tbody className="font-semibold text-slate-200">
                <tr className="border-b border-slate-800/40">
                  <td className="py-3 font-bold">Daily</td>
                  <td className="py-3">
                    <span className={`px-2 py-0.5 rounded text-[9px] font-mono ${getShapeColor(data.timeframes.daily.shape)}`}>
                      {data.timeframes.daily.shape}
                    </span>
                  </td>
                  <td className="py-3 text-right">
                    <span className={`font-mono font-bold text-xs ${
                      data.timeframes.daily.verdict === 'Buy' ? 'text-emerald-400' :
                      data.timeframes.daily.verdict === 'Sell' ? 'text-red-400' : 'text-slate-400'
                    }`}>
                      {data.timeframes.daily.verdict}
                    </span>
                  </td>
                </tr>
                <tr className="border-b border-slate-800/40">
                  <td className="py-3 font-bold">Weekly</td>
                  <td className="py-3">
                    <span className={`px-2 py-0.5 rounded text-[9px] font-mono ${getShapeColor(data.timeframes.weekly.shape)}`}>
                      {data.timeframes.weekly.shape}
                    </span>
                  </td>
                  <td className="py-3 text-right">
                    <span className={`font-mono font-bold text-xs ${
                      data.timeframes.weekly.verdict === 'Buy' ? 'text-emerald-400' :
                      data.timeframes.weekly.verdict === 'Sell' ? 'text-red-400' : 'text-slate-400'
                    }`}>
                      {data.timeframes.weekly.verdict}
                    </span>
                  </td>
                </tr>
                <tr>
                  <td className="py-3 font-bold">Monthly</td>
                  <td className="py-3">
                    <span className={`px-2 py-0.5 rounded text-[9px] font-mono ${getShapeColor(data.timeframes.monthly.shape)}`}>
                      {data.timeframes.monthly.shape}
                    </span>
                  </td>
                  <td className="py-3 text-right">
                    <span className={`font-mono font-bold text-xs ${
                      data.timeframes.monthly.verdict === 'Buy' ? 'text-emerald-400' :
                      data.timeframes.monthly.verdict === 'Sell' ? 'text-red-400' : 'text-slate-400'
                    }`}>
                      {data.timeframes.monthly.verdict}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* SECTOR RS RATING */}
          <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-xl grid grid-cols-3 gap-2 text-center text-xs shadow-sm">
            <div>
              <span className="text-[10px] text-slate-500 block font-bold uppercase tracking-wider">Sector Score</span>
              <span className="font-extrabold text-sm text-slate-200 mt-0.5 inline-block">{data.sector_integration.sector_score}/100</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block font-bold uppercase tracking-wider">Sector Rank</span>
              <span className="font-extrabold text-sm text-slate-200 mt-0.5 inline-block">#{data.sector_integration.sector_rank}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block font-bold uppercase tracking-wider">Relative Strength</span>
              <span className={`font-extrabold text-sm mt-0.5 inline-block ${data.sector_integration.relative_strength_rank >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {data.sector_integration.relative_strength_rank >= 0 ? '+' : ''}{data.sector_integration.relative_strength_rank} RS
              </span>
            </div>
          </div>

        </div>

      </div>

      {/* Educational sliding panel drawer */}
      {showHelp && (
        <VolumeProfileHelpCenter 
          onClose={() => setShowHelp(false)} 
          initialTopic={helpTab}
        />
      )}

      {/* Guided Tour Overlay */}
      {showTour && (
        <VolumeProfileTour 
          onClose={() => setShowTour(false)}
        />
      )}

    </div>
  );
};

export default VolumeProfilePage;
