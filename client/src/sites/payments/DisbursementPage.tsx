import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  DollarSign, 
  Wallet, 
  CheckCircle, 
  AlertCircle,
  Loader2,
  Copy
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { useAuth } from '@/context/AuthContext';

interface LoanDetails {
  id: number;
  amount: number;
  currency: string;
  borrower: string;
  interest_rate: number;
  term_months: number;
  disbursement_date: string;
  repayment_schedule: Array<{
    date: string;
    amount: number;
    principal: number;
    interest: number;
  }>;
}

export function DisbursementPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user: _user } = useAuth(); // user unused - prefix with _
  const loanId = searchParams.get('loan_id');
  
  const [loanDetails, setLoanDetails] = useState<LoanDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [walletConnected, setWalletConnected] = useState(false);
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [transactionHash, setTransactionHash] = useState<string | null>(null);

  useEffect(() => {
    if (loanId) {
      fetchLoanDetails();
    } else {
      setError('Loan ID is required');
      setLoading(false);
    }
  }, [loanId]);

  const fetchLoanDetails = async () => {
    try {
      const response = await fetchWithAuth(`/api/loans/${loanId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch loan details');
      }
      const data = await response.json();
      setLoanDetails(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load loan details');
    } finally {
      setLoading(false);
    }
  };

  const connectWallet = async () => {
    try {
      if (typeof window.ethereum !== 'undefined') {
        const accounts = await window.ethereum.request({ 
          method: 'eth_requestAccounts' 
        }) as string[];
        if (Array.isArray(accounts) && accounts.length > 0) {
          setWalletAddress(accounts[0]);
          setWalletConnected(true);
        }
      } else {
        setError('MetaMask is not installed. Please install MetaMask to continue.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect wallet');
    }
  };

  const handleDisbursement = async () => {
    if (!walletConnected || !walletAddress || !loanDetails) {
      setError('Please connect your wallet first');
      return;
    }

    setProcessing(true);
    setError(null);

    try {
      // x402 payment protocol integration
      const response = await fetchWithAuth('/api/payments/disburse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          loan_id: loanId,
          wallet_address: walletAddress,
          amount: loanDetails.amount,
          currency: loanDetails.currency,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Disbursement failed');
      }

      const data = await response.json();
      setTransactionHash(data.transaction_hash);
      
      // Navigate to receipt page after successful disbursement
      setTimeout(() => {
        navigate(`/receipt?loan_id=${loanId}&tx_hash=${data.transaction_hash}`);
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Disbursement failed');
    } finally {
      setProcessing(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  if (loading) {
    return (
      <div className="min-h-screen surface-gradient text-[var(--color-foreground)] py-12 px-4">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  if (error && !loanDetails) {
    return (
      <div className="min-h-screen surface-gradient text-[var(--color-foreground)] py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <Card className="surface-panel">
            <CardContent className="p-8 text-center">
              <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
              <h1 className="text-2xl font-bold mb-2">Error</h1>
              <p className="text-[var(--color-muted-foreground)] mb-6">{error}</p>
              <Button onClick={() => navigate('/dashboard')}>
                Go to Dashboard
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen surface-gradient text-[var(--color-foreground)] py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Loan Disbursement</h1>
          <p className="text-[var(--color-muted-foreground)]">Complete the disbursement process using x402 payment protocol</p>
        </div>

        {loanDetails && (
          <>
            {/* Loan Details Card */}
            <Card className="surface-panel mb-6">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5 text-emerald-400" />
                  Loan Details
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-[var(--color-muted-foreground)]">Borrower</p>
                    <p className="text-lg font-semibold">{loanDetails.borrower}</p>
                  </div>
                  <div>
                    <p className="text-sm text-[var(--color-muted-foreground)]">Amount</p>
                    <p className="text-lg font-semibold">
                      {loanDetails.currency} {loanDetails.amount.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-[var(--color-muted-foreground)]">Interest Rate</p>
                    <p className="text-lg font-semibold">{loanDetails.interest_rate}%</p>
                  </div>
                  <div>
                    <p className="text-sm text-[var(--color-muted-foreground)]">Term</p>
                    <p className="text-lg font-semibold">{loanDetails.term_months} months</p>
                  </div>
                  <div>
                    <p className="text-sm text-[var(--color-muted-foreground)]">Disbursement Date</p>
                    <p className="text-lg font-semibold">
                      {new Date(loanDetails.disbursement_date).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Wallet Connection Card */}
            <Card className="surface-panel mb-6">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Wallet className="h-5 w-5 text-blue-400" />
                  Wallet Connection
                </CardTitle>
              </CardHeader>
              <CardContent>
                {!walletConnected ? (
                  <div className="space-y-4">
                    <p className="text-[var(--color-muted-foreground)]">
                      Connect your MetaMask wallet to proceed with the disbursement
                    </p>
                    <Button
                      onClick={connectWallet}
                      className="gap-2"
                    >
                      <Wallet className="h-4 w-4" />
                      Connect MetaMask
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 text-emerald-400">
                      <CheckCircle className="h-5 w-5" />
                      <span>Wallet Connected</span>
                    </div>
                    <div className="bg-[var(--color-panel-deep)] rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm text-[var(--color-muted-foreground)] mb-1">Wallet Address</p>
                          <p className="font-mono text-sm break-all">{walletAddress}</p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => walletAddress && copyToClipboard(walletAddress)}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Disbursement Action */}
            {walletConnected && (
              <Card className="surface-panel mb-6">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="text-sm text-[var(--color-muted-foreground)]">Disbursement Amount</p>
                      <p className="text-3xl font-bold text-emerald-400">
                        {loanDetails.currency} {loanDetails.amount.toLocaleString()}
                      </p>
                    </div>
                  </div>
                  
                  {transactionHash ? (
                    <div className="space-y-4">
                      <div className="flex items-center gap-2 text-emerald-400">
                        <CheckCircle className="h-5 w-5" />
                        <span>Transaction Submitted</span>
                      </div>
                      <div className="bg-[var(--color-panel-deep)] rounded-lg p-4">
                        <p className="text-sm text-[var(--color-muted-foreground)] mb-1">Transaction Hash</p>
                        <div className="flex items-center gap-2">
                          <p className="font-mono text-sm break-all">{transactionHash}</p>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => transactionHash && copyToClipboard(transactionHash)}
                          >
                            <Copy className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                      <p className="text-sm text-[var(--color-muted-foreground)]">
                        Redirecting to receipt page...
                      </p>
                    </div>
                  ) : (
                    <Button
                      onClick={handleDisbursement}
                      disabled={processing}
                      className="w-full gap-2"
                      size="lg"
                    >
                      {processing ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        <>
                          <DollarSign className="h-4 w-4" />
                          Confirm Disbursement
                        </>
                      )}
                    </Button>
                  )}
                </CardContent>
              </Card>
            )}

            {error && (
              <Card className="bg-[var(--color-error-bg)] border-[var(--color-error-border)]">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 text-[var(--color-error-foreground)]">
                    <AlertCircle className="h-5 w-5" />
                    <p>{error}</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Extend Window interface for MetaMask
// Note: Window.ethereum type is declared in WalletContext.tsx
// Using the same type to avoid conflicts
