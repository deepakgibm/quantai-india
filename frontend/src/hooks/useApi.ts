import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, apiGet, apiPost, apiRequest, API_URL, getAuthHeaders } from '../services/api';

export const useWatchlistQuery = () => {
  return useQuery({
    queryKey: ['watchlist'],
    queryFn: async () => {
      const res = await apiGet<any[]>('/api/watchlist');
      if (!res.success) {
        throw new Error(res.error?.message || 'Failed to fetch watchlist');
      }
      return res.data || [];
    },
  });
};

export const useWatchlistPerformanceQuery = (virtualInvestment: number) => {
  return useQuery({
    queryKey: ['watchlist-performance', virtualInvestment],
    queryFn: async () => {
      const res = await apiGet<any>(`/api/watchlist/performance?virtualInvestment=${virtualInvestment}`);
      if (!res.success) {
        throw new Error(res.error?.message || 'Failed to fetch performance');
      }
      return res.data;
    },
  });
};

export const useWatchlistAnalyticsQuery = (virtualInvestment: number) => {
  return useQuery({
    queryKey: ['watchlist-analytics', virtualInvestment],
    queryFn: async () => {
      const res = await apiGet<any>(`/api/watchlist/analytics?virtualInvestment=${virtualInvestment}`);
      if (!res.success) {
        throw new Error(res.error?.message || 'Failed to fetch analytics');
      }
      return res.data;
    },
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
