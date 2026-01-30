import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { SignaturePad } from '@/components/ui/SignaturePad';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

interface PortalStatus {
  document_title?: string;
  signer_name?: string;
  signer_email?: string;
  status?: 'pending' | 'completed' | 'expired';
  expires_at?: string | null;
}

export function SignerPortal() {
  const { token } = useParams<{ token: string }>();
  const [status, setStatus] = useState<PortalStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [signatureData, setSignatureData] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [completed, setCompleted] = useState(false);

  useEffect(() => {
    if (!token) {
      setError('Missing signing token.');
      setLoading(false);
      return;
    }

    const loadStatus = async () => {
      setLoading(true);
      setError(null);
      try {
        // Backend endpoint to be implemented in Phase 2:
        // GET /api/signatures/portal/{token}
        const res = await fetchWithAuth(`/api/signatures/portal/${token}`);
        if (!res.ok) {
          throw new Error('Failed to load signing request.');
        }
        const data = await res.json();
        setStatus(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load signing request.');
      } finally {
        setLoading(false);
      }
    };

    loadStatus();
  }, [token]);

  const handleSubmit = async () => {
    if (!token || !signatureData) {
      setError('Please provide a signature before submitting.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      // Backend endpoint to be implemented in Phase 2:
      // POST /api/signatures/portal/{token}/sign
      const res = await fetchWithAuth(`/api/signatures/portal/${token}/sign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signature: signatureData }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const msg = data.detail?.message || data.detail || data.message || 'Failed to submit signature.';
        throw new Error(msg);
      }
      setCompleted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit signature.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-50">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <Card className="max-w-lg w-full bg-slate-900 border-red-600/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-400">
              <AlertCircle className="h-5 w-5" />
              Signing link error
            </CardTitle>
          </CardHeader>
          <CardContent className="text-slate-200">
            <p className="mb-2">{error}</p>
            <p className="text-sm text-slate-400">
              Your signing link may have expired or been revoked. Please contact the sender for a new link.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (completed) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <Card className="max-w-lg w-full bg-slate-900 border-emerald-600/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-emerald-400">
              <CheckCircle2 className="h-5 w-5" />
              Signature completed
            </CardTitle>
            <CardDescription className="text-slate-300">
              Thank you. Your signature has been recorded.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <Card className="max-w-3xl w-full bg-slate-900 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-50">Document Signature</CardTitle>
          <CardDescription className="text-slate-300">
            Please review and sign the document below. By signing, you confirm that you have read and agree to the
            terms of the document.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {status && (
            <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 text-sm text-slate-200">
              <div className="flex flex-col gap-1">
                {status.document_title && (
                  <div>
                    <span className="font-semibold">Document:</span> {status.document_title}
                  </div>
                )}
                {status.signer_name && (
                  <div>
                    <span className="font-semibold">Signer:</span> {status.signer_name} ({status.signer_email})
                  </div>
                )}
                {status.expires_at && (
                  <div>
                    <span className="font-semibold">Expires:</span>{' '}
                    {new Date(status.expires_at).toLocaleString()}
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="space-y-3">
            <p className="text-sm text-slate-200 font-semibold">Signature</p>
            <SignaturePad
              onSave={(sig) => setSignatureData(sig)}
              onClear={() => setSignatureData(null)}
              width={600}
              height={200}
            />
            <p className="text-xs text-slate-400">
              Your signature will be captured and securely stored with this document&apos;s audit trail.
            </p>
          </div>

          <div className="flex items-center justify-end gap-3">
            <Button
              variant="outline"
              size="sm"
              className="border-slate-600 text-slate-200"
              onClick={() => window.close()}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              className="bg-emerald-600 hover:bg-emerald-500 text-white"
              disabled={submitting || !signatureData}
              onClick={handleSubmit}
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Submitting...
                </>
              ) : (
                'Sign Document'
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

