import React, { useRef, useEffect, useCallback, useImperativeHandle, forwardRef } from 'react';
import {
  createChart,
  ColorType,
  CrosshairMode,
  IChartApi,
  ISeriesApi,
  UTCTimestamp,
  SeriesMarker,
  Time,
} from 'lightweight-charts';
import { RefreshCw } from 'lucide-react';
import { AdvancedChartData, ChartTimeframe, CrosshairData, IndicatorConfig } from './chartTypes';
import { CHART_COLORS } from './chartConstants';

// ============================================================================
// Types
// ============================================================================

export interface TradingChartHandle {
  getChart: () => IChartApi | null;
  getCandlestickSeries: () => ISeriesApi<'Candlestick'> | null;
  takeScreenshot: () => string | undefined;
  fitContent: () => void;
  updateIncrementalCandle: (candle: any) => void;
}

interface TradingChartProps {
  chartData: AdvancedChartData | null;
  chartLoading: boolean;
  chartError: string | null;
  timeframe: ChartTimeframe;
  activeIndicators: IndicatorConfig[];
  onCrosshairMove?: (data: CrosshairData) => void;
  isFullscreen: boolean;
  className?: string;
}

// ============================================================================
// Utility: Normalize timestamps
// ============================================================================

function normalizeTimestamp(t: any): UTCTimestamp {
  if (typeof t === 'string' && t.includes('T')) {
    return Math.floor(new Date(t).getTime() / 1000) as UTCTimestamp;
  }
  if (typeof t === 'number' && t > 10000000000) {
    return Math.floor(t / 1000) as UTCTimestamp;
  }
  return t as UTCTimestamp;
}

function timeToComparable(time: any): number {
  if (time === null || time === undefined) return 0;
  if (typeof time === 'object' && time.year && time.month && time.day) {
    return time.year * 10000 + time.month * 100 + time.day;
  }
  if (typeof time === 'string') {
    if (time.includes('T')) return Math.floor(new Date(time).getTime() / 1000);
    const parts = time.split('-');
    if (parts.length === 3) {
      const y = parseInt(parts[0], 10);
      const m = parseInt(parts[1], 10);
      const d = parseInt(parts[2], 10);
      if (!isNaN(y) && !isNaN(m) && !isNaN(d)) return y * 10000 + m * 100 + d;
    }
    return Math.floor(new Date(time).getTime() / 1000);
  }
  if (typeof time === 'number') {
    return time > 10000000000 ? Math.floor(time / 1000) : time;
  }
  return 0;
}

// ============================================================================
// Component
// ============================================================================

