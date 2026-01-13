import { useState, useEffect } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  FileText,
  CheckCircle,
  Clock,
  XCircle,
  AlertCircle,
  Download,
  RefreshCw,
  Loader2,
  Mail,
  User,
  Calendar,
  ExternalLink
} from 'lucide-react';

interface Signer {
  name: string;
  email: string;
  role: string;
  signed_at?: string;
}

interface SignatureStatus {
  id: number;
  document_id: number;
  generated_document_id?: number;
  signature_provider: string;
  signature_request_id: string;
  signature_status: string;
  signers: Signer[];
  signature_provider_data?: Record<string, any>;
  signed_document_url?: string;
  signed_document_path?: string;
  requested_at: string;
  completed_at?: string;
  expires_at?: string;
}

interface SignatureStatusProps {
  documentId: number;
  signatureId?: number;
}

export function SignatureStatus({ documentId, signatureId }: SignatureStatusProps) {
  const [signature, setSignature] = useState<SignatureStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (signatureId) {
      fetchSignatureStatus();
    } else {
      // Fetch latest signature for document
      fetchDocumentSignatures();
    }
  }, [documentId, signatureId]);

  const fetchDocumentSignatures = async () => {
    // This would need a new endpoint to get signatures for a document
    // For now, we'll use the signature ID if provided
    if (signatureId) {
      fetchSignatureStatus();
    } else {
      setLoading(false);
    }
  };

  const fetchSignatureStatus = async () => {
    if (!signatureId) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetchWithAuth(`/api/signatures/${signatureId}/status`);
      if (!response.ok) {
        throw new Error('Failed to fetch signature status');
      }
      const data = await response.json();
      setSignature(data.signature);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load signature status');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    if (!signatureId) return;

    setRefreshing(true);
    try {
      await fetchSignatureStatus();
    } finally {
      setRefreshing(false);
    }
  };

  const handleDownload = async () => {
    if (!signatureId || !signature) return;

    setDownloading(true);
    try {
      const response = await fetchWithAuth(`/api/signatures/${signatureId}/download`);
      if (!response.ok) {
        throw new Error('Failed to download signed document');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `signed-document-${signatureId}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download document');
    } finally {
      setDownloading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50';
      case 'pending':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      case 'declined':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      case 'expired':
        return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5" />;
      case 'pending':
        return <Clock className="h-5 w-5" />;
      case 'declined':
        return <XCircle className="h-5 w-5" />;
      case 'expired':
        return <AlertCircle className="h-5 w-5" />;
      default:
        return <Clock className="h-5 w-5" />;
    }
  };

  const getDaysUntilExpiry = (expiresAt?: string) => {
    if (!expiresAt) return null;
    const expiryDate = new Date(expiresAt);
    const today = new Date();
    const diffTime = expiryDate.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  if (loading) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error && !signature) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div className="flex items-center gap-2 text-red-400">
            <AlertCircle className="h-5 w-5" />
            <span>{error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!signature) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6 text-center text-slate-400">
          No signature request found for this document
        </CardContent>
      </Card>
    );
  }

  const daysUntilExpiry = getDaysUntilExpiry(signature.expires_at);
  const allSigned = signature.signers.every((s) => s.signed_at);
  const pendingSigners = signature.signers.filter((s) => !s.signed_at);

  return (
    <Card className="bg-slate-800 border-slate-700">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Signature Status
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              disabled={refreshing}
              className="text-slate-400 hover:text-slate-100"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            {signature.signature_status === 'completed' && (
              <Button
                size="sm"
                onClick={handleDownload}
                disabled={downloading}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                {downloading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Downloading...
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4 mr-2" />
                    Download Signed
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Status Badge */}
          <div className="flex items-center gap-4">
            <Badge className={getStatusColor(signature.signature_status)}>
              <div className="flex items-center gap-2">
                {getStatusIcon(signature.signature_status)}
                {signature.signature_status.toUpperCase()}
              </div>
            </Badge>
            {signature.signature_provider && (
              <Badge variant="outline" className="text-slate-400">
                {signature.signature_provider}
              </Badge>
            )}
            {signature.signature_request_id && (
              <span className="text-sm text-slate-400 font-mono">
                ID: {signature.signature_request_id.substring(0, 8)}...
              </span>
            )}
          </div>

          {/* Expiry Warning */}
          {signature.expires_at && daysUntilExpiry !== null && daysUntilExpiry <= 7 && (
            <div
              className={`p-3 rounded-lg border ${
                daysUntilExpiry <= 1
                  ? 'bg-red-500/10 border-red-500/50 text-red-400'
                  : 'bg-yellow-500/10 border-yellow-500/50 text-yellow-400'
              }`}
            >
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                <span className="text-sm">
                  {daysUntilExpiry <= 0
                    ? 'Signature request has expired'
                    : `Expires in ${daysUntilExpiry} day${daysUntilExpiry !== 1 ? 's' : ''}`}
                </span>
              </div>
            </div>
          )}

          {/* Signers */}
          <div>
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Signers</h3>
            <div className="space-y-3">
              {signature.signers.map((signer, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-slate-900 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center ${
                        signer.signed_at
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-slate-700 text-slate-400'
                      }`}
                    >
                      {signer.signed_at ? (
                        <CheckCircle className="h-5 w-5" />
                      ) : (
                        <User className="h-5 w-5" />
                      )}
                    </div>
                    <div>
                      <p className="text-slate-100 font-medium">{signer.name}</p>
                      <div className="flex items-center gap-2 text-sm text-slate-400">
                        <Mail className="h-3 w-3" />
                        {signer.email}
                      </div>
                      {signer.role && (
                        <Badge variant="outline" className="text-xs text-slate-400 mt-1">
                          {signer.role}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    {signer.signed_at ? (
                      <div>
                        <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/50">
                          Signed
                        </Badge>
                        <p className="text-xs text-slate-400 mt-1">
                          {new Date(signer.signed_at).toLocaleDateString()}
                        </p>
                      </div>
                    ) : (
                      <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/50">
                        Pending
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Progress Summary */}
          <div className="p-4 bg-slate-900 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-400">Progress</span>
              <span className="text-sm font-semibold text-slate-100">
                {signature.signers.filter((s) => s.signed_at).length} / {signature.signers.length}
              </span>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-2">
              <div
                className="bg-emerald-500 h-2 rounded-full transition-all"
                style={{
                  width: `${
                    (signature.signers.filter((s) => s.signed_at).length /
                      signature.signers.length) *
                    100
                  }%`
                }}
              />
            </div>
          </div>

          {/* Timestamps */}
          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-700">
            <div>
              <p className="text-xs text-slate-400 mb-1">Requested</p>
              <div className="flex items-center gap-2 text-sm text-slate-300">
                <Calendar className="h-4 w-4" />
                {new Date(signature.requested_at).toLocaleDateString()}
              </div>
            </div>
            {signature.completed_at && (
              <div>
                <p className="text-xs text-slate-400 mb-1">Completed</p>
                <div className="flex items-center gap-2 text-sm text-slate-300">
                  <CheckCircle className="h-4 w-4" />
                  {new Date(signature.completed_at).toLocaleDateString()}
                </div>
              </div>
            )}
            {signature.expires_at && (
              <div>
                <p className="text-xs text-slate-400 mb-1">Expires</p>
                <div className="flex items-center gap-2 text-sm text-slate-300">
                  <Clock className="h-4 w-4" />
                  {new Date(signature.expires_at).toLocaleDateString()}
                </div>
              </div>
            )}
          </div>

          {/* Actions */}
          {signature.signature_status === 'completed' && signature.signed_document_url && (
            <div className="pt-4 border-t border-slate-700">
              <Button
                variant="outline"
                onClick={() => window.open(signature.signed_document_url, '_blank')}
                className="w-full text-slate-400 hover:text-slate-100"
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                View Signed Document
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
