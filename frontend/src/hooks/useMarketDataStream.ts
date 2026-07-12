/**
 * useMarketDataStream.ts
 *
 * Singleton WebSocket manager for the Scanner market feed (/api/scanner/ws).
 *
 * ARCHITECTURE: Only ONE WebSocket connection is ever opened to /api/scanner/ws
 * regardless of how many components consume this hook. A reference counter tracks
 * active consumers; the socket is created on the first mount and torn down when the
 * last consumer unmounts.
 *
 * All message callbacks from individual pages (MomentAlert, Week52Breakout, etc.)
 * are registered via the `onMessage` option instead of opening a second raw WebSocket.
 *
 * This fixes the "3 concurrent connections saturate the backend event loop" bug that
 * caused readyState:3 (CLOSED) errors on the frontend.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { API_URL } from '../services/api';

// ── Public types ──────────────────────────────────────────────────────────────

export interface MarketIndex {
  name: string;
  value: number;
  change: number;
  percent: number;
  loading?: boolean;
}

export interface WsMetrics {
  connectionTime: string | null;
  disconnectReason: string;
  reconnectCount: number;
  averageSessionDuration: number;
  messageThroughput: number;
}

export interface UseMarketDataStreamOptions {
  /** Set false to prevent connecting (e.g. market closed). Default: true */
  enabled?: boolean;
  /** Optional callback to receive every raw parsed WS message */
  onMessage?: (message: any) => void;
}

// ── Singleton state (module-level, shared across all hook instances) ──────────

let _socket: WebSocket | null = null;
let _refCount = 0;

let _isConnected = false;
let _indices: MarketIndex[] = [];
let _metrics: WsMetrics = {
  connectionTime: null,
  disconnectReason: '',
  reconnectCount: 0,
  averageSessionDuration: 0,
  messageThroughput: 0,
};

/** State-change listeners (trigger React re-renders) */
type StateListener = () => void;
const _stateListeners: Set<StateListener> = new Set();

/** Raw message subscribers — e.g. MomentAlert, Week52Breakout */
type MessageListener = (msg: any) => void;
const _messageListeners: Set<MessageListener> = new Set();

let _retryCount = 0;
let _pingIntervalId: ReturnType<typeof setInterval> | null = null;
let _reconnectTimeoutId: ReturnType<typeof setTimeout> | null = null;
let _sessionStart: number | null = null;
let _messageCount = 0;
let _sessionDurations: number[] = [];

const MAX_RETRIES = 10;
const BASE_DELAY_MS = 1000;

