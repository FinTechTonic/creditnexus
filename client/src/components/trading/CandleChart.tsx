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

/** Optional prediction overlay: forecast values (e.g. from Chronos) aligned to future bars */
export interface PredictionOverlay {
  values: number[];
  label?: string;
}

/** Optional backtest overlay: entry/exit markers */
export interface BacktestSignal {
  date: string;
  action: 'buy' | 'sell';
  price: number;
}

interface CandleChartProps {
  symbol: string;
  timeframe?: '1D' | '1H' | '15Min';
  days?: number;
  height?: number;
  /** Prediction overlay: forecast line (values aligned to candle count) */
  predictionOverlay?: PredictionOverlay;
  /** Backtest overlay: buy/sell markers on the chart */
  backtestSignals?: BacktestSignal[];
}

export function CandleChart({ 
  symbol, 
  timeframe = '1D', 
  days = 30,
  height = 400,
  predictionOverlay,
  backtestSignals = [],
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
  const baseChartData = data.map((d) => ({
    ...d,
    date: new Date(d.timestamp).toLocaleDateString(),
    dateKey: d.timestamp,
    bodyTop: Math.max(d.open, d.close),
    bodyBottom: Math.min(d.open, d.close),
    isUp: d.close >= d.open,
  }));

  // Merge prediction overlay: align forecast values to trailing candles + future points
  const forecastValues = predictionOverlay?.values ?? [];
  const chartData = baseChartData.map((row, i) => {
    const forecastIdx = i - (baseChartData.length - forecastValues.length);
    const forecastVal = forecastIdx >= 0 && forecastIdx < forecastValues.length ? forecastValues[forecastIdx] : undefined;
    return { ...row, forecast: forecastVal };
  });
  // Append future forecast points if we have more forecast than history (e.g. next 5 days)
  const extraForecast = forecastValues.length > baseChartData.length
    ? forecastValues.slice(baseChartData.length).map((val, i) => ({
        date: `+${i + 1}`,
        dateKey: `future-${i}`,
        close: val,
        forecast: val,
        high: val,
        low: val,
        open: chartData[chartData.length - 1]?.close ?? val,
        volume: 0,
        bodyTop: val,
        bodyBottom: val,
        isUp: true,
      }))
    : [];
  const chartDataWithForecast = extraForecast.length ? [...chartData, ...extraForecast] : chartData;

  // Backtest signals: add signalBuy/signalSell per row for dot overlay
  const normalizeDate = (d: string) => d.split('T')[0] || d;
  const finalChartData = chartDataWithForecast.map((row) => {
    const rowDate = normalizeDate(row.dateKey || row.date);
    const buys = backtestSignals.filter((s) => normalizeDate(s.date) === rowDate && s.action === 'buy');
    const sells = backtestSignals.filter((s) => normalizeDate(s.date) === rowDate && s.action === 'sell');
    return {
      ...row,
      signalBuy: buys.length ? buys[0].price : undefined,
      signalSell: sells.length ? sells[0].price : undefined,
    };
  });

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center justify-between">
          <span>{symbol} - {timeframe}</span>
          <span className="text-xs text-muted-foreground font-normal">
            {data.length} candles
            {predictionOverlay && ' · forecast'}
            {backtestSignals.length > 0 && ` · ${backtestSignals.length} signals`}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={height - 80}>
          <ComposedChart data={finalChartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
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
            {predictionOverlay && forecastValues.length > 0 && (
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="forecast"
                stroke="hsl(var(--chart-2))"
                strokeWidth={1.5}
                strokeDasharray="4 2"
                dot={false}
                connectNulls
                name={predictionOverlay.label ?? 'Forecast'}
              />
            )}
            {backtestSignals.length > 0 && (
              <>
                <Line
                  yAxisId="price"
                  type="monotone"
                  dataKey="signalBuy"
                  stroke="none"
                  dot={{ fill: 'hsl(142 76% 36%)', r: 4 }}
                  connectNulls
                  name="Buy"
                />
                <Line
                  yAxisId="price"
                  type="monotone"
                  dataKey="signalSell"
                  stroke="none"
                  dot={{ fill: 'hsl(0 84% 60%)', r: 4 }}
                  connectNulls
                  name="Sell"
                />
              </>
            )}
            <ReferenceLine yAxisId="price" y={data[data.length - 1]?.close} stroke="hsl(var(--primary))" strokeDasharray="2 2" />
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
