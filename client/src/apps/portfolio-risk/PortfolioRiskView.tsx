/**
 * Portfolio Risk Analysis – asset-class allocation, risk metrics, recommendations (Trading Phase 5).
 * Premium feature: requires Pro, Premium, or Lifetime subscription.
 */

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { fetchWithAuth } from '@/context/AuthContext';
import { PermissionGate } from '@/components/PermissionGate';
import { PERMISSION_TRADE_VIEW } from '@/utils/permissions';
import { BarChart2, Loader2, TrendingUp, AlertCircle } from 'lucide-react';

interface RiskMetrics {
  sharpe_ratio: number | null;
  beta: number | null;
  var_95: number | null;
  max_drawdown: number | null;
}

interface RiskAnalysis {
  asset_class_allocation: Record<string, number>;
  sector_exposure: Record<string, number>;
  country_exposure: Record<string, number>;
  currency_exposure: Record<string, number>;
  risk_metrics: RiskMetrics;
  recommendations: string[];
  total_equity: number;
}

export function PortfolioRiskView() {
  const [data, setData] = useState<RiskAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgradeRequired, setUpgradeRequired] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setUpgradeRequired(false);
    fetchWithAuth('/api/portfolio/risk-analysis')
      .then((res) => {
        if (cancelled) return;
        if (res.status === 403) {
          try {
            return res.json().then((j: { detail?: string }) => {
              if (j?.detail?.toLowerCase().includes('subscription') || j?.detail?.toLowerCase().includes('pro') || j?.detail?.toLowerCase().includes('premium')) {
                setUpgradeRequired(true);
              }
              return null;
            });
          } catch {
            setUpgradeRequired(true);
            return null;
          }
        }
        if (!res.ok) return null;
        return res.json();
      })
      .then((json) => {
        if (!cancelled && json) setData(json);
      })
      .catch(() => {
        if (!cancelled) setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const fmt = (v: number) => (v * 100).toFixed(1) + '%';
  const num = (v: number | null) => (v != null ? v.toFixed(2) : '—');

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Risk analysis</h2>
        <p className="text-muted-foreground">
          Asset-class allocation, risk metrics, and diversification recommendations. Available on Pro, Premium, or Lifetime.
        </p>
      </div>

      <PermissionGate permission={PERMISSION_TRADE_VIEW}>
        {loading ? (
          <Card className="border-slate-700 bg-slate-800/50">
            <CardContent className="p-8 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
            </CardContent>
          </Card>
        ) : upgradeRequired ? (
          <Card className="border-amber-700/50 bg-amber-900/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg text-amber-400">
                <AlertCircle className="h-5 w-5" />
                Premium feature
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                Upgrade to Pro, Premium, or Lifetime to view risk analysis and diversification insights.
              </p>
            </CardContent>
          </Card>
        ) : data ? (
          <>
            <Card className="border-slate-700 bg-slate-800/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <BarChart2 className="h-5 w-5 text-cyan-400" />
                  Asset-class allocation
                </CardTitle>
                <p className="text-sm text-muted-foreground">Total equity: {data.total_equity.toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {Object.entries(data.asset_class_allocation)
                    .filter(([, p]) => p > 0)
                    .sort((a, b) => b[1] - a[1])
                    .map(([k, p]) => (
                      <li key={k} className="flex items-center justify-between py-2 border-b border-slate-700/50 last:border-0">
                        <span className="capitalize font-medium">{k.replace(/_/g, ' ')}</span>
                        <span className="font-mono text-emerald-400">{fmt(p)}</span>
                      </li>
                    ))}
                </ul>
                {Object.values(data.asset_class_allocation).every((p) => p === 0) && (
                  <p className="text-muted-foreground">Add positions or manual assets to see allocation.</p>
                )}
              </CardContent>
            </Card>

            <Card className="border-slate-700 bg-slate-800/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <TrendingUp className="h-5 w-5 text-amber-400" />
                  Risk metrics
                </CardTitle>
                <p className="text-sm text-muted-foreground">Requires return history to compute (currently stubbed).</p>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div><span className="text-muted-foreground text-sm">Sharpe</span><p className="font-mono">{num(data.risk_metrics.sharpe_ratio)}</p></div>
                  <div><span className="text-muted-foreground text-sm">Beta</span><p className="font-mono">{num(data.risk_metrics.beta)}</p></div>
                  <div><span className="text-muted-foreground text-sm">VaR (95%)</span><p className="font-mono">{num(data.risk_metrics.var_95)}</p></div>
                  <div><span className="text-muted-foreground text-sm">Max drawdown</span><p className="font-mono">{num(data.risk_metrics.max_drawdown)}</p></div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-700 bg-slate-800/50">
              <CardHeader>
                <CardTitle className="text-lg">Recommendations</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {data.recommendations.map((r, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-cyan-400 mt-0.5">•</span>
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </>
        ) : (
          <Card className="border-slate-700 bg-slate-800/50">
            <CardContent className="p-8">
              <p className="text-muted-foreground">Unable to load risk analysis.</p>
            </CardContent>
          </Card>
        )}
      </PermissionGate>
    </div>
  );
}
