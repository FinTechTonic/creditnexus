import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  Shield, 
  DollarSign, 
  Wallet, 
  CheckCircle, 
  AlertCircle,
  Loader2,
  ExternalLink
} from 'lucide-react';
import { useWallet } from '@/context/WalletContext';
import { useX402Payment } from '@/hooks/useX402Payment';
import { fetchWithAuth, useAuth } from '@/context/AuthContext';

interface NotarizationPaymentProps {
  notarizationId?: number;
  dealId: number;
  onPaymentComplete?: (transactionHash: string) => void;
  onPaymentSkipped?: () => void;
  onError?: (error: string) => void;
}

export function NotarizationPayment({
  notarizationId,
  dealId,
  onPaymentComplete,
  onPaymentSkipped,
  onError,
}: NotarizationPaymentProps) {
  const { user } = useAuth();
  const { isConnected, account, connect } = useWallet();
  const { processPayment, isProcessing, error: paymentError, lastTransactionHash } = useX402Payment();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paymentStatus, setPaymentStatus] = useState<'idle' | 'required' | 'processing' | 'paid' | 'skipped'>('idle');
  const [paymentRequest, setPaymentRequest] = useState<{
    amount: string;
    currency: string;
    facilitator_url?: string;
  } | null>(null);
  const [canSkipPayment, setCanSkipPayment] = useState(false);

  useEffect(() => {
    // Check if user can skip payment (admin)
    if (user?.role === 'admin') {
      setCanSkipPayment(true);
    }
  }, [user]);

  useEffect(() => {
    if (lastTransactionHash && paymentStatus === 'processing') {
      setPaymentStatus('paid');
      onPaymentComplete?.(lastTransactionHash);
    }
  }, [lastTransactionHash, paymentStatus, onPaymentComplete]);

  useEffect(() => {
    if (paymentError) {
      setError(paymentError);
      onError?.(paymentError);
    }
  }, [paymentError, onError]);

  const handleCreateNotarization = async (skipPayment: boolean = false) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchWithAuth(`/api/remote/deals/${dealId}/notarize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          required_signers: account ? [account] : [],
          skip_payment: skipPayment && canSkipPayment,
        }),
      });

      if (response.status === 402) {
        // Payment Required
        const paymentData = await response.json();
        setPaymentRequest({
          amount: paymentData.amount,
          currency: paymentData.currency,
          facilitator_url: paymentData.facilitator_url,
        });
        setPaymentStatus('required');
        setLoading(false);
        return;
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create notarization');
      }

      const data = await response.json();
      
      if (skipPayment) {
        setPaymentStatus('skipped');
        onPaymentSkipped?.();
      } else if (data.payment_status === 'paid' || data.payment_status === 'skipped') {
        setPaymentStatus(data.payment_status);
        if (data.payment_status === 'paid' && data.payment_transaction_hash) {
          onPaymentComplete?.(data.payment_transaction_hash);
        } else {
          onPaymentSkipped?.();
        }
      } else {
        // Payment still required
        setPaymentRequest({
          amount: data.amount || '50.00',
          currency: data.currency || 'USD',
          facilitator_url: data.facilitator_url,
        });
        setPaymentStatus('required');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create notarization';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleProcessPayment = async () => {
    if (!paymentRequest || !isConnected || !account) {
      setError('Wallet connection required');
      return;
    }

    setPaymentStatus('processing');
    setError(null);

    try {
      const endpoint = notarizationId 
        ? `/api/remote/deals/${dealId}/notarize`
        : `/api/remote/deals/${dealId}/notarize`;

      const paymentRequestData = {
        amount: paymentRequest.amount,
        currency: paymentRequest.currency,
        payment_type: 'notarization_fee',
        payer_info: {
          wallet_address: account,
          user_id: user?.id,
          name: user?.display_name || user?.email,
        },
        receiver_info: {
          name: 'CreditNexus System',
        },
        deal_id: dealId,
        notarization_id: notarizationId,
        facilitator_url: paymentRequest.facilitator_url,
      };

      const result = await processPayment(endpoint, paymentRequestData, {
        method: 'POST',
        body: {
          required_signers: [account],
          payment_payload: {
            wallet_address: account,
            amount: paymentRequest.amount,
            currency: paymentRequest.currency,
          },
        },
      });

      if (result.status === 'payment_required') {
        // Open facilitator URL if available
        if (result.facilitator_url) {
          window.open(result.facilitator_url, '_blank');
        }
        setPaymentStatus('required');
        setError('Payment required. Please complete payment via x402 facilitator.');
      } else if (result.status === 'paid') {
        setPaymentStatus('paid');
        if (result.transaction_hash) {
          onPaymentComplete?.(result.transaction_hash);
        }
      } else {
        throw new Error(result.error || 'Payment processing failed');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Payment processing failed';
      setError(errorMessage);
      setPaymentStatus('required');
      onError?.(errorMessage);
    }
  };

  const handleConnectWallet = async () => {
    try {
      await connect();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect wallet');
    }
  };

  // Payment required state
  if (paymentStatus === 'required' && paymentRequest) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-blue-400" />
            Payment Required
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-blue-900/20 border border-blue-500/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-400">Amount</span>
              <span className="text-lg font-semibold text-blue-400">
                {paymentRequest.currency} {paymentRequest.amount}
              </span>
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Notarization fee required to complete request
            </div>
          </div>

          {!isConnected ? (
            <div className="space-y-3">
              <div className="bg-yellow-900/20 border border-yellow-500/50 rounded-lg p-3">
                <div className="flex items-center gap-2 text-yellow-400 mb-2">
                  <AlertCircle className="h-4 w-4" />
                  <span className="text-sm font-semibold">Wallet Not Connected</span>
                </div>
                <p className="text-xs text-slate-400 mb-3">
                  Connect your MetaMask wallet to process payment.
                </p>
                <Button
                  onClick={handleConnectWallet}
                  className="w-full bg-yellow-600 hover:bg-yellow-500 text-white"
                >
                  <Wallet className="h-4 w-4 mr-2" />
                  Connect MetaMask
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-emerald-400">
                <CheckCircle className="h-4 w-4" />
                <span className="text-sm">Wallet Connected: {account?.slice(0, 6)}...{account?.slice(-4)}</span>
              </div>
              
              <Button
                onClick={handleProcessPayment}
                disabled={isProcessing || loading}
                className="w-full bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                {isProcessing || loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Processing Payment...
                  </>
                ) : (
                  <>
                    <DollarSign className="h-4 w-4 mr-2" />
                    Pay {paymentRequest.currency} {paymentRequest.amount}
                  </>
                )}
              </Button>

              {paymentRequest.facilitator_url && (
                <Button
                  onClick={() => window.open(paymentRequest.facilitator_url, '_blank')}
                  variant="outline"
                  className="w-full border-blue-500/50 text-blue-400 hover:bg-blue-900/20"
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Open x402 Facilitator
                </Button>
              )}
            </div>
          )}

          {error && (
            <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-3">
              <div className="flex items-center gap-2 text-red-400">
                <AlertCircle className="h-4 w-4" />
                <p className="text-sm">{error}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  // Payment completed state
  if (paymentStatus === 'paid') {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-emerald-400" />
            Payment Completed
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-emerald-900/20 border border-emerald-500/50 rounded-lg p-4">
            <div className="flex items-center gap-2 text-emerald-400 mb-2">
              <CheckCircle className="h-4 w-4" />
              <span className="text-sm font-semibold">Payment Successful</span>
            </div>
            {lastTransactionHash && (
              <div className="text-xs text-slate-400 mt-2">
                Transaction: {lastTransactionHash.slice(0, 10)}...{lastTransactionHash.slice(-8)}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Payment skipped state
  if (paymentStatus === 'skipped') {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-yellow-400" />
            Payment Skipped (Admin)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-yellow-900/20 border border-yellow-500/50 rounded-lg p-4">
            <div className="flex items-center gap-2 text-yellow-400 mb-2">
              <Shield className="h-4 w-4" />
              <span className="text-sm font-semibold">Admin Privilege</span>
            </div>
            <p className="text-xs text-slate-400">
              Payment skipped due to administrator privileges.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Initial state - create notarization
  return (
    <Card className="bg-slate-800 border-slate-700">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-blue-400" />
          Notarization Payment
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-slate-400">
          Create a notarization request for this deal. Payment is required unless you have admin privileges.
        </p>
        
        {canSkipPayment && (
          <div className="bg-yellow-900/20 border border-yellow-500/50 rounded-lg p-3">
            <div className="flex items-center gap-2 text-yellow-400 mb-2">
              <Shield className="h-4 w-4" />
              <span className="text-sm font-semibold">Admin Privilege</span>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              You can skip payment as an administrator.
            </p>
            <div className="flex gap-2">
              <Button
                onClick={() => handleCreateNotarization(true)}
                disabled={loading}
                variant="outline"
                className="flex-1 border-yellow-500/50 text-yellow-400 hover:bg-yellow-900/20"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Shield className="h-4 w-4 mr-2" />
                    Skip Payment (Admin)
                  </>
                )}
              </Button>
              <Button
                onClick={() => handleCreateNotarization(false)}
                disabled={loading}
                className="flex-1 bg-blue-600 hover:bg-blue-500 text-white"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <DollarSign className="h-4 w-4 mr-2" />
                    Pay & Create
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
        
        {!canSkipPayment && (
          <Button
            onClick={() => handleCreateNotarization(false)}
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Creating Notarization...
              </>
            ) : (
              <>
                <Shield className="h-4 w-4 mr-2" />
                Create Notarization Request
              </>
            )}
          </Button>
        )}

        {error && (
          <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-3">
            <div className="flex items-center gap-2 text-red-400">
              <AlertCircle className="h-4 w-4" />
              <p className="text-sm">{error}</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
