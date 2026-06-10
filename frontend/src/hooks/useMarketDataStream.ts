import { useState, useEffect, useRef, useCallback } from 'react';
import { API_URL } from '../services/api';

interface MarketIndex {
    name: string;
    value: number;
    change: number;
    percent: number;
    loading?: boolean;
}

interface UseMarketDataStreamOptions {
    url?: string;
    enabled?: boolean;
    pollInterval?: number; // fallback polling hint (not implemented here, managed by consumer)
}

export const useMarketDataStream = (options: UseMarketDataStreamOptions = {}) => {
    // Derive WS URL from API_URL (handle both http/https and relative paths)
    const getWsUrl = () => {
        const baseUrl = API_URL || window.location.origin;
        const proto = baseUrl.startsWith('https') ? 'wss' : 'ws';
        const host = baseUrl.replace(/^https?:\/\//, '');
        return `${proto}://${host}/api/scanner/ws`;
    };

    const {
        url = getWsUrl(),
        enabled = true
    } = options;

    const [isConnected, setIsConnected] = useState(false);
    const [indices, setIndices] = useState<MarketIndex[]>([]);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    // Monitoring refs
    const sessionStartRef = useRef<number | null>(null);
    const messageCountRef = useRef(0);
    const sessionDurationsRef = useRef<number[]>([]);

    const [metrics, setMetrics] = useState({
        connectionTime: null as string | null,
        disconnectReason: '',
        reconnectCount: 0,
        averageSessionDuration: 0,
        messageThroughput: 0
    });

    // Exponential backoff state
    const retryCountRef = useRef(0);
    const maxRetries = 10;
    const baseDelay = 1000;

    const connect = useCallback(() => {
        if (!enabled) return;

        try {
            console.log('Connecting to Market WS:', url);
            const ws = new WebSocket(url);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('Market WS Connected');
                setIsConnected(true);
                retryCountRef.current = 0; // Reset backoff
                
                const now = new Date();
                sessionStartRef.current = now.getTime();
                messageCountRef.current = 0;
                
                setMetrics(prev => ({
                    ...prev,
                    connectionTime: now.toISOString()
                }));
            };

            ws.onmessage = (event) => {
                messageCountRef.current++;
                if (sessionStartRef.current) {
                    const elapsedSec = (Date.now() - sessionStartRef.current) / 1000;
                    const throughput = elapsedSec > 0 ? messageCountRef.current / elapsedSec : 0;
                    setMetrics(prev => ({
                        ...prev,
                        messageThroughput: parseFloat(throughput.toFixed(2))
                    }));
                }

                try {
                    const message = JSON.parse(event.data);
                    if (message.indices && Array.isArray(message.indices)) {
                        setIndices(prev => {
                            // Merge updates carefully to preserve data if new payload is empty/invalid
                            return message.indices.map((newIdx: MarketIndex) => {
                                const existing = prev.find(p => p.name === newIdx.name);
                                if (!newIdx.value || newIdx.value === 0) {
                                    return existing || newIdx;
                                }
                                return newIdx;
                            });
                        });
                    }
                } catch (e) {
                    console.warn('Market WS Parse Error:', e);
                }
            };

            ws.onclose = (event) => {
                console.log('Market WS Closed');
                setIsConnected(false);
                wsRef.current = null;

                let reason = `Code: ${event.code}`;
                if (event.reason) reason += ` - ${event.reason}`;

                if (sessionStartRef.current) {
                    const duration = Date.now() - sessionStartRef.current;
                    sessionDurationsRef.current.push(duration);
                }

                const durations = sessionDurationsRef.current;
                const avgDur = durations.length > 0
                    ? durations.reduce((a, b) => a + b, 0) / durations.length
                    : 0;

                setMetrics(prev => ({
                    ...prev,
                    disconnectReason: reason,
                    averageSessionDuration: parseFloat((avgDur / 1000).toFixed(2))
                }));

                scheduleReconnect();
            };

            ws.onerror = (err) => {
                console.warn('Market WS Error:', err);
                ws.close(); // Ensure cleanup triggers onclose
            };

        } catch (e) {
            console.error('Market WS Connection Failed:', e);
            scheduleReconnect();
        }
    }, [url, enabled]);

    const scheduleReconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);

        if (retryCountRef.current < maxRetries) {
            const delay = Math.min(30000, baseDelay * Math.pow(2, retryCountRef.current));
            console.log(`Scheduling reconnect in ${delay}ms (attempt ${retryCountRef.current + 1})`);
            reconnectTimeoutRef.current = setTimeout(() => {
                retryCountRef.current++;
                setMetrics(prev => ({
                    ...prev,
                    reconnectCount: retryCountRef.current
                }));
                connect();
            }, delay);
        }
    }, [connect]);

    useEffect(() => {
        connect();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
        };
    }, [connect]);

    return {
        isConnected,
        indices,
        metrics
    };
};
