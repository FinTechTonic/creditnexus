/**
 * Brokerage onboarding: apply for Alpaca account, check status, upload documents when ACTION_REQUIRED.
 * Uses /api/brokerage/account/status, /api/brokerage/account/apply, /api/brokerage/account/documents.
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { fetchWithAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';
import { Loader2, CheckCircle2, AlertTriangle, FileUp, Send } from 'lucide-react';

interface BrokerageStatus {
  has_account: boolean;
  status?: string;
  alpaca_account_id?: string;
  account_number?: string;
  action_required_reason?: string;
  currency: string;
}

export function BrokerageOnboarding() {
  const [status, setStatus] = useState<BrokerageStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [applyLoading, setApplyLoading] = useState(false);
  const [docLoading, setDocLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [documentType, setDocumentType] = useState('identity_document');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

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

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleApply = async () => {
    setApplyLoading(true);
    setError(null);
    setMessage(null);
    try {
      const r = await fetchWithAuth(resolveApiUrl('/api/brokerage/account/apply'), {
        method: 'POST',
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

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Trading account (Alpaca)</h2>
        <p className="text-muted-foreground">
          Open a brokerage account to place trades. Complete the application and upload any requested documents.
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
              <>Brokerage account</>
            )}
          </CardTitle>
          <CardDescription>
            {isActive && status?.account_number && `Account #${status.account_number}`}
            {isActionRequired && status?.action_required_reason}
            {isPending && 'Your application is under review. Status updates automatically.'}
            {!status?.has_account && 'Apply to open a brokerage account and start trading.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!status?.has_account && (
            <Button
              onClick={handleApply}
              disabled={applyLoading}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              {applyLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Send className="h-4 w-4 mr-2" />}
              Apply for trading account
            </Button>
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

          {!loading && status?.has_account && (
            <Button variant="outline" size="sm" onClick={fetchStatus}>
              Refresh status
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
