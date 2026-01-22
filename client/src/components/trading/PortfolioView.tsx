/**
 * Portfolio View Component
 *
 * Displays aggregated portfolio from /api/portfolio/overview (trading + bank + manual).
 * Subscribes to /ws/trading/{user_id} for live updates; refetches on non-ping messages.
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { TrendingUp, TrendingDown, DollarSign, PieChart, Loader2 } from 'lucide-react';
import { fetchWithAuth, useAuth } from '@/context/AuthContext';
import { useTradingWebSocket } from '@/hooks/useTradingWebSocket';
import { useFDC3, type PortfolioContext } from '@/context/FDC3Context';

interface Position {
  id: string;
  symbol: string;
  quantity: number;
  average_price: number;
  current_price: number;
  unrealized_pnl: number;
  realized_pnl: number;
  total_value: number;
}

interface PortfolioSummary {
  total_value: number;
  unrealized_pnl: number;
  realized_pnl: number;
  total_pnl: number;
  positions: Position[];
}

export function PortfolioView() {
  const { user } = useAuth();
  const { context } = useFDC3();
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refetch, setRefetch] = useState(0);

  // Listen for FDC3 portfolio context updates
  useEffect(() => {
    if (context?.type === 'finos.creditnexus.portfolio') {
      // Portfolio context received - trigger refresh
      setRefetch((r) => r + 1);
    }
  }, [context]);

  const loadPortfolio = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetchWithAuth('/api/portfolio/overview', { method: 'GET' });
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to load portfolio' }));
        throw new Error(err.detail || err.message || `HTTP ${response.status}`);
      }
      const raw = await response.json();
      const u = Number(raw?.unrealized_pl) || 0;
      const r = 0;
      const positions = (raw?.positions || []).map((p: Record<string, unknown>, i: number) => ({
        id: (p?.id as string) ?? `${(p?.symbol as string) ?? 'pos'}-${i}`,
        symbol: String(p?.symbol ?? ''),
        quantity: Number(p?.quantity ?? 0),
        average_price: Number(p?.average_price ?? 0),
        current_price: Number(p?.current_price ?? 0),
        unrealized_pnl: Number(p?.unrealized_pnl ?? p?.unrealized_pl ?? 0),
        realized_pnl: Number(p?.realized_pnl ?? 0),
        total_value: Number(p?.total_value ?? p?.market_value ?? 0),
      }));
      setPortfolio({
        total_value: Number(raw?.total_equity) ?? 0,
        unrealized_pnl: u,
        realized_pnl: r,
        total_pnl: u + r,
        positions,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load portfolio');
      setPortfolio({ total_value: 0, unrealized_pnl: 0, realized_pnl: 0, total_pnl: 0, positions: [] });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useTradingWebSocket(user?.id ?? null, () => setRefetch((r) => r + 1));

  useEffect(() => {
    loadPortfolio();
  }, [loadPortfolio, refetch]);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-12">
          <div className="text-center text-muted-foreground">
            <p className="text-sm">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!portfolio) {
    return (
      <Card>
        <CardContent className="py-12">
          <div className="text-center text-muted-foreground">
            <p className="text-sm">No portfolio data available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const pnlPercentage = portfolio.total_value > 0 
    ? ((portfolio.total_pnl / portfolio.total_value) * 100).toFixed(2)
    : '0.00';

  return (
    <div className="space-y-6">
      {/* Portfolio Summary */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${portfolio.total_value.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">Current portfolio value</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
            {portfolio.total_pnl >= 0 ? (
              <TrendingUp className="h-4 w-4 text-green-500" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-500" />
            )}
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${portfolio.total_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              ${portfolio.total_pnl.toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground">
              {pnlPercentage}% {portfolio.total_pnl >= 0 ? 'gain' : 'loss'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Unrealized P&L</CardTitle>
            <PieChart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${portfolio.unrealized_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              ${portfolio.unrealized_pnl.toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground">Open positions</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Realized P&L</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${portfolio.realized_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              ${portfolio.realized_pnl.toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground">Closed positions</p>
          </CardContent>
        </Card>
      </div>

      {/* Positions Table */}
      <Card>
        <CardHeader>
          <CardTitle>Current Positions</CardTitle>
          <CardDescription>
            Your open positions and performance
          </CardDescription>
        </CardHeader>
        <CardContent>
          {portfolio.positions.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-sm">No open positions</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2 font-medium">Symbol</th>
                    <th className="text-right p-2 font-medium">Quantity</th>
                    <th className="text-right p-2 font-medium">Avg Price</th>
                    <th className="text-right p-2 font-medium">Current Price</th>
                    <th className="text-right p-2 font-medium">Value</th>
                    <th className="text-right p-2 font-medium">Unrealized P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.positions.map((position) => (
                    <tr key={position.id} className="border-b">
                      <td className="p-2 font-medium">{position.symbol}</td>
                      <td className="p-2 text-right">{position.quantity.toFixed(2)}</td>
                      <td className="p-2 text-right">${position.average_price.toFixed(2)}</td>
                      <td className="p-2 text-right">${position.current_price.toFixed(2)}</td>
                      <td className="p-2 text-right">${position.total_value.toFixed(2)}</td>
                      <td className={`p-2 text-right font-medium ${
                        position.unrealized_pnl >= 0 ? 'text-green-500' : 'text-red-500'
                      }`}>
                        ${position.unrealized_pnl.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
