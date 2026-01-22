import { useState, useEffect, Fragment } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  CheckCircle, 
  Download, 
  Printer, 
  Share2,
  FileText,
  Loader2,
  Copy
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

interface ReceiptData {
  loan_id: number;
  transaction_hash: string;
  amount: number;
  currency: string;
  borrower: string;
  disbursement_date: string;
  interest_rate: number;
  term_months: number;
  repayment_schedule: Array<{
    date: string;
    amount: number;
    principal: number;
    interest: number;
  }>;
}

export function ReceiptPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const loanId = searchParams.get('loan_id');
  const txHash = searchParams.get('tx_hash');
  
  const [receiptData, setReceiptData] = useState<ReceiptData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (loanId && txHash) {
      fetchReceiptData();
    } else {
      setError('Loan ID and transaction hash are required');
      setLoading(false);
    }
  }, [loanId, txHash]);

  const fetchReceiptData = async () => {
    try {
      const response = await fetchWithAuth(`/api/payments/receipt?loan_id=${loanId}&tx_hash=${txHash}`);
      if (!response.ok) {
        throw new Error('Failed to fetch receipt data');
      }
      const data = await response.json();
      setReceiptData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load receipt data');
    } finally {
      setLoading(false);
    }
  };

  const downloadPDF = async () => {
    if (!receiptData) return;
    
    setDownloading(true);
    try {
      const response = await fetchWithAuth(
        `/api/payments/receipt/pdf?loan_id=${loanId}&tx_hash=${txHash}`,
        { method: 'GET' }
      );
      
      if (!response.ok) {
        throw new Error('Failed to generate PDF');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `receipt_${loanId}_${txHash}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download PDF');
    } finally {
      setDownloading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleShare = async () => {
    if (navigator.share && receiptData) {
      try {
        await navigator.share({
          title: 'Loan Disbursement Receipt',
          text: `Loan disbursement receipt for ${receiptData.borrower}`,
          url: window.location.href,
        });
      } catch (err) {
        // User cancelled or share failed
        console.error('Share failed:', err);
      }
    } else {
      // Fallback: copy link to clipboard
      navigator.clipboard.writeText(window.location.href);
      alert('Link copied to clipboard');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  if (loading) {
    return (
      <div className="min-h-screen surface-gradient text-[var(--color-foreground)] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  if (error && !receiptData) {
    return (
      <div className="min-h-screen surface-gradient text-[var(--color-foreground)] py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <Card className="surface-panel">
            <CardContent className="p-8 text-center">
              <p className="text-[var(--color-muted-foreground)] mb-6">{error}</p>
              <Button
                onClick={() => navigate('/dashboard')}
                className="gap-2"
              >
                Go to Dashboard
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen surface-gradient text-[var(--color-foreground)] py-12 px-4 print:bg-white print:text-black">
      <div className="max-w-4xl mx-auto">
        {/* Success Header */}
        <div className="text-center mb-8 print:hidden">
          <div className="w-16 h-16 bg-[var(--color-success-bg)] rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="h-8 w-8 text-[var(--color-success)]" />
          </div>
          <h1 className="text-4xl font-bold mb-2">Disbursement Successful</h1>
          <p className="text-[var(--color-muted-foreground)]">Your loan has been disbursed successfully</p>
        </div>

        {receiptData && (
          <Fragment>
            <Card className="surface-panel print:bg-white print:border-gray-300">
              <CardHeader className="print:border-b print:border-gray-300">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="h-5 w-5 text-emerald-400" />
                    Receipt
                  </CardTitle>
                  <div className="flex gap-2 print:hidden">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={downloadPDF}
                      disabled={downloading}
                      className="gap-2"
                    >
                      {downloading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4" />
                      )}
                      PDF
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handlePrint}
                      className="gap-2"
                    >
                      <Printer className="h-4 w-4" />
                      Print
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleShare}
                      className="gap-2"
                    >
                      <Share2 className="h-4 w-4" />
                      Share
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-8 print:p-6">
                {/* Receipt Details */}
                <div className="space-y-6">
                  <div className="grid grid-cols-2 gap-6 print:grid-cols-2">
                    <div>
                      <p className="text-sm text-[var(--color-muted-foreground)] print:text-gray-600 mb-1">Loan ID</p>
                      <p className="text-lg font-semibold">#{receiptData.loan_id}</p>
                    </div>
                    <div>
                      <p className="text-sm text-[var(--color-muted-foreground)] print:text-gray-600 mb-1">Transaction Hash</p>
                      <div className="flex items-center gap-2">
                        <p className="text-lg font-semibold font-mono text-sm break-all">
                          {receiptData.transaction_hash}
                        </p>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard(receiptData.transaction_hash)}
                          className="print:hidden gap-2"
                        >
                          <Copy className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                    <div>
                      <p className="text-sm text-[var(--color-muted-foreground)] print:text-gray-600 mb-1">Borrower</p>
                      <p className="text-lg font-semibold">{receiptData.borrower}</p>
                    </div>
                    <div>
                      <p className="text-sm text-[var(--color-muted-foreground)] print:text-gray-600 mb-1">Disbursement Date</p>
                      <p className="text-lg font-semibold">
                        {new Date(receiptData.disbursement_date).toLocaleDateString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-[var(--color-muted-foreground)] print:text-gray-600 mb-1">Amount</p>
                      <p className="text-2xl font-bold text-[var(--color-success)] print:text-black">
                        {receiptData.currency} {receiptData.amount.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-[var(--color-muted-foreground)] print:text-gray-600 mb-1">Interest Rate</p>
                      <p className="text-lg font-semibold">{receiptData.interest_rate}%</p>
                    </div>
                  </div>

                  {/* Repayment Schedule */}
                  {receiptData.repayment_schedule && receiptData.repayment_schedule.length > 0 && (
                    <div className="border-t border-[var(--color-border)] print:border-gray-300 pt-6">
                      <h3 className="text-lg font-semibold mb-4">Repayment Schedule</h3>
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead>
                            <tr className="border-b border-[var(--color-border)] print:border-gray-300">
                              <th className="text-left py-2 text-sm text-[var(--color-muted-foreground)] print:text-gray-600">Date</th>
                              <th className="text-right py-2 text-sm text-[var(--color-muted-foreground)] print:text-gray-600">Principal</th>
                              <th className="text-right py-2 text-sm text-[var(--color-muted-foreground)] print:text-gray-600">Interest</th>
                              <th className="text-right py-2 text-sm text-[var(--color-muted-foreground)] print:text-gray-600">Total</th>
                            </tr>
                          </thead>
                          <tbody>
                            {receiptData.repayment_schedule.map((payment, index) => (
                              <tr 
                                key={index}
                                className="border-b border-[var(--color-divider)] print:border-gray-200"
                              >
                                <td className="py-2 text-sm">
                                  {new Date(payment.date).toLocaleDateString()}
                                </td>
                                <td className="text-right py-2 text-sm">
                                  {receiptData.currency} {payment.principal.toLocaleString()}
                                </td>
                                <td className="text-right py-2 text-sm">
                                  {receiptData.currency} {payment.interest.toLocaleString()}
                                </td>
                                <td className="text-right py-2 text-sm font-semibold">
                                  {receiptData.currency} {payment.amount.toLocaleString()}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-4 mt-6 print:hidden">
              <Button
                onClick={() => navigate('/dashboard')}
                className="gap-2"
              >
                Go to Dashboard
              </Button>
              <Button
                variant="outline"
                onClick={() => navigate(`/dashboard/applications`)}
                className="gap-2"
              >
                View Applications
              </Button>
            </div>
          </Fragment>
        )}
      </div>
    </div>
  );
}
