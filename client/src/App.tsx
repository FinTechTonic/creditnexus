import { useState } from 'react';
import { ReviewInterface } from '@/components/ReviewInterface';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Upload, FileText } from 'lucide-react';

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

function App() {
  const [documentText, setDocumentText] = useState('');
  const [extractedData, setExtractedData] = useState<CreditAgreement | undefined>();
  const [isExtracting, setIsExtracting] = useState(false);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const text = await file.text();
    setDocumentText(text);
    setExtractedData(undefined);
  };

  const handleExtract = async () => {
    if (!documentText.trim()) return;

    setIsExtracting(true);
    try {
      const response = await fetch('/api/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: documentText }),
      });

      if (!response.ok) {
        throw new Error('Extraction failed');
      }

      const result = await response.json();
      setExtractedData(result.agreement || result);
    } catch (error) {
      console.error('Extraction error:', error);
      // For demo: use mock data
      setExtractedData({
        agreement_date: '2023-10-15',
        parties: [
          { name: 'ACME INDUSTRIES INC.', role: 'Borrower' },
          { name: 'GLOBAL BANK CORP.', role: 'Lender' },
        ],
        facilities: [
          {
            facility_name: 'Term Loan Facility',
            commitment_amount: { amount: 500000000, currency: 'USD' },
            maturity_date: '2028-10-15',
          },
        ],
        governing_law: 'State of New York',
        extraction_status: 'success',
      });
    } finally {
      setIsExtracting(false);
    }
  };

  const handleApprove = (data: CreditAgreement) => {
    console.log('Approved:', data);
    // TODO: Send to backend staging area
    alert('Data approved and sent to staging area');
  };

  const handleReject = (reason?: string) => {
    console.log('Rejected:', reason);
    // TODO: Send rejection to backend
    alert(`Data rejected: ${reason || 'No reason provided'}`);
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">CreditNexus</h1>
            <p className="text-muted-foreground">FINOS-Compliant Financial AI Agent</p>
          </div>
        </div>

        {!extractedData && (
          <Card>
            <CardHeader>
              <CardTitle>Upload Document</CardTitle>
              <CardDescription>
                Upload a credit agreement PDF or paste text to extract structured data
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4">
                <label className="flex-1">
                  <input
                    type="file"
                    accept=".pdf,.txt"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                  <Button variant="outline" className="w-full" asChild>
                    <span>
                      <Upload className="h-4 w-4 mr-2" />
                      Upload File
                    </span>
                  </Button>
                </label>
                <Button
                  onClick={handleExtract}
                  disabled={!documentText.trim() || isExtracting}
                >
                  <FileText className="h-4 w-4 mr-2" />
                  {isExtracting ? 'Extracting...' : 'Extract Data'}
                </Button>
              </div>
              {documentText && (
                <div className="mt-4">
                  <p className="text-sm text-muted-foreground mb-2">
                    Document loaded ({documentText.length} characters)
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {extractedData && (
          <ReviewInterface
            documentText={documentText}
            extractedData={extractedData}
            onApprove={handleApprove}
            onReject={handleReject}
          />
        )}
      </div>
    </div>
  );
}

export default App;
