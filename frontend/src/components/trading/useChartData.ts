import { useState, useRef, useCallback } from 'react';
import { api } from '../../services/api';
import { AdvancedChartData, ChartTimeframe } from './chartTypes';
import { CHART_DEFAULTS } from './chartConstants';

/**
 * Custom hook that encapsulates all chart data fetching, caching, and incremental update logic.
 * Extracted from OptionFlow.tsx to decouple data management from rendering.
 */
export function useChartData(selectedSymbol: string) {
  const [chartData, setChartData] = useState<AdvancedChartData | null>(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState<string | null>(null);

  const chartCacheRef = useRef<Record<string, AdvancedChartData>>({});
  const abortControllerRef = useRef<AbortController | null>(null);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /**
   * Fetch full chart data for a symbol and timeframe.
   * Uses cache when available, otherwise fetches from API.
   */
  const fetchChartData = useCallback(async (symbol: string, timeframe: ChartTimeframe) => {
    const clean = symbol.toUpperCase().replace('NSE:', '').trim();
    const cacheKey = `${clean}_${timeframe}`;

    // Abort any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Check cache first
    if (chartCacheRef.current[cacheKey]) {
      console.log(`[Chart Data] Using cache for ${cacheKey}`);
      setChartData(chartCacheRef.current[cacheKey]);
      return;
    }

    setChartLoading(true);
    setChartError(null);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    let retries = 0;
    const maxRetries = CHART_DEFAULTS.maxRetries;

    const attemptFetch = async (): Promise<void> => {
      try {
        const response = await api.getOptionFlowChart(clean, timeframe);
        if (controller.signal.aborted) return;

        const chartPayload = response?.data && response?.success ? response.data : response;

        if (chartPayload && chartPayload.candles && chartPayload.candles.length > 0) {
          console.log(`[Chart Data] Fetched ${chartPayload.candles.length} candles for ${cacheKey}`);
          chartCacheRef.current[cacheKey] = chartPayload;
          setChartData(chartPayload);
          setChartError(null);
        } else {
          console.warn(`[Chart Data] No candles returned for ${cacheKey}`);
          setChartData(null);
          setChartError('No chart data available for this symbol.');
        }
      } catch (err: any) {
        if (controller.signal.aborted) return;

        if (retries < maxRetries) {
          retries++;
          console.warn(`[Chart Data] Fetch failed, retry ${retries}/${maxRetries}:`, err.message);
          return new Promise<void>((resolve) => {
            retryTimeoutRef.current = setTimeout(() => {
              attemptFetch().then(resolve);
            }, 2000 * retries);
          });
        }

        console.error(`[Chart Data] Failed after ${maxRetries} retries:`, err);
        setChartError(err.message || 'Failed to load chart data.');
      } finally {
        if (!controller.signal.aborted) {
          setChartLoading(false);
        }
      }
    };

    await attemptFetch();
  }, []);

  /**
   * Clear the cache for a specific key or all keys.
   */
  const clearCache = useCallback((cacheKey?: string) => {
    if (cacheKey) {
      delete chartCacheRef.current[cacheKey];
    } else {
      chartCacheRef.current = {};
    }
  }, []);

  /**
   * Cleanup abort controllers and retry timeouts.
   */
  const cleanup = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
    }
  }, []);

  return {
    chartData,
    setChartData,
    chartLoading,
    chartError,
    setChartError,
    fetchChartData,
    clearCache,
    cleanup,
    abortControllerRef,
    retryTimeoutRef,
  };
}
