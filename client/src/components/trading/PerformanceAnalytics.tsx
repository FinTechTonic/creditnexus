/**
 * Performance Analytics Component
 * 
 * Displays portfolio performance metrics and analytics.
 * Backend API: /api/portfolio/performance
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Loader2, TrendingUp, TrendingDown, BarChart3, DollarSign } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface PerformanceMetrics {
  total_return: number;
  total_return_percent: number;
  daily_return: number;
  daily_return_percent: number;
  weekly_return: number;
  weekly_return_percent: number;
  monthly_return: number;
  monthly_return_percent: number;
  best_day?: { date: string; return: number; return_percent: number } | null;
  worst_day?: { date: string; return: number; return_percent: number } | null;
  win_rate?: number | null;
  avg_win?: number | null;
  avg_loss?: number | null;
}

interface PerformanceData {
  current_value: number;
  initial_value: number;
  metrics: PerformanceMetrics;
  daily_returns: Array<{
    date: string;
    value: number;
    return: number;
    return_percent: number;
  }>;
  period_start: string;
  period_end: string;
}

export function PerformanceAnalytics() {
  const [data, setData] = useState<PerformanceData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);

  const loadPerformance = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const apiUrl = resolveApiUrl(`/api/portfolio/performance?days=${days}`);
      const response = await fetchWithAuth(apiUrl, { method: 'GET' });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to load performance data' }));
        throw new Error(err.detail || err.message || `HTTP ${response.status}`);
      }

      const result: PerformanceData = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load performance data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPerformance();
  }, [days]);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12 text-muted-foreground">
          {error || 'No performance data available'}
        </CardContent>
      </Card>
    );
  }

  const formatCurrency = (value: number) => `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const formatPercent = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;

  return (
    <div className="space-y-6">
      {/* Period Selector */}
      <Card>
        <CardHeader>
          <CardTitle>Performance Analytics</CardTitle>
          <CardDescription>Portfolio performance metrics and returns</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <Label htmlFor="period-days">Analysis Period</Label>
            <Select
              id="period-days"
              value={days.toString()}
              onValueChange={(value) => setDays(parseInt(value, 10))}
            >
              <option value="7">7 Days</option>
              <option value="30">30 Days</option>
              <option value="90">90 Days</option>
              <option value="180">180 Days</option>
              <option value="365">1 Year</option>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Return</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(data.metrics.total_return)}
            </div>
            <div className={`text-sm flex items-center gap-1 ${
              data.metrics.total_return_percent >= 0 ? 'text-green-500' : 'text-red-500'
            }`}>
              {data.metrics.total_return_percent >= 0 ? (
                <TrendingUp className="h-4 w-4" />
              ) : (
                <TrendingDown className="h-4 w-4" />
              )}
              {formatPercent(data.metrics.total_return_percent)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Daily Return</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(data.metrics.daily_return)}
            </div>
            <div className={`text-sm flex items-center gap-1 ${
              data.metrics.daily_return_percent >= 0 ? 'text-green-500' : 'text-red-500'
            }`}>
              {data.metrics.daily_return_percent >= 0 ? (
                <TrendingUp className="h-4 w-4" />
              ) : (
                <TrendingDown className="h-4 w-4" />
              )}
              {formatPercent(data.metrics.daily_return_percent)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Current Value</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              {formatCurrency(data.current_value)}
            </div>
            <div className="text-sm text-muted-foreground">
              Initial: {formatCurrency(data.initial_value)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {data.metrics.win_rate !== null && data.metrics.win_rate !== undefined
                ? `${(data.metrics.win_rate * 100).toFixed(1)}%`
                : 'N/A'}
            </div>
            <div className="text-sm text-muted-foreground">
              {data.metrics.avg_win && data.metrics.avg_loss && (
                <>Avg Win: {formatCurrency(data.metrics.avg_win)} | Avg Loss: {formatCurrency(Math.abs(data.metrics.avg_loss))}</>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Performance Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Portfolio Value Over Time
          </CardTitle>
          <CardDescription>
            {new Date(data.period_start).toLocaleDateString()} - {new Date(data.period_end).toLocaleDateString()}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={data.daily_returns}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--muted))" />
              <XAxis 
                dataKey="date" 
                tick={{ fontSize: 10 }}
                tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                angle={-45}
                textAnchor="end"
                height={60}
              />
              <YAxis 
                tick={{ fontSize: 10 }}
                tickFormatter={(value) => formatCurrency(value)}
                domain={['auto', 'auto']}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '4px',
                }}
                formatter={(value: number | undefined) => value != null ? formatCurrency(value) : ''}
                labelFormatter={(label) => `Date: ${new Date(label).toLocaleDateString()}`}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="value"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={false}
                name="Portfolio Value"
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Additional Metrics */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Weekly Return</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-xl font-semibold ${
              data.metrics.weekly_return_percent >= 0 ? 'text-green-500' : 'text-red-500'
            }`}>
              {formatPercent(data.metrics.weekly_return_percent)}
            </div>
            <div className="text-sm text-muted-foreground">
              {formatCurrency(data.metrics.weekly_return)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Monthly Return</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-xl font-semibold ${
              data.metrics.monthly_return_percent >= 0 ? 'text-green-500' : 'text-red-500'
            }`}>
              {formatPercent(data.metrics.monthly_return_percent)}
            </div>
            <div className="text-sm text-muted-foreground">
              {formatCurrency(data.metrics.monthly_return)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Best Day</CardTitle>
          </CardHeader>
          <CardContent>
            {data.metrics.best_day ? (
              <>
                <div className="text-xl font-semibold text-green-500">
                  {formatPercent(data.metrics.best_day.return_percent)}
                </div>
                <div className="text-sm text-muted-foreground">
                  {new Date(data.metrics.best_day.date).toLocaleDateString()}
                </div>
              </>
            ) : (
              <div className="text-sm text-muted-foreground">N/A</div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
