import { create } from 'zustand';
import { MarketQuote, MarketDataService } from '../services/marketDataService';

interface MarketDataState {
  quotes: Record<string, MarketQuote>;
  subscriptions: Record<string, number>; // symbol -> reference count
  
  // Actions
  subscribe: (symbol: string) => () => void;
  updateQuote: (symbol: string, quote: MarketQuote) => void;
}

export const useMarketDataStore = create<MarketDataState>((set, get) => ({
  quotes: {},
  subscriptions: {},

  updateQuote: (symbol, quote) => {
    set((state) => ({
      quotes: {
        ...state.quotes,
        [symbol]: quote,
      },
    }));
  },

  subscribe: (symbol: string) => {
    const cleanSymbol = symbol.toUpperCase().trim();
    let unsubscribeService: (() => void) | null = null;
    
    // Increment subscription count and subscribe if it is the first subscriber
    set((state) => {
      const count = state.subscriptions[cleanSymbol] || 0;
      const nextCount = count + 1;
      
      if (nextCount === 1) {
        const callback = (quote: MarketQuote) => {
          get().updateQuote(cleanSymbol, quote);
        };
        
        // Subscribe via MarketDataService
        if (typeof MarketDataService.subscribe === 'function') {
          unsubscribeService = MarketDataService.subscribe(cleanSymbol, callback);
        }
      }

      return {
        subscriptions: {
          ...state.subscriptions,
          [cleanSymbol]: nextCount,
        },
      };
    });

    // Return cleanup function
    return () => {
      set((state) => {
        const count = state.subscriptions[cleanSymbol] || 1;
        const newSubscriptions = { ...state.subscriptions };
        
        if (count <= 1) {
          delete newSubscriptions[cleanSymbol];
          // Call the service level unsubscribe if available
          if (unsubscribeService) {
            unsubscribeService();
          }
        } else {
          newSubscriptions[cleanSymbol] = count - 1;
        }

        return { subscriptions: newSubscriptions };
      });
    };
  },
}));
