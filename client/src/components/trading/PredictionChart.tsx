/**
 * Simple chart for forecast array (e.g. from Chronos or technical strategy).
 */

interface PredictionChartProps {
  forecast: number[];
  title?: string;
  height?: number;
}

export function PredictionChart({ forecast, title = 'Forecast', height = 160 }: PredictionChartProps) {
  if (!forecast || forecast.length === 0) {
    return (
      <div className="rounded border bg-muted/30 flex items-center justify-center text-muted-foreground text-sm" style={{ height }}>
        No forecast data
      </div>
    );
  }

  const min = Math.min(...forecast);
  const max = Math.max(...forecast);
  const range = max - min || 1;
  const h = height - 24;

  return (
    <div className="space-y-1">
      {title && <p className="text-sm font-medium text-muted-foreground">{title}</p>}
      <div
        className="rounded border bg-muted/20 overflow-hidden flex items-end gap-px"
        style={{ height: h, minWidth: 120 }}
      >
        {forecast.map((v, i) => {
          const pct = ((v - min) / range) * 100;
          return (
            <div
              key={i}
              className="flex-1 min-w-[2px] bg-primary/70 rounded-t transition-opacity hover:opacity-90"
              style={{ height: `${Math.max(4, pct)}%` }}
              title={`Step ${i + 1}: ${v.toFixed(2)}`}
            />
          );
        })}
      </div>
      <p className="text-xs text-muted-foreground">
        {forecast.length} steps · range {min.toFixed(2)} – {max.toFixed(2)}
      </p>
    </div>
  );
}
