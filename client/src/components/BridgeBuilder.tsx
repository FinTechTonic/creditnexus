/**
 * Bridge Builder: trade ChallengeCoin NFTs across blockchains.
 * - Fetches /api/challenge-coins/my-tokens
 * - POST /api/bridge-builder/create-trade → then sign & send via MetaMask or paste signed hex
 * - POST /api/bridge-builder/execute-trade (with signed_lock_tx or lock_tx_hash)
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { fetchWithAuth } from '@/context/AuthContext';
import { ArrowRight, Lock, Loader2, Coins } from 'lucide-react';

interface TokenRow {
  token_id: number;
  asset_id: string;
  deal_id: string;
  asset_type: string;
  principal_amount: string;
  locked?: boolean;
}

const CHAINS: { value: string; label: string }[] = [
  { value: '1', label: 'Ethereum Mainnet' },
  { value: '8453', label: 'Base' },
  { value: '137', label: 'Polygon' },
  { value: '1337', label: 'Local / Hardhat' },
];

export function BridgeBuilder() {
  const [tokens, setTokens] = useState<TokenRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedToken, setSelectedToken] = useState<number | null>(null);
  const [targetChain, setTargetChain] = useState<string>('8453');
  const [targetAddress, setTargetAddress] = useState('');
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [pendingTrade, setPendingTrade] = useState<{ trade_id: number; lock_transaction: Record<string, unknown> } | null>(null);
  const [signedHex, setSignedHex] = useState('');
  const [executeLoading, setExecuteLoading] = useState(false);
  const [executeError, setExecuteError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<Record<string, unknown> | null>(null);

  const loadTokens = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchWithAuth('/api/challenge-coins/my-tokens')
      .then((r) => (r.ok ? r.json() : { tokens: [] }))
      .then((d) => setTokens(Array.isArray(d.tokens) ? d.tokens : []))
      .catch((e) => { setError(String(e)); setTokens([]); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadTokens(); }, [loadTokens]);

  const handleCreateTrade = async () => {
    if (selectedToken == null || !targetAddress.trim()) return;
    setCreateLoading(true);
    setCreateError(null);
    setPendingTrade(null);
    setLastResult(null);
    try {
      const res = await fetchWithAuth('/api/bridge-builder/create-trade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token_id: selectedToken,
          target_chain_id: parseInt(targetChain, 10),
          target_address: targetAddress.trim(),
          trade_type: 'transfer',
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText || 'Create failed');
      setPendingTrade({ trade_id: data.trade_id, lock_transaction: data.lock_transaction || {} });
    } catch (e: unknown) {
      setCreateError(e instanceof Error ? e.message : String(e));
    } finally {
      setCreateLoading(false);
    }
  };

  const sendWithMetaMask = async () => {
    if (!pendingTrade || !window.ethereum) {
      setExecuteError('MetaMask not found. Connect MetaMask or paste the signed transaction hex below.');
      return;
    }
    const tx = pendingTrade.lock_transaction as Record<string, unknown>;
    const p: Record<string, string> = {
      to: String(tx.to ?? ''),
      data: String(tx.data ?? '0x'),
      value: tx.value != null ? `0x${Number(tx.value).toString(16)}` : '0x0',
      from: String(tx.from ?? ''),
    };
    if (tx.gas != null) p.gas = `0x${Number(tx.gas).toString(16)}`;
    if (tx.gasPrice != null) p.gasPrice = `0x${Number(tx.gasPrice).toString(16)}`;
    setExecuteLoading(true);
    setExecuteError(null);
    try {
      const hash = (await window.ethereum.request({ method: 'eth_sendTransaction', params: [p] })) as string;
      const res = await fetchWithAuth('/api/bridge-builder/execute-trade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trade_id: pendingTrade.trade_id, lock_tx_hash: hash }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText || 'Execute failed');
      setLastResult(data);
      setPendingTrade(null);
      setSignedHex('');
      loadTokens();
    } catch (e: unknown) {
      setExecuteError(e instanceof Error ? e.message : String(e));
    } finally {
      setExecuteLoading(false);
    }
  };

  const handleExecuteWithSignedHex = async () => {
    if (!pendingTrade || !signedHex.trim()) return;
    setExecuteLoading(true);
    setExecuteError(null);
    try {
      const res = await fetchWithAuth('/api/bridge-builder/execute-trade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trade_id: pendingTrade.trade_id, signed_lock_tx: signedHex.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || res.statusText || 'Execute failed');
      setLastResult(data);
      setPendingTrade(null);
      setSignedHex('');
      loadTokens();
    } catch (e: unknown) {
      setExecuteError(e instanceof Error ? e.message : String(e));
    } finally {
      setExecuteLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-semibold text-slate-100 mb-2">Bridge Builder</h2>
        <p className="text-slate-400">Trade challenge coins across blockchains</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Coins className="h-4 w-4" /> My Tokens</CardTitle>
            <CardDescription>ChallengeCoin NFTs in your wallet</CardDescription>
          </CardHeader>
          <CardContent>
            {loading && <p className="text-muted-foreground">Loading…</p>}
            {error && <p className="text-destructive text-sm">{error}</p>}
            {!loading && !error && tokens.length === 0 && (
              <p className="text-muted-foreground">No challenge coins. Issue some from the securitization flow.</p>
            )}
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {tokens.map((t) => (
                <div
                  key={t.token_id}
                  role="button"
                  tabIndex={0}
                  onClick={() => setSelectedToken(t.token_id)}
                  onKeyDown={(e) => e.key === 'Enter' && setSelectedToken(t.token_id)}
                  className={`p-3 border rounded cursor-pointer ${
                    selectedToken === t.token_id ? 'border-emerald-500 bg-emerald-500/10' : 'border-border'
                  } ${t.locked ? 'opacity-60' : ''}`}
                >
                  <div className="font-medium">{t.asset_id}</div>
                  <div className="text-sm text-muted-foreground">
                    {t.asset_type} • {t.principal_amount} (6 decimals)
                  </div>
                  {t.locked && <span className="text-xs text-amber-500">Locked</span>}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Lock className="h-4 w-4" /> Bridge</CardTitle>
            <CardDescription>Select token, target chain and address</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>Target chain</Label>
              <select
                value={targetChain}
                onChange={(e) => setTargetChain(e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-background border rounded-md"
              >
                {CHAINS.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>
            <div>
              <Label>Target address (0x…)</Label>
              <Input
                placeholder="0x..."
                value={targetAddress}
                onChange={(e) => setTargetAddress(e.target.value)}
                className="mt-1"
              />
            </div>
            <Button
              onClick={handleCreateTrade}
              disabled={selectedToken == null || !targetAddress.trim() || createLoading}
              className="w-full"
            >
              {createLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4 mr-2" />}
              Create Bridge Trade
            </Button>
            {createError && <p className="text-destructive text-sm">{createError}</p>}

            {pendingTrade && (
              <div className="pt-4 border-t space-y-3">
                <p className="text-sm text-muted-foreground">Lock transaction prepared. Sign and send:</p>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={sendWithMetaMask}
                    disabled={executeLoading || !(typeof window !== 'undefined' && window.ethereum)}
                  >
                    {executeLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    Send with MetaMask
                  </Button>
                </div>
                <div>
                  <Label className="text-xs">Or paste signed tx hex (0x…)</Label>
                  <Input
                    placeholder="0x..."
                    value={signedHex}
                    onChange={(e) => setSignedHex(e.target.value)}
                    className="mt-1 font-mono text-sm"
                  />
                  <Button
                    size="sm"
                    className="mt-2"
                    onClick={handleExecuteWithSignedHex}
                    disabled={executeLoading || !signedHex.trim()}
                  >
                    Execute with signed hex
                  </Button>
                </div>
                {executeError && <p className="text-destructive text-sm">{executeError}</p>}
              </div>
            )}

            {lastResult && (
              <div className="pt-2 text-sm text-emerald-600">
                Status: {String(lastResult.status)} • Lock tx: {String(lastResult.lock_tx_hash || '').slice(0, 18)}…
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
