/**
 * Asset Alerts – upcoming maturity and amortization payments, and alert list (Trading Phase 3).
 */

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { fetchWithAuth } from '@/context/AuthContext';
import { PermissionGate } from '@/components/PermissionGate';
import { PERMISSION_TRADE_VIEW } from '@/utils/permissions';
import { Bell, Calendar, Loader2 } from 'lucide-react';

interface UpcomingPayment {
  asset_id: number;
  due_date: string;
  days_until: number;
  type: string;
  amount: number;
  message: string;
}

interface AssetAlertRow {
  id: number;
  asset_id: number;
  alert_type: string;
  trigger_date: string | null;
  trigger_price: number | null;
  message: string;
  is_active: boolean;
  notified: boolean;
  notified_at: string | null;
  created_at: string;
}

export function AssetAlertsView() {
  const [payments, setPayments] = useState<UpcomingPayment[]>([]);
  const [alerts, setAlerts] = useState<AssetAlertRow[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [pRes, aRes] = await Promise.all([
        fetchWithAuth('/api/assets/upcoming-payments?days_ahead=60'),
        fetchWithAuth('/api/assets/alerts?active_only=true'),
      ]);
      if (pRes.ok) setPayments(await pRes.json());
      if (aRes.ok) setAlerts(await aRes.json());
    } catch (e) {
      console.error('Failed to load asset alerts:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Asset alerts</h2>
        <p className="text-muted-foreground">Upcoming maturities and amortization payments for your manual assets.</p>
      </div>

      <PermissionGate permission={PERMISSION_TRADE_VIEW}>
        {loading ? (
          <Card className="border-slate-700 bg-slate-800/50">
            <CardContent className="p-8 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
            </CardContent>
          </Card>
        ) : (
          <>
            <Card className="border-slate-700 bg-slate-800/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Calendar className="h-5 w-5 text-amber-400" />
                  Upcoming payments (60 days)
                </CardTitle>
              </CardHeader>
              <CardContent>
                {payments.length === 0 ? (
                  <p className="text-muted-foreground">No upcoming maturity or amortization payments.</p>
                ) : (
                  <ul className="space-y-2">
                    {payments.map((p, i) => (
                      <li key={`${p.asset_id}-${p.due_date}-${i}`} className="flex items-center justify-between py-2 border-b border-slate-700/50 last:border-0">
                        <div>
                          <span className="font-medium">{p.message}</span>
                          <span className="text-muted-foreground text-sm ml-2">{p.due_date} (in {p.days_until} days)</span>
                        </div>
                        <span className="font-mono text-emerald-400">{typeof p.amount === 'number' ? p.amount.toLocaleString(undefined, { minimumFractionDigits: 2 }) : p.amount}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card className="border-slate-700 bg-slate-800/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Bell className="h-5 w-5 text-cyan-400" />
                  Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                {alerts.length === 0 ? (
                  <p className="text-muted-foreground">No active alerts.</p>
                ) : (
                  <ul className="space-y-2">
                    {alerts.map((a) => (
                      <li key={a.id} className="flex items-center justify-between py-2 border-b border-slate-700/50 last:border-0">
                        <div>
                          <span className="font-medium">{a.message}</span>
                          {a.trigger_date && <span className="text-muted-foreground text-sm ml-2">{a.trigger_date}</span>}
                          {a.notified && <span className="text-slate-500 text-xs ml-2">notified</span>}
                        </div>
                        <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300">{a.alert_type}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </PermissionGate>
    </div>
  );
}
