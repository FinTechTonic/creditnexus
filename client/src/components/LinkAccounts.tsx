/**
 * Link Accounts – connect bank (Plaid) and other data sources.
 * Uses server-derived status (plaid_enabled, connected) only; no secrets in client config.
 * Plaid is not a sign-in method; this is a post-login "Link accounts" flow.
 * 
 * Moved from apps/link-accounts to components (Phase 2, Week 8).
 */

import { useEffect, useRef, useState } from 'react';
import { usePlaidLink } from 'react-plaid-link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { fetchWithAuth } from '@/context/AuthContext';
import { usePayment } from '@/context/PaymentContext';
import { PermissionGate } from '@/components/PermissionGate';
import { PERMISSION_TRADE_VIEW } from '@/utils/permissions';
import { Landmark, Link2, Loader2, Unplug, CheckCircle2, Briefcase } from 'lucide-react';

interface BankingStatus {
  plaid_enabled: boolean;
  connected: boolean;
}

/** One Plaid connection (multi-item) from GET /api/banking/connections */
interface PlaidConnectionItem {
  id: number;
  item_id_masked: string | null;
  created_at: string | null;
}

interface BrokerageStatus {
  has_account: boolean;
  status?: string;
  crypto_status?: string;
  enabled_assets?: string[];
  alpaca_account_id?: string;
  account_number?: string;
  action_required_reason?: string;
  currency: string;
}

export interface LinkedBank {
  relationship_id: string;
  nickname?: string | null;
  status?: string | null;
  alpaca_account_id?: string;
}

