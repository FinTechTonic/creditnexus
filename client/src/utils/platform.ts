/**
 * Platform detection for payment and signup flows.
 * - Electron: desktop app (MetaMask, RevenueCat, Plaid).
 * - Mobile: Capacitor/React Native app; "App purchase" (RevenueCat) gives instant credits.
 */

declare global {
  interface Window {
    __ELECTRON__?: boolean;
    Capacitor?: { isNativePlatform?: () => boolean };
  }
}

/** True when running inside Electron (desktop app). */
export function isElectron(): boolean {
  if (typeof window === 'undefined') return false;
  if (window.__ELECTRON__ === true) return true;
  if (typeof (window as unknown as { electron?: unknown }).electron !== 'undefined') return true;
  const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
  return /electron/i.test(ua);
}

/** True when running on mobile (Capacitor, React Native, or mobile user agent). */
export function isMobile(): boolean {
  if (typeof window === 'undefined') return false;
  if (window.Capacitor?.isNativePlatform?.()) return true;
  const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
  return /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(ua);
}
