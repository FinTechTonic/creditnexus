/**
 * WebSocket hook for real-time verification updates.
 * 
 * Manages WebSocket connection for layer verification progress,
 * layer updates, and verification completion.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import type {
  LayerUpdate,
  VerificationProgress,
  VerificationComplete,
  WebSocketMessage
} from '@/types/layers';
import { useLayerStore } from '@/stores/layerStore';

interface UseVerificationWebSocketOptions {
  assetId: number;
  onLayerUpdate?: (update: LayerUpdate) => void;
  onProgress?: (progress: VerificationProgress) => void;
  onComplete?: (complete: VerificationComplete) => void;
  onError?: (error: Error) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  enabled?: boolean;
}

interface UseVerificationWebSocketReturn {
  connected: boolean;
  connectionError: Error | null;
  reconnect: () => void;
  disconnect: () => void;
  sendMessage: (message: any) => void;
}

export function useVerificationWebSocket({
  assetId,
  onLayerUpdate,
  onProgress,
  onComplete,
  onError,
  autoReconnect = true,
  reconnectInterval = 3000,
  enabled = true
}: UseVerificationWebSocketOptions): UseVerificationWebSocketReturn {
  const [connected, setConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<Error | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  
  // Use refs for callbacks to avoid dependency issues
  const callbacksRef = useRef({ onLayerUpdate, onProgress, onComplete, onError });
  const storeRef = useRef(useLayerStore.getState());
  
  // Update refs when callbacks change
  useEffect(() => {
    callbacksRef.current = { onLayerUpdate, onProgress, onComplete, onError };
    storeRef.current = useLayerStore.getState();
  }, [onLayerUpdate, onProgress, onComplete, onError]);
  
  const connect = useCallback(() => {
    if (!enabled || assetId <= 0) {
      return;
    }
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }
    
    try {
      // Determine WebSocket protocol (ws:// or wss://)
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      
      // In development, Vite runs on port 5000 but backend is on 8000
      // WebSocket connections don't go through HTTP proxy, so connect directly to backend
      const isDev = import.meta.env.DEV;
      const backendHost = isDev ? '127.0.0.1:8000' : window.location.host;
      const wsUrl = `${protocol}//${backendHost}/ws/verification/${assetId}`;
      
      // Add token if available (from localStorage or context)
      const token = localStorage.getItem('token');
      const urlWithToken = token ? `${wsUrl}?token=${token}` : wsUrl;
      
      const ws = new WebSocket(urlWithToken);
      
      ws.onopen = () => {
        setConnected(true);
        setConnectionError(null);
        reconnectAttemptsRef.current = 0;
        storeRef.current.setConnectionState(true, null);
        console.log(`WebSocket connected for asset ${assetId}`);
      };
      
      ws.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);
          const callbacks = callbacksRef.current;
          const store = storeRef.current;
          
          switch (data.type) {
            case 'layer_update':
              const layerUpdate = data as LayerUpdate;
              store.handleLayerUpdate(layerUpdate);
              callbacks.onLayerUpdate?.(layerUpdate);
              break;
              
            case 'progress':
              const progress = data as VerificationProgress;
              store.handleProgress(progress);
              callbacks.onProgress?.(progress);
              break;
              
            case 'verification_complete':
              const complete = data as VerificationComplete;
              store.handleVerificationComplete(complete);
              callbacks.onComplete?.(complete);
              break;
              
            case 'error':
              const error = new Error(data.message || 'WebSocket error');
              setConnectionError(error);
              store.setConnectionState(false, error.message);
              callbacks.onError?.(error);
              break;
              
            case 'connected':
              console.log('WebSocket connection confirmed');
              break;
              
            case 'ping':
              // Respond to ping with pong
              if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ type: 'pong' }));
              }
              break;
              
            case 'pong':
              // Keepalive response
              break;
              
            default:
              console.warn('Unknown WebSocket message type:', data.type);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
          const parseError = error instanceof Error ? error : new Error('Failed to parse message');
          onError?.(parseError);
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        const wsError = new Error('WebSocket connection error');
        setConnectionError(wsError);
        storeRef.current.setConnectionState(false, wsError.message);
        callbacksRef.current.onError?.(wsError);
      };
      
      ws.onclose = (event) => {
        setConnected(false);
        storeRef.current.setConnectionState(false, null);
        console.log(`WebSocket closed for asset ${assetId}`, event.code, event.reason);
        
        // Auto-reconnect if enabled and not a normal closure
        if (autoReconnect && event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`Attempting to reconnect (${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          const maxAttemptsError = new Error('Max reconnection attempts reached');
          setConnectionError(maxAttemptsError);
          storeRef.current.setConnectionState(false, maxAttemptsError.message);
          callbacksRef.current.onError?.(maxAttemptsError);
        }
      };
      
      wsRef.current = ws;
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Connection failed');
      setConnectionError(err);
      storeRef.current.setConnectionState(false, err.message);
      callbacksRef.current.onError?.(err);
    }
  }, [assetId, enabled, autoReconnect, reconnectInterval]);
  
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }
    
    setConnected(false);
    storeRef.current.setConnectionState(false, null);
  }, []);
  
  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(message));
      } catch (error) {
        console.error('Failed to send WebSocket message:', error);
      }
    } else {
      console.warn('WebSocket is not connected, cannot send message');
    }
  }, []);
  
  // Connect on mount and when assetId/enabled changes
  useEffect(() => {
    if (enabled && assetId > 0) {
      connect();
    }
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect, enabled, assetId]);
  
  return {
    connected,
    connectionError,
    reconnect: connect,
    disconnect,
    sendMessage
  };
}
