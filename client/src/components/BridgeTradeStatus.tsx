/**
 * BridgeTradeStatus: display status of a bridge trade (Phase 9).
 * Fetches GET /api/bridge-builder/trade/{id} and shows status, lock_tx_hash, timestamps.
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { fetchWithAuth } from '@/context/AuthContext';
import { Loader2, CheckCircle2, XCircle, Clock, ArrowRight } from 'lucide-react';

interface BridgeTradeStatusData {
  id: number;
  user_id: number;
  token_id: number;
  source_chain_id: number;
  target_chain_id: number;
  target_address: string;
  trade_type: string;
  status: string;
  lock_tx_hash: string | null;
  bridge_external_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

interface BridgeTradeStatusProps {
  tradeId: number;
  onClose?: () => void;
}

const CHAIN_LABELS: Record<number, string> = {
  1: 'Ethereum',
  137: 'Polygon',
  8453: 'Base',
  1337: 'Local',
};

function statusIcon(status: string) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-5 w-5 text-emerald-400" />;
    case 'failed':
      return <XCircle className="h-5 w-5 text-red-400" />;
    default:
      return <Clock className="h-5 w-5 text-amber-400" />;
  }
}

export function BridgeTradeStatus({ tradeId, onClose }: BridgeTradeStatusProps) {
  const [data, setData] = useState<BridgeTradeStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!tradeId) return;
    setLoading(true);
    setError(null);
    fetchWithAuth(`/api/bridge-builder/trade/${tradeId}`)
      .then((r) => {
        if (!r.ok) throw new Error('Trade not found');
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load trade'))
      .finally(() => setLoading(false));
  }, [tradeId]);

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent className="py-6">
          <p className="text-sm text-red-400">{error ?? 'Trade not found'}</p>
          {onClose && (
            <button type="button" onClick={onClose} className="mt-2 text-sm text-slate-400 hover:text-slate-300">
              Close
            </button>
          )}
        </CardContent>
      </Card>
    );
  }

  const sourceLabel = CHAIN_LABELS[data.source_chain_id] ?? `Chain ${data.source_chain_id}`;
  const targetLabel = CHAIN_LABELS[data.target_chain_id] ?? `Chain ${data.target_chain_id}`;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            {statusIcon(data.status)}
            Trade #{data.id} – {data.status}
          </CardTitle>
          {onClose && (
            <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-300 text-sm">
              Close
            </button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex items-center gap-2 text-slate-300">
          <span>{sourceLabel}</span>
          <ArrowRight className="h-4 w-4 text-slate-500" />
          <span>{targetLabel}</span>
        </div>
        <div>
          <span className="text-slate-500">Token ID:</span>
          <span className="ml-2 text-slate-200">{data.token_id}</span>
        </div>
        <div>
          <span className="text-slate-500">Target:</span>
          <span className="ml-2 font-mono text-xs text-slate-400 truncate block max-w-full" title={data.target_address}>
            {data.target_address}
          </span>
        </div>
        {data.lock_tx_hash && (
          <div>
            <span className="text-slate-500">Lock TX:</span>
            <span className="ml-2 font-mono text-xs text-slate-400 truncate block max-w-full" title={data.lock_tx_hash}>
              {data.lock_tx_hash}
            </span>
          </div>
        )}
        {data.bridge_external_id && (
          <div>
            <span className="text-slate-500">Bridge ID:</span>
            <span className="ml-2 text-slate-400">{data.bridge_external_id}</span>
          </div>
        )}
        <div className="flex gap-4 text-slate-500 text-xs pt-2">
          <span>Created: {data.created_at ? new Date(data.created_at).toLocaleString() : '—'}</span>
          <span>Updated: {data.updated_at ? new Date(data.updated_at).toLocaleString() : '—'}</span>
        </div>
      </CardContent>
    </Card>
  );
}
