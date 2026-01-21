/**
 * Displays an order recommendation (buy/sell/hold) and a button to request one.
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, ThumbsUp, ThumbsDown, Minus, Target } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';

interface Recommendation {
  id: number;
  symbol: string;
  action: 'buy' | 'sell' | 'hold';
  confidence: number;
  reasoning?: string | null;
  strategy: string;
  created_at: string;
}

interface OrderRecommendationCardProps {
  symbol: string;
  predictionId?: number | null;
  timeframe?: string;
  onRecommendation?: (r: Recommendation) => void;
}

export function OrderRecommendationCard({
  symbol,
  predictionId,
  timeframe = 'daily',
  onRecommendation,
}: OrderRecommendationCardProps) {
  const [rec, setRec] = useState<Recommendation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runRecommendation = async () => {
    if (!symbol?.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const url = resolveApiUrl('/api/stock-prediction/recommend-order');
      const res = await fetchWithAuth(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: symbol.trim(),
          prediction_id: predictionId || null,
          timeframe,
          strategy: 'combined',
        }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || d.error || d.reason || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setRec(data);
      onRecommendation?.(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to get recommendation');
    } finally {
      setLoading(false);
    }
  };

  const ActionIcon = rec?.action === 'buy' ? ThumbsUp : rec?.action === 'sell' ? ThumbsDown : Minus;
  const actionClass =
    rec?.action === 'buy'
      ? 'text-emerald-600'
      : rec?.action === 'sell'
        ? 'text-red-500'
        : 'text-amber-500';

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Target className="h-4 w-4" />
          Order recommendation
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button
          onClick={runRecommendation}
          disabled={loading || !symbol?.trim()}
          className="w-full sm:w-auto"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Analysing…
            </>
          ) : (
            'Get recommendation'
          )}
        </Button>
        {error && <p className="text-sm text-destructive">{error}</p>}
        {rec && (
          <div className="rounded-lg border bg-muted/30 p-4 space-y-2">
            <div className="flex items-center gap-2">
              <ActionIcon className={`h-5 w-5 ${actionClass}`} />
              <span className="font-medium capitalize">{rec.action}</span>
              <span className="text-muted-foreground">· {rec.symbol}</span>
              <span className="text-muted-foreground text-sm">{(rec.confidence * 100).toFixed(0)}% confidence</span>
            </div>
            {rec.reasoning && <p className="text-sm text-muted-foreground">{rec.reasoning}</p>}
            <p className="text-xs text-muted-foreground">Strategy: {rec.strategy}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
