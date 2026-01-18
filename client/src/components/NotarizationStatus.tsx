import { useState, useEffect } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Shield,
  CheckCircle,
  Clock,
  AlertCircle,
  RefreshCw,
  Loader2,
  Wallet,
  Calendar,
  Copy,
} from 'lucide-react';

interface NotarizationSigner {
  wallet_address: string;
  signature?: string;
  signed_at?: string;
}

interface NotarizationStatusData {
  id: number;
  notarization_hash: string;
  status: 'pending' | 'signed' | 'completed';
  required_signers: string[];
  signatures: NotarizationSigner[];
  completed_at?: string;
  created_at?: string;
  payment_status?: string;
  cdm_event_id?: string;
}

interface NotarizationStatusProps {
  documentId?: number;
  dealId?: number;
  notarizationId?: number;
  compact?: boolean;
}

export function NotarizationStatus({
  documentId,
  dealId,
  notarizationId,
  compact = false,
}: NotarizationStatusProps) {
  const [notarization, setNotarization] = useState<NotarizationStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (notarizationId || documentId || dealId) {
      fetchNotarizationStatus();
    }
  }, [notarizationId, documentId, dealId]);

  const fetchNotarizationStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      let response;
      
      if (notarizationId) {
        // Fetch by notarization ID
        response = await fetchWithAuth(`/api/remote/notarization/${notarizationId}`);
      } else if (documentId) {
        // Fetch by document ID
        response = await fetchWithAuth(`/api/documents/${documentId}/notarization`);
      } else if (dealId) {
        // Fetch by deal ID
        response = await fetchWithAuth(`/api/deals/${dealId}/notarization`);
      } else {
        setLoading(false);
        return;
      }

      if (!response.ok) {
        throw new Error('Failed to fetch notarization status');
      }

      const data = await response.json();
      
      if (data.notarization) {
        setNotarization(data.notarization);
      } else if (data.id) {
        // Direct notarization object
        setNotarization(data);
      } else {
        setNotarization(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load notarization status');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await fetchNotarizationStatus();
    } finally {
      setRefreshing(false);
    }
  };

  const handleCopyHash = () => {
    if (notarization?.notarization_hash) {
      navigator.clipboard.writeText(notarization.notarization_hash);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
      case 'signed':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50';
      case 'pending':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
      case 'signed':
        return <CheckCircle className="h-5 w-5" />;
      case 'pending':
        return <Clock className="h-5 w-5" />;
      default:
        return <AlertCircle className="h-5 w-5" />;
    }
  };

  const getPaymentStatusColor = (status?: string) => {
    switch (status) {
      case 'paid':
        return 'bg-emerald-500/20 text-emerald-400';
      case 'pending':
        return 'bg-yellow-500/20 text-yellow-400';
      case 'skipped':
      case 'skipped_admin':
        return 'bg-blue-500/20 text-blue-400';
      case 'failed':
        return 'bg-red-500/20 text-red-400';
      default:
        return 'bg-slate-500/20 text-slate-400';
    }
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

  if (error && !notarization) {
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

  if (!notarization) {
    return null; // Don't show anything if no notarization
  }

  const signedCount = notarization.signatures?.filter(s => s.signed_at).length || 0;
  const requiredCount = notarization.required_signers?.length || 0;
  // const allSigned = signedCount >= requiredCount; // unused

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <Badge className={getStatusColor(notarization.status)}>
          <div className="flex items-center gap-2">
            {getStatusIcon(notarization.status)}
            {notarization.status.toUpperCase()}
          </div>
        </Badge>
        {notarization.payment_status && (
          <Badge className={getPaymentStatusColor(notarization.payment_status)}>
            Payment: {notarization.payment_status}
          </Badge>
        )}
      </div>
    );
  }

  return (
    <Card className="bg-slate-800 border-slate-700">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Notarization Status
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
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Status Badge */}
          <div className="flex items-center gap-4">
            <Badge className={getStatusColor(notarization.status)}>
              <div className="flex items-center gap-2">
                {getStatusIcon(notarization.status)}
                {notarization.status.toUpperCase()}
              </div>
            </Badge>
            {notarization.payment_status && (
              <Badge className={getPaymentStatusColor(notarization.payment_status)}>
                Payment: {notarization.payment_status}
              </Badge>
            )}
            {notarization.cdm_event_id && (
              <Badge variant="outline" className="text-slate-400">
                CDM Event: {notarization.cdm_event_id.substring(0, 8)}...
              </Badge>
            )}
          </div>

          {/* Progress */}
          <div className="p-4 bg-slate-900 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-400">Signing Progress</span>
              <span className="text-sm font-semibold text-slate-100">
                {signedCount} / {requiredCount}
              </span>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-2">
              <div
                className="bg-emerald-500 h-2 rounded-full transition-all"
                style={{
                  width: `${requiredCount > 0 ? (signedCount / requiredCount) * 100 : 0}%`
                }}
              />
            </div>
          </div>

          {/* Signers */}
          <div>
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Required Signers</h3>
            <div className="space-y-3">
              {notarization.required_signers?.map((address, index) => {
                const signature = notarization.signatures?.find(
                  s => s.wallet_address?.toLowerCase() === address.toLowerCase()
                );
                const isSigned = !!signature?.signed_at;

                return (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-slate-900 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          isSigned
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : 'bg-slate-700 text-slate-400'
                        }`}
                      >
                        {isSigned ? (
                          <CheckCircle className="h-5 w-5" />
                        ) : (
                          <Wallet className="h-5 w-5" />
                        )}
                      </div>
                      <div>
                        <p className="text-slate-100 font-mono text-sm">
                          {address.slice(0, 6)}...{address.slice(-4)}
                        </p>
                        {signature?.signed_at && (
                          <p className="text-xs text-slate-400 mt-1">
                            Signed: {new Date(signature.signed_at).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      {isSigned ? (
                        <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/50">
                          Signed
                        </Badge>
                      ) : (
                        <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/50">
                          Pending
                        </Badge>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Notarization Hash */}
          <div>
            <h3 className="text-sm font-semibold text-slate-300 mb-2">Notarization Hash</h3>
            <div className="flex items-center gap-2 p-3 bg-slate-900 rounded-lg">
              <code className="flex-1 text-xs font-mono text-slate-300 break-all">
                {notarization.notarization_hash}
              </code>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopyHash}
                className="h-8 w-8 p-0"
                title="Copy hash"
              >
                {copied ? (
                  <CheckCircle className="h-4 w-4 text-emerald-400" />
                ) : (
                  <Copy className="h-4 w-4 text-slate-400" />
                )}
              </Button>
            </div>
          </div>

          {/* Timestamps */}
          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-700">
            <div>
              <p className="text-xs text-slate-400 mb-1">Created</p>
              <div className="flex items-center gap-2 text-sm text-slate-300">
                <Calendar className="h-4 w-4" />
                {notarization.created_at
                  ? new Date(notarization.created_at).toLocaleDateString()
                  : 'N/A'}
              </div>
            </div>
            {notarization.completed_at && (
              <div>
                <p className="text-xs text-slate-400 mb-1">Completed</p>
                <div className="flex items-center gap-2 text-sm text-slate-300">
                  <CheckCircle className="h-4 w-4" />
                  {new Date(notarization.completed_at).toLocaleDateString()}
                </div>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
