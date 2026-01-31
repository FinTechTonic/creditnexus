/**
 * Polymarket external CLOB trading: link status, browse markets, place order.
 * - Link CTA if not linked (BYOK Polymarket in User Settings).
 * - Browse external events/markets and order book.
 * - Place order via POST /api/polymarket/orders (client must provide signed order).
 * - Optional: deploy wallet (relayer) and approve-setup for first-time users.
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { fetchWithAuth } from '@/context/AuthContext';
import { Link } from 'react-router-dom';
import { BarChart3, Link2, Loader2 } from 'lucide-react';

interface LinkStatus {
  linked: boolean;
  funder_address?: string;
  linked_at?: string;
}

interface ExternalEvent {
  id?: string;
  title?: string;
  slug?: string;
  markets?: { condition_id?: string; question?: string; tokens?: { token_id?: string }[] }[];
}

export function PolymarketTrading() {
  const [linkStatus, setLinkStatus] = useState<LinkStatus | null>(null);
  const [events, setEvents] = useState<ExternalEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadLinkStatus = useCallback(async () => {
    try {
      const r = await fetchWithAuth('/api/polymarket/link-status');
      if (r.ok) {
        const d = await r.json();
        setLinkStatus({ linked: !!d.linked, funder_address: d.funder_address, linked_at: d.linked_at });
      } else {
        setLinkStatus({ linked: false });
      }
    } catch {
      setLinkStatus({ linked: false });
    } finally {
      setLoading(false);
    }
  }, []);

  const loadExternalEvents = useCallback(async () => {
    setEventsLoading(true);
    setError(null);
    try {
      const r = await fetchWithAuth('/api/polymarket/external/events?active=true&limit=20');
      const data = r.ok ? await r.json() : [];
      setEvents(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load events');
      setEvents([]);
    } finally {
      setEventsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLinkStatus();
  }, [loadLinkStatus]);

  useEffect(() => {
    loadExternalEvents();
  }, [loadExternalEvents]);

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6 flex items-center justify-center gap-2">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Loading…</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Polymarket Trading
          </CardTitle>
          <CardDescription>
            Trade on external Polymarket CLOB. Link your Polymarket account (BYOK) in User Settings to place orders.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!linkStatus?.linked ? (
            <div className="rounded-lg border border-amber-500/50 bg-amber-500/10 p-4 flex items-center justify-between gap-4">
              <p className="text-sm">
                Link your Polymarket account (API key, secret, passphrase, and funder address) in User Settings → BYOK → Polymarket to place orders.
              </p>
              <Button asChild variant="default" size="sm">
                <Link to="/settings?tab=byok">
                  <Link2 className="h-4 w-4 mr-2" />
                  Link in Settings
                </Link>
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Badge variant="secondary">Linked</Badge>
              {linkStatus.funder_address && (
                <span className="font-mono text-xs truncate max-w-[200px]" title={linkStatus.funder_address}>
                  {linkStatus.funder_address}
                </span>
              )}
            </div>
          )}

          <div>
            <h4 className="text-sm font-medium mb-2">Browse external markets</h4>
            {eventsLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading events…
              </div>
            ) : error ? (
              <p className="text-sm text-destructive">{error}</p>
            ) : events.length === 0 ? (
              <p className="text-sm text-muted-foreground">No external events. Enable Polymarket and Gamma API to browse.</p>
            ) : (
              <ul className="space-y-2 max-h-64 overflow-y-auto">
                {events.slice(0, 20).map((ev, i) => (
                  <li key={ev.id ?? ev.slug ?? i} className="text-sm border-b border-border/50 pb-2">
                    <span className="font-medium">{ev.title ?? ev.slug ?? 'Event'}</span>
                    {ev.markets?.length ? (
                      <span className="text-muted-foreground ml-2">({ev.markets.length} market(s))</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <p className="text-xs text-muted-foreground">
            To place an order: create and sign the order in your wallet or CLOB client, then POST the signed order to <code className="bg-muted px-1 rounded">/api/polymarket/orders</code> (order_type: GTC/FOK/GTD). Builder attribution is applied server-side.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