export const TradingChart = forwardRef<TradingChartHandle, TradingChartProps>(
  ({ chartData, chartLoading, chartError, timeframe, activeIndicators, onCrosshairMove, isFullscreen, className }, ref) => {

    // Refs
    const containerRef = useRef<HTMLDivElement | null>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const candlestickRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
    const volumeRef = useRef<ISeriesApi<'Histogram'> | null>(null);
    const ema20Ref = useRef<ISeriesApi<'Line'> | null>(null);
    const ema50Ref = useRef<ISeriesApi<'Line'> | null>(null);
    const vwapRef = useRef<ISeriesApi<'Line'> | null>(null);
    const markersRef = useRef<any[]>([]);
    const lastTimeRef = useRef<any>(null);
    const resizeObserverRef = useRef<ResizeObserver | null>(null);

    // ========================================================================
    // Expose imperative handle
    // ========================================================================
    useImperativeHandle(ref, () => ({
      getChart: () => chartRef.current,
      getCandlestickSeries: () => candlestickRef.current as ISeriesApi<'Candlestick'> | null,
      takeScreenshot: () => {
        if (chartRef.current) {
          return chartRef.current.takeScreenshot().toDataURL();
        }
        return undefined;
      },
      fitContent: () => {
        if (chartRef.current) {
          chartRef.current.timeScale().fitContent();
        }
      },
      updateIncrementalCandle: (candle: any) => {
        if (!candlestickRef.current) return;
        const t = normalizeTimestamp(candle.time);
        const newComp = timeToComparable(t);
        const lastComp = timeToComparable(lastTimeRef.current);
        if (lastTimeRef.current && newComp < lastComp) return;

        candlestickRef.current.update({
          time: t,
          open: Number(candle.open),
          high: Number(candle.high),
          low: Number(candle.low),
          close: Number(candle.close),
        });

        if (volumeRef.current && candle.volume != null) {
          volumeRef.current.update({
            time: t,
            value: Number(candle.volume),
            color: Number(candle.close) >= Number(candle.open) ? CHART_COLORS.bullishFaded : CHART_COLORS.bearishFaded,
          });
        }
        if (ema20Ref.current && candle.ema_20 != null && !isNaN(candle.ema_20)) {
          ema20Ref.current.update({ time: t, value: Number(candle.ema_20) });
        }
        if (ema50Ref.current && candle.ema_50 != null && !isNaN(candle.ema_50)) {
          ema50Ref.current.update({ time: t, value: Number(candle.ema_50) });
        }
        if (vwapRef.current && candle.vwap != null && !isNaN(candle.vwap)) {
          vwapRef.current.update({ time: t, value: Number(candle.vwap) });
        }

        if (newComp >= lastComp) lastTimeRef.current = t;
      },
    }));

    // ========================================================================
    // 1. Create chart instance (runs on mount + timeframe change)
    // ========================================================================
    useEffect(() => {
      const container = containerRef.current;
      if (!container) return;

      // Destroy previous chart
      if (chartRef.current) {
        try { chartRef.current.remove(); } catch (_) {}
        chartRef.current = null;
        candlestickRef.current = null;
        volumeRef.current = null;
        ema20Ref.current = null;
        ema50Ref.current = null;
        vwapRef.current = null;
        markersRef.current = [];
      }
      lastTimeRef.current = null;

      // Disconnect previous observer
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
        resizeObserverRef.current = null;
      }

      try {
        const chart = createChart(container, {
          width: container.clientWidth || 800,
          height: container.clientHeight || 700,
          layout: {
            background: { type: ColorType.Solid, color: CHART_COLORS.background },
            textColor: CHART_COLORS.textColor,
            fontFamily: "'Inter', 'SF Pro', -apple-system, sans-serif",
          },
          grid: {
            vertLines: { color: CHART_COLORS.gridLines },
            horzLines: { color: CHART_COLORS.gridLines },
          },
          crosshair: {
            mode: CrosshairMode.Normal,
            vertLine: { color: '#475569', width: 1, style: 3, labelBackgroundColor: '#1e293b' },
            horzLine: { color: '#475569', width: 1, style: 3, labelBackgroundColor: '#1e293b' },
          },
          rightPriceScale: {
            visible: true,
            borderColor: CHART_COLORS.borderColor,
            scaleMargins: { top: 0.05, bottom: 0.25 },
          },
          timeScale: {
            borderColor: CHART_COLORS.borderColor,
            timeVisible: true,
            secondsVisible: false,
            rightOffset: 5,
            minBarSpacing: 3,
          },
          handleScroll: { mouseWheel: true, pressedMouseMove: true },
          handleScale: { mouseWheel: true, pinch: true },
        });

        chartRef.current = chart;

        // Candlestick series
        const candlestickSeries = chart.addCandlestickSeries({
          upColor: CHART_COLORS.bullish,
          downColor: CHART_COLORS.bearish,
          borderVisible: false,
          wickUpColor: CHART_COLORS.bullish,
          wickDownColor: CHART_COLORS.bearish,
        });
        candlestickRef.current = candlestickSeries;

        // Volume series
        const volumeSeries = chart.addHistogramSeries({
          color: '#26a69a',
          priceFormat: { type: 'volume' },
          priceScaleId: 'volume',
        });
        volumeSeries.priceScale().applyOptions({
          scaleMargins: { top: 0.82, bottom: 0 },
        });
        volumeRef.current = volumeSeries;

        // EMA 20
        const ema20 = chart.addLineSeries({
          color: CHART_COLORS.ema20,
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        ema20Ref.current = ema20;

        // EMA 50
        const ema50 = chart.addLineSeries({
          color: CHART_COLORS.ema50,
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        ema50Ref.current = ema50;

        // VWAP
        const vwap = chart.addLineSeries({
          color: CHART_COLORS.vwap,
          lineWidth: 1,
          lineStyle: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        vwapRef.current = vwap;

        // Crosshair subscription
        chart.subscribeCrosshairMove((param) => {
          if (!onCrosshairMove) return;
          if (!param.time || !param.point) {
            onCrosshairMove({ time: null, price: null, ohlc: null, volume: null, indicators: {}, changePercent: null, changeAbsolute: null });
            return;
          }

          const ohlcData = param.seriesData?.get(candlestickSeries) as any;
          const volData = param.seriesData?.get(volumeSeries) as any;
          const ema20Data = param.seriesData?.get(ema20) as any;
          const ema50Data = param.seriesData?.get(ema50) as any;
          const vwapData = param.seriesData?.get(vwap) as any;

          onCrosshairMove({
            time: param.time as UTCTimestamp,
            price: ohlcData?.close ?? null,
            ohlc: ohlcData ? { open: ohlcData.open, high: ohlcData.high, low: ohlcData.low, close: ohlcData.close } : null,
            volume: volData?.value ?? null,
            indicators: {
              ema20: ema20Data?.value ?? null,
              ema50: ema50Data?.value ?? null,
              vwap: vwapData?.value ?? null,
            },
            changePercent: ohlcData ? ((ohlcData.close - ohlcData.open) / ohlcData.open) * 100 : null,
            changeAbsolute: ohlcData ? ohlcData.close - ohlcData.open : null,
          });
        });

        // ResizeObserver
        const observer = new ResizeObserver(entries => {
          if (!entries.length) return;
          const { width, height } = entries[0].contentRect;
          if (chartRef.current && width > 0 && height > 0) {
            chartRef.current.resize(width, height);
          }
        });
        observer.observe(container);
        resizeObserverRef.current = observer;

      } catch (e: any) {
        console.error('[TradingChart] Fatal error during chart creation:', e);
      }

      return () => {
        if (resizeObserverRef.current) {
          resizeObserverRef.current.disconnect();
          resizeObserverRef.current = null;
        }
        if (chartRef.current) {
          try { chartRef.current.remove(); } catch (_) {}
          chartRef.current = null;
          candlestickRef.current = null;
          volumeRef.current = null;
          ema20Ref.current = null;
          ema50Ref.current = null;
          vwapRef.current = null;
          markersRef.current = [];
        }
      };
    }, [timeframe]);

    // ========================================================================
    // 2. Populate chart data when chartData changes
    // ========================================================================
    useEffect(() => {
      const chart = chartRef.current;
      const candlestick = candlestickRef.current;
      const volume = volumeRef.current;
      const ema20 = ema20Ref.current;
      const ema50 = ema50Ref.current;
      const vwap = vwapRef.current;

      if (!chart || !candlestick || !volume || !ema20 || !ema50 || !vwap || !chartData?.candles?.length) {
        return;
      }

      // Build series data arrays
      const candles = chartData.candles
        .filter((c: any) => c && c.time && c.open != null && c.high != null && c.low != null && c.close != null && !isNaN(c.close))
        .map((c: any) => ({
          time: normalizeTimestamp(c.time),
          open: Number(c.open),
          high: Number(c.high),
          low: Number(c.low),
          close: Number(c.close),
        }));

      const volumeData = chartData.candles
        .filter((c: any) => c && c.time && c.volume != null && !isNaN(c.volume))
        .map((c: any) => ({
          time: normalizeTimestamp(c.time),
          value: Number(c.volume),
          color: Number(c.close) >= Number(c.open) ? CHART_COLORS.bullishFaded : CHART_COLORS.bearishFaded,
        }));

      const ema20Data = chartData.candles
        .filter((c: any) => c && c.time && c.ema_20 != null && !isNaN(c.ema_20))
        .map((c: any) => ({ time: normalizeTimestamp(c.time), value: Number(c.ema_20) }));

      const ema50Data = chartData.candles
        .filter((c: any) => c && c.time && c.ema_50 != null && !isNaN(c.ema_50))
        .map((c: any) => ({ time: normalizeTimestamp(c.time), value: Number(c.ema_50) }));

      const vwapData = chartData.candles
        .filter((c: any) => c && c.time && c.vwap != null && !isNaN(c.vwap))
        .map((c: any) => ({ time: normalizeTimestamp(c.time), value: Number(c.vwap) }));

      // Set data
      try {
        candlestick.setData(candles);
        if (candles.length > 0) {
          lastTimeRef.current = candles[candles.length - 1].time;
        }
      } catch (e) { console.error('[TradingChart] Error setting candlestick data:', e); }

      try { volume.setData(volumeData); } catch (e) { console.error('[TradingChart] Error setting volume data:', e); }
      try { ema20.setData(ema20Data); } catch (e) { console.error('[TradingChart] Error setting EMA20 data:', e); }
      try { ema50.setData(ema50Data); } catch (e) { console.error('[TradingChart] Error setting EMA50 data:', e); }
      try { vwap.setData(vwapData); } catch (e) { console.error('[TradingChart] Error setting VWAP data:', e); }

      // Clear previous price lines
      if ((candlestick as any)._priceLines) {
        (candlestick as any)._priceLines.forEach((l: any) => {
          try { candlestick.removePriceLine(l); } catch (_) {}
        });
      }
      (candlestick as any)._priceLines = [];

      // Support zones
      if (chartData.support_zones?.length) {
        chartData.support_zones.forEach(price => {
          const line = candlestick.createPriceLine({
            price,
            color: CHART_COLORS.support,
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: 'S',
          });
          (candlestick as any)._priceLines.push(line);
        });
      }

      // Resistance zones
      if (chartData.resistance_zones?.length) {
        chartData.resistance_zones.forEach(price => {
          const line = candlestick.createPriceLine({
            price,
            color: CHART_COLORS.resistance,
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: 'R',
          });
          (candlestick as any)._priceLines.push(line);
        });
      }

      // Breakout markers
      if (chartData.breakout_markers?.length) {
        try {
          const validMarkers = chartData.breakout_markers.map((m: any) => ({
            ...m,
            time: normalizeTimestamp(m.time),
          }));
          candlestick.setMarkers(validMarkers as SeriesMarker<Time>[]);
          markersRef.current = validMarkers;
        } catch (e) {
          console.error('[TradingChart] Error setting markers:', e);
        }
      } else {
        candlestick.setMarkers([]);
        markersRef.current = [];
      }

      // Auto-fit
      try { chart.timeScale().fitContent(); } catch (_) {}

    }, [chartData]);

    // ========================================================================
    // Render
    // ========================================================================

    return (
      <div className={`relative w-full h-full ${className || ''}`}>
        {/* Loading overlay */}
        {chartLoading && (
          <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center z-10">
            <div className="flex items-center gap-2 text-xs text-violet-400 font-bold">
              <RefreshCw className="animate-spin" size={14} />
              Loading Chart Data...
            </div>
          </div>
        )}

        {/* Error overlay */}
        {chartError && (
          <div className="absolute inset-0 bg-red-950/80 backdrop-blur-sm flex flex-col items-center justify-center z-20 p-6 text-center border border-red-500/50 rounded-xl">
            <span className="text-red-400 font-bold mb-2">Chart Render Error</span>
            <p className="text-xs text-red-200/80 whitespace-pre-wrap break-all">{chartError}</p>
          </div>
        )}

        {/* Chart container */}
        <div ref={containerRef} className="w-full h-full" />
      </div>
    );
  }
);

TradingChart.displayName = 'TradingChart';
