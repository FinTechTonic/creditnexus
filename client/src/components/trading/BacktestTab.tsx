/**
 * Backtesting interface: run backtests with symbol, date range, strategy, timeframe, initial capital.
 * Uses POST /api/stock-prediction/backtest and displays metrics, equity curve, and trades table.
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Loader2, Play, TrendingUp, TrendingDown, AlertTriangle, BarChart2 } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';
import { EquityCurveChart } from './EquityCurveChart';

const STRATEGIES = ['combined', 'trend', 'mean_reversion', 'momentum', 'volatility', 'stat_arb'] as const;
const TIMEFRAMES = ['1d', '1h', '15m'] as const;

function toYMD(d: Date): string {
  return d.toISOString().slice(0, 10);
}

interface BacktestTrade {
  side: string;
  price?: number;
  shares?: number;
  cost?: number;
  pnl?: number;
  equity?: number;
}

interface BacktestResult {
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  n_trades: number;
  equity_curve: number[];
  trades: BacktestTrade[];
  metadata: { error?: string; strategy?: string; initial_capital?: number; final_equity?: number };
}

const defaultEnd = new Date();
const defaultStart = new Date(defaultEnd);
defaultStart.setFullYear(defaultStart.getFullYear() - 1);

export function BacktestTab() {
  const [symbol, setSymbol] = useState('AAPL');
  const [start, setStart] = useState(toYMD(defaultStart));
  const [end, setEnd] = useState(toYMD(defaultEnd));
  const [strategy, setStrategy] = useState<string>('combined');
  const [timeframe, setTimeframe] = useState<string>('1d');
  const [initialCapital, setInitialCapital] = useState('100000');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BacktestResult | null>(null);

  const runBacktest = async () => {
    if (!symbol?.trim()) {
      setError('Symbol is required');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const body = {
        symbol: symbol.trim().toUpperCase(),
        start,
        end,
        strategy,
        timeframe,
        initial_capital: Math.max(100, parseFloat(initialCapital) || 100_000),
      };
      const url = resolveApiUrl('/api/stock-prediction/backtest');
      const res = await fetchWithAuth(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.detail || data.error || `HTTP ${res.status}`);
        return;
      }
      if (data.metadata?.error) {
        setError(data.metadata.error);
        setResult(data);
        return;
      }
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  const cap = result?.metadata?.initial_capital ?? (parseFloat(initialCapital) || 100_000);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart2 className="h-4 w-4" />
            Backtest
          </CardTitle>
          <CardDescription>
            Run a long-only backtest using signal strategies (trend, mean reversion, momentum, etc.) on OHLCV data.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <Label htmlFor="bt-symbol">Symbol</Label>
              <Input
                id="bt-symbol"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="AAPL"
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="bt-start">Start (YYYY-MM-DD)</Label>
              <Input
                id="bt-start"
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="bt-end">End (YYYY-MM-DD)</Label>
              <Input
                id="bt-end"
                type="date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="bt-strategy">Strategy</Label>
              <Select
                id="bt-strategy"
                value={strategy}
                onValueChange={setStrategy}
                className="mt-1"
              >
                {STRATEGIES.map((s) => (
                  <option key={s} value={s}>
                    {s.replace(/_/g, ' ')}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="bt-timeframe">Timeframe</Label>
              <Select
                id="bt-timeframe"
                value={timeframe}
                onValueChange={setTimeframe}
                className="mt-1"
              >
                {TIMEFRAMES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="bt-capital">Initial capital</Label>
              <Input
                id="bt-capital"
                type="number"
                min={100}
                step={1000}
                value={initialCapital}
                onChange={(e) => setInitialCapital(e.target.value)}
                placeholder="100000"
                className="mt-1"
              />
            </div>
          </div>
          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <Button onClick={runBacktest} disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Running…
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Run backtest
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {result && !result.metadata?.error && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Total return</CardTitle>
              </CardHeader>
              <CardContent className="flex items-center gap-2">
                {result.total_return >= 0 ? (
                  <TrendingUp className="h-4 w-4 text-green-600" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-red-600" />
                )}
                <span className={result.total_return >= 0 ? 'text-green-600' : 'text-red-600'}>
                  {(result.total_return * 100).toFixed(2)}%
                </span>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Sharpe ratio</CardTitle>
              </CardHeader>
              <CardContent>{result.sharpe_ratio.toFixed(2)}</CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Max drawdown</CardTitle>
              </CardHeader>
              <CardContent className="text-red-600">{(result.max_drawdown * 100).toFixed(2)}%</CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Win rate</CardTitle>
              </CardHeader>
              <CardContent>{(result.win_rate * 100).toFixed(1)}%</CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Trades</CardTitle>
              </CardHeader>
              <CardContent>{result.n_trades}</CardContent>
            </Card>
          </div>

          {result.equity_curve && result.equity_curve.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Equity curve</CardTitle>
              </CardHeader>
              <CardContent>
                <EquityCurveChart
                  equityCurve={result.equity_curve}
                  initialCapital={cap}
                  title=""
                  height={220}
                />
              </CardContent>
            </Card>
          )}

          {result.trades && result.trades.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Trades</CardTitle>
                <CardDescription>{result.trades.length} round-trips</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Side</TableHead>
                      <TableHead>Price</TableHead>
                      <TableHead>Shares</TableHead>
                      <TableHead>Cost</TableHead>
                      <TableHead>P&amp;L</TableHead>
                      <TableHead>Equity</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {result.trades.map((t, i) => (
                      <TableRow key={i}>
                        <TableCell className="capitalize">{t.side}</TableCell>
                        <TableCell>{t.price != null ? t.price.toFixed(2) : '—'}</TableCell>
                        <TableCell>{t.shares != null ? t.shares.toFixed(4) : '—'}</TableCell>
                        <TableCell>{t.cost != null ? t.cost.toFixed(2) : '—'}</TableCell>
                        <TableCell>
                          {t.pnl != null ? (
                            <span className={t.pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                              {t.pnl.toFixed(2)}
                            </span>
                          ) : (
                            '—'
                          )}
                        </TableCell>
                        <TableCell>{t.equity != null ? t.equity.toFixed(2) : '—'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          {result.metadata?.final_equity != null && (
            <p className="text-sm text-muted-foreground">
              Final equity: {result.metadata.final_equity.toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </p>
          )}
        </>
      )}
    </div>
  );
}
