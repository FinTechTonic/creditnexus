import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  CheckCircle2, 
  XCircle, 
  FileText, 
  Code, 
  Calendar, 
  Users, 
  Building2, 
  Scale,
  DollarSign,
  Clock
} from 'lucide-react';
import { useFDC3 } from '@/hooks/useFDC3';

interface CreditAgreement {
  agreement_date: string;
  parties: Array<{ name: string; role: string }>;
  facilities: Array<{
    facility_name: string;
    commitment_amount: { amount: number; currency: string };
    maturity_date: string;
  }>;
  governing_law: string;
  extraction_status?: string;
}

interface ReviewInterfaceProps {
  documentText?: string;
  extractedData?: CreditAgreement;
  onApprove: (data: CreditAgreement) => void;
  onReject: (reason?: string) => void;
}

export function ReviewInterface({
  documentText = '',
  extractedData,
  onApprove,
  onReject,
}: ReviewInterfaceProps) {
  const { broadcast } = useFDC3();
  const [rejectionReason, setRejectionReason] = useState('');
  const [activeTab, setActiveTab] = useState('summary');

  const handleApprove = () => {
    if (extractedData) {
      broadcast({
        type: 'fdc3.creditnexus.loan',
        loan: {
          agreementDate: extractedData.agreement_date,
          parties: extractedData.parties,
          facilities: extractedData.facilities?.map(f => ({
            name: f.facility_name,
            amount: f.commitment_amount.amount,
            currency: f.commitment_amount.currency,
          })),
        },
      });
      onApprove(extractedData);
    }
  };

  const handleReject = () => {
    onReject(rejectionReason || 'Rejected by analyst');
  };

  if (!extractedData) {
    return (
      <Card className="shadow-lg border-0">
        <CardHeader className="text-center py-12">
          <CardTitle className="text-muted-foreground">No Data to Review</CardTitle>
          <p className="text-sm text-muted-foreground mt-2">Extract data from a document first</p>
        </CardHeader>
      </Card>
    );
  }

  const isSuccess = extractedData.extraction_status === 'success' || !extractedData.extraction_status;
  const isFailure = extractedData.extraction_status === 'irrelevant_document';

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const totalCommitment = extractedData.facilities?.reduce(
    (sum, f) => sum + f.commitment_amount.amount,
    0
  ) || 0;

  const currency = extractedData.facilities?.[0]?.commitment_amount.currency || 'USD';

  return (
    <div className="space-y-6">
      {isFailure && (
        <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-xl flex items-center gap-3">
          <XCircle className="h-5 w-5 text-destructive flex-shrink-0" />
          <div>
            <p className="font-medium text-destructive">Document Not Recognized</p>
            <p className="text-sm text-muted-foreground">This document does not appear to be a credit agreement.</p>
          </div>
        </div>
      )}

      {isSuccess && (
        <div className="p-4 bg-[oklch(55%_0.15_145_/_0.1)] border border-[oklch(55%_0.15_145_/_0.2)] rounded-xl flex items-center gap-3">
          <CheckCircle2 className="h-5 w-5 text-[oklch(55%_0.15_145)] flex-shrink-0" />
          <div>
            <p className="font-medium text-[oklch(45%_0.12_145)]">Extraction Complete</p>
            <p className="text-sm text-muted-foreground">Review the extracted data below and approve or reject.</p>
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2">
          <Card className="shadow-lg border-0 h-full">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <CardTitle className="text-base">Source Document</CardTitle>
                  <p className="text-xs text-muted-foreground">{documentText.length.toLocaleString()} characters</p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[500px] overflow-auto rounded-lg bg-muted/50 p-4">
                <pre className="text-xs font-mono whitespace-pre-wrap text-muted-foreground leading-relaxed">
                  {documentText || 'No document text available'}
                </pre>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-3">
          <Card className="shadow-lg border-0">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Code className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-base">Extracted Data</CardTitle>
                  <p className="text-xs text-muted-foreground">FINOS CDM Format</p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <TabsList className="w-full grid grid-cols-2 mb-4">
                  <TabsTrigger value="summary" className="gap-2">
                    <Users className="h-4 w-4" />
                    Summary
                  </TabsTrigger>
                  <TabsTrigger value="json" className="gap-2">
                    <Code className="h-4 w-4" />
                    Raw JSON
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="summary" className="mt-0">
                  <div className="space-y-6">
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div className="p-4 rounded-xl bg-muted/50">
                        <div className="flex items-center gap-2 text-muted-foreground mb-2">
                          <Calendar className="h-4 w-4" />
                          <span className="text-xs font-medium uppercase tracking-wide">Agreement Date</span>
                        </div>
                        <p className="text-lg font-semibold">{formatDate(extractedData.agreement_date)}</p>
                      </div>
                      <div className="p-4 rounded-xl bg-muted/50">
                        <div className="flex items-center gap-2 text-muted-foreground mb-2">
                          <DollarSign className="h-4 w-4" />
                          <span className="text-xs font-medium uppercase tracking-wide">Total Commitment</span>
                        </div>
                        <p className="text-lg font-semibold">{formatCurrency(totalCommitment, currency)}</p>
                      </div>
                    </div>

                    <div className="p-4 rounded-xl bg-muted/50">
                      <div className="flex items-center gap-2 text-muted-foreground mb-3">
                        <Users className="h-4 w-4" />
                        <span className="text-xs font-medium uppercase tracking-wide">Parties ({extractedData.parties?.length || 0})</span>
                      </div>
                      <div className="space-y-2">
                        {extractedData.parties?.map((party, idx) => (
                          <div key={idx} className="flex items-center justify-between p-3 bg-background rounded-lg">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                                <Building2 className="h-4 w-4 text-primary" />
                              </div>
                              <span className="font-medium">{party.name}</span>
                            </div>
                            <span className="px-3 py-1 text-xs font-medium bg-secondary text-secondary-foreground rounded-full">
                              {party.role}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="p-4 rounded-xl bg-muted/50">
                      <div className="flex items-center gap-2 text-muted-foreground mb-3">
                        <DollarSign className="h-4 w-4" />
                        <span className="text-xs font-medium uppercase tracking-wide">Facilities ({extractedData.facilities?.length || 0})</span>
                      </div>
                      <div className="space-y-3">
                        {extractedData.facilities?.map((facility, idx) => (
                          <div key={idx} className="p-4 bg-background rounded-lg">
                            <div className="flex items-start justify-between mb-3">
                              <h4 className="font-semibold">{facility.facility_name}</h4>
                              <span className="text-lg font-bold text-primary">
                                {formatCurrency(facility.commitment_amount.amount, facility.commitment_amount.currency)}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <Clock className="h-4 w-4" />
                              <span>Maturity: {formatDate(facility.maturity_date)}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="p-4 rounded-xl bg-muted/50">
                      <div className="flex items-center gap-2 text-muted-foreground mb-2">
                        <Scale className="h-4 w-4" />
                        <span className="text-xs font-medium uppercase tracking-wide">Governing Law</span>
                      </div>
                      <p className="font-medium">{extractedData.governing_law}</p>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="json" className="mt-0">
                  <div className="h-[420px] overflow-auto rounded-lg bg-muted/50 p-4">
                    <pre className="text-xs font-mono text-muted-foreground">
                      {JSON.stringify(extractedData, null, 2)}
                    </pre>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card className="shadow-lg border-0">
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
            <div className="flex-1">
              {!isSuccess && (
                <textarea
                  placeholder="Rejection reason (optional)..."
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  className="w-full min-h-[60px] px-4 py-3 text-sm border rounded-xl bg-muted/50 resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
              )}
              {isSuccess && (
                <p className="text-muted-foreground">
                  Review the extracted data above. Approve to send to staging or reject with a reason.
                </p>
              )}
            </div>
            <div className="flex gap-3">
              <Button
                variant="outline"
                size="lg"
                onClick={handleReject}
                disabled={!extractedData}
                className="gap-2 border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
              >
                <XCircle className="h-4 w-4" />
                Reject
              </Button>
              <Button
                size="lg"
                onClick={handleApprove}
                disabled={!extractedData || !isSuccess}
                className="gap-2"
              >
                <CheckCircle2 className="h-4 w-4" />
                Approve & Stage
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
