/**
 * Structured Products tab: securitization pool pricing,
 * bundle builder (equity/commodity/loan/deal), tranche purchase,
 * and internal market (list pool/tranche for funding, loan binary markets).
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { fetchWithAuth, useAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';
import { Loader2, Layers, Percent, DollarSign, Plus, Trash2, Package, ShoppingCart, List, Coins, Sparkles, BarChart2 } from 'lucide-react';

interface Pool {
  id: number;
  pool_id: string;
  pool_name: string;
  pool_type: string;
  currency: string;
  status: string;
}

interface TrancheRow {
  id: number;
  tranche_id: string;
  tranche_name: string;
  tranche_class: string;
  size: string;
  currency: string;
  interest_rate: number;
  risk_rating?: string;
  token_id?: string;
  owner_wallet_address?: string;
}

type AssetKind = 'deal' | 'loan_asset' | 'equity' | 'commodity';
interface BasketAsset {
  kind: AssetKind;
  asset_id?: string;
  deal_id?: string | number;
  loan_asset_id?: number;
  equity_symbol?: string;
  commodity_code?: string;
  value?: number;
  quantity?: number;
  unit_price?: number;
  label: string;
}

interface TranchePricing {
  tranche_id: string;
  tranche_name: string;
  fair_value: number;
  yield_to_maturity?: number;
  spread_bps?: number;
  duration?: number;
  principal?: number;
  coupon_rate_percent?: number;
}

interface Pricing {
  pool_id: string;
  pool_name: string;
  currency: string;
  total_fair_value: number;
  weighted_average_yield_percent?: number;
  benchmark_rate_percent?: number;
  as_of_date?: string;
  tranches: TranchePricing[];
}

const POOL_TYPES = ['ABS', 'CLO', 'MBS', 'EQ_BUNDLE', 'COMMODITY_BUNDLE'] as const;

function BuildBundleSection({
  basket,
  poolName,
  poolType,
  lockDays,
  createLoading,
  createError,
  deals,
  loans,
  onPoolNameChange,
  onPoolTypeChange,
  onLockDaysChange,
  onAdd,
  onRemove,
  onCreate,
  onLoadDeals,
  onLoadLoans,
}: {
  basket: BasketAsset[];
  poolName: string;
  poolType: string;
  lockDays: number | '';
  createLoading: boolean;
  createError: string | null;
  deals: { id: number; deal_id: string; total_commitment?: number; currency?: string }[];
  loans: { id: number; loan_id: string }[];
  onPoolNameChange: (v: string) => void;
  onPoolTypeChange: (v: string) => void;
  onLockDaysChange: (v: number | '') => void;
  onAdd: (a: BasketAsset) => void;
  onRemove: (i: number) => void;
  onCreate: () => void;
  onLoadDeals: () => void;
  onLoadLoans: () => void;
}) {
  const [addKind, setAddKind] = useState<AssetKind>('equity');
  const [eqSym, setEqSym] = useState('');
  const [eqVal, setEqVal] = useState('');
  const [commCode, setCommCode] = useState('');
  const [commVal, setCommVal] = useState('');
  const [selDealId, setSelDealId] = useState<number | ''>('');
  const [selLoanId, setSelLoanId] = useState<number | ''>('');

  useEffect(() => { onLoadDeals(); onLoadLoans(); }, [onLoadDeals, onLoadLoans]);

  const doAdd = () => {
    if (addKind === 'deal' && selDealId !== '') {
      const d = deals.find((x) => x.id === selDealId);
      onAdd({ 
        kind: 'deal', 
        deal_id: selDealId, 
        value: d?.total_commitment ?? undefined,
        label: d ? `${d.deal_id} (${d.total_commitment ?? '?'})` : `Deal ${selDealId}` 
      });
      setSelDealId('');
    } else if (addKind === 'loan_asset' && selLoanId !== '') {
      const l = loans.find((x) => x.id === selLoanId);
      onAdd({ kind: 'loan_asset', loan_asset_id: selLoanId, label: l ? l.loan_id : `Loan ${selLoanId}` });
      setSelLoanId('');
    } else if (addKind === 'equity' && eqSym.trim()) {
      const v = eqVal ? Number(eqVal) : undefined;
      onAdd({ kind: 'equity', equity_symbol: eqSym.trim(), value: v, label: `${eqSym}${v != null ? ` $${v}` : ''}` });
      setEqSym(''); setEqVal('');
    } else if (addKind === 'commodity' && commCode.trim()) {
      const v = commVal ? Number(commVal) : undefined;
      onAdd({ kind: 'commodity', commodity_code: commCode.trim(), value: v, label: `${commCode}${v != null ? ` $${v}` : ''}` });
      setCommCode(''); setCommVal('');
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Package className="h-4 w-4" />Build bundle</CardTitle>
        <CardDescription>Add equities, commodities, loans, or deals; create a pool with one Class A tranche.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2">
          <div>
            <label className="text-sm font-medium">Pool name</label>
            <input value={poolName} onChange={(e) => onPoolNameChange(e.target.value)} className="w-full px-3 py-2 mt-1 bg-background border rounded-md" placeholder="My bundle" />
          </div>
          <div>
            <label className="text-sm font-medium">Pool type</label>
            <select value={poolType} onChange={(e) => onPoolTypeChange(e.target.value)} className="w-full px-3 py-2 mt-1 bg-background border rounded-md">
              {POOL_TYPES.map((t) => (<option key={t} value={t}>{t}</option>))}
            </select>
          </div>
        </div>
        <div>
          <label className="text-sm font-medium">Lock days (equity bundles, optional)</label>
          <input type="number" min={0} value={lockDays} onChange={(e) => onLockDaysChange(e.target.value === '' ? '' : Number(e.target.value))} className="w-24 px-3 py-2 mt-1 bg-background border rounded-md" placeholder="30" />
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <select value={addKind} onChange={(e) => setAddKind(e.target.value as AssetKind)} className="px-3 py-2 bg-background border rounded-md">
            <option value="deal">Deal</option>
            <option value="loan_asset">Loan</option>
            <option value="equity">Equity</option>
            <option value="commodity">Commodity</option>
          </select>
          {addKind === 'deal' && (
            <select value={selDealId} onChange={(e) => setSelDealId(e.target.value === '' ? '' : Number(e.target.value))} className="px-3 py-2 bg-background border rounded-md">
              <option value="">Select deal</option>
              {deals.map((d) => (<option key={d.id} value={d.id}>{d.deal_id} ({d.total_commitment ?? '?'})</option>))}
            </select>
          )}
          {addKind === 'loan_asset' && (
            <select value={selLoanId} onChange={(e) => setSelLoanId(e.target.value === '' ? '' : Number(e.target.value))} className="px-3 py-2 bg-background border rounded-md">
              <option value="">Select loan</option>
              {loans.map((l) => (<option key={l.id} value={l.id}>{l.loan_id}</option>))}
            </select>
          )}
          {addKind === 'equity' && (
            <>
              <input value={eqSym} onChange={(e) => setEqSym(e.target.value)} placeholder="Symbol (e.g. AAPL)" className="w-32 px-3 py-2 bg-background border rounded-md" />
              <input type="number" value={eqVal} onChange={(e) => setEqVal(e.target.value)} placeholder="Value" className="w-28 px-3 py-2 bg-background border rounded-md" />
            </>
          )}
          {addKind === 'commodity' && (
            <>
              <input value={commCode} onChange={(e) => setCommCode(e.target.value)} placeholder="Code (e.g. GOLD)" className="w-32 px-3 py-2 bg-background border rounded-md" />
              <input type="number" value={commVal} onChange={(e) => setCommVal(e.target.value)} placeholder="Value" className="w-28 px-3 py-2 bg-background border rounded-md" />
            </>
          )}
          <Button size="sm" onClick={doAdd}><Plus className="h-4 w-4 mr-1" />Add</Button>
        </div>
        {basket.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-1">Basket</p>
            <ul className="border rounded-md divide-y">
              {basket.map((a, i) => (
                <li key={i} className="flex items-center justify-between px-3 py-2">
                  <span className="text-sm">{a.label} ({a.kind})</span>
                  <Button variant="ghost" size="sm" onClick={() => onRemove(i)}><Trash2 className="h-4 w-4" /></Button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {createError && <p className="text-destructive text-sm">{createError}</p>}
        <Button onClick={onCreate} disabled={createLoading || basket.length === 0 || !poolName.trim()}>
          {createLoading ? <><Loader2 className="h-4 w-4 animate-spin mr-2" />Creating…</> : 'Create pool'}
        </Button>
      </CardContent>
    </Card>
  );
}

const LOAN_OUTCOME_TYPES = [
  { value: 'LOAN_REPAID', label: 'Repaid' },
  { value: 'LOAN_ON_TIME', label: 'On-time' },
  { value: 'LOAN_REPAID_CRYPTO', label: 'Repaid (crypto)' },
] as const;

function InternalMarketSection({
  pools,
}: {
  pools: Pool[];
}) {
  const [loans, setLoans] = useState<{ id: number; loan_id: string }[]>([]);
  const [loansLoading, setLoansLoading] = useState(false);
  const [listPoolPool, setListPoolPool] = useState<number | ''>('');
  const [listPoolQuestion, setListPoolQuestion] = useState('');
  const [listPoolLoading, setListPoolLoading] = useState(false);
  const [listPoolError, setListPoolError] = useState<string | null>(null);
  const [listPoolSuccess, setListPoolSuccess] = useState<string | null>(null);
  const [listTranchePool, setListTranchePool] = useState<number | ''>('');
  const [tranchesForTranche, setTranchesForTranche] = useState<TrancheRow[]>([]);
  const [trancheSelectLoading, setTrancheSelectLoading] = useState(false);
  const [listTrancheTranche, setListTrancheTranche] = useState<number | ''>('');
  const [listTrancheQuestion, setListTrancheQuestion] = useState('');
  const [listTrancheLoading, setListTrancheLoading] = useState(false);
  const [listTrancheError, setListTrancheError] = useState<string | null>(null);
  const [listTrancheSuccess, setListTrancheSuccess] = useState<string | null>(null);
  const [loanMarketLoan, setLoanMarketLoan] = useState<number | ''>('');
  const [loanMarketType, setLoanMarketType] = useState<string>(LOAN_OUTCOME_TYPES[0].value);
  const [loanMarketQuestion, setLoanMarketQuestion] = useState('');
  const [loanMarketLoading, setLoanMarketLoading] = useState(false);
  const [loanMarketError, setLoanMarketError] = useState<string | null>(null);
  const [loanMarketSuccess, setLoanMarketSuccess] = useState<string | null>(null);

  const loadLoans = useCallback(async () => {
    setLoansLoading(true);
    try {
      const res = await fetchWithAuth(resolveApiUrl('/api/securitization/available-loans?limit=50'));
      if (!res.ok) return;
      const d = await res.json();
      setLoans(d?.loans ?? []);
    } catch {
      setLoans([]);
    } finally {
      setLoansLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLoans();
  }, [loadLoans]);

  useEffect(() => {
    if (listTranchePool === '') {
      setTranchesForTranche([]);
      setListTrancheTranche('');
      return;
    }
    setTrancheSelectLoading(true);
    setListTrancheTranche('');
    fetchWithAuth(resolveApiUrl(`/api/securitization/pools/${listTranchePool}/tranches`))
      .then((res) => (res.ok ? res.json() : { tranches: [] }))
      .then((d) => setTranchesForTranche(d?.tranches ?? []))
      .catch(() => setTranchesForTranche([]))
      .finally(() => setTrancheSelectLoading(false));
  }, [listTranchePool]);

  const listPool = async () => {
    const pid = listPoolPool === '' ? null : Number(listPoolPool);
    if (pid == null || !listPoolQuestion.trim()) {
      setListPoolError('Select a pool and enter a question.');
      return;
    }
    setListPoolLoading(true);
    setListPoolError(null);
    setListPoolSuccess(null);
    try {
      const res = await fetchWithAuth(resolveApiUrl('/api/polymarket/markets'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pool_id: pid,
          question: listPoolQuestion.trim(),
          outcome_type: 'binary',
          resolution_condition: { type: 'POOL_LISTING' },
          market_event_type: 'POOL_LISTING',
        }),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.detail || e.message || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setListPoolSuccess(`Listed: ${data.market_id}`);
      setListPoolQuestion('');
    } catch (e) {
      setListPoolError(e instanceof Error ? e.message : 'List pool failed');
    } finally {
      setListPoolLoading(false);
    }
  };

  const listTranche = async () => {
    const tid = listTrancheTranche === '' ? null : Number(listTrancheTranche);
    if (tid == null || !listTrancheQuestion.trim()) {
      setListTrancheError('Select a tranche and enter a question.');
      return;
    }
    setListTrancheLoading(true);
    setListTrancheError(null);
    setListTrancheSuccess(null);
    try {
      const res = await fetchWithAuth(resolveApiUrl('/api/polymarket/markets'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tranche_id: tid,
          question: listTrancheQuestion.trim(),
          outcome_type: 'binary',
          resolution_condition: { type: 'TRANCHE_LISTING' },
          market_event_type: 'TRANCHE_LISTING',
        }),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.detail || e.message || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setListTrancheSuccess(`Listed: ${data.market_id}`);
      setListTrancheQuestion('');
    } catch (e) {
      setListTrancheError(e instanceof Error ? e.message : 'List tranche failed');
    } finally {
      setListTrancheLoading(false);
    }
  };

  const createLoanMarket = async () => {
    const lid = loanMarketLoan === '' ? null : Number(loanMarketLoan);
    if (lid == null || !loanMarketQuestion.trim()) {
      setLoanMarketError('Select a loan and enter a question.');
      return;
    }
    setLoanMarketLoading(true);
    setLoanMarketError(null);
    setLoanMarketSuccess(null);
    try {
      const res = await fetchWithAuth(resolveApiUrl('/api/polymarket/markets'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          loan_asset_id: lid,
          question: loanMarketQuestion.trim(),
          outcome_type: 'binary',
          resolution_condition: { type: loanMarketType, loan_asset_id: lid },
          market_event_type: loanMarketType,
        }),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.detail || e.message || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setLoanMarketSuccess(`Created: ${data.market_id}`);
      setLoanMarketQuestion('');
    } catch (e) {
      setLoanMarketError(e instanceof Error ? e.message : 'Create loan market failed');
    } finally {
      setLoanMarketLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><List className="h-4 w-4" />List pool for funding</CardTitle>
          <CardDescription>Create an internal market to list a securitization pool for funding.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <label className="text-sm font-medium">Pool</label>
            <select value={listPoolPool} onChange={(e) => setListPoolPool(e.target.value === '' ? '' : Number(e.target.value))} className="w-full mt-1 px-3 py-2 bg-background border rounded-md">
              <option value="">Select pool</option>
              {pools.map((p) => (<option key={p.id} value={p.id}>{p.pool_name} ({p.pool_id})</option>))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">Question</label>
            <input value={listPoolQuestion} onChange={(e) => setListPoolQuestion(e.target.value)} placeholder="e.g. Will this pool receive funding?" className="w-full mt-1 px-3 py-2 bg-background border rounded-md" />
          </div>
          {listPoolError && <p className="text-destructive text-sm">{listPoolError}</p>}
          {listPoolSuccess && <p className="text-emerald-600 text-sm">{listPoolSuccess}</p>}
          <Button onClick={listPool} disabled={listPoolLoading || listPoolPool === '' || !listPoolQuestion.trim()}>
            {listPoolLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}List pool
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Layers className="h-4 w-4" />List tranche</CardTitle>
          <CardDescription>List a tranche on the internal market for investment.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <label className="text-sm font-medium">Pool</label>
            <select value={listTranchePool} onChange={(e) => setListTranchePool(e.target.value === '' ? '' : Number(e.target.value))} className="w-full mt-1 px-3 py-2 bg-background border rounded-md">
              <option value="">Select pool</option>
              {pools.map((p) => (<option key={p.id} value={p.id}>{p.pool_name}</option>))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">Tranche</label>
            <select value={listTrancheTranche} onChange={(e) => setListTrancheTranche(e.target.value === '' ? '' : Number(e.target.value))} className="w-full mt-1 px-3 py-2 bg-background border rounded-md" disabled={trancheSelectLoading || !listTranchePool}>
              <option value="">{trancheSelectLoading ? 'Loading…' : 'Select tranche'}</option>
              {tranchesForTranche.map((t) => (<option key={t.id} value={t.id}>{t.tranche_name} ({t.tranche_class})</option>))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">Question</label>
            <input value={listTrancheQuestion} onChange={(e) => setListTrancheQuestion(e.target.value)} placeholder="e.g. Will this tranche be fully subscribed?" className="w-full mt-1 px-3 py-2 bg-background border rounded-md" />
          </div>
          {listTrancheError && <p className="text-destructive text-sm">{listTrancheError}</p>}
          {listTrancheSuccess && <p className="text-emerald-600 text-sm">{listTrancheSuccess}</p>}
          <Button onClick={listTranche} disabled={listTrancheLoading || listTrancheTranche === '' || !listTrancheQuestion.trim()}>
            {listTrancheLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}List tranche
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Coins className="h-4 w-4" />Create loan outcome market</CardTitle>
          <CardDescription>Binary market: repaid, on-time, or repaid in crypto. Resolution oracle not yet implemented.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <label className="text-sm font-medium">Loan</label>
            <select value={loanMarketLoan} onChange={(e) => setLoanMarketLoan(e.target.value === '' ? '' : Number(e.target.value))} className="w-full mt-1 px-3 py-2 bg-background border rounded-md" disabled={loansLoading}>
              <option value="">{loansLoading ? 'Loading…' : 'Select loan'}</option>
              {loans.map((l) => (<option key={l.id} value={l.id}>{l.loan_id}</option>))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">Outcome</label>
            <select value={loanMarketType} onChange={(e) => setLoanMarketType(e.target.value)} className="w-full mt-1 px-3 py-2 bg-background border rounded-md">
              {LOAN_OUTCOME_TYPES.map((o) => (<option key={o.value} value={o.value}>{o.label}</option>))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">Question</label>
            <input value={loanMarketQuestion} onChange={(e) => setLoanMarketQuestion(e.target.value)} placeholder="e.g. Will this loan be repaid on time?" className="w-full mt-1 px-3 py-2 bg-background border rounded-md" />
          </div>
          {loanMarketError && <p className="text-destructive text-sm">{loanMarketError}</p>}
          {loanMarketSuccess && <p className="text-emerald-600 text-sm">{loanMarketSuccess}</p>}
          <Button onClick={createLoanMarket} disabled={loanMarketLoading || loanMarketLoan === '' || !loanMarketQuestion.trim()}>
            {loanMarketLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}Create loan outcome market
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

export function StructuredProductsTab() {
  const { user } = useAuth();
  const [pools, setPools] = useState<Pool[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [pricing, setPricing] = useState<Pricing | null>(null);
  const [tranchesList, setTranchesList] = useState<TrancheRow[]>([]);
  const [benchmark, setBenchmark] = useState(5);
  const [loadingPools, setLoadingPools] = useState(true);
  const [loadingPricing, setLoadingPricing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSubTab, setActiveSubTab] = useState<'pricing' | 'build' | 'internal' | 'generic'>('pricing');

  // Generic SIP state
  const [sipTemplates, setSipTemplates] = useState<any[]>([]);
  const [sipInstances, setSipInstances] = useState<any[]>([]);
  const [loadingSip, setLoadingSip] = useState(false);

  // Build bundle state
  const [basket, setBasket] = useState<BasketAsset[]>([]);
  const [poolName, setPoolName] = useState('');
  const [poolType, setPoolType] = useState<string>(POOL_TYPES[0]);
  const [lockDays, setLockDays] = useState<number | ''>('');
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [deals, setDeals] = useState<{ id: number; deal_id: string; total_commitment?: number; currency?: string }[]>([]);
  const [loans, setLoans] = useState<{ id: number; loan_id: string }[]>([]);
  const [purchasingId, setPurchasingId] = useState<number | null>(null);

  const loadPools = useCallback(async () => {
    setLoadingPools(true);
    setError(null);
    try {
      const res = await fetchWithAuth('/api/securitization/pools?limit=50');
      if (!res.ok) throw new Error('Failed to load pools');
      const data = await res.json();
      const list = data?.pools ?? [];
      setPools(list);
      setSelectedId((prev) => (prev != null ? prev : list[0]?.id ?? null));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load pools');
      setPools([]);
    } finally {
      setLoadingPools(false);
    }
  }, []);

  useEffect(() => { loadPools(); }, [loadPools]);

  const loadPricing = useCallback(async () => {
    if (selectedId == null) return;
    setLoadingPricing(true);
    setError(null);
    try {
      const res = await fetchWithAuth(
        `/api/securitization/pools/${selectedId}/pricing?benchmark_rate=${benchmark}`
      );
      if (!res.ok) throw new Error('Failed to load pricing');
      const data = await res.json();
      setPricing(data?.pricing ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load pricing');
      setPricing(null);
    } finally {
      setLoadingPricing(false);
    }
  }, [selectedId, benchmark]);

  useEffect(() => { loadPricing(); }, [loadPricing]);

  const loadTranches = useCallback(async () => {
    if (selectedId == null) return;
    try {
      const res = await fetchWithAuth(`/api/securitization/pools/${selectedId}/tranches`);
      if (!res.ok) return;
      const d = await res.json();
      setTranchesList(d?.tranches ?? []);
    } catch {
      setTranchesList([]);
    }
  }, [selectedId]);
  useEffect(() => { loadTranches(); }, [loadTranches]);

  const loadDeals = useCallback(async () => {
    try {
      const res = await fetchWithAuth('/api/securitization/available-deals?limit=50');
      if (!res.ok) return;
      const d = await res.json();
      setDeals(d?.deals ?? []);
    } catch { setDeals([]); }
  }, []);
  const loadLoans = useCallback(async () => {
    try {
      const res = await fetchWithAuth('/api/securitization/available-loans?limit=50');
      if (!res.ok) return;
      const d = await res.json();
      setLoans(d?.loans ?? []);
    } catch { setLoans([]); }
  }, []);

  const addToBasket = (a: BasketAsset) => setBasket((b) => [...b, a]);
  const removeFromBasket = (i: number) => setBasket((b) => b.filter((_, j) => j !== i));

  const createPool = async () => {
    if (!user?.id || !poolName.trim() || basket.length === 0) {
      setCreateError('Pool name and at least one asset required.');
      return;
    }
    setCreateLoading(true);
    setCreateError(null);
    try {
      const underlying_asset_ids = basket.map((a) => {
        const base: Record<string, unknown> = { asset_type: a.kind, allocation_percentage: 0 };
        if (a.kind === 'deal' && a.deal_id) {
          base.deal_id = a.deal_id;
          // Include value if provided, otherwise backend will try to extract from deal
          if (a.value != null) base.value = a.value;
        } else if (a.kind === 'loan_asset' && a.loan_asset_id != null) {
          base.loan_asset_id = a.loan_asset_id;
          // Include value if provided, otherwise backend will try to extract from loan_asset
          if (a.value != null) base.value = a.value;
        } else if (a.kind === 'equity' && a.equity_symbol) {
          base.equity_symbol = a.equity_symbol;
          if (a.value != null) base.value = a.value;
          else if (a.quantity != null && a.unit_price != null) { base.quantity = a.quantity; base.unit_price = a.unit_price; }
        } else if (a.kind === 'commodity' && a.commodity_code) {
          base.commodity_code = a.commodity_code;
          if (a.value != null) base.value = a.value;
          else if (a.quantity != null && a.unit_price != null) { base.quantity = a.quantity; base.unit_price = a.unit_price; }
        }
        return base;
      });
      const res = await fetchWithAuth('/api/securitization/pools', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pool_name: poolName.trim(),
          pool_type: poolType,
          originator_user_id: user.id,
          trustee_user_id: user.id,
          underlying_asset_ids,
          tranche_data: [],
          auto_tranche: true,
          lock_period_days: lockDays === '' ? null : Number(lockDays),
        }),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.detail || e.message || `HTTP ${res.status}`);
      }
      setBasket([]);
      setPoolName('');
      setActiveSubTab('pricing');
      loadPools();
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : 'Create failed');
    } finally {
      setCreateLoading(false);
    }
  };

  const purchaseTranche = async (trancheDbId: number) => {
    if (selectedId == null || !user?.id) return;
    setPurchasingId(trancheDbId);
    try {
      const res = await fetchWithAuth(`/api/securitization/pools/${selectedId}/purchase-tranche`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tranche_id: trancheDbId, buyer_user_id: user.id, payment_payload: null }),
      });
      if (res.status === 402) {
        const j = await res.json().catch(() => ({}));
        setError(`Payment required: ${j.amount || ''} ${j.currency || ''}. Provide payment_payload or use admin.`);
        return;
      }
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.detail || e.message || `HTTP ${res.status}`);
      }
      loadTranches();
      loadPricing();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Purchase failed');
    } finally {
      setPurchasingId(null);
    }
  };

  const fmt = (n: number) => `$${Number(n).toFixed(2)}`;
  const pct = (n: number) => `${Number(n).toFixed(2)}%`;

  const byName = (name: string) => tranchesList.find((t) => t.tranche_name === name);

  const loadSipData = useCallback(async () => {
    setLoadingSip(true);
    try {
      const [tplRes, instRes] = await Promise.all([
        fetchWithAuth('/api/structured-products/templates'),
        fetchWithAuth('/api/structured-products/instances')
      ]);
      if (tplRes.ok) setSipTemplates(await tplRes.json());
      if (instRes.ok) setSipInstances(await instRes.json());
    } catch (e) {
      console.error("Failed to load SIP data", e);
    } finally {
      setLoadingSip(false);
    }
  }, []);

  useEffect(() => {
    if (activeSubTab === 'generic') loadSipData();
  }, [activeSubTab, loadSipData]);

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Structured Products</h3>
        <p className="text-muted-foreground text-sm">
          Pricing, bundle builder (equities, commodities, loans, deals), and tranche purchase
        </p>
      </div>

      <Tabs value={activeSubTab} onValueChange={(v) => setActiveSubTab(v as 'pricing' | 'build' | 'internal' | 'generic')}>
        <TabsList>
          <TabsTrigger value="pricing">Pricing</TabsTrigger>
          <TabsTrigger value="build">Build bundle</TabsTrigger>
          <TabsTrigger value="generic">Generic SIPs</TabsTrigger>
          <TabsTrigger value="internal">Internal market</TabsTrigger>
        </TabsList>

        <TabsContent value="generic" className="space-y-4 mt-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Sparkles className="h-4 w-4" />Available Templates</CardTitle>
                <CardDescription>Bespoke structured product types</CardDescription>
              </CardHeader>
              <CardContent>
                {loadingSip ? <div className="flex justify-center"><Loader2 className="h-6 w-6 animate-spin" /></div> : (
                  <div className="space-y-3">
                    {sipTemplates.length === 0 ? <p className="text-muted-foreground text-sm">No templates available.</p> : 
                      sipTemplates.map(t => (
                        <div key={t.id} className="p-3 border rounded-lg flex items-center justify-between">
                          <div>
                            <p className="font-medium">{t.name}</p>
                            <p className="text-xs text-muted-foreground">{t.product_type} • {t.underlying_symbol}</p>
                          </div>
                          <Button size="sm" variant="outline" onClick={() => {/* TODO: Issue modal */}}>Issue</Button>
                        </div>
                      ))
                    }
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><BarChart2 className="h-4 w-4" />Live Instances</CardTitle>
                <CardDescription>Issued products tracking performance</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {sipInstances.length === 0 ? <p className="text-muted-foreground text-sm">No live instances.</p> : 
                    sipInstances.map(i => (
                      <div key={i.id} className="p-3 border rounded-lg flex items-center justify-between">
                        <div>
                          <p className="font-medium">Instance #{i.id}</p>
                          <p className="text-xs text-muted-foreground">Matures: {i.maturity_date}</p>
                        </div>
                        <div className="text-right">
                          <p className="font-bold text-emerald-500">${i.current_value?.toLocaleString()}</p>
                          <Button size="xs" variant="link" className="h-auto p-0">Subscribe</Button>
                        </div>
                      </div>
                    ))
                  }
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="internal" className="space-y-4 mt-4">
          <InternalMarketSection pools={pools} />
        </TabsContent>

        <TabsContent value="build" className="space-y-4 mt-4">
          <BuildBundleSection
            basket={basket}
            poolName={poolName}
            poolType={poolType}
            lockDays={lockDays}
            createLoading={createLoading}
            createError={createError}
            deals={deals}
            loans={loans}
            onPoolNameChange={setPoolName}
            onPoolTypeChange={setPoolType}
            onLockDaysChange={setLockDays}
            onAdd={addToBasket}
            onRemove={removeFromBasket}
            onCreate={createPool}
            onLoadDeals={loadDeals}
            onLoadLoans={loadLoans}
          />
        </TabsContent>

        <TabsContent value="pricing" className="mt-4">
      {loadingPools && <div className="flex items-center gap-2 text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> Loading pools…</div>}
      {error && <p className="text-destructive text-sm">{error}</p>}

      {!loadingPools && pools.length > 0 && (
        <>
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <label className="text-sm font-medium mr-2">Pool</label>
              <select
                value={selectedId ?? ''}
                onChange={(e) => setSelectedId(e.target.value ? Number(e.target.value) : null)}
                className="px-3 py-2 bg-background border rounded-md"
              >
                {pools.map((p) => (
                  <option key={p.id} value={p.id}>{p.pool_name} ({p.pool_id})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mr-2">Benchmark %</label>
              <input
                type="number"
                step="0.25"
                value={benchmark}
                onChange={(e) => setBenchmark(Number(e.target.value) || 5)}
                className="w-20 px-3 py-2 bg-background border rounded-md"
              />
            </div>
          </div>

          {loadingPricing && <div className="flex items-center gap-2 text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> Loading pricing…</div>}

          {pricing && !loadingPricing && (
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Fair Value</CardTitle>
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{fmt(pricing.total_fair_value)}</div>
                  <p className="text-xs text-muted-foreground">{pricing.currency}</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Wtd Avg Yield</CardTitle>
                  <Percent className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {pricing.weighted_average_yield_percent != null
                      ? pct(pricing.weighted_average_yield_percent)
                      : '—'}
                  </div>
                  <p className="text-xs text-muted-foreground">Benchmark {pct(pricing.benchmark_rate_percent ?? benchmark)}</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Tranches</CardTitle>
                  <Layers className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{pricing.tranches?.length ?? 0}</div>
                </CardContent>
              </Card>
            </div>
          )}

          {pricing?.tranches?.length ? (
            <Card>
              <CardHeader>
                <CardTitle>Tranche Pricing</CardTitle>
                <CardDescription>Fair value, YTM, spread, duration</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-2 font-medium">Tranche</th>
                        <th className="text-right p-2 font-medium">Fair Value</th>
                        <th className="text-right p-2 font-medium">YTM %</th>
                        <th className="text-right p-2 font-medium">Spread bps</th>
                        <th className="text-right p-2 font-medium">Duration</th>
                        <th className="text-right p-2 font-medium">Principal</th>
                        <th className="text-right p-2 font-medium">Purchase</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pricing.tranches.map((t, i) => {
                        const tr = byName(t.tranche_name || t.tranche_id || '');
                        return (
                          <tr key={t.tranche_id || i} className="border-b">
                            <td className="p-2 font-medium">{t.tranche_name || t.tranche_id || '—'}</td>
                            <td className="p-2 text-right">{fmt(t.fair_value ?? 0)}</td>
                            <td className="p-2 text-right">{t.yield_to_maturity != null ? pct(t.yield_to_maturity) : '—'}</td>
                            <td className="p-2 text-right">{t.spread_bps != null ? t.spread_bps : '—'}</td>
                            <td className="p-2 text-right">{t.duration != null ? Number(t.duration).toFixed(2) : '—'}</td>
                            <td className="p-2 text-right">{t.principal != null ? fmt(t.principal) : '—'}</td>
                            <td className="p-2 text-right">
                              {tr ? (
                                <Button size="sm" variant="outline" onClick={() => purchaseTranche(tr.id)} disabled={!!purchasingId || !!tr.owner_wallet_address}>
                                  {purchasingId === tr.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShoppingCart className="h-4 w-4" />}
                                </Button>
                              ) : '—'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          ) : pricing && !loadingPricing ? (
            <p className="text-muted-foreground text-sm">No tranches in this pool.</p>
          ) : null}
        </>
      )}

      {!loadingPools && pools.length === 0 && !error && (
        <p className="text-muted-foreground text-sm">No securitization pools. Create one via Build bundle.</p>
      )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
