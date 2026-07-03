import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, apiGet, apiPost, apiRequest, API_URL, getAuthHeaders } from '../services/api';

export const useWatchlistQuery = () => {
  return useQuery({
    queryKey: ['watchlist'],
    queryFn: async () => {
      console.log("Loading Watchlist Portfolio...");
      console.log("Calling watchlist sync API...");
      try {
        const res = await apiGet<any[]>('/api/watchlist');
        if (!res.success) {
          throw new Error(res.error?.message || 'Failed to fetch watchlist');
        }
        console.log("Watchlist API Response:", res);
        const data = res.data || [];
        localStorage.setItem('watchlist_cache', JSON.stringify(data));
        localStorage.setItem('watchlist_cache_time', Date.now().toString());
        return data;
      } catch (err: any) {
        console.error("Watchlist Sync Error:", err);
        console.error("Status:", err?.response?.status);
        console.error("Response:", err?.response?.data);
        const cached = localStorage.getItem('watchlist_cache');
        if (cached) {
          console.warn('Watchlist API failed, returning cached data:', err);
          return JSON.parse(cached);
        }
        throw err;
      }
    },
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    refetchInterval: 5000,
  });
};

export const useWatchlistPerformanceQuery = (virtualInvestment: number) => {
  return useQuery({
    queryKey: ['watchlist-performance', virtualInvestment],
    queryFn: async () => {
      try {
        const res = await apiGet<any>(`/api/watchlist/performance?virtualInvestment=${virtualInvestment}`);
        if (!res.success) {
          throw new Error(res.error?.message || 'Failed to fetch performance');
        }
        localStorage.setItem(`watchlist_perf_cache_${virtualInvestment}`, JSON.stringify(res.data));
        return res.data;
      } catch (err) {
        const cached = localStorage.getItem(`watchlist_perf_cache_${virtualInvestment}`);
        if (cached) {
          console.warn('Watchlist performance API failed, returning cached data:', err);
          return JSON.parse(cached);
        }
        throw err;
      }
    },
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    refetchInterval: 5000,
  });
};

export const useWatchlistAnalyticsQuery = (virtualInvestment: number) => {
  return useQuery({
    queryKey: ['watchlist-analytics', virtualInvestment],
    queryFn: async () => {
      try {
        const res = await apiGet<any>(`/api/watchlist/analytics?virtualInvestment=${virtualInvestment}`);
        if (!res.success) {
          throw new Error(res.error?.message || 'Failed to fetch analytics');
        }
        localStorage.setItem(`watchlist_analytics_cache_${virtualInvestment}`, JSON.stringify(res.data));
        return res.data;
      } catch (err) {
        const cached = localStorage.getItem(`watchlist_analytics_cache_${virtualInvestment}`);
        if (cached) {
          console.warn('Watchlist analytics API failed, returning cached data:', err);
          return JSON.parse(cached);
        }
        throw err;
      }
    },
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    refetchInterval: 5000,
  });
};

export const useSectorAnalysisQuery = (timeframe: string = '1D') => {
  return useQuery({
    queryKey: ['sector-analysis', timeframe],
    queryFn: async () => {
      const res = await apiGet<any>(`/api/sector-analysis?timeframe=${timeframe}`);
      if (!res.success) {
        throw new Error(res.error?.message || 'Failed to fetch sector analysis');
      }
      return res.data;
    },
    refetchInterval: 30000, // refresh every 30s
  });
};

export const useSectorHeatmapQuery = () => {
  return useQuery({
    queryKey: ['sector-heatmap'],
    queryFn: async () => {
      const res = await apiGet<any>('/api/market/heatmap');
      if (!res.success) {
        throw new Error(res.error?.message || 'Failed to fetch heatmap');
      }
      return res.data;
    },
    refetchInterval: 30000,
  });
};

export const useGainersLosersQuery = () => {
  return useQuery({
    queryKey: ['gainers-losers'],
    queryFn: async () => {
      const res = await apiGet<any>('/api/market/top-movers');
      if (!res.success) {
        throw new Error(res.error?.message || 'Failed to fetch top movers');
      }
      return res.data;
    },
    refetchInterval: 30000,
  });
};

export const useMarketIndicesQuery = () => {
  return useQuery({
    queryKey: ['market-indices'],
    queryFn: async () => {
      return await api.getMarketIndices();
    },
    refetchInterval: 30000,
  });
};

export const useOrdersQuery = () => {
  return useQuery({
    queryKey: ['orders'],
    queryFn: async () => {
      return await api.getOrders();
    },
  });
};

export const useAddWatchlistItemMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { symbol: string; watchlist_price?: number }) => {
      const res = await apiPost<any>('/api/watchlist', payload);
      if (!res.success) {
        throw new Error(res.error?.message || 'Failed to add symbol');
      }
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
      queryClient.invalidateQueries({ queryKey: ['watchlist-performance'] });
      queryClient.invalidateQueries({ queryKey: ['watchlist-analytics'] });
    },
  });
};

export const useRemoveWatchlistItemMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (symbol: string) => {
      const res = await apiRequest<{ status: string }>(
        `${API_URL}/api/watchlist/${symbol}`,
        { method: 'DELETE', headers: getAuthHeaders() }
      );
      if (!res.success) {
        throw new Error(res.error?.message || 'Failed to remove symbol');
      }
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
      queryClient.invalidateQueries({ queryKey: ['watchlist-performance'] });
      queryClient.invalidateQueries({ queryKey: ['watchlist-analytics'] });
    },
  });
};