function _getWsUrl(): string {
  const baseUrl = API_URL || window.location.origin;
  const proto = baseUrl.startsWith('https') ? 'wss' : 'ws';
  const host = baseUrl.replace(/^https?:\/\//, '');
  return `${proto}://${host}/api/scanner/ws`;
}

function _notifyState() {
  _stateListeners.forEach(fn => fn());
}

function _scheduleReconnect() {
  if (_reconnectTimeoutId) clearTimeout(_reconnectTimeoutId);
  if (_retryCount >= MAX_RETRIES) {
    console.warn('[MarketWS] Max retries reached. Giving up.');
    return;
  }

  const delay = Math.min(30_000, BASE_DELAY_MS * Math.pow(2, _retryCount));
  _retryCount++;
  _metrics = { ..._metrics, reconnectCount: _retryCount };
  _notifyState();

  console.log(`[MarketWS] Reconnecting in ${delay}ms (attempt ${_retryCount}/${MAX_RETRIES})`);
  _reconnectTimeoutId = setTimeout(_connect, delay);
}

function _connect() {
  if (_refCount === 0) return; // No consumers — skip
  if (_socket &&
    (_socket.readyState === WebSocket.CONNECTING ||
      _socket.readyState === WebSocket.OPEN)) return;

  const url = _getWsUrl();
  console.log('[MarketWS] Opening singleton connection:', url);

  try {
    const ws = new WebSocket(url);
    _socket = ws;

    ws.onopen = () => {
      console.log('[MarketWS] Connected');
      _isConnected = true;
      _retryCount = 0;
      _sessionStart = Date.now();
      _messageCount = 0;
      _metrics = { ..._metrics, connectionTime: new Date().toISOString() };
      _notifyState();

      if (_pingIntervalId) clearInterval(_pingIntervalId);
      _pingIntervalId = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30_000);
    };

    ws.onmessage = (event) => {
      _messageCount++;
      if (_sessionStart) {
        const elapsedSec = (Date.now() - _sessionStart) / 1000;
        const throughput = elapsedSec > 0 ? _messageCount / elapsedSec : 0;
        _metrics = { ..._metrics, messageThroughput: parseFloat(throughput.toFixed(2)) };
      }

      try {
        const message = JSON.parse(event.data);

        // Update shared index state
        if (message.indices && Array.isArray(message.indices)) {
          _indices = message.indices.map((newIdx: MarketIndex) => {
            const existing = _indices.find(p => p.name === newIdx.name);
            if (!newIdx.value || newIdx.value === 0) return existing || newIdx;
            return newIdx;
          });
          _notifyState();
        }

        // Broadcast raw message to all page-level subscribers
        _messageListeners.forEach(cb => {
          try { cb(message); } catch (_) { /* ignore per-subscriber errors */ }
        });
      } catch (e) {
        console.warn('[MarketWS] Parse error:', e);
      }
    };

    ws.onclose = (event) => {
      console.log('[MarketWS] Closed', event.code, event.reason);
      _isConnected = false;

      if (_pingIntervalId) { clearInterval(_pingIntervalId); _pingIntervalId = null; }

      if (_sessionStart) {
        const dur = Date.now() - _sessionStart;
        _sessionDurations.push(dur);
        const avg = _sessionDurations.reduce((a, b) => a + b, 0) / _sessionDurations.length;
        _metrics = {
          ..._metrics,
          disconnectReason: `Code:${event.code}${event.reason ? ' - ' + event.reason : ''}`,
          averageSessionDuration: parseFloat((avg / 1000).toFixed(2)),
        };
      }
      _socket = null;
      _notifyState();

      if (_refCount > 0) _scheduleReconnect();
    };

    ws.onerror = () => {
      console.warn('[MarketWS] Error — closing to trigger reconnect');
      ws.close();
    };
  } catch (e) {
    console.error('[MarketWS] Failed to create WebSocket:', e);
    _scheduleReconnect();
  }
}

function _teardown() {
  if (_reconnectTimeoutId) { clearTimeout(_reconnectTimeoutId); _reconnectTimeoutId = null; }
  if (_pingIntervalId)     { clearInterval(_pingIntervalId);   _pingIntervalId = null; }
  if (_socket) {
    _socket.onclose = null; // Prevent retry loop on intentional close
    _socket.close();
    _socket = null;
  }
  _isConnected = false;
  _retryCount = 0;
  _notifyState();
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export const useMarketDataStream = (options: UseMarketDataStreamOptions = {}) => {
  const { enabled = true, onMessage } = options;

  // Force re-render when singleton state changes
  const [, setTick] = useState(0);
  const forceUpdate = useCallback(() => setTick(t => t + 1), []);

  // Stable ref to the latest onMessage callback — avoids stale closure issues
  const onMessageRef = useRef<MessageListener | undefined>(onMessage);
  useEffect(() => { onMessageRef.current = onMessage; }, [onMessage]);

  // Stable wrapper that always calls the latest callback
  const stableMessageCb = useCallback((msg: any) => {
    onMessageRef.current?.(msg);
  }, []);

  useEffect(() => {
    if (!enabled) return;

    _refCount++;
    _stateListeners.add(forceUpdate);
    if (onMessage) _messageListeners.add(stableMessageCb);

    _connect();

    return () => {
      _stateListeners.delete(forceUpdate);
      _messageListeners.delete(stableMessageCb);
      _refCount--;

      if (_refCount <= 0) {
        _refCount = 0;
        _teardown();
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  return {
    isConnected: _isConnected,
    indices: _indices,
    metrics: _metrics,
  };
};
