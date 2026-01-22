/**
 * Candlestick Chart Component
 * 
 * Displays OHLCV (Open, High, Low, Close, Volume) candlestick chart using Recharts.
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';

interface OHLCVData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface CandleChartProps {
  symbol: string;
  timeframe?: '1D' | '1H' | '15Min';
  days?: number;
  height?: number;
}

export function CandleChart({ 
  symbol, 
  timeframe = '1D', 
  days = 30,
  height = 400 
}: CandleChartProps) {
  const [data, setData] = useState<OHLCVData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!symbol?.trim()) {
      setData([]);
      setIsLoading(false);
      return;
    }

    const loadOHLCV = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const url = resolveApiUrl(
          `/api/trades/ohlcv/${encodeURIComponent(symbol.trim().toUpperCase())}?timeframe=${timeframe}&days=${days}`
        );
        const res = await fetchWithAuth(url);
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: 'Failed to load OHLCV data' }));
          throw new Error(err.detail || err.message || `HTTP ${res.status}`);
        }
        const result = await res.json();
        setData(result.data || []);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load chart data');
        setData([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadOHLCV();
  }, [symbol, timeframe, days]);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center" style={{ height }}>
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">{symbol} Chart</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center text-muted-foreground text-sm" style={{ height: height - 60 }}>
          {error || 'No chart data available'}
        </CardContent>
      </Card>
    );
  }

  // Format data for Recharts
  // Create candlestick visualization using lines and bars
  const chartData = data.map((d) => ({
    ...d,
    date: new Date(d.timestamp).toLocaleDateString(),
    // For candlestick: use high-low line and open-close bar
    bodyTop: Math.max(d.open, d.close),
    bodyBottom: Math.min(d.open, d.close),
    isUp: d.close >= d.open,
  }));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center justify-between">
          <span>{symbol} - {timeframe}</span>
          <span className="text-xs text-muted-foreground font-normal">
            {data.length} candles
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={height - 80}>
          <ComposedChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--muted))" />
            <XAxis 
              dataKey="date" 
              tick={{ fontSize: 10 }}
              angle={-45}
              textAnchor="end"
              height={60}
            />
            <YAxis 
              yAxisId="price"
              orientation="left"
              tick={{ fontSize: 10 }}
              domain={['auto', 'auto']}
            />
            <YAxis 
              yAxisId="volume"
              orientation="right"
              tick={{ fontSize: 10 }}
              domain={[0, 'auto']}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--background))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '4px',
              }}
              formatter={(value: number, name: string) => {
                if (name === 'volume') {
                  return [value.toLocaleString(), 'Volume'];
                }
                return [`$${value.toFixed(2)}`, name.charAt(0).toUpperCase() + name.slice(1)];
              }}
              labelFormatter={(label) => `Date: ${label}`}
            />
            {/* High-Low line (wick) */}
            <Line
              yAxisId="price"
              type="monotone"
              dataKey="high"
              stroke="hsl(var(--muted-foreground))"
              strokeWidth={1}
              dot={false}
              connectNulls
            />
            <Line
              yAxisId="price"
              type="monotone"
              dataKey="low"
              stroke="hsl(var(--muted-foreground))"
              strokeWidth={1}
              dot={false}
              connectNulls
            />
            {/* Volume bars */}
            <Bar
              yAxisId="volume"
              dataKey="volume"
              fill="hsl(var(--muted))"
              opacity={0.3}
            />
            {/* Price line (close) */}
            <Line
              yAxisId="price"
              type="monotone"
              dataKey="close"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={false}
              connectNulls
            />
            <ReferenceLine yAxisId="price" y={chartData[chartData.length - 1]?.close} stroke="hsl(var(--primary))" strokeDasharray="2 2" />
          </ComposedChart>
        </ResponsiveContainer>
        <div className="mt-2 text-xs text-muted-foreground flex items-center justify-between">
          <span>
            O: ${data[data.length - 1]?.open.toFixed(2)} | 
            H: ${Math.max(...data.map(d => d.high)).toFixed(2)} | 
            L: ${Math.min(...data.map(d => d.low)).toFixed(2)} | 
            C: ${data[data.length - 1]?.close.toFixed(2)}
          </span>
          <span>
            {timeframe === '1D' ? `${days} days` : timeframe === '1H' ? `${days * 24} hours` : `${days * 24 * 4} candles`}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
