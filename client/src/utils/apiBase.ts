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
<<<<<<< HEAD
  
  // In development, Vite runs on port 5000 but backend is on 8000
  // Check if we're in development mode (port 5000) and use backend port 8000
  const host = window.location.host;
  if (host.includes(':5000') || host === 'localhost:5000') {
    return 'ws://localhost:8000';
  }
  
=======
  const host = window.location.host;
>>>>>>> origin/main
  return window.location.protocol === 'https:' ? `wss://${host}` : `ws://${host}`;
}
