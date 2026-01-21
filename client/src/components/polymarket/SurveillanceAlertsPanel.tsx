/**
 * Polymarket Surveillance Alerts panel.
 * Fetches /api/polymarket/surveillance/alerts. On 403, shows upgrade CTA only (no alerts table).
 * Supports severity/reviewed filters, Run cycle, and Review (dismissed|escalated|false_positive).
 */

import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { fetchWithAuth } from '@/context/AuthContext';
import { Loader2, ShieldAlert, ArrowUpCircle, Play, CheckCircle } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface AlertRow {
  id: number;
  alert_type: string;
  severity: string;
  condition_id?: string | null;
  proxy_wallet?: string | null;
  message: string;
  signal_values?: Record<string, unknown> | null;
  created_at: string;
  reviewed_at?: string | null;
  resolution?: string | null;
}

export function SurveillanceAlertsPanel() {
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [subscriptionRequired, setSubscriptionRequired] = useState(false);
  const [upgradeUrl, setUpgradeUrl] = useState<string>('/subscriptions');
  const [severity, setSeverity] = useState<string>('');
  const [reviewed, setReviewed] = useState<string>('all');
  const [runCycleLoading, setRunCycleLoading] = useState(false);
  const [reviewingId, setReviewingId] = useState<number | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    setSubscriptionRequired(false);
    const params = new URLSearchParams();
    if (severity) params.set('severity', severity);
    if (reviewed === 'yes') params.set('reviewed', 'true');
    if (reviewed === 'no') params.set('reviewed', 'false');
    params.set('limit', '50');
    fetchWithAuth(`/api/polymarket/surveillance/alerts?${params.toString()}`)
      .then((res) => {
        if (res.status === 403) {
          setSubscriptionRequired(true);
          const h = res.headers.get('X-Upgrade-Url');
          if (h) setUpgradeUrl(h);
          return res.json().catch(() => ({})).then((body: { detail?: { upgrade_url?: string } }) => {
            const u = typeof body?.detail === 'object' && body?.detail?.upgrade_url
              ? body.detail.upgrade_url
              : null;
            if (u) setUpgradeUrl(u);
            return null as unknown as AlertRow[];
          });
        }
        if (!res.ok) throw new Error('Failed to load surveillance alerts');
        return res.json();
      })
      .then((data) => {
        if (data != null && Array.isArray(data)) setAlerts(data);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : 'Failed to load');
      })
      .finally(() => setLoading(false));
  }, [severity, reviewed]);

  useEffect(() => { load(); }, [load]);

  const runCycle = async () => {
    setRunCycleLoading(true);
    setError(null);
    try {
      const res = await fetchWithAuth('/api/polymarket/surveillance/run-cycle', { method: 'POST' });
      if (res.status === 403) {
        setSubscriptionRequired(true);
        return;
      }
      if (!res.ok) throw new Error('Run cycle failed');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Run cycle failed');
    } finally {
      setRunCycleLoading(false);
    }
  };

  const reviewAlert = async (id: number, resolution: string) => {
    setReviewingId(id);
    setError(null);
    try {
      const res = await fetchWithAuth(`/api/polymarket/surveillance/alerts/${id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolution }),
      });
      if (!res.ok) throw new Error('Review failed');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Review failed');
    } finally {
      setReviewingId(null);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8 flex items-center justify-center gap-2">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Loading surveillance…</span>
        </CardContent>
      </Card>
    );
  }

  if (subscriptionRequired) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldAlert className="h-5 w-5" />
            Market intelligence
          </CardTitle>
          <CardDescription>
            Market intelligence requires a Pro subscription. Upgrade to view alerts, run detection cycles, and access surveillance signals.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link to={upgradeUrl.startsWith('/api/') ? '/subscriptions' : upgradeUrl} className="inline-flex items-center gap-2">
              <ArrowUpCircle className="h-4 w-4" />
              Upgrade to Pro
            </Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive">
        <CardContent className="pt-6">
          <p className="text-destructive">{error}</p>
          <Button variant="outline" size="sm" className="mt-2" onClick={load}>Retry</Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Surveillance alerts</CardTitle>
        <CardDescription>Alerts from the Polymarket surveillance detection cycle.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Select className="w-[120px]" value={severity || 'all'} onValueChange={(v) => setSeverity(v === 'all' ? '' : v)}>
            <SelectTrigger>
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severity</SelectItem>
              <SelectItem value="low">Low</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
            </SelectContent>
          </Select>
          <Select className="w-[130px]" value={reviewed} onValueChange={setReviewed}>
            <SelectTrigger>
              <SelectValue placeholder="Reviewed" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="yes">Reviewed</SelectItem>
              <SelectItem value="no">Not reviewed</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>Refresh</Button>
          <Button size="sm" onClick={runCycle} disabled={runCycleLoading}>
            {runCycleLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            <span className="ml-1">Run cycle</span>
          </Button>
        </div>
        {alerts.length === 0 ? (
          <p className="text-muted-foreground text-sm">No alerts. Run a detection cycle to populate.</p>
        ) : (
          <div className="rounded border divide-y max-h-64 overflow-y-auto">
            {alerts.map((a) => (
              <div key={a.id} className="p-3 text-sm flex items-start justify-between gap-2">
                <div>
                  <div className="font-medium">{a.alert_type}</div>
                  <div className="text-muted-foreground">{a.message}</div>
                  <div className="text-xs mt-1">
                    Severity: {a.severity} · {a.created_at}
                    {a.reviewed_at && a.resolution && (
                      <span className="ml-1">· <CheckCircle className="inline h-3 w-3" /> {a.resolution}</span>
                    )}
                  </div>
                </div>
                {!a.reviewed_at && (
                  <div className="flex items-center gap-1 shrink-0">
                    <Select className="w-[130px] h-8" onValueChange={(r) => reviewAlert(a.id, r)} disabled={reviewingId === a.id}>
                      <SelectTrigger>
                        <SelectValue placeholder="Review" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="dismissed">Dismissed</SelectItem>
                        <SelectItem value="escalated">Escalated</SelectItem>
                        <SelectItem value="false_positive">False positive</SelectItem>
                      </SelectContent>
                    </Select>
                    {reviewingId === a.id && <Loader2 className="h-4 w-4 animate-spin" />}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
