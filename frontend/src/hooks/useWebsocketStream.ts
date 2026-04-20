import { useEffect, useRef, useState, useCallback } from 'react';

type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface MarketTick {
  symbol: string;
  data: {
    last_price: number;
    open: number;
    high: number;
    low: number;
    close: number;
    change_percent: number;
    volume: number;
    timestamp: string;
  };
}

export function useWebsocketStream(symbols: string[] = []) {
  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const [ticks, setTicks] = useState<Record<string, MarketTick['data']>>({});
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus('connecting');
    const wsUrl = process.env.NODE_ENV === 'production' 
      ? `wss://${window.location.host}/api/ws/live`
      : 'ws://localhost:8000/api/ws/live';

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setStatus('connected');
      if (symbols.length > 0) {
        ws.send(JSON.stringify({ action: 'subscribe', symbols }));
      }
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.event === 'market_tick') {
          setTicks(prev => ({
            ...prev,
            [payload.symbol]: payload.data
          }));
        }
      } catch (err) {
        console.error('WebSocket message parsing error:', err);
      }
    };

    ws.onclose = () => {
      setStatus('disconnected');
      // Attempt reconnect after 3 seconds
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket Error:', error);
      setStatus('error');
    };

    wsRef.current = ws;
  }, [symbols]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  // Method to dynamically add subscriptions
  const subscribe = useCallback((newSymbols: string[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'subscribe', symbols: newSymbols }));
    }
  }, []);

  return {
    status,
    ticks,
    subscribe
  };
}
