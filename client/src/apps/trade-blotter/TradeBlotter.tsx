import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useFDC3 } from '@/context/FDC3Context';
import type { CreditAgreementData, Facility, CreditNexusLoanContext } from '@/context/FDC3Context';
import { FileText, Calendar, DollarSign, Building2, CheckCircle2, Clock, AlertTriangle, Shield, XCircle, Wallet, Loader2 } from 'lucide-react';
import { PermissionGate } from '@/components/PermissionGate';
import { PERMISSION_TRADE_EXECUTE, PERMISSION_TRADE_VIEW } from '@/utils/permissions';

function addBusinessDays(date: Date, days: number): Date {
  const result = new Date(date);
  let added = 0;
  while (added < days) {
    result.setDate(result.getDate() + 1);
    const dayOfWeek = result.getDay();
    if (dayOfWeek !== 0 && dayOfWeek !== 6) {
      added++;
    }
  }
  return result;
}

function formatDate(date: Date): string {
  return date.toISOString().split('T')[0];
}

interface PolicyDecision {
  decision: 'ALLOW' | 'BLOCK' | 'FLAG';
  rule_applied?: string;
  trace_id?: string;
  requires_review?: boolean;
}

interface PaymentRequest {
  amount: string;
  currency: string;
  payer: { id: string; name: string; lei?: string };
  receiver: { id: string; name: string; lei?: string };
  facilitator_url: string;
}

interface TradeBlotterState {
  loanData: CreditAgreementData | null;
  tradeStatus: 'pending' | 'confirmed' | 'settled';
  settlementDate: string;
  tradePrice: string;
  tradeAmount: string;
  tradeId: string | null;
  policyDecision: PolicyDecision | null;
  policyLoading: boolean;
  policyError: string | null;
  paymentRequest: PaymentRequest | null;
  paymentLoading: boolean;
  paymentError: string | null;
  paymentStatus: 'idle' | 'requested' | 'processing' | 'completed' | 'failed';
}

interface TradeBlotterProps {
  state: TradeBlotterState;
  setState: React.Dispatch<React.SetStateAction<TradeBlotterState>>;
}