export function LinkAccounts() {
  const { fetchWithPaymentHandling } = usePayment();
  const [status, setStatus] = useState<BankingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [connectLoading, setConnectLoading] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [disconnectLoading, setDisconnectLoading] = useState(false);
  const [disconnectingId, setDisconnectingId] = useState<number | null>(null);
  const [plaidConnections, setPlaidConnections] = useState<PlaidConnectionItem[]>([]);
  const [brokerageStatus, setBrokerageStatus] = useState<BrokerageStatus | null>(null);
  const [linkedBanks, setLinkedBanks] = useState<LinkedBank[]>([]);
  const [fundingLinkToken, setFundingLinkToken] = useState<string | null>(null);
  const [fundAmount, setFundAmount] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [withdrawRelationshipId, setWithdrawRelationshipId] = useState('');
  const [fundLoading, setFundLoading] = useState(false);
  const [withdrawLoading, setWithdrawLoading] = useState(false);
  const [fundError, setFundError] = useState<string | null>(null);
  const [withdrawError, setWithdrawError] = useState<string | null>(null);
  const [linkFundingError, setLinkFundingError] = useState<string | null>(null);
  const openedForRef = useRef<string | null>(null);
  const openedFundingRef = useRef<string | null>(null);

  const fetchStatus = async () => {
    setError(null);
    try {
      const r = await fetchWithPaymentHandling('/api/banking/status');
      if (r.ok) {
        const d = await r.json();
        setStatus({ plaid_enabled: d.plaid_enabled, connected: d.connected });
        if (d.connected) {
          const connR = await fetchWithPaymentHandling('/api/banking/connections');
          if (connR.ok) {
            const list = await connR.json();
            setPlaidConnections(Array.isArray(list) ? list : []);
          } else {
            setPlaidConnections([]);
          }
        } else {
          setPlaidConnections([]);
        }
      } else {
        if (r.status === 403) {
          setStatus(null);
          setError("You don't have permission to manage bank connections.");
        } else {
          setError('Failed to load banking status.');
        }
      }
      // Brokerage (Alpaca) account status
      const br = await fetchWithPaymentHandling('/api/brokerage/account/status');
      if (br.ok) {
        const bd = await br.json();
        setBrokerageStatus(bd);
        // When ACTIVE, fetch linked banks for funding
        if (bd.status === 'ACTIVE') {
          const ach = await fetchWithPaymentHandling('/api/brokerage/ach-relationships');
          if (ach.ok) {
            const list = await ach.json();
            setLinkedBanks(Array.isArray(list) ? list : []);
          } else {
            setLinkedBanks([]);
          }
        } else {
          setLinkedBanks([]);
        }
      } else {
        setBrokerageStatus(null);
        setLinkedBanks([]);
      }
    } catch (e) {
      setError('Failed to load banking status.');
      setStatus(null);
      setBrokerageStatus(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [fetchWithPaymentHandling]);

  useEffect(() => {
    if (linkedBanks.length === 1 && !withdrawRelationshipId) {
      setWithdrawRelationshipId(linkedBanks[0].relationship_id);
    }
  }, [linkedBanks]);

  const { open, ready } = usePlaidLink({
    token: linkToken,
    onSuccess: async (public_token: string) => {
      setConnectError(null);
      setConnectLoading(true);
      try {
        const r = await fetchWithAuth('/api/banking/connect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ public_token }),
        });
        if (r.ok) {
          setLinkToken(null);
          openedForRef.current = null;
          await fetchStatus();
        } else {
          const d = await r.json().catch(() => ({}));
          setConnectError(d.detail || 'Failed to connect bank.');
        }
      } catch (e) {
        setConnectError('Failed to connect bank.');
      } finally {
        setConnectLoading(false);
      }
    },
    onExit: () => {
      setLinkToken(null);
      openedForRef.current = null;
      setConnectLoading(false);
    },
  });

  const { open: openFundingLink, ready: readyFundingLink } = usePlaidLink({
    token: fundingLinkToken,
    onSuccess: async (public_token: string, metadata: { accounts?: Array<{ id: string; name?: string }> }) => {
      setLinkFundingError(null);
      const account_id = metadata?.accounts?.[0]?.id;
      if (!account_id) {
        setLinkFundingError('No account selected.');
        setFundingLinkToken(null);
        openedFundingRef.current = null;
        return;
      }
      try {
        const r = await fetchWithAuth('/api/brokerage/link-bank-for-funding', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ public_token, plaid_account_id: account_id }),
        });
        if (r.ok) {
          setFundingLinkToken(null);
          openedFundingRef.current = null;
          await fetchStatus();
        } else {
          const d = await r.json().catch(() => ({}));
          setLinkFundingError(d.detail?.message ?? d.detail ?? 'Failed to link bank for funding.');
        }
      } catch {
        setLinkFundingError('Failed to link bank for funding.');
      } finally {
        setFundingLinkToken(null);
        openedFundingRef.current = null;
      }
    },
    onExit: () => {
      setFundingLinkToken(null);
      openedFundingRef.current = null;
    },
  });

  // When we have a linkToken and Plaid is ready, open Link once
  useEffect(() => {
    if (linkToken && ready && open && openedForRef.current !== linkToken) {
      open();
      openedForRef.current = linkToken;
    }
  }, [linkToken, ready, open]);

  useEffect(() => {
    if (fundingLinkToken && readyFundingLink && openFundingLink && openedFundingRef.current !== fundingLinkToken) {
      openFundingLink();
      openedFundingRef.current = fundingLinkToken;
    }
  }, [fundingLinkToken, readyFundingLink, openFundingLink]);

  const handleLinkBank = async () => {
    setConnectError(null);
    setConnectLoading(true);
    try {
      const r = await fetchWithAuth('/api/banking/link-token');
      const d = await r.json();
      if (d.link_token) {
        setLinkToken(d.link_token);
      } else {
        setConnectError(d.detail || d.error || 'Could not start Link.');
        setConnectLoading(false);
      }
    } catch (e) {
      setConnectError('Could not start Link.');
      setConnectLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setDisconnectLoading(true);
    try {
      const r = await fetchWithAuth('/api/banking/disconnect', { method: 'DELETE' });
      if (r.ok || r.status === 204) {
        await fetchStatus();
      }
    } finally {
      setDisconnectLoading(false);
    }
  };

  const handleDisconnectOne = async (connectionId: number) => {
    setDisconnectingId(connectionId);
    try {
      const r = await fetchWithAuth(`/api/banking/connections/${connectionId}`, { method: 'DELETE' });
      if (r.ok || r.status === 204) {
        await fetchStatus();
      }
    } finally {
      setDisconnectingId(null);
    }
  };

  const handleLinkBankForFunding = async () => {
    setLinkFundingError(null);
    try {
      const r = await fetchWithPaymentHandling('/api/brokerage/funding-link-token');
      const d = await r.json();
      if (r.ok && d.link_token) {
        setFundingLinkToken(d.link_token);
      } else {
        setLinkFundingError(d.detail?.message ?? d.detail ?? 'Could not start Link for funding.');
      }
    } catch {
      setLinkFundingError('Could not start Link for funding.');
    }
  };

  const handleFund = async (e: React.FormEvent) => {
    e.preventDefault();
    setFundError(null);
    if (!fundAmount || Number(fundAmount) <= 0) {
      setFundError('Enter a valid amount.');
      return;
    }
    setFundLoading(true);
    try {
      const body: { amount: string; relationship_id?: string } = { amount: fundAmount };
      if (linkedBanks.length >= 1) {
        const sel = linkedBanks.length === 1
          ? linkedBanks[0]
          : (linkedBanks.find((b) => b.relationship_id === withdrawRelationshipId) ?? linkedBanks[0]);
        body.relationship_id = sel.relationship_id;
      }
      const r = await fetchWithAuth('/api/brokerage/fund', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const d = await r.json().catch(() => ({}));
      if (r.ok) {
        setFundAmount('');
        await fetchStatus();
      } else {
        setFundError(d.detail?.message ?? d.detail ?? 'Fund failed.');
      }
    } catch {
      setFundError('Fund failed.');
    } finally {
      setFundLoading(false);
    }
  };

  const handleWithdraw = async (e: React.FormEvent) => {
    e.preventDefault();
    setWithdrawError(null);
    if (!withdrawAmount || Number(withdrawAmount) <= 0) {
      setWithdrawError('Enter a valid amount.');
      return;
    }
    if (!withdrawRelationshipId) {
      setWithdrawError('Select a bank to withdraw to.');
      return;
    }
    setWithdrawLoading(true);
    try {
      const r = await fetchWithAuth('/api/brokerage/withdraw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: withdrawAmount, relationship_id: withdrawRelationshipId }),
      });
      const d = await r.json().catch(() => ({}));
      if (r.ok) {
        setWithdrawAmount('');
        setWithdrawRelationshipId(linkedBanks[0]?.relationship_id ?? '');
        await fetchStatus();
      } else {
        setWithdrawError(d.detail?.message ?? d.detail ?? 'Withdraw failed.');
      }
    } catch {
      setWithdrawError('Withdraw failed.');
    } finally {
      setWithdrawLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Link accounts</h2>
        <p className="text-muted-foreground">Connect bank accounts for balances and transactions in trading and portfolio views.</p>
      </div>

      <PermissionGate permission={PERMISSION_TRADE_VIEW}>
        {loading ? (
          <Card className="border-slate-700 bg-slate-800/50">
            <CardContent className="p-8 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
            </CardContent>
          </Card>
        ) : error ? (
          <Card className="border-slate-700 bg-slate-800/50">
            <CardContent className="p-6 text-muted-foreground">{error}</CardContent>
          </Card>
        ) : !status?.plaid_enabled ? (
          <Card className="border-slate-700 bg-slate-800/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Landmark className="h-5 w-5 text-slate-400" />
                Bank linking
              </CardTitle>
            </CardHeader>
            <CardContent className="text-muted-foreground">
              Bank linking (Plaid) is not enabled for this environment. Contact your administrator.
            </CardContent>
          </Card>
        ) : (
          <Card className="border-slate-700 bg-slate-800/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Landmark className="h-5 w-5 text-emerald-400" />
                Bank account (Plaid)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {status.connected ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-emerald-400">
                    <CheckCircle2 className="h-5 w-5" />
                    <span>Bank account{plaidConnections.length !== 1 ? 's' : ''} connected</span>
                  </div>
                  {plaidConnections.length > 0 && (
                    <ul className="space-y-2">
                      {plaidConnections.map((c: PlaidConnectionItem) => (
                        <li
                          key={c.id}
                          className="flex items-center justify-between rounded-lg border border-slate-600 bg-slate-900/50 px-3 py-2"
                        >
                          <span className="text-sm text-slate-300">
                            Bank {c.item_id_masked ?? `#${c.id}`}
                            {c.created_at && (
                              <span className="ml-2 text-slate-500 text-xs">
                                linked {new Date(c.created_at).toLocaleDateString()}
                              </span>
                            )}
                          </span>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-slate-400 hover:text-red-400"
                            onClick={() => handleDisconnectOne(c.id)}
                            disabled={disconnectingId === c.id}
                          >
                            {disconnectingId === c.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Unplug className="h-4 w-4" />}
                          </Button>
                        </li>
                      ))}
                    </ul>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <Button
                      onClick={handleLinkBank}
                      disabled={connectLoading}
                      variant="outline"
                      size="sm"
                    >
                      {connectLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Link2 className="h-4 w-4 mr-2" />}
                      Link another bank
                    </Button>
                    {plaidConnections.length > 1 && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleDisconnect}
                        disabled={disconnectLoading}
                      >
                        {disconnectLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Unplug className="h-4 w-4 mr-2" />}
                        Disconnect all
                      </Button>
                    )}
                  </div>
                </div>
              ) : (
                <div>
                  <Button
                    onClick={handleLinkBank}
                    disabled={connectLoading}
                    className="bg-emerald-600 hover:bg-emerald-700"
                  >
                    {connectLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Link2 className="h-4 w-4 mr-2" />}
                    Link bank
                  </Button>
                </div>
              )}
              {connectError && <p className="text-sm text-red-400">{connectError}</p>}
            </CardContent>
          </Card>
        )}

        {brokerageStatus !== null && (
          <Card className="border-slate-700 bg-slate-800/50 mt-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Briefcase className="h-5 w-5 text-slate-400" />
                Trading account (Alpaca)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {brokerageStatus.has_account ? (
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={brokerageStatus.status === 'ACTIVE' ? 'text-emerald-400' : 'text-amber-400'}>
                      {brokerageStatus.status === 'ACTIVE' ? <CheckCircle2 className="h-5 w-5" /> : <Landmark className="h-5 w-5" />}
                    </span>
                    <span>
                      {brokerageStatus.status === 'ACTIVE'
                        ? `Active${brokerageStatus.account_number ? ` · #${brokerageStatus.account_number}` : ''}`
                        : brokerageStatus.status ?? 'Pending'}
                    </span>
                  </div>
                  {(brokerageStatus.status != null || brokerageStatus.crypto_status != null) && (
                    <p className="text-sm text-muted-foreground">
                      Equities: <span className="capitalize">{(brokerageStatus.status ?? '—').toLowerCase()}</span>
                      {brokerageStatus.crypto_status != null && (
                        <> · Crypto: <span className="capitalize">{brokerageStatus.crypto_status.toLowerCase()}</span></>
                      )}
                    </p>
                  )}
                  {brokerageStatus.action_required_reason && (
                    <p className="text-sm text-amber-400 mt-1">{brokerageStatus.action_required_reason}</p>
                  )}
                </div>
              ) : (
                <p className="text-muted-foreground">No brokerage account. Open one in Settings → Trading account.</p>
              )}
            </CardContent>
          </Card>
        )}

        {brokerageStatus?.status === 'ACTIVE' && (
          <Card className="border-slate-700 bg-slate-800/50 mt-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Landmark className="h-5 w-5 text-slate-400" />
                Bank accounts for funding
              </CardTitle>
              <p className="text-sm text-muted-foreground">Link a bank to deposit or withdraw to/from your brokerage account.</p>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">Linked banks</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleLinkBankForFunding}
                    disabled={!!fundingLinkToken}
                  >
                    {fundingLinkToken ? <Loader2 className="h-4 w-4 animate-spin" /> : <Link2 className="h-4 w-4 mr-2" />}
                    Link bank for funding
                  </Button>
                </div>
                {linkFundingError && <p className="text-sm text-red-400 mb-2">{linkFundingError}</p>}
                {linkedBanks.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No linked banks. Link a bank to fund or withdraw.</p>
                ) : (
                  <ul className="text-sm space-y-1">
                    {linkedBanks.map((b) => (
                      <li key={b.relationship_id} className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                        {b.nickname || `Bank · ${(b.relationship_id ?? '').slice(-8)}`}
                        {b.status && <span className="text-muted-foreground">({b.status})</span>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <form onSubmit={handleFund} className="space-y-2">
                <Label>Deposit to brokerage (USD)</Label>
                <div className="flex gap-2 flex-wrap">
                  <input
                    type="text"
                    inputMode="decimal"
                    placeholder="Amount"
                    value={fundAmount}
                    onChange={(e) => setFundAmount(e.target.value)}
                    className="flex-1 min-w-[120px] rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-sm"
                  />
                  <Button type="submit" disabled={fundLoading || linkedBanks.length === 0}>
                    {fundLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    Deposit
                  </Button>
                </div>
                {fundError && <p className="text-sm text-red-400">{fundError}</p>}
              </form>

              <form onSubmit={handleWithdraw} className="space-y-2">
                <Label>Withdraw to bank (USD)</Label>
                {linkedBanks.length > 0 && (
                  <select
                    value={withdrawRelationshipId}
                    onChange={(e) => setWithdrawRelationshipId(e.target.value)}
                    className="mb-2 w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-sm"
                  >
                    <option value="">Select bank</option>
                    {linkedBanks.map((b) => (
                      <option key={b.relationship_id} value={b.relationship_id}>
                        {b.nickname || `Bank · ${(b.relationship_id ?? '').slice(-8)}`}
                      </option>
                    ))}
                  </select>
                )}
                <div className="flex gap-2 flex-wrap">
                  <input
                    type="text"
                    inputMode="decimal"
                    placeholder="Amount"
                    value={withdrawAmount}
                    onChange={(e) => setWithdrawAmount(e.target.value)}
                    className="flex-1 min-w-[120px] rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-sm"
                  />
                  <Button type="submit" variant="outline" disabled={withdrawLoading || linkedBanks.length === 0}>
                    {withdrawLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    Withdraw
                  </Button>
                </div>
                {withdrawError && <p className="text-sm text-red-400">{withdrawError}</p>}
              </form>
            </CardContent>
          </Card>
        )}
      </PermissionGate>
    </div>
  );
}
