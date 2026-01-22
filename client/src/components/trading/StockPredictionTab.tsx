/**
 * Stock prediction tab: MarketStatusWidget, symbol + timeframe + run prediction,
 * PredictionChart, OrderRecommendationCard, PredictionHistory (placeholder).
 * FDC3: prefills symbol from fdc3.instrument, finos.creditnexus.instrument, finos.creditnexus.stockPrediction;
 * broadcasts finos.creditnexus.stockPrediction on successful run.
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, LineChart } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { useFDC3 } from '@/context/FDC3Context';
import { createStockPredictionContext } from '@/context/FDC3Context';
import { resolveApiUrl } from '@/utils/apiBase';
import { MarketStatusWidget } from './MarketStatusWidget';
import { PredictionChart } from './PredictionChart';
import { OrderRecommendationCard } from './OrderRecommendationCard';

function symbolFromContext(ctx: { type?: string; symbol?: string; id?: { ticker?: string; symbol?: string }; symbols?: string[] } | null): string | undefined {
  if (!ctx) return undefined;
  if (ctx.type === 'finos.creditnexus.stockPrediction' && ctx.symbol) return ctx.symbol;
  if (ctx.type === 'finos.creditnexus.agentResult' && ctx.symbols?.[0]) return ctx.symbols[0];
  const t = (ctx as { id?: { ticker?: string; symbol?: string } }).id?.ticker ?? (ctx as { id?: { ticker?: string; symbol?: string } }).id?.symbol;
  if (t) return t;
  return undefined;
}

type Timeframe = 'daily' | 'hourly' | '15min';
type Strategy = 'chronos' | 'technical';

export function StockPredictionTab() {
  const { context, broadcast } = useFDC3();
  const [symbol, setSymbol] = useState('AAPL');
  const [timeframe, setTimeframe] = useState<Timeframe>('daily');
  const [strategy, setStrategy] = useState<Strategy>('chronos');
  const [modelId, setModelId] = useState('');
  const [result, setResult] = useState<{ forecast?: number[]; prediction_id?: number; error?: string; cached?: boolean } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const s = symbolFromContext(context as Parameters<typeof symbolFromContext>[0]);
    if (s && s !== symbol) setSymbol(s);
  }, [context]);

  const runPrediction = async () => {
    if (!symbol?.trim()) return;
    setLoading(true);
    setResult(null);
    const endpoint =
      timeframe === 'daily'
        ? '/api/stock-prediction/daily'
        : timeframe === 'hourly'
          ? '/api/stock-prediction/hourly'
          : '/api/stock-prediction/15min';
    try {
      const params = new URLSearchParams({ symbol: symbol.trim(), strategy });
      if (strategy === 'chronos' && modelId) params.set('model_id', modelId);
      const url = resolveApiUrl(`${endpoint}?${params}`);
      const res = await fetchWithAuth(url);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setResult({ error: data.error || data.detail || `HTTP ${res.status}` });
        return;
      }
      const forecast = Array.isArray(data.forecast) ? data.forecast : (data.forecast as number[] | undefined);
      const next = {
        forecast: forecast || [],
        prediction_id: data.prediction_id,
        error: data.error || undefined,
        cached: data.cached === true,
      };
      setResult(next);
      try {
        broadcast(createStockPredictionContext(symbol.trim(), {
          symbol: symbol.trim(),
          timeframe,
          strategy,
          forecast: next.forecast,
          signal: (data as { signal?: 'bullish'|'bearish'|'neutral' }).signal,
          prediction_id: next.prediction_id,
          cached: next.cached,
        }));
      } catch {
        // ignore FDC3 broadcast errors
      }
    } catch (e) {
      setResult({ error: e instanceof Error ? e.message : 'Request failed' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <MarketStatusWidget market="US_STOCKS" />
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Predict</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="sp-symbol">Symbol</Label>
              <Input
                id="sp-symbol"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="AAPL"
                className="mt-1"
              />
            </div>
            <div>
              <Label>Timeframe</Label>
              <select
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value as Timeframe)}
                className="mt-1 w-full rounded border bg-background px-3 py-2 text-sm"
              >
                <option value="daily">Daily</option>
                <option value="hourly">Hourly</option>
                <option value="15min">15 min</option>
              </select>
            </div>
            <div>
              <Label>Strategy</Label>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value as Strategy)}
                className="mt-1 w-full rounded border bg-background px-3 py-2 text-sm"
              >
                <option value="chronos">Chronos</option>
                <option value="technical">Technical</option>
              </select>
            </div>
            {strategy === 'chronos' && (
              <div>
                <Label>Chronos model</Label>
                <select
                  value={modelId}
                  onChange={(e) => setModelId(e.target.value)}
                  className="mt-1 w-full rounded border bg-background px-3 py-2 text-sm"
                >
                  <option value="">Default (server config)</option>
                  <option value="amazon/chronos-t5-small">Chronos T5 Small</option>
                  <option value="amazon/chronos-t5-base">Chronos T5 Base</option>
                </select>
              </div>
            )}
            <Button onClick={runPrediction} disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Running…
                </>
              ) : (
                'Run prediction'
              )}
            </Button>
          </CardContent>
        </Card>
        <OrderRecommendationCard
          symbol={symbol}
          predictionId={result?.prediction_id}
          timeframe={timeframe}
        />
      </div>

      {result && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <LineChart className="h-4 w-4" />
              Forecast {result.cached ? '(cached)' : ''}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {result.error ? (
              <p className="text-destructive">{result.error}</p>
            ) : (
              <PredictionChart forecast={result.forecast || []} title={`${symbol} ${timeframe}`} />
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Prediction history</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">Recent predictions will appear here.</p>
        </CardContent>
      </Card>
    </div>
  );
}
