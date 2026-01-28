import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { FileText, Clock, PenTool, Loader2, AlertCircle } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { Link } from 'react-router-dom';

interface PendingSignature {
  id: number;
  document_id: number;
  document_title?: string;
  signature_provider: string;
  signature_status: string;
  requested_at: string;
  expires_at?: string;
  access_token?: string;
}

export function MyPendingSignatures() {
  const [signatures, setSignatures] = useState<PendingSignature[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPendingSignatures();
  }, []);

  const loadPendingSignatures = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWithAuth('/api/signatures/my-pending');
      if (!res.ok) {
        throw new Error(res.status === 403 ? 'You do not have permission to view pending signatures.' : 'Failed to load pending signatures');
      }
      const data = await res.json();
      setSignatures(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pending signatures');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center text-red-400">
        <AlertCircle className="h-12 w-12 mx-auto mb-4" />
        <p>{error}</p>
        <Button variant="outline" className="mt-4" onClick={loadPendingSignatures}>
          Retry
        </Button>
      </div>
    );
  }

  if (signatures.length === 0) {
    return (
      <div className="p-12 text-center text-slate-400">
        <FileText className="h-12 w-12 mx-auto mb-4 opacity-20" />
        <p>You have no pending signature requests.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 p-6">
      {signatures.map((sig) => (
        <Card key={sig.id} className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors">
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between">
              <Badge variant="outline" className="text-[10px] uppercase tracking-wider text-emerald-400 border-emerald-400/30">
                {sig.signature_provider}
              </Badge>
              <div className="flex items-center text-xs text-slate-500 gap-1">
                <Clock className="h-3 w-3" />
                {new Date(sig.requested_at).toLocaleDateString()}
              </div>
            </div>
            <CardTitle className="text-lg mt-2 line-clamp-1">{sig.document_title || `Document ${sig.document_id}`}</CardTitle>
            <CardDescription className="text-xs">
              {sig.expires_at ? `Expires: ${new Date(sig.expires_at).toLocaleDateString()}` : 'No expiry'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Link to={sig.access_token ? `/signers/${sig.access_token}` : `/app/document-history/${sig.document_id}`} className="flex-1">
                <Button className="w-full bg-emerald-600 hover:bg-emerald-500 text-white gap-2 h-9 text-sm">
                  <PenTool className="h-4 w-4" />
                  Sign Now
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
