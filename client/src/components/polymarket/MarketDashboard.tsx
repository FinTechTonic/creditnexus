/**
 * Polymarket-style prediction markets dashboard.
 * Internal SFP marketplace: on-chain notarized, order book, place/cancel orders.
 * Optional Browse external Polymarket (read-only).
 * FDC3: broadcasts finos.creditnexus.predictionMarket when a market is selected;
 * listens for finos.creditnexus.predictionMarket to focus that market.
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Label } from '@/components/ui/label';
import { fetchWithAuth } from '@/context/AuthContext';
import { useFDC3 } from '@/context/FDC3Context';
import { createPredictionMarketContext } from '@/context/FDC3Context';
import { BarChart3, Plus, CheckCircle2, Loader2, Link2, X, ShieldAlert, ArrowRight } from 'lucide-react';
import { getBlockExplorerTxUrl } from '@/utils/blockExplorer';
import { MarketCreationModal } from './MarketCreationModal';
import { SurveillanceAlertsPanel } from './SurveillanceAlertsPanel';
import { CrossChainTimeline } from './CrossChainTimeline';

interface Market {
  market_id: string;
  deal_id: number;
  question: string;
  outcome_type: string;
  resolution_condition: Record<string, unknown>;
  resolved_at: string | null;
  resolution_outcome: string | null;
  oracle_triggered: boolean;
  created_at: string | null;
  sfp_id: string | null;
  merkle_root: string | null;
  transaction_hash?: string | null;
  block_number?: number | null;
}

interface OrderBook {
  bids: [number, number][];
  asks: [number, number][];
}

interface MarketOrderRow {
  order_id: number;
  market_id: string;
  side: string;
  price: number;
  size: number;
  status: string;
  created_at: string | null;
  filled_at: string | null;
}

export function MarketDashboard() {
  const { context, broadcast } = useFDC3();
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [resolveMarketId, setResolveMarketId] = useState<string | null>(null);
  const [resolveOutcome, setResolveOutcome] = useState('yes');
  const [resolveOracle, setResolveOracle] = useState(false);
  const [resolveSubmitting, setResolveSubmitting] = useState(false);
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [resolveSuggesting, setResolveSuggesting] = useState(false);
  const [resolveSuggestMsg, setResolveSuggestMsg] = useState<string | null>(null);

  const [selectedMarketId, setSelectedMarketId] = useState<string | null>(null);
  const [book, setBook] = useState<OrderBook | null>(null);
  const [bookLoading, setBookLoading] = useState(false);
  const [myOrders, setMyOrders] = useState<MarketOrderRow[]>([]);
  const [myOrdersLoading, setMyOrdersLoading] = useState(false);
  const [orderSide, setOrderSide] = useState<'yes' | 'no'>('yes');
  const [orderPrice, setOrderPrice] = useState('0.5');
  const [orderSize, setOrderSize] = useState('10');
  const [placeSubmitting, setPlaceSubmitting] = useState(false);
  const [placeError, setPlaceError] = useState<string | null>(null);
  const [browseEvents, setBrowseEvents] = useState<Record<string, unknown>[]>([]);
  const [browseMarkets, setBrowseMarkets] = useState<Record<string, unknown>[]>([]);
  const [browseLoading, setBrowseLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchWithAuth('/api/polymarket/markets?limit=100')
      .then((r) => {
        if (!r.ok) throw new Error(r.status === 400 ? 'Polymarket is disabled. Enable POLYMARKET_ENABLED.' : 'Failed to load markets');
        return r.json();
      })
      .then((data) => setMarkets(Array.isArray(data) ? data : []))
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const ctx = context as { type?: string; market_id?: string } | null;
    if (ctx?.type === 'finos.creditnexus.predictionMarket' && ctx.market_id && ctx.market_id !== selectedMarketId) {
      setSelectedMarketId(ctx.market_id);
    }
  }, [context]);

  useEffect(() => {
    if (!selectedMarketId) return;
    const m = markets.find((x) => x.market_id === selectedMarketId);
    if (!m) return;
    try {
      broadcast(createPredictionMarketContext(selectedMarketId, {
        question: m.question,
        outcome_type: m.outcome_type,
        deal_id: m.deal_id,
        sfp_id: m.sfp_id,
        resolved_at: m.resolved_at,
        resolution_outcome: m.resolution_outcome,
      }));
    } catch {
      // ignore FDC3 broadcast errors
    }
  }, [selectedMarketId, markets, broadcast]);

  useEffect(() => {
    if (!selectedMarketId) {
      setBook(null);
      setMyOrders([]);
      return;
    }
    setBookLoading(true);
    setMyOrdersLoading(true);
    Promise.all([
      fetchWithAuth(`/api/polymarket/markets/${encodeURIComponent(selectedMarketId)}/book`).then((r) => (r.ok ? r.json() : { bids: [], asks: [] })),
      fetchWithAuth(`/api/polymarket/markets/${encodeURIComponent(selectedMarketId)}/orders?user=me`).then((r) => (r.ok ? r.json() : [])),
    ])
      .then(([b, o]) => {
        setBook(b);
        setMyOrders(Array.isArray(o) ? o : []);
      })
      .catch(() => { setBook({ bids: [], asks: [] }); setMyOrders([]); })
      .finally(() => { setBookLoading(false); setMyOrdersLoading(false); });
  }, [selectedMarketId]);

  const refreshBookAndOrders = useCallback(() => {
    if (!selectedMarketId) return;
    fetchWithAuth(`/api/polymarket/markets/${encodeURIComponent(selectedMarketId)}/book`).then((r) => (r.ok ? r.json() : { bids: [], asks: [] })).then(setBook).catch(() => setBook({ bids: [], asks: [] }));
    fetchWithAuth(`/api/polymarket/markets/${encodeURIComponent(selectedMarketId)}/orders?user=me`).then((r) => (r.ok ? r.json() : [])).then((o) => setMyOrders(Array.isArray(o) ? o : [])).catch(() => setMyOrders([]));
  }, [selectedMarketId]);

  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMarketId) return;
    setPlaceError(null);
    setPlaceSubmitting(true);
    const price = parseFloat(orderPrice);
    const size = parseFloat(orderSize);
    if (Number.isNaN(price) || Number.isNaN(size) || price < 0 || price > 1 || size <= 0) {
      setPlaceError('Invalid price (0–1) or size (>0)');
      setPlaceSubmitting(false);
      return;
    }
    try {
      const res = await fetchWithAuth(`/api/polymarket/markets/${encodeURIComponent(selectedMarketId)}/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ side: orderSide, price, size }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.message || 'Failed to place order');
      refreshBookAndOrders();
      setOrderPrice('0.5');
      setOrderSize('10');
    } catch (e) {
      setPlaceError(e instanceof Error ? e.message : 'Failed to place order');
    } finally {
      setPlaceSubmitting(false);
    }
  };

  const handleCancelOrder = async (orderId: number) => {
    try {
      const res = await fetchWithAuth(`/api/polymarket/markets/orders/${orderId}`, { method: 'DELETE' });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || d.message || 'Failed to cancel');
      }
      refreshBookAndOrders();
    } catch {
      // could add toast
    }
  };

  const handleResolve = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolveMarketId) return;
    setResolveError(null);
    setResolveSubmitting(true);
    try {
      const res = await fetchWithAuth(`/api/polymarket/markets/${encodeURIComponent(resolveMarketId)}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolution_outcome: resolveOutcome, oracle_triggered: resolveOracle }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.message || 'Failed to resolve');
      setResolveMarketId(null);
      load();
    } catch (e) {
      setResolveError(e instanceof Error ? e.message : 'Failed to resolve');
    } finally {
      setResolveSubmitting(false);
    }
  };

  const handleSuggestResolution = async () => {
    if (!resolveMarketId) return;
    setResolveSuggestMsg(null);
    setResolveError(null);
    setResolveSuggesting(true);
    try {
      const res = await fetchWithAuth(`/api/polymarket/markets/${encodeURIComponent(resolveMarketId)}/suggest-resolution`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.message || 'Suggest failed');
      const out = data.suggested_outcome;
      if (out === 'yes' || out === 'no') {
        setResolveOutcome(out);
        setResolveOracle(true);
        setResolveSuggestMsg(`Oracle suggests: ${out}`);
      } else {
        setResolveSuggestMsg(data.reason || 'No suggestion');
      }
    } catch (e) {
      setResolveSuggestMsg(e instanceof Error ? e.message : 'Suggest failed');
    } finally {
      setResolveSuggesting(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <BarChart3 className="h-6 w-6" />
            Polymarket Dashboard
          </h2>
          <p className="text-muted-foreground">
            SFP-backed prediction markets. Create markets for deals and resolve when conditions are met.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create market
        </Button>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <Card>
          <CardContent className="py-12 flex items-center justify-center gap-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Loading markets…</span>
          </CardContent>
        </Card>
      ) : markets.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No markets yet</CardTitle>
            <CardDescription>
              Create a prediction market for a deal to get started. Ensure POLYMARKET_ENABLED is true and the deal has documents.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create market
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {markets.map((m) => (
            <Card key={m.market_id}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <CardTitle className="text-base">{m.question}</CardTitle>
                      {(m.transaction_hash || m.block_number != null) && (
                        m.transaction_hash ? (
                          <a
                            href={getBlockExplorerTxUrl(m.transaction_hash)}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex"
                          >
                            <Badge variant="outline" className="text-xs hover:bg-muted">On-chain · View tx</Badge>
                          </a>
                        ) : (
                          <Badge variant="outline" className="text-xs">On-chain</Badge>
                        )
                      )}
                    </div>
                    <CardDescription>
                      Deal #{m.deal_id} · {m.outcome_type} · {m.sfp_id || '—'}
                    </CardDescription>
                  </div>
                  {m.resolved_at ? (
                    <Badge variant="secondary" className="shrink-0">
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                      {m.resolution_outcome ?? 'Resolved'}
                    </Badge>
                  ) : (
                    <div className="flex gap-2 shrink-0">
                      <Button
                        size="sm"
                        variant="default"
                        onClick={() => {
                          setSelectedMarketId(m.market_id);
                          setPlaceError(null);
                        }}
                      >
                        Trade
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setResolveMarketId(m.market_id);
                          setResolveOutcome('yes');
                          setResolveOracle(false);
                          setResolveError(null);
                          setResolveSuggestMsg(null);
                        }}
                      >
                        Resolve
                      </Button>
                    </div>
                  )}
                </div>
              </CardHeader>
              {m.merkle_root && (
                <CardContent className="pt-0">
                  <p className="text-xs text-muted-foreground font-mono truncate">Merkle: {m.merkle_root}</p>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}

      <Accordion type="single" collapsible onValueChange={(v) => { if (v === 'browse') { setBrowseLoading(true); Promise.all([ fetchWithAuth('/api/polymarket/external/events?limit=10').then((r) => (r.ok ? r.json() : [])), fetchWithAuth('/api/polymarket/external/markets?limit=10').then((r) => (r.ok ? r.json() : [])), ]).then(([e, m]) => { setBrowseEvents(Array.isArray(e) ? e : []); setBrowseMarkets(Array.isArray(m) ? m : []); }).catch(() => { setBrowseEvents([]); setBrowseMarkets([]); }).finally(() => setBrowseLoading(false)); } }}>
        <AccordionItem value="surveillance">
          <AccordionTrigger className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4" />
            Surveillance
          </AccordionTrigger>
          <AccordionContent>
            <SurveillanceAlertsPanel />
          </AccordionContent>
        </AccordionItem>
        <AccordionItem value="crosschain">
          <AccordionTrigger className="flex items-center gap-2">
            <ArrowRight className="h-4 w-4" />
            Cross-chain
          </AccordionTrigger>
          <AccordionContent>
            <CrossChainTimeline />
          </AccordionContent>
        </AccordionItem>
        <AccordionItem value="browse">
          <AccordionTrigger className="flex items-center gap-2">
            <Link2 className="h-4 w-4" />
            Browse external Polymarket
          </AccordionTrigger>
          <AccordionContent>
            <p className="text-muted-foreground text-sm mb-2">Read-only view of external Polymarket for discovery. SFPs are listed only in CreditNexus.</p>
            {browseLoading ? (
              <div className="flex items-center gap-2 py-4"><Loader2 className="h-4 w-4 animate-spin" /> Loading…</div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <div className="text-xs font-medium text-muted-foreground mb-1">Events</div>
                  <div className="rounded border p-2 space-y-1 max-h-48 overflow-y-auto text-sm">
                    {browseEvents.length === 0 ? <span className="text-muted-foreground">—</span> : browseEvents.slice(0, 8).map((ev: Record<string, unknown>, i) => (
                      <div key={i} className="truncate">{(ev.title ?? ev.question ?? ev.id ?? '—') as string}</div>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-medium text-muted-foreground mb-1">Markets</div>
                  <div className="rounded border p-2 space-y-1 max-h-48 overflow-y-auto text-sm">
                    {browseMarkets.length === 0 ? <span className="text-muted-foreground">—</span> : browseMarkets.slice(0, 8).map((mk: Record<string, unknown>, i) => (
                      <div key={i} className="truncate">{(mk.question ?? mk.condition_id ?? mk.id ?? '—') as string}</div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      <MarketCreationModal
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={load}
      />

      <Dialog open={!!selectedMarketId} onOpenChange={(o) => !o && setSelectedMarketId(null)}>
        <DialogContent onClose={() => setSelectedMarketId(null)} className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {(() => {
                const m = markets.find((x) => x.market_id === selectedMarketId);
                return m?.question ?? selectedMarketId ?? '';
              })()}
              {(() => {
                const m = markets.find((x) => x.market_id === selectedMarketId);
                if (m && (m.transaction_hash || m.block_number != null)) {
                  return m?.transaction_hash ? (
                    <a
                      href={getBlockExplorerTxUrl(m.transaction_hash)}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex"
                    >
                      <Badge variant="outline" className="text-xs hover:bg-muted">On-chain · View tx</Badge>
                    </a>
                  ) : (
                    <Badge variant="outline" className="text-xs">On-chain</Badge>
                  );
                }
                return null;
              })()}
            </DialogTitle>
            <DialogDescription>Internal order book. Place and cancel orders.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label className="text-xs text-muted-foreground">Order book</Label>
              {bookLoading ? (
                <div className="flex items-center gap-2 py-4"><Loader2 className="h-4 w-4 animate-spin" /> Loading…</div>
              ) : book ? (
                <div className="mt-1 rounded border p-2 font-mono text-sm space-y-1 max-h-40 overflow-y-auto">
                  <div className="text-muted-foreground">Yes (bids)</div>
                  {(book.bids || []).slice(0, 5).map(([p, s], i) => (
                    <div key={`b-${i}`}>{Number(p).toFixed(2)} × {Number(s).toFixed(2)}</div>
                  ))}
                  {(book.bids || []).length === 0 && <div className="text-muted-foreground">—</div>}
                  <div className="text-muted-foreground pt-2">No (asks)</div>
                  {(book.asks || []).slice(0, 5).map(([p, s], i) => (
                    <div key={`a-${i}`}>{Number(p).toFixed(2)} × {Number(s).toFixed(2)}</div>
                  ))}
                  {(book.asks || []).length === 0 && <div className="text-muted-foreground">—</div>}
                </div>
              ) : null}
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Place order</Label>
              <form onSubmit={handlePlaceOrder} className="mt-1 space-y-2">
                {placeError && <p className="text-sm text-destructive" role="alert">{placeError}</p>}
                <div className="flex gap-2">
                  {(['yes', 'no'] as const).map((s) => (
                    <Button key={s} type="button" variant={orderSide === s ? 'default' : 'outline'} size="sm" onClick={() => setOrderSide(s)}>{s === 'yes' ? 'Yes' : 'No'}</Button>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input type="number" step="0.01" min={0} max={1} placeholder="Price 0–1" value={orderPrice} onChange={(e) => setOrderPrice(e.target.value)} />
                  <Input type="number" step="0.01" min={0.01} placeholder="Size" value={orderSize} onChange={(e) => setOrderSize(e.target.value)} />
                </div>
                <Button type="submit" size="sm" disabled={placeSubmitting}>{placeSubmitting ? 'Placing…' : 'Place order'}</Button>
              </form>
            </div>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">My open orders</Label>
            {myOrdersLoading ? (
              <div className="flex items-center gap-2 py-2"><Loader2 className="h-4 w-4 animate-spin" /> Loading…</div>
            ) : (
              <div className="mt-1 rounded border p-2 space-y-1 max-h-32 overflow-y-auto">
                {myOrders.filter((o) => o.status === 'open').length === 0 ? (
                  <div className="text-muted-foreground text-sm">No open orders</div>
                ) : (
                  myOrders.filter((o) => o.status === 'open').map((o) => (
                    <div key={o.order_id} className="flex items-center justify-between text-sm">
                      <span>{o.side} @ {Number(o.price).toFixed(2)} × {Number(o.size).toFixed(2)}</span>
                      <Button type="button" size="sm" variant="ghost" className="h-7 px-1" onClick={() => handleCancelOrder(o.order_id)}><X className="h-3 w-3" /></Button>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!resolveMarketId} onOpenChange={(o) => !o && setResolveMarketId(null)}>
        <DialogContent onClose={() => setResolveMarketId(null)} className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Resolve market</DialogTitle>
            <DialogDescription>
              Set the resolution outcome for {resolveMarketId || ''}.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleResolve} className="space-y-4">
            {resolveError && <p className="text-sm text-destructive" role="alert">{resolveError}</p>}
            {resolveSuggestMsg && <p className="text-sm text-muted-foreground" role="status">{resolveSuggestMsg}</p>}
            <div>
              <Label>Outcome</Label>
              <div className="flex gap-2 mt-1 flex-wrap items-center">
                {(['yes', 'no'] as const).map((o) => (
                  <Button
                    key={o}
                    type="button"
                    variant={resolveOutcome === o ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setResolveOutcome(o)}
                  >
                    {o}
                  </Button>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleSuggestResolution}
                  disabled={resolveSuggesting}
                >
                  {resolveSuggesting ? '…' : 'Suggest from oracle'}
                </Button>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="oracle"
                checked={resolveOracle}
                onChange={(e) => setResolveOracle(e.target.checked)}
              />
              <Label htmlFor="oracle">Oracle / automation triggered</Label>
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setResolveMarketId(null)}>
                Cancel
              </Button>
              <Button type="submit" disabled={resolveSubmitting}>
                {resolveSubmitting ? 'Resolving…' : 'Resolve'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
