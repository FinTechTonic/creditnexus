/**
 * Cross-chain transactions timeline for Polymarket/SFP.
 * Fetches GET /api/cross-chain/transactions and shows dest_tx_hash block explorer links.
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { fetchWithAuth } from '@/context/AuthContext';
import { Loader2, ExternalLink, ArrowRight } from 'lucide-react';
import { getBlockExplorerTxUrl } from '@/utils/blockExplorer';

interface CrossChainTx {
  id: number;
  source_chain_id: number;
  dest_chain_id: number;
  bridge_external_id: string | null;
  status: string;
  amount: string | null;
  token_address: string | null;
  market_event_id: number | null;
  outcome_token_id: string | null;
  dest_tx_hash: string | null;
  extra_data: Record<string, unknown> | null;
  created_at: string | null;
  updated_at: string | null;
}

export function CrossChainTimeline() {
  const [items, setItems] = useState<CrossChainTx[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchWithAuth('/api/cross-chain/transactions?limit=20')
      .then((r) => {
        if (!r.ok) throw new Error('Failed to load cross-chain transactions');
        return r.json();
      })
      .then((data) => setItems(Array.isArray(data) ? data : []))
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8 flex items-center justify-center gap-2">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="text-muted-foreground">Loading cross-chain transactions…</span>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardContent className="pt-6">
          <p className="text-destructive text-sm">{error}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <ArrowRight className="h-4 w-4" />
          Cross-chain timeline
        </CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-muted-foreground text-sm">No cross-chain transactions yet.</p>
        ) : (
          <ul className="space-y-3">
            {items.map((tx) => (
              <li
                key={tx.id}
                className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm border-b border-slate-700/50 pb-2 last:border-0 last:pb-0"
              >
                <span className="text-muted-foreground shrink-0">
                  {tx.created_at ? new Date(tx.created_at).toLocaleString() : '—'}
                </span>
                <span className="shrink-0">
                  {tx.source_chain_id} → {tx.dest_chain_id}
                </span>
                <Badge
                  variant={
                    tx.status === 'completed' ? 'default' : tx.status === 'failed' ? 'destructive' : 'secondary'
                  }
                  className="shrink-0 text-xs"
                >
                  {tx.status}
                </Badge>
                {tx.amount != null && <span className="shrink-0">{tx.amount}</span>}
                {tx.outcome_token_id != null && (
                  <span className="text-muted-foreground shrink-0">token #{tx.outcome_token_id}</span>
                )}
                {tx.dest_tx_hash && (
                  <a
                    href={getBlockExplorerTxUrl(tx.dest_tx_hash, tx.dest_chain_id)}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-cyan-400 hover:underline shrink-0"
                  >
                    <ExternalLink className="h-3 w-3" />
                    tx
                  </a>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
