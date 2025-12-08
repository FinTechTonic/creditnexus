import { useState } from 'react';
import { ReviewInterface } from '@/components/ReviewInterface';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Upload, FileText, Sparkles, Shield, Zap, ArrowRight, X } from 'lucide-react';

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
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [extractedData, setExtractedData] = useState<CreditAgreement | undefined>();
  const [isExtracting, setIsExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warningMessage, setWarningMessage] = useState<string | null>(null);

  const isPdfFile = (file: File) => {
    return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setExtractedData(undefined);
    setError(null);

    if (isPdfFile(file)) {
      setUploadedFile(file);
      setDocumentText(`[PDF File: ${file.name}]`);
    } else {
      const text = await file.text();
      setDocumentText(text);
      setUploadedFile(null);
    }
  };

  const handleExtract = async () => {
    if (!documentText.trim() && !uploadedFile) return;

    setIsExtracting(true);
    setError(null);
    setWarningMessage(null);
    try {
      let response: Response;
      
      if (uploadedFile) {
        const formData = new FormData();
        formData.append('file', uploadedFile);
        response = await fetch('/api/upload', {
          method: 'POST',
          body: formData,
        });
      } else {
        response = await fetch('/api/extract', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: documentText }),
        });
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const detail = errorData.detail;
        if (typeof detail === 'object' && detail.message) {
          setError(detail.message);
        } else if (typeof detail === 'string') {
          setError(detail);
        } else {
          setError(`Extraction failed with status ${response.status}`);
        }
        return;
      }

      const result = await response.json();
      
      if (result.status === 'irrelevant_document') {
        setError(result.message || 'This document does not appear to be a credit agreement.');
        return;
      }
      
      if (result.agreement) {
        if (result.extracted_text && uploadedFile) {
          setDocumentText(result.extracted_text);
          setUploadedFile(null);
        }
        setExtractedData({
          ...result.agreement,
          extraction_status: result.status,
        });
        if (result.status === 'partial_data_missing' && result.message) {
          setWarningMessage(result.message);
        }
      } else {
        setError('No data could be extracted from this document.');
      }
    } catch (err) {
      console.error('Extraction error:', err);
      setError('Failed to connect to extraction service. Please try again.');
    } finally {
      setIsExtracting(false);
    }
  };

  const handleApprove = (data: CreditAgreement) => {
    console.log('Approved:', data);
    alert('Data approved and sent to staging area');
  };

  const handleReject = (reason?: string) => {
    console.log('Rejected:', reason);
    alert(`Data rejected: ${reason || 'No reason provided'}`);
  };

  const handleReset = () => {
    setDocumentText('');
    setUploadedFile(null);
    setExtractedData(undefined);
    setError(null);
    setWarningMessage(null);
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">CreditNexus</h1>
              <p className="text-xs text-muted-foreground">FINOS CDM Compliant</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2 text-sm text-muted-foreground">
              <Shield className="h-4 w-4 text-primary" />
              <span>Enterprise Grade</span>
            </div>
            {extractedData && (
              <Button variant="outline" size="sm" onClick={handleReset}>
                <X className="h-4 w-4 mr-2" />
                New Extraction
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {!extractedData ? (
          <div className="space-y-8">
            <div className="text-center max-w-2xl mx-auto space-y-4">
              <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
                Extract Structured Data from
                <span className="gradient-text"> Credit Agreements</span>
              </h2>
              <p className="text-lg text-muted-foreground">
                Upload your credit agreement documents and let AI extract machine-readable,
                FINOS CDM-compliant data in seconds.
              </p>
            </div>

            <div className="grid sm:grid-cols-3 gap-4 max-w-3xl mx-auto">
              <Card className="glass-card border-0 shadow-sm">
                <CardContent className="pt-6 text-center">
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3">
                    <Zap className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="font-semibold mb-1">Fast Processing</h3>
                  <p className="text-sm text-muted-foreground">Extract data from complex agreements in seconds</p>
                </CardContent>
              </Card>
              <Card className="glass-card border-0 shadow-sm">
                <CardContent className="pt-6 text-center">
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3">
                    <Shield className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="font-semibold mb-1">CDM Compliant</h3>
                  <p className="text-sm text-muted-foreground">Output follows FINOS Common Domain Model</p>
                </CardContent>
              </Card>
              <Card className="glass-card border-0 shadow-sm">
                <CardContent className="pt-6 text-center">
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3">
                    <FileText className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="font-semibold mb-1">Human Review</h3>
                  <p className="text-sm text-muted-foreground">Verify and approve extracted data before use</p>
                </CardContent>
              </Card>
            </div>

            <Card className="max-w-4xl mx-auto shadow-lg border-0">
              <CardContent className="p-8">
                <div className="space-y-6">
                  <div className="flex items-center gap-4">
                    <div className="flex-1 h-px bg-border" />
                    <span className="text-sm font-medium text-muted-foreground">Upload or Paste Document</span>
                    <div className="flex-1 h-px bg-border" />
                  </div>

                  <div className="grid md:grid-cols-2 gap-6">
                    <label className="group cursor-pointer">
                      <input
                        type="file"
                        accept=".pdf,.txt"
                        onChange={handleFileUpload}
                        className="hidden"
                      />
                      <div className="border-2 border-dashed rounded-xl p-8 text-center transition-all hover:border-primary hover:bg-primary/5 group-hover:border-primary">
                        <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mx-auto mb-4 group-hover:bg-primary/10 transition-colors">
                          <Upload className="h-8 w-8 text-muted-foreground group-hover:text-primary transition-colors" />
                        </div>
                        <p className="font-medium mb-1">Drop file here or click to upload</p>
                        <p className="text-sm text-muted-foreground">Supports PDF and TXT files</p>
                      </div>
                    </label>

                    <div className="space-y-3">
                      <textarea
                        placeholder="Or paste your credit agreement text here..."
                        value={uploadedFile ? '' : documentText}
                        onChange={(e) => {
                          setDocumentText(e.target.value);
                          setUploadedFile(null);
                          setError(null);
                        }}
                        disabled={!!uploadedFile}
                        className="w-full h-[180px] px-4 py-3 text-sm border rounded-xl bg-muted/50 resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                      />
                    </div>
                  </div>

                  {(documentText || uploadedFile) && (
                    <div className="flex items-center justify-between p-4 bg-muted/50 rounded-xl">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                          <FileText className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <p className="font-medium">
                            {uploadedFile ? uploadedFile.name : 'Document Ready'}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {uploadedFile 
                              ? `PDF file - ${(uploadedFile.size / 1024).toFixed(1)} KB` 
                              : `${documentText.length.toLocaleString()} characters`}
                          </p>
                        </div>
                      </div>
                      <Button
                        onClick={handleExtract}
                        disabled={isExtracting}
                        size="lg"
                        className="gap-2"
                      >
                        {isExtracting ? (
                          <>
                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            Processing...
                          </>
                        ) : (
                          <>
                            Extract Data
                            <ArrowRight className="h-4 w-4" />
                          </>
                        )}
                      </Button>
                    </div>
                  )}

                  {error && (
                    <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-xl text-destructive text-sm">
                      {error}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          <ReviewInterface
            documentText={documentText}
            extractedData={extractedData}
            warningMessage={warningMessage || undefined}
            onApprove={handleApprove}
            onReject={handleReject}
          />
        )}
      </main>

      <footer className="border-t mt-auto">
        <div className="max-w-7xl mx-auto px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <p>Powered by OpenAI GPT-4o and LangChain</p>
          <p>FINOS Common Domain Model Compliant</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
