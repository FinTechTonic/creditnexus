/**
 * Spending breakdown by category (and optionally merchant) from Plaid transactions.
 * AGGREGATED_DASHBOARD_AND_PORTFOLIO_PLAN: fetch GET /api/portfolio/spending-breakdown,
 * chart by category, empty state + CTA to link accounts.
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { fetchWithAuth } from '@/context/AuthContext';
import { Loader2, Link2, PieChart as PieChartIcon } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface CategoryItem {
  category: string;
  amount: number;
  count: number;
}

interface MerchantItem {
  merchant: string;
  amount: number;
  count: number;
}

interface BreakdownData {
  by_category: CategoryItem[];
  by_merchant: MerchantItem[];
  total_spend: number;
  total_transactions: number;
  days: number;
}

interface SpendingBreakdownResponse {
  breakdown: BreakdownData;
  requires_link_accounts: boolean;
}

const COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#84cc16'];

interface SpendingBreakdownProps {
  days?: number;
}

export function SpendingBreakdown({ days = 30 }: SpendingBreakdownProps) {
  const navigate = useNavigate();
  const [data, setData] = useState<BreakdownData | null>(null);
  const [requiresLinkAccounts, setRequiresLinkAccounts] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadBreakdown = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchWithAuth(`/api/portfolio/spending-breakdown?days=${days}`);
      if (!response.ok) {
        setData(null);
        setRequiresLinkAccounts(true);
        return;
      }
      const json: SpendingBreakdownResponse = await response.json();
      setData(json.breakdown ?? null);
      setRequiresLinkAccounts(json.requires_link_accounts ?? false);
    } catch {
      setData(null);
      setError('Failed to load spending breakdown');
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    loadBreakdown();
  }, [loadBreakdown]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PieChartIcon className="h-4 w-4" />
            Spending by category
          </CardTitle>
          <CardDescription>Last {days} days</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PieChartIcon className="h-4 w-4" />
            Spending by category
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (requiresLinkAccounts || !data || (data.by_category.length === 0 && data.total_spend === 0)) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PieChartIcon className="h-4 w-4" />
            Spending by category
          </CardTitle>
          <CardDescription>Last {days} days</CardDescription>
        </CardHeader>
        <CardContent className="py-8">
          <p className="text-sm text-muted-foreground mb-4">
            Link your bank to see spending breakdown by category.
          </p>
          <Button
            variant="outline"
            onClick={() => navigate('/app/link-accounts')}
            className="gap-2"
          >
            <Link2 className="h-4 w-4" />
            Link accounts
          </Button>
        </CardContent>
      </Card>
    );
  }

  const chartData = data.by_category.slice(0, 12).map((c) => ({
    name: c.category.length > 14 ? c.category.slice(0, 12) + '…' : c.category,
    fullName: c.category,
    amount: c.amount,
    count: c.count,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PieChartIcon className="h-4 w-4" />
          Spending by category
        </CardTitle>
        <CardDescription>
          Last {data.days} days · {data.total_transactions} transactions · ${data.total_spend.toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {chartData.length > 0 ? (
          <>
            <div className="h-[240px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11 }}
                    angle={-35}
                    textAnchor="end"
                    height={56}
                  />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v}`} />
                  <Tooltip
                    formatter={(value: number | undefined) => [value != null ? `$${value.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '', 'Spend']}
                    labelFormatter={(_, payload) => payload[0]?.payload?.fullName ?? ''}
                  />
                  <Bar dataKey="amount" name="Spend" radius={[4, 4, 0, 0]}>
                    {chartData.map((_, index) => (
                      <Cell key={index} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <ul className="mt-4 space-y-1.5 text-sm">
              {data.by_category.slice(0, 6).map((c, i) => (
                <li key={c.category} className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: COLORS[i % COLORS.length] }}
                    />
                    <span className="truncate">{c.category}</span>
                  </span>
                  <span className="font-medium tabular-nums">
                    ${c.amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </span>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">No spending data in this period.</p>
        )}
      </CardContent>
    </Card>
  );
}
