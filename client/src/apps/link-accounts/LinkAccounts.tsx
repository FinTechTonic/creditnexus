/**
 * Link Accounts – connect bank (Plaid) and other data sources.
 * Uses server-derived status (plaid_enabled, connected) only; no secrets in client config.
 * Plaid is not a sign-in method; this is a post-login "Link accounts" flow.
 */

import { useEffect, useRef, useState } from 'react';
import { usePlaidLink } from 'react-plaid-link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { fetchWithAuth } from '@/context/AuthContext';
import { PermissionGate } from '@/components/PermissionGate';
import { PERMISSION_TRADE_VIEW } from '@/utils/permissions';
import { Landmark, Link2, Loader2, Unplug, CheckCircle2 } from 'lucide-react';

interface BankingStatus {
  plaid_enabled: boolean;
  connected: boolean;
}

export function LinkAccounts() {
  const [status, setStatus] = useState<BankingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [connectLoading, setConnectLoading] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [disconnectLoading, setDisconnectLoading] = useState(false);
  const openedForRef = useRef<string | null>(null);

  const fetchStatus = async () => {
    setError(null);
    try {
      const r = await fetchWithAuth('/api/banking/status');
      if (r.ok) {
        const d = await r.json();
        setStatus({ plaid_enabled: d.plaid_enabled, connected: d.connected });
      } else {
        if (r.status === 403) {
          setStatus(null);
          setError('You don’t have permission to manage bank connections.');
        } else {
          setError('Failed to load banking status.');
        }
      }
    } catch (e) {
      setError('Failed to load banking status.');
      setStatus(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

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

  // When we have a linkToken and Plaid is ready, open Link once
  useEffect(() => {
    if (linkToken && ready && open && openedForRef.current !== linkToken) {
      open();
      openedForRef.current = linkToken;
    }
  }, [linkToken, ready, open]);

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
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-emerald-400">
                    <CheckCircle2 className="h-5 w-5" />
                    <span>Bank account connected</span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDisconnect}
                    disabled={disconnectLoading}
                  >
                    {disconnectLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Unplug className="h-4 w-4 mr-2" />}
                    Disconnect
                  </Button>
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
      </PermissionGate>
    </div>
  );
}