export function TradeBlotter({ state, setState }: TradeBlotterProps) {
  const { context, clearContext } = useFDC3();
  const { 
    loanData, 
    tradeStatus, 
    settlementDate, 
    tradePrice, 
    tradeAmount, 
    tradeId,
    policyDecision, 
    policyLoading, 
    policyError,
    paymentRequest,
    paymentLoading,
    paymentError,
    paymentStatus
  } = state;

  useEffect(() => {
    if (context?.loan) {
      const isNewLoan = !loanData || 
        loanData.deal_id !== context.loan.deal_id ||
        loanData.agreement_date !== context.loan.agreement_date;
      
      if (isNewLoan) {
        const today = new Date();
        const settlement = addBusinessDays(today, 5);
        
        const totalCommitment = context.loan.facilities?.reduce(
          (sum: number, f: Facility) => sum + (f.commitment_amount?.amount || 0), 0
        ) || 0;
        
        setState(prev => ({
          ...prev,
          loanData: context.loan,
          tradeStatus: 'pending',
          settlementDate: formatDate(settlement),
          tradeAmount: totalCommitment.toString(),
          tradeId: null,
          policyDecision: null,
          policyLoading: false,
          policyError: null,
          paymentRequest: null,
          paymentLoading: false,
          paymentError: null,
          paymentStatus: 'idle',
        }));
      }
    }
  }, [context, setState, loanData]);

  const handleConfirmTrade = async () => {
    if (!loanData) return;
    
    // Reset policy state
    setState(prev => ({ ...prev, policyLoading: true, policyError: null, policyDecision: null }));
    
    try {
      const borrower = loanData.parties?.find(p => p.role.toLowerCase().includes('borrower'));
      const borrowerName = borrower?.name || borrower?.legal_name || 'Unknown Borrower';
      const tradeAmountNum = parseFloat(tradeAmount) || 0;
      const rate = spread / 100; // Convert bps to percentage
      
      // Generate trade ID
      const tradeId = `TRADE-${loanData.deal_id || 'AUTO'}-${Date.now()}`;
      
      // Call trade execution endpoint with policy evaluation
      const response = await fetch('/api/trades/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          trade_id: tradeId,
          borrower: borrowerName,
          amount: tradeAmountNum,
          rate: rate,
          credit_agreement_id: null, // Could be enhanced to pass document ID
        }),
      });
      
      const result = await response.json();
      
      if (result.status === 'blocked') {
        // Trade blocked by policy
        setState(prev => ({
          ...prev,
          policyDecision: {
            decision: 'BLOCK',
            rule_applied: result.rule,
            trace_id: result.trace_id,
          },
          policyLoading: false,
          policyError: result.message || 'Trade execution blocked by compliance policy',
        }));
        return; // Don't confirm trade if blocked
      }
      
      // Trade allowed or flagged - store trade_id for settlement
      const confirmedTradeId = result.trade_id || tradeId;
      
      setState(prev => ({
        ...prev,
        tradeStatus: 'confirmed',
        tradeId: confirmedTradeId,
        policyDecision: result.policy_decision ? {
          decision: result.policy_decision.decision,
          rule_applied: result.policy_decision.rule_applied,
          trace_id: result.policy_decision.trace_id,
          requires_review: result.policy_decision.requires_review || false,
        } : null,
        policyLoading: false,
        policyError: null,
      }));
      
    } catch (error) {
      console.error('Trade execution failed:', error);
      setState(prev => ({
        ...prev,
        policyLoading: false,
        policyError: error instanceof Error ? error.message : 'Failed to execute trade',
      }));
    }
  };

  const handleSettleTrade = async () => {
    if (!tradeId) {
      console.error('No trade ID available for settlement');
      setState(prev => ({
        ...prev,
        paymentError: 'Trade ID not found. Please confirm trade first.'
      }));
      return;
    }
    
    // Reset payment state
    setState(prev => ({
      ...prev,
      paymentLoading: true,
      paymentError: null,
      paymentStatus: 'processing'
    }));
    
    try {
      // Call trade settlement endpoint (without payment payload first to get payment request)
      const response = await fetch(`/api/trades/${tradeId}/settle`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          payment_payload: null  // Request payment instructions
        }),
      });
      
      if (response.status === 402) {
        // Payment Required - extract payment request
        const paymentData = await response.json();
        setState(prev => ({
          ...prev,
          paymentRequest: paymentData.payment_request || {
            amount: paymentData.amount,
            currency: paymentData.currency,
            payer: paymentData.payer,
            receiver: paymentData.receiver,
            facilitator_url: paymentData.facilitator_url
          },
          paymentStatus: 'requested',
          paymentLoading: false,
        }));
        return; // Show payment UI
      }
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail?.message || 'Settlement failed');
      }
      
      const result = await response.json();
      
      // Trade settled successfully
      setState(prev => ({
        ...prev,
        tradeStatus: 'settled',
        paymentStatus: 'completed',
        paymentLoading: false,
        paymentRequest: null,
      }));
      
    } catch (error) {
      console.error('Trade settlement failed:', error);
      setState(prev => ({
        ...prev,
        paymentLoading: false,
        paymentError: error instanceof Error ? error.message : 'Failed to settle trade',
        paymentStatus: 'failed',
      }));
    }
  };
  
  const handleSubmitPayment = async (paymentPayload: any) => {
    if (!tradeId) {
      setState(prev => ({
        ...prev,
        paymentError: 'Trade ID not found'
      }));
      return;
    }
    
    setState(prev => ({
      ...prev,
      paymentLoading: true,
      paymentError: null,
      paymentStatus: 'processing'
    }));
    
    try {
      const response = await fetch(`/api/trades/${tradeId}/settle`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          payment_payload: paymentPayload
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail?.message || 'Payment failed');
      }
      
      const result = await response.json();
      
      // Payment successful - trade settled
      setState(prev => ({
        ...prev,
        tradeStatus: 'settled',
        paymentStatus: 'completed',
        paymentLoading: false,
        paymentRequest: null,
      }));
      
    } catch (error) {
      console.error('Payment submission failed:', error);
      setState(prev => ({
        ...prev,
        paymentLoading: false,
        paymentError: error instanceof Error ? error.message : 'Payment submission failed',
        paymentStatus: 'failed',
      }));
    }
  };

  const handleClearTrade = () => {
    setState(prev => ({
      ...prev,
      loanData: null,
      tradeStatus: 'pending',
      tradeId: null,
      policyDecision: null,
      policyLoading: false,
      policyError: null,
      paymentRequest: null,
      paymentLoading: false,
      paymentError: null,
      paymentStatus: 'idle',
    }));
    clearContext();
  };

  const setTradeAmount = (value: string) => {
    setState(prev => ({ ...prev, tradeAmount: value }));
  };

  const setTradePrice = (value: string) => {
    setState(prev => ({ ...prev, tradePrice: value }));
  };

  const borrower = loanData?.parties?.find(p => p.role.toLowerCase().includes('borrower'));
  const currency = loanData?.facilities?.[0]?.commitment_amount?.currency || 'USD';
  const spread = loanData?.facilities?.[0]?.interest_terms?.rate_option?.spread_bps || 0;

  const industryStandard = 20;
  const ourSettlement = 5;
  const daysSaved = industryStandard - ourSettlement;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Trade Blotter</h2>
          <p className="text-muted-foreground">LMA Trade Confirmation & Settlement</p>
        </div>
        {loanData && (
          <Button variant="outline" size="sm" onClick={handleClearTrade}>
            Clear Trade
          </Button>
        )}
      </div>

      {!loanData ? (
        <Card className="border-slate-700 bg-slate-800/50">
          <CardContent className="p-12 text-center">
            <div className="w-20 h-20 rounded-full bg-slate-700/50 flex items-center justify-center mx-auto mb-6">
              <FileText className="h-10 w-10 text-slate-500" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Waiting for Loan Context</h3>
            <p className="text-muted-foreground max-w-md mx-auto">
              Use the Docu-Digitizer to extract loan data and broadcast it to this Trade Blotter.
              The trade ticket will be pre-filled automatically.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card className="border-slate-700 bg-slate-800/50">
              <CardHeader className="border-b border-slate-700">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="h-5 w-5 text-emerald-400" />
                    LMA Trade Confirmation Ticket
                  </CardTitle>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    tradeStatus === 'settled' ? 'bg-emerald-500/20 text-emerald-400' :
                    tradeStatus === 'confirmed' ? 'bg-blue-500/20 text-blue-400' :
                    'bg-yellow-500/20 text-yellow-400'
                  }`}>
                    {tradeStatus === 'settled' ? 'Settled' :
                     tradeStatus === 'confirmed' ? 'Confirmed' : 'Pending'}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="p-6">
                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <label className="text-xs text-muted-foreground flex items-center gap-1">
                        <Building2 className="h-3 w-3" /> Borrower
                      </label>
                      <p className="font-medium text-lg">{borrower?.name || 'N/A'}</p>
                      {borrower?.lei && (
                        <p className="text-xs font-mono text-muted-foreground">LEI: {borrower.lei}</p>
                      )}
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Facility</label>
                      <p className="font-medium">
                        {loanData.facilities?.[0]?.facility_name || 'Term Loan'}
                      </p>
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Deal ID</label>
                      <p className="font-mono">{loanData.deal_id || (context?.type === 'fdc3.creditnexus.loan' ? (context as CreditNexusLoanContext).id?.DealID : undefined) || 'AUTO-' + Date.now().toString(36).toUpperCase()}</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="text-xs text-muted-foreground flex items-center gap-1">
                        <DollarSign className="h-3 w-3" /> Trade Amount
                      </label>
                      <input
                        type="text"
                        value={tradeAmount}
                        onChange={(e) => setTradeAmount(e.target.value)}
                        disabled={tradeStatus !== 'pending'}
                        className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg font-mono text-lg disabled:opacity-50"
                      />
                      <p className="text-xs text-muted-foreground mt-1">{currency}</p>
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Trade Price</label>
                      <input
                        type="text"
                        value={tradePrice}
                        onChange={(e) => setTradePrice(e.target.value)}
                        disabled={tradeStatus !== 'pending'}
                        className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg font-mono disabled:opacity-50"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Margin (bps)</label>
                      <p className="font-mono text-emerald-400">+{spread}</p>
                    </div>
                  </div>
                </div>

                <div className="mt-6 pt-6 border-t border-slate-700">
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="text-xs text-muted-foreground flex items-center gap-1">
                        <Calendar className="h-3 w-3" /> Trade Date
                      </label>
                      <p className="font-medium">{formatDate(new Date())}</p>
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground flex items-center gap-1">
                        <Calendar className="h-3 w-3" /> Settlement Date (T+5)
                      </label>
                      <p className="font-medium text-emerald-400">{settlementDate}</p>
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Agreement Date</label>
                      <p className="font-medium">{loanData.agreement_date || 'N/A'}</p>
                    </div>
                  </div>
                </div>

                {/* Policy Decision Display */}
                {policyDecision && (
                  <div className={`mt-6 p-4 rounded-lg border ${
                    policyDecision.decision === 'BLOCK' 
                      ? 'bg-red-500/10 border-red-500/30 text-red-400'
                      : policyDecision.decision === 'FLAG'
                      ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400'
                      : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                  }`}>
                    <div className="flex items-start gap-3">
                      {policyDecision.decision === 'BLOCK' && (
                        <XCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                      )}
                      {policyDecision.decision === 'FLAG' && (
                        <AlertTriangle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                      )}
                      {policyDecision.decision === 'ALLOW' && (
                        <Shield className="h-5 w-5 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1">
                        <div className="font-medium mb-1">
                          {policyDecision.decision === 'BLOCK' && 'Trade Blocked by Policy'}
                          {policyDecision.decision === 'FLAG' && 'Trade Flagged for Review'}
                          {policyDecision.decision === 'ALLOW' && 'Policy Compliance Verified'}
                        </div>
                        {policyDecision.rule_applied && (
                          <p className="text-xs opacity-80">
                            Rule: {policyDecision.rule_applied}
                          </p>
                        )}
                        {policyDecision.requires_review && (
                          <p className="text-xs mt-1 opacity-80">
                            This trade requires manual review before settlement.
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Policy Error Display */}
                {policyError && (
                  <div className="mt-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
                    <div className="flex items-start gap-3">
                      <XCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                      <div>
                        <div className="font-medium mb-1">Policy Evaluation Error</div>
                        <p className="text-xs opacity-80">{policyError}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Payment Request Display (x402 Payment Required) */}
                {paymentRequest && paymentStatus === 'requested' && (
                  <div className="mt-6 p-4 rounded-lg bg-blue-500/10 border border-blue-500/30">
                    <div className="flex items-start gap-3">
                      <Wallet className="h-5 w-5 flex-shrink-0 mt-0.5 text-blue-400" />
                      <div className="flex-1">
                        <div className="font-medium mb-2 text-blue-400">Payment Required (x402)</div>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Amount:</span>
                            <span className="font-mono font-medium">
                              {paymentRequest.amount} {paymentRequest.currency}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Payer:</span>
                            <span>{paymentRequest.payer.name}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Receiver:</span>
                            <span>{paymentRequest.receiver.name}</span>
                          </div>
                          <div className="mt-3 p-3 bg-slate-900/50 rounded border border-slate-700">
                            <p className="text-xs text-muted-foreground mb-2">
                              Connect your wallet and submit payment to complete settlement.
                            </p>
                            <p className="text-xs text-muted-foreground">
                              Facilitator: {paymentRequest.facilitator_url}
                            </p>
                          </div>
                        </div>
                        <div className="mt-4 flex gap-2">
                          <Button
                            size="sm"
                            onClick={() => {
                              // In production, this would connect to wallet and get payment payload
                              // For demo, we'll simulate a payment payload
                              const mockPaymentPayload = {
                                transaction: {
                                  to: paymentRequest.receiver.id,
                                  value: paymentRequest.amount,
                                  currency: paymentRequest.currency
                                },
                                signature: "mock_signature_for_demo"
                              };
                              handleSubmitPayment(mockPaymentPayload);
                            }}
                            className="bg-blue-600 hover:bg-blue-700"
                          >
                            <Wallet className="h-4 w-4 mr-2" />
                            Submit Payment
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setState(prev => ({
                                ...prev,
                                paymentRequest: null,
                                paymentStatus: 'idle'
                              }));
                            }}
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Payment Status Display */}
                {paymentStatus === 'processing' && (
                  <div className="mt-6 p-4 rounded-lg bg-blue-500/10 border border-blue-500/30">
                    <div className="flex items-center gap-3">
                      <Loader2 className="h-5 w-5 animate-spin text-blue-400" />
                      <div>
                        <div className="font-medium text-blue-400">Processing Payment...</div>
                        <p className="text-xs text-muted-foreground mt-1">
                          Verifying and settling payment via x402
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Payment Error Display */}
                {paymentError && (
                  <div className="mt-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
                    <div className="flex items-start gap-3">
                      <XCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                      <div>
                        <div className="font-medium mb-1">Payment Error</div>
                        <p className="text-xs opacity-80">{paymentError}</p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="mt-6 flex gap-4">
                  {tradeStatus === 'pending' && (
                    <PermissionGate permission={PERMISSION_TRADE_EXECUTE}>
                      <Button 
                        onClick={handleConfirmTrade} 
                        disabled={policyLoading || policyDecision?.decision === 'BLOCK'}
                        className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {policyLoading ? (
                          <>
                            <Clock className="h-4 w-4 mr-2 animate-spin" />
                            Evaluating Policy...
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="h-4 w-4 mr-2" />
                            Confirm Trade
                          </>
                        )}
                      </Button>
                    </PermissionGate>
                  )}
                  {tradeStatus === 'confirmed' && (
                    <PermissionGate permission={PERMISSION_TRADE_EXECUTE}>
                      <Button 
                        onClick={handleSettleTrade} 
                        disabled={paymentLoading}
                        className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {paymentLoading ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Processing Payment...
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="h-4 w-4 mr-2" />
                            Settle Trade
                          </>
                        )}
                      </Button>
                    </PermissionGate>
                  )}
                  {tradeStatus === 'settled' && (
                    <div className="flex items-center gap-2 text-emerald-400">
                      <CheckCircle2 className="h-5 w-5" />
                      <span className="font-medium">Trade Successfully Settled</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="border-emerald-500/30 bg-emerald-500/5">
              <CardHeader>
                <CardTitle className="text-emerald-400 flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Settlement Advantage
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center">
                  <div className="text-4xl font-bold text-emerald-400 mb-2">T+{ourSettlement}</div>
                  <p className="text-sm text-muted-foreground mb-4">Our Settlement Time</p>
                  
                  <div className="flex items-center justify-center gap-2 text-sm">
                    <span className="text-muted-foreground">vs Industry Standard</span>
                    <span className="font-mono text-yellow-400">T+{industryStandard}</span>
                  </div>
                  
                  <div className="mt-4 p-3 bg-emerald-500/10 rounded-lg">
                    <p className="text-emerald-400 font-medium">
                      {daysSaved} Business Days Saved
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Faster settlement reduces counterparty risk
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-700 bg-slate-800/50">
              <CardHeader>
                <CardTitle className="text-sm">Trade Workflow</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className={`flex items-center gap-3 ${tradeStatus !== 'pending' ? 'text-emerald-400' : 'text-muted-foreground'}`}>
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                      tradeStatus !== 'pending' ? 'bg-emerald-500/20' : 'bg-slate-700'
                    }`}>1</div>
                    <span>Ticket Pre-filled</span>
                    {tradeStatus !== 'pending' && <CheckCircle2 className="h-4 w-4 ml-auto" />}
                  </div>
                  <div className={`flex items-center gap-3 ${
                    tradeStatus === 'confirmed' || tradeStatus === 'settled' ? 'text-emerald-400' : 'text-muted-foreground'
                  }`}>
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                      tradeStatus === 'confirmed' || tradeStatus === 'settled' ? 'bg-emerald-500/20' : 'bg-slate-700'
                    }`}>2</div>
                    <span>Trade Confirmed</span>
                    {(tradeStatus === 'confirmed' || tradeStatus === 'settled') && <CheckCircle2 className="h-4 w-4 ml-auto" />}
                  </div>
                  <div className={`flex items-center gap-3 ${tradeStatus === 'settled' ? 'text-emerald-400' : 'text-muted-foreground'}`}>
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                      tradeStatus === 'settled' ? 'bg-emerald-500/20' : 'bg-slate-700'
                    }`}>3</div>
                    <span>Settled (T+5)</span>
                    {tradeStatus === 'settled' && <CheckCircle2 className="h-4 w-4 ml-auto" />}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
