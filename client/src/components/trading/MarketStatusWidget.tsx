/**
 * Market status widget: is_open, status_text, next_trading_day, time_until_open/close.
 * Fetches GET /api/stock-prediction/market-status
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, Clock, Calendar } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';

interface MarketStatus {
  is_open: boolean;
  status_text: string;
  next_trading_day: string;
  last_updated: string;
  time_until_open: string;
  time_until_close: string;
  current_time_et: string;
  market_name: string;
  market_type: string;
  market_symbol: string;
}

interface MarketStatusWidgetProps {
  market?: string;
}

export function MarketStatusWidget({ market = 'US_STOCKS' }: MarketStatusWidgetProps) {
  const [status, setStatus] = useState<MarketStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const url = resolveApiUrl(`/api/stock-prediction/market-status?market=${encodeURIComponent(market)}`);
        const res = await fetchWithAuth(url);
        if (!res.ok) throw new Error(await res.text().catch(() => `HTTP ${res.status}`));
        const data = await res.json();
        if (!cancelled) setStatus(data);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load market status');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [market]);

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 py-6">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-muted-foreground">Loading market status…</span>
        </CardContent>
      </Card>
    );
  }
  if (error || !status) {
    return (
      <Card>
        <CardContent className="py-6 text-destructive">{error || 'Market status unavailable'}</CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Clock className="h-4 w-4" />
          {status.market_name}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p className={status.is_open ? 'text-emerald-600 font-medium' : 'text-muted-foreground'}>
          {status.status_text}
        </p>
        <div className="flex items-center gap-2 text-muted-foreground">
          <Calendar className="h-3.5 w-3.5" />
          Next: {status.next_trading_day}
        </div>
        {!status.is_open && status.time_until_open !== 'N/A (24/7 Market)' && (
          <p className="text-muted-foreground">Opens in {status.time_until_open}</p>
        )}
        {status.is_open && status.time_until_close !== 'N/A (24/7 Market)' && (
          <p className="text-muted-foreground">Closes in {status.time_until_close}</p>
        )}
      </CardContent>
    </Card>
  );
}
