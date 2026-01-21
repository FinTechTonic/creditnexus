/**
 * Portfolio View Component
 * 
 * Displays current positions, P&L, asset allocation, and performance charts.
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { TrendingUp, TrendingDown, DollarSign, PieChart, Loader2 } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';

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
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadPortfolio = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const apiUrl = resolveApiUrl('/api/trades/portfolio');
        const response = await fetchWithAuth(apiUrl, {
          method: 'GET',
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Failed to load portfolio' }));
          throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}: Failed to load portfolio`);
        }

        const raw = await response.json();
        // Map API (market_value, unrealized_pl) to UI (total_value, unrealized_pnl, id for positions)
        const positions = (raw?.positions || []).map((p: any, i: number) => ({
          ...p,
          id: p?.id ?? `${p?.symbol ?? 'pos'}-${i}`,
          total_value: p?.total_value ?? p?.market_value ?? 0,
          unrealized_pnl: p?.unrealized_pnl ?? p?.unrealized_pl ?? 0,
          realized_pnl: p?.realized_pnl ?? 0,
        }));
        setPortfolio({ ...raw, positions });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load portfolio');
        // Set mock data for development
        setPortfolio({
          total_value: 0,
          unrealized_pnl: 0,
          realized_pnl: 0,
          total_pnl: 0,
          positions: [],
        });
      } finally {
        setIsLoading(false);
      }
    };

    loadPortfolio();
  }, []);

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
