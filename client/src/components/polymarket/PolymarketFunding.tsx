/**
 * Polymarket funding: display funding markets (internal SFP + external Polymarket where applicable).
 * "Fund via Polymarket" uses linked account and CLOB/relayer as needed.
 * Excludes platform-created equities and structured loan products per roadmap.
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { fetchWithAuth } from '@/context/AuthContext';
import { usePayment } from '@/context/PaymentContext';
import { Link } from 'react-router-dom';
import { Wallet, Loader2, Link2, BarChart3, DollarSign } from 'lucide-react';

interface LinkStatus {
  linked: boolean;
  funder_address?: string;
}

interface FundingMarket {
  market_id?: string;
  deal_id?: number;
  question?: string;
  outcome_type?: string;
  visibility?: string;
  created_at?: string | null;
}

export function PolymarketFunding() {
  const { fetchWithPaymentHandling } = usePayment();
  const [linkStatus, setLinkStatus] = useState<LinkStatus | null>(null);
  const [markets, setMarkets] = useState<FundingMarket[]>([]);
  const [loading, setLoading] = useState(true);
  const [marketsLoading, setMarketsLoading] = useState(false);
  const [fundAmount, setFundAmount] = useState('');
  const [fundLoading, setFundLoading] = useState(false);
  const [fundError, setFundError] = useState<string | null>(null);

  const loadLinkStatus = useCallback(async () => {
    try {
      const r = await fetchWithAuth('/api/polymarket/link-status');
      if (r.ok) {
        const d = await r.json();
        setLinkStatus({ linked: !!d.linked, funder_address: d.funder_address });
      } else {
        setLinkStatus({ linked: false });
      }
    } catch {
      setLinkStatus({ linked: false });
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMarkets = useCallback(async () => {
    setMarketsLoading(true);
    try {
      const r = await fetchWithAuth('/api/polymarket/funding-markets?limit=50');
      if (r.ok) {
        const data = await r.json();
        const list = Array.isArray(data) ? data : [];
        setMarkets(list);
      } else {
        setMarkets([]);
      }
    } catch {
      setMarkets([]);
    } finally {
      setMarketsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLinkStatus();
  }, [loadLinkStatus]);

  useEffect(() => {
    loadMarkets();
  }, [loadMarkets]);

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6 flex items-center justify-center gap-2">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Loading…</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wallet className="h-5 w-5" />
            Polymarket Funding
          </CardTitle>
          <CardDescription>
            Funding markets (internal SFP and external Polymarket). Link your Polymarket account to fund via CLOB.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!linkStatus?.linked ? (
            <div className="rounded-lg border border-amber-500/50 bg-amber-500/10 p-4 flex items-center justify-between gap-4">
              <p className="text-sm">
                Link your Polymarket account in User Settings → BYOK to fund via Polymarket.
              </p>
              <Button asChild variant="default" size="sm">
                <Link to="/settings?tab=byok">
                  <Link2 className="h-4 w-4 mr-2" />
                  Link in Settings
                </Link>
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Badge variant="secondary">Linked</Badge>
              {linkStatus.funder_address && (
                <span className="font-mono text-xs truncate max-w-[200px]" title={linkStatus.funder_address}>
                  {linkStatus.funder_address}
                </span>
              )}
            </div>
          )}

          {linkStatus?.linked && (
            <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 space-y-2">
              <Label>Fund Polymarket (USD)</Label>
              <div className="flex gap-2 flex-wrap">
                <Input
                  type="text"
                  inputMode="decimal"
                  placeholder="Amount"
                  value={fundAmount}
                  onChange={(e) => setFundAmount(e.target.value)}
                  className="max-w-[140px]"
                />
                <Button
                  size="sm"
                  disabled={fundLoading || !fundAmount || Number(fundAmount) <= 0}
                  onClick={async () => {
                    setFundError(null);
                    setFundLoading(true);
                    try {
                      const r = await fetchWithPaymentHandling('/api/funding/request', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          amount: fundAmount,
                          payment_type: 'polymarket_funding',
                          destination_id: linkStatus?.funder_address ?? undefined,
                        }),
                      });
                      if (r.ok) {
                        setFundAmount('');
                        await loadLinkStatus();
                      } else if (r.status !== 402) {
                        const d = await r.json().catch(() => ({}));
                        setFundError(d.detail?.message ?? d.detail ?? 'Fund request failed');
                      }
                    } catch {
                      setFundError('Fund request failed');
                    } finally {
                      setFundLoading(false);
                    }
                  }}
                >
                  {fundLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <DollarSign className="h-4 w-4 mr-2" />}
                  Fund Polymarket
                </Button>
              </div>
              {fundError && <p className="text-sm text-red-400">{fundError}</p>}
            </div>
          )}

          <div>
            <h4 className="text-sm font-medium mb-2">Funding markets</h4>
            {marketsLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading…
              </div>
            ) : markets.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No funding markets. Create markets in the Prediction Markets dashboard or browse external Polymarket.
              </p>
            ) : (
              <ul className="space-y-2 max-h-64 overflow-y-auto">
                {markets.slice(0, 20).map((m, i) => (
                  <li key={m.market_id ?? i} className="text-sm border-b border-border/50 pb-2">
                    <span className="font-medium">{m.question ?? 'Market'}</span>
                    {m.outcome_type && (
                      <Badge variant="outline" className="ml-2 text-xs">{m.outcome_type}</Badge>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <Button asChild variant="outline" size="sm">
            <Link to="/dashboard" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Open Prediction Markets
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
