/**
 * Portfolio Dashboard: aggregated view from /api/portfolio/overview
 * (trading + bank + manual assets). Uses /ws/trading/{user_id} for live updates.
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { fetchWithAuth, useAuth } from '@/context/AuthContext';
import { useTradingWebSocket } from '@/hooks/useTradingWebSocket';
import { DollarSign, Loader2, TrendingUp, TrendingDown, Wallet, Building2, PiggyBank } from 'lucide-react';

interface Overview {
  total_equity: number;
  bank_balances: number;
  trading_equity: number;
  manual_assets_value: number;
  unrealized_pl: number;
  buying_power: number;
  positions: Array<{
    symbol?: string;
    quantity?: number;
    average_price?: number;
    current_price?: number;
    market_value?: number;
    unrealized_pl?: number;
  }>;
  account_info?: Record<string, unknown>;
}

export function PortfolioDashboard() {
  const { user } = useAuth();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refetch, setRefetch] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWithAuth('/api/portfolio/overview', { method: 'GET' });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.detail || e.message || `HTTP ${res.status}`);
      }
      setOverview(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load portfolio');
      setOverview(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useTradingWebSocket(user?.id ?? null, () => setRefetch((r) => r + 1));
  useEffect(() => { load(); }, [load, refetch]);

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">{error || 'No portfolio data'}</p>
      </div>
    );
  }

  const u = overview.unrealized_pl ?? 0;
  const fmt = (n: number) => `$${Number(n).toFixed(2)}`;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Portfolio</h2>
        <p className="text-muted-foreground">Aggregated trading, bank, and manual assets</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Equity</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fmt(overview.total_equity)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Trading</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fmt(overview.trading_equity)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Bank</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fmt(overview.bank_balances)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Manual Assets</CardTitle>
            <PiggyBank className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fmt(overview.manual_assets_value)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Buying Power</CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fmt(overview.buying_power)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Unrealized P&L</CardTitle>
            {u >= 0 ? <TrendingUp className="h-4 w-4 text-green-500" /> : <TrendingDown className="h-4 w-4 text-red-500" />}
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${u >= 0 ? 'text-green-500' : 'text-red-500'}`}>{fmt(u)}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Positions</CardTitle>
          <CardDescription>Combined trading and manual holdings</CardDescription>
        </CardHeader>
        <CardContent>
          {!overview.positions?.length ? (
            <p className="text-muted-foreground text-sm">No positions</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2 font-medium">Symbol</th>
                    <th className="text-right p-2 font-medium">Qty</th>
                    <th className="text-right p-2 font-medium">Avg</th>
                    <th className="text-right p-2 font-medium">Value</th>
                    <th className="text-right p-2 font-medium">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {overview.positions.map((p, i) => (
                    <tr key={p.symbol ? `${p.symbol}-${i}` : i} className="border-b">
                      <td className="p-2 font-medium">{p.symbol || '—'}</td>
                      <td className="p-2 text-right">{Number(p.quantity ?? 0).toFixed(2)}</td>
                      <td className="p-2 text-right">{fmt(Number(p.average_price ?? 0))}</td>
                      <td className="p-2 text-right">{fmt(Number(p.market_value ?? 0))}</td>
                      <td className={`p-2 text-right ${Number(p.unrealized_pl ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {fmt(Number(p.unrealized_pl ?? 0))}
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
