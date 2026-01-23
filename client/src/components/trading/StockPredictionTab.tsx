/**
 * Stock prediction tab: MarketStatusWidget, symbol + timeframe + run prediction,
 * PredictionChart, OrderRecommendationCard, PredictionHistory (placeholder).
 * FDC3: prefills symbol from fdc3.instrument, finos.creditnexus.instrument, finos.creditnexus.stockPrediction;
 * broadcasts finos.creditnexus.stockPrediction on successful run.
 */

import { useState, useEffect, useRef } from 'react';
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
import { ErrorBoundary } from '@/components/ErrorBoundary';

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
  // Load result from sessionStorage on mount to persist across re-renders
  const getInitialResult = (): { forecast?: number[]; prediction_id?: number; error?: string; cached?: boolean } | null => {
    try {
      const saved = sessionStorage.getItem('stockPredictionResult');
      if (saved) {
        const parsed = JSON.parse(saved);
        // Only restore if it's recent (within last hour)
        if (parsed.timestamp && Date.now() - parsed.timestamp < 3600000) {
          return parsed.result;
        }
      }
    } catch {
      // Ignore errors
    }
    return null;
  };
  
  const initialResult = getInitialResult();
  const [result, setResult] = useState<{ forecast?: number[]; prediction_id?: number; error?: string; cached?: boolean } | null>(initialResult);
  const [loading, setLoading] = useState(false);
  // Track our own broadcasts to prevent reacting to them
  const lastBroadcastRef = useRef<{ symbol: string; prediction_id?: number } | null>(null);
  // Persist result in ref to prevent loss during re-renders
  const resultRef = useRef<{ forecast?: number[]; prediction_id?: number; error?: string; cached?: boolean } | null>(initialResult);
  
  // Sync ref with state whenever result changes
  useEffect(() => {
    if (result) {
      resultRef.current = result;
    }
  }, [result]);

  useEffect(() => {
    try {
      // Ignore our own broadcasts by checking if this context matches what we just broadcasted
      if (context?.type === 'finos.creditnexus.stockPrediction') {
        const ctx = context as { symbol?: string; prediction_id?: number };
        if (lastBroadcastRef.current && 
            ctx.symbol === lastBroadcastRef.current.symbol &&
            ctx.prediction_id === lastBroadcastRef.current.prediction_id) {
          // This is our own broadcast - ignore it completely
          // Don't update symbol, don't clear result, just return
          // Also restore result from ref if it was lost during re-render
          if (!result && resultRef.current) {
            setResult(resultRef.current);
          }
          return;
        }
      }
      
      const s = symbolFromContext(context as Parameters<typeof symbolFromContext>[0]);
      // Only update symbol if it's different AND not from our own broadcast
      // IMPORTANT: Don't clear result when updating symbol from external context
      if (s && s !== symbol && context?.type !== 'finos.creditnexus.stockPrediction') {
        setSymbol(s);
        // Note: We intentionally don't clear result here - let user keep their prediction results
      }
      
      // Restore result from ref or sessionStorage if it was lost (safety check)
      if (!result) {
        if (resultRef.current) {
          setResult(resultRef.current);
        } else {
          const restored = getInitialResult();
          if (restored) {
            resultRef.current = restored;
            setResult(restored);
          }
        }
      }
    } catch (e) {
      console.error('Error in StockPredictionTab useEffect:', e);
      // Restore result from ref on error
      if (!result && resultRef.current) {
        setResult(resultRef.current);
      }
    }
    // Only depend on context, not symbol, to avoid infinite loops
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      // Handle forecast data - it might be nested in the response
      let forecast: number[] = [];
      if (data.forecast) {
        if (Array.isArray(data.forecast)) {
          forecast = data.forecast;
        } else if (typeof data.forecast === 'object' && Array.isArray(data.forecast.forecast)) {
          // Handle nested forecast structure
          forecast = data.forecast.forecast;
        }
      }
      
      const next = {
        forecast: forecast,
        prediction_id: data.prediction_id,
        error: data.error || undefined,
        cached: data.cached === true,
      };
      // Set result first to ensure UI updates
      // Also store in ref and sessionStorage to persist across re-renders
      resultRef.current = next;
      setResult(next);
      // Persist to sessionStorage
      try {
        sessionStorage.setItem('stockPredictionResult', JSON.stringify({
          result: next,
          timestamp: Date.now(),
        }));
      } catch (e) {
        console.debug('Failed to save result to sessionStorage:', e);
      }
      
      // Only broadcast if we have a valid forecast or prediction_id
      // Use setTimeout to defer broadcast and prevent it from interfering with state updates
      // Increased delay to ensure state updates complete before broadcast
      if (forecast.length > 0 || next.prediction_id) {
        // Track what we're about to broadcast so we can ignore it in useEffect
        lastBroadcastRef.current = {
          symbol: symbol.trim(),
          prediction_id: next.prediction_id,
        };
        
        // Defer broadcast significantly to ensure UI has fully updated
        setTimeout(() => {
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
            // Clear the ref after a delay to allow useEffect to process it
            setTimeout(() => {
              lastBroadcastRef.current = null;
            }, 500);
          } catch (e) {
            // ignore FDC3 broadcast errors - don't let them break the UI
            console.debug('FDC3 broadcast error (ignored):', e);
            // Clear the ref if broadcast failed
            lastBroadcastRef.current = null;
          }
        }, 300);
      }
    } catch (e) {
      console.error('Prediction request failed:', e);
      setResult({ error: e instanceof Error ? e.message : 'Request failed' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <ErrorBoundary fallback={<Card><CardContent className="py-6 text-muted-foreground text-sm">Market status unavailable</CardContent></Card>}>
          <MarketStatusWidget market="US_STOCKS" />
        </ErrorBoundary>
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
        <ErrorBoundary fallback={<Card><CardContent className="py-6 text-muted-foreground text-sm">Order recommendation unavailable</CardContent></Card>}>
          <OrderRecommendationCard
            symbol={symbol}
            predictionId={result?.prediction_id}
            timeframe={timeframe}
          />
        </ErrorBoundary>
      </div>

      {result && (
        <Card key={`result-${result.prediction_id || 'temp'}`}>
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
              <ErrorBoundary fallback={
                <div className="py-6 text-muted-foreground text-sm">
                  Error displaying chart. Forecast data: {result.forecast?.length || 0} points
                </div>
              }>
                <PredictionChart forecast={result.forecast || []} title={`${symbol} ${timeframe}`} />
              </ErrorBoundary>
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
