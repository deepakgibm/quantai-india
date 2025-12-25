import React, { useState, useEffect, useRef, useCallback } from 'react';
// GoogleGenAI import removed - API calls now go through secure backend proxy
import { Activity, Wifi, ChevronDown, Eye, BarChart2, Layers, Maximize2, Newspaper, RefreshCw, ExternalLink, AlertCircle } from 'lucide-react';
import { createChart, ColorType, CrosshairMode, LineStyle, Time } from 'lightweight-charts';

// --- Types ---
interface ChartData {
   time: Time;
   open: number;
   high: number;
   low: number;
   close: number;
   volume: number;
}

interface IndicatorConfig {
   id: string;
   type: 'SMA' | 'EMA' | 'RSI';
   period: number;
   color: string;
   visible: boolean;
}

interface Position {
   id: string;
   symbol: string;
   quantity: number;
   entryPrice: number;
   ltp: number;
   pnl: number;
}

interface SentimentData {
   sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL' | 'UNKNOWN';
   text: string;
   sources: { title: string; uri: string }[];
}

// --- Hooks ---

// Detect Dark Mode changes
const useDarkMode = () => {
   const [isDark, setIsDark] = useState(document.documentElement.classList.contains('dark'));
   useEffect(() => {
      const observer = new MutationObserver(() => {
         setIsDark(document.documentElement.classList.contains('dark'));
      });
      observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
      return () => observer.disconnect();
   }, []);
   return isDark;
};

// Robust Resize Observer
const useResizeObserver = (ref: React.RefObject<HTMLElement>, callback: (entry: ResizeObserverEntry) => void) => {
   useEffect(() => {
      if (!ref.current) return;
      const observer = new ResizeObserver((entries) => {
         if (entries[0]) callback(entries[0]);
      });
      observer.observe(ref.current);
      return () => observer.disconnect();
   }, [ref, callback]);
};

