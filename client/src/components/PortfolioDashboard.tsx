/**
 * Portfolio Dashboard: aggregated view from /api/portfolio/overview
 * (trading + bank + manual assets). Uses /ws/trading/{user_id} for live updates.
 * Enhanced to show transactions, investments, and liabilities from aggregation API.
 */

import { useState, useEffect, useCallback } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { fetchWithAuth, useAuth } from '@/context/AuthContext';
import { useTradingWebSocket } from '@/hooks/useTradingWebSocket';
import { useFDC3, type PortfolioContext } from '@/context/FDC3Context';
import { DollarSign, Loader2, TrendingUp, TrendingDown, Wallet, Building2, PiggyBank, ArrowLeftRight, PieChart, FileText } from 'lucide-react';
import { UnifiedGraphs } from '@/components/UnifiedGraphs';

interface Overview {
  total_equity: number;
  bank_balances: number;
  trading_equity: number;
  manual_assets_value: number;
  unrealized_pl: number;
  buying_power: number;
  positions: Array<{
    symbol?: string;
    quantity?: number;
    average_price?: number;
    current_price?: number;
    market_value?: number;
    unrealized_pl?: number;
  }>;
  account_info?: Record<string, unknown>;
}

interface Transaction {
  transaction_id?: string;
  account_id?: string;
  amount?: number;
  date?: string;
  name?: string;
  merchant_name?: string;
  category?: string[];
  type?: string;
}

interface InvestmentPosition {
  symbol?: string;
  quantity?: number;
  average_price?: number;
  current_price?: number;
  market_value?: number;
  unrealized_pl?: number;
}

interface Liabilities {
  credit?: Array<Record<string, unknown>>;
  mortgage?: Array<Record<string, unknown>>;
  student?: Array<Record<string, unknown>>;
}

