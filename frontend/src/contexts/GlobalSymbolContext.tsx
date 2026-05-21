import React, { createContext, useContext, useState, useEffect } from 'react';

interface GlobalSymbolContextType {
  selectedSymbol: string;
  setSelectedSymbol: (symbol: string) => void;
  selectedDays: number;
  setSelectedDays: (days: number) => void;
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

  const setSelectedSymbol = (symbol: string) => {
    const cleanSymbol = symbol.toUpperCase().trim();
    setSelectedSymbolState(cleanSymbol);
    localStorage.setItem('selectedSymbol', cleanSymbol);
  };

  const setSelectedDays = (days: number) => {
    // Limit to max 60 days
    const cleanDays = Math.min(Math.max(days, 5), 60);
    setSelectedDaysState(cleanDays);
    localStorage.setItem('selectedDays', cleanDays.toString());
  };

  return (
    <GlobalSymbolContext.Provider
      value={{
        selectedSymbol,
        setSelectedSymbol,
        selectedDays,
        setSelectedDays,
      }}
    >
      {children}
    </GlobalSymbolContext.Provider>
  );
};
