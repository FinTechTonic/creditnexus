import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { fetchWithAuth, useAuth } from '@/context/AuthContext';
import { useWallet } from '@/context/WalletContext';
import { useX402Payment } from '@/hooks/useX402Payment';
import { DollarSign, ExternalLink, Loader2, AlertCircle, Wallet, CreditCard, Building2 } from 'lucide-react';

interface OrgAdminPaymentModalProps {
  open: boolean;
  onClose: () => void;
  onPaid: () => void;
  canBypass?: boolean;
  /** When provided, show "Skip for now" so user can complete signup without paying (e.g. REQUIRE_SIGNUP_PAYMENT=false). */
  onSkip?: () => void;
}

export function OrgAdminPaymentModal({ open, onClose, onPaid, canBypass = false, onSkip }: OrgAdminPaymentModalProps) {
  const { user } = useAuth();
  const { isConnected, account, connect } = useWallet();
  const { processPayment, isProcessing } = useX402Payment();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paymentRequest, setPaymentRequest] = useState<any>(null);
  const [facilitatorUrl, setFacilitatorUrl] = useState<string | null>(null);
  const [amount, setAmount] = useState<string>('2.00');
  const [paymentPayload, setPaymentPayload] = useState<any>(null);
  const [selectedMethod, setSelectedMethod] = useState<'crypto' | 'card' | 'bank' | null>(null);

  useEffect(() => {
    if (!open) {
      setLoading(false);
      setError(null);
      setPaymentRequest(null);
      setFacilitatorUrl(null);
      setAmount('2.00');
      setPaymentPayload(null);
      setSelectedMethod(null);
    }
  }, [open]);

  const loadPaymentOptions = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetchWithAuth('/api/subscriptions/org-admin/upgrade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });

      if (r.status === 402) {
        const d = await r.json().catch(() => ({}));
        setPaymentRequest(d.payment_request || null);
        setFacilitatorUrl(d.facilitator_url || null);
        setAmount(d.amount || '2.00');
        setPaymentPayload(d);
        return;
      }

      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        setError(d.detail || 'Failed to load payment options.');
        return;
      }

      // If backend is configured to auto-settle (e.g., mocked x402), it may return settled here.
      const d = await r.json().catch(() => ({}));
      if (d.status === 'settled') {
        onPaid();
        return;
      }
      setError('Payment did not settle. Please retry.');
    } catch {
      setError('Failed to load payment options.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      loadPaymentOptions();
    }
  }, [open]);

  const handlePayWithCrypto = async () => {
    if (!isConnected || !account) {
      setError('Wallet connection required');
      await connect();
      return;
    }

    setLoading(true);
    setError(null);
    setSelectedMethod('crypto');

    try {
      const paymentReq = {
        amount: amount,
        currency: 'USD',
        payment_type: 'org_admin_upgrade',
        payer_info: {
          wallet_address: account,
          user_id: user?.id,
        },
        facilitator_url: facilitatorUrl ?? undefined,
      };

      const result = await processPayment('/api/subscriptions/org-admin/upgrade', paymentReq, {
        method: 'POST',
        body: {},
      });

      if (result.status === 'paid') {
        onPaid();
      } else {
        setError(result.message || 'Payment failed');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Payment failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePayWithCard = async () => {
    setLoading(true);
    setError(null);
    setSelectedMethod('card');

    try {
      const response = await fetchWithAuth('/api/subscriptions/revenuecat/purchase', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: 'org_admin',
          amount: amount,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.status === 'completed') {
          onPaid();
        } else {
          setError('Payment not completed');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.detail || 'Payment failed');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Payment failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePayWithBank = async () => {
    setLoading(true);
    setError(null);
    setSelectedMethod('bank');

    try {
      // Plaid payment flow - routes to PlaidService
      const response = await fetchWithAuth('/api/banking/payment/initiate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: amount,
          currency: 'USD',
          payment_type: 'org_admin_upgrade',
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.payment_id) {
          setError('Plaid payment initiated. Waiting for confirmation...');
        } else {
          setError('Failed to initiate payment');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.detail || 'Payment initiation failed');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Payment failed');
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg">
        <Card className="border-slate-700 bg-slate-900">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-emerald-400" />
              Organization Admin Signup Payment
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg border border-emerald-700/40 bg-emerald-900/10 p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-300">Subscription</span>
                <span className="text-lg font-semibold text-emerald-300">USD {amount}</span>
              </div>
              <p className="mt-2 text-xs text-slate-400">
                Required to activate Organization Admin access and unlock initial credits.
              </p>
            </div>

            {error && (
              <div className="rounded-lg border border-red-700/40 bg-red-900/10 p-3 text-sm text-red-300 flex items-start gap-2">
                <AlertCircle className="h-4 w-4 mt-0.5" />
                <div>{error}</div>
              </div>
            )}

            {/* Payment Method Selection */}
            {paymentPayload && (
              <div className="space-y-2">
                <div className="text-sm font-semibold text-slate-200">Choose Payment Method:</div>
                
                {/* Pay with Crypto */}
                <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-3">
                  {!isConnected ? (
                    <>
                      <div className="text-sm text-slate-200 mb-2">Pay with Crypto</div>
                      <Button 
                        onClick={connect} 
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
                        onClick={handlePayWithCrypto} 
                        className="w-full bg-emerald-600 hover:bg-emerald-700"
                        disabled={loading || isProcessing}
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

                {/* Pay with Card (RevenueCat) */}
                {paymentPayload.revenuecat_available && (
                  <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-3">
                    <div className="text-sm text-slate-200 mb-2">Pay with Card</div>
                    <Button 
                      onClick={handlePayWithCard} 
                      className="w-full bg-blue-600 hover:bg-blue-700"
                      disabled={loading}
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

                {/* Pay with Bank (Plaid) */}
                <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-3">
                  <div className="text-sm text-slate-200 mb-2">Pay with Bank</div>
                  <Button 
                    onClick={handlePayWithBank} 
                    className="w-full bg-purple-600 hover:bg-purple-700"
                    disabled={loading}
                  >
                    {loading ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Building2 className="h-4 w-4 mr-2" />
                    )}
                    Pay with Bank
                  </Button>
                </div>

                {/* Facilitator URL Option */}
                {facilitatorUrl && (
                  <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-3">
                    <div className="text-sm text-slate-200 mb-2">Pay via x402 Facilitator</div>
                    <Button 
                      onClick={() => window.open(facilitatorUrl, '_blank')} 
                      className="w-full bg-slate-600 hover:bg-slate-700"
                      disabled={loading}
                    >
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Open Payment Facilitator
                    </Button>
                  </div>
                )}
              </div>
            )}

            {!paymentPayload && loading && (
              <div className="flex items-center justify-center p-4">
                <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
              </div>
            )}

            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              {onSkip && (
                <Button variant="ghost" onClick={onSkip}>
                  Skip for now
                </Button>
              )}
              {canBypass && (
                <Button variant="secondary" onClick={onPaid}>
                  Bypass (instance admin)
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
