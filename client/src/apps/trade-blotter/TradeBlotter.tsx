import { useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useFDC3 } from '@/context/FDC3Context';
import type { CreditAgreementData, Facility, CreditNexusLoanContext } from '@/context/FDC3Context';
import { FileText, Calendar, DollarSign, Building2, CheckCircle2, Clock } from 'lucide-react';

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

interface TradeBlotterState {
  loanData: CreditAgreementData | null;
  tradeStatus: 'pending' | 'confirmed' | 'settled';
  settlementDate: string;
  tradePrice: string;
  tradeAmount: string;
}

interface TradeBlotterProps {
  state: TradeBlotterState;
  setState: React.Dispatch<React.SetStateAction<TradeBlotterState>>;
}

export function TradeBlotter({ state, setState }: TradeBlotterProps) {
  const { context, clearContext } = useFDC3();
  const { loanData, tradeStatus, settlementDate, tradePrice, tradeAmount } = state;

  useEffect(() => {
    if (context?.loan) {
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
      }));
    }
  }, [context, setState]);

  const handleConfirmTrade = () => {
    setState(prev => ({ ...prev, tradeStatus: 'confirmed' }));
  };

  const handleSettleTrade = () => {
    setState(prev => ({ ...prev, tradeStatus: 'settled' }));
  };

  const handleClearTrade = () => {
    setState(prev => ({
      ...prev,
      loanData: null,
      tradeStatus: 'pending',
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

                <div className="mt-6 flex gap-4">
                  {tradeStatus === 'pending' && (
                    <Button onClick={handleConfirmTrade} className="bg-blue-600 hover:bg-blue-700">
                      <CheckCircle2 className="h-4 w-4 mr-2" />
                      Confirm Trade
                    </Button>
                  )}
                  {tradeStatus === 'confirmed' && (
                    <Button onClick={handleSettleTrade} className="bg-emerald-600 hover:bg-emerald-700">
                      <CheckCircle2 className="h-4 w-4 mr-2" />
                      Mark as Settled
                    </Button>
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
