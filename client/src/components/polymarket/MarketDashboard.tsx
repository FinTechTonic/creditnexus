/**
 * Polymarket-style prediction markets dashboard.
 * Lists SFP-backed markets, supports create and resolve.
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { fetchWithAuth } from '@/context/AuthContext';
import { BarChart3, Plus, CheckCircle2, Loader2 } from 'lucide-react';
import { MarketCreationModal } from './MarketCreationModal';

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
}

export function MarketDashboard() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [resolveMarketId, setResolveMarketId] = useState<string | null>(null);
  const [resolveOutcome, setResolveOutcome] = useState('yes');
  const [resolveOracle, setResolveOracle] = useState(false);
  const [resolveSubmitting, setResolveSubmitting] = useState(false);
  const [resolveError, setResolveError] = useState<string | null>(null);

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
                    <CardTitle className="text-base">{m.question}</CardTitle>
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
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setResolveMarketId(m.market_id);
                        setResolveOutcome('yes');
                        setResolveOracle(false);
                        setResolveError(null);
                      }}
                    >
                      Resolve
                    </Button>
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

      <MarketCreationModal
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={load}
      />

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
            <div>
              <Label>Outcome</Label>
              <div className="flex gap-2 mt-1">
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
