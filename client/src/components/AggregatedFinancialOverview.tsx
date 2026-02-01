/**
 * Aggregated Financial Overview: hero metrics, chart, consolidated positions,
 * SpendingBreakdown card, liabilities card, empty states + CTAs.
 * AGGREGATED_DASHBOARD_AND_PORTFOLIO_PLAN.
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { fetchWithAuth } from '@/context/AuthContext';
import { SpendingBreakdown } from '@/components/dashboard-tabs/SpendingBreakdown';
import {
  Loader2,
  Link2,
  DollarSign,
  TrendingUp,
  Building2,
  Wallet,
  PieChart,
  AlertCircle,
} from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell } from 'recharts';

interface Position {
  symbol?: string;
  quantity?: number;
  market_value?: number;
  unrealized_pl?: number;
  source?: string;
  type?: string;
}

interface OverviewResponse {
  total_equity: number;
  bank_balances: number;
  trading_equity: number;
  manual_assets_value: number;
  unrealized_pl: number;
  buying_power: number;
  positions: Position[];
  account_info: Record<string, unknown>;
  liabilities?: Record<string, unknown> | null;
  message?: string | null;
  requires_link_accounts?: boolean;
  requires_positions?: boolean;
}

const SOURCE_LABELS: Record<string, string> = {
  plaid_investments: 'Bank/Investments',
  trading: 'Trading',
  manual: 'Manual',
};

export function AggregatedFinancialOverview() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWithAuth('/api/portfolio/overview');
      if (!res.ok) {
        setOverview(null);
        setError('Failed to load portfolio');
        return;
      }
      const data: OverviewResponse = await res.json();
      setOverview(data);
    } catch {
      setOverview(null);
      setError('Failed to load portfolio');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n);

  if (loading) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[320px]">
        <Loader2 className="h-10 w-10 animate-spin text-muted-foreground" />
        <p className="mt-4 text-sm text-muted-foreground">Loading financial overview…</p>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="p-6">
        <Card className="border-destructive/50">
          <CardContent className="pt-6">
            <p className="text-destructive mb-4">{error ?? 'No data'}</p>
            <Button variant="outline" onClick={loadOverview}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const hasEmpty = overview.requires_link_accounts || overview.requires_positions;
  const chartData = [
    { name: 'Bank', value: overview.bank_balances, fill: '#10b981' },
    { name: 'Trading', value: overview.trading_equity, fill: '#3b82f6' },
    { name: 'Manual', value: overview.manual_assets_value, fill: '#8b5cf6' },
  ].filter((d) => d.value > 0);

  return (
    <div className="p-6 space-y-6 flex flex-col">
      {/* Empty state CTA */}
      {hasEmpty && overview.message && (
        <Card className="bg-amber-950/30 border-amber-800/50">
          <CardContent className="pt-6 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-slate-200">{overview.message}</p>
                {overview.requires_link_accounts && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3 gap-2"
                    onClick={() => navigate('/app/link-accounts')}
                  >
                    <Link2 className="h-4 w-4" />
                    Link accounts
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Hero metrics */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <DollarSign className="h-4 w-4" />
              Total equity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-slate-100">{formatCurrency(overview.total_equity)}</p>
          </CardContent>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Building2 className="h-4 w-4" />
              Bank balances
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-slate-100">{formatCurrency(overview.bank_balances)}</p>
          </CardContent>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Trading equity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-slate-100">{formatCurrency(overview.trading_equity)}</p>
          </CardContent>
        </Card>
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Wallet className="h-4 w-4" />
              Buying power
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-slate-100">{formatCurrency(overview.buying_power)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Equity breakdown chart */}
      {chartData.length > 0 && (
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <PieChart className="h-4 w-4" />
              Equity breakdown
            </CardTitle>
            <CardDescription>Bank vs trading vs manual assets</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[200px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 24, left: 60, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-slate-700" />
                  <XAxis type="number" tickFormatter={(v) => `$${v}`} />
                  <YAxis type="category" dataKey="name" width={56} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(v: number | undefined) => [v != null ? formatCurrency(v) : '', '']} />
                  <Bar dataKey="value" name="Value" radius={[0, 4, 4, 0]}>
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Consolidated positions */}
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader>
            <CardTitle className="text-base">Consolidated positions</CardTitle>
            <CardDescription>By source: bank investments, trading, manual</CardDescription>
          </CardHeader>
          <CardContent>
            {!overview.positions || overview.positions.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4">
                No positions yet. Link accounts or add manual holdings.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700 text-muted-foreground text-left">
                      <th className="pb-2 pr-2">Symbol</th>
                      <th className="pb-2 pr-2">Source</th>
                      <th className="pb-2 pr-2 text-right">Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.positions.slice(0, 12).map((p, i) => (
                      <tr key={i} className="border-b border-slate-800/50">
                        <td className="py-2 pr-2 font-medium">{p.symbol ?? '—'}</td>
                        <td className="py-2 pr-2 text-muted-foreground">
                          {SOURCE_LABELS[p.source ?? ''] ?? p.source ?? '—'}
                        </td>
                        <td className="py-2 pr-2 text-right tabular-nums">
                          {p.market_value != null ? formatCurrency(p.market_value) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {overview.positions.length > 12 && (
                  <p className="text-xs text-muted-foreground mt-2">
                    +{overview.positions.length - 12} more
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Liabilities card */}
        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader>
            <CardTitle className="text-base">Liabilities</CardTitle>
            <CardDescription>Credit, mortgage, student (from linked accounts)</CardDescription>
          </CardHeader>
          <CardContent>
            {!overview.liabilities || Object.keys(overview.liabilities).length === 0 ? (
              <p className="text-sm text-muted-foreground py-4">
                No liability data. Link accounts to see credit and loan balances.
              </p>
            ) : (
              <pre className="text-xs text-muted-foreground overflow-auto max-h-[240px] p-3 rounded bg-slate-950/50">
                {JSON.stringify(overview.liabilities, null, 2)}
              </pre>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Spending breakdown card */}
      <SpendingBreakdown days={30} />
    </div>
  );
}
