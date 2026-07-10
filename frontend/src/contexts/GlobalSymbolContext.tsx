import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { IndexInfo, UNIVERSE_OPTIONS } from '../types/indices';
import { API_URL, getAuthHeaders } from '../services/api';

interface GlobalSymbolContextType {
  selectedSymbol: string;
  setSelectedSymbol: (symbol: string) => void;
  selectedDays: number;
  setSelectedDays: (days: number) => void;
  // === Universe / Index filter ===
  selectedUniverse: string;
  setSelectedUniverse: (universe: string) => void;
  availableIndices: IndexInfo[];
  indicesLoading: boolean;
  refreshIndices: () => void;
}

const GlobalSymbolContext = createContext<GlobalSymbolContextType | null>(null);

export const useGlobalSymbol = () => {
  const context = useContext(GlobalSymbolContext);
  if (!context) {
    throw new Error('useGlobalSymbol must be used within a GlobalSymbolProvider');
  }
  return context;
};

export const GlobalSymbolProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedSymbol, setSelectedSymbolState] = useState<string>(() => {
    return localStorage.getItem('selectedSymbol') || 'RELIANCE';
  });
  const [selectedDays, setSelectedDaysState] = useState<number>(() => {
    const cached = localStorage.getItem('selectedDays');
    return cached ? parseInt(cached, 10) : 30;
  });

  // Universe / Index filter — persisted across sessions
  const [selectedUniverse, setSelectedUniverseState] = useState<string>(() => {
    return localStorage.getItem('selectedUniverse') || 'NIFTY 500';
  });
  const [availableIndices, setAvailableIndices] = useState<IndexInfo[]>([]);
  const [indicesLoading, setIndicesLoading] = useState(false);

  const setSelectedSymbol = (symbol: string) => {
    const cleanSymbol = symbol.toUpperCase().trim();
    setSelectedSymbolState(cleanSymbol);
    localStorage.setItem('selectedSymbol', cleanSymbol);
  };

  const setSelectedDays = (days: number) => {
    const cleanDays = Math.min(Math.max(days, 5), 60);
    setSelectedDaysState(cleanDays);
    localStorage.setItem('selectedDays', cleanDays.toString());
  };

  const setSelectedUniverse = (universe: string) => {
    setSelectedUniverseState(universe);
    localStorage.setItem('selectedUniverse', universe);
  };

  const fetchIndices = useCallback(async () => {
    setIndicesLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/indices`, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        setAvailableIndices(data.indices || []);
      }
    } catch (err) {
      console.warn('Failed to fetch indices from server, using static list');
      // Fall back to the static UNIVERSE_OPTIONS as IndexInfo-like objects
      const fallback: IndexInfo[] = UNIVERSE_OPTIONS
        .filter(o => o.value !== 'ALL')
        .map(o => ({
          index_name: o.value,
          display_name: o.label,
          category: o.category,
          description: '',
          constituent_count: 0,
          last_refreshed: null,
          is_active: true,
          nse_index_code: '',
          coverage_pct: 0,
        }));
      setAvailableIndices(fallback);
    } finally {
      setIndicesLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchIndices();
  }, [fetchIndices]);

  return (
    <GlobalSymbolContext.Provider
      value={{
        selectedSymbol,
        setSelectedSymbol,
        selectedDays,
        setSelectedDays,
        selectedUniverse,
        setSelectedUniverse,
        availableIndices,
        indicesLoading,
        refreshIndices: fetchIndices,
      }}
    >
      {children}
    </GlobalSymbolContext.Provider>
  );
};
