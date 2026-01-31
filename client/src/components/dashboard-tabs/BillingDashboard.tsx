/**
 * Billing Dashboard (Phase 10): Overview, Org Costs, Role Costs, History, Invoices.
 * Fetches /api/billing/periods, /api/billing/invoices and aggregate endpoints.
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { fetchWithAuth } from '@/context/AuthContext';
import { Loader2, DollarSign, Building2, Users, FileText, History } from 'lucide-react';

interface BillingPeriod {
  id: number;
  period_type: string;
  period_start: string;
  period_end: string;
  organization_id: number | null;
  user_id: number | null;
  total_cost: number;
  subscription_cost: number;
  usage_cost: number;
  commission_revenue: number;
  credit_usage: number;
  payment_cost: number;
  currency: string;
  status: string;
  invoice_id: number | null;
  created_at: string;
  updated_at: string;
}

interface Invoice {
  id: number;
  invoice_number: string;
  invoice_date: string;
  due_date: string;
  organization_id: number | null;
  user_id: number | null;
  subtotal: number;
  tax: number;
  total: number;
  currency: string;
  status: string;
  paid_at: string | null;
  created_at: string;
  updated_at: string;
}

interface OrgAggregate {
  organization_id: number | null;
  total: number;
}

interface RoleAggregate {
  user_role: string | null;
  total: number;
}

export function BillingDashboard() {
  const [activeTab, setActiveTab] = useState('overview');
  const [periods, setPeriods] = useState<BillingPeriod[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [selectedPeriodId, setSelectedPeriodId] = useState<number | null>(null);
  const [orgCosts, setOrgCosts] = useState<OrgAggregate[]>([]);
  const [roleCosts, setRoleCosts] = useState<RoleAggregate[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingAggregate, setLoadingAggregate] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPeriods = useCallback(async () => {
    try {
      const res = await fetchWithAuth('/api/billing/periods?limit=20');
      if (!res.ok) throw new Error('Failed to load periods');
      const data = await res.json();
      setPeriods(Array.isArray(data) ? data : []);
      if (!selectedPeriodId && Array.isArray(data) && data.length > 0) {
        setSelectedPeriodId((data as BillingPeriod[])[0].id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load periods');
      setPeriods([]);
    }
  }, [selectedPeriodId]);

  const loadInvoices = useCallback(async () => {
    try {
      const res = await fetchWithAuth('/api/billing/invoices?limit=20');
      if (!res.ok) throw new Error('Failed to load invoices');
      const data = await res.json();
      setInvoices(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load invoices');
      setInvoices([]);
    }
  }, []);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    await Promise.all([loadPeriods(), loadInvoices()]);
    setLoading(false);
  }, [loadPeriods, loadInvoices]);

  const loadOrgCosts = useCallback(async () => {
    if (!selectedPeriodId) return;
    setLoadingAggregate(true);
    try {
      const res = await fetchWithAuth(`/api/billing/periods/${selectedPeriodId}/aggregate-by-organization`);
      if (!res.ok) throw new Error('Failed to load org costs');
      const data = await res.json();
      setOrgCosts(Array.isArray(data) ? data : []);
    } catch (e) {
      setOrgCosts([]);
    } finally {
      setLoadingAggregate(false);
    }
  }, [selectedPeriodId]);

  const loadRoleCosts = useCallback(async () => {
    if (!selectedPeriodId) return;
    setLoadingAggregate(true);
    try {
      const res = await fetchWithAuth(`/api/billing/periods/${selectedPeriodId}/aggregate-by-role`);
      if (!res.ok) throw new Error('Failed to load role costs');
      const data = await res.json();
      setRoleCosts(Array.isArray(data) ? data : []);
    } catch (e) {
      setRoleCosts([]);
    } finally {
      setLoadingAggregate(false);
    }
  }, [selectedPeriodId]);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  useEffect(() => {
    if (activeTab === 'org-costs') loadOrgCosts();
  }, [activeTab, selectedPeriodId, loadOrgCosts]);

  useEffect(() => {
    if (activeTab === 'role-costs') loadRoleCosts();
  }, [activeTab, selectedPeriodId, loadRoleCosts]);

  const formatDate = (s: string) => (s ? new Date(s).toLocaleDateString() : '—');
  const formatCurrency = (n: number, currency = 'USD') =>
    new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(n);

  return (
    <div className="p-6 space-y-6 flex flex-col h-full overflow-hidden">
      <div>
        <h2 className="text-2xl font-bold mb-2 text-slate-100">Billing Dashboard</h2>
        <p className="text-muted-foreground max-w-2xl text-sm">
          View billing periods, cost allocations by organization and role, and invoices.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
        <TabsList className="bg-slate-900 border-slate-800 self-start">
          <TabsTrigger value="overview" className="data-[state=active]:bg-slate-800">
            Overview
          </TabsTrigger>
          <TabsTrigger value="org-costs" className="data-[state=active]:bg-slate-800">
            Org Costs
          </TabsTrigger>
          <TabsTrigger value="role-costs" className="data-[state=active]:bg-slate-800">
            Role Costs
          </TabsTrigger>
          <TabsTrigger value="history" className="data-[state=active]:bg-slate-800">
            History
          </TabsTrigger>
          <TabsTrigger value="invoices" className="data-[state=active]:bg-slate-800">
            Invoices
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="flex-1 overflow-auto mt-4 bg-slate-950/20 rounded-xl border border-slate-800/50 p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
          ) : error ? (
            <p className="text-destructive">{error}</p>
          ) : (
            <div className="grid gap-6 md:grid-cols-2">
              <Card className="bg-slate-900/50 border-slate-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <History className="h-4 w-4" />
                    Recent periods
                  </CardTitle>
                  <CardDescription>Latest billing periods</CardDescription>
                </CardHeader>
                <CardContent>
                  {periods.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No billing periods yet.</p>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {periods.slice(0, 5).map((p) => (
                        <li key={p.id} className="flex justify-between">
                          <span>
                            {formatDate(p.period_start)} – {formatDate(p.period_end)} ({p.period_type})
                          </span>
                          <span>{formatCurrency(p.total_cost, p.currency)}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>
              <Card className="bg-slate-900/50 border-slate-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Recent invoices
                  </CardTitle>
                  <CardDescription>Latest invoices</CardDescription>
                </CardHeader>
                <CardContent>
                  {invoices.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No invoices yet.</p>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {invoices.slice(0, 5).map((inv) => (
                        <li key={inv.id} className="flex justify-between">
                          <span>
                            {inv.invoice_number} – {formatDate(inv.invoice_date)}
                          </span>
                          <span className={inv.status === 'paid' ? 'text-emerald-400' : ''}>
                            {formatCurrency(inv.total, inv.currency)} ({inv.status})
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="org-costs" className="flex-1 overflow-auto mt-4 bg-slate-950/20 rounded-xl border border-slate-800/50 p-6">
          <div className="flex items-center gap-4 mb-4">
            <label className="text-sm text-muted-foreground">Period</label>
            <select
              className="bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-100"
              value={selectedPeriodId ?? ''}
              onChange={(e) => setSelectedPeriodId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Select period</option>
              {periods.map((p) => (
                <option key={p.id} value={p.id}>
                  {formatDate(p.period_start)} – {formatDate(p.period_end)}
                </option>
              ))}
            </select>
            <Button variant="outline" size="sm" onClick={loadOrgCosts} disabled={loadingAggregate || !selectedPeriodId}>
              {loadingAggregate ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Refresh'}
            </Button>
          </div>
          {loadingAggregate ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
            </div>
          ) : (
            <Card className="bg-slate-900/50 border-slate-800">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Building2 className="h-4 w-4" />
                  Cost by organization
                </CardTitle>
              </CardHeader>
              <CardContent>
                {orgCosts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No allocations for this period.</p>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {orgCosts.map((row, i) => (
                      <li key={i} className="flex justify-between">
                        <span>Org {row.organization_id ?? '—'}</span>
                        <span>{formatCurrency(row.total)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="role-costs" className="flex-1 overflow-auto mt-4 bg-slate-950/20 rounded-xl border border-slate-800/50 p-6">
          <div className="flex items-center gap-4 mb-4">
            <label className="text-sm text-muted-foreground">Period</label>
            <select
              className="bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-100"
              value={selectedPeriodId ?? ''}
              onChange={(e) => setSelectedPeriodId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Select period</option>
              {periods.map((p) => (
                <option key={p.id} value={p.id}>
                  {formatDate(p.period_start)} – {formatDate(p.period_end)}
                </option>
              ))}
            </select>
            <Button variant="outline" size="sm" onClick={loadRoleCosts} disabled={loadingAggregate || !selectedPeriodId}>
              {loadingAggregate ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Refresh'}
            </Button>
          </div>
          {loadingAggregate ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
            </div>
          ) : (
            <Card className="bg-slate-900/50 border-slate-800">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Cost by role
                </CardTitle>
              </CardHeader>
              <CardContent>
                {roleCosts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No allocations for this period.</p>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {roleCosts.map((row, i) => (
                      <li key={i} className="flex justify-between">
                        <span>{row.user_role ?? '—'}</span>
                        <span>{formatCurrency(row.total)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="history" className="flex-1 overflow-auto mt-4 bg-slate-950/20 rounded-xl border border-slate-800/50 p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
          ) : (
            <Card className="bg-slate-900/50 border-slate-800">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Billing periods</CardTitle>
                <CardDescription>All billing periods you have access to</CardDescription>
              </CardHeader>
              <CardContent>
                {periods.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No billing periods yet.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-700 text-left text-muted-foreground">
                          <th className="pb-2 pr-4">Period</th>
                          <th className="pb-2 pr-4">Type</th>
                          <th className="pb-2 pr-4">Total cost</th>
                          <th className="pb-2">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {periods.map((p) => (
                          <tr key={p.id} className="border-b border-slate-800/50">
                            <td className="py-2 pr-4">
                              {formatDate(p.period_start)} – {formatDate(p.period_end)}
                            </td>
                            <td className="py-2 pr-4">{p.period_type}</td>
                            <td className="py-2 pr-4">{formatCurrency(p.total_cost, p.currency)}</td>
                            <td className="py-2">{p.status}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="invoices" className="flex-1 overflow-auto mt-4 bg-slate-950/20 rounded-xl border border-slate-800/50 p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
          ) : (
            <Card className="bg-slate-900/50 border-slate-800">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Invoices</CardTitle>
                <CardDescription>All invoices you have access to</CardDescription>
              </CardHeader>
              <CardContent>
                {invoices.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No invoices yet.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-700 text-left text-muted-foreground">
                          <th className="pb-2 pr-4">Number</th>
                          <th className="pb-2 pr-4">Date</th>
                          <th className="pb-2 pr-4">Due</th>
                          <th className="pb-2 pr-4">Total</th>
                          <th className="pb-2">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {invoices.map((inv) => (
                          <tr key={inv.id} className="border-b border-slate-800/50">
                            <td className="py-2 pr-4">{inv.invoice_number}</td>
                            <td className="py-2 pr-4">{formatDate(inv.invoice_date)}</td>
                            <td className="py-2 pr-4">{formatDate(inv.due_date)}</td>
                            <td className="py-2 pr-4">{formatCurrency(inv.total, inv.currency)}</td>
                            <td className="py-2">
                              <span className={inv.status === 'paid' ? 'text-emerald-400' : ''}>{inv.status}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
