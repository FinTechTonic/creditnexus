/**
 * When the app is loaded via file:// (Electron loadFile), relative /api URLs
 * resolve to file:// paths and fail. Use resolveApiUrl() so /api/... becomes
 * http://localhost:8000/api/... in that case.
 */
export function getApiBase(): string {
  return typeof window !== 'undefined' && window.location.protocol === 'file:'
    ? 'http://localhost:8000'
    : '';
}

export function resolveApiUrl(url: string): string {
  return url.startsWith('http') ? url : getApiBase() + url;
}

/** Base URL for WebSocket connections (ws/wss). Used for /ws/trading, etc. */
export function getWsBase(): string {
  if (typeof window === 'undefined') return 'ws://localhost:8000';
  if (window.location.protocol === 'file:') return 'ws://localhost:8000';
  const host = window.location.host;
  return window.location.protocol === 'https:' ? `wss://${host}` : `ws://${host}`;
}
