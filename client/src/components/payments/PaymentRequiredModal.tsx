import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, ExternalLink, Loader2, Wallet, CreditCard, Building2 } from 'lucide-react';
import { useWallet } from '@/context/WalletContext';
import { fetchWithAuth, useAuth } from '@/context/AuthContext';
import { useX402Payment } from '@/hooks/useX402Payment';

export interface PaymentRequiredPayload {
  message?: string;
  amount?: string;
  currency?: string;
  facilitator_url?: string;
  payment_request?: any;
  cost?: {
    usd?: string;
    credits?: string;
    credit_type?: string;
  };
  payment_type?: string;
  endpoint?: string; // Original endpoint that triggered 402
  retry_body?: any; // Original request body to retry after payment
}

interface PaymentRequiredModalProps {
  open: boolean;
  payload: PaymentRequiredPayload | null;
  onClose: () => void;
  onRetry: () => Promise<void> | void;
  onPaymentComplete?: () => void;
}

type PaymentMethod = 'metamask' | 'revenuecat' | 'plaid' | 'facilitator';

export function PaymentRequiredModal({ 
  open, 
  payload, 
  onClose, 
  onRetry,
  onPaymentComplete 
}: PaymentRequiredModalProps) {
  const { user } = useAuth();
  const { isConnected, account, connect } = useWallet();
  const { processPayment, isProcessing } = useX402Payment();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMethod, setSelectedMethod] = useState<PaymentMethod | null>(null);
  const [paymentStatus, setPaymentStatus] = useState<'idle' | 'processing' | 'success' | 'failed'>('idle');

  useEffect(() => {
    if (!open) {
      setLoading(false);
      setError(null);
      setSelectedMethod(null);
      setPaymentStatus('idle');
    }
  }, [open]);

  if (!open) return null;

  const facilitatorUrl = payload?.facilitator_url;
  const usd = payload?.cost?.usd || payload?.amount;
  const credits = payload?.cost?.credits;
  const creditType = payload?.cost?.credit_type;
  const paymentType = payload?.payment_type || 'payment';
  const endpoint = payload?.endpoint;

  // Determine available payment methods based on payment type and configuration
  const availableMethods: PaymentMethod[] = [];
  
  // MetaMask/x402 is always available for blockchain payments
  if (facilitatorUrl || paymentType === 'notarization_fee' || paymentType === 'subscription_upgrade' || paymentType === 'tranche_purchase') {
    availableMethods.push('metamask', 'facilitator');
  }
  
  // RevenueCat for subscription upgrades
  if (paymentType === 'subscription_upgrade' || paymentType === 'org_admin_upgrade') {
    availableMethods.push('revenuecat');
  }
  
  // Plaid for bank-based payments (future)
  if (paymentType === 'plaid_accounts_get' || paymentType === 'plaid_balances_get' || paymentType === 'plaid_transactions_get') {
    availableMethods.push('plaid');
  }

  // Default to facilitator if no specific methods available
  if (availableMethods.length === 0 && facilitatorUrl) {
    availableMethods.push('facilitator');
  }

  const handleConnectWallet = async () => {
    setError(null);
    try {
      await connect();
      setSelectedMethod('metamask');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to connect wallet');
    }
  };

  const handlePayWithMetaMask = async () => {
    if (!isConnected || !account || !endpoint) {
      setError('Wallet connection required');
      await handleConnectWallet();
      return;
    }

    setLoading(true);
    setError(null);
    setPaymentStatus('processing');
    setSelectedMethod('metamask');

    try {
      // Use x402 payment hook to process payment
      const paymentRequest = {
        amount: usd || '0',
        currency: payload?.currency || 'USD',
        payment_type: paymentType,
        payer_info: {
          wallet_address: account,
          user_id: user?.id,
        },
        facilitator_url: facilitatorUrl,
      };

      const result = await processPayment(endpoint || '', paymentRequest, {
        method: 'POST',
        body: payload?.retry_body || {},
      });

      if (result.status === 'paid') {
        setPaymentStatus('success');
        setTimeout(() => {
          onPaymentComplete?.();
          onRetry();
        }, 1000);
      } else if (result.status === 'payment_required') {
        setError('Payment still required. Please try again.');
        setPaymentStatus('failed');
      } else {
        setError(result.message || 'Payment failed');
        setPaymentStatus('failed');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Payment failed');
      setPaymentStatus('failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePayWithRevenueCat = async () => {
    setLoading(true);
    setError(null);
    setPaymentStatus('processing');
    setSelectedMethod('revenuecat');

    try {
      // Determine product_id based on payment type
      let productId = 'subscription_upgrade';
      if (paymentType === 'org_admin_upgrade') {
        productId = 'org_admin';
      } else if (paymentType === 'subscription_upgrade') {
        productId = 'subscription_upgrade';
      }

      // RevenueCat payment flow
      // Note: In production, RevenueCat SDK would handle the actual purchase UI
      // This endpoint grants entitlements after RevenueCat SDK purchase
      const response = await fetchWithAuth('/api/subscriptions/revenuecat/purchase', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: productId,
          amount: usd,
          transaction_id: null, // Would be provided by RevenueCat SDK
          purchase_token: null, // Would be provided by RevenueCat SDK
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.status === 'completed') {
          setPaymentStatus('success');
          setTimeout(() => {
            onPaymentComplete?.();
            onRetry();
          }, 1000);
        } else {
          setError('Payment not completed');
          setPaymentStatus('failed');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.detail || 'RevenueCat payment failed');
        setPaymentStatus('failed');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'RevenueCat payment failed');
      setPaymentStatus('failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePayWithPlaid = async () => {
    setLoading(true);
    setError(null);
    setPaymentStatus('processing');
    setSelectedMethod('plaid');

    try {
      // Plaid payment flow - routes to PlaidService
      const response = await fetchWithAuth('/api/banking/payment/initiate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: usd,
          currency: payload?.currency || 'USD',
          payment_type: paymentType,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.payment_id) {
          // Plaid payment initiated, wait for webhook confirmation
          setError('Plaid payment initiated. Waiting for confirmation...');
          // In production, would poll or listen for webhook
        } else {
          setError('Failed to initiate Plaid payment');
          setPaymentStatus('failed');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.detail || 'Plaid payment initiation failed');
        setPaymentStatus('failed');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Plaid payment failed');
      setPaymentStatus('failed');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenFacilitator = () => {
    if (facilitatorUrl) {
      window.open(facilitatorUrl, '_blank');
      setSelectedMethod('facilitator');
    }
  };

  const handleRetry = async () => {
    setLoading(true);
    setError(null);
    try {
      await onRetry();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Retry failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg">
        <Card className="border-slate-700 bg-slate-900">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-yellow-400" />
              Payment Required
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg border border-yellow-700/40 bg-yellow-900/10 p-4">
              <div className="text-sm text-slate-300">
                {payload?.message || 'Payment is required to continue.'}
              </div>
              {(usd || credits) && (
                <div className="mt-3 text-xs text-slate-400">
                  {usd && <div><span className="font-semibold">USD:</span> ${usd}</div>}
                  {credits && (
                    <div>
                      <span className="font-semibold">Credits:</span> {credits}
                      {creditType ? ` (${creditType})` : ''}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Payment Method Selection */}
            <div className="space-y-2">
              <div className="text-sm font-semibold text-slate-200">Choose Payment Method:</div>
              
              {/* MetaMask/Crypto Option */}
              {availableMethods.includes('metamask') && (
                <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-3">
                  {!isConnected ? (
                    <>
                      <div className="text-sm text-slate-200 mb-2">Pay with Crypto</div>
                      <Button 
                        onClick={handleConnectWallet} 
                        className="w-full bg-emerald-600 hover:bg-emerald-700"
                        disabled={loading}
                      >
                        <Wallet className="h-4 w-4 mr-2" />
                        Connect Wallet
                      </Button>
                    </>
                  ) : (
                    <>
                      <div className="text-xs text-slate-400 mb-2">
                        Wallet connected: {account?.slice(0, 6)}...{account?.slice(-4)}
                      </div>
                      <Button 
                        onClick={handlePayWithMetaMask} 
                        className="w-full bg-emerald-600 hover:bg-emerald-700"
                        disabled={loading || isProcessing || paymentStatus === 'processing'}
                      >
                        {loading || isProcessing ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <Wallet className="h-4 w-4 mr-2" />
                        )}
                        Pay with Crypto
                      </Button>
                    </>
                  )}
                </div>
              )}

              {/* RevenueCat/Card Option */}
              {availableMethods.includes('revenuecat') && (
                <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-3">
                  <div className="text-sm text-slate-200 mb-2">Pay with Card</div>
                  <Button 
                    onClick={handlePayWithRevenueCat} 
                    className="w-full bg-blue-600 hover:bg-blue-700"
                    disabled={loading || paymentStatus === 'processing'}
                  >
                    {loading ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <CreditCard className="h-4 w-4 mr-2" />
                    )}
                    Pay with Card
                  </Button>
                </div>
              )}

              {/* Plaid/Bank Option */}
              {availableMethods.includes('plaid') && (
                <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-3">
                  <div className="text-sm text-slate-200 mb-2">Pay with Bank</div>
                  <Button 
                    onClick={handlePayWithPlaid} 
                    className="w-full bg-purple-600 hover:bg-purple-700"
                    disabled={loading || paymentStatus === 'processing'}
                  >
                    {loading ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Building2 className="h-4 w-4 mr-2" />
                    )}
                    Pay with Bank
                  </Button>
                </div>
              )}

              {/* Facilitator URL Option */}
              {availableMethods.includes('facilitator') && facilitatorUrl && (
                <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-3">
                  <div className="text-sm text-slate-200 mb-2">Pay via x402 Facilitator</div>
                  <Button 
                    onClick={handleOpenFacilitator} 
                    className="w-full bg-slate-600 hover:bg-slate-700"
                    disabled={loading}
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Open Payment Facilitator
                  </Button>
                </div>
              )}
            </div>

            {paymentStatus === 'success' && (
              <div className="rounded-lg border border-green-700/40 bg-green-900/10 p-3 text-sm text-green-300">
                Payment successful! Processing...
              </div>
            )}

            {error && <div className="text-sm text-red-300">{error}</div>}

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={onClose} disabled={loading}>
                Close
              </Button>
              {paymentStatus !== 'success' && (
                <Button 
                  onClick={handleRetry} 
                  disabled={loading || paymentStatus === 'processing'} 
                  className="bg-emerald-600 hover:bg-emerald-700"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Retry'}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
