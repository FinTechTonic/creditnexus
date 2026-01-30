/**
 * Bring Your Own Keys (BYOK) – crypto and trading keys only.
 * Alpaca (required to unlock trading), Polygon (market data), Polymarket (prediction markets).
 * Plaid is not BYOK; link bank/brokerage in Link Accounts tab.
 */

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { fetchWithAuth } from '@/context/AuthContext';
import { Key, CheckCircle2, TrendingUp, BarChart3, Loader2 } from 'lucide-react';

interface ByokKeyMeta {
  provider: string;
  provider_type: string | null;
  is_verified: boolean;
  unlocks_trading: boolean;
}

export function BringYourOwnKeys() {
  const [tradingUnlocked, setTradingUnlocked] = useState(false);
  const [keys, setKeys] = useState<ByokKeyMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [alpaca, setAlpaca] = useState({ api_key: '', api_secret: '', paper: true });
  const [polygonApiKey, setPolygonApiKey] = useState('');
  const [polygonSaving, setPolygonSaving] = useState(false);
  const [polymarket, setPolymarket] = useState({ api_key: '', secret: '', passphrase: '', funder_address: '' });
  const [polymarketSaving, setPolymarketSaving] = useState(false);

  const fetchByokState = async () => {
    setError(null);
    try {
      const [unlockedRes, keysRes] = await Promise.all([
        fetchWithAuth('/api/user-settings/byok/trading-unlocked'),
        fetchWithAuth('/api/user-settings/byok/keys'),
      ]);
      if (unlockedRes.ok) {
        const d = await unlockedRes.json();
        setTradingUnlocked(d.unlocked === true);
      }
      if (keysRes.ok) {
        const d = await keysRes.json();
        setKeys(d.keys || []);
      }
    } catch {
      setError('Failed to load BYOK status.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchByokState();
  }, []);

  const hasAlpaca = keys.some((k) => k.provider === 'alpaca');
  const hasPolygon = keys.some((k) => k.provider === 'polygon');
  const hasPolymarket = keys.some((k) => k.provider === 'polymarket');

  const handleSubmitAlpaca = async () => {
    if (!alpaca.api_key || !alpaca.api_secret) {
      setError('Enter API key and secret.');
      return;
    }
    setError(null);
    setSuccess(null);
    setSaving(true);
    try {
      const res = await fetchWithAuth('/api/user-settings/byok/alpaca', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: alpaca.api_key,
          api_secret: alpaca.api_secret,
          paper: alpaca.paper,
        }),
      });
      if (res.status === 402) {
        setError('BYOK access required. Upgrade or pay to configure keys.');
        return;
      }
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        setError(d.detail || 'Invalid Alpaca API key or secret.');
        return;
      }
      setSuccess('Alpaca key saved. Trading is unlocked.');
      setAlpaca({ api_key: '', api_secret: '', paper: true });
      await fetchByokState();
    } catch {
      setError('Failed to save Alpaca key.');
    } finally {
      setSaving(false);
    }
  };

  const handleSubmitPolygon = async () => {
    if (!polygonApiKey.trim()) {
      setError('Enter Polygon API key.');
      return;
    }
    setError(null);
    setSuccess(null);
    setPolygonSaving(true);
    try {
      const res = await fetchWithAuth('/api/user-settings/byok/polygon', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: polygonApiKey.trim() }),
      });
      if (res.status === 402) {
        setError('BYOK access required. Upgrade or pay to configure keys.');
        return;
      }
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        setError(d.detail || 'Invalid Polygon API key.');
        return;
      }
      setSuccess('Polygon key saved.');
      setPolygonApiKey('');
      await fetchByokState();
    } catch {
      setError('Failed to save Polygon key.');
    } finally {
      setPolygonSaving(false);
    }
  };

  const handleSubmitPolymarket = async () => {
    if (!polymarket.api_key.trim() || !polymarket.secret || !polymarket.passphrase) {
      setError('Enter API key, secret, and passphrase.');
      return;
    }
    setError(null);
    setSuccess(null);
    setPolymarketSaving(true);
    try {
      const res = await fetchWithAuth('/api/user-settings/byok/polymarket', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: polymarket.api_key.trim(),
          secret: polymarket.secret,
          passphrase: polymarket.passphrase,
          ...(polymarket.funder_address?.trim() && { funder_address: polymarket.funder_address.trim() }),
        }),
      });
      if (res.status === 402) {
        setError('BYOK access required. Upgrade or pay to configure keys.');
        return;
      }
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        setError(d.detail || 'Failed to save Polymarket credentials.');
        return;
      }
      setSuccess('Polymarket credentials saved.');
      setPolymarket({ api_key: '', secret: '', passphrase: '' });
      await fetchByokState();
    } catch {
      setError('Failed to save Polymarket credentials.');
    } finally {
      setPolymarketSaving(false);
    }
  };

  const handleRemoveProvider = async (provider: string) => {
    if (!confirm(`Remove ${provider} key?`)) return;
    setError(null);
    try {
      const res = await fetchWithAuth(`/api/user-settings/byok/${provider}`, { method: 'DELETE' });
      if (res.ok) await fetchByokState();
      else setError('Failed to remove key.');
    } catch {
      setError('Failed to remove key.');
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-slate-400 flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              Bring Your Own Keys
            </CardTitle>
            {tradingUnlocked && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/20 px-3 py-1 text-sm font-medium text-emerald-400">
                <CheckCircle2 className="h-4 w-4" /> Trading unlocked
              </span>
            )}
          </div>
          <CardDescription>
            Configure your own API keys for trading and market data. Link your bank and brokerage accounts in the Link Accounts tab.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {error && (
            <p className="text-amber-500 text-sm">{error}</p>
          )}
          {success && (
            <p className="text-emerald-500 text-sm">{success}</p>
          )}

          {/* Alpaca – required to unlock trading */}
          <div className="space-y-3 rounded-lg border border-slate-700 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-slate-400" />
                <Label className="font-medium">Alpaca (Trading)</Label>
                {hasAlpaca && <span className="text-xs text-slate-400">Configured</span>}
              </div>
              {hasAlpaca && (
                <Button variant="ghost" size="sm" onClick={() => handleRemoveProvider('alpaca')}>
                  Remove
                </Button>
              )}
            </div>
            {!hasAlpaca && (
              <>
                <p className="text-xs text-slate-400">Add your Alpaca Trading API key to unlock trading. Paper or live.</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  <Input
                    placeholder="API Key"
                    type="password"
                    value={alpaca.api_key}
                    onChange={(e) => setAlpaca({ ...alpaca, api_key: e.target.value })}
                  />
                  <Input
                    placeholder="API Secret"
                    type="password"
                    value={alpaca.api_secret}
                    onChange={(e) => setAlpaca({ ...alpaca, api_secret: e.target.value })}
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    id="alpaca-paper"
                    checked={alpaca.paper}
                    onCheckedChange={(checked) => setAlpaca({ ...alpaca, paper: checked })}
                  />
                  <Label htmlFor="alpaca-paper">Paper / sandbox</Label>
                </div>
                <Button onClick={handleSubmitAlpaca} disabled={saving}>
                  {saving ? 'Saving…' : 'Save Alpaca key'}
                </Button>
              </>
            )}
          </div>

          {/* Polygon – market data */}
          <div className="space-y-3 rounded-lg border border-slate-700 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-slate-400" />
                <Label className="font-medium">Polygon (market data)</Label>
                {hasPolygon && <span className="text-xs text-slate-400">Configured</span>}
              </div>
              {hasPolygon && (
                <Button variant="ghost" size="sm" onClick={() => handleRemoveProvider('polygon')}>
                  Remove
                </Button>
              )}
            </div>
            {!hasPolygon && (
              <>
                <p className="text-xs text-slate-400">Add your Polygon API key for market data (LangAlpha, stock analysis).</p>
                <div className="flex gap-2">
                  <Input
                    placeholder="Polygon API Key"
                    type="password"
                    value={polygonApiKey}
                    onChange={(e) => setPolygonApiKey(e.target.value)}
                  />
                  <Button onClick={handleSubmitPolygon} disabled={polygonSaving}>
                    {polygonSaving ? 'Saving…' : 'Save'}
                  </Button>
                </div>
              </>
            )}
          </div>

          {/* Polymarket – prediction markets */}
          <div className="space-y-3 rounded-lg border border-slate-700 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-slate-400" />
                <Label className="font-medium">Polymarket (prediction markets)</Label>
                {hasPolymarket && <span className="text-xs text-slate-400">Configured</span>}
              </div>
              {hasPolymarket && (
                <Button variant="ghost" size="sm" onClick={() => handleRemoveProvider('polymarket')}>
                  Remove
                </Button>
              )}
            </div>
            {!hasPolymarket && (
              <>
                <p className="text-xs text-slate-400">Add Polymarket L2 credentials (api_key, secret, passphrase) for CLOB prediction-market trading. Derive from your wallet or Polymarket settings.</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  <Input
                    placeholder="API Key"
                    type="password"
                    value={polymarket.api_key}
                    onChange={(e) => setPolymarket({ ...polymarket, api_key: e.target.value })}
                  />
                  <Input
                    placeholder="Secret"
                    type="password"
                    value={polymarket.secret}
                    onChange={(e) => setPolymarket({ ...polymarket, secret: e.target.value })}
                  />
                  <Input
                    placeholder="Passphrase"
                    type="password"
                    value={polymarket.passphrase}
                    onChange={(e) => setPolymarket({ ...polymarket, passphrase: e.target.value })}
                  />
                  <Input
                    placeholder="Funder address (Polygon proxy/Safe, required for orders)"
                    value={polymarket.funder_address}
                    onChange={(e) => setPolymarket({ ...polymarket, funder_address: e.target.value })}
                    className="sm:col-span-2"
                  />
                </div>
                <Button onClick={handleSubmitPolymarket} disabled={polymarketSaving}>
                  {polymarketSaving ? 'Saving…' : 'Save Polymarket credentials'}
                </Button>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
