import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  CreditCard, 
  DollarSign, 
  Wallet, 
  CheckCircle, 
  AlertCircle,
  Loader2,
  ExternalLink,
  Building2,
  TrendingUp
} from 'lucide-react';
import { useWallet } from '@/context/WalletContext';
import { useX402Payment } from '@/hooks/useX402Payment';
import { fetchWithAuth, useAuth } from '@/context/AuthContext';

interface TranchePurchaseProps {
  poolId: string;
  trancheId: string;
  onPurchaseComplete?: (transactionHash: string, tokenId: string) => void;
  onError?: (error: string) => void;
}

export function TranchePurchase({
  poolId,
  trancheId,
  onPurchaseComplete,
  onError,
}: TranchePurchaseProps) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { isConnected, account, connect } = useWallet();
  const { processPayment, isProcessing, error: paymentError, lastTransactionHash } = useX402Payment();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [trancheDetails, setTrancheDetails] = useState<{
    tranche_name: string;
    tranche_class: string;
    size: string;
    currency: string;
    interest_rate: number;
    risk_rating: string | null;
  } | null>(null);
  const [poolDetails, setPoolDetails] = useState<{
    pool_name: string;
    pool_id: string;
  } | null>(null);
  const [paymentStatus, setPaymentStatus] = useState<'idle' | 'required' | 'processing' | 'paid' | 'failed'>('idle');
  const [paymentRequest, setPaymentRequest] = useState<{
    amount: string;
    currency: string;
    facilitator_url?: string;
  } | null>(null);

  useEffect(() => {
    fetchTrancheAndPoolDetails();
  }, [poolId, trancheId]);

  useEffect(() => {
    if (lastTransactionHash && paymentStatus === 'processing') {
      setPaymentStatus('paid');
      // Extract token_id from response if available
      onPurchaseComplete?.(lastTransactionHash, '');
    }
  }, [lastTransactionHash, paymentStatus, onPurchaseComplete]);

  useEffect(() => {
    if (paymentError) {
      setError(paymentError);
      setPaymentStatus('failed');
      onError?.(paymentError);
    }
  }, [paymentError, onError]);

  const fetchTrancheAndPoolDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch pool details to get tranche info
      const poolResponse = await fetchWithAuth(`/api/securitization/pools/${poolId}`);
      if (!poolResponse.ok) {
        throw new Error('Failed to fetch pool details');
      }
      const poolData = await poolResponse.json();
      
      const pool = poolData.pool?.pool || poolData.pool;
      const tranches = poolData.pool?.tranches || [];
      
      setPoolDetails({
        pool_name: pool.pool_name,
        pool_id: pool.pool_id
      });
      
      // Find the specific tranche
      const tranche = tranches.find((t: any) => 
        t.tranche_id === trancheId || t.id?.toString() === trancheId
      );
      
      if (!tranche) {
        throw new Error('Tranche not found');
      }
      
      setTrancheDetails({
        tranche_name: tranche.tranche_name,
        tranche_class: tranche.tranche_class,
        size: tranche.size,
        currency: tranche.currency,
        interest_rate: tranche.interest_rate,
        risk_rating: tranche.risk_rating
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tranche details');
    } finally {
      setLoading(false);
    }
  };

  const handlePurchase = async () => {
    if (!isConnected || !account) {
      try {
        await connect();
      } catch (err) {
        setError('Please connect your MetaMask wallet to purchase a tranche');
        return;
      }
    }

    if (!user) {
      setError('You must be logged in to purchase a tranche');
      return;
    }

    setLoading(true);
    setError(null);
    setPaymentStatus('processing');

    try {
      // First, get the tranche database ID from the pool details
      const poolResponse = await fetchWithAuth(`/api/securitization/pools/${poolId}`);
      if (!poolResponse.ok) {
        throw new Error('Failed to fetch pool details');
      }
      const poolData = await poolResponse.json();
      const tranches = poolData.pool?.tranches || [];
      const tranche = tranches.find((t: any) => 
        t.tranche_id === trancheId || t.id?.toString() === trancheId
      );
      
      if (!tranche) {
        throw new Error('Tranche not found');
      }

      // Prepare payment request
      const paymentRequest: any = {
        amount: tranche.size,
        currency: tranche.currency,
        payment_type: 'tranche_purchase',
        payer_info: {
          wallet_address: account,
          user_id: user.id,
          name: user.display_name
        },
        receiver_info: {
          name: 'Securitization Pool',
          contract_address: undefined // Will be set by backend
        },
        pool_id: poolId,
        tranche_id: tranche.id || tranche.tranche_id
      };

      // Call purchase endpoint
      const purchaseResponse = await processPayment(
        `/api/securitization/pools/${poolId}/purchase-tranche`,
        paymentRequest,
        {
          method: 'POST',
          body: {
            tranche_id: tranche.id || parseInt(trancheId),
            buyer_user_id: user.id
          }
        }
      );

      if (purchaseResponse.status === 'payment_required') {
        setPaymentRequest({
          amount: purchaseResponse.amount || tranche.size,
          currency: purchaseResponse.currency || tranche.currency,
          facilitator_url: purchaseResponse.facilitator_url
        });
        setPaymentStatus('required');
        setLoading(false);
        return;
      }

      if (purchaseResponse.status === 'paid' || purchaseResponse.status === 'completed') {
        setPaymentStatus('paid');
        onPurchaseComplete?.(purchaseResponse.transaction_hash || '', '');
        
        // Navigate back to pool detail after a short delay
        setTimeout(() => {
          navigate(`/app/securitization/pools/${poolId}`);
        }, 2000);
      } else {
        throw new Error(purchaseResponse.message || purchaseResponse.error || 'Purchase failed');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to purchase tranche';
      setError(errorMessage);
      setPaymentStatus('failed');
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !trancheDetails) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-900">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  if (error && !trancheDetails) {
    return (
      <div className="p-6 space-y-4">
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-6 text-center">
            <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-slate-100 mb-2">Error</h2>
            <p className="text-slate-400 mb-4">{error}</p>
            <Button
              onClick={() => navigate(`/app/securitization/pools/${poolId}`)}
              variant="outline"
            >
              Back to Pool
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const purchaseAmount = trancheDetails ? parseFloat(trancheDetails.size) : 0;

  return (
    <div className="space-y-6 p-6 max-w-2xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold text-slate-100 mb-2">Purchase Tranche</h1>
        {poolDetails && (
          <p className="text-slate-400">
            {poolDetails.pool_name} • {trancheDetails?.tranche_name}
          </p>
        )}
      </div>

      {error && paymentStatus !== 'required' && (
        <Card className="bg-red-900/20 border-red-500/50">
          <CardContent className="p-4 flex items-center gap-2 text-red-400">
            <AlertCircle className="h-5 w-5" />
            <span>{error}</span>
          </CardContent>
        </Card>
      )}

      {trancheDetails && (
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Tranche Details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-slate-400">Tranche Name</p>
                <p className="text-lg font-semibold text-slate-100">{trancheDetails.tranche_name}</p>
              </div>
              <div>
                <p className="text-sm text-slate-400">Class</p>
                <p className="text-lg font-semibold text-slate-100">{trancheDetails.tranche_class}</p>
              </div>
              <div>
                <p className="text-sm text-slate-400">Size</p>
                <p className="text-lg font-semibold text-slate-100">
                  {trancheDetails.currency} {purchaseAmount.toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-sm text-slate-400">Interest Rate</p>
                <p className="text-lg font-semibold text-slate-100">{trancheDetails.interest_rate}%</p>
              </div>
              {trancheDetails.risk_rating && (
                <div>
                  <p className="text-sm text-slate-400">Risk Rating</p>
                  <p className="text-lg font-semibold text-slate-100">{trancheDetails.risk_rating}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {paymentStatus === 'required' && paymentRequest && (
        <Card className="bg-blue-900/20 border-blue-500/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Payment Required
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-slate-900 p-4 rounded-lg">
              <div className="flex justify-between items-center mb-2">
                <span className="text-slate-400">Amount:</span>
                <span className="text-2xl font-bold text-slate-100">
                  {paymentRequest.currency} {parseFloat(paymentRequest.amount).toLocaleString()}
                </span>
              </div>
            </div>
            
            {paymentRequest.facilitator_url && (
              <div className="space-y-2">
                <p className="text-sm text-slate-400">
                  Complete payment via x402 facilitator:
                </p>
                <Button
                  onClick={() => window.open(paymentRequest.facilitator_url, '_blank')}
                  className="w-full bg-blue-600 hover:bg-blue-500 text-white"
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Open Payment Facilitator
                </Button>
              </div>
            )}
            
            <div className="flex gap-2">
              <Button
                onClick={() => {
                  setPaymentStatus('idle');
                  setPaymentRequest(null);
                }}
                variant="outline"
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={handlePurchase}
                disabled={isProcessing || loading}
                className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                {isProcessing || loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <CreditCard className="h-4 w-4 mr-2" />
                    Retry Payment
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {paymentStatus === 'paid' && (
        <Card className="bg-emerald-900/20 border-emerald-500/50">
          <CardContent className="p-6 text-center">
            <CheckCircle className="h-12 w-12 text-emerald-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-slate-100 mb-2">Purchase Successful!</h2>
            <p className="text-slate-400 mb-4">
              Your tranche purchase has been completed. Redirecting to pool details...
            </p>
            {lastTransactionHash && (
              <p className="text-xs text-slate-500 font-mono break-all">
                TX: {lastTransactionHash}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {paymentStatus === 'idle' && (
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wallet className="h-5 w-5" />
              Wallet Connection
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {!isConnected ? (
              <div className="space-y-4">
                <p className="text-slate-400">
                  Connect your MetaMask wallet to purchase this tranche.
                </p>
                <Button
                  onClick={connect}
                  className="w-full bg-blue-600 hover:bg-blue-500 text-white"
                >
                  <Wallet className="h-4 w-4 mr-2" />
                  Connect MetaMask
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="bg-slate-900 p-4 rounded-lg">
                  <p className="text-sm text-slate-400 mb-1">Connected Wallet</p>
                  <p className="text-slate-100 font-mono text-sm break-all">
                    {account}
                  </p>
                </div>
                
                <div className="bg-slate-900 p-4 rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-slate-400">Purchase Amount:</span>
                    <span className="text-2xl font-bold text-emerald-400">
                      {trancheDetails?.currency} {purchaseAmount.toLocaleString()}
                    </span>
                  </div>
                </div>
                
                <Button
                  onClick={handlePurchase}
                  disabled={isProcessing || loading}
                  className="w-full bg-emerald-600 hover:bg-emerald-500 text-white"
                >
                  {isProcessing || loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Processing Purchase...
                    </>
                  ) : (
                    <>
                      <CreditCard className="h-4 w-4 mr-2" />
                      Purchase Tranche
                    </>
                  )}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <div className="flex justify-end">
        <Button
          onClick={() => navigate(`/app/securitization/pools/${poolId}`)}
          variant="outline"
        >
          Back to Pool
        </Button>
      </div>
    </div>
  );
}
