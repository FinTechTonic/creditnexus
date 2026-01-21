/**
 * WebSocket hook for /ws/trading/{user_id}.
 * Connects when userId is set; requires JWT in ?token=.
 * Calls onMessage for app-level messages (skips ping/pong/connected).
 */

import { useEffect, useRef } from 'react';
import { getWsBase } from '@/utils/apiBase';

const TOKEN_KEY = 'creditnexus_access_token';

export function useTradingWebSocket(
  userId: number | null,
  onMessage?: (data: Record<string, unknown>) => void
): void {
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (!userId) return;
    const token = typeof localStorage !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;
    if (!token) return;

    const base = getWsBase();
    const path = `/ws/trading/${userId}?token=${encodeURIComponent(token)}`;
    const url = base + path;
    let ws: WebSocket | null = null;

    try {
      ws = new WebSocket(url);
    } catch (e) {
      return;
    }

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data || '{}') as Record<string, unknown>;
        const t = data?.type;
        if (t === 'ping' || t === 'pong' || t === 'connected') return;
        onMessageRef.current?.(data);
      } catch {
        // ignore parse errors
      }
    };

    return () => {
      try {
        ws?.close();
      } catch {
        // ignore
      }
    };
  }, [userId]);
}
