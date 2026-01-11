/**
 * Test Transaction Builder - Form to build test transactions with pre-population.
 * 
 * Features:
 * - Form to build test transactions
 * - Pre-populate from deal/CDM data
 * - Save test cases for regression testing
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchWithAuth } from '../../context/AuthContext';
import { 
  Save, 
  Download, 
  Upload, 
  FileText, 
  Building2,
  Loader2,
  Plus,
  X,
  CheckCircle2
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../../components/ui/dialog';

// Types
interface TestTransaction {
  transaction_id?: string;
  transaction_type?: string;
  originator?: {
    id?: string;
    name?: string;
    lei?: string;
    jurisdiction?: string;
    kyc_status?: boolean;
  };
  amount?: number;
  currency?: string;
  facility_type?: string;
  sustainability_linked?: boolean;
  governing_law?: string;
  regulatory_framework?: string[];
  [key: string]: any;
}

interface TestCase {
  id?: string;
  name: string;
  description?: string;
  transaction: TestTransaction;
  expected_decision: 'ALLOW' | 'BLOCK' | 'FLAG';
}

interface TestTransactionBuilderProps {
  dealId?: number;
  cdmData?: any;
  onTransactionBuilt?: (transaction: TestTransaction) => void;
  onTestCaseSave?: (testCase: TestCase) => void;
  className?: string;
}

export function TestTransactionBuilder({ 
  dealId,
  cdmData,
  onTransactionBuilt,
  onTestCaseSave,
  className = '' 
}: TestTransactionBuilderProps) {
  const [transaction, setTransaction] = useState<TestTransaction>({});
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [testCaseName, setTestCaseName] = useState('');
  const [testCaseDescription, setTestCaseDescription] = useState('');
  const [expectedDecision, setExpectedDecision] = useState<'ALLOW' | 'BLOCK' | 'FLAG'>('ALLOW');
  const [activeTab, setActiveTab] = useState<'form' | 'json' | 'saved'>('form');
  
  // Load deal/CDM data on mount
  useEffect(() => {
    if (dealId) {
      loadDealData(dealId);
    } else if (cdmData) {
      populateFromCdmData(cdmData);
    }
  }, [dealId, cdmData]);
  
  const loadDealData = async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetchWithAuth(`/api/deals/${id}`);
      if (!response.ok) {
        throw new Error('Failed to load deal');
      }
      
      const data = await response.json();
      const deal = data.deal;
      
      // Populate transaction from deal
      const populated: TestTransaction = {
        transaction_id: deal.deal_id || `DEAL_${deal.id}`,
        transaction_type: 'facility_creation',
        originator: {
          id: deal.applicant_id?.toString(),
          name: deal.deal_data?.borrower_name,
          lei: deal.deal_data?.borrower_lei,
          jurisdiction: deal.deal_data?.jurisdiction || 'US',
          kyc_status: true
        },
        amount: deal.deal_data?.amount || 0,
        currency: deal.deal_data?.currency || 'USD',
        facility_type: deal.deal_type || 'SyndicatedLoan',
        sustainability_linked: deal.deal_data?.sustainability_linked || false,
        governing_law: deal.deal_data?.governing_law || 'NY',
        regulatory_framework: deal.deal_data?.regulatory_framework || ['US_Regulations']
      };
      
      setTransaction(populated);
      
      if (onTransactionBuilt) {
        onTransactionBuilt(populated);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load deal data');
    } finally {
      setLoading(false);
    }
  };
  
  const populateFromCdmData = (data: any) => {
    const populated: TestTransaction = {
      transaction_id: data.deal_id || data.loan_identification_number || 'CDM_TEST',
      transaction_type: 'facility_creation',
      originator: {
        id: data.parties?.[0]?.id,
        name: data.parties?.[0]?.name,
        lei: data.parties?.[0]?.lei,
        jurisdiction: data.parties?.[0]?.jurisdiction || 'US',
        kyc_status: true
      },
      amount: data.facilities?.[0]?.commitment_amount?.amount || 0,
      currency: data.facilities?.[0]?.commitment_amount?.currency || 'USD',
      facility_type: data.facilities?.[0]?.facility_type || 'SyndicatedLoan',
      sustainability_linked: data.sustainability_linked || false,
      governing_law: data.governing_law || 'NY',
      regulatory_framework: data.regulatory_framework || ['US_Regulations']
    };
    
    setTransaction(populated);
    
    if (onTransactionBuilt) {
      onTransactionBuilt(populated);
    }
  };
  
  const handleFieldChange = (path: string, value: any) => {
    const keys = path.split('.');
    const newTransaction = { ...transaction };
    
    let current: any = newTransaction;
    for (let i = 0; i < keys.length - 1; i++) {
      const key = keys[i];
      if (!current[key]) {
        current[key] = {};
      }
      current = current[key];
    }
    
    const lastKey = keys[keys.length - 1];
    current[lastKey] = value;
    
    setTransaction(newTransaction);
    
    if (onTransactionBuilt) {
      onTransactionBuilt(newTransaction);
    }
  };
  
  const handleJsonChange = (jsonString: string) => {
    try {
      const parsed = JSON.parse(jsonString);
      setTransaction(parsed);
      setError(null);
      
      if (onTransactionBuilt) {
        onTransactionBuilt(parsed);
      }
    } catch (err) {
      setError('Invalid JSON format');
    }
  };
  
  const handleSaveTestCase = () => {
    if (!testCaseName.trim()) {
      setError('Test case name is required');
      return;
    }
    
    const testCase: TestCase = {
      name: testCaseName,
      description: testCaseDescription,
      transaction: transaction,
      expected_decision: expectedDecision
    };
    
    setTestCases([...testCases, testCase]);
    setShowSaveDialog(false);
    setTestCaseName('');
    setTestCaseDescription('');
    setSuccess('Test case saved');
    
    if (onTestCaseSave) {
      onTestCaseSave(testCase);
    }
    
    setTimeout(() => setSuccess(null), 3000);
  };
  
  const handleLoadTestCase = (testCase: TestCase) => {
    setTransaction(testCase.transaction);
    setExpectedDecision(testCase.expected_decision);
    setActiveTab('form');
    
    if (onTransactionBuilt) {
      onTransactionBuilt(testCase.transaction);
    }
  };
  
  const handleDeleteTestCase = (index: number) => {
    setTestCases(testCases.filter((_, i) => i !== index));
  };
  
  const handleExportTestCases = () => {
    const dataStr = JSON.stringify(testCases, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'test_cases.json';
    link.click();
    URL.revokeObjectURL(url);
  };
  
  const handleImportTestCases = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const imported = JSON.parse(e.target?.result as string);
        if (Array.isArray(imported)) {
          setTestCases([...testCases, ...imported]);
          setSuccess(`Imported ${imported.length} test case(s)`);
        } else {
          setError('Invalid test cases file format');
        }
      } catch (err) {
        setError('Failed to parse test cases file');
      }
    };
    reader.readAsText(file);
  };
  
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <FileText className="h-6 w-6" />
            Test Transaction Builder
          </h2>
          <p className="text-muted-foreground">
            Build test transactions from deals, CDM data, or manually
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setShowSaveDialog(true)}
          >
            <Save className="h-4 w-4 mr-2" />
            Save Test Case
          </Button>
          {testCases.length > 0 && (
            <>
              <Button
                variant="outline"
                onClick={handleExportTestCases}
              >
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
              <label>
                <Button variant="outline" asChild>
                  <span>
                    <Upload className="h-4 w-4 mr-2" />
                    Import
                  </span>
                </Button>
                <input
                  type="file"
                  accept=".json"
                  onChange={handleImportTestCases}
                  className="hidden"
                />
              </label>
            </>
          )}
        </div>
      </div>
      
      {/* Success/Error Alerts */}
      {success && (
        <Alert>
          <CheckCircle2 className="h-4 w-4" />
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}
      {error && (
        <Alert variant="destructive">
          <X className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      
      {/* Transaction Builder */}
      <Card>
        <CardHeader>
          <CardTitle>Transaction</CardTitle>
          <CardDescription>
            {dealId && `Pre-populated from deal ${dealId}`}
            {cdmData && !dealId && 'Pre-populated from CDM data'}
            {!dealId && !cdmData && 'Build transaction manually'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
            <TabsList>
              <TabsTrigger value="form">Form</TabsTrigger>
              <TabsTrigger value="json">JSON</TabsTrigger>
              {testCases.length > 0 && (
                <TabsTrigger value="saved">
                  Saved ({testCases.length})
                </TabsTrigger>
              )}
            </TabsList>
            
            <TabsContent value="form" className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Transaction ID</Label>
                  <Input
                    value={transaction.transaction_id || ''}
                    onChange={(e) => handleFieldChange('transaction_id', e.target.value)}
                    placeholder="TEST_001"
                  />
                </div>
                <div>
                  <Label>Transaction Type</Label>
                  <Input
                    value={transaction.transaction_type || ''}
                    onChange={(e) => handleFieldChange('transaction_type', e.target.value)}
                    placeholder="facility_creation"
                  />
                </div>
              </div>
              
              <div>
                <Label>Originator Name</Label>
                <Input
                  value={transaction.originator?.name || ''}
                  onChange={(e) => handleFieldChange('originator.name', e.target.value)}
                  placeholder="Test Originator"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>LEI</Label>
                  <Input
                    value={transaction.originator?.lei || ''}
                    onChange={(e) => handleFieldChange('originator.lei', e.target.value)}
                    placeholder="TEST1234567890123456"
                  />
                </div>
                <div>
                  <Label>Jurisdiction</Label>
                  <Input
                    value={transaction.originator?.jurisdiction || ''}
                    onChange={(e) => handleFieldChange('originator.jurisdiction', e.target.value)}
                    placeholder="US"
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Amount</Label>
                  <Input
                    type="number"
                    value={transaction.amount || ''}
                    onChange={(e) => handleFieldChange('amount', parseFloat(e.target.value) || 0)}
                    placeholder="1000000"
                  />
                </div>
                <div>
                  <Label>Currency</Label>
                  <Input
                    value={transaction.currency || ''}
                    onChange={(e) => handleFieldChange('currency', e.target.value)}
                    placeholder="USD"
                  />
                </div>
              </div>
              
              <div>
                <Label>Facility Type</Label>
                <Input
                  value={transaction.facility_type || ''}
                  onChange={(e) => handleFieldChange('facility_type', e.target.value)}
                  placeholder="SyndicatedLoan"
                />
              </div>
              
              <div>
                <Label>
                  <input
                    type="checkbox"
                    checked={transaction.sustainability_linked || false}
                    onChange={(e) => handleFieldChange('sustainability_linked', e.target.checked)}
                    className="mr-2"
                  />
                  Sustainability Linked
                </Label>
              </div>
              
              <div>
                <Label>Governing Law</Label>
                <Input
                  value={transaction.governing_law || ''}
                  onChange={(e) => handleFieldChange('governing_law', e.target.value)}
                  placeholder="NY"
                />
              </div>
            </TabsContent>
            
            <TabsContent value="json" className="mt-4">
              <Textarea
                value={JSON.stringify(transaction, null, 2)}
                onChange={(e) => handleJsonChange(e.target.value)}
                className="font-mono text-sm h-[400px]"
                placeholder='{"transaction_id": "TEST_001", ...}'
              />
            </TabsContent>
            
            <TabsContent value="saved" className="mt-4">
              <div className="space-y-2">
                {testCases.map((testCase, index) => (
                  <Card key={index} className="cursor-pointer hover:bg-muted" onClick={() => handleLoadTestCase(testCase)}>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="font-semibold">{testCase.name}</h4>
                            <Badge variant="outline">{testCase.expected_decision}</Badge>
                          </div>
                          {testCase.description && (
                            <p className="text-sm text-muted-foreground">{testCase.description}</p>
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteTestCase(index);
                          }}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
      
      {/* Save Test Case Dialog */}
      <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save Test Case</DialogTitle>
            <DialogDescription>
              Save this transaction as a test case for regression testing
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Test Case Name *</Label>
              <Input
                value={testCaseName}
                onChange={(e) => setTestCaseName(e.target.value)}
                placeholder="e.g., Block Sanctioned Party Test"
              />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                value={testCaseDescription}
                onChange={(e) => setTestCaseDescription(e.target.value)}
                placeholder="Describe what this test case validates..."
                rows={3}
              />
            </div>
            <div>
              <Label>Expected Decision</Label>
              <select
                value={expectedDecision}
                onChange={(e) => setExpectedDecision(e.target.value as any)}
                className="w-full p-2 border rounded"
              >
                <option value="ALLOW">ALLOW</option>
                <option value="BLOCK">BLOCK</option>
                <option value="FLAG">FLAG</option>
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setShowSaveDialog(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSaveTestCase}
                disabled={!testCaseName.trim()}
              >
                <Save className="h-4 w-4 mr-2" />
                Save
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