export function PortfolioDashboard() {
  const { user } = useAuth();
  const { context } = useFDC3();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [investments, setInvestments] = useState<InvestmentPosition[]>([]);
  const [liabilities, setLiabilities] = useState<Liabilities>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refetch, setRefetch] = useState(0);
  const [activeTab, setActiveTab] = useState('overview');
  const [brokerageStatus, setBrokerageStatus] = useState<{ has_account: boolean; status?: string; account_number?: string } | null>(null);

  // Listen for FDC3 portfolio context updates
  useEffect(() => {
    if (context?.type === 'finos.creditnexus.portfolio') {
      // Portfolio context received - trigger refresh
      setRefetch((r) => r + 1);
    }
  }, [context]);

  const loadOverview = useCallback(async () => {
    try {
      const res = await fetchWithAuth('/api/portfolio/overview', { method: 'GET' });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.detail || e.message || `HTTP ${res.status}`);
      }
      setOverview(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load portfolio');
      setOverview(null);
    }
  }, []);

  const loadTransactions = useCallback(async () => {
    try {
      const res = await fetchWithAuth('/api/portfolio/transactions?days=30', { method: 'GET' });
      if (res.ok) {
        const data = await res.json();
        setTransactions(data.transactions || []);
      }
    } catch (e) {
      // Non-critical: transactions may not be available
      console.warn('Failed to load transactions:', e);
    }
  }, []);

  const loadInvestments = useCallback(async () => {
    try {
      const res = await fetchWithAuth('/api/portfolio/investments', { method: 'GET' });
      if (res.ok) {
        const data = await res.json();
        setInvestments(data.positions || []);
      }
    } catch (e) {
      // Non-critical: investments may not be available
      console.warn('Failed to load investments:', e);
    }
  }, []);

  const loadLiabilities = useCallback(async () => {
    try {
      const res = await fetchWithAuth('/api/portfolio/liabilities', { method: 'GET' });
      if (res.ok) {
        const data = await res.json();
        setLiabilities(data.liabilities || {});
      }
    } catch (e) {
      // Non-critical: liabilities may not be available
      console.warn('Failed to load liabilities:', e);
    }
  }, []);

  const loadBrokerageStatus = useCallback(async () => {
    try {
      const res = await fetchWithAuth('/api/brokerage/account/status', { method: 'GET' });
      if (res.ok) {
        const d = await res.json();
        setBrokerageStatus(d);
      } else {
        setBrokerageStatus(null);
      }
    } catch {
      setBrokerageStatus(null);
    }
  }, []);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    await Promise.all([
      loadOverview(),
      loadTransactions(),
      loadInvestments(),
      loadLiabilities(),
      loadBrokerageStatus(),
    ]);
    setLoading(false);
  }, [loadOverview, loadTransactions, loadInvestments, loadLiabilities, loadBrokerageStatus]);

  useTradingWebSocket(user?.id ?? null, () => setRefetch((r) => r + 1));
  useEffect(() => { loadAll(); }, [loadAll, refetch]);

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">{error || 'No portfolio data'}</p>
      </div>
    );
  }

  const u = overview?.unrealized_pl ?? 0;
  const fmt = (n: number) => `$${Number(n).toFixed(2)}`;
  const fmtDate = (d: string) => new Date(d).toLocaleDateString();

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Portfolio</h2>
        <p className="text-muted-foreground">Aggregated trading, bank, and manual assets</p>
        {brokerageStatus !== null && (
          <p className="text-sm text-muted-foreground mt-1">
            Trading account: {brokerageStatus.has_account
              ? brokerageStatus.status === 'ACTIVE'
                ? `Active${brokerageStatus.account_number ? ` · #${brokerageStatus.account_number}` : ''}`
                : (brokerageStatus.status ?? 'Pending')
              : 'Not opened'}
          </p>
        )}
      </div>

      {overview && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Equity</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{fmt(overview.total_equity)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Trading</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{fmt(overview.trading_equity)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Bank</CardTitle>
              <Building2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{fmt(overview.bank_balances)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Manual Assets</CardTitle>
              <PiggyBank className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{fmt(overview.manual_assets_value)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Buying Power</CardTitle>
              <Wallet className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{fmt(overview.buying_power)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Unrealized P&L</CardTitle>
              {u >= 0 ? <TrendingUp className="h-4 w-4 text-green-500" /> : <TrendingDown className="h-4 w-4 text-red-500" />}
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${u >= 0 ? 'text-green-500' : 'text-red-500'}`}>{fmt(u)}</div>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList>
          <TabsTrigger value="overview">
            <PieChart className="h-4 w-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="graphs">
            <TrendingUp className="h-4 w-4 mr-2" />
            Graphs
          </TabsTrigger>
          <TabsTrigger value="transactions">
            <ArrowLeftRight className="h-4 w-4 mr-2" />
            Transactions
          </TabsTrigger>
          <TabsTrigger value="investments">
            <TrendingUp className="h-4 w-4 mr-2" />
            Investments
          </TabsTrigger>
          <TabsTrigger value="liabilities">
            <FileText className="h-4 w-4 mr-2" />
            Liabilities
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Positions</CardTitle>
              <CardDescription>Combined trading and manual holdings</CardDescription>
            </CardHeader>
            <CardContent>
              {!overview?.positions?.length ? (
                <p className="text-muted-foreground text-sm">No positions</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-2 font-medium">Symbol</th>
                        <th className="text-right p-2 font-medium">Qty</th>
                        <th className="text-right p-2 font-medium">Avg</th>
                        <th className="text-right p-2 font-medium">Value</th>
                        <th className="text-right p-2 font-medium">P&L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {overview.positions.map((p, i) => (
                        <tr key={p.symbol ? `${p.symbol}-${i}` : i} className="border-b">
                          <td className="p-2 font-medium">{p.symbol || '—'}</td>
                          <td className="p-2 text-right">{Number(p.quantity ?? 0).toFixed(2)}</td>
                          <td className="p-2 text-right">{fmt(Number(p.average_price ?? 0))}</td>
                          <td className="p-2 text-right">{fmt(Number(p.market_value ?? 0))}</td>
                          <td className={`p-2 text-right ${Number(p.unrealized_pl ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {fmt(Number(p.unrealized_pl ?? 0))}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="graphs" className="mt-4">
          <UnifiedGraphs userId={user?.id} days={30} />
        </TabsContent>

        <TabsContent value="transactions" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Transactions</CardTitle>
              <CardDescription>Last 30 days from linked accounts</CardDescription>
            </CardHeader>
            <CardContent>
              {!transactions.length ? (
                <p className="text-muted-foreground text-sm">No transactions available</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-2 font-medium">Date</th>
                        <th className="text-left p-2 font-medium">Name</th>
                        <th className="text-left p-2 font-medium">Category</th>
                        <th className="text-right p-2 font-medium">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.slice(0, 50).map((tx, i) => (
                        <tr key={tx.transaction_id || i} className="border-b">
                          <td className="p-2 text-sm">{tx.date ? fmtDate(tx.date) : '—'}</td>
                          <td className="p-2 font-medium">{tx.name || tx.merchant_name || '—'}</td>
                          <td className="p-2 text-sm text-muted-foreground">
                            {Array.isArray(tx.category) ? tx.category.join(', ') : tx.category || '—'}
                          </td>
                          <td className={`p-2 text-right font-medium ${(tx.amount ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {fmt(tx.amount ?? 0)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="investments" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Investment Holdings</CardTitle>
              <CardDescription>Positions from linked investment accounts</CardDescription>
            </CardHeader>
            <CardContent>
              {!investments.length ? (
                <p className="text-muted-foreground text-sm">No investment positions available</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-2 font-medium">Symbol</th>
                        <th className="text-right p-2 font-medium">Quantity</th>
                        <th className="text-right p-2 font-medium">Avg Price</th>
                        <th className="text-right p-2 font-medium">Current Price</th>
                        <th className="text-right p-2 font-medium">Market Value</th>
                        <th className="text-right p-2 font-medium">P&L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {investments.map((inv, i) => (
                        <tr key={inv.symbol ? `${inv.symbol}-${i}` : i} className="border-b">
                          <td className="p-2 font-medium">{inv.symbol || '—'}</td>
                          <td className="p-2 text-right">{Number(inv.quantity ?? 0).toFixed(4)}</td>
                          <td className="p-2 text-right">{fmt(Number(inv.average_price ?? 0))}</td>
                          <td className="p-2 text-right">{fmt(Number(inv.current_price ?? 0))}</td>
                          <td className="p-2 text-right">{fmt(Number(inv.market_value ?? 0))}</td>
                          <td className={`p-2 text-right ${Number(inv.unrealized_pl ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {fmt(Number(inv.unrealized_pl ?? 0))}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="liabilities" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Liabilities</CardTitle>
              <CardDescription>Credit cards, mortgages, and loans from linked accounts</CardDescription>
            </CardHeader>
            <CardContent>
              {!Object.keys(liabilities).length ? (
                <p className="text-muted-foreground text-sm">No liabilities data available</p>
              ) : (
                <div className="space-y-4">
                  {liabilities.credit && Array.isArray(liabilities.credit) && liabilities.credit.length > 0 && (
                    <div>
                      <h3 className="font-semibold mb-2">Credit Cards</h3>
                      <div className="space-y-2">
                        {liabilities.credit.map((cc: any, i: number) => (
                          <div key={i} className="p-3 border rounded">
                            <div className="flex justify-between">
                              <span className="font-medium">{cc.account_name || 'Credit Card'}</span>
                              <span className="text-red-500">{fmt(cc.balance?.current ?? 0)}</span>
                            </div>
                            {cc.aprs && Array.isArray(cc.aprs) && cc.aprs.length > 0 && (
                              <p className="text-sm text-muted-foreground mt-1">
                                APR: {cc.aprs[0].apr_percentage ?? 'N/A'}%
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {liabilities.mortgage && Array.isArray(liabilities.mortgage) && liabilities.mortgage.length > 0 && (
                    <div>
                      <h3 className="font-semibold mb-2">Mortgages</h3>
                      <div className="space-y-2">
                        {liabilities.mortgage.map((m: any, i: number) => (
                          <div key={i} className="p-3 border rounded">
                            <div className="flex justify-between">
                              <span className="font-medium">{m.account_name || 'Mortgage'}</span>
                              <span className="text-red-500">{fmt(m.balance?.current ?? 0)}</span>
                            </div>
                            {m.interest_rate && (
                              <p className="text-sm text-muted-foreground mt-1">
                                Interest Rate: {m.interest_rate.percentage ?? 'N/A'}%
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {liabilities.student && Array.isArray(liabilities.student) && liabilities.student.length > 0 && (
                    <div>
                      <h3 className="font-semibold mb-2">Student Loans</h3>
                      <div className="space-y-2">
                        {liabilities.student.map((sl: any, i: number) => (
                          <div key={i} className="p-3 border rounded">
                            <div className="flex justify-between">
                              <span className="font-medium">{sl.account_name || 'Student Loan'}</span>
                              <span className="text-red-500">{fmt(sl.balance?.current ?? 0)}</span>
                            </div>
                            {sl.interest_rate && (
                              <p className="text-sm text-muted-foreground mt-1">
                                Interest Rate: {sl.interest_rate.percentage ?? 'N/A'}%
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