const LiveMonitor: React.FC = () => {
   // --- Refs ---
   const chartContainerRef = useRef<HTMLDivElement>(null);
   const volumeContainerRef = useRef<HTMLDivElement>(null);
   const indicatorContainerRef = useRef<HTMLDivElement>(null);
   const toolTipRef = useRef<HTMLDivElement>(null);

   const chartRef = useRef<any>(null);
   const volumeChartRef = useRef<any>(null);
   const indicatorChartRef = useRef<any>(null);

   const candleSeriesRef = useRef<any>(null);
   const volumeSeriesRef = useRef<any>(null);
   const indicatorSeriesRef = useRef<any>(null);

   const smaSeriesMap = useRef<Map<string, any>>(new Map());

   // Ref to store data for event listeners to avoid stale closures
   const dataRef = useRef<ChartData[]>([]);

   // --- State ---
   const isDark = useDarkMode();
   const [data, setData] = useState<ChartData[]>([]);
   const [currentPrice, setCurrentPrice] = useState(22430.5);
   const [legendData, setLegendData] = useState<ChartData | null>(null);

   // Selection & AI State
   const [selectedSymbol, setSelectedSymbol] = useState('NIFTY 50');
   const [aiSentiment, setAiSentiment] = useState<SentimentData>({
      sentiment: 'UNKNOWN',
      text: 'Initializing AI Agent...',
      sources: []
   });
   const [isAiLoading, setIsAiLoading] = useState(false);

   // Sync dataRef with state
   useEffect(() => {
      dataRef.current = data;
   }, [data]);

   // Positions State
   const [positions, setPositions] = useState<Position[]>([
      { id: '1', symbol: 'RELIANCE', quantity: 50, entryPrice: 2440.0, ltp: 2456.0, pnl: 800 },
      { id: '2', symbol: 'HDFCBANK', quantity: 25, entryPrice: 1455.0, ltp: 1450.0, pnl: -125 },
      { id: '3', symbol: 'INFY', quantity: 100, entryPrice: 1580.0, ltp: 1585.0, pnl: 500 },
   ]);

   // Calculate Dynamic P&L
   const totalPnl = positions.reduce((acc, pos) => acc + pos.pnl, 0);
   const dailyGoal = 10000;
   const progressPct = Math.min(Math.max((totalPnl / dailyGoal) * 100, 0), 100);

   const [indicators, setIndicators] = useState<IndicatorConfig[]>([
      { id: 'sma20', type: 'SMA', period: 20, color: '#eab308', visible: true },
      { id: 'sma50', type: 'SMA', period: 50, color: '#ec4899', visible: false },
      { id: 'rsi', type: 'RSI', period: 14, color: '#8b5cf6', visible: false },
   ]);
   const [showIndicatorMenu, setShowIndicatorMenu] = useState(false);

   // --- AI Data Fetcher (Price + Sentiment) ---
   // SECURITY: Uses backend proxy instead of exposing API key to frontend
   const fetchRealTimeData = async (symbol: string) => {
      setIsAiLoading(true);
      try {
         // Call backend proxy endpoint - API key stays server-side
         const response = await fetch(`http://localhost:8000/api/ai/sentiment?symbol=${encodeURIComponent(symbol)}`);

         if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
         }

         const data = await response.json();

         setAiSentiment({
            sentiment: data.sentiment || 'NEUTRAL',
            text: data.summary || 'Market data updated successfully.',
            sources: []  // Sources come from backend if needed
         });

         if (data.ltp && typeof data.ltp === 'number') {
            const newPrice = data.ltp;

            setCurrentPrice(newPrice);

            // Use precise financial math for P&L calculation
            setPositions(prev => prev.map(p => {
               if (p.symbol === symbol) {
                  // Precise P&L: (currentPrice - entryPrice) * quantity
                  // Using manual Decimal-like precision (TODO: import Money utility)
                  const priceDiff = Math.round((newPrice - p.entryPrice) * 100) / 100;
                  const newPnl = Math.round(priceDiff * p.quantity * 100) / 100;
                  return { ...p, ltp: newPrice, pnl: newPnl };
               }
               return p;
            }));
         }

      } catch (e) {
         console.error("AI Fetch Error", e);
         setAiSentiment({
            sentiment: 'UNKNOWN',
            text: "Unable to fetch real-time data. Please check your connection.",
            sources: []
         });
      } finally {
         setIsAiLoading(false);
      }
   };

   // Initial Fetch & on selection change
   useEffect(() => {
      fetchRealTimeData(selectedSymbol);
   }, [selectedSymbol]);


   // --- Helpers ---
   const generateInitialData = (count = 300): ChartData[] => {
      let initialData: ChartData[] = [];
      let time = Math.floor(Date.now() / 1000) - count * 60;
      let price = currentPrice; // Use current state price
      for (let i = 0; i < count; i++) {
         const open = price + (Math.random() - 0.5) * 20;
         const close = open + (Math.random() - 0.5) * 20;
         const high = Math.max(open, close) + Math.random() * 10;
         const low = Math.min(open, close) - Math.random() * 10;
         const volume = Math.floor(Math.random() * 10000) + 1000;
         initialData.push({ time: time as Time, open, high, low, close, volume });
         price = close;
         time += 60;
      }
      return initialData;
   };

   const calculateSMA = (data: ChartData[], period: number) => {
      const smaData = [];
      for (let i = 0; i < data.length; i++) {
         if (i < period - 1) continue;
         let sum = 0;
         for (let j = 0; j < period; j++) {
            sum += data[i - j].close;
         }
         smaData.push({ time: data[i].time, value: sum / period });
      }
      return smaData;
   };

   const calculateRSI = (data: ChartData[], period: number) => {
      const rsiData = [];
      let gains = 0;
      let losses = 0;

      // First calculation
      for (let i = 1; i <= period; i++) {
         const change = data[i].close - data[i - 1].close;
         if (change > 0) gains += change;
         else losses += Math.abs(change);
      }

      let avgGain = gains / period;
      let avgLoss = losses / period;

      for (let i = period + 1; i < data.length; i++) {
         const change = data[i].close - data[i - 1].close;
         const gain = change > 0 ? change : 0;
         const loss = change < 0 ? Math.abs(change) : 0;

         avgGain = (avgGain * (period - 1) + gain) / period;
         avgLoss = (avgLoss * (period - 1) + loss) / period;

         const rs = avgGain / avgLoss;
         const rsi = 100 - (100 / (1 + rs));

         rsiData.push({ time: data[i].time, value: rsi });
      }
      return rsiData;
   };

   // --- Chart Initialization ---
   useEffect(() => {
      if (!chartContainerRef.current || !volumeContainerRef.current) return;

      const chartColors = {
         bg: isDark ? '#0f172a' : '#ffffff', // slate-900 : white
         text: isDark ? '#94a3b8' : '#334155',
         border: isDark ? '#1e293b' : '#e2e8f0',
         grid: isDark ? '#1e293b' : '#f1f5f9',
      };

      const commonOptions = {
         layout: {
            background: { type: ColorType.Solid, color: chartColors.bg },
            textColor: chartColors.text,
         },
         grid: {
            vertLines: { color: chartColors.grid },
            horzLines: { color: chartColors.grid },
         },
         crosshair: { mode: CrosshairMode.Normal },
         timeScale: { timeVisible: true, secondsVisible: false, borderColor: chartColors.border },
         rightPriceScale: { borderColor: chartColors.border },
      };

      // 1. Main Candlestick Chart
      const mainChart = createChart(chartContainerRef.current, {
         ...commonOptions,
         height: 300,
         width: chartContainerRef.current.clientWidth,
      }) as any;

      // Visual differentiation: Green for Up (Bullish), Red for Down (Bearish)
      const candleSeries = mainChart.addCandlestickSeries({
         upColor: '#22c55e',        // Green body
         downColor: '#ef4444',      // Red body
         borderVisible: true,
         borderUpColor: '#22c55e',  // Green border
         borderDownColor: '#ef4444',// Red border
         wickUpColor: '#22c55e',    // Green wick
         wickDownColor: '#ef4444'   // Red wick
      });

      // 2. Volume Chart
      const volumeChart = createChart(volumeContainerRef.current, {
         ...commonOptions,
         height: 80,
         width: volumeContainerRef.current.clientWidth,
         layout: { ...commonOptions.layout, background: { type: ColorType.Solid, color: 'transparent' } } // Seamless look
      }) as any;

      const volumeSeries = volumeChart.addHistogramSeries({
         priceFormat: { type: 'volume' },
         priceScaleId: '', // Overlay mode if needed, but here we use separate chart
      });

      // 3. RSI Indicator Chart (Conditional)
      let indicatorChart: any = null;
      let indicatorSeries: any = null;

      if (indicatorContainerRef.current) {
         indicatorChart = createChart(indicatorContainerRef.current, {
            ...commonOptions,
            height: 100,
            width: indicatorContainerRef.current.clientWidth,
         }) as any;

         indicatorSeries = indicatorChart.addLineSeries({ color: '#8b5cf6', lineWidth: 2 });
         // Add RSI Bands
         const topLine = indicatorChart.addLineSeries({ color: '#94a3b8', lineWidth: 1, lineStyle: LineStyle.Dotted });
         const botLine = indicatorChart.addLineSeries({ color: '#94a3b8', lineWidth: 1, lineStyle: LineStyle.Dotted });
         topLine.setData([{ time: 0 as unknown as Time, value: 70 }, { time: 2000000000 as unknown as Time, value: 70 }]);
         botLine.setData([{ time: 0 as unknown as Time, value: 30 }, { time: 2000000000 as unknown as Time, value: 30 }]);
      }

      // Store Refs
      chartRef.current = mainChart;
      volumeChartRef.current = volumeChart;
      indicatorChartRef.current = indicatorChart;

      candleSeriesRef.current = candleSeries;
      volumeSeriesRef.current = volumeSeries;
      indicatorSeriesRef.current = indicatorSeries;

      // Initial Data
      const initialData = generateInitialData();
      setData(initialData);
      dataRef.current = initialData;

      candleSeries.setData(initialData);
      volumeSeries.setData(initialData.map(d => ({
         time: d.time,
         value: d.volume,
         color: d.close >= d.open ? '#22c55e' : '#ef4444'
      })));

      if (indicatorSeries) {
         indicatorSeries.setData(calculateRSI(initialData, 14));
      }

      setLegendData(initialData[initialData.length - 1]);

      // --- Synchronization ---
      const getSeries = (chart: any) => {
         if (chart === mainChart) return candleSeries;
         if (chart === volumeChart) return volumeSeries;
         if (chart === indicatorChart) return indicatorSeries;
         return null;
      };

      const syncCharts = (source: any, targets: any[]) => {
         source.timeScale().subscribeVisibleTimeRangeChange((range: any) => {
            targets.forEach(t => {
               if (t && range) t.timeScale().setVisibleRange(range);
            });
         });
         // Crosshair Sync
         source.subscribeCrosshairMove((param: any) => {
            targets.forEach(t => {
               if (!t) return;
               if (!param.time) {
                  t.clearCrosshairPosition();
                  return;
               }
               const s = getSeries(t);
               if (s) {
                  t.setCrosshairPosition(0, param.time, s);
               }
            });
         });
      };

      const allCharts = [mainChart, volumeChart, indicatorChart].filter(Boolean);

      if (allCharts.length > 1) {
         syncCharts(mainChart, [volumeChart, indicatorChart]);
         syncCharts(volumeChart, [mainChart, indicatorChart]);
         if (indicatorChart) syncCharts(indicatorChart, [mainChart, volumeChart]);
      }

      // --- Crosshair Move Handler ---
      mainChart.subscribeCrosshairMove((param: any) => {
         const tooltip = toolTipRef.current;
         if (!tooltip) return;

         if (
            param.point === undefined ||
            !param.time ||
            param.point.x < 0 ||
            param.point.x > chartContainerRef.current!.clientWidth ||
            param.point.y < 0 ||
            param.point.y > chartContainerRef.current!.clientHeight
         ) {
            tooltip.style.display = 'none';
            // Reset legend to latest data
            const latest = dataRef.current[dataRef.current.length - 1];
            if (latest) setLegendData(latest);
            return;
         }

         const item = param.seriesData.get(candleSeries);
         const dataPoint = dataRef.current.find(d => d.time === param.time);
         const volume = dataPoint ? dataPoint.volume : 0;

         if (item) {
            // Update Tooltip
            tooltip.style.display = 'block';
            const dateStr = new Date(param.time * 1000).toLocaleTimeString();
            const isUp = item.close >= item.open;
            const colorHex = isUp ? '#22c55e' : '#ef4444';

            let left = param.point.x + 15;
            let top = param.point.y + 15;

            // Prevent tooltip clipping
            const containerWidth = chartContainerRef.current!.clientWidth;
            const containerHeight = chartContainerRef.current!.clientHeight;
            const tooltipWidth = 190;
            const tooltipHeight = 140;

            if (left + tooltipWidth > containerWidth) left = param.point.x - tooltipWidth - 15;
            if (top + tooltipHeight > containerHeight) top = param.point.y - tooltipHeight - 15;

            tooltip.style.left = `${left}px`;
            tooltip.style.top = `${top}px`;

            tooltip.innerHTML = `
             <div class="font-bold text-slate-700 dark:text-slate-300 mb-2 border-b border-slate-200 dark:border-slate-700 pb-1">${dateStr}</div>
             <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                <span class="text-slate-500 dark:text-slate-400">Open</span>
                <span class="text-right font-medium dark:text-white">${item.open.toFixed(2)}</span>
                
                <span class="text-slate-500 dark:text-slate-400">High</span>
                <span class="text-right font-medium text-green-500">${item.high.toFixed(2)}</span>
                
                <span class="text-slate-500 dark:text-slate-400">Low</span>
                <span class="text-right font-medium text-red-500">${item.low.toFixed(2)}</span>
                
                <span class="text-slate-500 dark:text-slate-400">Close</span>
                <span class="text-right font-bold" style="color: ${colorHex}">${item.close.toFixed(2)}</span>
                
                <span class="text-slate-500 dark:text-slate-400">Volume</span>
                <span class="text-right font-medium text-blue-500">${volume.toLocaleString()}</span>
             </div>
          `;

            // Update Legend
            setLegendData({
               ...item,
               volume: volume
            } as ChartData);
         }
      });

      return () => {
         mainChart.remove();
         volumeChart.remove();
         if (indicatorChart) indicatorChart.remove();
      };
   }, [isDark]); // Re-create chart on theme change

   // --- Resize Handling ---
   const handleResize = useCallback((entry: ResizeObserverEntry) => {
      if (chartRef.current) chartRef.current.applyOptions({ width: entry.contentRect.width });
      if (volumeChartRef.current) volumeChartRef.current.applyOptions({ width: entry.contentRect.width });
      if (indicatorChartRef.current) indicatorChartRef.current.applyOptions({ width: entry.contentRect.width });
   }, []);

   useResizeObserver(chartContainerRef, handleResize);

   // --- Real-time Updates ---
   useEffect(() => {
      const interval = setInterval(() => {
         setData(prevData => {
            if (prevData.length === 0) return prevData;
            const last = prevData[prevData.length - 1];
            const nextTime = (last.time as unknown as number + 60) as Time;

            // Simulate movement around the CURRENT REAL PRICE
            const volatility = currentPrice * 0.0005; // 0.05% volatility
            const change = (Math.random() - 0.5) * volatility;

            // Use currentPrice state as the anchor
            const close = currentPrice + change;
            const open = last.close;
            const high = Math.max(open, close) + Math.random() * (volatility / 2);
            const low = Math.min(open, close) - Math.random() * (volatility / 2);
            const volume = Math.floor(Math.random() * 5000) + 500;

            const newCandle = { time: nextTime, open, high, low, close, volume };

            // Update Charts
            if (candleSeriesRef.current) candleSeriesRef.current.update(newCandle);
            if (volumeSeriesRef.current) volumeSeriesRef.current.update({
               time: nextTime,
               value: volume,
               color: close >= open ? '#22c55e' : '#ef4444'
            });

            // Smoothly transition price state
            setCurrentPrice(close);

            const newData = [...prevData.slice(-299), newCandle]; // Keep 300

            // Update RSI
            const rsiInd = indicators.find(i => i.type === 'RSI' && i.visible);
            if (rsiInd && indicatorSeriesRef.current) {
               const rsiData = calculateRSI(newData, rsiInd.period);
               const lastRsi = rsiData[rsiData.length - 1];
               if (lastRsi) indicatorSeriesRef.current.update(lastRsi);
            }

            setLegendData(prev => prev ? newCandle : null);

            return newData;
         });

         // Simulate position P&L updates based on current price movements
         setPositions(prevPositions => prevPositions.map(pos => {
            // If this position is the selected symbol, sync it with the main chart's price
            // Otherwise, just add random noise for the demo
            if (pos.symbol === selectedSymbol) {
               const newPnl = (currentPrice - pos.entryPrice) * pos.quantity;
               return { ...pos, ltp: currentPrice, pnl: newPnl };
            } else {
               const fluctuation = (Math.random() - 0.5) * 1.5;
               const newLtp = pos.ltp + fluctuation;
               const newPnl = (newLtp - pos.entryPrice) * pos.quantity;
               return { ...pos, ltp: newLtp, pnl: newPnl };
            }
         }));

      }, 1000);
      return () => clearInterval(interval);
   }, [indicators, currentPrice, selectedSymbol]);

   // --- Update Indicators (SMA) ---
   useEffect(() => {
      if (!chartRef.current || data.length === 0) return;

      indicators.filter(i => i.type === 'SMA').forEach(ind => {
         let series = smaSeriesMap.current.get(ind.id);

         if (ind.visible) {
            if (!series) {
               series = chartRef.current!.addLineSeries({
                  color: ind.color,
                  lineWidth: 2,
                  crosshairMarkerVisible: false,
                  lastValueVisible: false,
                  priceLineVisible: false
               });
               smaSeriesMap.current.set(ind.id, series);
            }
            const smaData = calculateSMA(data, ind.period);
            series.setData(smaData);
         } else {
            if (series) {
               chartRef.current?.removeSeries(series);
               smaSeriesMap.current.delete(ind.id);
            }
         }
      });
   }, [data, indicators]);

   const toggleIndicator = (id: string) => {
      setIndicators(prev => prev.map(i => i.id === id ? { ...i, visible: !i.visible } : i));
   };

   const rsiVisible = indicators.find(i => i.type === 'RSI')?.visible;

   return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-140px)]">

         {/* LEFT: Charting Engine */}
         <div className="lg:col-span-2 flex flex-col gap-4">
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 flex-1 flex flex-col overflow-hidden relative">

               {/* Header / Toolbar */}
               <div className="flex justify-between items-center p-3 border-b border-slate-200 dark:border-slate-700 z-20 bg-white dark:bg-slate-800">
                  <div className="flex items-center gap-4">
                     <div className="flex items-center gap-2 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 px-2 py-1 rounded transition-colors group">
                        <h2 className="font-bold text-lg text-slate-900 dark:text-white group-hover:text-brand-600 transition-colors">{selectedSymbol}</h2>
                        <ChevronDown size={16} className="text-slate-400" />
                     </div>
                     <div className="flex items-baseline gap-2">
                        <span className={`text-2xl font-bold font-mono ${currentPrice >= 22400 ? 'text-green-500' : 'text-red-500'}`}>
                           ₹{currentPrice.toFixed(2)}
                        </span>
                        <span className="flex items-center gap-1 text-[10px] font-bold text-green-600 bg-green-100 dark:bg-green-900/30 px-2 py-0.5 rounded-full animate-pulse">
                           <Wifi size={10} /> MARKET OPEN
                        </span>
                     </div>
                  </div>

                  <div className="flex items-center gap-2">
                     <div className="relative">
                        <button
                           onClick={() => setShowIndicatorMenu(!showIndicatorMenu)}
                           className={`p-2 rounded-lg border flex items-center gap-2 text-sm font-medium transition-all ${showIndicatorMenu ? 'bg-brand-50 border-brand-200 text-brand-600' : 'bg-white dark:bg-slate-700 border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300'}`}
                        >
                           <Layers size={16} /> Study
                        </button>
                        {showIndicatorMenu && (
                           <div className="absolute top-full right-0 mt-2 w-56 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 p-3 z-50">
                              <h4 className="text-xs font-bold text-slate-400 uppercase mb-2">Overlays</h4>
                              {indicators.map(ind => (
                                 <div key={ind.id} className="flex items-center justify-between py-1.5">
                                    <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300 cursor-pointer select-none">
                                       <input type="checkbox" checked={ind.visible} onChange={() => toggleIndicator(ind.id)} className="rounded text-brand-600 focus:ring-brand-500" />
                                       {ind.type} {ind.period}
                                    </label>
                                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: ind.color }}></div>
                                 </div>
                              ))}
                           </div>
                        )}
                     </div>
                     <div className="h-6 w-px bg-slate-200 dark:bg-slate-700 mx-1"></div>
                     <button className="p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"><BarChart2 size={18} /></button>
                     <button className="p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"><Maximize2 size={18} /></button>
                  </div>
               </div>

               {/* Chart Area */}
               <div className="flex-1 relative flex flex-col bg-slate-50 dark:bg-slate-900/50">
                  {/* Tooltip Element */}
                  <div
                     ref={toolTipRef}
                     className="absolute z-50 hidden p-3 rounded-xl shadow-xl pointer-events-none text-xs font-mono whitespace-nowrap backdrop-blur-md bg-white/90 dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 transition-all duration-75"
                     style={{ top: 0, left: 0 }}
                  ></div>

                  {/* Floating Legend */}
                  <div className="absolute top-2 left-3 z-10 pointer-events-none flex gap-4 text-xs font-mono">
                     <div className="flex gap-3 bg-white/80 dark:bg-slate-900/80 backdrop-blur px-3 py-1.5 rounded border border-slate-200 dark:border-slate-700 shadow-sm">
                        <span className="text-slate-500">O <span className={`font-bold ${legendData && legendData.open > legendData.close ? 'text-red-500' : 'text-green-500'}`}>{legendData?.open.toFixed(2)}</span></span>
                        <span className="text-slate-500">H <span className={`font-bold ${legendData && legendData.open > legendData.close ? 'text-red-500' : 'text-green-500'}`}>{legendData?.high.toFixed(2)}</span></span>
                        <span className="text-slate-500">L <span className={`font-bold ${legendData && legendData.open > legendData.close ? 'text-red-500' : 'text-green-500'}`}>{legendData?.low.toFixed(2)}</span></span>
                        <span className="text-slate-500">C <span className={`font-bold ${legendData && legendData.open > legendData.close ? 'text-red-500' : 'text-green-500'}`}>{legendData?.close.toFixed(2)}</span></span>
                        <span className="text-slate-500 border-l border-slate-300 dark:border-slate-600 pl-3">Vol <span className="font-bold text-slate-700 dark:text-slate-300">{legendData?.volume.toLocaleString()}</span></span>
                     </div>
                  </div>

                  {/* Main Chart */}
                  <div ref={chartContainerRef} className="flex-grow w-full relative" />

                  {/* Volume Chart (Fixed Height) */}
                  <div ref={volumeContainerRef} className="h-20 w-full border-t border-slate-200 dark:border-slate-800" />

                  {/* Indicator Pane (Conditional) */}
                  {rsiVisible && (
                     <div className="h-24 w-full border-t border-slate-200 dark:border-slate-800 relative bg-white dark:bg-slate-900">
                        <span className="absolute top-1 left-2 text-[10px] font-bold text-purple-500 bg-purple-50 dark:bg-purple-900/20 px-1.5 rounded z-10">RSI (14)</span>
                        <div ref={indicatorContainerRef} className="w-full h-full" />
                     </div>
                  )}
               </div>
            </div>
         </div>

         {/* RIGHT: Info Panel */}
         <div className="flex flex-col gap-4 h-full overflow-hidden">
            {/* P&L Card */}
            <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-2xl p-5 shadow-lg flex-shrink-0">
               <div className="flex justify-between items-start mb-4">
                  <div>
                     <p className="text-slate-400 text-xs uppercase font-bold tracking-wider mb-1">Net P&L</p>
                     <h3 className={`text-3xl font-bold flex items-center gap-2 ${totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {totalPnl >= 0 ? '+' : ''}₹{totalPnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} <Activity size={20} className="animate-pulse" />
                     </h3>
                  </div>
                  <div className="text-right">
                     <div className="text-xs bg-white/10 px-2 py-1 rounded border border-white/10">Margin Used: 45%</div>
                  </div>
               </div>
               <div className="w-full bg-slate-700/50 h-1.5 rounded-full overflow-hidden mb-2">
                  <div
                     className={`h-full ${totalPnl >= 0 ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]' : 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]'}`}
                     style={{ width: `${progressPct}%` }}
                  ></div>
               </div>
               <div className="flex justify-between text-xs text-slate-400">
                  <span>Daily Goal: ₹{dailyGoal.toLocaleString()}</span>
                  <span>{progressPct.toFixed(0)}% Achieved</span>
               </div>
            </div>

            {/* Positions List - Updated to handle dynamic P&L visual changes */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 flex-1 flex flex-col overflow-hidden">
               <div className="p-4 border-b border-slate-100 dark:border-slate-700 flex justify-between items-center flex-shrink-0">
                  <h3 className="font-bold text-slate-800 dark:text-white flex items-center gap-2">
                     <Eye size={16} className="text-brand-500" /> Open Positions
                  </h3>
                  <span className="bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400 text-xs font-bold px-2 py-0.5 rounded-full">{positions.length}</span>
               </div>
               <div className="flex-1 overflow-y-auto p-2 space-y-2">
                  {positions.map(pos => {
                     const isProfit = pos.pnl >= 0;
                     return (
                        <div
                           key={pos.id}
                           onClick={() => setSelectedSymbol(pos.symbol)}
                           className={`p-3 rounded-xl border transition-all group cursor-pointer ${selectedSymbol === pos.symbol ? 'bg-brand-50 border-brand-300 dark:bg-brand-900/20 dark:border-brand-700' : 'bg-slate-50 dark:bg-slate-900/50 border-slate-100 dark:border-slate-700 hover:border-brand-200 dark:hover:border-slate-600'}`}
                        >
                           <div className="flex justify-between items-center mb-2">
                              <span className="font-bold text-slate-700 dark:text-slate-200">{pos.symbol}</span>
                              <span className={`font-mono font-bold ${isProfit ? 'text-green-500' : 'text-red-500'}`}>
                                 {isProfit ? '+' : ''}₹{pos.pnl.toFixed(2)}
                              </span>
                           </div>
                           <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mb-2">
                              <span>{pos.quantity} Qty @ {pos.entryPrice}</span>
                              <span className="flex items-center gap-1">LTP: {pos.ltp.toFixed(2)}</span>
                           </div>
                           <div className="h-1 w-full bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden flex">
                              <div className={`h-full transition-all duration-500 ${isProfit ? 'bg-green-500' : 'bg-red-500'}`} style={{ width: `${Math.min(Math.abs(pos.pnl) / 10, 100)}%` }}></div>
                           </div>
                        </div>
                     )
                  })}
               </div>
            </div>

            {/* AI News & Sentiment Card - FIXED visual layout */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 h-64 overflow-hidden flex flex-col border border-slate-200 dark:border-slate-700 shadow-sm relative flex-shrink-0">
               <div className="flex items-center justify-between mb-3 border-b border-slate-100 dark:border-slate-700 pb-2 flex-shrink-0">
                  <div className="flex items-center gap-2 font-bold text-slate-800 dark:text-white">
                     <Newspaper size={16} className="text-brand-500" />
                     AI News & Sentiment
                  </div>
                  <button
                     onClick={() => fetchRealTimeData(selectedSymbol)}
                     disabled={isAiLoading}
                     className={`p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors ${isAiLoading ? 'animate-spin text-brand-500' : 'text-slate-500'}`}
                     title="Refresh Sentiment"
                  >
                     <RefreshCw size={14} />
                  </button>
               </div>

               <div className="flex-1 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-slate-200 dark:scrollbar-thumb-slate-700">
                  <div className="mb-4">
                     <div className="flex items-center flex-wrap gap-2 mb-2">
                        <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{selectedSymbol} Outlook:</span>
                        {aiSentiment.sentiment !== 'UNKNOWN' && (
                           <span className={`text-[10px] font-extrabold px-2.5 py-0.5 rounded border ${aiSentiment.sentiment === 'BULLISH' ? 'bg-green-50 text-green-600 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800' :
                              aiSentiment.sentiment === 'BEARISH' ? 'bg-red-50 text-red-600 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800' :
                                 'bg-yellow-50 text-yellow-600 border-yellow-200 dark:bg-yellow-900/20 dark:text-yellow-400 dark:border-yellow-800'
                              }`}>
                              {aiSentiment.sentiment}
                           </span>
                        )}
                     </div>
                     <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed border-l-2 border-brand-200 dark:border-brand-800 pl-3">
                        {aiSentiment.text}
                     </p>
                  </div>

                  {aiSentiment.sources.length > 0 && (
                     <div>
                        <p className="text-[10px] font-bold text-slate-400 uppercase mb-2 flex items-center gap-1"><AlertCircle size={10} /> Top Sources</p>
                        <div className="space-y-2">
                           {aiSentiment.sources.map((source, idx) => (
                              <a
                                 key={idx}
                                 href={source.uri}
                                 target="_blank"
                                 rel="noreferrer"
                                 className="block p-2.5 bg-slate-50 dark:bg-slate-900/40 rounded-lg border border-slate-100 dark:border-slate-700 hover:border-brand-300 dark:hover:border-brand-700 hover:shadow-sm transition-all group"
                              >
                                 <div className="flex items-start justify-between gap-2">
                                    <p className="text-xs font-medium text-slate-700 dark:text-slate-300 line-clamp-1 group-hover:text-brand-600 dark:group-hover:text-brand-400">
                                       {source.title}
                                    </p>
                                    <ExternalLink size={12} className="text-slate-400 flex-shrink-0 mt-0.5 group-hover:text-brand-500" />
                                 </div>
                              </a>
                           ))}
                        </div>
                     </div>
                  )}
               </div>

               {isAiLoading && (
                  <div className="absolute inset-0 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm flex items-center justify-center z-10 rounded-b-2xl">
                     <div className="flex flex-col items-center gap-3">
                        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
                        <span className="text-xs font-bold text-brand-600 animate-pulse">Fetching Real-Time Data...</span>
                     </div>
                  </div>
               )}
            </div>
         </div>
      </div>
   );
};

export default LiveMonitor;