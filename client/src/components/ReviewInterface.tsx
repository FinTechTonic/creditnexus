import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CheckCircle2, XCircle, FileText, Code } from 'lucide-react';
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

  const handleApprove = () => {
    if (extractedData) {
      // Broadcast to FDC3
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
      <Card className="w-full">
        <CardHeader>
          <CardTitle>No Data to Review</CardTitle>
          <CardDescription>Extract data from a document first</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const isSuccess = extractedData.extraction_status === 'success' || !extractedData.extraction_status;
  const isFailure = extractedData.extraction_status === 'irrelevant_document';

  return (
    <div className="w-full h-full flex flex-col gap-4">
      {/* Status Banner */}
      {isFailure && (
        <Card className="border-destructive bg-destructive/10">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <XCircle className="h-5 w-5" />
              <span className="font-semibold">Document Not Recognized</span>
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              This document does not appear to be a credit agreement.
            </p>
          </CardContent>
        </Card>
      )}

      {isSuccess && (
        <Card className="border-green-500/50 bg-green-500/10">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
              <CheckCircle2 className="h-5 w-5" />
              <span className="font-semibold">Extraction Successful</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Review Area */}
      <div className="flex-1 grid grid-cols-2 gap-4 min-h-0">
        {/* Left: Document Text */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Source Document
            </CardTitle>
            <CardDescription>Original credit agreement text</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 overflow-auto">
            <pre className="text-xs font-mono whitespace-pre-wrap text-muted-foreground">
              {documentText || 'No document text available'}
            </pre>
          </CardContent>
        </Card>

        {/* Right: Extracted JSON */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Code className="h-5 w-5" />
              Extracted Data
            </CardTitle>
            <CardDescription>FINOS CDM-compliant structured data</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 overflow-auto">
            <Tabs defaultValue="json" className="w-full">
              <TabsList>
                <TabsTrigger value="json">JSON</TabsTrigger>
                <TabsTrigger value="summary">Summary</TabsTrigger>
              </TabsList>
              <TabsContent value="json" className="mt-4">
                <pre className="text-xs font-mono bg-muted p-4 rounded-md overflow-auto">
                  {JSON.stringify(extractedData, null, 2)}
                </pre>
              </TabsContent>
              <TabsContent value="summary" className="mt-4 space-y-4">
                <div>
                  <h4 className="font-semibold mb-2">Agreement Date</h4>
                  <p className="text-sm text-muted-foreground">{extractedData.agreement_date}</p>
                </div>
                <div>
                  <h4 className="font-semibold mb-2">Parties ({extractedData.parties?.length || 0})</h4>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    {extractedData.parties?.map((party, idx) => (
                      <li key={idx}>
                        {party.name} ({party.role})
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold mb-2">Facilities ({extractedData.facilities?.length || 0})</h4>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    {extractedData.facilities?.map((facility, idx) => (
                      <li key={idx}>
                        {facility.facility_name}: {facility.commitment_amount.amount.toLocaleString()} {facility.commitment_amount.currency}
                        <br />
                        <span className="text-xs">Maturity: {facility.maturity_date}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold mb-2">Governing Law</h4>
                  <p className="text-sm text-muted-foreground">{extractedData.governing_law}</p>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>

      {/* Action Buttons */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1">
              {!isSuccess && (
                <textarea
                  placeholder="Rejection reason (optional)"
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  className="w-full min-h-[60px] px-3 py-2 text-sm border rounded-md bg-background"
                />
              )}
            </div>
            <div className="flex gap-2">
              <Button
                variant="destructive"
                onClick={handleReject}
                disabled={!extractedData}
              >
                <XCircle className="h-4 w-4 mr-2" />
                Reject
              </Button>
              <Button
                onClick={handleApprove}
                disabled={!extractedData || !isSuccess}
              >
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Approve
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

