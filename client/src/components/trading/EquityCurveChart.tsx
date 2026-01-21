/**
 * Equity curve chart for backtest results.
 * Renders a simple SVG line from equity_curve data.
 */

interface EquityCurveChartProps {
  equityCurve: number[];
  title?: string;
  height?: number;
  initialCapital?: number;
}

export function EquityCurveChart({
  equityCurve,
  title = 'Equity curve',
  height = 200,
  initialCapital,
}: EquityCurveChartProps) {
  if (!equityCurve || equityCurve.length === 0) {
    return (
      <div
        className="rounded border bg-muted/30 flex items-center justify-center text-muted-foreground text-sm"
        style={{ height }}
      >
        No equity data
      </div>
    );
  }

  const min = Math.min(...equityCurve);
  const max = Math.max(...equityCurve);
  const range = max - min || 1;
  const padding = { top: 8, right: 8, bottom: 24, left: 48 };
  const w = 400;
  const h = height - padding.top - padding.bottom;
  const points = equityCurve.map((v, i) => {
    const x = padding.left + (i / Math.max(1, equityCurve.length - 1)) * (w - padding.left - padding.right);
    const y = padding.top + h - ((v - min) / range) * h;
    return `${x},${y}`;
  });
  const path = `M ${points.join(' L ')}`;
  const start = equityCurve[0];
  const end = equityCurve[equityCurve.length - 1];
  const isPositive = end >= (initialCapital ?? start);
  const bottomY = padding.top + h;
  const [x0] = points[0].split(',').map(Number);
  const [xN] = points[points.length - 1].split(',').map(Number);
  const areaPath = `${path} L ${xN},${bottomY} L ${x0},${bottomY} Z`;
  const strokeColor = isPositive ? 'hsl(142 76% 36%)' : 'hsl(0 84% 60%)';

  return (
    <div className="space-y-1">
      {title && <p className="text-sm font-medium text-muted-foreground">{title}</p>}
      <div className="rounded border bg-muted/20 overflow-x-auto" style={{ minHeight: height }}>
        <svg width={w} height={height} className="min-w-full">
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="1" x2="0" y2="0">
              <stop offset="0%" stopColor={strokeColor} stopOpacity="0.25" />
              <stop offset="100%" stopColor={strokeColor} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={areaPath} fill="url(#equityGradient)" />
          <path
            d={path}
            fill="none"
            stroke={strokeColor}
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* y-axis labels */}
          <text x={padding.left - 4} y={padding.top + 4} textAnchor="end" className="fill-muted-foreground" fontSize="10">
            {max.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </text>
          <text x={padding.left - 4} y={height - padding.bottom + 4} textAnchor="end" className="fill-muted-foreground" fontSize="10">
            {min.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </text>
        </svg>
      </div>
      <p className="text-xs text-muted-foreground">
        {equityCurve.length} bars · Start: {start.toLocaleString(undefined, { maximumFractionDigits: 2 })} → End:{' '}
        {end.toLocaleString(undefined, { maximumFractionDigits: 2 })}
        {initialCapital != null && ` (initial: ${initialCapital.toLocaleString(undefined, { maximumFractionDigits: 0 })})`}
      </p>
    </div>
  );
}
