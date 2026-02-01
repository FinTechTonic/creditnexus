/**
 * UnifiedGraphs Component (Phase 2, Week 7)
 * 
 * Displays portfolio performance, transaction trends, and investment allocation graphs.
 * Integrates with portfolio aggregation API endpoints.
 */

import { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { fetchWithAuth } from '@/context/AuthContext';
import { Loader2 } from 'lucide-react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

interface PortfolioPerformanceData {
  date: string;
  value: number;
  return_percent: number;
}

interface TransactionTrendData {
  date: string;
  income: number;
  expenses: number;
  net: number;
}

interface InvestmentAllocationData {
  name: string;
  value: number;
  color: string;
}

interface UnifiedGraphsProps {
  userId?: number;
  days?: number;
}

const COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899'];

export function UnifiedGraphs({ userId, days = 30 }: UnifiedGraphsProps) {
  const [performanceData, setPerformanceData] = useState<PortfolioPerformanceData[]>([]);
  const [transactionTrends, setTransactionTrends] = useState<TransactionTrendData[]>([]);
  const [investmentAllocation, setInvestmentAllocation] = useState<InvestmentAllocationData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadGraphData = async () => {
      setLoading(true);
      setError(null);

      try {
        // Load performance data
        const perfRes = await fetchWithAuth(`/api/portfolio/performance?days=${days}`);
        if (perfRes.ok) {
          const perfData = await perfRes.json();
          const dailyReturns = (perfData.daily_returns || []).map((d: any) => ({
            date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
            value: d.value || 0,
            return_percent: d.return_percent || 0,
          }));
          setPerformanceData(dailyReturns);
        }

        // Load transactions for trend analysis
        const txRes = await fetchWithAuth(`/api/portfolio/transactions?days=${days}`);
        if (txRes.ok) {
          const txData = await txRes.json();
          const transactions = txData.transactions || [];

          // Group transactions by date and calculate income/expenses
          const groupedByDate: Record<string, { income: number; expenses: number }> = {};
          transactions.forEach((tx: any) => {
            const date = tx.date ? new Date(tx.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'Unknown';
            const amount = tx.amount || 0;
            if (!groupedByDate[date]) {
              groupedByDate[date] = { income: 0, expenses: 0 };
            }
            if (amount > 0) {
              groupedByDate[date].income += amount;
            } else {
              groupedByDate[date].expenses += Math.abs(amount);
            }
          });

          const trends = Object.entries(groupedByDate)
            .map(([date, data]) => ({
              date,
              income: data.income,
              expenses: data.expenses,
              net: data.income - data.expenses,
            }))
            .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
          setTransactionTrends(trends);
        }

        // Load investments for allocation
        const invRes = await fetchWithAuth('/api/portfolio/investments');
        if (invRes.ok) {
          const invData = await invRes.json();
          const positions = invData.positions || [];

          // Group by symbol and calculate total market value
          const allocationMap: Record<string, number> = {};
          positions.forEach((pos: any) => {
            const symbol = pos.symbol || 'Unknown';
            const value = pos.market_value || 0;
            allocationMap[symbol] = (allocationMap[symbol] || 0) + value;
          });

          const allocation = Object.entries(allocationMap)
            .map(([name, value], index) => ({
              name,
              value,
              color: COLORS[index % COLORS.length],
            }))
            .sort((a, b) => b.value - a.value)
            .slice(0, 7); // Top 7 holdings

          setInvestmentAllocation(allocation);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load graph data');
      } finally {
        setLoading(false);
      }
    };

    loadGraphData();
  }, [userId, days]);

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardContent className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12 text-muted-foreground">
          {error}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {/* Portfolio Performance Graph */}
      <Card className="md:col-span-2">
        <CardHeader>
          <CardTitle>Portfolio Performance</CardTitle>
          <CardDescription>Portfolio value over time</CardDescription>
        </CardHeader>
        <CardContent>
          {performanceData.length === 0 ? (
            <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
              No performance data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-slate-700" />
                <XAxis
                  dataKey="date"
                  className="text-xs"
                  tick={{ fill: '#94a3b8' }}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                />
                <YAxis
                  className="text-xs"
                  tick={{ fill: '#94a3b8' }}
                  tickFormatter={(value) => `$${value.toLocaleString()}`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '6px',
                  }}
                  formatter={(value: number | undefined) => [value != null ? `$${value.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '', 'Value']}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                  name="Portfolio Value"
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Transaction Trends Graph */}
      <Card className="md:col-span-2">
        <CardHeader>
          <CardTitle>Transaction Trends</CardTitle>
          <CardDescription>Income vs expenses over time</CardDescription>
        </CardHeader>
        <CardContent>
          {transactionTrends.length === 0 ? (
            <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
              No transaction data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={transactionTrends}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-slate-700" />
                <XAxis
                  dataKey="date"
                  className="text-xs"
                  tick={{ fill: '#94a3b8' }}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                />
                <YAxis
                  className="text-xs"
                  tick={{ fill: '#94a3b8' }}
                  tickFormatter={(value) => `$${value.toLocaleString()}`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '6px',
                  }}
                  formatter={(value: number | undefined) => [value != null ? `$${value.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '', '']}
                />
                <Legend />
                <Bar dataKey="income" fill="#10b981" name="Income" />
                <Bar dataKey="expenses" fill="#ef4444" name="Expenses" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Investment Allocation Graph */}
      <Card>
        <CardHeader>
          <CardTitle>Investment Allocation</CardTitle>
          <CardDescription>Portfolio distribution by holding</CardDescription>
        </CardHeader>
        <CardContent>
          {investmentAllocation.length === 0 ? (
            <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
              No investment data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={investmentAllocation}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {investmentAllocation.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '6px',
                  }}
                  formatter={(value: number | undefined) => value != null ? `$${value.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : ''}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
