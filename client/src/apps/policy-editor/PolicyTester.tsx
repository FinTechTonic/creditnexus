/**
 * Policy Tester - Transaction builder and policy testing component.
 * 
 * Features:
 * - Transaction builder form
 * - Test transaction against policy
 * - Show evaluation trace
 * - Show matched rules
 * - Show decision result (ALLOW/BLOCK/FLAG)
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { fetchWithAuth } from '../../context/AuthContext';
import { 
  Play, 
  Loader2, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle,
  FileText,
  Code,
  List,
  ArrowRight
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';

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

interface TestResult {
  test_name: string;
  passed: boolean;
  expected_decision: string;
  actual_decision: string;
  matched_rules: string[];
  trace: any[];
  error?: string;
}

interface PolicyTesterProps {
  policyId?: number;
  initialTransaction?: TestTransaction;
  onTestComplete?: (result: TestResult) => void;
  className?: string;
}

export function PolicyTester({ 
  policyId: propPolicyId,
  initialTransaction,
  onTestComplete,
  className = '' 
}: PolicyTesterProps) {
  const { policyId: urlPolicyId } = useParams<{ policyId?: string }>();
  const policyId = propPolicyId || (urlPolicyId ? parseInt(urlPolicyId) : null);
  
  const [transaction, setTransaction] = useState<TestTransaction>(initialTransaction || {
    transaction_id: 'TEST_001',
    transaction_type: 'facility_creation',
    originator: {
      id: 'TEST_ORIGINATOR',
      name: 'Test Originator',
      lei: 'TEST1234567890123456',
      jurisdiction: 'US',
      kyc_status: true
    },
    amount: 1000000.0,
    currency: 'USD',
    facility_type: 'SyndicatedLoan',
    sustainability_linked: false,
    governing_law: 'NY',
    regulatory_framework: ['US_Regulations', 'FATF']
  });
  
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'form' | 'json'>('form');
  
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
  };
  
  const handleJsonChange = (jsonString: string) => {
    try {
      const parsed = JSON.parse(jsonString);
      setTransaction(parsed);
      setError(null);
    } catch (err) {
      // Invalid JSON - keep current transaction
      setError('Invalid JSON format');
    }
  };
  
  const handleTest = async () => {
    if (!policyId) {
      setError('No policy ID provided');
      return;
    }
    
    try {
      setTesting(true);
      setError(null);
      setTestResult(null);
      
      const response = await fetchWithAuth(`/api/policies/${policyId}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          test_transactions: [{
            transaction: transaction,
            expected_decision: 'ALLOW',
            test_name: 'Manual Test'
          }]
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to test policy');
      }
      
      const data = await response.json();
      if (data.results && data.results.length > 0) {
        const result = data.results[0];
        setTestResult(result);
        
        if (onTestComplete) {
          onTestComplete(result);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to test policy');
    } finally {
      setTesting(false);
    }
  };
  
  const getDecisionBadge = (decision: string) => {
    switch (decision.toUpperCase()) {
      case 'ALLOW':
        return <Badge className="bg-green-500"><CheckCircle2 className="h-3 w-3 mr-1" />ALLOW</Badge>;
      case 'BLOCK':
        return <Badge variant="destructive"><XCircle className="h-3 w-3 mr-1" />BLOCK</Badge>;
      case 'FLAG':
        return <Badge className="bg-yellow-500"><AlertTriangle className="h-3 w-3 mr-1" />FLAG</Badge>;
      default:
        return <Badge>{decision}</Badge>;
    }
  };
  
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Play className="h-6 w-6" />
            Policy Tester
          </h2>
          <p className="text-muted-foreground">
            Test transactions against the policy to verify behavior
          </p>
        </div>
        <Button
          onClick={handleTest}
          disabled={testing || !policyId}
        >
          {testing ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Testing...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Run Test
            </>
          )}
        </Button>
      </div>
      
      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      
      <div className="grid grid-cols-2 gap-6">
        {/* Left: Transaction Builder */}
        <Card>
          <CardHeader>
            <CardTitle>Test Transaction</CardTitle>
            <CardDescription>Build a transaction to test against the policy</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
              <TabsList>
                <TabsTrigger value="form">Form</TabsTrigger>
                <TabsTrigger value="json">JSON</TabsTrigger>
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
            </Tabs>
          </CardContent>
        </Card>
        
        {/* Right: Test Results */}
        <Card>
          <CardHeader>
            <CardTitle>Test Results</CardTitle>
            <CardDescription>Policy evaluation results</CardDescription>
          </CardHeader>
          <CardContent>
            {!testResult ? (
              <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground">
                <FileText className="h-12 w-12 mb-4 opacity-50" />
                <p>No test results yet. Click "Run Test" to evaluate the transaction.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Decision */}
                <div>
                  <Label>Decision</Label>
                  <div className="mt-2">
                    {getDecisionBadge(testResult.actual_decision)}
                  </div>
                </div>
                
                {/* Expected vs Actual */}
                {testResult.expected_decision && (
                  <div>
                    <Label>Expected: {testResult.expected_decision}</Label>
                    <div className="mt-1">
                      {testResult.passed ? (
                        <Alert>
                          <CheckCircle2 className="h-4 w-4" />
                          <AlertDescription>
                            Test passed - Decision matches expected
                          </AlertDescription>
                        </Alert>
                      ) : (
                        <Alert variant="destructive">
                          <XCircle className="h-4 w-4" />
                          <AlertDescription>
                            Test failed - Expected {testResult.expected_decision}, got {testResult.actual_decision}
                          </AlertDescription>
                        </Alert>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Matched Rules */}
                {testResult.matched_rules && testResult.matched_rules.length > 0 && (
                  <div>
                    <Label>Matched Rules ({testResult.matched_rules.length})</Label>
                    <div className="mt-2 space-y-1">
                      {testResult.matched_rules.map((rule, index) => (
                        <Badge key={index} variant="outline" className="mr-2">
                          {rule}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Evaluation Trace */}
                {testResult.trace && testResult.trace.length > 0 && (
                  <div>
                    <Label>Evaluation Trace</Label>
                    <div className="mt-2 p-4 bg-muted rounded-lg max-h-[200px] overflow-y-auto">
                      <pre className="text-xs font-mono">
                        {JSON.stringify(testResult.trace, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
                
                {/* Error */}
                {testResult.error && (
                  <Alert variant="destructive">
                    <XCircle className="h-4 w-4" />
                    <AlertDescription>{testResult.error}</AlertDescription>
                  </Alert>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
