/**
 * Brokerage onboarding: Plaid KYC (identity) + Alpaca agreements + apply.
 * Flow: 1) Link Plaid (brokerage link-token) for identity verification
 *       2) Review prefill from Plaid
 *       3) Accept Customer Agreement and Margin Agreement (required by Alpaca)
 *       4) Submit application with agreements and use_plaid_kyc
 */

import { useState, useEffect, useRef } from 'react';
import { usePlaidLink } from 'react-plaid-link';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { fetchWithAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';
import { Loader2, CheckCircle2, AlertTriangle, FileUp, Send, Link2, FileText } from 'lucide-react';

interface BrokerageStatus {
  has_account: boolean;
  status?: string;
  alpaca_account_id?: string;
  account_number?: string;
  action_required_reason?: string;
  currency: string;
}

interface Prefill {
  given_name?: string;
  family_name?: string;
  street_address?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
}

const ALPACA_CUSTOMER_AGREEMENT_URL = 'https://alpaca.markets/disclosures';
const ALPACA_MARGIN_AGREEMENT_URL = 'https://alpaca.markets/disclosures';

export function BrokerageOnboarding() {
  const [status, setStatus] = useState<BrokerageStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [applyLoading, setApplyLoading] = useState(false);
  const [docLoading, setDocLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [documentType, setDocumentType] = useState('identity_document');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Plaid KYC flow
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [prefill, setPrefill] = useState<Prefill | null>(null);
  const [prefillLoading, setPrefillLoading] = useState(false);
  const [agreedCustomer, setAgreedCustomer] = useState(false);
  const [agreedMargin, setAgreedMargin] = useState(false);
  const [agreedAt, setAgreedAt] = useState<string | null>(null);
  const openedForRef = useRef<string | null>(null);

  const fetchStatus = async () => {
    setError(null);
    try {
      const r = await fetchWithAuth(resolveApiUrl('/api/brokerage/account/status'));
      if (r.ok) {
        const d = await r.json();
        setStatus(d);
      } else {
        setStatus(null);
        setError('Failed to load brokerage status.');
      }
    } catch (e) {
      setStatus(null);
      setError('Failed to load brokerage status.');
    } finally {
      setLoading(false);
    }
  };

  const fetchPrefill = async () => {
    setPrefillLoading(true);
    try {
      const r = await fetchWithAuth(resolveApiUrl('/api/brokerage/prefill'));
      if (r.ok) {
        const d = await r.json();
        setPrefill(d.prefill && Object.keys(d.prefill).length > 0 ? d.prefill : null);
      } else {
        setPrefill(null);
      }
    } catch {
      setPrefill(null);
    } finally {
      setPrefillLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  // When status loaded and no account yet, fetch prefill once (user may have linked Plaid earlier)
  const prefillFetchedRef = useRef(false);
  useEffect(() => {
    if (!loading && status && !status.has_account && !prefillFetchedRef.current) {
      prefillFetchedRef.current = true;
      fetchPrefill();
    }
  }, [loading, status?.has_account]);

  // Plaid Link for brokerage (identity verification)
  const { open, ready } = usePlaidLink({
    token: linkToken,
    onSuccess: async (public_token: string) => {
      setError(null);
      setApplyLoading(true);
      try {
        const r = await fetchWithAuth(resolveApiUrl('/api/banking/connect'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ public_token }),
        });
        if (r.ok) {
          setLinkToken(null);
          openedForRef.current = null;
          await fetchPrefill();
        } else {
          const d = await r.json().catch(() => ({}));
          setError(d.detail || 'Failed to connect bank for identity verification.');
        }
      } catch (e) {
        setError('Failed to connect bank.');
      } finally {
        setApplyLoading(false);
      }
    },
    onExit: () => {
      setLinkToken(null);
      openedForRef.current = null;
    },
  });

  useEffect(() => {
    if (linkToken && ready && open && openedForRef.current !== linkToken) {
      open();
      openedForRef.current = linkToken;
    }
  }, [linkToken, ready, open]);

  const handleGetPlaidLinkToken = async () => {
    setError(null);
    try {
      const r = await fetchWithAuth(resolveApiUrl('/api/brokerage/link-token'));
      const d = await r.json().catch(() => ({}));
      if (d.link_token) {
        setLinkToken(d.link_token);
      } else {
        setError(d.detail || d.error || 'Could not start identity verification.');
      }
    } catch (e) {
      setError('Could not start identity verification.');
    }
  };

  const handleAgreementChange = (customer: boolean, margin: boolean) => {
    setAgreedCustomer(customer);
    setAgreedMargin(margin);
    if (customer && margin && !agreedAt) {
      setAgreedAt(new Date().toISOString());
    }
  };

  const handleApply = async (usePlaidKyc: boolean) => {
    setApplyLoading(true);
    setError(null);
    setMessage(null);
    try {
      const signedAt = agreedAt || new Date().toISOString();
      const body = {
        use_plaid_kyc: usePlaidKyc,
        agreements: [
          { agreement: 'customer_agreement', signed_at: signedAt, ip_address: '0.0.0.0' },
          { agreement: 'margin_agreement', signed_at: signedAt, ip_address: '0.0.0.0' },
        ],
        prefill: prefill || undefined,
      };
      const r = await fetchWithAuth(resolveApiUrl('/api/brokerage/account/apply'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const d = await r.json().catch(() => ({}));
      if (r.ok) {
        setMessage(d.message || 'Application submitted. Check status for updates.');
        await fetchStatus();
      } else {
        setError(d.detail || d.message || 'Failed to submit application.');
      }
    } catch (e) {
      setError('Failed to submit application.');
    } finally {
      setApplyLoading(false);
    }
  };

  const handleDocumentUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !status?.has_account) return;
    setDocLoading(true);
    setError(null);
    setMessage(null);
    try {
      const form = new FormData();
      form.append('document_type', documentType);
      form.append('file', selectedFile);
      const r = await fetchWithAuth(resolveApiUrl('/api/brokerage/account/documents'), {
        method: 'POST',
        body: form,
      });
      const d = await r.json().catch(() => ({}));
      if (r.ok) {
        setMessage(d.message || 'Document submitted for review.');
        setSelectedFile(null);
        await fetchStatus();
      } else {
        setError(d.detail || d.message || 'Failed to upload document.');
      }
    } catch (e) {
      setError('Failed to upload document.');
    } finally {
      setDocLoading(false);
    }
  };

  if (loading) {
    return (
      <Card className="border-slate-700 bg-slate-800/50">
        <CardContent className="p-8 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </CardContent>
      </Card>
    );
  }

  const isActive = status?.status === 'ACTIVE';
  const isActionRequired = status?.status === 'ACTION_REQUIRED';
  const isPending = status?.has_account && !isActive && !isActionRequired;
  const canApplyPlaid = !status?.has_account && prefill !== null && agreedCustomer && agreedMargin;
  const canApplyWithoutPlaid = !status?.has_account && agreedCustomer && agreedMargin;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Trading account (Alpaca)</h2>
        <p className="text-muted-foreground">
          Verify your identity with Plaid, accept the required agreements, and submit to open a brokerage account.
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {message && (
        <Alert className="border-emerald-700 bg-emerald-900/20">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}

      <Card className="border-slate-700 bg-slate-800/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            {isActive ? (
              <>
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                Trading account active
              </>
            ) : isActionRequired ? (
              <>
                <AlertTriangle className="h-5 w-5 text-amber-400" />
                Action required
              </>
            ) : isPending ? (
              <>Application in progress</>
            ) : (
              <>Open brokerage account (Plaid KYC + agreements)</>
            )}
          </CardTitle>
          <CardDescription>
            {isActive && status?.account_number && `Account #${status.account_number}`}
            {isActionRequired && status?.action_required_reason}
            {isPending && 'Your application is under review. Status updates automatically.'}
            {!status?.has_account && 'Complete the steps below to apply.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {!status?.has_account && (
            <>
              {/* Step 1: Plaid identity verification */}
              <div className="space-y-2">
                <Label className="text-base font-medium flex items-center gap-2">
                  <Link2 className="h-4 w-4" />
                  Step 1: Verify identity with your bank (Plaid)
                </Label>
                <p className="text-sm text-muted-foreground">
                  Link a bank account to verify your identity. We use Plaid; no account access is required for verification.
                </p>
                {prefill ? (
                  <div className="flex items-center gap-2 text-emerald-400">
                    <CheckCircle2 className="h-5 w-5" />
                    <span>Identity verified</span>
                  </div>
                ) : (
                  <Button
                    onClick={handleGetPlaidLinkToken}
                    disabled={!!linkToken || applyLoading}
                    variant="outline"
                    className="border-emerald-600 text-emerald-400 hover:bg-emerald-900/20"
                  >
                    {applyLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Link2 className="h-4 w-4 mr-2" />}
                    Verify identity with Plaid
                  </Button>
                )}
              </div>

              {/* Step 2: Prefill from Plaid (optional; show agreements even without prefill) */}
              {(prefill !== null || prefillLoading || (prefill === null && !prefillLoading)) && (
                <div className="space-y-2 border-t border-slate-700 pt-4">
                  <Label className="text-base font-medium flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Step 2: Your information (from Plaid)
                  </Label>
                  {prefillLoading ? (
                    <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                  ) : prefill && Object.keys(prefill).length > 0 ? (
                    <div className="grid gap-2 text-sm text-muted-foreground">
                      {(prefill.given_name || prefill.family_name) && (
                        <p>Name: {[prefill.given_name, prefill.family_name].filter(Boolean).join(' ')}</p>
                      )}
                      {(prefill.street_address || prefill.city) && (
                        <p>
                          Address: {[prefill.street_address, prefill.city, prefill.state, prefill.postal_code, prefill.country]
                            .filter(Boolean)
                            .join(', ')}
                        </p>
                      )}
                    </div>
                  ) : !prefillLoading ? (
                    <p className="text-sm text-muted-foreground">No Plaid identity linked. You can still apply without Plaid (admin/legacy flow) below.</p>
                  ) : null}
                </div>
              )}

              {/* Step 3: Alpaca agreements (required for all) */}
              {(
                <div className="space-y-3 border-t border-slate-700 pt-4">
                  <Label className="text-base font-medium flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Step 3: Accept required agreements
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Alpaca requires acceptance of the Customer Agreement and Margin Agreement before opening an account.
                  </p>
                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <Checkbox
                        id="customer_agreement"
                        checked={agreedCustomer}
                        onCheckedChange={(checked) => handleAgreementChange(!!checked, agreedMargin)}
                      />
                      <label htmlFor="customer_agreement" className="text-sm leading-tight cursor-pointer">
                        I agree to the{' '}
                        <a href={ALPACA_CUSTOMER_AGREEMENT_URL} target="_blank" rel="noopener noreferrer" className="underline text-emerald-400">
                          Customer Agreement
                        </a>
                      </label>
                    </div>
                    <div className="flex items-start gap-3">
                      <Checkbox
                        id="margin_agreement"
                        checked={agreedMargin}
                        onCheckedChange={(checked) => handleAgreementChange(agreedCustomer, !!checked)}
                      />
                      <label htmlFor="margin_agreement" className="text-sm leading-tight cursor-pointer">
                        I agree to the{' '}
                        <a href={ALPACA_MARGIN_AGREEMENT_URL} target="_blank" rel="noopener noreferrer" className="underline text-emerald-400">
                          Margin Agreement
                        </a>
                      </label>
                    </div>
                  </div>
                </div>
              )}

              {/* Step 4: Submit */}
              <div className="border-t border-slate-700 pt-4 space-y-2">
                {prefill !== null && (
                  <Button
                    onClick={() => handleApply(true)}
                    disabled={!canApplyPlaid || applyLoading}
                    className="bg-emerald-600 hover:bg-emerald-700"
                  >
                    {applyLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Send className="h-4 w-4 mr-2" />}
                    Submit application (with Plaid identity)
                  </Button>
                )}
                <Button
                  onClick={() => handleApply(false)}
                  disabled={!canApplyWithoutPlaid || applyLoading}
                  variant={prefill !== null ? 'outline' : 'default'}
                  className={prefill === null ? 'bg-emerald-600 hover:bg-emerald-700' : ''}
                >
                  {applyLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Send className="h-4 w-4 mr-2" />}
                  {prefill !== null ? 'Submit without Plaid (admin/legacy)' : 'Submit application'}
                </Button>
                {(!agreedCustomer || !agreedMargin) && (
                  <p className="text-sm text-muted-foreground">Accept both agreements above to submit.</p>
                )}
              </div>
            </>
          )}

          {isActionRequired && (
            <form onSubmit={handleDocumentUpload} className="space-y-4 border-t border-slate-700 pt-4">
              <div>
                <Label>Document type</Label>
                <Input
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value)}
                  placeholder="e.g. identity_document, address_verification"
                  className="mt-1"
                />
              </div>
              <div>
                <Label>File (PDF or image)</Label>
                <Input
                  type="file"
                  accept=".pdf,image/*"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                  className="mt-1"
                />
              </div>
              <Button type="submit" disabled={!selectedFile || docLoading}>
                {docLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <FileUp className="h-4 w-4 mr-2" />}
                Upload document
              </Button>
            </form>
          )}

          {status?.has_account && !loading && (
            <Button variant="outline" size="sm" onClick={fetchStatus}>
              Refresh status
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
